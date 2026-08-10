"""Approval-only boundary between local privacy processing and cloud backends."""

from __future__ import annotations

import hmac
import stat
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, UnidentifiedImageError

from debugmate.adapters.base import ApprovedImageBackend, CandidateRunResult
from debugmate.diagnosis.correction import CorrectionOverlay, apply_correction
from debugmate.diagnosis.extraction import CaseFacts
from debugmate.diagnosis.workflow import DiagnosisRunOutcome, DiagnosisWorkflow
from debugmate.hashing import UnsafeArtifactPath, resolve_artifact_path, sha256_bytes
from debugmate.privacy.approval import ApprovalInvalid, verify_approval
from debugmate.privacy.image_models import MAX_SCREENSHOT_BYTES, MAX_SCREENSHOT_PIXELS
from debugmate.privacy.models import ApprovedRedactedInput

_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        raise ApprovalInvalid("approved redacted screenshot is unavailable") from None
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & _REPARSE_POINT
    )


def _resolve_regular_screenshot(root: Path, relative: Path) -> Path:
    """Reject every link/reparse component before resolving under the trusted root."""

    root_resolved = root.resolve()
    candidate = root_resolved
    for part in relative.parts:
        candidate /= part
        if _is_link_or_reparse(candidate):
            raise ApprovalInvalid("approved screenshot path is unsafe")
    try:
        resolved = resolve_artifact_path(root_resolved, relative)
        metadata = resolved.lstat()
    except (OSError, UnsafeArtifactPath):
        raise ApprovalInvalid("approved screenshot path is unsafe") from None
    if not stat.S_ISREG(metadata.st_mode):
        raise ApprovalInvalid("approved redacted screenshot is unavailable")
    return resolved


def _read_approved_image(
    path: Path, expected_sha256: str
) -> tuple[bytes, Literal["image/png", "image/jpeg"]]:
    """Read once, then bind hashing, decoding and MIME to the same immutable bytes."""

    try:
        before = path.lstat()
        with path.open("rb") as source:
            content = source.read(MAX_SCREENSHOT_BYTES + 1)
        after = path.lstat()
    except OSError:
        raise ApprovalInvalid("approved redacted screenshot is unavailable") from None
    if _is_link_or_reparse(path) or (before.st_dev, before.st_ino) != (
        after.st_dev,
        after.st_ino,
    ):
        raise ApprovalInvalid("approved screenshot path is unsafe")
    if len(content) > MAX_SCREENSHOT_BYTES:
        raise ApprovalInvalid("approved screenshot exceeds the size limit")
    actual_sha256 = sha256_bytes(content)
    if not hmac.compare_digest(actual_sha256, expected_sha256):
        raise ApprovalInvalid("approved redacted screenshot has changed")

    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image_format = image.format
            width, height = image.size
    except (OSError, UnidentifiedImageError, ValueError):
        raise ApprovalInvalid("approved screenshot is invalid") from None
    if width <= 0 or height <= 0 or width * height > MAX_SCREENSHOT_PIXELS:
        raise ApprovalInvalid("approved screenshot dimensions are invalid")

    suffix = path.suffix.casefold()
    if image_format == "PNG" and suffix == ".png":
        return content, "image/png"
    if image_format == "JPEG" and suffix in {".jpg", ".jpeg"}:
        return content, "image/jpeg"
    raise ApprovalInvalid("approved screenshot extension and MIME do not match")


class CloudGateway:
    """Expose one narrow cloud call that cannot accept raw or preview input."""

    def __init__(
        self,
        backend: ApprovedImageBackend,
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
            path = _resolve_regular_screenshot(
                self._redacted_root, Path(redacted.redacted_screenshot_path)
            )
            content, mime_type = _read_approved_image(
                path, redacted.redacted_screenshot_sha256
            )
            uploaded = self._backend.upload_bytes(
                content,
                filename=path.name,
                mime_type=mime_type,
                user=self._user,
            )
            inputs["image_input"] = {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": uploaded.file_id,
            }

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
