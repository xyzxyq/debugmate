from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from debugmate import cli
from debugmate.cli import main
from debugmate.knowledge.build import build_knowledge
from debugmate.knowledge.models import load_registry
from debugmate.knowledge.sync import (
    DifyReadbackAttestation,
    DifySyncConfig,
    KnowledgeSyncError,
    MissingDatasetKey,
    SyncConfirmationRequired,
    list_remote_documents,
    synchronize_knowledge,
)


def _seventeen_source_build(tmp_path: Path):
    registry = load_registry(Path("knowledge/sources.json"))
    headings = "".join(
        f"<h2>{heading}</h2><p>Deterministic fixture content for {heading}.</p>"
        for heading in (
            "Syntax Errors",
            "Exceptions",
            "Handling Exceptions",
            "Raising Exceptions",
            "Creating virtual environments",
            "How venvs work",
            "The import system",
            "Searching",
            "Loading",
            "Dependency Resolution",
            "Backtracking",
            "Reduce the number of versions pip is trying to use",
            "Installing Packages",
            "Requirements Files",
            "Constraints Files",
            "CUDA semantics",
            "Asynchronous execution",
            "Memory management",
            "Serialization semantics",
            "Saving and loading tensors",
            "torch.load with weights_only=True",
            "torch.Tensor.view",
            "CUDA Compatibility",
            "System Requirements",
            "Installing CUDA Development Tools",
            "Verifying the Installation",
            "Installation",
            "Install with pip",
            "Offline mode",
            "Understand caching",
            "Cache limitations",
            "Cache-system reference",
            "Install Ultralytics",
            "Headless Server Installation",
            "Use Ultralytics with Python",
            "Model Prediction with Ultralytics YOLO",
            "Key Features of Predict Mode",
            "Inference Sources",
            "about_Environment_Variables",
            "Use the variable syntax",
            "Create persistent environment variables in Windows",
            "Path information",
            "About Execution Policies",
            "PowerShell execution policies",
            "Manage the execution policy",
            "File path formats on Windows systems",
            "Traditional DOS paths",
            "UNC paths",
            "Path normalization",
        )
    ).encode()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html", "Last-Modified": "Fri, 10 Jul 2026 08:00:00 GMT"},
            content=b"<html><body>" + headings + b"</body></html>",
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return build_knowledge(registry, tmp_path / "builds", client)


def test_paginated_inventory_collects_all_pages_and_rejects_duplicates() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = int(request.url.params["page"])
        document_id = "doc-one" if page == 1 else "doc-two"
        source_id = "source-one" if page == 1 else "source-two"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": document_id,
                        "name": source_id,
                        "doc_metadata": [
                            {"name": "source_id", "value": source_id},
                            {"name": "content_sha256", "value": "a" * 64},
                        ],
                    }
                ],
                "page": page,
                "limit": 1,
                "total": 2,
                "has_more": page == 1,
            },
        )

    with httpx.Client(
        base_url="https://api.dify.ai/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        manifest = list_remote_documents(
            client, "dataset", {"Authorization": "Bearer key"}, page_size=1
        )

    assert [item.source_id for item in manifest.documents] == ["source-one", "source-two"]
    assert [request.url.params["page"] for request in requests] == ["1", "2"]

    def duplicate_handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": f"doc-{page}",
                        "name": "source-one",
                        "doc_metadata": [
                            {"name": "source_id", "value": "source-one"},
                            {"name": "content_sha256", "value": "a" * 64},
                        ],
                    }
                ],
                "page": page,
                "limit": 1,
                "total": 2,
                "has_more": page == 1,
            },
        )

    with (
        httpx.Client(
            base_url="https://api.dify.ai/v1/", transport=httpx.MockTransport(duplicate_handler)
        ) as client,
        pytest.raises(KnowledgeSyncError, match="duplicate"),
    ):
        list_remote_documents(client, "dataset", {"Authorization": "Bearer key"}, page_size=1)


def test_full_seventeen_source_sync_polls_then_writes_metadata_and_exactly_reads_back(
    tmp_path: Path,
) -> None:
    build = _seventeen_source_build(tmp_path)
    assert len(build.notes) == 17
    requests: list[httpx.Request] = []
    documents: list[dict[str, object]] = []
    fields: list[dict[str, str]] = []
    pending_metadata: dict[str, list[dict[str, str]]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if request.method == "GET" and path.endswith("/documents"):
            return httpx.Response(
                200,
                json={
                    "data": documents,
                    "page": 1,
                    "limit": 100,
                    "total": len(documents),
                    "has_more": False,
                },
            )
        if request.method == "POST" and path.endswith("/document/create-by-text"):
            payload = json.loads(request.content)
            assert "doc_metadata" not in payload
            index = len(documents)
            document = {"id": f"doc-{index}", "name": payload["name"], "doc_metadata": []}
            documents.append(document)
            return httpx.Response(
                200, json={"document": {"id": document["id"]}, "batch": f"batch-{index}"}
            )
        if request.method == "GET" and path.endswith("/indexing-status"):
            return httpx.Response(
                200,
                json={"data": [{"id": "opaque", "indexing_status": "completed", "error": None}]},
            )
        if request.method == "GET" and path.endswith("/metadata"):
            return httpx.Response(200, json={"doc_metadata": fields})
        if request.method == "POST" and path.endswith("/metadata") and "/documents/" not in path:
            payload = json.loads(request.content)
            field = {"id": f"field-{len(fields)}", "name": payload["name"], "type": payload["type"]}
            fields.append(field)
            return httpx.Response(200, json=field)
        if request.method == "POST" and path.endswith("/documents/metadata"):
            for operation in json.loads(request.content)["operation_data"]:
                pending_metadata[operation["document_id"]] = operation["metadata_list"]
            for document in documents:
                document["doc_metadata"] = [
                    {
                        "id": item["id"],
                        "name": next(
                            field["name"] for field in fields if field["id"] == item["id"]
                        ),
                        "value": item["value"],
                    }
                    for item in pending_metadata[str(document["id"])]
                ]
            return httpx.Response(200, json={"result": "success"})
        if request.method == "GET" and path.endswith("/datasets/dataset"):
            return httpx.Response(
                200,
                json={
                    "indexing_technique": "high_quality",
                    "retrieval_model_dict": {
                        "search_method": "semantic_search",
                        "top_k": 3,
                        "score_threshold_enabled": True,
                        "score_threshold": 0.5,
                    },
                    "process_rule": {
                        "rules": {"segmentation": {"max_tokens": 800, "chunk_overlap": 120}}
                    },
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {path}")

    with httpx.Client(
        base_url="https://api.dify.ai/v1/", transport=httpx.MockTransport(handler)
    ) as client:
        attestation = synchronize_knowledge(
            build.path,
            client=client,
            dataset_key="dataset-key",
            dataset_id="dataset",
            sleep=lambda _seconds: None,
            monotonic=lambda: 0.0,
        )

    assert attestation.document_count == 17
    assert attestation.knowledge_build_id == build.build_id
    assert len(attestation.document_fingerprints) == 17
    serialized = attestation.model_dump_json()
    assert "dataset-key" not in serialized
    assert 'dataset"' not in serialized
    assert all(str(document["id"]) not in serialized for document in documents)
    metadata_call = next(
        i for i, request in enumerate(requests) if request.url.path.endswith("/documents/metadata")
    )
    last_poll = max(
        i for i, request in enumerate(requests) if request.url.path.endswith("/indexing-status")
    )
    assert metadata_call > last_poll


def test_live_sync_fails_before_mutation_for_key_delete_and_index_error(tmp_path: Path) -> None:
    build = _seventeen_source_build(tmp_path)
    calls: list[httpx.Request] = []

    def poison(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise AssertionError("no request expected")

    with (
        httpx.Client(
            base_url="https://api.dify.ai/v1/", transport=httpx.MockTransport(poison)
        ) as client,
        pytest.raises(MissingDatasetKey, match="dataset_key_missing"),
    ):
        synchronize_knowledge(build.path, client=client, dataset_key=None, dataset_id="dataset")
    assert calls == []

    remote = {
        "id": "doc-stale",
        "name": "stale-source",
        "doc_metadata": [
            {"name": "source_id", "value": "stale-source"},
            {"name": "content_sha256", "value": "a" * 64},
        ],
    }

    def stale_handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200, json={"data": [remote], "page": 1, "limit": 100, "total": 1, "has_more": False}
        )

    calls.clear()
    with (
        httpx.Client(
            base_url="https://api.dify.ai/v1/", transport=httpx.MockTransport(stale_handler)
        ) as client,
        pytest.raises(SyncConfirmationRequired),
    ):
        synchronize_knowledge(build.path, client=client, dataset_key="key", dataset_id="dataset")
    assert all(request.method == "GET" for request in calls)


def test_missing_inventory_page_fails_closed() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"data": [], "page": 1, "limit": 100, "total": 1, "has_more": False}
        )

    with (
        httpx.Client(
            base_url="https://api.dify.ai/v1/", transport=httpx.MockTransport(handler)
        ) as client,
        pytest.raises(KnowledgeSyncError, match="pagination"),
    ):
        list_remote_documents(client, "dataset", {"Authorization": "Bearer key"})


def test_cli_default_sync_never_constructs_an_http_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    build = _seventeen_source_build(tmp_path)

    def poison_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("offline knowledge-sync must not construct HTTP")

    monkeypatch.setattr(cli.httpx, "Client", poison_client)
    assert main(["knowledge-sync", str(build.path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["executed"] is False
    assert payload["document_count"] == 17
    assert "dataset_id" not in payload
    assert "document_id" not in json.dumps(payload)


def test_cli_execute_missing_key_is_value_free_and_transport_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    build = _seventeen_source_build(tmp_path)
    monkeypatch.delenv("DIFY_DATASET_API_KEY", raising=False)
    monkeypatch.setenv("DIFY_DATASET_ID", "dataset-binding")

    def poison_client(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("missing configuration must fail before HTTP construction")

    monkeypatch.setattr(cli.httpx, "Client", poison_client)
    assert main(["knowledge-sync", str(build.path), "--execute"]) == 1
    assert json.loads(capsys.readouterr().out) == {"code": "dataset_key_missing", "ok": False}


def test_attestation_output_is_strict_validated_and_atomically_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    build = _seventeen_source_build(tmp_path)
    output = tmp_path / "nested" / "attestation.json"
    monkeypatch.setenv("DIFY_DATASET_API_KEY", "secret-key")
    monkeypatch.setenv("DIFY_DATASET_ID", "dataset-binding")
    attestation = DifyReadbackAttestation(
        knowledge_build_id=build.build_id,
        dataset_fingerprint="a" * 64,
        document_count=17,
        document_fingerprints=[f"{index:064x}" for index in range(1, 18)],
        config=DifySyncConfig(),
        response_hashes=["f" * 64],
    )

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(cli.httpx, "Client", lambda **_kwargs: FakeClient())
    monkeypatch.setattr(cli, "synchronize_knowledge", lambda *_args, **_kwargs: attestation)
    assert main(
        [
            "knowledge-sync",
            str(build.path),
            "--execute",
            "--attestation-output",
            str(output),
        ]
    ) == 0
    written = DifyReadbackAttestation.model_validate_json(
        output.read_text(encoding="utf-8"), strict=True
    )
    assert written == attestation
    stdout = capsys.readouterr().out
    assert "secret-key" not in stdout
    assert "dataset-binding" not in stdout
