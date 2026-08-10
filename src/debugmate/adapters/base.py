"""Platform-neutral backend port used by DebugMate."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from debugmate.cloud.contracts import DifyRunEnvelope, DifyUsage
from debugmate.contracts import CapabilityStatus

MAX_CANDIDATE_PAYLOAD_BYTES = 256 * 1024


@dataclass(frozen=True, slots=True)
class FileUploadResult:
    file_id: str
    filename: str
    backend: str
    file_id_fingerprint: str | None = None
    mime_type: str | None = None
    size: int | None = None


@dataclass(frozen=True, slots=True)
class CandidateRunResult:
    run_id: str
    backend: str
    candidate_payload: object
    run_envelope: DifyRunEnvelope | None = None
    usage: DifyUsage = DifyUsage()

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.backend.strip():
            raise ValueError("candidate envelope metadata must not be blank")
        try:
            encoded = json.dumps(
                self.candidate_payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            raise TypeError("candidate payload must be a JSON value") from None
        if len(encoded) > MAX_CANDIDATE_PAYLOAD_BYTES:
            raise ValueError("candidate payload exceeds the local size limit")
        object.__setattr__(self, "candidate_payload", copy.deepcopy(self.candidate_payload))


@dataclass(frozen=True, slots=True)
class AudioSynthesisResult:
    audio: bytes
    mime_type: str
    backend: str


@dataclass(frozen=True, slots=True)
class CapabilityProbeResult:
    backend: str
    capabilities: dict[str, CapabilityStatus]


@runtime_checkable
class CandidateBackend(Protocol):
    """Candidate-only transport port used by local diagnosis generation."""

    def run_workflow(self, inputs: dict[str, object], user: str) -> CandidateRunResult: ...


@runtime_checkable
class ApprovedImageBackend(CandidateBackend, Protocol):
    """Cloud boundary that accepts only an application-owned byte snapshot."""

    def upload_bytes(
        self,
        content: bytes,
        *,
        filename: str,
        mime_type: Literal["image/png", "image/jpeg"],
        user: str,
    ) -> FileUploadResult: ...


@runtime_checkable
class DiagnosisBackend(ApprovedImageBackend, Protocol):
    """Backend interface shared by fixture and cloud adapters."""

    def synthesize_audio(self, text: str, user: str) -> AudioSynthesisResult: ...

    def capability_probe(self) -> CapabilityProbeResult: ...
