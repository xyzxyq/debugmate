"""Private, loopback-only truth-state controls for the Phase 4 QA runner.

This module is deliberately not imported by the normal application assembly.
It accepts closed scenario identifiers, never paths, and keeps the bearer
capability exclusively at the ASGI boundary.
"""

from __future__ import annotations

import hmac
import re
import threading
from collections.abc import Callable, Iterator, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.service import ResultApplicationService

QA_STAGE_ORDER: tuple[str, ...] = (
    "source",
    "presentation",
    "report",
    "card",
    "audio",
    "consistency",
    "publish",
)

_QA_ROUTE = "/_debugmate/qa"
_CAPABILITY_HEADER = "x-debugmate-qa-capability"
_CAPABILITY_PATTERN = re.compile(r"qa_[0-9a-f]{64}\Z")


class QaScenario(Enum):
    """The complete set of browser-audit states; arbitrary input is impossible."""

    VQ_02_REPLAY = "vq-02-replay"
    VQ_03_RUNNING = "vq-03-running"
    VQ_06_TTS_FAILED = "vq-06-tts-failed"
    VQ_07_PNG_FAILED = "vq-07-png-failed"
    VQ_08_SOURCE_INVALID = "vq-08-source-invalid"
    VQ_09_FALLBACK = "vq-09-fallback"


QA_SCENARIOS = frozenset(QaScenario)


class QaStage(Enum):
    SOURCE = "source"
    PRESENTATION = "presentation"
    REPORT = "report"
    CARD = "card"
    AUDIO = "audio"
    CONSISTENCY = "consistency"
    PUBLISH = "publish"


class QaStageAction(Enum):
    HOLD = "hold"
    RELEASE = "release"


@dataclass(frozen=True, slots=True)
class QaScenarioSpec:
    """Safe scenario facts plus the strict UI state that realizes them."""

    scenario: QaScenario
    mode: str
    status: str
    available: tuple[str, ...]
    view_state: ResultViewState
    fixture_id: str | None = None
    fixture_name: str | None = None
    failure_code: str | None = None
    retry_scope: str | None = None
    fallback_backend: str | None = None
    download: bool = True
    source_hashes: tuple[tuple[str, str], ...] = ()
    category: str | None = None
    recap_text: str | None = None


@dataclass(frozen=True, slots=True)
class VerifiedQaBaseline:
    """Opaque result state returned only after the real replay service verifies it."""

    state: ResultViewState
    service: ResultApplicationService
    source_hashes: tuple[tuple[str, str], ...]
    category: str
    recap_text: str


@dataclass(frozen=True, slots=True)
class QaStageSnapshot:
    current_stage: str
    completed_stages: tuple[str, ...]


class QaStageGate:
    """A bounded, thread-safe seven-stage rendezvous with strict ordering."""

    def __init__(self, *, timeout_seconds: float = 5.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("QA stage timeout must be positive")
        self._condition = threading.Condition()
        self._timeout = timeout_seconds
        self._next_index = 0
        self._current: str | None = None
        self._broken = False

    @property
    def finished(self) -> bool:
        with self._condition:
            return self._next_index == len(QA_STAGE_ORDER) and self._current is None

    @property
    def protocol_timeout(self) -> float:
        return self._timeout

    def arrive(self, stage: str) -> QaStageSnapshot:
        with self._condition:
            if self._broken or self._current is not None or self._next_index >= len(QA_STAGE_ORDER):
                raise RuntimeError("QA stage gate is not ready")
            expected = QA_STAGE_ORDER[self._next_index]
            if stage != expected:
                raise ValueError("QA stage is out of order")
            self._current = stage
            snapshot = QaStageSnapshot(stage, QA_STAGE_ORDER[: self._next_index])
            self._condition.notify_all()
            released = self._condition.wait_for(
                lambda: self._current is None or self._broken,
                timeout=self._timeout,
            )
            if not released:
                self._broken = True
                self._current = None
                self._condition.notify_all()
                raise TimeoutError("QA stage release timed out")
            if self._broken:
                raise RuntimeError("QA stage gate is broken")
            return snapshot

    def wait_for_stage(self, stage: QaStage, *, timeout_seconds: float) -> QaStageSnapshot:
        if not isinstance(stage, QaStage) or timeout_seconds <= 0:
            raise ValueError("invalid QA stage wait")
        with self._condition:
            ready = self._condition.wait_for(
                lambda: self._current == stage.value or self._broken,
                timeout=timeout_seconds,
            )
            if not ready:
                raise TimeoutError("QA stage arrival timed out")
            if self._broken:
                raise RuntimeError("QA stage gate is broken")
            return QaStageSnapshot(stage.value, QA_STAGE_ORDER[: self._next_index])

    def release(self, stage: QaStage) -> None:
        with self._condition:
            if self._broken:
                raise RuntimeError("QA stage gate is broken")
            if not isinstance(stage, QaStage) or self._current is None:
                raise ValueError("QA stage is not awaiting release")
            if stage.value != self._current:
                raise ValueError("QA stage is not awaiting release")
            self._current = None
            self._next_index += 1
            self._condition.notify_all()


class QaAccessDenied(LookupError):
    """Value-free denial used for every private-endpoint rejection."""

    def __init__(self) -> None:
        super().__init__("QA endpoint unavailable")


def parse_qa_request(payload: object) -> QaScenario:
    """Parse exactly one enum field; reject extensions and path-like values."""

    if not isinstance(payload, dict) or set(payload) != {"scenario"}:
        raise QaAccessDenied()
    value = payload["scenario"]
    if not isinstance(value, str):
        raise QaAccessDenied()
    try:
        return QaScenario(value)
    except ValueError:
        raise QaAccessDenied() from None


class QaCapabilityGate:
    """Authorize a literal-loopback request before parsing or side effects."""

    def __init__(
        self,
        *,
        process_enabled: bool,
        capability: str,
        scenario_handler: Callable[[QaScenario], object],
        stage_gate: QaStageGate | None = None,
    ) -> None:
        self._enabled = process_enabled is True
        self._capability = capability if _CAPABILITY_PATTERN.fullmatch(capability) else ""
        self._handler = scenario_handler
        self._stage_gate = stage_gate
        self._counts = {"scenario": 0, "workflow": 0, "result": 0, "download": 0}

    @property
    def side_effect_counts(self) -> dict[str, int]:
        return dict(self._counts)

    @property
    def route_enabled(self) -> bool:
        """Whether both server-owned installation gates were satisfied."""

        return self._enabled and bool(self._capability)

    def authorize(self, request: object) -> None:
        client = getattr(request, "client", None)
        host = getattr(client, "host", None)
        headers = getattr(request, "headers", {})
        supplied = headers.get(_CAPABILITY_HEADER, "")
        if (
            not self._enabled
            or host != "127.0.0.1"
            or not self._capability
            or not isinstance(supplied, str)
            or not hmac.compare_digest(self._capability, supplied)
        ):
            raise QaAccessDenied()

    def dispatch_authorized(self, payload: object) -> object:
        if isinstance(payload, dict) and set(payload) == {"action", "stage"}:
            if self._stage_gate is None:
                raise QaAccessDenied()
            try:
                action = QaStageAction(payload["action"])
                stage = QaStage(payload["stage"])
            except (TypeError, ValueError):
                raise QaAccessDenied() from None
            if action is QaStageAction.HOLD:
                snapshot = self._stage_gate.wait_for_stage(
                    stage, timeout_seconds=self._stage_gate.protocol_timeout
                )
                return {
                    "stage": snapshot.current_stage,
                    "completed_stages": list(snapshot.completed_stages),
                }
            self._stage_gate.release(stage)
            return {"released": stage.value}
        scenario = parse_qa_request(payload)
        self._counts["scenario"] += 1
        return self._handler(scenario)

    def dispatch(self, request: object, payload: object) -> object:
        self.authorize(request)
        return self.dispatch_authorized(payload)


def mount_qa_endpoint(app: Any, gate: QaCapabilityGate) -> None:
    """Mount the private handler on an explicitly supplied QA-enabled ASGI app."""

    if not gate.route_enabled:
        return

    async def dispatch_private_scenario(request: Request) -> JSONResponse:
        try:
            gate.authorize(request)
            payload = await request.json()
            result = gate.dispatch_authorized(payload)
        except (QaAccessDenied, RuntimeError, TimeoutError, ValueError, TypeError):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return JSONResponse(result)

    app.add_api_route(
        _QA_ROUTE,
        dispatch_private_scenario,
        methods=["POST"],
        include_in_schema=False,
    )


@contextmanager
def runner_qa_environment(environ: MutableMapping[str, str], capability: str) -> Iterator[None]:
    """Temporarily pass runner-owned process facts and restore them in ``finally``."""

    if not _CAPABILITY_PATTERN.fullmatch(capability):
        raise ValueError("invalid QA capability")
    names = ("DEBUGMATE_QA_ENABLED", "DEBUGMATE_QA_CAPABILITY")
    previous = {name: environ.get(name) for name in names}
    environ[names[0]] = "1"
    environ[names[1]] = capability
    try:
        yield
    finally:
        for name in names:
            old = previous[name]
            if old is None:
                environ.pop(name, None)
            else:
                environ[name] = old


def _verified_baseline_state(value: ResultViewState) -> ResultViewState:
    baseline = ResultViewState.model_validate_json(value.model_dump_json(), strict=True)
    if (
        baseline.mode is not ResultMode.REPLAY
        or baseline.status not in {ResultStatus.COMPLETED, ResultStatus.PARTIAL}
        or baseline.fixture_id != "module-not-found"
        or baseline.identity is None
        or baseline.result_id is None
        or baseline.audio is None
        or (baseline.status is ResultStatus.COMPLETED and not baseline.audio.available)
    ):
        raise ValueError("QA baseline must be a verified module-not-found replay")
    return baseline


def load_verified_qa_baseline(service: ResultApplicationService) -> VerifiedQaBaseline:
    """Load the allowlisted repository fixture through the real strict service."""

    if not isinstance(service, ResultApplicationService):
        raise TypeError("QA baseline requires ResultApplicationService")
    _row, outcome, source = service._load_fixture_source("module-not-found")
    state = _verified_baseline_state(service.load_replay("module-not-found"))
    if (
        outcome.extraction is None
        or outcome.diagnosis is None
        or state.identity is None
        or state.identity.case_id != source.case_id
        or state.identity.source_run_id != source.source_run_id
    ):
        raise ValueError("QA fixture source and result identities differ")
    return VerifiedQaBaseline(
        state=state,
        service=service,
        source_hashes=tuple(sorted(outcome.extraction.source_hashes.items())),
        category=outcome.diagnosis.category,
        recap_text=outcome.diagnosis.recap_text,
    )


def _spec(scenario: QaScenario, verified: VerifiedQaBaseline) -> QaScenarioSpec:
    if not isinstance(verified, VerifiedQaBaseline):
        raise TypeError("QA scenarios require a verified baseline handle")
    baseline = _verified_baseline_state(verified.state)
    if scenario is QaScenario.VQ_02_REPLAY:
        if baseline.status is not ResultStatus.COMPLETED or baseline.failure is not None:
            raise ValueError("VQ-02 requires a published completed replay")
        state = baseline
    elif scenario is QaScenario.VQ_03_RUNNING:
        state = ResultViewState(
            mode=ResultMode.LIVE,
            status=ResultStatus.RUNNING,
            availability=ArtifactAvailability(),
            current_stage=QA_STAGE_ORDER[0],
        )
    elif scenario is QaScenario.VQ_06_TTS_FAILED:
        if (
            baseline.status is not ResultStatus.PARTIAL
            or baseline.failure is None
            or (
                baseline.failure.code,
                baseline.failure.failed_stage,
                baseline.failure.retry_scope,
            )
            != ("tts_failed", "audio", "tts")
        ):
            raise ValueError("VQ-06 requires a published TTS partial")
        state = baseline
    elif scenario is QaScenario.VQ_07_PNG_FAILED:
        if (
            baseline.status is not ResultStatus.PARTIAL
            or baseline.failure is None
            or (
                baseline.failure.code,
                baseline.failure.failed_stage,
                baseline.failure.retry_scope,
            )
            != ("png_layout_failed", "card", "card")
        ):
            raise ValueError("VQ-07 requires a published PNG partial")
        state = baseline
    elif scenario is QaScenario.VQ_08_SOURCE_INVALID:
        state = ResultViewState(
            mode=ResultMode.LIVE,
            status=ResultStatus.FAILED,
            availability=ArtifactAvailability(),
            failure=SafeFailure(
                code="source_bundle_invalid", failed_stage="source", retry_scope="source"
            ),
        )
    else:
        if (
            baseline.status is not ResultStatus.COMPLETED
            or baseline.audio is None
            or not baseline.audio.fallback_used
            or baseline.audio.backend not in {"edge_tts", "sapi"}
        ):
            raise ValueError("VQ-09 requires a published local fallback result")
        state = baseline

    failure = state.failure
    available = tuple(
        name
        for name in ("report", "card", "recap_text", "audio")
        if getattr(state.availability, name)
    )
    return QaScenarioSpec(
        scenario=scenario,
        mode=state.mode.value,
        status=state.status.value,
        available=available,
        view_state=state,
        fixture_id=state.fixture_id,
        fixture_name=state.fixture_name,
        failure_code=None if failure is None else failure.code,
        retry_scope=None if failure is None else failure.retry_scope,
        fallback_backend=(
            state.audio.backend if state.audio is not None and state.audio.fallback_used else None
        ),
        download=state.status is not ResultStatus.FAILED,
        source_hashes=(() if state.status is ResultStatus.FAILED else verified.source_hashes),
        category=None if state.status is ResultStatus.FAILED else verified.category,
        recap_text=None if state.status is ResultStatus.FAILED else verified.recap_text,
    )


def build_qa_scenario(scenario: QaScenario, *, baseline: VerifiedQaBaseline) -> QaScenarioSpec:
    """Build one deterministic strict scenario without filesystem access."""

    if not isinstance(scenario, QaScenario):
        raise TypeError("scenario must be QaScenario")
    return _spec(scenario, baseline)
