from __future__ import annotations

from pathlib import Path

import pytest

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.contracts import DiagnosisRecord
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
from debugmate.ui import presentation as presentation_module
from debugmate.ui.presentation import (
    PHASE4_STAGES,
    render_verified_diagnosis,
    render_view_state,
)

_ROOT = Path(__file__).resolve().parents[2]

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
        "execution_backend": ExecutionBackend.LOCAL_FALLBACK,
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
    if payload["mode"] is ResultMode.REPLAY and "execution_backend" not in changes:
        payload["execution_backend"] = ExecutionBackend.REPLAY
    return ResultViewState(**payload)


def test_idle_completed_partial_and_failed_have_exact_safe_visibility() -> None:
    idle = render_view_state(_state(ResultStatus.IDLE))
    assert idle.state_tone == "neutral"
    assert idle.overview_heading == "两步开始诊断"
    assert "1. 生成脱敏预览" in idle.overview_body
    assert "2. 确认并开始诊断" in idle.overview_body
    assert idle.secondary_disclosure_visible is False
    assert idle.status_badge == "● 等待诊断"
    assert idle.primary_action == "开始诊断"
    assert idle.empty_heading == "尚未生成诊断结果"
    assert idle.download_label is None
    assert idle.visible_tabs == ("文字报告", "诊断卡", "语音复盘", "引用与下载")
    assert idle.tabs_enabled is False

    completed = render_view_state(_state(ResultStatus.COMPLETED))
    assert completed.state_tone == "green"
    assert completed.secondary_disclosure_visible is True
    assert completed.status_badge == "✓ 已完成"
    assert completed.visible_tabs == ("文字报告", "诊断卡", "语音复盘", "引用与下载")
    assert completed.download_label == "下载完整证据包"
    assert completed.failure_detail_labels == ()

    partial = render_view_state(_state(ResultStatus.PARTIAL))
    assert partial.state_tone == "amber"
    assert partial.secondary_disclosure_visible is True
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
    assert failed.state_tone == "red"
    assert failed.secondary_disclosure_visible is True
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
    assert view.state_tone == "blue"
    assert view.overview_heading == view.status_badge
    assert view.secondary_disclosure_visible is False
    assert view.status_badge == f"▶ 正在生成结果 · {view.stage_label}"
    assert view.running_copy == f"正在{view.stage_label}，请勿重复提交。已完成 {index} 个阶段。"
    assert view.actions_enabled is False
    assert "%" not in view.running_copy


def test_verified_diagnosis_selects_highest_confidence_cause_and_first_safe_action() -> None:
    diagnosis = DiagnosisRecord.model_validate_json(
        (_ROOT / "fixtures/cases/module_not_found/diagnosis.json").read_bytes(), strict=True
    )

    presentation = render_verified_diagnosis(diagnosis)

    expected_cause = max(
        diagnosis.root_cause_candidates,
        key=lambda candidate: candidate.confidence,
    ).cause
    first_action = (diagnosis.checks + diagnosis.fixes)[0]
    assert presentation.category == "依赖与环境问题"
    assert presentation.confidence == f"{diagnosis.confidence:.2f}"
    assert presentation.root_cause == expected_cause
    assert presentation.next_action == first_action.command
    assert presentation.next_action_kind == "检查"


def test_verified_diagnosis_empty_candidates_and_actions_are_explicit_without_guessing() -> None:
    diagnosis = DiagnosisRecord.model_validate_json(
        (_ROOT / "fixtures/cases/module_not_found/diagnosis.json").read_bytes(), strict=True
    ).model_copy(
        update={
            "root_cause_candidates": [],
            "checks": [],
            "fixes": [],
        }
    )

    presentation = render_verified_diagnosis(diagnosis)

    assert presentation.root_cause is None
    assert presentation.next_action is None
    assert presentation.next_action_kind is None
    assert "ModuleNotFoundError" not in repr(presentation)


def test_verified_diagnosis_fails_closed_for_unvalidated_input() -> None:
    with pytest.raises(TypeError, match="DiagnosisRecord"):
        render_verified_diagnosis({"category": "dependency_environment"})  # type: ignore[arg-type]


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
    assert view.mode_badge == "↺ 固定回放 · ModuleNotFoundError：缺少虚构依赖包"
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


_PRIVACY_EXPECTATIONS = {
    "idle": ("● 等待输入", False, True, True, False),
    "invalid": ("⚠ 还缺少主要报错", False, False, False, False),
    "preparing": ("▶ 正在本地生成脱敏预览", False, False, False, False),
    "ready": ("✓ 脱敏预览已就绪", True, True, True, False),
    "stale": ("⚠ 预览已失效", False, True, False, False),
    "error": ("✕ 本地 OCR 暂不可用", False, True, False, False),
    "approving": ("▶ 正在确认脱敏输入", False, False, True, False),
    "approved": ("● 等待诊断", False, False, True, False),
}


@pytest.mark.parametrize(
    ("privacy_name", "expected"),
    tuple(_PRIVACY_EXPECTATIONS.items()),
)
def test_privacy_result_mode_combinations_are_exhaustive_and_deduplicate_aria(
    privacy_name: str,
    expected: tuple[str, bool, bool, bool, bool],
) -> None:
    """A wrong precedence branch, action permission or repeated announcement must fail."""

    privacy_type = getattr(presentation_module, "PrivacyPreviewState", None)
    render_combined = getattr(presentation_module, "render_combined_state", None)
    assert privacy_type is not None and callable(render_combined)
    privacy = privacy_type(privacy_name)
    status, confirm, preview_action, preview_visible, result_visible = expected

    idle = render_combined(
        mode=ResultMode.LIVE,
        privacy=privacy,
        result=_state(ResultStatus.IDLE),
    )
    assert idle.primary_status == status
    assert idle.confirm_enabled is confirm
    assert idle.preview_enabled is preview_action
    assert idle.preview_visible is preview_visible
    assert idle.result_visible is result_visible
    assert idle.aria_live == status
    assert render_combined(
        mode=ResultMode.LIVE,
        privacy=privacy,
        result=_state(ResultStatus.IDLE),
        previous_aria_live=idle.aria_live,
    ).aria_live is None

    previous = render_combined(
        mode=ResultMode.LIVE,
        privacy=privacy,
        result=_state(ResultStatus.FAILED),
    )
    assert previous.result_visible is True
    if privacy_name == "approved":
        assert previous.primary_status == "✕ 诊断失败"
        assert previous.secondary_status == "✓ 已确认脱敏输入"
    else:
        assert previous.primary_status == status
        assert previous.secondary_status == "上次结果：诊断失败"

    running = render_combined(
        mode=ResultMode.LIVE,
        privacy=privacy,
        result=_state(ResultStatus.RUNNING),
    )
    if privacy_name == "approved":
        assert running.primary_status == "▶ 正在生成结果 · 验证来源"
        assert running.secondary_status == "✓ 已确认脱敏输入"
        assert running.result_visible is True
    else:
        assert running.primary_status == status
        assert running.secondary_status == "本机预处理"
        assert running.result_visible is False

    replay_result = _state(
        ResultStatus.IDLE,
        mode=ResultMode.REPLAY,
        fixture_id="module-not-found",
        fixture_name="ModuleNotFoundError：缺少虚构依赖包",
    )
    replay = render_combined(
        mode=ResultMode.REPLAY,
        privacy=privacy,
        result=replay_result,
    )
    assert replay.primary_status == "↺ 固定回放 · ModuleNotFoundError：缺少虚构依赖包"
    assert replay.secondary_status == "本地固定案例"
    assert replay.confirm_enabled is False
    assert replay.preview_authoritative is False
    assert "已确认脱敏输入" not in repr(replay)
    assert "云端" not in repr(replay)


def test_approved_running_result_outranks_privacy_without_flattening_axes() -> None:
    privacy_type = getattr(presentation_module, "PrivacyPreviewState", None)
    render_combined = getattr(presentation_module, "render_combined_state", None)
    assert privacy_type is not None and callable(render_combined)

    running = render_combined(
        mode=ResultMode.LIVE,
        privacy=privacy_type("approved"),
        result=_state(ResultStatus.RUNNING),
    )

    assert running.primary_status == "▶ 正在生成结果 · 验证来源"
    assert running.secondary_status == "✓ 已确认脱敏输入"
    assert running.inputs_enabled is False
    assert running.preview_enabled is False
    assert running.confirm_enabled is False
    assert running.preview_visible is True
    assert running.result_visible is True
    assert running.aria_live == "▶ 正在生成结果 · 验证来源"


def test_privacy_state_rejects_undeclared_raw_or_path_values() -> None:
    privacy_type = getattr(presentation_module, "PrivacyPreviewState", None)
    assert privacy_type is not None
    assert {item.value for item in privacy_type} == set(_PRIVACY_EXPECTATIONS)
    with pytest.raises(ValueError):
        privacy_type("raw=C:\\Users\\student")  # PHASE7_SYNTHETIC_SECRET
