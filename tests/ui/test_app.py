from __future__ import annotations

import asyncio
import hashlib
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
from debugmate.ui.app import CallbackPayload, build_app
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
        availability = ArtifactAvailability(
            report=True, card=True, recap_text=True, audio=False
        )
    else:
        failure = SafeFailure(
            code="png_layout_failed", failed_stage="card", retry_scope="card"
        )
        audio = completed.audio
        availability = ArtifactAvailability(
            report=True, card=False, recap_text=True, audio=True
        )
    return completed.model_copy(
        update={
            "status": ResultStatus.PARTIAL,
            "result_id": "result_" + "7" * 32,
            "availability": availability,
            "failure": failure,
            "audio": audio,
        }
    )


def test_build_app_has_native_three_region_workbench_and_no_unsafe_components() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    rendered = repr(config)

    workbench_grids = [
        component
        for component in config["components"]
        if component.get("props", {}).get("elem_id") == "workbench-grid"
    ]
    assert len(workbench_grids) == 1

    for text in (
        "DebugMate 诊断工作台",
        "输入与抽取",
        "诊断与证据",
        "三模态结果",
        "文字报告",
        "诊断卡",
        "语音复盘",
        "引用与下载",
        "确认修改并重新诊断",
        "诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。",
        "页面仅展示已验证的脱敏输入与结果。",
    ):
        assert text in rendered
    assert "html" not in {component["type"] for component in config["components"]}
    assert "subprocess" not in Path("src/debugmate/ui/app.py").read_text(encoding="utf-8")
    assert "gr.HTML" not in Path("src/debugmate/ui/app.py").read_text(encoding="utf-8")
    assert "#workbench-grid:has(> #workbench-grid)" in app.css
    assert "minmax(280px, 3fr) minmax(360px, 4fr) minmax(440px, 5fr)" in app.css
    assert "gap: 16px;" in app.css
    assert "@media (max-width: 1199px)" in app.css
    assert "@media (max-width: 899px)" in app.css
    assert "overflow-x: hidden" not in app.css


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

    assert "生成本地脱敏预览" in buttons
    assert "确认预览并开始本地诊断" in buttons
    assert buttons["确认预览并开始本地诊断"]["props"]["interactive"] is False
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
    assert download["props"]["visible"] is True
    assert download["props"]["interactive"] is False


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


def test_live_callback_sends_postprocessed_dataframe_cells_and_one_metadata_row() -> None:
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
    assert fact_value["headers"] == [
        "事实 ID",
        "观察或结论",
        "证据 ID",
        "来源",
        "支持关系",
    ]
    assert any("ModuleNotFoundError" in cell for row in fact_value["data"] for cell in row)
    assert any(cell.startswith("evidence_") for row in fact_value["data"] for cell in row)
    assert citation_value["headers"] == ["证据 ID", "标题", "官方来源", "版本范围"]
    assert any(
        cell == "https://docs.python.org/3/library/exceptions.html"
        for row in citation_value["data"]
        for cell in row
    )
    assert any(cell == "ModuleNotFoundError" for row in citation_value["data"] for cell in row)


def test_gap_01_archive_preserves_the_original_browser_failure() -> None:
    assert _GAP_01_ARCHIVE.is_file()
    assert hashlib.sha256(_GAP_01_ARCHIVE.read_bytes()).hexdigest() == _GAP_01_ARCHIVE_SHA256


def test_replay_default_is_allowlisted_and_only_enables_its_control() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    replay = next(
        component
        for component in config["components"]
        if component["type"] == "dropdown" and component["props"].get("label") == "固定回放案例"
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
    assert all(frame[22]["interactive"] is False for frame in frames[:-1])
    assert frames[-1][8].status is ResultStatus.COMPLETED


def test_replay_generator_process_api_keeps_all_media_on_verified_loopback_urls() -> None:
    """The actual Gradio stream must not rebuild media as a local server path."""

    app = build_app(_Service())

    async def stream_replay() -> list[dict[str, object]]:
        state = SessionState(app)
        response = await app.process_api(
            0,
            ["module-not-found"],
            state=state,
            session_hash="replay-process-api",
            simple_format=True,
        )
        frames = [response]
        while response["is_generating"]:
            response = await app.process_api(
                0,
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
    for index in (4, 5, 6):
        value = terminal["data"][index]["value"]
        assert value["path"] == value["url"]
        parsed = urlsplit(value["url"])
        assert (parsed.scheme, parsed.hostname) == ("http", "127.0.0.1")
        assert parsed.path.startswith("/debugmate-content/")
        assert "X:\\" not in value["path"]
        assert "phase-1-foundation-platform-gate" not in value["path"]
        assert "/gradio_api/file=" not in value["path"]
        urls.append(value["url"])

    expected = (b"verified-card", b"verified-audio", b"verified-zip")
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
