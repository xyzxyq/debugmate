"""Pure, filesystem-free mapping from strict result state to component facts."""

from __future__ import annotations

from dataclasses import dataclass

from debugmate.results.contracts import ResultMode, ResultStatus, ResultViewState

PHASE4_STAGES: tuple[str, ...] = (
    "source",
    "presentation",
    "report",
    "card",
    "audio",
    "consistency",
    "publish",
)

_STAGE_LABELS = {
    "source": "验证来源",
    "presentation": "整理诊断",
    "report": "生成报告",
    "card": "绘制诊断卡",
    "audio": "生成语音",
    "consistency": "一致性校验",
    "publish": "发布结果包",
}
_TABS = ("文字报告", "诊断卡", "语音复盘", "引用与下载")
_FAILURE_DETAIL_LABELS = (
    "失败节点",
    "安全错误码",
    "已完成阶段",
    "继承阶段",
    "仍可使用的结果",
    "可重试范围",
    "建议操作",
)
_SAFE_FAILURE_COPY = "此阶段未完成。请按“可重试范围”操作；详细开发日志不会显示在页面中。"
_EMPTY_BODY = (
    "提交已脱敏输入，或从固定案例中选择一个回放案例。"
    "结果会在此显示文字报告、诊断卡和语音复盘。"
)


@dataclass(frozen=True, slots=True)
class ComponentViewModel:
    """All UI visibility/copy facts, derived only from ``ResultViewState``."""

    mode_badge: str
    status_badge: str
    accessible_status: str
    primary_action: str | None
    retry_label: str | None
    actions_enabled: bool
    visible_tabs: tuple[str, ...]
    tabs_enabled: bool
    available_artifacts: tuple[str, ...]
    missing_artifact_copy: str | None
    download_label: str | None
    result_metadata: str
    download_metadata: str
    audio_metadata: str | None
    fallback_badge: str | None
    failure_detail_labels: tuple[str, ...]
    failure_code: str | None
    safe_failure_copy: str | None
    stage_label: str | None
    running_copy: str | None
    empty_heading: str | None
    empty_body: str | None
    evidence_empty: str | None


def _mode_badge(state: ResultViewState) -> str:
    if state.mode is ResultMode.REPLAY:
        return f"↺ 离线回放 · {state.fixture_name}"
    return "● 实时诊断"


def _result_metadata(state: ResultViewState) -> str:
    source = "" if state.identity is None else f"；来源运行：{state.identity.source_run_id}"
    if state.mode is ResultMode.REPLAY:
        return f"离线回放：{state.fixture_name}{source}"
    return "" if not source else f"实时诊断{source}"


def _audio_metadata(state: ResultViewState) -> tuple[str | None, str | None]:
    audio = state.audio
    if audio is None:
        return None, None
    if audio.available:
        reason = "无"
        if audio.fallback_used:
            reason = next(
                (
                    attempt.safe_error_code
                    for attempt in audio.attempts
                    if not attempt.succeeded and attempt.safe_error_code is not None
                ),
                "tts_backend_failed",
            )
        metadata = (
            f"语音后端：{audio.backend}；时长：{audio.duration_ms} ms；"
            f"是否降级：{'是' if audio.fallback_used else '否'}；降级原因：{reason}"
        )
        fallback = f"⚠ 语音已降级 · {audio.backend}" if audio.fallback_used else None
        return metadata, fallback
    reason = audio.failure.code if audio.failure is not None else "tts_failed"
    return f"语音未生成（{reason}）", None


def _available_artifacts(state: ResultViewState) -> tuple[str, ...]:
    return tuple(
        name
        for name in ("report", "card", "recap_text", "audio")
        if getattr(state.availability, name)
    )


def _missing_artifact_copy(state: ResultViewState) -> str | None:
    if state.status is not ResultStatus.PARTIAL or state.failure is None:
        return None
    if state.failure.failed_stage == "card":
        return f"诊断卡未生成（{state.failure.code}）"
    if state.failure.failed_stage == "audio":
        return f"语音未生成（{state.failure.code}）"
    return None


def render_view_state(state: ResultViewState) -> ComponentViewModel:
    """Map one strict state without I/O, service calls, paths, or exceptions."""

    if not isinstance(state, ResultViewState):
        raise TypeError("render_view_state requires ResultViewState")

    mode_badge = _mode_badge(state)
    metadata = _result_metadata(state)
    audio_metadata, fallback_badge = _audio_metadata(state)
    available = _available_artifacts(state)
    common = dict(
        mode_badge=mode_badge,
        visible_tabs=_TABS,
        available_artifacts=available,
        result_metadata=metadata,
        download_metadata=metadata,
        audio_metadata=audio_metadata,
        fallback_badge=fallback_badge,
        missing_artifact_copy=_missing_artifact_copy(state),
    )

    if state.status is ResultStatus.IDLE:
        action = "加载回放案例" if state.mode is ResultMode.REPLAY else "开始诊断"
        return ComponentViewModel(
            **common,
            status_badge="● 等待诊断",
            accessible_status="状态：等待诊断",
            primary_action=action,
            retry_label=None,
            actions_enabled=True,
            tabs_enabled=False,
            download_label=None,
            failure_detail_labels=(),
            failure_code=None,
            safe_failure_copy=None,
            stage_label=None,
            running_copy=None,
            empty_heading="尚未生成诊断结果",
            empty_body=_EMPTY_BODY,
            evidence_empty="暂无可展示证据。诊断完成后将按事实 ID 与证据 ID 交叉列出。",
        )

    if state.status is ResultStatus.RUNNING:
        stage_label = _STAGE_LABELS.get(state.current_stage or "", "准备结果")
        completed = len(state.completed_stages)
        return ComponentViewModel(
            **common,
            status_badge=f"▶ 正在生成结果 · {stage_label}",
            accessible_status=f"状态：正在生成结果，{stage_label}",
            primary_action=None,
            retry_label=None,
            actions_enabled=False,
            tabs_enabled=False,
            download_label=None,
            failure_detail_labels=(),
            failure_code=None,
            safe_failure_copy=None,
            stage_label=stage_label,
            running_copy=f"正在{stage_label}，请勿重复提交。已完成 {completed} 个阶段。",
            empty_heading=None,
            empty_body=None,
            evidence_empty=None,
        )

    if state.status is ResultStatus.COMPLETED:
        return ComponentViewModel(
            **common,
            status_badge="✓ 已完成",
            accessible_status="状态：已完成",
            primary_action="确认修改并重新诊断",
            retry_label=None,
            actions_enabled=True,
            tabs_enabled=True,
            download_label="下载完整证据包",
            failure_detail_labels=(),
            failure_code=None,
            safe_failure_copy=None,
            stage_label=None,
            running_copy=None,
            empty_heading=None,
            empty_body=None,
            evidence_empty=None,
        )

    if state.status is ResultStatus.PARTIAL:
        assert state.failure is not None
        return ComponentViewModel(
            **common,
            status_badge="⚠ 部分完成",
            accessible_status="状态：部分完成",
            primary_action=f"重试：{state.failure.retry_scope}",
            retry_label=f"重试：{state.failure.retry_scope}",
            actions_enabled=True,
            tabs_enabled=True,
            download_label="下载部分结果包",
            failure_detail_labels=_FAILURE_DETAIL_LABELS,
            failure_code=state.failure.code,
            safe_failure_copy=_SAFE_FAILURE_COPY,
            stage_label=None,
            running_copy=None,
            empty_heading=None,
            empty_body=None,
            evidence_empty=None,
        )

    assert state.status is ResultStatus.FAILED
    assert state.failure is not None
    return ComponentViewModel(
        **common,
        status_badge="✕ 失败",
        accessible_status="状态：失败",
        primary_action=f"重试：{state.failure.retry_scope}",
        retry_label=f"重试：{state.failure.retry_scope}",
        actions_enabled=True,
        tabs_enabled=False,
        download_label=None,
        failure_detail_labels=_FAILURE_DETAIL_LABELS,
        failure_code=state.failure.code,
        safe_failure_copy=_SAFE_FAILURE_COPY,
        stage_label=None,
        running_copy=None,
        empty_heading=None,
        empty_body=None,
        evidence_empty=None,
    )
