"""Bounded, allowlisted contracts for untrusted Dify workflow data."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from debugmate.contracts import DiagnosisRecord, ObservedFact

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
ReportedMetric = (
    Annotated[int, Field(strict=True, ge=0)]
    | Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
    | Literal["not_reported"]
)


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
    )


class ExecutionBackend(StrEnum):
    DIFY = "dify"
    LOCAL_FALLBACK = "local_fallback"
    REPLAY = "replay"


class DifyAttemptKind(StrEnum):
    UPLOAD = "upload"
    WORKFLOW = "workflow"
    CONTRACT_REPAIR = "contract_repair"


class AttemptStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    UNCERTAIN = "uncertain"
    FAILED = "failed"


class ReceiptStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    UNCERTAIN = "uncertain"
    FAILED = "failed"


class CloudFailureCode(StrEnum):
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    QUOTA = "quota"
    PRE_DISPATCH_TRANSPORT = "pre_dispatch_transport"
    AMBIGUOUS_TIMEOUT = "ambiguous_timeout"
    UPLOAD = "upload"
    WORKFLOW_ENVELOPE = "workflow_envelope"
    DIAGNOSIS_VALIDATION = "diagnosis_validation"
    REPAIR_EXHAUSTION = "repair_exhaustion"
    KNOWLEDGE_READBACK = "knowledge_readback"
    LOCAL_RESULT_COMPOSITION = "local_result_composition"


ExecutionBackendValue = Annotated[ExecutionBackend, Field(strict=False)]
DifyAttemptKindValue = Annotated[DifyAttemptKind, Field(strict=False)]
AttemptStatusValue = Annotated[AttemptStatus, Field(strict=False)]
ReceiptStatusValue = Annotated[ReceiptStatus, Field(strict=False)]
CloudFailureCodeValue = Annotated[CloudFailureCode, Field(strict=False)]


class DifyUsage(StrictFrozenModel):
    total_tokens: ReportedMetric = "not_reported"
    total_steps: ReportedMetric = "not_reported"
    elapsed_time: ReportedMetric = "not_reported"
    total_price: ReportedMetric = "not_reported"


class DifyAttempt(StrictFrozenModel):
    kind: DifyAttemptKindValue
    attempt_fingerprint: Sha256
    status: AttemptStatusValue
    latency_ms: int | Literal["not_reported"] = Field(default="not_reported")

    @model_validator(mode="after")
    def bounded_latency(self) -> DifyAttempt:
        if isinstance(self.latency_ms, bool):
            raise ValueError("attempt latency must be a strict nonnegative integer")
        if isinstance(self.latency_ms, int) and self.latency_ms < 0:
            raise ValueError("attempt latency must be nonnegative")
        return self


class RetrievalHit(StrictFrozenModel):
    chunk_fingerprint: Sha256
    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._:-]{1,127}$")
    source_title: str = Field(min_length=1, max_length=300)
    source_url: HttpUrl
    locator: str = Field(min_length=1, max_length=300)
    content_summary: str = Field(min_length=1, max_length=2000)
    relevance_score: float | Literal["not_reported"] = "not_reported"

    @model_validator(mode="after")
    def bounded_score(self) -> RetrievalHit:
        if isinstance(self.relevance_score, float) and not 0 <= self.relevance_score <= 1:
            raise ValueError("retrieval relevance score must be between zero and one")
        return self


class RetrievalTrace(StrictFrozenModel):
    knowledge_build_id: Sha256
    run_fingerprint: Sha256
    node_fingerprint: Sha256
    hits: list[RetrievalHit] = Field(max_length=4)

    @model_validator(mode="after")
    def unique_hits(self) -> RetrievalTrace:
        identities = [hit.chunk_fingerprint for hit in self.hits]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate retrieval hit fingerprint")
        citations = [(hit.source_id, hit.locator) for hit in self.hits]
        if len(citations) != len(set(citations)):
            raise ValueError("duplicate retrieval source locator")
        return self


class DifyRunContract(StrictFrozenModel):
    schema_version: Literal["1.1.0"]
    prompt_version: str = Field(pattern=r"^[a-z][a-z0-9._-]{2,63}$")
    knowledge_build_id: Sha256
    dsl_semantic_sha256: Sha256


class DifyRunEnvelope(StrictFrozenModel):
    envelope_version: Literal["1.0.0"]
    case_id: str = Field(pattern=r"^case_[0-9a-f]{32}$")
    diagnosis: DiagnosisRecord
    extraction_facts: list[ObservedFact] = Field(max_length=64)
    retrieval_trace: RetrievalTrace
    contract: DifyRunContract

    @model_validator(mode="after")
    def same_run_identity(self) -> DifyRunEnvelope:
        if self.case_id != self.diagnosis.case_id:
            raise ValueError("envelope and diagnosis case identities differ")
        if self.extraction_facts != self.diagnosis.observed_facts:
            raise ValueError("envelope extraction facts differ from diagnosis facts")
        if self.contract.knowledge_build_id != self.retrieval_trace.knowledge_build_id:
            raise ValueError("envelope knowledge build identities differ")
        if any(
            anchor.knowledge_build_id != self.contract.knowledge_build_id
            for anchor in self.diagnosis.evidence
        ):
            raise ValueError("diagnosis evidence does not match the envelope knowledge build")
        return self


class DifyReceipt(StrictFrozenModel):
    receipt_version: Literal["1.0.0"] = "1.0.0"
    receipt_id: Sha256
    case_id: str = Field(pattern=r"^case_[0-9a-f]{32}$")
    preview_hash: Sha256
    backend: ExecutionBackendValue
    status: ReceiptStatusValue
    started_at: datetime
    terminal_at: datetime | None = None
    attempts: tuple[DifyAttempt, ...] = Field(default=(), max_length=3)
    usage: DifyUsage = Field(default_factory=DifyUsage)
    accepted_result_id: str | None = Field(
        default=None, pattern=r"^(?:result|run)_[0-9a-f]{32}$"
    )
    failure_code: CloudFailureCodeValue | None = None
    safe_failure_detail: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def legal_state_shape(self) -> DifyReceipt:
        if self.started_at.tzinfo is None:
            raise ValueError("receipt timestamps must be timezone-aware")
        if self.terminal_at is not None and (
            self.terminal_at.tzinfo is None or self.terminal_at < self.started_at
        ):
            raise ValueError("receipt terminal timestamp is invalid")
        if self.status is ReceiptStatus.STARTED:
            if any(
                value is not None
                for value in (
                    self.terminal_at,
                    self.accepted_result_id,
                    self.failure_code,
                    self.safe_failure_detail,
                )
            ):
                raise ValueError("started receipt cannot contain terminal fields")
        elif self.status is ReceiptStatus.SUCCEEDED:
            if (
                self.terminal_at is None
                or self.accepted_result_id is None
                or self.failure_code is not None
                or self.safe_failure_detail is not None
            ):
                raise ValueError("succeeded receipt requires only terminal result identity")
        elif (
            self.terminal_at is None
            or self.accepted_result_id is not None
            or self.failure_code is None
            or self.safe_failure_detail is None
        ):
            raise ValueError("failed or uncertain receipt requires only a safe failure")
        return self


def _require_sha256(value: str, field: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{field} must be a SHA-256 fingerprint")
    return value


def receipt_identity(approval_identity_fingerprint: str, preview_hash: str) -> str:
    """Derive a non-secret receipt identity without retaining approval material."""

    payload = {
        "approval_identity_fingerprint": _require_sha256(
            approval_identity_fingerprint, "approval identity"
        ),
        "preview_hash": _require_sha256(preview_hash, "preview hash"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def new_started_receipt(
    *,
    case_id: str,
    approval_identity_fingerprint: str,
    preview_hash: str,
    started_at: datetime,
    backend: ExecutionBackend = ExecutionBackend.DIFY,
) -> DifyReceipt:
    """Construct the only legal pre-dispatch receipt shape."""

    return DifyReceipt(
        receipt_id=receipt_identity(approval_identity_fingerprint, preview_hash),
        case_id=case_id,
        preview_hash=preview_hash,
        backend=backend,
        status=ReceiptStatus.STARTED,
        started_at=started_at,
    )
