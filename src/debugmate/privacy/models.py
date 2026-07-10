"""Strict contracts for local redaction, preview, and upload approval."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from debugmate.contracts import CaseId

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
StrictIndex = Annotated[int, Field(strict=True, ge=0)]
StrictCount = Annotated[int, Field(strict=True, ge=0)]


class StrictPrivacyModel(BaseModel):
    """Reject undeclared fields and implicit type coercion at privacy boundaries."""

    model_config = ConfigDict(strict=True, extra="forbid")


class InputEnvelope(StrictPrivacyModel):
    """Raw local input accepted before any cloud operation is possible."""

    case_id: CaseId
    error_text: str | None = Field(default=None, repr=False)
    screenshot_path: str | None = Field(default=None, repr=False)
    code: str | None = Field(default=None, repr=False)
    environment: dict[str, str] = Field(default_factory=dict, repr=False)

    @model_validator(mode="after")
    def require_primary_input(self) -> Self:
        if not (self.error_text and self.error_text.strip()) and not self.screenshot_path:
            raise ValueError("error_text or screenshot_path is required")
        return self


class SecretKind(StrEnum):
    """Stable marker names used by deterministic text and image redaction."""

    PRIVATE_KEY = "PRIVATE_KEY"
    PASSWORD = "PASSWORD"
    TOKEN = "TOKEN"
    EMAIL = "EMAIL"
    WINDOWS_PATH = "WINDOWS_PATH"
    UNIX_PATH = "UNIX_PATH"
    PRIVATE_HOST = "PRIVATE_HOST"
    USERNAME = "USERNAME"
    HIGH_ENTROPY = "HIGH_ENTROPY"


class SecretCandidate(StrictPrivacyModel):
    """A sensitive span represented without retaining its matched value."""

    kind: SecretKind
    field: str
    start: StrictIndex
    end: StrictIndex
    rule_id: str
    confidence: float = Field(strict=True, ge=0.0, le=1.0)
    match_sha256: Sha256

    @model_validator(mode="after")
    def require_non_empty_span(self) -> Self:
        if self.end <= self.start:
            raise ValueError("candidate end must be greater than start")
        return self


class RedactedFields(StrictPrivacyModel):
    """Only the sanitized values that may be considered for upload."""

    error_text: str | None = None
    code: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    redacted_screenshot_path: str | None = None
    redacted_screenshot_sha256: Sha256 | None = None


class RedactionAudit(StrictPrivacyModel):
    """Value-free aggregate data suitable for logs and evidence bundles."""

    candidate_count: StrictCount
    counts_by_kind: dict[SecretKind, StrictCount] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_consistent_count(self) -> Self:
        if sum(self.counts_by_kind.values()) != self.candidate_count:
            raise ValueError("candidate_count must equal counts_by_kind total")
        return self


class PreviewBundle(StrictPrivacyModel):
    """Deterministic redaction result presented for explicit user confirmation."""

    case_id: CaseId
    redacted: RedactedFields
    candidates: list[SecretCandidate]
    audit: RedactionAudit
    source_hash: Sha256
    preview_hash: Sha256
    rule_version: str
    created_at_utc: datetime

    @field_validator("created_at_utc")
    @classmethod
    def require_utc_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at_utc must be UTC aware")
        return value

    @model_validator(mode="after")
    def require_ordered_consistent_candidates(self) -> Self:
        ordering = [(item.field, item.start, item.end, item.rule_id) for item in self.candidates]
        if ordering != sorted(ordering):
            raise ValueError("candidates must use deterministic field/span ordering")
        if len(self.candidates) != self.audit.candidate_count:
            raise ValueError("audit candidate_count must match candidates")
        actual_counts: dict[SecretKind, int] = {}
        for item in self.candidates:
            actual_counts[item.kind] = actual_counts.get(item.kind, 0) + 1
        if actual_counts != self.audit.counts_by_kind:
            raise ValueError("audit counts_by_kind must match candidates")
        return self


class ApprovedRedactedInput(StrictPrivacyModel):
    """User-approved redacted input and its tamper-evident approval metadata."""

    case_id: CaseId
    redacted: RedactedFields
    preview_hash: Sha256
    approval_id: str
    approval_signature: Sha256
    approved_at_utc: datetime

    @field_validator("approved_at_utc")
    @classmethod
    def require_utc_approved_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("approved_at_utc must be UTC aware")
        return value
