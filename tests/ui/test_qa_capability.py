"""RED isolation contracts for the runner-owned QA capability."""

from __future__ import annotations

import importlib
import json
import logging
import socket
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from debugmate.ui import serve as serve_module
from debugmate.ui.app import build_app

CAPABILITY = "qa_" + "a" * 64
HEADER = "x-debugmate-qa-capability"
QA_ROUTE = "/_debugmate/qa"


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
        self.evidence: list[dict[str, str]] = []

    def __call__(self, scenario):
        self.calls.append(scenario)
        record = {"event": "qa_scenario_accepted", "scenario": scenario.value}
        self.evidence.append(record)
        logging.getLogger("debugmate.qa.audit").info("qa scenario accepted: %s", scenario.value)
        return {"accepted": True}


INVALID_PAYLOADS = (
    {},
    {"scenario": "vq-99-unknown"},
    {"scenario": "vq-02-replay", "extra": True},
    {"scenario": "../vq-02-replay"},
    {"scenario": r"C:\\fixtures\\replay.json"},
    {"scenario": "/tmp/replay.json"},
)


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


@pytest.mark.parametrize("payload", INVALID_PAYLOADS)
def test_invalid_scenario_payloads_cross_real_http_endpoint_with_zero_side_effects(
    payload: object,
) -> None:
    """The mounted endpoint cannot bypass the strict parser before effect ports."""

    qa = _qa()
    calls = _ScenarioCalls()
    gate = qa.QaCapabilityGate(
        process_enabled=True,
        capability=CAPABILITY,
        scenario_handler=calls,
    )
    app = build_app(object())
    qa.mount_qa_endpoint(app.app, gate)

    response = TestClient(app.app, client=("127.0.0.1", 50000)).post(
        QA_ROUTE,
        headers={HEADER: CAPABILITY},
        json=payload,
    )

    assert response.status_code == 404
    assert calls.calls == []
    assert calls.evidence == []
    assert gate.side_effect_counts == {
        "scenario": 0,
        "workflow": 0,
        "result": 0,
        "download": 0,
    }


def test_real_http_qa_route_accepts_exact_capability_and_records_safe_audit(
    caplog: pytest.LogCaptureFixture,
) -> None:
    qa = _qa()
    calls = _ScenarioCalls()
    gate = qa.QaCapabilityGate(
        process_enabled=True,
        capability=CAPABILITY,
        scenario_handler=calls,
    )

    app = build_app(object())
    qa.mount_qa_endpoint(app.app, gate)
    caplog.set_level(logging.INFO, logger="debugmate.qa.audit")
    response = TestClient(app.app, client=("127.0.0.1", 50000)).post(
        QA_ROUTE,
        headers={HEADER: CAPABILITY},
        json={"scenario": "vq-02-replay"},
    )

    assert response.status_code == 200
    assert response.json() == {"accepted": True}
    assert calls.calls == [qa.QaScenario.VQ_02_REPLAY]
    serialized_evidence = json.dumps(calls.evidence, sort_keys=True)
    assert "qa_scenario_accepted" in serialized_evidence
    assert "qa scenario accepted" in caplog.text
    for surface in (response.text, serialized_evidence, caplog.text):
        assert CAPABILITY not in surface
        assert HEADER not in surface.lower()


@pytest.mark.parametrize(
    "process_enabled,client_host,headers,wrong_token",
    [
        (True, "127.0.0.1", {}, None),
        (True, "127.0.0.1", {HEADER: "qa_" + "b" * 64}, "qa_" + "b" * 64),
        (True, "192.0.2.10", {HEADER: CAPABILITY}, None),
        (False, "127.0.0.1", {HEADER: CAPABILITY}, None),
    ],
)
def test_real_http_qa_route_denies_missing_wrong_or_nonloopback_without_side_effects(
    process_enabled: bool,
    client_host: str,
    headers: dict[str, str],
    wrong_token: str | None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    qa = _qa()
    calls = _ScenarioCalls()
    gate = qa.QaCapabilityGate(
        process_enabled=process_enabled,
        capability=CAPABILITY,
        scenario_handler=calls,
    )
    app = build_app(object())
    qa.mount_qa_endpoint(app.app, gate)
    caplog.set_level(logging.DEBUG)

    response = TestClient(app.app, client=(client_host, 50000)).post(
        QA_ROUTE,
        headers=headers,
        json={"scenario": "vq-02-replay"},
    )

    assert response.status_code == 404
    assert calls.calls == []
    assert calls.evidence == []
    assert gate.side_effect_counts == {
        "scenario": 0,
        "workflow": 0,
        "result": 0,
        "download": 0,
    }
    assert CAPABILITY not in response.text
    assert HEADER not in response.text.lower()
    assert CAPABILITY not in caplog.text
    assert HEADER not in caplog.text.lower()
    if wrong_token is not None:
        assert wrong_token not in response.text
        assert wrong_token not in caplog.text


@pytest.mark.parametrize(
    "enabled,capability",
    [(False, CAPABILITY), (True, "not-a-fresh-capability")],
)
def test_qa_route_is_not_installed_without_both_server_side_gates(
    enabled: bool, capability: str
) -> None:
    qa = _qa()
    gate = qa.QaCapabilityGate(
        process_enabled=enabled,
        capability=capability,
        scenario_handler=lambda _scenario: {"accepted": True},
    )
    app = build_app(object())

    qa.mount_qa_endpoint(app.app, gate)

    assert QA_ROUTE not in {getattr(route, "path", "") for route in app.app.routes}


def test_enabled_qa_handler_on_real_app_keeps_capability_out_of_every_public_surface() -> None:
    qa = _qa()
    gate = qa.QaCapabilityGate(
        process_enabled=True,
        capability=CAPABILITY,
        scenario_handler=lambda _scenario: {"status": "accepted"},
    )
    app = build_app(object())
    qa.mount_qa_endpoint(app.app, gate)
    config = app.get_config_file()
    route_surfaces = tuple(
        (
            getattr(route, "path", ""),
            getattr(route, "name", ""),
            getattr(getattr(route, "endpoint", None), "__qualname__", ""),
        )
        for route in app.app.routes
    )
    public_surfaces = (
        json.dumps(config, sort_keys=True, default=str),
        repr(config.get("components", ())),
        repr(config.get("dependencies", ())),
        repr(route_surfaces),
        *(path for path, _name, _endpoint in route_surfaces),
    )

    assert any("qa" in path.lower() for path, _name, _endpoint in route_surfaces)
    assert all(CAPABILITY not in surface for surface in public_surfaces)
    assert all(HEADER not in surface.lower() for surface in public_surfaces)


def test_ordinary_serve_assembly_ignores_residual_qa_environment_without_explicit_enablement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _qa()
    monkeypatch.setenv("DEBUGMATE_QA_ENABLED", "1")
    monkeypatch.setenv("DEBUGMATE_QA_CAPABILITY", CAPABILITY)
    monkeypatch.setattr(serve_module, "_local_service", lambda **_kwargs: object())
    captured: dict[str, object] = {}

    class _LaunchProbe:
        def __init__(self, app) -> None:
            self.app = app

        def launch(self, **kwargs) -> None:
            captured["launch"] = kwargs

    def capture_build(service, **kwargs):
        app = build_app(service, **kwargs)
        captured["app"] = app
        return _LaunchProbe(app)

    monkeypatch.setattr(serve_module, "build_app", capture_build)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        port = int(listener.getsockname()[1])

    assert serve_module.main(["--host", "127.0.0.1", "--port", str(port)]) == 0
    app = captured["app"]
    route_surfaces = repr(
        [
            (
                getattr(route, "path", ""),
                getattr(route, "name", ""),
                getattr(getattr(route, "endpoint", None), "__qualname__", ""),
            )
            for route in app.app.routes
        ]
    ).lower()
    callback_surfaces = repr(
        [
            (
                getattr(block_fn.fn, "__module__", ""),
                getattr(block_fn.fn, "__qualname__", ""),
            )
            for block_fn in app.fns.values()
        ]
    ).lower()

    assert "qa_scenarios" not in route_surfaces + callback_surfaces
    assert QA_ROUTE not in route_surfaces
    assert CAPABILITY not in route_surfaces + callback_surfaces


def test_runner_environment_restores_preexisting_and_missing_values() -> None:
    qa = _qa()

    class RunnerBodyFailed(RuntimeError):
        pass

    environ = {
        "DEBUGMATE_QA_ENABLED": "previous-enabled",
        "DEBUGMATE_QA_CAPABILITY": "previous-capability",
        "KEEP": "untouched",
    }
    with pytest.raises(RunnerBodyFailed), qa.runner_qa_environment(environ, CAPABILITY):
        assert environ["DEBUGMATE_QA_ENABLED"] == "1"
        assert environ["DEBUGMATE_QA_CAPABILITY"] == CAPABILITY
        raise RunnerBodyFailed
    assert environ == {
        "DEBUGMATE_QA_ENABLED": "previous-enabled",
        "DEBUGMATE_QA_CAPABILITY": "previous-capability",
        "KEEP": "untouched",
    }

    clean = {"KEEP": "untouched"}
    with pytest.raises(RunnerBodyFailed), qa.runner_qa_environment(clean, CAPABILITY):
        raise RunnerBodyFailed
    assert clean == {"KEEP": "untouched"}
