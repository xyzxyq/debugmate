from __future__ import annotations

import pytest

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
from debugmate.ui.presentation import PHASE4_STAGES, render_view_state

IDENTITY = ArtifactIdentity(
    case_id="case_" + "1" * 32,
    source_run_id="run_" + "2" * 32,
    diagnosis_sha256="3" * 64,
    schema_version="1.1.0",
    generation_version="gen_" + "4" * 32,
)


def _audio(*, fallback: bool = False) -> AudioResult:
    attempts = (
        AudioAttempt(
            backend="dify",
            rate_profile="normal",
            succeeded=False,
            safe_error_code="tts_backend_failed",
        ),
        AudioAttempt(
            backend="edge_tts",
            rate_profile="faster",
            succeeded=True,
            duration_ms=40_000,
            sha256="7" * 64,
        ),
    )
    return AudioResult(
        identity=IDENTITY,
        available=True,
        backend="edge_tts",
        fallback_used=fallback,
        attempts=attempts[-1:] if not fallback else attempts,
        duration_ms=40_000,
        sha256="7" * 64,
    )


def _state(status: ResultStatus, **changes: object) -> ResultViewState:
    payload: dict[str, object] = {
        "mode": ResultMode.LIVE,
        "status": status,
        "availability": ArtifactAvailability(),
    }
    if status is ResultStatus.COMPLETED:
        payload.update(
            identity=IDENTITY,
            result_id="result_" + "5" * 32,
            availability=ArtifactAvailability(report=True, card=True, recap_text=True, audio=True),
            audio=_audio(),
        )
    elif status is ResultStatus.PARTIAL:
        failure = SafeFailure(code="png_layout_failed", failed_stage="card", retry_scope="card")
        payload.update(
            identity=IDENTITY,
            result_id="result_" + "5" * 32,
            availability=ArtifactAvailability(report=True, card=False, recap_text=True, audio=True),
            failure=failure,
            audio=_audio(),
        )
    elif status is ResultStatus.FAILED:
        payload.update(
            failure=SafeFailure(
                code="source_bundle_invalid", failed_stage="source", retry_scope="source"
            )
        )
    elif status is ResultStatus.RUNNING:
        payload.update(current_stage=PHASE4_STAGES[0])
    payload.update(changes)
    return ResultViewState(**payload)


def test_idle_completed_partial_and_failed_have_exact_safe_visibility() -> None:
    idle = render_view_state(_state(ResultStatus.IDLE))
    assert idle.status_badge == "● 等待诊断"
    assert idle.primary_action == "开始诊断"
    assert idle.empty_heading == "尚未生成诊断结果"
    assert idle.download_label is None
    assert idle.visible_tabs == ("文字报告", "诊断卡", "语音复盘", "引用与下载")
    assert idle.tabs_enabled is False

    completed = render_view_state(_state(ResultStatus.COMPLETED))
    assert completed.status_badge == "✓ 已完成"
    assert completed.visible_tabs == ("文字报告", "诊断卡", "语音复盘", "引用与下载")
    assert completed.download_label == "下载完整证据包"
    assert completed.failure_detail_labels == ()

    partial = render_view_state(_state(ResultStatus.PARTIAL))
    assert partial.status_badge == "⚠ 部分完成"
    assert partial.visible_tabs == ("文字报告", "诊断卡", "语音复盘", "引用与下载")
    assert partial.available_artifacts == ("report", "recap_text", "audio")
    assert partial.missing_artifact_copy == "诊断卡未生成（png_layout_failed）"
    assert partial.download_label == "下载部分结果包"
    assert partial.failure_detail_labels == (
        "失败节点",
        "安全错误码",
        "已完成阶段",
        "继承阶段",
        "仍可使用的结果",
        "可重试范围",
        "建议操作",
    )

    failed = render_view_state(_state(ResultStatus.FAILED))
    assert failed.status_badge == "✕ 诊断失败"
    assert failed.tabs_enabled is False
    assert failed.download_label is None
    assert failed.failure_code == "source_bundle_invalid"
    assert "C:" not in repr(failed)


@pytest.mark.parametrize("stage", PHASE4_STAGES)
def test_running_stages_are_ordered_indeterminate_and_disable_duplicate_actions(stage: str) -> None:
    index = PHASE4_STAGES.index(stage)
    state = _state(
        ResultStatus.RUNNING,
        current_stage=stage,
        completed_stages=PHASE4_STAGES[:index],
    )
    view = render_view_state(state)
    assert view.status_badge == f"▶ 正在生成结果 · {view.stage_label}"
    assert view.running_copy == f"正在{view.stage_label}，请勿重复提交。已完成 {index} 个阶段。"
    assert view.actions_enabled is False
    assert "%" not in view.running_copy


@pytest.mark.parametrize(
    "status",
    [
        ResultStatus.IDLE,
        ResultStatus.RUNNING,
        ResultStatus.COMPLETED,
        ResultStatus.PARTIAL,
        ResultStatus.FAILED,
    ],
)
def test_replay_is_orthogonal_and_never_uses_live_success_wording(status: ResultStatus) -> None:
    state = _state(
        status,
        mode=ResultMode.REPLAY,
        fixture_id="module-not-found",
        fixture_name="ModuleNotFoundError：缺少虚构依赖包",
    )
    view = render_view_state(state)
    assert view.mode_badge == "↺ 离线回放 · ModuleNotFoundError：缺少虚构依赖包"
    assert "回放" in view.result_metadata
    assert "云端运行成功" not in repr(view)


def test_fallback_is_an_audio_fact_and_not_an_outcome_substitute() -> None:
    state = _state(ResultStatus.COMPLETED, audio=_audio(fallback=True))
    view = render_view_state(state)
    assert view.status_badge == "✓ 已完成"
    assert view.fallback_badge == "⚠ 语音已降级 · edge_tts"
    assert (
        view.audio_metadata
        == "语音后端：edge_tts；时长：40000 ms；是否降级：是；降级原因：tts_backend_failed"
    )


def test_failure_details_have_only_safe_derived_values_and_exact_invalid_copy() -> None:
    source = render_view_state(
        _state(
            ResultStatus.FAILED,
            completed_stages=("source",),
            inherited_stages=("presentation",),
        )
    )

    assert source.safe_failure_copy == "来源证据未通过校验（source_bundle_invalid），未生成结果。"
    assert source.failure_details == (
        ("失败节点", "验证来源"),
        ("安全错误码", "source_bundle_invalid"),
        ("已完成阶段", "验证来源"),
        ("继承阶段", "整理诊断"),
        ("仍可使用的结果", "无"),
        ("可重试范围", "来源证据"),
        ("建议操作", "重新验证来源证据后重试。"),
    )

    replay = render_view_state(
        _state(
            ResultStatus.FAILED,
            mode=ResultMode.REPLAY,
            fixture_id="module-not-found",
            fixture_name="ModuleNotFoundError：缺少虚构依赖包",
            failure=SafeFailure(
                code="replay_bundle_invalid", failed_stage="replay", retry_scope="replay"
            ),
        )
    )
    assert replay.safe_failure_copy == (
        "回放案例校验失败（replay_bundle_invalid）。请选择其他固定案例。"
    )
    assert replay.failure_details[-2:] == (
        ("可重试范围", "固定回放案例"),
        ("建议操作", "请选择其他固定案例。"),
    )
    assert "C:" not in repr(source.failure_details + replay.failure_details)
