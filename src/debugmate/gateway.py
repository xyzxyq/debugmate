"""Approval-only boundary between local privacy processing and cloud backends."""

from __future__ import annotations

import hmac
from pathlib import Path

from debugmate.adapters.base import CandidateRunResult, DiagnosisBackend
from debugmate.diagnosis.correction import CorrectionOverlay, apply_correction
from debugmate.diagnosis.extraction import CaseFacts
from debugmate.diagnosis.workflow import DiagnosisRunOutcome, DiagnosisWorkflow
from debugmate.hashing import UnsafeArtifactPath, resolve_artifact_path, sha256_file
from debugmate.privacy.approval import ApprovalInvalid, verify_approval
from debugmate.privacy.models import ApprovedRedactedInput


class CloudGateway:
    """Expose one narrow cloud call that cannot accept raw or preview input."""

    def __init__(
        self,
        backend: DiagnosisBackend,
        *,
        approval_key: bytes,
        user: str = "debugmate-local",
        redacted_root: Path | None = None,
    ) -> None:
        self._backend = backend
        self._approval_key = approval_key
        self._user = user
        self._redacted_root = None if redacted_root is None else Path(redacted_root)

    def run(self, approved: ApprovedRedactedInput) -> CandidateRunResult:
        if not isinstance(approved, ApprovedRedactedInput):
            raise TypeError("CloudGateway accepts only ApprovedRedactedInput")
        verify_approval(approved, self._approval_key)

        redacted = approved.redacted
        inputs: dict[str, object] = {
            "error_text": redacted.error_text,
            "code": redacted.code,
            "environment": redacted.environment,
            "case_id": approved.case_id,
        }
        if redacted.redacted_screenshot_path is not None:
            if redacted.redacted_screenshot_sha256 is None:
                raise ApprovalInvalid("approved screenshot hash is missing")
            if self._redacted_root is None:
                raise ApprovalInvalid("approved screenshot root is unavailable")
            try:
                path = resolve_artifact_path(
                    self._redacted_root, Path(redacted.redacted_screenshot_path)
                )
            except UnsafeArtifactPath:
                raise ApprovalInvalid("approved screenshot path is unsafe") from None
            if not path.is_file():
                raise ApprovalInvalid("approved redacted screenshot is unavailable")
            actual_hash = sha256_file(path)
            if not hmac.compare_digest(actual_hash, redacted.redacted_screenshot_sha256):
                raise ApprovalInvalid("approved redacted screenshot has changed")
            uploaded = self._backend.upload_file(path, self._user)
            inputs["screenshot_file_id"] = uploaded.file_id

        return self._backend.run_workflow(inputs, self._user)


def run_diagnosis_json(
    workflow: DiagnosisWorkflow,
    approved_payload: str,
    *,
    followup_answers: dict[object, str] | None = None,
) -> DiagnosisRunOutcome:
    """Strict JSON entry; the workflow performs approval verification before work."""

    approved = ApprovedRedactedInput.model_validate_json(approved_payload, strict=True)
    return workflow.run(approved, followup_answers=followup_answers)


def apply_correction_json(facts_payload: str, overlay_payload: str) -> CaseFacts:
    """Strict optimistic-lock correction boundary with no provider side effects."""

    facts = CaseFacts.model_validate_json(facts_payload, strict=True)
    overlay = CorrectionOverlay.model_validate_json(overlay_payload, strict=True)
    return apply_correction(facts, overlay)


def rerun_diagnosis_json(
    workflow: DiagnosisWorkflow,
    previous_payload: str,
    overlay_payload: str,
) -> DiagnosisRunOutcome:
    """Strict correction-rerun boundary preserving the previous immutable outcome."""

    previous = DiagnosisRunOutcome.model_validate_json(previous_payload, strict=True)
    overlay = CorrectionOverlay.model_validate_json(overlay_payload, strict=True)
    return workflow.rerun(previous, overlay)
