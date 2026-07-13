"""Native Gradio 6 workbench structure for verified DebugMate results."""

from __future__ import annotations

from typing import Any

import gradio as gr

from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultMode,
    ResultStatus,
    ResultViewState,
)
from debugmate.results.service import ResultApplicationService
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


def _state_updates(state: ResultViewState) -> tuple[Any, ...]:
    """Map only the strict view state; result bytes are resolved by callbacks later."""

    view = render_view_state(state)
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
        gr.update(
            value=view.download_label or "下载结果包",
            visible=view.download_label is not None,
        ),
        gr.update(interactive=view.actions_enabled),
        state,
    )


def build_app(service: ResultApplicationService) -> gr.Blocks:
    """Build the compact workbench without an upload, path, or shell boundary."""

    with gr.Blocks(title="DebugMate 诊断工作台", analytics_enabled=False) as app:
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
                        gr.Markdown("尚未生成诊断结果", elem_classes="report-panel")
                    with gr.Tab("诊断卡"):
                        gr.Image(
                            label="诊断卡",
                            type="filepath",
                            interactive=False,
                            sources=None,
                            buttons=[],
                        )
                    with gr.Tab("语音复盘"):
                        gr.Audio(
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
                        download = gr.DownloadButton(
                            "下载结果包", visible=False, interactive=False
                        )
        start_button = gr.Button("开始诊断", variant="primary", interactive=False)
        gr.Markdown("诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。")

        def load_replay(fixture_id: str | None):
            if not isinstance(fixture_id, str):
                state = _idle_view()
            else:
                state = service.load_replay(fixture_id)
            return _state_updates(state)

        replay_button.click(
            load_replay,
            inputs=[replay],
            outputs=[status, result_metadata, failure, download, correction_button, current_state],
            api_name=False,
            queue=True,
            trigger_mode="once",
            concurrency_limit=1,
            concurrency_id="debugmate-case",
        )
        # The only live boundary is an application-owned approved payload State;
        # no component supplies a DiagnosisRunOutcome, path, command or shell.
        start_button.click(
            lambda approved: _state_updates(service.diagnose_and_compose(approved)),
            inputs=[approved_payload],
            outputs=[status, result_metadata, failure, download, correction_button, current_state],
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
