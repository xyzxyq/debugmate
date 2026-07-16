"""RED contracts for the private Phase 4 truth-state scenario factory."""

from __future__ import annotations

import importlib
import threading
from enum import Enum
from pathlib import Path

import pytest

from debugmate.results.contracts import ResultStatus
from debugmate.ui.serve import _local_service

EXPECTED_SCENARIOS = (
    "vq-02-replay",
    "vq-03-running",
    "vq-06-tts-failed",
    "vq-07-png-failed",
    "vq-08-source-invalid",
    "vq-09-fallback",
)
EXPECTED_STAGES = (
    "source",
    "presentation",
    "report",
    "card",
    "audio",
    "consistency",
    "publish",
)


def _qa():
    return importlib.import_module("debugmate.ui.qa_scenarios")


def test_qa_scenario_registry_is_closed_and_enum_only() -> None:
    qa = _qa()

    assert issubclass(qa.QaScenario, Enum)
    assert tuple(item.value for item in qa.QaScenario) == EXPECTED_SCENARIOS
    assert tuple(qa.QA_STAGE_ORDER) == EXPECTED_STAGES
    assert set(qa.QA_SCENARIOS) == set(qa.QaScenario)
    with pytest.raises((TypeError, ValueError)):
        qa.build_qa_scenario("vq-02-replay")


def test_qa_request_parser_returns_only_a_registered_enum() -> None:
    qa = _qa()

    parsed = qa.parse_qa_request({"scenario": "vq-06-tts-failed"})

    assert parsed is qa.QaScenario.VQ_06_TTS_FAILED
    assert not isinstance(parsed, str)


def test_stage_gate_is_ordered_bounded_and_has_no_percentage() -> None:
    qa = _qa()
    gate = qa.QaStageGate(timeout_seconds=0.01)

    with pytest.raises((RuntimeError, ValueError)):
        gate.arrive("report")
    assert tuple(item.value for item in qa.QaStage) == EXPECTED_STAGES


def test_stage_gate_rejects_wrong_release_duplicates_and_use_after_completion() -> None:
    qa = _qa()
    gate = qa.QaStageGate(timeout_seconds=0.01)

    with pytest.raises((RuntimeError, ValueError)):
        gate.release(qa.QaStage.SOURCE)
    with pytest.raises((RuntimeError, ValueError)):
        gate.release(qa.QaStage.REPORT)


@pytest.fixture(scope="module")
def verified_replay(tmp_path_factory: pytest.TempPathFactory):
    qa = _qa()
    runtime = tmp_path_factory.mktemp("qa-verified-replay")
    baseline = qa.load_verified_qa_baseline(
        _local_service(runtime_root=Path(runtime), replay_local_only=True)
    )
    state = baseline.state
    assert state.status is ResultStatus.COMPLETED
    assert state.identity is not None and state.audio is not None
    assert tuple(attempt.backend for attempt in state.audio.attempts) == ("sapi",)
    assert baseline.source_hashes == (
        (
            "error_text",
            "f16d05ec6b29248d2c61adb1e9263f78e4f7bace1b955014a2d17872cfe4064d",
        ),
    )
    return baseline


def test_truth_state_specs_preserve_replay_partial_failed_and_fallback_semantics(
    verified_replay,
) -> None:
    qa = _qa()
    state = verified_replay.state
    specs = {
        scenario: qa.build_qa_scenario(scenario, baseline=verified_replay)
        for scenario in qa.QaScenario
    }

    replay = specs[qa.QaScenario.VQ_02_REPLAY]
    assert replay.mode == "replay" and replay.status == "completed"
    assert replay.fixture_id and replay.fixture_name
    tts = specs[qa.QaScenario.VQ_06_TTS_FAILED]
    assert (tts.status, tts.failure_code, tts.retry_scope) == (
        "partial",
        "tts_failed",
        "tts",
    )
    assert tts.available == ("report", "card", "recap_text")
    png = specs[qa.QaScenario.VQ_07_PNG_FAILED]
    assert (png.status, png.failure_code, png.retry_scope) == (
        "partial",
        "png_layout_failed",
        "card",
    )
    assert png.available == ("report", "recap_text", "audio")
    failed = specs[qa.QaScenario.VQ_08_SOURCE_INVALID]
    assert failed.status == "failed" and failed.failure_code == "source_bundle_invalid"
    assert failed.available == () and failed.download is False
    fallback = specs[qa.QaScenario.VQ_09_FALLBACK]
    assert fallback.status == "completed" and fallback.fallback_backend in {
        "edge_tts",
        "sapi",
    }
    for spec in specs.values():
        if spec.view_state.identity is not None:
            assert spec.view_state.identity == state.identity
            assert spec.view_state.result_id == state.result_id
    assert replay.fixture_name == state.fixture_name
    assert specs[qa.QaScenario.VQ_07_PNG_FAILED].view_state.audio == state.audio
    assert fallback.view_state.audio is not None
    assert fallback.view_state.audio.identity == state.audio.identity
    assert fallback.view_state.audio.sha256 == state.audio.sha256
    assert fallback.view_state.audio.duration_ms == state.audio.duration_ms
    assert fallback.view_state.audio.attempts[-1] == state.audio.attempts[-1]
    assert replay.source_hashes == verified_replay.source_hashes
    assert replay.category == "dependency_environment"
    assert replay.recap_text == verified_replay.recap_text
    assert failed.source_hashes == () and failed.recap_text is None


def test_stage_gate_rendezvous_blocks_worker_until_ordered_runner_release() -> None:
    qa = _qa()
    gate = qa.QaStageGate(timeout_seconds=1.0)
    completed: list[str] = []
    returned = {stage: threading.Event() for stage in qa.QA_STAGE_ORDER}

    def worker() -> None:
        for stage in qa.QA_STAGE_ORDER:
            gate.arrive(stage)
            completed.append(stage)
            returned[stage].set()

    thread = threading.Thread(target=worker)
    thread.start()
    for index, stage in enumerate(qa.QA_STAGE_ORDER):
        snapshot = gate.wait_for_stage(qa.QaStage(stage), timeout_seconds=1.0)
        assert snapshot.completed_stages == qa.QA_STAGE_ORDER[:index]
        assert not returned[stage].is_set()
        assert completed == list(qa.QA_STAGE_ORDER[:index])
        gate.release(qa.QaStage(stage))
    thread.join(timeout=1.0)
    assert not thread.is_alive()
    assert completed == list(qa.QA_STAGE_ORDER)
    assert gate.finished is True


def test_stage_gate_timeout_breaks_gate_and_prevents_reuse() -> None:
    qa = _qa()
    gate = qa.QaStageGate(timeout_seconds=0.01)

    with pytest.raises(TimeoutError):
        gate.arrive("source")
    with pytest.raises(RuntimeError):
        gate.arrive("source")
    with pytest.raises(RuntimeError):
        gate.release(qa.QaStage.SOURCE)
