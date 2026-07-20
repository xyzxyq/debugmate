from __future__ import annotations

import asyncio
import hashlib
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from gradio.state_holder import SessionState

import debugmate.ui.app as app_module
from debugmate.privacy.models import ApprovedRedactedInput
from debugmate.results.contracts import (
    ArtifactAvailability,
    ArtifactIdentity,
    AudioAttempt,
    AudioResult,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.service import ServiceStageEvent
from debugmate.results.verifier import VerifiedDownload
from debugmate.ui import serve as serve_module
from debugmate.ui.app import CallbackPayload, _UiSessionStateStore, build_app
from debugmate.ui.presentation import render_view_state
from debugmate.ui.serve import _local_service

_ROOT = Path(__file__).resolve().parents[2]
_GAP_01_ARCHIVE = _ROOT / "evidence" / "ui" / "phase4" / "archive" / "GAP-01-VQ-01-failing.png"
_GAP_01_ARCHIVE_SHA256 = "12be2e55e45f78ddee0f8c6cdbc9cce4ffdd4c494192d63c2c22c6ef61fd10cc"


def _completed_state() -> ResultViewState:
    identity = ArtifactIdentity(
        case_id="case_" + "1" * 32,
        source_run_id="run_" + "2" * 32,
        diagnosis_sha256="3" * 64,
        schema_version="1.1.0",
        generation_version="gen_" + "4" * 32,
    )
    audio = AudioResult(
        identity=identity,
        available=True,
        backend="dify",
        attempts=(
            AudioAttempt(
                backend="dify",
                rate_profile="normal",
                succeeded=True,
                duration_ms=40_000,
                sha256="5" * 64,
            ),
        ),
        duration_ms=40_000,
        sha256="5" * 64,
    )
    return ResultViewState(
        mode=ResultMode.LIVE,
        status=ResultStatus.COMPLETED,
        identity=identity,
        result_id="result_" + "6" * 32,
        availability=ArtifactAvailability(report=True, card=True, recap_text=True, audio=True),
        audio=audio,
    )


class _Service:
    """Minimal strict façade fake; the app must not need an outcome or path."""

    def load_replay(self, fixture_id: str) -> ResultViewState:
        assert fixture_id == "module-not-found"
        return _completed_state()

    def __init__(self) -> None:
        self.diagnose_calls: list[ApprovedRedactedInput] = []
        self.retry_calls: list[tuple[str, str]] = []

    def diagnose_and_compose_events(self, approved: ApprovedRedactedInput):
        assert isinstance(approved, ApprovedRedactedInput)
        self.diagnose_calls.append(approved)
        yield ServiceStageEvent(
            state=ResultViewState(
                mode=ResultMode.LIVE,
                status=ResultStatus.RUNNING,
                availability=ArtifactAvailability(),
                current_stage="source",
            )
        )
        yield ServiceStageEvent(state=_completed_state())

    def load_replay_events(self, fixture_id: str):
        assert fixture_id == "module-not-found"
        stages = (
            "source",
            "presentation",
            "report",
            "card",
            "audio",
            "consistency",
            "publish",
        )
        for index, stage in enumerate(stages):
            yield ServiceStageEvent(
                state=ResultViewState(
                    mode=ResultMode.REPLAY,
                    status=ResultStatus.RUNNING,
                    fixture_id="module-not-found",
                    fixture_name="ModuleNotFoundError：缺少虚构依赖包",
                    availability=ArtifactAvailability(),
                    current_stage=stage,
                    completed_stages=stages[:index],
                )
            )
        yield ServiceStageEvent(
            state=_completed_state().model_copy(
                update={
                    "mode": ResultMode.REPLAY,
                    "fixture_id": "module-not-found",
                    "fixture_name": "ModuleNotFoundError：缺少虚构依赖包",
                }
            )
        )

    def resolve_download(self, case_id: str, result_id: str, member_id: str) -> VerifiedDownload:
        state = _completed_state()
        assert state.identity is not None and state.result_id is not None
        assert (case_id, result_id) == (state.identity.case_id, state.result_id)
        contents = {
            "diagnosis": (
                (_ROOT / "fixtures/cases/module_not_found/diagnosis.json").read_bytes(),
                "diagnosis.json",
                "application/json",
            ),
            "report": (b"# DebugMate", "report.md", "text/markdown"),
            "card": (b"verified-card", "card.png", "image/png"),
            "recap_text": (
                b"ModuleNotFoundError recap",
                "recap.txt",
                "text/plain",
            ),
            "audio": (b"verified-audio", "recap.mp3", "audio/mpeg"),
            "bundle": (b"verified-zip", "debugmate-result.zip", "application/zip"),
        }
        payload, filename, mime_type = contents[member_id]
        return VerifiedDownload._issue(
            payload=payload,
            member_id=member_id,
            filename=filename,
            mime_type=mime_type,
            identity=state.identity,
        )

    def retry_stage(self, case_id: str, result_id: str) -> ResultViewState:
        self.retry_calls.append((case_id, result_id))
        return _completed_state().model_copy(update={"result_id": "result_" + "8" * 32})


def _partial_state_for_app(failed_stage: str) -> ResultViewState:
    completed = _completed_state()
    assert completed.identity is not None
    if failed_stage == "audio":
        failure = SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="tts")
        audio = AudioResult(
            identity=completed.identity,
            available=False,
            attempts=(
                AudioAttempt(
                    backend="dify",
                    rate_profile="normal",
                    succeeded=False,
                    safe_error_code="tts_failed",
                ),
            ),
            failure=failure,
        )
        availability = ArtifactAvailability(report=True, card=True, recap_text=True, audio=False)
    else:
        failure = SafeFailure(code="png_layout_failed", failed_stage="card", retry_scope="card")
        audio = completed.audio
        availability = ArtifactAvailability(report=True, card=False, recap_text=True, audio=True)
    return completed.model_copy(
        update={
            "status": ResultStatus.PARTIAL,
            "result_id": "result_" + "7" * 32,
            "availability": availability,
            "failure": failure,
            "audio": audio,
        }
    )


def test_build_app_has_student_first_learning_workbench_and_no_unsafe_components() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    rendered = repr(config)

    workbench_grids = [
        component
        for component in config["components"]
        if component.get("props", {}).get("elem_id") == "workbench-grid"
    ]
    assert len(workbench_grids) == 1

    command_bars = [
        component
        for component in config["components"]
        if "command-bar" in component.get("props", {}).get("elem_classes", [])
    ]
    control_rails = [
        component
        for component in config["components"]
        if "control-rail" in component.get("props", {}).get("elem_classes", [])
    ]
    diagnosis_canvases = [
        component
        for component in config["components"]
        if "diagnosis-canvas" in component.get("props", {}).get("elem_classes", [])
    ]
    result_workspaces = [
        component
        for component in config["components"]
        if "result-workspace" in component.get("props", {}).get("elem_classes", [])
    ]
    correction_panels = [
        component
        for component in config["components"]
        if "correction-panel" in component.get("props", {}).get("elem_classes", [])
    ]
    assert len(command_bars) == 1
    assert len(control_rails) == 1
    assert len(diagnosis_canvases) == 1
    assert len(result_workspaces) == 1
    assert len(correction_panels) == 1
    assert correction_panels[0]["type"] == "accordion"
    assert correction_panels[0]["props"]["open"] is False
    assert correction_panels[0]["props"]["visible"] is False
    assert any(
        "section-kicker" in component.get("props", {}).get("elem_classes", [])
        for component in config["components"]
    )

    elem_ids = {
        component.get("props", {}).get("elem_id") for component in config["components"]
    }
    assert {
        "diagnostic-status",
        "accessible-status",
        "result-metadata",
        "workbench-grid",
        "local-preview",
        "local-approve",
        "replay-action",
        "fact-table",
        "diagnostic-commands",
        "failure-details",
        "partial-retry",
        "diagnostic-report",
        "diagnostic-card",
        "diagnostic-audio",
        "audio-metadata",
        "recap-text",
        "citation-table",
        "individual-artifacts",
        "download-metadata",
        "download-result",
        "result-tabs",
        "student-overview",
        "technical-details",
    } <= elem_ids

    for text in (
        "DebugMate 学习诊断助手",
        "1. 生成脱敏预览",
        "2. 确认并开始诊断",
        "查看示例",
        "示例案例",
        "抽取字段与纠错",
        "问题概览",
        "下一步怎么做",
        "技术详情与恢复信息",
        "结果查看",
        "文字报告",
        "诊断卡",
        "语音复盘",
        "引用与下载",
        "确认修改并重新诊断",
        "诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。",
        "页面仅展示已验证的脱敏输入与结果。",
    ):
        assert text in rendered
    html_components = [
        component for component in config["components"] if component["type"] == "html"
    ]
    assert len(html_components) == 1
    assert html_components[0]["props"]["elem_id"] == "accessible-status"
    assert html_components[0]["props"]["html_template"] == (
        '<p role="status" aria-live="polite" aria-atomic="true">${value}</p>'
    )
    assert "subprocess" not in Path("src/debugmate/ui/app.py").read_text(encoding="utf-8")
    source = Path("src/debugmate/ui/app.py").read_text(encoding="utf-8")
    assert source.count("gr.HTML(") == 1
    assert "<script" not in source.lower()
    assert "#workbench-grid:has(> #workbench-grid)" in app.css
    approved_colors = {
        "#f5f7fb",
        "#ffffff",
        "#f8fafc",
        "#edf2f7",
        "#0f172a",
        "#5f6b7a",
        "#d8dee8",
        "#007aff",
        "#e9f2ff",
        "#fff7ed",
        "#ff9f0a",
        "#fff1f2",
        "#ff3b30",
        "#ecfdf3",
        "#34c759",
    }
    for token in (
        "--canvas: #f5f7fb",
        "--surface-1: #ffffff",
        "--surface-2: #f8fafc",
        "--sidebar: #edf2f7",
        "--text: #0f172a",
        "--muted: #5f6b7a",
        "--border: #d8dee8",
        "--primary: #007aff",
        "--primary-soft: #e9f2ff",
        "--warning-surface: #fff7ed",
        "--warning: #ff9f0a",
        "--failure-surface: #fff1f2",
        "--failure: #ff3b30",
        "--success-surface: #ecfdf3",
        "--success: #34c759",
    ):
        assert token in app.css
    css_hex_colors = {
        color.lower() for color in re.findall(r"#[0-9a-fA-F]{3,8}\b", app.css)
    }
    css_function_colors = re.findall(r"\b(?:rgb|rgba)\([^)]*\)", app.css, re.IGNORECASE)
    assert css_hex_colors == approved_colors
    assert css_function_colors == []
    assert "minmax(280px, 0.8fr) minmax(360px, 1fr) minmax(460px, 1.3fr)" in app.css
    assert "gap: 16px;" in app.css
    assert ".command-bar { position: sticky;" in app.css
    assert ".control-rail" in app.css
    assert ".diagnosis-canvas" in app.css
    assert ".result-workspace" in app.css
    assert ".section-kicker" in app.css
    assert ".correction-panel" in app.css
    assert "box-shadow:" in app.css
    assert "backdrop-filter" not in app.css
    assert "tone-neutral" in app.css
    assert "tone-blue" in app.css
    assert "tone-green" in app.css
    assert "tone-amber" in app.css
    assert "tone-red" in app.css
    assert "@media (max-width: 1199px)" in app.css
    assert "@media (max-width: 899px)" in app.css
    assert "@media (max-width: 639px)" in app.css
    assert "overflow-x: hidden" not in app.css

    result_tabs = next(
        component
        for component in config["components"]
        if component.get("props", {}).get("elem_id") == "result-tabs"
    )
    tab_items = [
        component
        for component in config["components"]
        if component["type"] == "tabitem"
        and component["props"].get("label")
        in {"文字报告", "诊断卡", "语音复盘", "引用与下载"}
    ]
    assert result_tabs["type"] == "tabs"
    assert len(tab_items) == 4
    assert all(component["props"]["interactive"] is False for component in tab_items)
    assert "gr.Tabs(interactive=" not in source


def test_production_app_has_no_qa_handler_route_selector_or_capability_surface() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    rendered = repr(config).lower()
    callbacks = tuple(block_fn.fn for block_fn in app.fns.values())
    callback_surfaces = tuple(
        (
            getattr(callback, "__module__", ""),
            getattr(callback, "__qualname__", ""),
        )
        for callback in callbacks
    )
    route_surfaces = tuple(
        (
            getattr(route, "path", ""),
            getattr(route, "name", ""),
            getattr(getattr(route, "endpoint", None), "__module__", ""),
            getattr(getattr(route, "endpoint", None), "__qualname__", ""),
        )
        for route in app.app.routes
    )
    dependency_surfaces = repr(config.get("dependencies", ())).lower()

    assert not any(
        "qa_scenarios" in module or "qa" in name.lower() for module, name in callback_surfaces
    )
    assert not any(
        "qa_scenarios" in module
        or "qa" in name.lower()
        or "qa" in endpoint.lower()
        or "qa" in path.lower()
        for path, name, module, endpoint in route_surfaces
    )
    assert "qa_scenarios" not in dependency_surfaces
    assert "debugmate_qa" not in dependency_surfaces
    assert not any(
        "qa" in str(dependency.get("api_name", "")).lower()
        or "scenario" in str(dependency.get("api_name", "")).lower()
        or "capability" in str(dependency.get("api_name", "")).lower()
        for dependency in config["dependencies"]
    )
    assert "debugmate_qa" not in rendered
    assert "qa scenario" not in rendered
    assert "x-debugmate-qa-capability" not in rendered
    assert not any(
        component["type"] in {"dropdown", "textbox"}
        and "qa" in str(component.get("props", {}).get("label", "")).lower()
        for component in config["components"]
    )


class _Request:
    def __init__(self, session_hash: str) -> None:
        self.session_hash = session_hash
        self.url = "http://127.0.0.1:7860/queue/join"


def _callback(app, name: str):
    return next(
        block_fn.fn for block_fn in app.fns.values() if getattr(block_fn.fn, "__name__", "") == name
    )


def test_server_session_state_registry_isolated_strict_bounded_and_clearable() -> None:
    store = _UiSessionStateStore(max_sessions=2)
    first = _Request("session-registry-a")
    second = _Request("session-registry-b")
    third = _Request("session-registry-c")

    assert store.publish(first, {"status": "completed"}) is False
    assert store.publish(_Request("bad/session"), _completed_state()) is False
    assert store.read(second) is None

    expected = _completed_state()
    first_lease = store.issue_lease(first)
    second_lease = store.issue_lease(second)
    assert isinstance(first_lease, str) and first_lease != second_lease
    source_run_id = expected.identity.source_run_id
    assert store.publish_lease(first_lease + "tampered", expected, source_run_id) is False

    assert store.publish(first, expected) is True
    recovered = store.read(first)
    assert recovered == expected
    assert recovered is not expected
    assert len(store) == 1
    revised = expected.model_copy(update={"result_id": "result_" + "9" * 32})
    assert store.publish_lease(second_lease, revised, source_run_id) is False
    assert store.publish_lease(first_lease, revised, source_run_id) is True
    assert store.read(first) == revised
    assert store.read(second) is None

    assert store.publish(second, expected) is True
    assert store.publish(third, expected) is True
    assert len(store) == 2
    assert store.read(first) is None
    assert store.read(second) == expected
    assert store.read(third) == expected
    assert "/debugmate-content/" not in repr(store._values)
    snapshot = store.audit_snapshot()
    assert len(snapshot) == 2
    assert all(
        set(item) == {"session_sha256_prefix", "status", "source_run_id"}
        and len(item["session_sha256_prefix"] or "") == 12
        for item in snapshot
    )
    assert "session-registry" not in repr(snapshot)

    assert store.clear(second) is True
    assert store.clear(second) is False
    assert store.publish_lease(second_lease, expected, source_run_id) is False
    assert store.clear(third) is True
    assert len(store) == 0


def test_local_live_requires_preview_then_same_session_approval() -> None:
    service = _Service()
    app = build_app(service)
    prepare = _callback(app, "prepare_local_preview")
    approve = _callback(app, "approve_and_diagnose_stream")
    request = _Request("session-a")

    prepared = prepare(request)

    assert len(prepared) == 4
    token, approval_update, redacted_display, audit_display = prepared
    assert isinstance(token, str) and len(token) >= 32
    assert approval_update["interactive"] is True
    assert isinstance(redacted_display, str) and "ModuleNotFoundError" in redacted_display
    assert isinstance(audit_display, str) and audit_display
    assert service.diagnose_calls == []
    assert "PreviewBundle" not in repr(prepared)
    assert "approval_signature" not in repr(prepared)

    frames = list(approve(token, request))
    states = [next(item for item in frame if isinstance(item, ResultViewState)) for frame in frames]
    assert states[0].status is ResultStatus.RUNNING
    assert states[-1].status is ResultStatus.COMPLETED
    assert states[-1].mode is ResultMode.LIVE
    assert states[-1].fixture_id is None
    assert states[-1].fixture_name is None
    assert len(service.diagnose_calls) == 1
    assert frames[-1][1] == (
        f"实时诊断；来源运行：{states[-1].identity.source_run_id}；"
        "fixture_id=null；fixture_name=null"
    )


@pytest.mark.parametrize(
    ("token_transform", "session_hash"),
    [
        (lambda _token: None, "session-a"),
        (lambda token: token + "copied", "session-a"),
        (lambda token: token, "session-b"),
    ],
)
def test_local_live_rejects_missing_tampered_or_cross_session_token_without_diagnosis(
    token_transform, session_hash: str
) -> None:
    service = _Service()
    app = build_app(service)
    prepare = _callback(app, "prepare_local_preview")
    approve = _callback(app, "approve_and_diagnose_stream")
    token = prepare(_Request("session-a"))[0]

    frames = list(approve(token_transform(token), _Request(session_hash)))
    states = [next(item for item in frame if isinstance(item, ResultViewState)) for frame in frames]

    assert len(states) == 1
    assert states[0].status is ResultStatus.FAILED
    assert service.diagnose_calls == []


def test_local_live_token_is_one_time_and_every_preview_has_fresh_identity() -> None:
    service = _Service()
    app = build_app(service)
    prepare = _callback(app, "prepare_local_preview")
    approve = _callback(app, "approve_and_diagnose_stream")
    request = _Request("session-a")
    first_token = prepare(request)[0]
    second_token = prepare(request)[0]

    assert first_token != second_token
    assert list(approve(first_token, request))[-1][8].status is ResultStatus.COMPLETED
    reused = list(approve(first_token, request))

    assert reused[0][8].status is ResultStatus.FAILED
    assert len(service.diagnose_calls) == 1


def test_local_live_config_exposes_two_explicit_controls_and_no_unsafe_live_input() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    buttons = {
        component["props"].get("value"): component
        for component in config["components"]
        if component["type"] == "button"
    }
    source = Path("src/debugmate/ui/app.py").read_text(encoding="utf-8")

    assert "1. 生成脱敏预览" in buttons
    assert "2. 确认并开始诊断" in buttons
    assert buttons["2. 确认并开始诊断"]["props"]["interactive"] is False
    assert any(
        component["type"] == "markdown"
        and component["props"].get("value") == "后端：local-rule-v1（本地规则，无云端调用）"
        for component in config["components"]
    )
    assert "approved_payload = gr.State" not in source
    assert "inputs=[approved_payload]" not in source
    live_callback_source = source[
        source.index("def approve_and_diagnose_stream") : source.index(
            "def update_correction_draft"
        )
    ]
    assert "load_replay" not in live_callback_source
    assert "Dify" not in source
    assert "EdgeTtsAdapter" not in source
    for mojibake in ("鐢熸垚", "纭", "鍚庣", "鏂囧瓧", "寮曠敤", "瀹屾垚"):
        assert mojibake not in source


def test_local_live_events_share_the_bounded_diagnosis_queue_lane() -> None:
    app = build_app(_Service())
    prepare = next(
        block_fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "prepare_local_preview"
    )
    diagnose = next(
        block_fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "approve_and_diagnose_stream"
    )

    assert prepare.queue is True
    assert prepare.concurrency_id == "debugmate-case"
    assert prepare.concurrency_limit == 1
    assert diagnose.queue is True
    assert diagnose.concurrency_id == "debugmate-case"
    assert diagnose.concurrency_limit == 1


def test_local_live_controls_and_terminal_outputs_have_stable_elem_ids() -> None:
    config = build_app(_Service()).get_config_file()
    elem_ids = {component["props"].get("elem_id") for component in config["components"]}

    assert {
        "diagnostic-status",
        "result-metadata",
        "download-metadata",
        "audio-metadata",
        "diagnostic-audio",
        "diagnostic-report",
        "recap-text",
        "citation-table",
        "individual-artifacts",
        "local-preview",
        "local-approve",
        "replay-action",
        "download-result",
    } <= elem_ids
    download = next(
        component
        for component in config["components"]
        if component["props"].get("elem_id") == "download-result"
    )
    assert download["props"]["visible"] is False
    assert download["props"]["interactive"] is False

    correction_fields = [
        component
        for component in config["components"]
        if component["type"] == "textbox"
        and component["props"].get("label")
        in {"异常类型", "关键回溯行", "包/模块", "版本", "设备", "路径"}
    ]
    assert len(correction_fields) == 6
    assert all(component["props"]["interactive"] is False for component in correction_fields)


def test_main_payload_clears_download_surfaces_until_verified_resync() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    metadata = next(
        component
        for component in config["components"]
        if component["props"].get("elem_id") == "download-metadata"
    )
    download = next(
        component
        for component in config["components"]
        if component["props"].get("elem_id") == "download-result"
    )
    callback = _callback(app, "load_replay_stream")

    assert metadata["type"] == "markdown"
    assert metadata["id"] < download["id"]
    frame = list(callback("module-not-found", None))[-1]
    assert frame[6]["value"] is None
    assert frame[6]["visible"] is False
    assert frame[6]["interactive"] is False
    assert frame[34]["value"] == ""


def test_download_surfaces_resync_from_server_session_state_and_fail_closed() -> None:
    app = build_app(_Service())
    block = next(
        block_fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "sync_download_surfaces"
    )

    assert len(block.inputs) == 0
    assert [output.elem_id for output in block.outputs] == [
        "download-metadata",
        "download-result",
    ]
    assert block.queue is True
    assert block.concurrency_id == "debugmate-case"

    request = _Request("download-resync")
    replay = _callback(app, "load_replay_stream")("module-not-found", request)
    next(replay)
    metadata, download = block.fn(request)
    assert metadata["value"] == ""
    assert download["value"] is None
    assert download["visible"] is False
    assert download["interactive"] is False

    list(replay)
    metadata, download = block.fn(request)
    assert _completed_state().identity is not None
    assert _completed_state().identity.source_run_id in metadata["value"]
    assert download["visible"] is True
    assert download["interactive"] is True
    assert download["value"]["url"].startswith("http://127.0.0.1:7860/debugmate-content/")
    response = TestClient(app.app).get(download["value"]["url"])
    assert response.status_code == 200
    assert response.content == b"verified-zip"

    failed_request = _Request("download-resync-failed")
    list(_callback(app, "load_replay_stream")("not-allowlisted", failed_request))
    metadata, download = block.fn(failed_request)
    assert metadata["value"] == ""
    assert download["value"] is None
    assert download["visible"] is False
    assert download["interactive"] is False


def test_correction_chain_preserves_only_strict_run_and_draft_while_downloads_resync() -> None:
    from debugmate.diagnosis.extraction import FieldId
    from debugmate.results.service import CorrectionDraft

    app = build_app(_Service())
    block = next(
        block_fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "create_new_run_stream"
    )
    replay_block = next(
        block_fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "load_replay_stream"
    )
    run_id = _completed_state().identity.source_run_id
    draft = CorrectionDraft(
        field_id=FieldId.PACKAGE,
        replacement="replacement_pkg",
        reason="用户确认更正",
    )

    request = _Request("correction-chain")
    replay_frames = list(replay_block.fn("module-not-found", request))
    lease = replay_frames[-1][-1]
    assert isinstance(lease, str) and len(lease) == 38 and lease.startswith("lease_")
    assert all(character in "0123456789abcdef" for character in lease[6:])
    assert replay_block.outputs[-1].get_block_name() == "state"
    assert not any(
        getattr(block_fn.fn, "__name__", "") == "issue_session_lease"
        for block_fn in app.fns.values()
    )
    assert lease not in repr(app.get_config_file())
    stream = block.fn(run_id, draft, lease, request)
    frame = next(stream)
    stream.close()

    assert frame[8].status is ResultStatus.RUNNING
    assert frame[16] == run_id
    assert frame[17] == draft
    assert frame[6]["value"] is None
    assert frame[6]["visible"] is False
    assert frame[6]["interactive"] is False
    assert frame[34]["value"] == ""
    assert app._debugmate_content_callbacks.session_audit_snapshot() == (
        {
            "session_sha256_prefix": hashlib.sha256(b"correction-chain").hexdigest()[:12],
            "status": "running",
            "source_run_id": None,
        },
    )
    assert not any(
        getattr(block_fn.fn, "__name__", "") in {"begin_new_run", "complete_new_run"}
        for block_fn in app.fns.values()
    )
    block_index = next(index for index, candidate in app.fns.items() if candidate is block)
    resyncs = [
        candidate
        for candidate in app.fns.values()
        if getattr(candidate.fn, "__name__", "") == "sync_download_surfaces"
        and candidate.trigger_after == block_index
    ]
    assert len(resyncs) == 1


def test_native_audio_has_server_derived_metadata_surface() -> None:
    config = build_app(_Service()).get_config_file()
    metadata = next(
        component
        for component in config["components"]
        if component["props"].get("elem_id") == "audio-metadata"
    )
    audio = next(component for component in config["components"] if component["type"] == "audio")

    assert metadata["type"] == "markdown"
    assert metadata["id"] > audio["id"]
    assert audio["props"]["visible"] is False


def test_partial_retry_has_one_initially_disabled_server_labeled_control() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    retry_controls = [
        component
        for component in config["components"]
        if component["props"].get("elem_id") == "partial-retry"
    ]

    assert len(retry_controls) == 1
    assert retry_controls[0]["type"] == "button"
    assert retry_controls[0]["props"]["interactive"] is False
    assert retry_controls[0]["props"]["value"] == "安全重试"
    callbacks = [
        block_fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "retry_verified_partial"
    ]
    assert len(callbacks) == 1
    assert callbacks[0].queue is True
    assert callbacks[0].concurrency_id == "debugmate-case"


@pytest.mark.parametrize("failed_stage", ["audio", "card"])
def test_partial_retry_label_is_derived_from_verified_result_view_state(
    failed_stage: str,
) -> None:
    state = _partial_state_for_app(failed_stage)
    view = render_view_state(state)
    retry_updates = getattr(app_module, "_retry_control_updates", None)

    assert callable(retry_updates)
    update, case_id, result_id = retry_updates(
        CallbackPayload(
            state=state,
            view=view,
            report_markdown="# verified",
            card_url=None,
            audio_url=None,
            download_url=None,
            field_values=("", "", "", "", "", ""),
        )
    )
    assert update["value"] == view.retry_label
    assert update["interactive"] is True
    assert state.identity is not None
    assert (case_id, result_id) == (state.identity.case_id, state.result_id)


@pytest.mark.parametrize(
    "status", [ResultStatus.IDLE, ResultStatus.RUNNING, ResultStatus.COMPLETED]
)
def test_retry_control_is_disabled_outside_verified_partial_terminal_state(
    status: ResultStatus,
) -> None:
    if status is ResultStatus.COMPLETED:
        state = _completed_state()
    elif status is ResultStatus.RUNNING:
        state = ResultViewState(
            mode=ResultMode.LIVE,
            status=status,
            availability=ArtifactAvailability(),
            current_stage="report",
        )
    else:
        state = ResultViewState(
            mode=ResultMode.LIVE,
            status=status,
            availability=ArtifactAvailability(),
        )
    retry_updates = getattr(app_module, "_retry_control_updates", None)

    assert callable(retry_updates)
    update, case_id, result_id = retry_updates(
        CallbackPayload(
            state=state,
            view=render_view_state(state),
            report_markdown=None,
            card_url=None,
            audio_url=None,
            download_url=None,
            field_values=("", "", "", "", "", ""),
        )
    )
    assert update["interactive"] is False
    assert (case_id, result_id) == (None, None)


def test_live_callback_sends_accessible_read_only_tables_and_one_metadata_row() -> None:
    app = build_app(_Service())
    callback = next(
        block_fn.fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "approve_and_diagnose_stream"
    )
    prepare = next(
        block_fn.fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "prepare_local_preview"
    )
    request = _Request("dataframe-session")
    token = prepare(request)[0]

    frame = list(callback(token, request))[-1]

    assert "run_" not in frame[0]
    assert frame[1].count("run_") == 1
    fact_value = frame[28]["value"]
    citation_value = frame[29]["value"]
    assert "| 事实 ID | 观察或结论 | 证据 ID | 来源 | 支持关系 |" in fact_value
    assert "ModuleNotFoundError" in fact_value
    assert "evidence_" in fact_value
    assert "| 证据 ID | 标题 | 官方来源 | 版本范围 |" in citation_value
    assert "https://docs.python.org/3/library/exceptions.html" in citation_value
    assert "ModuleNotFoundError" in citation_value


def test_gap_01_archive_preserves_the_original_browser_failure() -> None:
    assert _GAP_01_ARCHIVE.is_file()
    assert hashlib.sha256(_GAP_01_ARCHIVE.read_bytes()).hexdigest() == _GAP_01_ARCHIVE_SHA256


def test_replay_default_is_allowlisted_and_only_enables_its_control() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    replay = next(
        component
        for component in config["components"]
        if component["type"] == "dropdown" and component["props"].get("label") == "示例案例"
    )
    replay_button = next(
        component
        for component in config["components"]
        if component["type"] == "button" and component["props"].get("value") == "加载回放案例"
    )
    enabled = next(
        block_fn.fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "replay_button_enabled"
    )

    assert replay["props"]["value"] == "module-not-found"
    assert replay["props"]["allow_custom_value"] is False
    assert replay_button["props"]["interactive"] is True
    assert enabled("module-not-found")["interactive"] is True
    assert enabled(None)["interactive"] is False
    assert enabled("not-allowlisted")["interactive"] is False


def test_long_content_replay_and_commands_are_strict_read_only_surfaces() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    replay = next(
        component
        for component in config["components"]
        if component["type"] == "dropdown" and component["props"].get("label") == "示例案例"
    )
    command_table = next(
        component
        for component in config["components"]
        if component["props"].get("elem_id") == "diagnostic-commands"
    )
    enabled = next(
        block_fn.fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "replay_button_enabled"
    )

    assert replay["props"]["choices"] == [
        ("ModuleNotFoundError：缺少虚构依赖包", "module-not-found"),
        ("长报告与长命令：布局韧性", "long-content"),
    ]
    assert replay["props"]["allow_custom_value"] is False
    assert enabled("long-content")["interactive"] is True
    assert enabled("../long-content")["interactive"] is False
    assert enabled('{"fixture_id":"long-content"}')["interactive"] is False
    assert command_table["type"] == "markdown"
    assert command_table["props"]["value"].startswith("### 已验证诊断命令")
    assert "| 步骤 | 命令 | 平台 | 影响 | 预期结果 | 回退说明 |" in command_table["props"]["value"]


def test_completed_payload_commands_are_exactly_derived_from_diagnosis_record() -> None:
    app = build_app(_Service())
    callback = app._debugmate_content_callbacks
    request = _Request("verified-command-rows")

    payload = callback.load_replay("module-not-found", request=request)

    diagnosis = json.loads(
        (_ROOT / "fixtures/cases/module_not_found/diagnosis.json").read_text(encoding="utf-8")
    )
    expected = tuple(
        (
            section,
            item["command"],
            item["platform"],
            item["impact"],
            item["expected_result"],
            item["rollback"],
        )
        for section, key in (("检查", "checks"), ("修复", "fixes"), ("验证", "verification_steps"))
        for item in diagnosis[key]
    )
    assert payload.command_rows == expected


def test_replay_button_callback_streams_running_states_and_disables_repeat_action() -> None:
    app = build_app(_Service())
    callback = next(
        block_fn.fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "load_replay_stream"
    )

    frames = list(callback("module-not-found", None))

    assert [frame[8].current_stage for frame in frames[:-1]] == [
        "source",
        "presentation",
        "report",
        "card",
        "audio",
        "consistency",
        "publish",
    ]
    assert [len(frame[8].completed_stages) for frame in frames[:-1]] == list(range(7))
    assert all(frame[8].mode is ResultMode.REPLAY for frame in frames[:-1])
    assert all(
        all(update["interactive"] is False for update in frame[9:15]) for frame in frames[:-1]
    )
    assert all(frame[22]["interactive"] is False for frame in frames[:-1])
    assert all(
        all(update["interactive"] is False for update in frame[-5:-1])
        for frame in frames[:-1]
    )
    assert frames[-1][8].status is ResultStatus.COMPLETED
    assert all(update["interactive"] is True for update in frames[-1][9:15])
    assert all(update["interactive"] is True for update in frames[-1][-5:-1])


def test_result_tabs_follow_partial_and_failed_view_permissions_atomically() -> None:
    app = build_app(_Service())
    callback = next(
        block_fn.fn
        for block_fn in app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "load_replay_stream"
    )
    callbacks = app._debugmate_content_callbacks
    completed = _completed_state()
    assert completed.audio is not None
    partial = completed.model_copy(
        update={
            "status": ResultStatus.PARTIAL,
            "availability": ArtifactAvailability(
                report=True, card=True, recap_text=True, audio=False
            ),
                "audio": AudioResult(
                    identity=completed.identity,
                    available=False,
                    attempts=(
                        AudioAttempt(
                            backend="dify",
                            rate_profile="normal",
                            succeeded=False,
                            safe_error_code="tts_failed",
                        ),
                    ),
                failure=SafeFailure(
                    code="tts_failed", failed_stage="audio", retry_scope="tts"
                ),
            ),
            "failure": SafeFailure(
                code="tts_failed", failed_stage="audio", retry_scope="tts"
            ),
        }
    )
    callbacks.load_replay_events = lambda _fixture_id, request=None: iter(  # type: ignore[method-assign]
        (callbacks._render(partial),)
    )

    partial_frame = list(callback("module-not-found", None))[-1]
    assert all(update["interactive"] is True for update in partial_frame[-5:-1])
    assert partial_frame[31]["visible"] is True
    assert partial_frame[31]["interactive"] is True

    failed_app = build_app(_Service())
    failed_callback = next(
        block_fn.fn
        for block_fn in failed_app.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "load_replay_stream"
    )
    failed_frame = list(failed_callback("../not-allowlisted", None))[-1]
    assert all(update["interactive"] is False for update in failed_frame[-5:-1])
    assert failed_frame[31]["visible"] is False
    assert failed_frame[31]["interactive"] is False


def test_replay_generator_process_api_keeps_all_media_on_verified_loopback_urls() -> None:
    """The actual Gradio stream must not rebuild media as a local server path."""

    app = build_app(_Service())
    replay_index = next(
        index
        for index, block_fn in app.fns.items()
        if getattr(block_fn.fn, "__name__", "") == "load_replay_stream"
    )

    async def stream_replay() -> list[dict[str, object]]:
        state = SessionState(app)
        response = await app.process_api(
            replay_index,
            ["module-not-found"],
            state=state,
            session_hash="replay-process-api",
            simple_format=True,
        )
        frames = [response]
        while response["is_generating"]:
            response = await app.process_api(
                replay_index,
                [],
                state=state,
                iterator=response["iterator"],
                session_hash="replay-process-api",
                simple_format=True,
            )
            frames.append(response)
        return frames

    frames = asyncio.run(stream_replay())

    first = frames[0]
    assert first["is_generating"] is True
    for index in (4, 5, 6):
        assert first["data"][index]["value"] is None

    terminal = frames[-1]
    assert terminal["is_generating"] is False
    urls = []
    for index in (4, 5):
        value = terminal["data"][index]["value"]
        assert value["path"] == value["url"]
        parsed = urlsplit(value["url"])
        assert (parsed.scheme, parsed.hostname) == ("http", "127.0.0.1")
        assert parsed.path.startswith("/debugmate-content/")
        assert "X:\\" not in value["path"]
        assert "phase-1-foundation-platform-gate" not in value["path"]
        assert "/gradio_api/file=" not in value["path"]
        urls.append(value["url"])

    assert terminal["data"][6]["value"] is None

    expected = (b"verified-card", b"verified-audio")
    client = TestClient(app.app)
    for url, payload in zip(urls, expected, strict=True):
        response = client.get(url)
        assert response.status_code == 200
        assert response.content == payload


def test_local_service_configures_a_real_result_composer_for_replay(tmp_path: Path) -> None:
    service = _local_service(runtime_root=tmp_path / "runtime")

    assert callable(service._composer)


def test_local_composer_uses_the_positional_tts_chain_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[object, ...]] = []

    class StopAfterTtsCall(RuntimeError):
        pass

    class CapturingChain:
        def __init__(self, _adapters) -> None:
            pass

        def synthesize(self, recap, request, candidate_root):
            calls.append((recap, request, candidate_root))
            raise StopAfterTtsCall

    monkeypatch.setattr(serve_module, "TtsFallbackChain", CapturingChain)
    service = serve_module._local_service(runtime_root=tmp_path / "runtime")
    row, _outcome, source = service._load_fixture_source("module-not-found")

    with pytest.raises(StopAfterTtsCall):
        service._composer(
            source,
            mode=ResultMode.REPLAY,
            fixture_id=str(row["fixture_id"]),
            fixture_name=str(row["display_label"]),
        )

    assert len(calls) == 1


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def test_serve_rejects_non_loopback_and_exposes_only_local_config_endpoint(tmp_path: Path) -> None:
    invalid = subprocess.run(
        [
            sys.executable,
            "-m",
            "debugmate.ui.serve",
            "--host",
            "0.0.0.0",
            "--port",
            "7860",
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert invalid.returncode != 0

    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "debugmate.ui.serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        response = None
        while time.monotonic() < deadline:
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/config", timeout=1)
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        assert response is not None and response.status_code == 200
        payload = response.json()
        assert isinstance(payload.get("version"), str)
        assert isinstance(payload.get("components"), list)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    closed_deadline = time.monotonic() + 5
    while time.monotonic() < closed_deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                break
        time.sleep(0.1)
    else:
        pytest.fail("loopback port remained open after child cleanup")
