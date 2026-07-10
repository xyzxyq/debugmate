"""Platform-neutral backend port used by DebugMate."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from debugmate.contracts import CapabilityStatus, DiagnosisRecord


@dataclass(frozen=True, slots=True)
class FileUploadResult:
    file_id: str
    filename: str
    backend: str


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    run_id: str
    diagnosis: DiagnosisRecord
    backend: str


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
class DiagnosisBackend(Protocol):
    """Narrow backend interface shared by fixture and cloud adapters."""

    def upload_file(self, path: Path, user: str) -> FileUploadResult: ...

    def run_workflow(self, inputs: dict[str, object], user: str) -> WorkflowRunResult: ...

    def synthesize_audio(self, text: str, user: str) -> AudioSynthesisResult: ...

    def capability_probe(self) -> CapabilityProbeResult: ...
