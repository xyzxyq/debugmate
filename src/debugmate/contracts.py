"""Strict, platform-independent data contracts for DebugMate."""

from __future__ import annotations

import hashlib
import json
import uuid
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.1.0"
CASE_ID_PATTERN = r"^case_[0-9a-f]{32}$"
FACT_ID_PATTERN = r"^fact_[0-9a-f]{32}$"
EVIDENCE_ID_PATTERN = r"^evidence_[0-9a-f]{32}$"
CANDIDATE_ID_PATTERN = r"^candidate_[0-9a-f]{32}$"

CaseId = Annotated[str, Field(pattern=CASE_ID_PATTERN)]
FactId = Annotated[str, Field(pattern=FACT_ID_PATTERN)]
EvidenceId = Annotated[str, Field(pattern=EVIDENCE_ID_PATTERN)]
CandidateId = Annotated[str, Field(pattern=CANDIDATE_ID_PATTERN)]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]


class ErrorCategory(StrEnum):
    """Stable top-level error categories used by the workflow contract."""

    DEPENDENCY_ENVIRONMENT = "dependency_environment"
    PATH_PERMISSION = "path_permission"
    PYTHON_RUNTIME = "python_runtime"
    TENSOR_SHAPE_DTYPE = "tensor_shape_dtype"
    CUDA_MEMORY = "cuda_memory"
    MODEL_LOADING = "model_loading"
    UNKNOWN = "unknown"


class CapabilityStatus(StrEnum):
    """Result states shared by backend capability probes."""

    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_TESTED = "not-tested"


class SourceKind(StrEnum):
    """Trusted provenance category for an observed fact."""

    TEXT = "text"
    OCR = "ocr"
    VLM = "vlm"
    USER = "user"


class ClaimKind(StrEnum):
    """Whether a root-cause claim is evidence-grounded or an inference."""

    GROUNDED = "grounded"
    INFERENCE = "inference"


class SupportType(StrEnum):
    """Semantic relationship between facts and evidence anchors."""

    SUPPORTS = "supports"
    CORROBORATES = "corroborates"


# JSON enum values are strings by definition. Keep primitive fields strict while
# allowing their exact string representation at Python dictionary boundaries.
ErrorCategoryValue = Annotated[ErrorCategory, Field(strict=False)]
SourceKindValue = Annotated[SourceKind, Field(strict=False)]
ClaimKindValue = Annotated[ClaimKind, Field(strict=False)]
SupportTypeValue = Annotated[SupportType, Field(strict=False)]


class StrictRecord(BaseModel):
    """Base configuration for all externally serialized records."""

    model_config = ConfigDict(strict=True, extra="forbid")


# Frozen 1.0.0 models. These deliberately retain the original serialized shape.
class RootCauseCandidateV100(StrictRecord):
    """Legacy root-cause candidate with text-only support."""

    cause: str
    supporting_facts: list[str]
    confidence: Confidence


class CitationV100(StrictRecord):
    """Legacy traceable source reference."""

    source_id: str
    title: str
    url: str
    locator: str
    excerpt: str


class CommandStepV100(StrictRecord):
    """Legacy command recommendation stored as inert data."""

    command: str
    platform: str
    impact: str
    expected_result: str
    rollback: str


class DiagnosisRecordV100(StrictRecord):
    """Frozen loader for the DiagnosisRecord 1.0.0 wire contract."""

    schema_version: Literal["1.0.0"]
    case_id: CaseId
    category: ErrorCategoryValue
    observed_facts: list[str]
    root_cause_candidates: list[RootCauseCandidateV100]
    missing_information: list[str]
    checks: list[CommandStepV100]
    fixes: list[CommandStepV100]
    verification_steps: list[CommandStepV100]
    confidence: Confidence
    limitations: list[str]
    recap_text: str
    citations: list[CitationV100]


class ObservedFact(StrictRecord):
    """One normalized observation with stable provenance."""

    fact_id: FactId
    field_id: str
    value: str
    source_kind: SourceKindValue
    confidence: Confidence
    locator: str


class EvidenceAnchor(StrictRecord):
    """A bounded, attributable knowledge-retrieval result."""

    evidence_id: EvidenceId
    chunk_id: str
    content_summary: str
    source_id: str
    source_url: str
    locator: str
    relevance_score: Confidence
    knowledge_build_id: str


class SupportLink(StrictRecord):
    """Explicit relationship between observed facts and evidence."""

    fact_ids: list[FactId]
    evidence_ids: list[EvidenceId]
    support_type: SupportTypeValue


class RootCauseCandidate(StrictRecord):
    """One possible cause with explicit support and uncertainty semantics."""

    candidate_id: CandidateId
    cause: str
    claim_kind: ClaimKindValue
    fact_ids: list[FactId]
    evidence_ids: list[EvidenceId]
    confidence: Confidence
    applicability: str
    counterevidence_or_limits: str

    @model_validator(mode="after")
    def require_explained_uncertainty(self) -> RootCauseCandidate:
        if not self.applicability.strip():
            raise ValueError("applicability must not be blank")
        if not self.counterevidence_or_limits.strip():
            raise ValueError("counterevidence_or_limits must not be blank")
        if len(self.fact_ids) != len(set(self.fact_ids)):
            raise ValueError("duplicate fact ID in root-cause candidate")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("duplicate evidence ID in root-cause candidate")
        if self.claim_kind is ClaimKind.GROUNDED and (not self.fact_ids or not self.evidence_ids):
            raise ValueError("grounded candidate requires fact and evidence IDs")
        return self


class CommandStep(StrictRecord):
    """A command recommendation stored as data and never executed here."""

    command: str
    platform: str
    impact: str
    expected_result: str
    rollback: str


class DiagnosisRecord(StrictRecord):
    """Current single source of truth for one diagnosis."""

    schema_version: Literal["1.1.0"]
    case_id: CaseId
    category: ErrorCategoryValue
    observed_facts: list[ObservedFact]
    evidence: list[EvidenceAnchor]
    support_links: list[SupportLink]
    root_cause_candidates: list[RootCauseCandidate]
    missing_information: list[str]
    checks: list[CommandStep]
    fixes: list[CommandStep]
    verification_steps: list[CommandStep]
    confidence: Confidence
    limitations: list[str]
    recap_text: str

    @model_validator(mode="after")
    def validate_support_graph(self) -> DiagnosisRecord:
        fact_ids = [fact.fact_id for fact in self.observed_facts]
        evidence_ids = [anchor.evidence_id for anchor in self.evidence]
        candidate_ids = [candidate.candidate_id for candidate in self.root_cause_candidates]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("duplicate fact ID")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("duplicate evidence ID")
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("duplicate candidate ID")

        known_facts = set(fact_ids)
        known_evidence = set(evidence_ids)
        for link in self.support_links:
            if len(link.fact_ids) != len(set(link.fact_ids)):
                raise ValueError("duplicate fact ID in support link")
            if len(link.evidence_ids) != len(set(link.evidence_ids)):
                raise ValueError("duplicate evidence ID in support link")
            if not link.fact_ids or not link.evidence_ids:
                raise ValueError("support link requires facts and evidence")
            if unknown := set(link.fact_ids) - known_facts:
                raise ValueError(f"support link references unknown fact IDs: {sorted(unknown)}")
            if unknown := set(link.evidence_ids) - known_evidence:
                raise ValueError(f"support link references unknown evidence IDs: {sorted(unknown)}")

        for candidate in self.root_cause_candidates:
            if unknown := set(candidate.fact_ids) - known_facts:
                raise ValueError(f"candidate references unknown fact IDs: {sorted(unknown)}")
            if unknown := set(candidate.evidence_ids) - known_evidence:
                raise ValueError(f"candidate references unknown evidence IDs: {sorted(unknown)}")
            if candidate.claim_kind is ClaimKind.GROUNDED:
                has_support = any(
                    set(candidate.fact_ids).intersection(link.fact_ids)
                    and set(candidate.evidence_ids).intersection(link.evidence_ids)
                    for link in self.support_links
                )
                if not has_support:
                    raise ValueError("grounded candidate requires a matching support link")
        return self


# Kept as a compatibility import for callers that explicitly need the old citation shape.
Citation = CitationV100


def new_case_id() -> str:
    """Return an opaque case identifier without time or user information."""

    return f"case_{uuid.uuid4().hex}"


def diagnosis_schema() -> dict[str, object]:
    """Return the generated JSON Schema for the current diagnosis contract."""

    return DiagnosisRecord.model_json_schema()


def schema_sha256() -> str:
    """Return a deterministic SHA-256 for the current generated JSON Schema."""

    canonical = json.dumps(
        diagnosis_schema(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
