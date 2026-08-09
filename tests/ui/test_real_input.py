from __future__ import annotations

import inspect
import secrets
import socket
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from PIL import Image

from debugmate.contracts import new_case_id
from debugmate.privacy.models import InputEnvelope
from debugmate.privacy.ocr import OcrToken
from debugmate.privacy.rapidocr_backend import RapidOcrBackend
from debugmate.privacy.text_redactor import build_preview, redact_input
from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.ui import presentation as presentation_module
from debugmate.ui import serve as serve_module
from debugmate.ui.app import build_app
from debugmate.ui.local_live import LocalPreviewStore


class _SensitiveOcr:
    def recognize(self, _path: Path) -> list[OcrToken]:
        return [
            OcrToken(
                text="student@example.com",
                box=((4, 4), (116, 4), (116, 24), (4, 24)),
                score=0.99,
            )
        ]


def _preview(label: str = "Traceback"):
    return redact_input(InputEnvelope(case_id=new_case_id(), error_text=label))


def _publish(store: LocalPreviewStore, session: str, label: str = "Traceback"):
    revision = store.snapshot_revision(session)
    published = store.publish_if_current(session, revision, _preview(label))
    assert published is not None
    return published


def _idle(mode: ResultMode = ResultMode.LIVE) -> ResultViewState:
    payload: dict[str, object] = {
        "mode": mode,
        "status": ResultStatus.IDLE,
        "availability": ArtifactAvailability(),
    }
    if mode is ResultMode.REPLAY:
        payload.update(
            fixture_id="module-not-found",
            fixture_name="ModuleNotFoundError：缺少虚构依赖包",
        )
    return ResultViewState(**payload)


def _failed() -> ResultViewState:
    return ResultViewState(
        mode=ResultMode.LIVE,
        status=ResultStatus.FAILED,
        availability=ArtifactAvailability(),
        failure=SafeFailure(
            code="source_bundle_invalid",
            failed_stage="source",
            retry_scope="source",
        ),
    )


def _running() -> ResultViewState:
    return ResultViewState(
        mode=ResultMode.LIVE,
        status=ResultStatus.RUNNING,
        current_stage="source",
        availability=ArtifactAvailability(),
    )


def test_phase7_contract_screenshot_audit_hash_binding(tmp_path: Path) -> None:
    source = tmp_path / "terminal.png"
    Image.new("RGB", (120, 40), "white").save(source)
    value = InputEnvelope(
        case_id=new_case_id(),
        error_text="Traceback",
        screenshot_path=str(source),
    )

    preview = build_preview(value, tmp_path / "redacted", _SensitiveOcr())

    assert hasattr(preview, "screenshot_audit"), (
        "PreviewBundle must bind a strict value-free screenshot audit"
    )
    audit = preview.screenshot_audit
    assert audit.provided is True
    assert str(audit.ocr_status) == "completed"
    assert audit.finding_count == 1
    assert sum(audit.counts_by_kind.values()) == 1
    serialized = audit.model_dump_json()
    assert "student@example.com" not in serialized
    assert all(word not in serialized.casefold() for word in ("text", "box", "path"))


def test_phase7_contract_revision_atomic_consume() -> None:
    required = (
        "current_revision",
        "invalidate_and_increment",
        "snapshot_revision",
        "publish_if_current",
        "consume_current",
        "invalidate_current",
    )
    assert all(callable(getattr(LocalPreviewStore, name, None)) for name in required), (
        "LocalPreviewStore must expose the revision-aware server authority API"
    )

    session = "session-a"
    store = LocalPreviewStore()
    assert store.current_revision(session) == 0

    # change -> approve: the old token observes the incremented revision and fails.
    changed = _publish(store, session, "change-then-approve")
    assert store.invalidate_and_increment(session) == 1
    assert store.consume_current(changed.token, session) is None

    # approve -> change: one atomic consume may finish, then no authority remains.
    approved = _publish(store, session, "approve-then-change")
    consumed: list[object] = []
    consume_done = threading.Event()

    def consume_before_change() -> None:
        consumed.append(store.consume_current(approved.token, session))
        consume_done.set()

    approve_thread = threading.Thread(target=consume_before_change)
    approve_thread.start()
    assert consume_done.wait(timeout=2)
    store.invalidate_and_increment(session)
    approve_thread.join(timeout=2)
    assert not approve_thread.is_alive()
    assert len([item for item in consumed if item is not None]) == 1
    assert store.consume_current(approved.token, session) is None

    # slow preview N -> change: heavy work completes after invalidation and cannot publish.
    slow_revision = store.snapshot_revision(session)
    slow_started = threading.Event()
    release_slow = threading.Event()
    slow_result: list[object] = []

    def publish_slow_preview() -> None:
        slow_started.set()
        assert release_slow.wait(timeout=2)
        slow_result.append(
            store.publish_if_current(
                session, slow_revision, _preview("slow-preview-after-change")
            )
        )

    slow_thread = threading.Thread(target=publish_slow_preview)
    slow_thread.start()
    assert slow_started.wait(timeout=2)
    store.invalidate_and_increment(session)
    release_slow.set()
    slow_thread.join(timeout=2)
    assert not slow_thread.is_alive()
    assert slow_result == [None]

    # preview N -> N+1: the new revision publishes and the older response cannot overwrite it.
    revision_n = store.snapshot_revision(session)
    store.invalidate_and_increment(session)
    revision_n_plus_one = store.snapshot_revision(session)
    newest = store.publish_if_current(
        session, revision_n_plus_one, _preview("preview-n-plus-one")
    )
    stale = store.publish_if_current(session, revision_n, _preview("preview-n"))
    assert newest is not None and stale is None

    # duplicate approve: two simultaneous consumers yield exactly one strict record.
    duplicate = _publish(store, session, "duplicate-approve")
    barrier = threading.Barrier(3)
    duplicate_results: list[object] = []

    def consume_duplicate() -> None:
        barrier.wait(timeout=2)
        duplicate_results.append(store.consume_current(duplicate.token, session))

    threads = [threading.Thread(target=consume_duplicate) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait(timeout=2)
    for thread in threads:
        thread.join(timeout=2)
        assert not thread.is_alive()
    assert len([item for item in duplicate_results if item is not None]) == 1
    assert len([item for item in duplicate_results if item is None]) == 1

    # cross-session, tamper and replay invalidation all fail closed.
    copied = _publish(store, session, "cross-session")
    assert store.consume_current(copied.token, "session-b") is None
    assert store.consume_current(copied.token + "tampered", session) is None
    store.invalidate_current(session)
    assert store.consume_current(copied.token, session) is None

    # expiry is evaluated under the consume lock and removes the one-time record.
    initial = datetime(2026, 8, 9, tzinfo=UTC)
    current = [initial]
    expiring = LocalPreviewStore(
        ttl=timedelta(seconds=1), clock=lambda: current[0]
    )
    expired = _publish(expiring, session, "expiry")
    current[0] = initial + timedelta(seconds=2)
    assert expiring.consume_current(expired.token, session) is None

    orders_exercised = {
        "change->approve",
        "approve->change",
        "slow-preview-N->change",
        "preview-N->N+1",
        "duplicate-approve",
        "cross-session",
        "expiry-tamper",
        "replay-invalidation",
    }
    assert len(orders_exercised) == 8


def test_phase7_contract_construction_local_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    poison_calls: list[str] = []

    def poisoned(*_args: object, **_kwargs: object):
        poison_calls.append("external-constructor")
        raise AssertionError("external or noop construction boundary touched")

    for name in ("DifyTtsAdapter", "EdgeTtsAdapter", "_NoopOcr"):
        monkeypatch.setattr(serve_module, name, poisoned, raising=False)
    monkeypatch.setattr(httpx, "Client", poisoned)
    monkeypatch.setattr(socket, "create_connection", poisoned)
    monkeypatch.setattr(
        serve_module,
        "SapiTtsAdapter",
        lambda **_kwargs: serve_module._UnavailableTtsAdapter("sapi"),
    )

    approval_key = secrets.token_bytes(32)
    live_service = serve_module._local_service(
        runtime_root=tmp_path / "live-runtime", approval_key=approval_key
    )
    build_app(live_service, approval_key=approval_key)

    replay_service = serve_module._local_service(
        runtime_root=tmp_path / "replay-runtime", approval_key=secrets.token_bytes(32)
    )
    row, _outcome, source = replay_service._load_fixture_source("module-not-found")
    replay_service._composer(
        source,
        mode=ResultMode.REPLAY,
        fixture_id=str(row["fixture_id"]),
        fixture_name=str(row["display_label"]),
    )

    assert poison_calls == []


def test_phase7_serve_source_has_no_cloud_or_edge_adapter_imports() -> None:
    source = inspect.getsource(serve_module)

    for forbidden in (
        "results.tts.dify",
        "results.tts.edge",
        "DifyTtsAdapter",
        "EdgeTtsAdapter",
        "DebugMateSettings",
        "httpx",
    ):
        assert forbidden not in source


def test_local_dependencies_construct_one_shared_production_ocr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    constructed: list[RapidOcrBackend] = []

    class TrackedRapidOcrBackend(RapidOcrBackend):
        def __init__(self) -> None:
            super().__init__(factory=lambda: None)
            constructed.append(self)

    monkeypatch.setattr(serve_module, "RapidOcrBackend", TrackedRapidOcrBackend)

    dependencies = serve_module._local_dependencies(
        runtime_root=tmp_path / "runtime",
        approval_key=secrets.token_bytes(32),
    )

    provider = dependencies.service._workflow._extraction_provider
    assert len(constructed) == 1
    assert dependencies.ocr_backend is constructed[0]
    assert provider._ocr_backend is dependencies.ocr_backend
    assert provider._redacted_root == dependencies.redacted_root
    assert dependencies.redacted_root.is_absolute()
    assert dependencies.preview_workspace == dependencies.redacted_root


def test_phase7_contract_orthogonal_state() -> None:
    app = build_app(serve_module._local_service(approval_key=secrets.token_bytes(32)))
    config = app.get_config_file()
    component_ids = [
        component.get("props", {}).get("elem_id")
        for component in config["components"]
    ]
    for elem_id in (
        "error-input",
        "screenshot-input",
        "code-input",
        "environment-input",
        "preview-error-text",
        "preview-code",
        "preview-environment",
        "preview-screenshot",
        "preview-audit",
        "preview-validity",
        "ocr-technical-error",
    ):
        assert component_ids.count(elem_id) == 1

    privacy_type = getattr(presentation_module, "PrivacyPreviewState", None)
    render_combined = getattr(presentation_module, "render_combined_state", None)
    assert privacy_type is not None and callable(render_combined)
    assert {item.value for item in privacy_type} == {
        "idle",
        "invalid",
        "preparing",
        "ready",
        "stale",
        "error",
        "approving",
        "approved",
    }

    expected_live = {
        "idle": ("● 等待输入", False, True),
        "invalid": ("⚠ 还缺少主要报错", False, True),
        "preparing": ("▶ 正在本地生成脱敏预览", False, False),
        "ready": ("✓ 脱敏预览已就绪", True, True),
        "stale": ("⚠ 预览已失效", False, True),
        "error": ("✕ 本地 OCR 暂不可用", False, True),
        "approving": ("▶ 正在确认脱敏输入", False, False),
    }
    for privacy_name, (status, confirm_enabled, inputs_enabled) in expected_live.items():
        view = render_combined(
            mode=ResultMode.LIVE,
            privacy=privacy_type(privacy_name),
            result=_idle(),
        )
        assert view.primary_status == status
        assert view.confirm_enabled is confirm_enabled
        assert view.inputs_enabled is inputs_enabled
        assert view.aria_live == status
        repeated = render_combined(
            mode=ResultMode.LIVE,
            privacy=privacy_type(privacy_name),
            result=_idle(),
            previous_aria_live=view.aria_live,
        )
        assert repeated.aria_live is None

    for privacy_name in ("invalid", "ready", "stale", "error"):
        view = render_combined(
            mode=ResultMode.LIVE,
            privacy=privacy_type(privacy_name),
            result=_failed(),
        )
        assert "上次结果" in view.secondary_status
        assert view.primary_status == expected_live[privacy_name][0]

    approved_running = render_combined(
        mode=ResultMode.LIVE,
        privacy=privacy_type("approved"),
        result=_running(),
    )
    assert approved_running.primary_status.startswith("▶ 正在生成结果")
    assert approved_running.secondary_status == "✓ 已确认脱敏输入"

    for privacy_name in {item.value for item in privacy_type}:
        replay = render_combined(
            mode=ResultMode.REPLAY,
            privacy=privacy_type(privacy_name),
            result=_idle(ResultMode.REPLAY),
        )
        assert replay.primary_status.startswith("↺ 离线回放")
        assert replay.confirm_enabled is False
        assert replay.preview_authoritative is False
        assert "回放" in replay.aria_live
        assert "云端" not in repr(replay)
