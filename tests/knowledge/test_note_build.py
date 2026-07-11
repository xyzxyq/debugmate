from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from pathlib import Path

import httpx
import pytest

from debugmate.contracts import ErrorCategory
from debugmate.knowledge.build import ImmutableBuildCollision, build_knowledge
from debugmate.knowledge.models import KnowledgeSource, SourceRegistry
from debugmate.knowledge.note_builder import NoteSummarizer

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "knowledge"
    / "python-errors.html"
)


@pytest.fixture
def source() -> KnowledgeSource:
    return KnowledgeSource(
        source_id="python-errors",
        title="Python Errors and Exceptions",
        url="https://docs.python.org/3/tutorial/errors.html",
        product="python",
        version_scope="Python 3",
        platform="cross-platform",
        allowed_domain="docs.python.org",
        heading_patterns=[r"^Exceptions$", r"^Handling Exceptions$"],
        error_categories=[ErrorCategory.PYTHON_RUNTIME],
        license_or_terms_note="Python documentation license applies.",
        selection_reason="Canonical Python runtime error reference.",
    )


@pytest.fixture
def registry(source: KnowledgeSource) -> SourceRegistry:
    return SourceRegistry(registry_version="1.0.0", sources=[source])


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def fixture_client() -> httpx.Client:
    raw = FIXTURE.read_bytes()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "ETag": '"fixture-v1"',
                "Last-Modified": "Fri, 10 Jul 2026 08:00:00 GMT",
            },
            content=raw,
        )

    with _client(handler) as client:
        yield client


def test_repeated_fixture_build_has_identical_notes_and_build_id(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
) -> None:
    first = build_knowledge(registry, tmp_path / "one", fixture_client)
    second = build_knowledge(registry, tmp_path / "two", fixture_client)

    assert first.status == "ready"
    assert first.syncable is True
    assert first.build_id == second.build_id
    assert first.content_hash == second.content_hash
    assert first.notes[0].markdown.encode() == second.notes[0].markdown.encode()
    assert (first.path / "notes" / "python-errors.md").read_bytes() == (
        second.path / "notes" / "python-errors.md"
    ).read_bytes()


def test_note_has_source_anchors_and_never_copies_full_page(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
) -> None:
    build = build_knowledge(registry, tmp_path, fixture_client)
    [note] = build.notes

    assert note.source_id == "python-errors"
    assert note.source_sha256
    assert note.locators == ["#exceptions", "#handling-exceptions"]
    assert all(locator in note.markdown for locator in note.locators)
    assert "## 症状与分类" in note.markdown
    assert "## 诊断事实" in note.markdown
    assert "## 检查建议" in note.markdown
    assert "## 版本与平台限制" in note.markdown
    assert "## 来源锚点" in note.markdown
    assert "## 短摘录" in note.markdown
    assert len(note.markdown.encode("utf-8")) < 32_000
    assert FIXTURE.read_text(encoding="utf-8") not in note.markdown
    assert "<html" not in note.markdown
    assert "Documentation footer" not in note.markdown
    assert note.content_sha256 == hashlib.sha256(note.markdown.encode()).hexdigest()


class _InvalidSummarizer(NoteSummarizer):
    def summarize(
        self,
        *,
        source: KnowledgeSource,
        sections: Sequence[object],
    ) -> Sequence[str]:
        del source, sections
        return ["Run a newly invented command without an anchor."]


class _GroundedSummarizer(NoteSummarizer):
    def summarize(
        self,
        *,
        source: KnowledgeSource,
        sections: Sequence[object],
    ) -> Sequence[str]:
        del source, sections
        return ["#exceptions：释义，异常回溯应核对 exception type 和 message。"]


class _InventedCommandSummarizer(NoteSummarizer):
    def summarize(
        self,
        *,
        source: KnowledgeSource,
        sections: Sequence[object],
    ) -> Sequence[str]:
        del source, sections
        return ["#exceptions：请运行 rm -rf / 修复 exception type 和 message。"]


def test_invalid_optional_summary_falls_back_to_grounded_templates(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
) -> None:
    default = build_knowledge(registry, tmp_path / "default", fixture_client)
    invalid = build_knowledge(
        registry,
        tmp_path / "invalid",
        fixture_client,
        summarizer=_InvalidSummarizer(),
    )

    assert invalid.notes[0].markdown == default.notes[0].markdown
    assert "invented command" not in invalid.notes[0].markdown


def test_grounded_summary_changes_content_and_therefore_build_id(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
) -> None:
    default = build_knowledge(registry, tmp_path, fixture_client)
    grounded = build_knowledge(
        registry,
        tmp_path,
        fixture_client,
        summarizer=_GroundedSummarizer(),
    )

    assert grounded.notes[0].markdown != default.notes[0].markdown
    assert grounded.build_id != default.build_id
    assert "### 可选摘要（释义）" in grounded.notes[0].markdown
    assert "官方“Exceptions”章节记录" in grounded.notes[0].markdown


def test_locator_and_chinese_do_not_make_an_invented_command_grounded(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
) -> None:
    default = build_knowledge(registry, tmp_path / "default", fixture_client)
    malicious = build_knowledge(
        registry,
        tmp_path / "malicious",
        fixture_client,
        summarizer=_InventedCommandSummarizer(),
    )

    assert malicious.notes[0].markdown == default.notes[0].markdown
    assert "rm -rf" not in malicious.notes[0].markdown


def test_partial_failure_writes_failed_unsyncable_manifest(
    tmp_path: Path,
    source: KnowledgeSource,
) -> None:
    second_source = KnowledgeSource(
        **{
            **source.model_dump(),
            "source_id": "python-venv",
            "title": "Python venv",
            "url": "https://docs.python.org/3/library/venv.html",
        }
    )
    registry = SourceRegistry(
        registry_version="1.0.0", sources=[source, second_source]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == source.url:
            return httpx.Response(
                200,
                headers={"Content-Type": "text/html; charset=utf-8"},
                content=FIXTURE.read_bytes(),
            )
        return httpx.Response(503, headers={"Content-Type": "text/html"})

    with _client(handler) as client:
        build = build_knowledge(registry, tmp_path, client)

    assert build.status == "failed"
    assert build.syncable is False
    assert [note.source_id for note in build.notes] == ["python-errors"]
    manifest = json.loads((build.path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["syncable"] is False
    assert manifest["document_count"] == 1
    assert manifest["failures"] == [
        {
            "error_type": "SourceStatusError",
            "message": "source 'python-venv' returned HTTP 503",
            "source_id": "python-venv",
        }
    ]


def test_different_failures_cannot_share_an_immutable_build_id(
    tmp_path: Path,
    registry: SourceRegistry,
) -> None:
    def status_client(status: int) -> httpx.Client:
        return _client(
            lambda _request: httpx.Response(
                status, headers={"Content-Type": "text/html"}
            )
        )

    with status_client(404) as first_client:
        first = build_knowledge(registry, tmp_path, first_client)
    with status_client(503) as second_client:
        second = build_knowledge(registry, tmp_path, second_client)

    assert first.build_id != second.build_id


def test_manifest_records_immutable_build_contract(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
) -> None:
    build = build_knowledge(registry, tmp_path, fixture_client)
    manifest = json.loads((build.path / "manifest.json").read_text(encoding="utf-8"))

    assert build.path == tmp_path / build.build_id
    assert manifest["build_id"] == build.build_id
    assert manifest["registry_version"] == "1.0.0"
    assert manifest["chunk_settings"] == {"overlap": 120, "size": 800}
    assert manifest["generator_version"]
    assert manifest["extractor_version"]
    assert manifest["document_count"] == 1
    assert manifest["categories"] == ["python_runtime"]
    assert manifest["failures"] == []
    assert manifest["notes"][0]["source_id"] == "python-errors"
    assert manifest["notes"][0]["source_sha256"] == build.notes[0].source_sha256
    assert manifest["notes"][0]["note_sha256"] == build.notes[0].content_sha256
    assert manifest["sources"][0]["retrieved_at"].endswith("Z")


def test_existing_immutable_build_is_reused_without_replacement(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
) -> None:
    first = build_knowledge(registry, tmp_path, fixture_client)
    marker = first.path / "preserve.txt"
    marker.write_text("immutable", encoding="utf-8")

    second = build_knowledge(registry, tmp_path, fixture_client)

    assert second.path == first.path
    assert marker.read_text(encoding="utf-8") == "immutable"


def test_reuse_tolerates_changed_response_metadata_and_keeps_first_manifest(
    tmp_path: Path,
    registry: SourceRegistry,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "ETag": f'"fixture-v{calls}"',
                "Last-Modified": f"Fri, {9 + calls} Jul 2026 08:00:00 GMT",
            },
            content=FIXTURE.read_bytes(),
        )

    with _client(handler) as client:
        first = build_knowledge(registry, tmp_path, client)
        first_manifest_bytes = (first.path / "manifest.json").read_bytes()
        first_manifest = json.loads(first_manifest_bytes)
        second = build_knowledge(registry, tmp_path, client)

    assert second.build_id == first.build_id
    assert (second.path / "manifest.json").read_bytes() == first_manifest_bytes
    assert first_manifest["sources"][0]["etag"] == '"fixture-v1"'
    assert first_manifest["sources"][0]["last_modified"] == (
        "Fri, 10 Jul 2026 08:00:00 GMT"
    )


@pytest.mark.parametrize("tamper", ["extra", "missing", "changed"])
def test_reuse_rejects_unmanifested_missing_or_changed_note_files(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
    tamper: str,
) -> None:
    build = build_knowledge(registry, tmp_path, fixture_client)
    note_path = build.path / "notes" / "python-errors.md"
    if tamper == "extra":
        (build.path / "notes" / "unmanifested.md").write_text(
            "not declared", encoding="utf-8"
        )
    elif tamper == "missing":
        note_path.unlink()
    else:
        note_path.write_text("changed", encoding="utf-8")

    with pytest.raises(ImmutableBuildCollision):
        build_knowledge(registry, tmp_path, fixture_client)


def test_reuse_rejects_invalid_first_published_manifest(
    tmp_path: Path,
    registry: SourceRegistry,
    fixture_client: httpx.Client,
) -> None:
    build = build_knowledge(registry, tmp_path, fixture_client)
    manifest_path = build.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"][0]["retrieved_at"] = "not-a-utc-timestamp"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ImmutableBuildCollision):
        build_knowledge(registry, tmp_path, fixture_client)
