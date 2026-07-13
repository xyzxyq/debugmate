"""Native Gradio 6 workbench structure for verified DebugMate results."""

from __future__ import annotations

import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path

import gradio as gr

from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.service import CorrectionDraft, ResultApplicationService, ResultServiceError
from debugmate.ui.presentation import ComponentViewModel, render_view_state

WORKBENCH_CSS = "\n".join(
    (
        ":root { --canvas: #f4f7fb; --surface: #ffffff; --ink: #172238; --accent: #2457a7; }",
        "* { box-sizing: border-box; }",
        ".gradio-container { max-width: 1440px !important; margin: 0 auto; }",
        ".gradio-container { background: var(--canvas); }",
        ".status-bar { position: sticky; top: 0; z-index: 2; background: var(--surface); }",
        ".status-bar { border-bottom: 1px solid #ccd6e5; }",
        ".workbench-grid { display: grid; grid-template-columns: 3fr 4fr 5fr; gap: 14px; }",
        ".workbench-grid { align-items: start; }",
        ".region { min-width: 0; background: var(--surface); border: 1px solid #ccd6e5; }",
        ".region { border-radius: 10px; padding: 12px; }",
        ".metadata { font-family: Cascadia Mono, Consolas, monospace; font-size: 12px; }",
        ".metadata { overflow-wrap: anywhere; }",
        ".report-panel { max-height: 440px; overflow: auto; }",
        ":focus-visible { outline: 2px solid var(--accent) !important; outline-offset: 2px; }",
        "@media (max-width: 1199px) { .workbench-grid { grid-template-columns: 5fr 7fr; } }",
        "@media (max-width: 1199px) { .results-region { grid-column: 1 / -1; } }",
        "@media (max-width: 899px) { .workbench-grid { grid-template-columns: 1fr; } }",
        "@media (max-width: 899px) { .results-region { grid-column: auto; } }",
        "@media (max-width: 899px) { .report-panel { max-height: none; } }",
        "@media (max-width: 639px) { .gradio-container { padding: 8px !important; } }",
    )
)

_FIELD_LABELS = (
    "异常类型",
    "关键回溯行",
    "包/模块",
    "版本",
    "设备",
    "路径",
)
_CASE_ID = "case_"
_RUN_ID = "run_"
_RESULT_ID = "result_"


@dataclass(frozen=True, slots=True)
class CallbackPayload:
    """Strict UI state plus server-owned component outputs, never input paths."""

    state: ResultViewState
    view: ComponentViewModel
    report_markdown: str | None
    card_path: str | None
    audio_path: str | None
    download_path: str | None


class UiCallbacks:
    """Thin adapter that resolves every displayed member through the service."""

    def __init__(self, service: ResultApplicationService, *, cache_root: Path) -> None:
        self._service = service
        self._cache_root = Path(cache_root)
        if not self._cache_root.is_absolute():
            raise ValueError("UI cache root must be absolute")
        self._cache_root.mkdir(parents=True, exist_ok=True)
        if not self._cache_root.is_dir() or self._cache_root.is_symlink():
            raise ValueError("UI cache root is unavailable")

    @staticmethod
    def _failure(state: ResultViewState, code: str) -> ResultViewState:
        safe_code = (
            code
            if code in {"download_invalid", "result_bundle_invalid"}
            else "result_bundle_invalid"
        )
        return ResultViewState(
            mode=state.mode,
            status=ResultStatus.FAILED,
            fixture_id=state.fixture_id,
            fixture_name=state.fixture_name,
            availability=ArtifactAvailability(),
            failure=SafeFailure(code=safe_code, failed_stage="download", retry_scope="download"),
        )

    @staticmethod
    def _strict_id(value: object, prefix: str) -> bool:
        return (
            isinstance(value, str)
            and value.startswith(prefix)
            and len(value) == len(prefix) + 32
            and all(character in "0123456789abcdef" for character in value[len(prefix) :])
        )

    def _cache_download(self, download) -> str:
        filename = download.filename
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).name != filename
            or any(marker in filename for marker in ("/", "\\", ":", "\x00"))
        ):
            raise ResultServiceError("download_invalid")
        payload = download.read_bytes()
        target = self._cache_root / f"{secrets.token_hex(16)}-{filename}"
        with target.open("xb") as handle:
            handle.write(payload)
        return str(target)

    def _member(self, state: ResultViewState, member_id: str):
        if state.identity is None or state.result_id is None:
            raise ResultServiceError("download_invalid")
        return self._service.resolve_download(
            state.identity.case_id, state.result_id, member_id
        )

    def _render(self, state: ResultViewState) -> CallbackPayload:
        if state.status not in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}:
            return CallbackPayload(
                state=state,
                view=render_view_state(state),
                report_markdown=None,
                card_path=None,
                audio_path=None,
                download_path=None,
            )
        created: list[Path] = []
        try:
            report = self._member(state, "report").read_bytes().decode("utf-8")
            card_path = None
            if state.availability.card:
                card_path = self._cache_download(self._member(state, "card"))
                created.append(Path(card_path))
            audio_path = None
            if state.availability.audio:
                audio_path = self._cache_download(self._member(state, "audio"))
                created.append(Path(audio_path))
            download_path = self._cache_download(self._member(state, "bundle"))
            created.append(Path(download_path))
            return CallbackPayload(
                state=state,
                view=render_view_state(state),
                report_markdown=report,
                card_path=card_path,
                audio_path=audio_path,
                download_path=download_path,
            )
        except (ResultServiceError, UnicodeError, OSError, ValueError):
            for path in created:
                path.unlink(missing_ok=True)
            failed = self._failure(state, "download_invalid")
            return CallbackPayload(
                state=failed,
                view=render_view_state(failed),
                report_markdown=None,
                card_path=None,
                audio_path=None,
                download_path=None,
            )

    def load_replay(self, fixture_id: object) -> CallbackPayload:
        if (
            not isinstance(fixture_id, str)
            or not fixture_id
            or "/" in fixture_id
            or "\\" in fixture_id
        ):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))
        try:
            return self._render(self._service.load_replay(fixture_id))
        except Exception:
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def diagnose(self, approved_payload: object) -> CallbackPayload:
        try:
            return self._render(self._service.diagnose_and_compose(approved_payload))
        except (ResultServiceError, TypeError, ValueError):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def refresh(self, case_id: object, result_id: object) -> CallbackPayload:
        if not self._strict_id(case_id, _CASE_ID) or not self._strict_id(result_id, _RESULT_ID):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))
        try:
            return self._render(self._service.restore_result(case_id, result_id))
        except Exception:
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def retry(self, case_id: object, result_id: object) -> CallbackPayload:
        if not self._strict_id(case_id, _CASE_ID) or not self._strict_id(result_id, _RESULT_ID):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))
        try:
            return self._render(self._service.retry_stage(case_id, result_id))
        except Exception:
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))

    def correct(
        self, previous_run_id: object, draft: CorrectionDraft | str, *, confirmed: object
    ) -> CallbackPayload:
        if not self._strict_id(previous_run_id, _RUN_ID) or not isinstance(confirmed, bool):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))
        try:
            return self._render(
                self._service.correct_and_compose(previous_run_id, draft, confirmed)
            )
        except (ResultServiceError, TypeError, ValueError):
            return self._render(self._failure(_idle_view(), "result_bundle_invalid"))


def _idle_view() -> ResultViewState:
    return ResultViewState(
        mode=ResultMode.LIVE,
        status=ResultStatus.IDLE,
        availability=ArtifactAvailability(),
    )


def _status_text(view: ComponentViewModel) -> str:
    rows = [f"### {view.status_badge}", view.mode_badge]
    if view.result_metadata:
        rows.append(view.result_metadata)
    if view.fallback_badge:
        rows.append(view.fallback_badge)
    if view.running_copy:
        rows.append(view.running_copy)
    if view.safe_failure_copy:
        rows.extend((view.safe_failure_copy, f"安全错误码：{view.failure_code}"))
    return "\n\n".join(rows)


def _component_updates(payload: CallbackPayload) -> tuple[object, ...]:
    """Convert one already verified callback payload into atomic native updates."""

    view = payload.view
    failure = ""
    if view.failure_detail_labels:
        failure = "\n\n".join(
            (
                "#### 运行详情",
                *view.failure_detail_labels,
                view.safe_failure_copy or "",
            )
        )
    return (
        _status_text(view),
        view.result_metadata,
        failure,
        gr.update(value=payload.report_markdown or "尚未生成诊断结果"),
        gr.update(value=payload.card_path, visible=payload.card_path is not None),
        gr.update(value=payload.audio_path, visible=payload.audio_path is not None),
        gr.update(
            value=payload.download_path,
            label=view.download_label or "下载结果包",
            visible=payload.download_path is not None,
            interactive=payload.download_path is not None,
        ),
        gr.update(interactive=view.actions_enabled),
        payload.state,
    )


def build_app(service: ResultApplicationService) -> gr.Blocks:
    """Build the compact workbench without an upload, path, or shell boundary."""

    with gr.Blocks(title="DebugMate 诊断工作台", analytics_enabled=False) as app:
        callbacks = UiCallbacks(
            service,
            cache_root=Path(tempfile.gettempdir()) / "debugmate-ui-cache",
        )
        current_state = gr.State(_idle_view())
        approved_payload = gr.State(value=None)
        with gr.Group(elem_classes="status-bar"):
            gr.Markdown("# DebugMate 诊断工作台")
            status = gr.Markdown("● 等待诊断", elem_id="diagnostic-status")
            result_metadata = gr.Markdown("", elem_classes="metadata")
        with gr.Group(elem_classes="workbench-grid"):
            with gr.Column(elem_classes="region"):
                gr.Markdown("## 输入与抽取")
                gr.Textbox(
                    label="脱敏后的输入",
                    interactive=False,
                    lines=5,
                    placeholder="已审批的脱敏输入将在此显示。",
                )
                replay = gr.Dropdown(
                    choices=[("ModuleNotFoundError：缺少虚构依赖包", "module-not-found")],
                    label="固定回放案例",
                    value=None,
                )
                replay_button = gr.Button("加载回放案例", variant="secondary")
                fields = [
                    gr.Textbox(label=label, interactive=True, value="") for label in _FIELD_LABELS
                ]
                pending = gr.Markdown("请先修改至少一个抽取字段。")
                correction_button = gr.Button("确认修改并重新诊断", interactive=False)
                with gr.Accordion("确认创建新运行", open=False):
                    gr.Markdown("确认后将创建新的运行和结果；当前证据与结果不会被覆盖。")
                    gr.Button("创建新运行", variant="primary", interactive=False)
                    gr.Button("返回检查")
                gr.Markdown("页面仅展示已验证的脱敏输入与结果。")

            with gr.Column(elem_classes="region"):
                gr.Markdown("## 诊断与证据")
                gr.Markdown("类别：等待诊断\n\n置信度：暂无")
                gr.Dataframe(
                    headers=["事实 ID", "观察或结论", "证据 ID", "来源", "支持关系"],
                    datatype=["str", "str", "str", "str", "str"],
                    interactive=False,
                    label="事实与证据",
                )
                with gr.Accordion("命令说明（仅供查看）", open=False):
                    gr.Markdown("诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。")
                failure = gr.Markdown("", elem_id="failure-details")

            with gr.Column(elem_classes=["region", "results-region"]):
                gr.Markdown("## 三模态结果")
                with gr.Tabs():
                    with gr.Tab("文字报告"):
                        report = gr.Markdown("尚未生成诊断结果", elem_classes="report-panel")
                    with gr.Tab("诊断卡"):
                        card = gr.Image(
                            label="诊断卡",
                            type="filepath",
                            interactive=False,
                            sources=None,
                            buttons=[],
                        )
                    with gr.Tab("语音复盘"):
                        audio = gr.Audio(
                            label="语音复盘",
                            type="filepath",
                            interactive=False,
                            sources=None,
                            recording=False,
                            buttons=[],
                        )
                        gr.Markdown("复盘稿会与语音一并经过验证后显示。")
                    with gr.Tab("引用与下载"):
                        gr.Dataframe(
                            headers=["证据 ID", "标题", "官方来源", "版本范围"],
                            datatype=["str", "str", "str", "str"],
                            interactive=False,
                            label="引用",
                        )
                        gr.File(label="已验证单个产物", interactive=False, visible=False)
                        download = gr.DownloadButton("下载结果包", visible=False, interactive=False)
        start_button = gr.Button("开始诊断", variant="primary", interactive=False)
        gr.Markdown("诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。")

        def load_replay(fixture_id: str | None):
            return _component_updates(callbacks.load_replay(fixture_id))

        replay_button.click(
            load_replay,
            inputs=[replay],
            outputs=[
                status,
                result_metadata,
                failure,
                report,
                card,
                audio,
                download,
                correction_button,
                current_state,
            ],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
        )
        # The only live boundary is an application-owned approved payload State;
        # no component supplies a DiagnosisRunOutcome, path, command or shell.
        start_button.click(
            lambda approved: _component_updates(callbacks.diagnose(approved)),
            inputs=[approved_payload],
            outputs=[
                status,
                result_metadata,
                failure,
                report,
                card,
                audio,
                download,
                correction_button,
                current_state,
            ],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
        )
        del fields, pending
    # Gradio 6 moved CSS from the constructor to ``launch``.  Retain it on
    # the app for structural inspection; ``serve`` supplies the same string
    # to launch without adding external assets or JavaScript.
    app.css = WORKBENCH_CSS
    return app.queue(default_concurrency_limit=1)
