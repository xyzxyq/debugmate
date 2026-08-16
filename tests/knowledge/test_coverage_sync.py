from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from debugmate.cli import main
from debugmate.contracts import ErrorCategory
from debugmate.knowledge.build import KnowledgeBuild, build_knowledge
from debugmate.knowledge.coverage import coverage_report
from debugmate.knowledge.models import KnowledgeSource, SourceRegistry
from debugmate.knowledge.sync import (
    DifyReadbackManifest,
    KnowledgeSyncError,
    MissingDatasetKey,
    SyncConfirmationRequired,
    SyncItem,
    SyncPlan,
    create_sync_plan,
    execute_sync,
    verify_remote_readback,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "knowledge" / "python-errors.html"


def _source(
    source_id: str = "python-errors",
    url: str = "https://docs.python.org/3/tutorial/errors.html",
) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=source_id,
        title=f"Python reference {source_id}",
        url=url,
        product="python",
        version_scope="Python 3",
        platform="cross-platform",
        allowed_domain="docs.python.org",
        heading_patterns=[r"^Exceptions$", r"^Handling Exceptions$"],
        error_categories=[ErrorCategory.PYTHON_RUNTIME],
        license_or_terms_note="Python documentation license applies.",
        selection_reason="Canonical Python runtime error reference.",
    )


def _fixture_client() -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Last-Modified": "Fri, 10 Jul 2026 08:00:00 GMT",
            },
            content=FIXTURE.read_bytes(),
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def build(tmp_path: Path) -> KnowledgeBuild:
    source = _source()
    registry = SourceRegistry(registry_version="1.0.0", sources=[source])
    with _fixture_client() as client:
        return build_knowledge(registry, tmp_path / "builds", client)


@pytest.fixture
def two_source_build(tmp_path: Path) -> KnowledgeBuild:
    registry = SourceRegistry(
        registry_version="1.0.0",
        sources=[
            _source(),
            _source(
                source_id="python-venv",
                url="https://docs.python.org/3/library/venv.html",
            ),
        ],
    )
    with _fixture_client() as client:
        return build_knowledge(registry, tmp_path / "two-builds", client)


def test_coverage_reports_all_categories_and_sorted_blind_spots(
    build: KnowledgeBuild,
) -> None:
    report = coverage_report(build)

    assert set(report.categories) == set(ErrorCategory)
    assert report.blind_spots == sorted(report.blind_spots)
    covered = report.categories[ErrorCategory.PYTHON_RUNTIME]
    assert covered.source_count == 1
    assert covered.note_count == 1
    assert covered.locator_count == 2
    assert covered.last_fetched_utc is not None
    assert covered.current_build_hash == build.content_hash
    assert report.categories[ErrorCategory.CUDA_MEMORY].source_count == 0
    assert ErrorCategory.CUDA_MEMORY.value in report.blind_spots


def test_sync_plan_is_deterministic_and_classifies_every_operation(
    build: KnowledgeBuild,
) -> None:
    note_hash = build.notes[0].content_sha256
    remote_manifest = {
        "documents": [
            {
                "source_id": "python-errors",
                "content_sha256": note_hash,
                "document_id": "doc-python",
            },
            {
                "source_id": "stale-source",
                "content_sha256": "a" * 64,
                "document_id": "doc-stale",
            },
        ]
    }

    unchanged = create_sync_plan(build, remote_manifest)
    changed_manifest = {
        "documents": [
            {
                "source_id": "python-errors",
                "content_sha256": "b" * 64,
                "document_id": "doc-python",
            }
        ]
    }
    update = create_sync_plan(build, changed_manifest)
    create = create_sync_plan(build, {"documents": []})

    assert [item.source_id for item in unchanged.unchanged] == ["python-errors"]
    assert [item.source_id for item in unchanged.deletes] == ["stale-source"]
    assert [item.source_id for item in update.updates] == ["python-errors"]
    assert [item.source_id for item in create.creates] == ["python-errors"]
    assert unchanged.model_dump(mode="json") == create_sync_plan(build, remote_manifest).model_dump(
        mode="json"
    )


def test_sync_plan_rejects_noncanonical_local_note_path(build: KnowledgeBuild) -> None:
    manifest_path = build.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["notes"][0]["path"] = "../outside.md"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(KnowledgeSyncError, match="canonical"):
        create_sync_plan(build.path, {"documents": []})


def test_dry_run_performs_zero_http_and_needs_no_key(build: KnowledgeBuild) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise AssertionError("dry-run must not make HTTP requests")

    plan = create_sync_plan(build, {"documents": []})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = execute_sync(plan, client=client, dry_run=True)

    assert result.executed is False
    assert result.operation_count == 1
    assert calls == []


def test_note_and_declared_hash_tamper_is_rejected_before_planning(
    build: KnowledgeBuild,
) -> None:
    calls: list[httpx.Request] = []
    note_path = build.path / "notes" / "python-errors.md"
    note_path.write_text("tampered together with its declared hash", encoding="utf-8")
    manifest_path = build.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["notes"][0]["note_sha256"] = hashlib.sha256(note_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)),
        pytest.raises((KnowledgeSyncError, ValueError), match="identity|manifest"),
    ):
        create_sync_plan(build.path, {"documents": []})

    assert calls == []


def test_sync_plan_and_request_carry_source_metadata_and_fixed_dify_config(
    build: KnowledgeBuild,
) -> None:
    requests: list[httpx.Request] = []
    plan = create_sync_plan(build, {"documents": []})

    assert plan.document_count == 1
    assert plan.config.chunk_size == 800
    assert plan.config.chunk_overlap == 120
    assert plan.config.indexing_technique == "economy"
    assert plan.config.retrieval_method == "keyword_search"
    assert plan.config.top_k == 3
    assert plan.config.score_threshold_enabled is False
    assert plan.config.score_threshold == 0.5
    assert plan.creates[0].source_metadata.product == "python"
    assert plan.creates[0].source_metadata.source_sha256 == build.notes[0].source_sha256

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "created"})

    with httpx.Client(
        base_url="https://api.dify.ai/v1/",
        transport=httpx.MockTransport(handler),
    ) as client:
        execute_sync(
            plan,
            client=client,
            dataset_key="dataset-key",
            dataset_id="dataset",
            dry_run=False,
        )

    payload = json.loads(requests[0].content)
    assert "doc_metadata" not in payload
    assert payload["process_rule"]["rules"]["segmentation"] == {
        "separator": "\n",
        "max_tokens": 800,
        "chunk_overlap": 120,
    }
    assert payload["indexing_technique"] == "economy"
    assert payload["retrieval_model"] == {
        "search_method": "keyword_search",
        "reranking_enable": True,
        "top_k": 3,
        "score_threshold_enabled": False,
        "score_threshold": 0.5,
    }


def test_remote_readback_strictly_compares_count_metadata_hashes_and_config(
    build: KnowledgeBuild,
) -> None:
    plan = create_sync_plan(build, {"documents": []})
    item = plan.creates[0]
    readback = DifyReadbackManifest(
        document_count=1,
        documents=[
            {
                "source_id": item.source_id,
                "content_sha256": item.content_sha256,
                "document_id": "doc-python",
                "source_metadata": item.source_metadata,
            }
        ],
        config=plan.config,
    )

    assert verify_remote_readback(plan, readback) == readback

    wrong_count = readback.model_copy(update={"document_count": 2})
    with pytest.raises(KnowledgeSyncError, match="document count"):
        verify_remote_readback(plan, wrong_count)
    wrong_config = readback.model_copy(
        update={"config": readback.config.model_copy(update={"chunk_size": 799})}
    )
    with pytest.raises(KnowledgeSyncError, match="configuration"):
        verify_remote_readback(plan, wrong_config)


def test_sync_never_deletes_without_confirmation(build: KnowledgeBuild) -> None:
    plan = create_sync_plan(
        build,
        {
            "documents": [
                {
                    "source_id": "stale-source",
                    "content_sha256": "a" * 64,
                    "document_id": "doc-stale",
                }
            ]
        },
    )

    with pytest.raises(SyncConfirmationRequired):
        execute_sync(
            plan,
            client=httpx.Client(),
            dataset_key="secret",
            dataset_id="dataset",
            confirm_delete=False,
            dry_run=False,
        )


def test_real_sync_requires_dataset_key(build: KnowledgeBuild) -> None:
    plan = create_sync_plan(build, {"documents": []})

    with pytest.raises(MissingDatasetKey):
        execute_sync(
            plan,
            client=httpx.Client(),
            dataset_id="dataset",
            dry_run=False,
        )


def test_real_sync_revalidates_note_bytes_before_upload(build: KnowledgeBuild) -> None:
    requests: list[httpx.Request] = []
    plan = create_sync_plan(build, {"documents": []})
    (build.path / "notes" / "python-errors.md").write_text(
        "changed after planning", encoding="utf-8"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(KnowledgeSyncError, match="changed"),
    ):
        execute_sync(
            plan,
            client=client,
            dataset_key="dataset-key",
            dataset_id="dataset",
            dry_run=False,
        )

    assert requests == []


def test_real_sync_rejects_unsafe_dataset_identifier(build: KnowledgeBuild) -> None:
    plan = create_sync_plan(build, {"documents": []})

    with pytest.raises(KnowledgeSyncError, match="dataset_id"):
        execute_sync(
            plan,
            client=httpx.Client(),
            dataset_key="dataset-key",
            dataset_id="../another-dataset",
            dry_run=False,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [("source_id", "../victim"), ("remote_document_id", "doc/escape")],
)
def test_sync_item_rejects_unsafe_identifiers(field: str, value: str) -> None:
    values: dict[str, object] = {
        "action": "delete",
        "source_id": "stale-source",
        "content_sha256": "a" * 64,
        "remote_document_id": "doc-stale",
    }
    values[field] = value

    with pytest.raises(ValidationError):
        SyncItem(**values)


def test_sync_item_enforces_action_field_invariants(build: KnowledgeBuild) -> None:
    with pytest.raises(ValidationError):
        SyncItem(
            action="delete",
            source_id="stale-source",
            content_sha256="a" * 64,
            local_path=build.path / "notes" / "python-errors.md",
            remote_document_id="doc-stale",
        )


def test_sync_plan_enforces_action_lists_and_build_bound_paths(
    build: KnowledgeBuild,
    tmp_path: Path,
) -> None:
    valid = create_sync_plan(build, {"documents": []})
    with pytest.raises(ValidationError, match="different action"):
        SyncPlan(
            build_id=valid.build_id,
            build_hash=valid.build_hash,
            build_path=valid.build_path,
            creates=[],
            updates=[],
            unchanged=[],
            deletes=valid.creates,
        )

    outside = SyncItem(
        action="create",
        source_id="python-errors",
        content_sha256=build.notes[0].content_sha256,
        local_path=tmp_path / "outside.md",
        source_metadata=valid.creates[0].source_metadata,
    )
    with pytest.raises(ValidationError, match="bound"):
        SyncPlan(
            build_id=valid.build_id,
            build_hash=valid.build_hash,
            build_path=valid.build_path,
            document_count=1,
            source_manifest_hash=valid.source_manifest_hash,
            config=valid.config,
            creates=[outside],
            updates=[],
            unchanged=[],
            deletes=[],
        )


def test_tampered_plan_or_current_build_identity_causes_zero_http(
    build: KnowledgeBuild,
) -> None:
    requests: list[httpx.Request] = []
    valid = create_sync_plan(build, {"documents": []})
    tampered = valid.model_copy(update={"build_hash": "a" * 64})

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    with httpx.Client(
        base_url="https://api.dify.ai/v1/",
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(KnowledgeSyncError, match="plan"):
            execute_sync(
                tampered,
                client=client,
                dataset_key="dataset-key",
                dataset_id="dataset",
                dry_run=False,
            )

        manifest_path = build.path / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["content_hash"] = "b" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(KnowledgeSyncError, match="identity"):
            execute_sync(
                valid,
                client=client,
                dataset_key="dataset-key",
                dataset_id="dataset",
                dry_run=False,
            )

    assert requests == []


def test_directly_constructed_malicious_delete_plan_is_rejected_before_http(
    build: KnowledgeBuild,
) -> None:
    requests: list[httpx.Request] = []
    malicious = SyncPlan(
        build_id=build.build_id,
        build_hash=build.content_hash,
        build_path=build.path,
        creates=[],
        updates=[],
        unchanged=[],
        deletes=[
            SyncItem(
                action="delete",
                source_id="stale-source",
                content_sha256="a" * 64,
                remote_document_id="doc-stale",
            )
        ],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    with (
        httpx.Client(
            base_url="https://api.dify.ai/v1/",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(KnowledgeSyncError, match="plan"),
    ):
        execute_sync(
            malicious,
            client=client,
            dataset_key="dataset-key",
            dataset_id="dataset",
            confirm_delete=True,
            dry_run=False,
        )

    assert requests == []


def test_stale_second_note_causes_zero_cloud_calls(
    two_source_build: KnowledgeBuild,
) -> None:
    requests: list[httpx.Request] = []
    plan = create_sync_plan(two_source_build, {"documents": []})
    second_note = two_source_build.path / "notes" / "python-venv.md"
    second_note.write_text("changed after planning", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    with (
        httpx.Client(
            base_url="https://api.dify.ai/v1/",
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(KnowledgeSyncError, match="changed"),
    ):
        execute_sync(
            plan,
            client=client,
            dataset_key="dataset-key",
            dataset_id="dataset",
            dry_run=False,
        )

    assert requests == []


@pytest.mark.cloud
def test_cloud_marked_executor_sends_key_only_during_explicit_execution(
    build: KnowledgeBuild,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "created"})

    plan = create_sync_plan(build, {"documents": []})
    with httpx.Client(
        base_url="https://api.dify.ai/v1/",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = execute_sync(
            plan,
            client=client,
            dataset_key="dataset-key",
            dataset_id="dataset",
            dry_run=False,
        )

    assert result.executed is True
    assert len(requests) == 1
    assert requests[0].headers["authorization"] == "Bearer dataset-key"
    assert requests[0].url == ("https://api.dify.ai/v1/datasets/dataset/document/create-by-text")


def test_coverage_cli_emits_ascii_safe_json(
    build: KnowledgeBuild,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["knowledge-coverage", str(build.path)]) == 0

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["build_id"] == build.build_id
    assert all(ord(character) < 128 for character in output)
