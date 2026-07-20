"""Tamper-evident, short-lived approval for a redaction preview."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from debugmate.hashing import canonical_json_bytes
from debugmate.privacy.models import ApprovedRedactedInput, PreviewBundle

APPROVAL_TTL = timedelta(minutes=30)
MINIMUM_KEY_BYTES = 32


class ApprovalInvalid(ValueError):
    """Raised without sensitive details when an approval cannot be trusted."""


def _validate_key(key: bytes) -> None:
    if not isinstance(key, bytes):
        raise TypeError("approval key must be bytes")
    if len(key) < MINIMUM_KEY_BYTES:
        raise ValueError("approval key is too short")


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def signature_payload(value: ApprovedRedactedInput | PreviewBundle) -> bytes:
    """Return canonical signed fields, including the approved redacted values."""

    payload: dict[str, object] = {
        "case_id": value.case_id,
        "preview_hash": value.preview_hash,
        "redacted": value.redacted.model_dump(mode="json"),
    }
    if isinstance(value, ApprovedRedactedInput):
        payload.update(
            {
                "approval_id": value.approval_id,
                "approved_at_utc": _utc_text(value.approved_at_utc),
            }
        )
    return canonical_json_bytes(payload)


def _signature(value: ApprovedRedactedInput | PreviewBundle, key: bytes) -> str:
    _validate_key(key)
    return hmac.new(key, signature_payload(value), hashlib.sha256).hexdigest()


def sign_preview(preview: PreviewBundle, key: bytes) -> str:
    """Sign a preview payload for callers that need a deterministic fingerprint."""

    return _signature(preview, key)


def approve_preview(
    preview: PreviewBundle,
    key: bytes,
    *,
    approved_at_utc: datetime | None = None,
) -> ApprovedRedactedInput:
    """Create a random approval ID and bind it to this exact redacted payload."""

    _validate_key(key)
    approved_at = datetime.now(UTC) if approved_at_utc is None else approved_at_utc
    if approved_at.tzinfo is None or approved_at.utcoffset() != UTC.utcoffset(approved_at):
        raise ValueError("approved_at_utc must be UTC aware")
    unsigned = ApprovedRedactedInput(
        case_id=preview.case_id,
        redacted=preview.redacted,
        preview_hash=preview.preview_hash,
        approval_id=secrets.token_hex(16),
        approval_signature="0" * 64,
        approved_at_utc=approved_at,
    )
    return unsigned.model_copy(update={"approval_signature": _signature(unsigned, key)})


def verify_approval(
    approved: ApprovedRedactedInput,
    key: bytes,
    *,
    now: datetime | None = None,
) -> None:
    """Reject modified, future-dated, expired, or wrongly signed approvals."""

    if not isinstance(approved, ApprovedRedactedInput):
        raise TypeError("approved input must be ApprovedRedactedInput")
    _validate_key(key)
    checked_at = datetime.now(UTC) if now is None else now
    if checked_at.tzinfo is None or checked_at.utcoffset() != UTC.utcoffset(checked_at):
        raise ValueError("now must be UTC aware")
    age = checked_at - approved.approved_at_utc
    if age < timedelta(0) or age > APPROVAL_TTL:
        raise ApprovalInvalid("approval is outside its validity window")
    expected = _signature(approved, key)
    if not hmac.compare_digest(approved.approval_signature, expected):
        raise ApprovalInvalid("approval signature is invalid")

