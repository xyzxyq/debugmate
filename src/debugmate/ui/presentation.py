"""Pure, filesystem-free mapping from strict result state to component facts."""

from __future__ import annotations

from dataclasses import dataclass

from debugmate.contracts import DiagnosisRecord
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
_CATEGORY_LABELS = {
    "dependency_environment": "依赖与环境问题",
    "path_permission": "路径与权限问题",
    "python_runtime": "Python 运行时问题",
    "tensor_shape_dtype": "张量形状或数据类型问题",
    "cuda_memory": "CUDA 显存问题",
    "model_loading": "模型加载问题",
    "unknown": "暂未确定类别",
}
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
_SAFE_FAILURE_COPY_BY_CODE = {
    "replay_bundle_invalid": "回放案例校验失败（replay_bundle_invalid）。请选择其他固定案例。",
    "source_bundle_invalid": "来源证据未通过校验（source_bundle_invalid），未生成结果。",
}
_SAFE_STAGE_LABELS = {
    **_STAGE_LABELS,
    "audio": "生成语音",
    "card": "绘制诊断卡",
    "correction": "字段修正",
    "download": "下载验证",
    "identity": "身份校验",
    "input": "已审批输入",
    "replay": "固定回放案例",
    "result": "结果生成",
    "source": "验证来源",
    "store": "结果存储",
    "tts": "语音复盘",
    "workflow": "诊断工作流",
}
_ARTIFACT_LABELS = {
    "report": "文字报告",
    "card": "诊断卡",
    "recap_text": "复盘稿",
    "audio": "语音复盘",
}
_RETRY_COPY = {
    "audio": ("语音复盘", "仅重试语音复盘生成。"),
    "card": ("诊断卡", "仅重试诊断卡生成。"),
    "correction": ("字段修正", "检查已确认的字段修正后重试。"),
    "download": ("下载验证", "重新验证结果包后重试下载。"),
    "input": ("已审批输入", "重新提交已审批的脱敏输入。"),
    "replay": ("固定回放案例", "请选择其他固定案例。"),
    "result": ("结果生成", "重新生成结果后重试。"),
    "source": ("来源证据", "重新验证来源证据后重试。"),
    "store": ("结果存储", "重新验证已保存结果后重试。"),
    "tts": ("语音复盘", "仅重试语音复盘生成。"),
    "workflow": ("诊断工作流", "确认诊断工作流配置后重试。"),
}
_EMPTY_BODY = (
    "提交已脱敏输入，或从固定案例中选择一个回放案例。结果会在此显示文字报告、诊断卡和语音复盘。"
)


@dataclass(frozen=True, slots=True)
class ComponentViewModel:
    """All UI visibility/copy facts, derived only from ``ResultViewState``."""

    mode_badge: str
    state_tone: str
    status_badge: str
    accessible_status: str
    overview_heading: str
    overview_body: str
    secondary_disclosure_visible: bool
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
    failure_details: tuple[tuple[str, str], ...]
    failure_code: str | None
    safe_failure_copy: str | None
    stage_label: str | None
    running_copy: str | None
    empty_heading: str | None
    empty_body: str | None
    evidence_empty: str | None


@dataclass(frozen=True, slots=True)
class VerifiedDiagnosisPresentation:
    """Student-facing facts derived only from one strictly validated diagnosis."""

    category: str
    confidence: str
    root_cause: str | None
    next_action: str | None
    next_action_kind: str | None


def render_verified_diagnosis(diagnosis: DiagnosisRecord) -> VerifiedDiagnosisPresentation:
    """Select the strongest cause and first safe action without inventing advice."""

    if not isinstance(diagnosis, DiagnosisRecord):
        raise TypeError("render_verified_diagnosis requires DiagnosisRecord")

    strongest = max(
        diagnosis.root_cause_candidates,
        key=lambda candidate: candidate.confidence,
        default=None,
    )
    if diagnosis.checks:
        action = diagnosis.checks[0]
        action_kind = "检查"
    elif diagnosis.fixes:
        action = diagnosis.fixes[0]
        action_kind = "修复"
    else:
        action = None
        action_kind = None
    return VerifiedDiagnosisPresentation(
        category=_CATEGORY_LABELS[str(diagnosis.category)],
        confidence=f"{diagnosis.confidence:.2f}",
        root_cause=None if strongest is None else strongest.cause,
        next_action=None if action is None else action.command,
        next_action_kind=action_kind,
    )


def _mode_badge(state: ResultViewState) -> str:
    if state.mode is ResultMode.REPLAY:
        return f"↺ 离线回放 · {state.fixture_name}"
    return "● 实时诊断"


def _result_metadata(state: ResultViewState) -> str:
    source = "" if state.identity is None else f"；来源运行：{state.identity.source_run_id}"
    if state.mode is ResultMode.REPLAY:
        return f"离线回放：{state.fixture_name}{source}"
    return "" if not source else f"实时诊断{source}；fixture_id=null；fixture_name=null"


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


def _safe_stage_list(stages: tuple[str, ...]) -> str:
    labels = tuple(_SAFE_STAGE_LABELS[stage] for stage in stages if stage in _SAFE_STAGE_LABELS)
    return "、".join(labels) if labels else "无"


def _safe_artifact_list(available: tuple[str, ...]) -> str:
    labels = tuple(_ARTIFACT_LABELS[name] for name in available if name in _ARTIFACT_LABELS)
    return "、".join(labels) if labels else "无"


def _failure_details(
    state: ResultViewState, available: tuple[str, ...]
) -> tuple[tuple[str, str], ...]:
    assert state.failure is not None
    failure = state.failure
    retry_label, recommendation = _retry_copy(failure.retry_scope)
    return (
        ("失败节点", _SAFE_STAGE_LABELS.get(failure.failed_stage, "安全处理")),
        ("安全错误码", failure.code),
        ("已完成阶段", _safe_stage_list(state.completed_stages)),
        ("继承阶段", _safe_stage_list(state.inherited_stages)),
        ("仍可使用的结果", _safe_artifact_list(available)),
        ("可重试范围", retry_label),
        ("建议操作", recommendation),
    )


def _retry_copy(scope: str) -> tuple[str, str]:
    return _RETRY_COPY.get(scope, ("安全重试", "请按安全重试范围操作。"))


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
            state_tone="neutral",
            status_badge="● 等待诊断",
            accessible_status="状态：等待诊断",
            overview_heading="两步开始诊断",
            overview_body=(
                "1. 生成脱敏预览，确认隐私信息已处理。\n\n"
                "2. 确认并开始诊断，结果会显示在下方。"
            ),
            secondary_disclosure_visible=False,
            primary_action=action,
            retry_label=None,
            actions_enabled=True,
            tabs_enabled=False,
            download_label=None,
            failure_detail_labels=(),
            failure_details=(),
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
            state_tone="blue",
            status_badge=f"▶ 正在生成结果 · {stage_label}",
            accessible_status=f"状态：正在生成结果，{stage_label}",
            overview_heading=f"▶ 正在生成结果 · {stage_label}",
            overview_body=f"正在{stage_label}，请勿重复提交。已完成 {completed} 个阶段。",
            secondary_disclosure_visible=False,
            primary_action=None,
            retry_label=None,
            actions_enabled=False,
            tabs_enabled=False,
            download_label=None,
            failure_detail_labels=(),
            failure_details=(),
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
            state_tone="green",
            status_badge="✓ 已完成",
            accessible_status="状态：已完成",
            overview_heading="✓ 诊断完成",
            overview_body="先查看原因与下一步，再按需展开完整证据和技术详情。",
            secondary_disclosure_visible=True,
            primary_action="确认修改并重新诊断",
            retry_label=None,
            actions_enabled=True,
            tabs_enabled=True,
            download_label="下载完整证据包",
            failure_detail_labels=(),
            failure_details=(),
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
            state_tone="amber",
            status_badge="⚠ 部分完成",
            accessible_status="状态：部分完成",
            overview_heading="⚠ 部分结果可用",
            overview_body="已完成的结果仍可查看；请根据恢复说明只重试失败阶段。",
            secondary_disclosure_visible=True,
            primary_action=f"重试：{_retry_copy(state.failure.retry_scope)[0]}",
            retry_label=f"重试：{_retry_copy(state.failure.retry_scope)[0]}",
            actions_enabled=True,
            tabs_enabled=True,
            download_label="下载部分结果包",
            failure_detail_labels=_FAILURE_DETAIL_LABELS,
            failure_details=_failure_details(state, available),
            failure_code=state.failure.code,
            safe_failure_copy=_SAFE_FAILURE_COPY_BY_CODE.get(
                state.failure.code, _SAFE_FAILURE_COPY
            ),
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
        state_tone="red",
        status_badge="✕ 诊断失败",
        accessible_status="状态：诊断失败",
        overview_heading="✕ 本次诊断未生成可信结果",
        overview_body="请查看恢复说明与安全错误码后重新开始。",
        secondary_disclosure_visible=True,
        primary_action=f"重试：{_retry_copy(state.failure.retry_scope)[0]}",
        retry_label=f"重试：{_retry_copy(state.failure.retry_scope)[0]}",
        actions_enabled=True,
        tabs_enabled=False,
        download_label=None,
        failure_detail_labels=_FAILURE_DETAIL_LABELS,
        failure_details=_failure_details(state, available),
        failure_code=state.failure.code,
        safe_failure_copy=_SAFE_FAILURE_COPY_BY_CODE.get(state.failure.code, _SAFE_FAILURE_COPY),
        stage_label=None,
        running_copy=None,
        empty_heading=None,
        empty_body=None,
        evidence_empty=None,
    )
