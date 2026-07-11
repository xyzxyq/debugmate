"""Approval-only boundary between local privacy processing and cloud backends."""

from __future__ import annotations

import hmac
from pathlib import Path

from debugmate.adapters.base import DiagnosisBackend, WorkflowRunResult
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

    def run(self, approved: ApprovedRedactedInput) -> WorkflowRunResult:
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
