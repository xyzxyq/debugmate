from __future__ import annotations

import builtins
import json
import socket
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from debugmate.contracts import new_case_id
from debugmate.knowledge.local_rule import load_local_rule_snapshot
from debugmate.privacy.approval import approve_preview
from debugmate.privacy.models import InputEnvelope
from debugmate.privacy.text_redactor import redact_input
from debugmate.results.contracts import ResultMode, ResultStatus
from debugmate.ui import serve as serve_module
from debugmate.ui.local_live import LocalPreviewStore

_KEY = b"local-live-approval-key-is-32bytes"


class _TrackedLock:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.waiting = threading.Event()

    def __enter__(self):
        if not self._lock.acquire(blocking=False):
            self.waiting.set()
            self._lock.acquire()
        return self

    def __exit__(self, *_args: object) -> None:
        self._lock.release()


def _preview(label: str = "ModuleNotFoundError"):
    return redact_input(InputEnvelope(case_id=new_case_id(), error_text=label))


def _publish(store: LocalPreviewStore, session: str, label: str = "ModuleNotFoundError"):
    revision = store.snapshot_revision(session)
    presentation = store.publish_if_current(session, revision, _preview(label))
    assert presentation is not None
    return presentation


def test_preview_store_atomically_consumes_only_same_session_token() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    store = LocalPreviewStore(clock=lambda: now)
    prepared = _publish(store, "session-a")

    record = store.consume_current(prepared.token, "session-a")

    assert record is not None
    assert record.request_session == "session-a"
    assert record.revision == 0
    assert store.consume_current(prepared.token, "session-a") is None


def test_preview_store_reads_clock_inside_consume_lock_before_atomic_pop() -> None:
    initial = datetime(2026, 7, 15, tzinfo=UTC)
    current = [initial]
    store = LocalPreviewStore(
        ttl=timedelta(seconds=1), clock=lambda: current[0]
    )
    prepared = _publish(store, "session-a")
    tracked = _TrackedLock()
    store._lock = tracked
    consumed: list[object] = []

    def consume() -> None:
        consumed.append(store.consume_current(prepared.token, "session-a"))

    with tracked:
        thread = threading.Thread(target=consume)
        thread.start()
        assert tracked.waiting.wait(timeout=2)
        current[0] = initial + timedelta(seconds=2)
    thread.join(timeout=2)

    assert not thread.is_alive()
    assert consumed == [None]


def test_preview_store_rejects_expired_cross_session_and_tampered_tokens() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    current = [now]
    store = LocalPreviewStore(
        ttl=timedelta(seconds=1), max_entries=2, clock=lambda: current[0]
    )
    cross_session = _publish(store, "session-a", "cross-session")
    tampered = _publish(store, "session-b", "tampered")

    assert store.consume_current(cross_session.token, "session-b") is None
    assert store.consume_current(tampered.token + "0", "session-b") is None
    current[0] = now + timedelta(seconds=2)
    assert store.consume_current(cross_session.token, "session-a") is None
    assert store.consume_current(tampered.token, "session-b") is None


def test_preview_store_is_bounded_and_issues_only_opaque_redacted_presentations() -> None:
    store = LocalPreviewStore(max_entries=2)
    first = _publish(store, "session-a", "first")
    second = _publish(store, "session-b", "second")
    third = _publish(store, "session-c", "ModuleNotFoundError")

    assert store.consume_current(first.token, "session-a") is None
    assert store.consume_current(second.token, "session-b") is not None
    assert store.consume_current(third.token, "session-c") is not None
    assert "ModuleNotFoundError" in third.redacted_display
    assert third.audit_display
    assert "PreviewBundle" not in repr(third)
    assert "ApprovedRedactedInput" not in repr(third)
    assert "approval_signature" not in repr(third)


def test_preview_store_invalidation_removes_every_session_token() -> None:
    store = LocalPreviewStore()
    first = _publish(store, "session-a", "first")
    second = _publish(store, "session-b", "second")

    assert store.invalidate_and_increment("session-a") == 1
    assert store.consume_current(first.token, "session-a") is None
    assert store.consume_current(second.token, "session-b") is not None


def test_preview_presentation_never_discloses_server_paths_or_strict_objects() -> None:
    preview = _preview(
        r"token=secret-value C:\Users\student\private.py"  # PHASE7_SYNTHETIC_SECRET
    )
    preview = preview.model_copy(
        update={
            "redacted": preview.redacted.model_copy(
                update={
                    "redacted_screenshot_path": "case_private/redacted.png",
                    "redacted_screenshot_sha256": "a" * 64,
                }
            )
        }
    )
    store = LocalPreviewStore()
    presentation = store.publish_if_current("session-a", 0, preview)

    assert presentation is not None
    exposed = repr(presentation)
    assert "secret-value" not in exposed
    assert "C:\\Users" not in exposed
    assert "case_private/redacted.png" not in exposed
    assert "PreviewBundle" not in exposed
    assert "ApprovedRedactedInput" not in exposed
    assert "approval_signature" not in exposed


def _install_project_read_guard(
    monkeypatch: pytest.MonkeyPatch, *, project_root: Path
) -> list[Path]:
    """Audit project reads and fail immediately on fixture or test inputs."""

    trusted_root = project_root.resolve()
    audit: list[Path] = []
    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes
    original_open = builtins.open

    def checked(value: object) -> None:
        if isinstance(value, int) or not isinstance(value, (str, bytes, Path)):
            return
        try:
            path = Path(value).resolve()
            relative = path.relative_to(trusted_root)
        except (OSError, TypeError, ValueError):
            return
        if relative.parts and relative.parts[0].casefold() in {"fixtures", "tests"}:
            raise AssertionError("forbidden project read")
        audit.append(path)

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        checked(path)
        return original_read_text(path, *args, **kwargs)

    def guarded_read_bytes(path: Path) -> bytes:
        checked(path)
        return original_read_bytes(path)

    def guarded_open(file: object, *args: object, **kwargs: object) -> Any:
        checked(file)
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(builtins, "open", guarded_open)
    return audit


def _evidence_run_paths(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("run_*") if path.is_dir())


def test_project_read_guard_blocks_fixture_and_test_reads_but_allows_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = Path.cwd()
    snapshot = project_root / "knowledge" / "snapshots" / "local-rule" / "manifest.json"
    fixture = project_root / "fixtures" / "replay" / "index.json"
    prebuilt_outcome = (
        project_root
        / "fixtures"
        / "replay"
        / "module-not-found"
        / "outcome.json"
    )
    test_source = Path(__file__).resolve()

    audit = _install_project_read_guard(monkeypatch, project_root=project_root)

    for forbidden in (fixture, prebuilt_outcome, test_source):
        with pytest.raises(AssertionError, match="^forbidden project read$"):
            forbidden.read_bytes()
        with (
            pytest.raises(AssertionError, match="^forbidden project read$"),
            builtins.open(forbidden, "rb") as handle,
        ):
            handle.read(1)
    assert snapshot.read_bytes()
    with builtins.open(snapshot, "rb") as handle:
        assert handle.read(1) == b"{"
    assert snapshot.resolve() in audit


def _approved_local_input():
    return approve_preview(
        redact_input(
            InputEnvelope(
                case_id=new_case_id(),
                error_text="ModuleNotFoundError: No module named 'fictional_pkg'",
                environment={"python": "3.13.5"},
            )
        ),
        _KEY,
    )


def _source_run_manifest(
    runtime_root: Path, case_id: str, source_run_id: str
) -> dict[str, object]:
    manifest = json.loads(
        (
            runtime_root
            / "evidence"
            / case_id
            / source_run_id
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(manifest, dict)
    return manifest


def test_local_rule_live_service_creates_verified_fresh_live_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as approval_patch:
        approval_patch.setattr(serve_module.secrets, "token_bytes", lambda _size: _KEY)
        service = serve_module._local_service(runtime_root=tmp_path / "runtime")

    first = service.diagnose_and_compose(_approved_local_input())
    second = service.diagnose_and_compose(_approved_local_input())

    assert first.mode is ResultMode.LIVE and first.fixture_id is None
    assert first.status is ResultStatus.COMPLETED
    assert first.identity is not None and second.identity is not None
    assert first.identity.case_id != second.identity.case_id
    assert first.identity.source_run_id != second.identity.source_run_id
    assert first.result_id != second.result_id
    source_manifest = _source_run_manifest(
        tmp_path / "runtime", first.identity.case_id, first.identity.source_run_id
    )
    assert source_manifest["backend"] == "local-rule-v1"
    assert source_manifest["knowledge_version"] == "local-rule-v1"
    assert source_manifest["knowledge_build_id"] == load_local_rule_snapshot(
        Path.cwd()
    ).knowledge_build_id


def test_nonmatching_local_request_publishes_no_outcome_or_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / "runtime"
    with monkeypatch.context() as approval_patch:
        approval_patch.setattr(serve_module.secrets, "token_bytes", lambda _size: _KEY)
        service = serve_module._local_service(runtime_root=runtime)
    approved = approve_preview(
        redact_input(
            InputEnvelope(
                case_id=new_case_id(),
                error_text="ValueError: invalid fictional value",
                environment={"python": "3.13.5"},
            )
        ),
        _KEY,
    )

    evidence_root = runtime / "evidence"
    sanity_run = evidence_root / "case_sanity" / "run_sanity"
    sanity_run.mkdir(parents=True)
    assert _evidence_run_paths(evidence_root) == [sanity_run]
    sanity_run.rmdir()
    sanity_run.parent.rmdir()

    result = service.diagnose_and_compose(approved)

    assert result.status is ResultStatus.FAILED
    assert not list((runtime / "outcomes").glob("*.json"))
    assert not _evidence_run_paths(evidence_root)
    assert not list((runtime / "results").glob("case_*"))


def test_local_live_path_never_constructs_cloud_tts_or_touches_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def poisoned(*_args: object, **_kwargs: object):
        raise AssertionError("network or cloud adapter boundary touched")

    monkeypatch.setattr(serve_module, "DifyTtsAdapter", poisoned, raising=False)
    monkeypatch.setattr(serve_module, "EdgeTtsAdapter", poisoned, raising=False)
    monkeypatch.setattr(httpx, "Client", poisoned)
    monkeypatch.setattr(socket, "create_connection", poisoned)
    project_root = Path.cwd()
    reads = _install_project_read_guard(monkeypatch, project_root=project_root)
    with monkeypatch.context() as approval_patch:
        approval_patch.setattr(serve_module.secrets, "token_bytes", lambda _size: _KEY)
        service = serve_module._local_service(runtime_root=tmp_path / "runtime")
    monkeypatch.setattr(service, "load_replay", poisoned)
    monkeypatch.setattr(service, "_load_fixture_source", poisoned)

    result = service.diagnose_and_compose(_approved_local_input())

    assert result.status is ResultStatus.COMPLETED
    snapshot_root = (project_root / "knowledge" / "snapshots" / "local-rule").resolve()
    snapshot_reads = {path for path in reads if snapshot_root in path.parents}
    assert snapshot_reads == {
        snapshot_root / "manifest.json",
        snapshot_root / "module-not-found.json",
    }
    assert all("fixtures" not in path.parts and "tests" not in path.parts for path in reads)
