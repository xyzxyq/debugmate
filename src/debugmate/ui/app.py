"""Native Gradio 6 workbench structure for verified DebugMate results."""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field

import gradio as gr
from fastapi import HTTPException
from fastapi.responses import Response

from debugmate.diagnosis.extraction import FieldId
from debugmate.hashing import sha256_bytes
from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.service import (
    CorrectionDraft,
    ResultApplicationService,
    ResultServiceError,
    ServiceStageEvent,
)
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
_FIELD_IDS = tuple(FieldId)
_EMPTY_FIELD_VALUES = ("", "", "", "", "", "")
_CASE_ID = "case_"
_RUN_ID = "run_"
_RESULT_ID = "result_"
_CONTENT_PREFIX = "/debugmate-content/"


@dataclass(frozen=True, slots=True)
class UiContent:
    """In-memory verified bytes issued to a native component through a token URL."""

    payload: bytes = field(repr=False)
    filename: str
    mime_type: str
    attachment: bool
    sha256: str


class _UiContentStore:
    """Bounded server-owned content registry with no caller-visible server path."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._values: dict[str, UiContent] = {}

    @staticmethod
    def _token_from_url(value: object) -> str:
        if not isinstance(value, str) or not value.startswith(_CONTENT_PREFIX):
            raise ResultServiceError("download_invalid")
        token = value.removeprefix(_CONTENT_PREFIX)
        if len(token) != 32 or any(character not in "0123456789abcdef" for character in token):
            raise ResultServiceError("download_invalid")
        return token

    def issue(self, download, *, attachment: bool) -> str:
        filename = download.filename
        mime_type = download.mime_type
        if (
            not isinstance(filename, str)
            or not filename
            or "/" in filename
            or "\\" in filename
            or ":" in filename
            or "\x00" in filename
        ):
            raise ResultServiceError("download_invalid")
        payload = download.read_bytes()
        content = UiContent(
            payload=payload,
            filename=filename,
            mime_type=mime_type,
            attachment=attachment,
            sha256=sha256_bytes(payload),
        )
        token = secrets.token_hex(16)
        with self._lock:
            self._values[token] = content
            while len(self._values) > 64:
                self._values.pop(next(iter(self._values)))
        return f"{_CONTENT_PREFIX}{token}"

    def resolve(self, url: object) -> UiContent:
        token = self._token_from_url(url)
        with self._lock:
            content = self._values.get(token)
        if content is None or sha256_bytes(content.payload) != content.sha256:
            raise ResultServiceError("download_invalid")
        return content


@dataclass(frozen=True, slots=True)
class CallbackPayload:
    """Strict UI state plus server-owned component outputs, never input paths."""

    state: ResultViewState
    view: ComponentViewModel
    report_markdown: str | None
    card_url: str | None
    audio_url: str | None
    download_url: str | None
    field_values: tuple[str, str, str, str, str, str]


class UiCallbacks:
    """Thin adapter that resolves every displayed member through the service."""

    def __init__(self, service: ResultApplicationService) -> None:
        self._service = service
        self._content = _UiContentStore()

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

    def resolve_content(self, url: object) -> UiContent:
        """Route-only content handoff; it never accepts or returns a file path."""

        return self._content.resolve(url)

    def _member(self, state: ResultViewState, member_id: str):
        if state.identity is None or state.result_id is None:
            raise ResultServiceError("download_invalid")
        return self._service.resolve_download(
            state.identity.case_id, state.result_id, member_id
        )

    def _correction_fields(
        self, state: ResultViewState
    ) -> tuple[str, str, str, str, str, str]:
        """Read six values only from the verified server-side run record."""

        if state.identity is None or state.status not in {
            ResultStatus.COMPLETED,
            ResultStatus.PARTIAL,
        }:
            return _EMPTY_FIELD_VALUES
        try:
            fields = self._service.correction_fields(state.identity.source_run_id)
            if fields.source_run_id != state.identity.source_run_id:
                raise ResultServiceError("correction_invalid")
            return fields.values
        except (AttributeError, ResultServiceError, TypeError, ValueError):
            return _EMPTY_FIELD_VALUES

    def _render(self, state: ResultViewState) -> CallbackPayload:
        if state.status not in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}:
            return CallbackPayload(
                state=state,
                view=render_view_state(state),
                report_markdown=None,
                card_url=None,
                audio_url=None,
                download_url=None,
                field_values=_EMPTY_FIELD_VALUES,
            )
        try:
            report = self._member(state, "report").read_bytes().decode("utf-8")
            card_url = None
            if state.availability.card:
                card_url = self._content.issue(self._member(state, "card"), attachment=False)
            audio_url = None
            if state.availability.audio:
                audio_url = self._content.issue(self._member(state, "audio"), attachment=False)
            download_url = self._content.issue(self._member(state, "bundle"), attachment=True)
            return CallbackPayload(
                state=state,
                view=render_view_state(state),
                report_markdown=report,
                card_url=card_url,
                audio_url=audio_url,
                download_url=download_url,
                field_values=self._correction_fields(state),
            )
        except (ResultServiceError, UnicodeError, OSError, ValueError):
            failed = self._failure(state, "download_invalid")
            return CallbackPayload(
                state=failed,
                view=render_view_state(failed),
                report_markdown=None,
                card_url=None,
                audio_url=None,
                download_url=None,
                field_values=_EMPTY_FIELD_VALUES,
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

    def diagnose_events(self, approved_payload: object):
        """Yield strict UI payloads as the service completes actual result stages."""

        try:
            for event in self._service.diagnose_and_compose_events(approved_payload):
                if not isinstance(event, ServiceStageEvent):
                    raise ResultServiceError("result_bundle_invalid")
                yield self._render(event.state)
        except (ResultServiceError, TypeError, ValueError):
            yield self._render(self._failure(_idle_view(), "result_bundle_invalid"))

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


def mount_content_endpoint(application, callbacks: UiCallbacks) -> None:
    """Serve a token's re-hashed in-memory bytes; no component path is exposed."""

    @application.get(f"{_CONTENT_PREFIX}{{token}}", include_in_schema=False)
    def content(token: str) -> Response:
        try:
            value = callbacks.resolve_content(f"{_CONTENT_PREFIX}{token}")
        except ResultServiceError:
            raise HTTPException(status_code=404, detail="content unavailable") from None
        headers = {}
        if value.attachment:
            headers["Content-Disposition"] = f'attachment; filename="{value.filename}"'
        return Response(content=value.payload, media_type=value.mime_type, headers=headers)


def _idle_view() -> ResultViewState:
    return ResultViewState(
        mode=ResultMode.LIVE,
        status=ResultStatus.IDLE,
        availability=ArtifactAvailability(),
    )


def correction_draft_from_fields(
    original: object, current: object, previous_run_id: object
) -> tuple[CorrectionDraft | None, str]:
    """Make a local single-field draft; this helper never calls the service."""

    if (
        not isinstance(original, (tuple, list))
        or not isinstance(current, (tuple, list))
        or len(original) != len(_FIELD_IDS)
        or len(current) != len(_FIELD_IDS)
        or not isinstance(previous_run_id, str)
        or not UiCallbacks._strict_id(previous_run_id, _RUN_ID)
        or not all(isinstance(value, str) for value in (*original, *current))
    ):
        return None, "请先修改至少一个抽取字段。"
    changed = [
        (index, before, after)
        for index, (before, after) in enumerate(zip(original, current, strict=True))
        if before != after
    ]
    if not changed:
        return None, "请先修改至少一个抽取字段。"
    count = len(changed)
    summary_lines = [f"有 {count} 项未确认修改。"]
    summary_lines.extend(
        f"{_FIELD_LABELS[index]}：{before} → {after}"
        for index, before, after in changed
    )
    if count != 1:
        summary_lines.append("请一次确认一项修改，避免混合多个字段的证据变更。")
        return None, "\n".join(summary_lines)
    index, _before, replacement = changed[0]
    if not replacement.strip():
        summary_lines.append("修改后的字段不能为空。")
        return None, "\n".join(summary_lines)
    try:
        draft = CorrectionDraft(
            field_id=_FIELD_IDS[index],
            replacement=replacement,
            reason="用户确认的已脱敏字段修正。",
        )
    except (TypeError, ValueError):
        return None, "请先修改至少一个抽取字段。"
    return draft, "\n".join(summary_lines)


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
        gr.update(value=payload.card_url, visible=payload.card_url is not None),
        gr.update(value=payload.audio_url, visible=payload.audio_url is not None),
        gr.update(
            value=payload.download_url,
            label=view.download_label or "下载结果包",
            visible=payload.download_url is not None,
            interactive=payload.download_url is not None,
        ),
        # A correction becomes actionable only after a local, explicit draft
        # exists; terminal state alone must never submit a rerun.
        gr.update(interactive=False),
        payload.state,
    )


def build_app(service: ResultApplicationService) -> gr.Blocks:
    """Build the compact workbench without an upload, path, or shell boundary."""

    with gr.Blocks(title="DebugMate 诊断工作台", analytics_enabled=False) as app:
        callbacks = UiCallbacks(service)
        current_state = gr.State(_idle_view())
        approved_payload = gr.State(value=None)
        correction_original = gr.State(value=_EMPTY_FIELD_VALUES)
        correction_run = gr.State(value=None)
        correction_draft = gr.State(value=None)
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
                pending = gr.Textbox(
                    label="修改草稿",
                    interactive=False,
                    lines=4,
                    value="请先修改至少一个抽取字段。",
                )
                correction_button = gr.Button("确认修改并重新诊断", interactive=False)
                with gr.Accordion("确认创建新运行", open=False) as confirmation_panel:
                    gr.Markdown("确认后将创建新的运行和结果；当前证据与结果不会被覆盖。")
                    confirmation_summary = gr.Textbox(
                        label="待确认修改",
                        interactive=False,
                        lines=5,
                    )
                    create_button = gr.Button("创建新运行", variant="primary", interactive=False)
                    return_button = gr.Button("返回检查")
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

        result_outputs = [
            status,
            result_metadata,
            failure,
            report,
            card,
            audio,
            download,
            correction_button,
            current_state,
            *fields,
            correction_original,
            correction_run,
            correction_draft,
            pending,
            confirmation_summary,
            confirmation_panel,
            create_button,
            replay_button,
            start_button,
        ]

        def apply_payload(payload: CallbackPayload) -> tuple[object, ...]:
            """Reset local correction controls whenever verified result changes."""

            source_run_id = (
                payload.state.identity.source_run_id
                if payload.state.identity is not None
                and payload.state.status in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}
                else None
            )
            values = payload.field_values if source_run_id is not None else _EMPTY_FIELD_VALUES
            return (
                *_component_updates(payload),
                *(gr.update(value=value) for value in values),
                values,
                source_run_id,
                None,
                gr.update(value="请先修改至少一个抽取字段。"),
                gr.update(value=""),
                gr.update(open=False),
                gr.update(interactive=False),
                gr.update(interactive=payload.state.status is not ResultStatus.RUNNING),
                gr.update(interactive=False),
            )

        def load_replay(fixture_id: str | None):
            return apply_payload(callbacks.load_replay(fixture_id))

        def diagnose_stream(approved: object):
            for payload in callbacks.diagnose_events(approved):
                yield apply_payload(payload)

        def update_correction_draft(
            original: object, previous_run_id: object, *values: object
        ) -> tuple[object, ...]:
            draft, summary = correction_draft_from_fields(
                original, values, previous_run_id
            )
            return (
                draft,
                gr.update(value=summary),
                gr.update(interactive=draft is not None),
                gr.update(open=False),
                gr.update(value=""),
                gr.update(interactive=False),
            )

        def open_correction_confirmation(
            draft: object, summary: object
        ) -> tuple[object, ...]:
            if not isinstance(draft, CorrectionDraft) or not isinstance(summary, str):
                return (
                    gr.update(open=False),
                    gr.update(value=""),
                    gr.update(interactive=False),
                )
            return (
                gr.update(open=True),
                gr.update(
                    value=(
                        f"{summary}\n\n"
                        "确认后将创建新的运行和结果；当前证据与结果不会被覆盖。"
                    )
                ),
                gr.update(interactive=True),
            )

        def return_to_check() -> tuple[object, ...]:
            return (
                gr.update(open=False),
                gr.update(value=""),
                gr.update(interactive=False),
            )

        def create_new_run(previous_run_id: object, draft: object) -> tuple[object, ...]:
            if not isinstance(draft, CorrectionDraft):
                return apply_payload(
                    callbacks._render(callbacks._failure(_idle_view(), "result_bundle_invalid"))
                )
            return apply_payload(callbacks.correct(previous_run_id, draft, confirmed=True))

        replay_button.click(
            load_replay,
            inputs=[replay],
            outputs=result_outputs,
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
        )
        # The only live boundary is an application-owned approved payload State;
        # no component supplies a DiagnosisRunOutcome, path, command or shell.
        start_button.click(
            diagnose_stream,
            inputs=[approved_payload],
            outputs=result_outputs,
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
        )
        for field in fields:
            field.input(
                update_correction_draft,
                inputs=[correction_original, correction_run, *fields],
                outputs=[
                    correction_draft,
                    pending,
                    correction_button,
                    confirmation_panel,
                    confirmation_summary,
                    create_button,
                ],
                api_name=False,
                queue=False,
            )
        correction_button.click(
            open_correction_confirmation,
            inputs=[correction_draft, pending],
            outputs=[confirmation_panel, confirmation_summary, create_button],
            api_name=False,
            queue=False,
        )
        return_button.click(
            return_to_check,
            outputs=[confirmation_panel, confirmation_summary, create_button],
            api_name=False,
            queue=False,
        )
        create_button.click(
            create_new_run,
            inputs=[correction_run, correction_draft],
            outputs=result_outputs,
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
        )
    # Gradio 6 moved CSS from the constructor to ``launch``.  Retain it on
    # the app for structural inspection; ``serve`` supplies the same string
    # to launch without adding external assets or JavaScript.
    app.css = WORKBENCH_CSS
    mount_content_endpoint(app.app, callbacks)
    return app.queue(default_concurrency_limit=1)
