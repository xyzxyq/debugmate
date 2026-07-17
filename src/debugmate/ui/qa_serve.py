"""Explicit runner-only Gradio assembly for real Edge truth-state checks.

Normal ``debugmate.ui.serve`` never imports this module.  The only selector is
the closed, capability-protected QA endpoint; no scenario value is exposed in
the public Gradio config or page state.
"""

from __future__ import annotations

import argparse
import os
import threading
from collections.abc import Iterator, Sequence
from pathlib import Path

from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.service import ServiceStageEvent
from debugmate.ui.app import WORKBENCH_CSS, build_app, ensure_content_endpoint
from debugmate.ui.qa_scenarios import (
    QA_STAGE_ORDER,
    QaCapabilityGate,
    QaScenario,
    QaStageGate,
    build_qa_scenario,
    load_verified_qa_baseline,
    mount_qa_endpoint,
)
from debugmate.ui.serve import _available_loopback_port, _local_service


class _QaService:
    """Switch only among server-built, verified scenario services."""

    def __init__(self, runtime_root: Path, stage_gate: QaStageGate) -> None:
        self._runtime_root = runtime_root
        self._stage_gate = stage_gate
        self._lock = threading.RLock()
        self._scenario: QaScenario | None = None
        self._services: dict[QaScenario, object] = {}
        self._states: dict[QaScenario, ResultViewState] = {}
        self._terminals: dict[QaScenario, ResultViewState] = {}

    def activate(self, scenario: QaScenario) -> dict[str, str]:
        modes = {
            QaScenario.VQ_02_REPLAY: None,
            QaScenario.VQ_03_RUNNING: None,
            QaScenario.VQ_06_TTS_FAILED: "tts_failed",
            QaScenario.VQ_07_PNG_FAILED: "png_failed",
            QaScenario.VQ_09_FALLBACK: "fallback",
        }
        with self._lock:
            if scenario is not QaScenario.VQ_08_SOURCE_INVALID and scenario not in self._states:
                service = _local_service(
                    runtime_root=self._runtime_root / scenario.value,
                    replay_local_only=True,
                    qa_result_mode=modes[scenario],
                )
                baseline = load_verified_qa_baseline(service)
                self._services[scenario] = service
                self._terminals[scenario] = baseline.state
                self._states[scenario] = build_qa_scenario(scenario, baseline=baseline).view_state
            self._scenario = scenario
        return {"accepted": scenario.value}

    def _selected(self) -> QaScenario:
        with self._lock:
            if self._scenario is None:
                raise ValueError("QA scenario is not active")
            return self._scenario

    def _service(self):
        scenario = self._selected()
        try:
            return self._services[scenario]
        except KeyError:
            raise ValueError("QA scenario has no result service") from None

    def audit_counts(self) -> dict[str, int]:
        """Return counts only from the selected runner-owned scenario tree."""

        scenario_root = self._runtime_root / self._selected().value
        return {
            "run_count": sum(
                1 for _item in (scenario_root / "evidence").glob("case_*/run_*/manifest.json")
            ),
            "result_count": sum(
                1
                for _item in (scenario_root / "results").glob(
                    "case_*/result_*/result-manifest.json"
                )
            ),
        }

    def load_replay_events(self, _fixture_id: str) -> Iterator[ServiceStageEvent]:
        scenario = self._selected()
        if scenario is QaScenario.VQ_08_SOURCE_INVALID:
            yield ServiceStageEvent(
                ResultViewState(
                    mode=ResultMode.LIVE,
                    status=ResultStatus.FAILED,
                    availability=ArtifactAvailability(),
                    failure=SafeFailure(
                        code="source_bundle_invalid",
                        failed_stage="source",
                        retry_scope="source",
                    ),
                )
            )
            return
        state = self._states[scenario]
        if scenario is QaScenario.VQ_03_RUNNING:
            for index, stage in enumerate(QA_STAGE_ORDER):
                yield ServiceStageEvent(
                    ResultViewState(
                        mode=ResultMode.REPLAY,
                        status=ResultStatus.RUNNING,
                        fixture_id="module-not-found",
                        fixture_name="ModuleNotFoundError：缺少虚构依赖包",
                        availability=ArtifactAvailability(),
                        current_stage=stage,
                        completed_stages=QA_STAGE_ORDER[:index],
                    )
                )
                self._stage_gate.arrive(stage)
        terminal = self._terminals[scenario] if scenario is QaScenario.VQ_03_RUNNING else state
        yield ServiceStageEvent(terminal)

    def load_replay(self, _fixture_id: str) -> ResultViewState:
        return self._states[self._selected()]

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._service(), name)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m debugmate.ui.qa_serve")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=_available_loopback_port)
    parser.add_argument("--runtime-root", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.host != "127.0.0.1":
        parser.error("host must be literal 127.0.0.1")
    capability = os.environ.get("DEBUGMATE_QA_CAPABILITY", "")
    enabled = os.environ.get("DEBUGMATE_QA_ENABLED") == "1"
    stage_gate = QaStageGate(timeout_seconds=30.0)
    service = _QaService(args.runtime_root.absolute(), stage_gate)
    app = build_app(service, content_origin=f"http://{args.host}:{args.port}")
    callbacks = app._debugmate_content_callbacks

    def audit() -> dict[str, object]:
        return {
            **service.audit_counts(),
            "session_states": callbacks.session_audit_snapshot(),
            "session_events": callbacks.session_audit_events(),
        }

    gate = QaCapabilityGate(
        process_enabled=enabled,
        capability=capability,
        scenario_handler=service.activate,
        stage_gate=stage_gate,
        audit_handler=audit,
    )
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        inbrowser=False,
        quiet=True,
        show_error=False,
        prevent_thread_lock=True,
        css=WORKBENCH_CSS,
    )
    ensure_content_endpoint(app)
    mount_qa_endpoint(app.app, gate)
    app.block_thread()
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by Edge runner
    raise SystemExit(main())
