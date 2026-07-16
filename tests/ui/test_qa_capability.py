"""RED isolation contracts for the runner-owned QA capability."""

from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass

import pytest

CAPABILITY = "qa_" + "a" * 64
HEADER = "x-debugmate-qa-capability"


def _qa():
    return importlib.import_module("debugmate.ui.qa_scenarios")


@dataclass
class _Client:
    host: str


@dataclass
class _Request:
    host: str = "127.0.0.1"
    capability: str | None = CAPABILITY

    @property
    def client(self):
        return _Client(self.host)

    @property
    def headers(self):
        return {} if self.capability is None else {HEADER: self.capability}


class _ScenarioCalls:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def __call__(self, scenario):
        self.calls.append(scenario)
        return {"accepted": True}


@pytest.mark.parametrize(
    "enabled,qa_request",
    [
        (False, _Request()),
        (True, _Request(capability=None)),
        (True, _Request(capability=CAPABILITY + "wrong")),
        (True, _Request(host="localhost")),
        (True, _Request(host="::1")),
        (True, _Request(host="192.0.2.10")),
    ],
)
def test_denied_qa_requests_have_zero_scenario_workflow_result_or_download_side_effects(
    enabled: bool, qa_request: _Request
) -> None:
    qa = _qa()
    calls = _ScenarioCalls()
    gate = qa.QaCapabilityGate(
        process_enabled=enabled,
        capability=CAPABILITY,
        scenario_handler=calls,
    )

    with pytest.raises(qa.QaAccessDenied):
        gate.dispatch(qa_request, {"scenario": "vq-02-replay"})

    assert calls.calls == []
    assert gate.side_effect_counts == {
        "scenario": 0,
        "workflow": 0,
        "result": 0,
        "download": 0,
    }


def test_dual_gate_accepts_only_enabled_literal_loopback_with_exact_header() -> None:
    qa = _qa()
    calls = _ScenarioCalls()
    gate = qa.QaCapabilityGate(
        process_enabled=True,
        capability=CAPABILITY,
        scenario_handler=calls,
    )

    response = gate.dispatch(_Request(), {"scenario": "vq-02-replay"})

    assert response == {"accepted": True}
    assert calls.calls == [qa.QaScenario.VQ_02_REPLAY]


def test_capability_never_serializes_or_reaches_config_dom_url_log_or_evidence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    qa = _qa()
    gate = qa.QaCapabilityGate(
        process_enabled=True,
        capability=CAPABILITY,
        scenario_handler=lambda _scenario: {"status": "accepted"},
    )
    caplog.set_level(logging.DEBUG)

    response = gate.dispatch(_Request(), {"scenario": "vq-09-fallback"})
    surfaces = (
        repr(gate.public_config()),
        repr(gate.component_values()),
        gate.dom_payload(),
        gate.public_url,
        caplog.text,
        json.dumps(gate.evidence_record(response), sort_keys=True),
        repr(gate),
    )

    assert all(CAPABILITY not in surface for surface in surfaces)
    assert all(HEADER not in surface.lower() for surface in surfaces)


def test_runner_environment_restores_preexisting_and_missing_values() -> None:
    qa = _qa()
    environ = {
        "DEBUGMATE_QA_ENABLED": "previous-enabled",
        "DEBUGMATE_QA_CAPABILITY": "previous-capability",
        "KEEP": "untouched",
    }
    with qa.runner_qa_environment(environ, CAPABILITY):
        assert environ["DEBUGMATE_QA_ENABLED"] == "1"
        assert environ["DEBUGMATE_QA_CAPABILITY"] == CAPABILITY
    assert environ == {
        "DEBUGMATE_QA_ENABLED": "previous-enabled",
        "DEBUGMATE_QA_CAPABILITY": "previous-capability",
        "KEEP": "untouched",
    }

    clean = {"KEEP": "untouched"}
    with qa.runner_qa_environment(clean, CAPABILITY):
        pass
    assert clean == {"KEEP": "untouched"}
