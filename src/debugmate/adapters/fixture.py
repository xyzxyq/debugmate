"""Deterministic offline backend for contract and evidence tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter

from debugmate.adapters.base import (
    AudioSynthesisResult,
    CandidateRunResult,
    CapabilityProbeResult,
    FileUploadResult,
)
from debugmate.contracts import CapabilityStatus, CaseId

_CASE_ID_ADAPTER = TypeAdapter(CaseId)


class FixtureNotFound(FileNotFoundError):
    """Raised when a named fixture case is unavailable."""


class FixtureCapabilityUnavailable(RuntimeError):
    """Raised when a cloud-only operation is requested from the fixture backend."""


class FixtureBackend:
    """Load one versioned fixture and validate it through the public contract."""

    def __init__(self, fixtures_root: Path, case_name: str = "module_not_found") -> None:
        self._fixtures_root = fixtures_root
        self._case_name = case_name

    @property
    def _case_dir(self) -> Path:
        case_dir = self._fixtures_root / self._case_name
        if not case_dir.is_dir():
            raise FixtureNotFound(f"fixture case not found: {self._case_name}")
        return case_dir

    def upload_file(self, path: Path, user: str) -> FileUploadResult:
        del user
        if not path.is_file():
            raise FileNotFoundError(path)
        return FileUploadResult(
            file_id=f"fixture:{path.name}",
            filename=path.name,
            backend="fixture",
        )

    def upload_bytes(
        self,
        content: bytes,
        *,
        filename: str,
        mime_type: Literal["image/png", "image/jpeg"],
        user: str,
    ) -> FileUploadResult:
        del content, mime_type, user
        return FileUploadResult(
            file_id=f"fixture:{filename}",
            filename=filename,
            backend="fixture",
        )

    def run_workflow(self, inputs: dict[str, object], user: str) -> CandidateRunResult:
        del user
        diagnosis_path = self._case_dir / "diagnosis.json"
        if not diagnosis_path.is_file():
            raise FixtureNotFound(f"fixture diagnosis not found: {self._case_name}")

        payload = json.loads(diagnosis_path.read_text(encoding="utf-8"))
        payload["case_id"] = _CASE_ID_ADAPTER.validate_python(inputs.get("case_id"), strict=True)
        return CandidateRunResult(
            run_id=f"fixture:{self._case_name}",
            backend="fixture",
            candidate_payload=payload,
        )

    def synthesize_audio(self, text: str, user: str) -> AudioSynthesisResult:
        del text, user
        raise FixtureCapabilityUnavailable("fixture backend does not generate audio")

    def capability_probe(self) -> CapabilityProbeResult:
        return CapabilityProbeResult(
            backend="fixture",
            capabilities={
                f"C{index:02d}": CapabilityStatus.NOT_TESTED for index in range(1, 8)
            },
        )
