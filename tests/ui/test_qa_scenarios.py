"""RED contracts for the private Phase 4 truth-state scenario factory."""

from __future__ import annotations

import importlib
from enum import Enum

import pytest

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
    gate = qa.QaStageGate()

    for index, stage in enumerate(EXPECTED_STAGES):
        snapshot = gate.arrive(stage)
        assert snapshot.current_stage == stage
        assert snapshot.completed_stages == EXPECTED_STAGES[:index]
        assert not hasattr(snapshot, "percentage")
        gate.release(stage)
    assert gate.finished is True
    with pytest.raises((RuntimeError, ValueError)):
        qa.QaStageGate().arrive("report")


def test_truth_state_specs_preserve_replay_partial_failed_and_fallback_semantics() -> None:
    qa = _qa()
    specs = {scenario: qa.build_qa_scenario(scenario) for scenario in qa.QaScenario}

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
