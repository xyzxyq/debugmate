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
    ArtifactIdentity,
    AudioAttempt,
    AudioResult,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)

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


@dataclass(frozen=True, slots=True)
class QaStageSnapshot:
    current_stage: str
    completed_stages: tuple[str, ...]


class QaStageGate:
    """A bounded, thread-safe seven-stage rendezvous with strict ordering."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._next_index = 0
        self._current: str | None = None

    @property
    def finished(self) -> bool:
        with self._condition:
            return self._next_index == len(QA_STAGE_ORDER) and self._current is None

    def arrive(self, stage: str) -> QaStageSnapshot:
        with self._condition:
            if self._current is not None or self._next_index >= len(QA_STAGE_ORDER):
                raise RuntimeError("QA stage gate is not ready")
            expected = QA_STAGE_ORDER[self._next_index]
            if stage != expected:
                raise ValueError("QA stage is out of order")
            self._current = stage
            return QaStageSnapshot(stage, QA_STAGE_ORDER[: self._next_index])

    def release(self, stage: str) -> None:
        with self._condition:
            if self._current is None or stage != self._current:
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
    ) -> None:
        self._enabled = process_enabled is True
        self._capability = capability if _CAPABILITY_PATTERN.fullmatch(capability) else ""
        self._handler = scenario_handler
        self._counts = {"scenario": 0, "workflow": 0, "result": 0, "download": 0}

    @property
    def side_effect_counts(self) -> dict[str, int]:
        return dict(self._counts)

    @property
    def route_enabled(self) -> bool:
        """Whether both server-owned installation gates were satisfied."""

        return self._enabled and bool(self._capability)

    def dispatch(self, request: object, payload: object) -> object:
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
        scenario = parse_qa_request(payload)
        self._counts["scenario"] += 1
        return self._handler(scenario)


def mount_qa_endpoint(app: Any, gate: QaCapabilityGate) -> None:
    """Mount the private handler on an explicitly supplied QA-enabled ASGI app."""

    if not gate.route_enabled:
        return

    async def dispatch_private_scenario(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
            result = gate.dispatch(request, payload)
        except (QaAccessDenied, ValueError, TypeError):
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


def _identity() -> ArtifactIdentity:
    return ArtifactIdentity(
        case_id="case_" + "1" * 32,
        source_run_id="run_" + "2" * 32,
        diagnosis_sha256="3" * 64,
        schema_version="1.1.0",
        generation_version="gen_" + "4" * 32,
    )


def _available_audio(identity: ArtifactIdentity, *, fallback: bool = False) -> AudioResult:
    successful = AudioAttempt(
        backend="edge_tts" if fallback else "dify",
        rate_profile="normal",
        succeeded=True,
        duration_ms=40_000,
        sha256="7" * 64,
    )
    attempts = (successful,)
    if fallback:
        attempts = (
            AudioAttempt(
                backend="dify",
                rate_profile="normal",
                succeeded=False,
                safe_error_code="tts_backend_failed",
            ),
            successful,
        )
    return AudioResult(
        identity=identity,
        available=True,
        backend=successful.backend,
        fallback_used=fallback,
        attempts=attempts,
        duration_ms=successful.duration_ms,
        sha256=successful.sha256,
    )


def _spec(scenario: QaScenario) -> QaScenarioSpec:
    identity = _identity()
    result_id = "result_" + "5" * 32
    complete = ArtifactAvailability(report=True, card=True, recap_text=True, audio=True)
    if scenario is QaScenario.VQ_02_REPLAY:
        state = ResultViewState(
            mode=ResultMode.REPLAY,
            status=ResultStatus.COMPLETED,
            fixture_id="module-not-found",
            fixture_name="ModuleNotFoundError：缺少虚拟环境依赖包",
            identity=identity,
            result_id=result_id,
            availability=complete,
            audio=_available_audio(identity),
        )
    elif scenario is QaScenario.VQ_03_RUNNING:
        state = ResultViewState(
            mode=ResultMode.LIVE,
            status=ResultStatus.RUNNING,
            availability=ArtifactAvailability(),
            current_stage=QA_STAGE_ORDER[0],
        )
    elif scenario is QaScenario.VQ_06_TTS_FAILED:
        failure = SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="tts")
        state = ResultViewState(
            mode=ResultMode.LIVE,
            status=ResultStatus.PARTIAL,
            identity=identity,
            result_id=result_id,
            availability=ArtifactAvailability(report=True, card=True, recap_text=True),
            failure=failure,
            audio=AudioResult(
                identity=identity,
                available=False,
                attempts=(
                    AudioAttempt(
                        backend="dify",
                        rate_profile="normal",
                        succeeded=False,
                        safe_error_code="tts_failed",
                    ),
                ),
                failure=failure,
            ),
        )
    elif scenario is QaScenario.VQ_07_PNG_FAILED:
        failure = SafeFailure(code="png_layout_failed", failed_stage="card", retry_scope="card")
        state = ResultViewState(
            mode=ResultMode.LIVE,
            status=ResultStatus.PARTIAL,
            identity=identity,
            result_id=result_id,
            availability=ArtifactAvailability(report=True, recap_text=True, audio=True),
            failure=failure,
            audio=_available_audio(identity),
        )
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
        state = ResultViewState(
            mode=ResultMode.LIVE,
            status=ResultStatus.COMPLETED,
            identity=identity,
            result_id=result_id,
            availability=complete,
            audio=_available_audio(identity, fallback=True),
        )

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
    )


def build_qa_scenario(scenario: QaScenario) -> QaScenarioSpec:
    """Build one deterministic strict scenario without filesystem access."""

    if not isinstance(scenario, QaScenario):
        raise TypeError("scenario must be QaScenario")
    return _spec(scenario)
