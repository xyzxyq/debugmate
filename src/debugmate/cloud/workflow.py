"""Consent-bound live Dify orchestration with strict local publication authority."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from debugmate.adapters.base import CandidateRunResult
from debugmate.adapters.dify import DifyAmbiguousTransportError, DifyError
from debugmate.cloud.contracts import (
    AttemptStatus,
    CloudFailureCode,
    DifyAttempt,
    DifyAttemptKind,
    DifyReceipt,
    DifyRunEnvelope,
    ReceiptStatus,
    new_started_receipt,
)
from debugmate.cloud.receipts import DifyReceiptStore, ReceiptStoreError
from debugmate.contracts import ObservedFact
from debugmate.diagnosis.evidence_binding import bind_retrieval_evidence
from debugmate.diagnosis.extraction import (
    ExtractionRecord,
    FieldId,
    SourceKind,
    TextLocator,
    build_case_facts,
    extraction_id_for,
    fact_id_for,
    make_candidate,
)
from debugmate.diagnosis.generation import DiagnosisGenerator, GenerationRequest
from debugmate.diagnosis.routing import DecisionStage, route_case
from debugmate.diagnosis.sufficiency import Ready, evaluate_sufficiency
from debugmate.diagnosis.workflow import (
    DiagnosisRunOutcome,
    WorkflowStatus,
    derive_run_identities,
    validate_diagnosis_outcome,
)
from debugmate.gateway import CloudDispatchResult, CloudGateway
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.knowledge.retrieval import RetrievalHit, RetrievalTrace
from debugmate.knowledge.sync import DifyReadbackAttestation
from debugmate.privacy.approval import verify_approval
from debugmate.privacy.models import ApprovedRedactedInput

RETRIEVAL_SANITIZER_FINGERPRINT = sha256_bytes(
    b"debugmate-direct-retrieval-sanitizer-v1"
)


class LiveGateway(Protocol):
    def verify(self, approved: ApprovedRedactedInput) -> None: ...

    def run(self, approved: ApprovedRedactedInput) -> CandidateRunResult: ...

    def repair(self, inputs: dict[str, object]) -> CandidateRunResult: ...


class CloudWorkflowError(RuntimeError):
    """Safe typed terminal error that never retains a provider exception."""

    def __init__(self, code: str, *, receipt_status: ReceiptStatus | None = None) -> None:
        self.code = code
        self.receipt_status = receipt_status
        super().__init__(code)


class _WorkflowEnvelopeInvalid(ValueError):
    """Provider provenance or envelope contract is not locally authoritative."""


class _RepairBackend:
    def __init__(self, gateway: LiveGateway) -> None:
        self._gateway = gateway

    def run_workflow(self, inputs: dict[str, object], user: str) -> CandidateRunResult:
        del user
        return self._gateway.repair(inputs)


def _attempt(kind: DifyAttemptKind, identity: str, status: AttemptStatus) -> DifyAttempt:
    return DifyAttempt(
        kind=kind,
        attempt_fingerprint=hashlib.sha256(identity.encode("utf-8")).hexdigest(),
        status=status,
    )


def _approval_fingerprint(approved: ApprovedRedactedInput) -> str:
    return hashlib.sha256(approved.approval_signature.encode("ascii")).hexdigest()


def _strict_manifest(value: Path | dict[str, object]) -> dict[str, object]:
    if isinstance(value, Path):
        path = value / "manifest.json" if value.is_dir() else value
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(json.dumps(value, ensure_ascii=False))
    if not isinstance(payload, dict):
        raise ValueError("knowledge manifest is invalid")
    sources = payload.get("sources")
    if not isinstance(sources, list) or len(sources) != 17:
        raise ValueError("exactly 17 sealed knowledge sources are required")
    return payload


def _extraction_from_facts(case_id: str, observed: list[ObservedFact]) -> ExtractionRecord:
    candidates = []
    cursor = 0
    identities: set[tuple[FieldId, str]] = set()
    for item in observed:
        field_id = FieldId(item.field_id)
        if item.fact_id != fact_id_for(field_id, item.value):
            raise ValueError("provider fact identity is not canonical")
        identity = (field_id, item.value)
        if identity in identities:
            raise ValueError("provider facts contain duplicates")
        identities.add(identity)
        locator = TextLocator(
            input_field="error_text", start=cursor, end=cursor + max(1, len(item.value))
        )
        candidates.append(
            make_candidate(
                field_id=field_id,
                value=item.value,
                source_kind=SourceKind.TEXT,
                confidence=item.confidence,
                locator=locator,
            )
        )
        cursor = locator.end + 1
    candidates.sort(key=lambda item: item.candidate_id)
    source_hashes = {
        "provider_facts": sha256_bytes(
            canonical_json_bytes([item.model_dump(mode="json") for item in observed])
        )
    }
    return ExtractionRecord(
        case_id=case_id,
        extraction_id=extraction_id_for(case_id, source_hashes, candidates),
        source_hashes=source_hashes,
        candidates=candidates,
    )


class DifyLiveWorkflow:
    """Turn one approved redacted input into one strict same-run Dify outcome."""

    def __init__(
        self,
        *,
        gateway: LiveGateway | CloudGateway,
        receipt_store: DifyReceiptStore,
        approval_key: bytes,
        build_manifest: Path | dict[str, object],
        readback_attestation: DifyReadbackAttestation,
        expected_dsl_semantic_sha256: str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(receipt_store, DifyReceiptStore):
            raise TypeError("DifyLiveWorkflow requires DifyReceiptStore")
        self._gateway = gateway
        self._receipts = receipt_store
        self._approval_key = approval_key
        self._manifest = _strict_manifest(build_manifest)
        self._attestation = DifyReadbackAttestation.model_validate(
            readback_attestation.model_dump(), strict=True
        )
        if not isinstance(expected_dsl_semantic_sha256, str) or len(
            expected_dsl_semantic_sha256
        ) != 64:
            raise ValueError("expected DSL semantic identity is invalid")
        self._expected_dsl_semantic_sha256 = expected_dsl_semantic_sha256
        self._clock = clock or (lambda: datetime.now(UTC))
        if self._manifest.get("build_id") != self._attestation.knowledge_build_id:
            raise ValueError("knowledge readback does not match sealed manifest")

    def _finish_failure(
        self,
        receipt: DifyReceipt,
        *,
        status: ReceiptStatus,
        code: CloudFailureCode,
        attempts: tuple[DifyAttempt, ...],
    ) -> CloudWorkflowError:
        self._receipts.finish(
            receipt.receipt_id,
            status=status,
            terminal_at=self._clock(),
            attempts=attempts,
            failure_code=code,
            safe_failure_detail=code.value,
        )
        return CloudWorkflowError(code.value, receipt_status=status)

    def _validate_envelope(self, approved: ApprovedRedactedInput, result: CandidateRunResult):
        if result.backend != "dify" or result.run_envelope is None:
            raise ValueError("workflow envelope is missing")
        if (
            result.run_envelope.contract.knowledge_build_id
            != self._attestation.knowledge_build_id
        ):
            raise LookupError("knowledge readback differs")
        envelope = DifyRunEnvelope.model_validate(
            result.run_envelope.model_dump(), strict=True
        )
        if envelope.case_id != approved.case_id:
            raise ValueError("workflow case identity differs")
        if (
            envelope.contract.schema_version != "1.1.0"
            or envelope.contract.prompt_version != "diagnosis-v1"
        ):
            raise ValueError("workflow contract version differs")
        if not hmac.compare_digest(
            envelope.contract.dsl_semantic_sha256,
            self._expected_dsl_semantic_sha256,
        ):
            raise _WorkflowEnvelopeInvalid("workflow DSL semantic identity differs")
        extraction = _extraction_from_facts(envelope.case_id, envelope.extraction_facts)
        facts = build_case_facts(extraction)
        fact_core = {
            item.fact_id: (item.field_id, item.value, item.confidence)
            for item in envelope.extraction_facts
        }
        if {
            item.fact_id: (item.field_id.value, item.value, item.confidence)
            for item in facts.facts
        } != fact_core:
            raise ValueError("provider facts do not map to strict local facts")

        cloud_trace = envelope.retrieval_trace
        expected_run_fingerprint = sha256_bytes(
            canonical_json_bytes(
                {
                    "case_id": envelope.case_id,
                    "hits": [
                        hit.model_dump(mode="json") for hit in cloud_trace.hits
                    ],
                }
            )
        )
        if not hmac.compare_digest(
            cloud_trace.run_fingerprint, expected_run_fingerprint
        ):
            raise _WorkflowEnvelopeInvalid("retrieval run fingerprint differs")
        if not hmac.compare_digest(
            cloud_trace.node_fingerprint, RETRIEVAL_SANITIZER_FINGERPRINT
        ):
            raise _WorkflowEnvelopeInvalid("retrieval sanitizer identity differs")
        direct_trace = RetrievalTrace(
            case_id=envelope.case_id,
            query_sha256=sha256_bytes(canonical_json_bytes(fact_core)),
            knowledge_build_id=cloud_trace.knowledge_build_id,
            retrieved_at_utc=self._clock(),
            hits=[
                RetrievalHit(
                    chunk_id=hit.chunk_fingerprint,
                    content_summary=hit.content_summary,
                    source_id=hit.source_id,
                    source_url=str(hit.source_url),
                    locator=hit.locator,
                    relevance_score=(
                        hit.relevance_score
                        if isinstance(hit.relevance_score, float)
                        else 0.0
                    ),
                )
                for hit in cloud_trace.hits
            ],
        )
        evidence = bind_retrieval_evidence(
            direct_trace,
            case_id=envelope.case_id,
            expected_build_id=self._attestation.knowledge_build_id,
            build_manifest=self._manifest,
        )
        provisional = route_case(facts, decision_stage=DecisionStage.PROVISIONAL)
        routing = route_case(facts, decision_stage=DecisionStage.FINAL)
        sufficiency = evaluate_sufficiency(facts, provisional, followup_round=1)
        if not isinstance(sufficiency, Ready):
            raise ValueError("provider facts are insufficient for a completed diagnosis")
        return envelope, extraction, facts, evidence, routing, sufficiency

    def run(self, approved: ApprovedRedactedInput) -> DiagnosisRunOutcome:
        if not isinstance(approved, ApprovedRedactedInput):
            raise TypeError("DifyLiveWorkflow accepts only ApprovedRedactedInput")
        now = self._clock()
        verify_approval(approved, self._approval_key, now=now)
        self._gateway.verify(approved)
        started = new_started_receipt(
            case_id=approved.case_id,
            approval_identity_fingerprint=_approval_fingerprint(approved),
            preview_hash=approved.preview_hash,
            started_at=now,
        )
        try:
            receipt = self._receipts.begin(started)
        except ReceiptStoreError:
            raise CloudWorkflowError("duplicate") from None

        attempts: list[DifyAttempt] = []
        try:
            if isinstance(self._gateway, CloudGateway):
                dispatch = self._gateway.run_live(approved)
                if not isinstance(dispatch, CloudDispatchResult):
                    raise TypeError("cloud dispatch result is invalid")
                primary = dispatch.candidate
                if dispatch.upload_fingerprint is not None:
                    attempts.append(
                        DifyAttempt(
                            kind=DifyAttemptKind.UPLOAD,
                            attempt_fingerprint=dispatch.upload_fingerprint,
                            status=AttemptStatus.SUCCEEDED,
                        )
                    )
            else:
                primary = self._gateway.run(approved)
            attempts.append(
                _attempt(DifyAttemptKind.WORKFLOW, primary.run_id, AttemptStatus.SUCCEEDED)
            )
        except DifyAmbiguousTransportError:
            attempts.append(
                _attempt(
                    DifyAttemptKind.WORKFLOW,
                    receipt.receipt_id + ":workflow",
                    AttemptStatus.UNCERTAIN,
                )
            )
            raise self._finish_failure(
                receipt,
                status=ReceiptStatus.UNCERTAIN,
                code=CloudFailureCode.AMBIGUOUS_TIMEOUT,
                attempts=tuple(attempts),
            ) from None
        except DifyError as error:
            code = CloudFailureCode(error.code)
            failed_kind = (
                DifyAttemptKind.UPLOAD
                if code is CloudFailureCode.UPLOAD
                else DifyAttemptKind.WORKFLOW
            )
            attempts.append(
                _attempt(
                    failed_kind,
                    receipt.receipt_id + f":{failed_kind.value}",
                    AttemptStatus.FAILED,
                )
            )
            raise self._finish_failure(
                receipt,
                status=ReceiptStatus.FAILED,
                code=code,
                attempts=tuple(attempts),
            ) from None

        try:
            envelope, extraction, facts, evidence, routing, sufficiency = (
                self._validate_envelope(approved, primary)
            )
            request = GenerationRequest(
                case_id=envelope.case_id,
                observed_facts=envelope.extraction_facts,
                evidence=evidence,
                routing=routing,
                knowledge_build_id=envelope.contract.knowledge_build_id,
                schema_version="1.1.0",
                prompt_version="diagnosis-v1",
            )
            generated = DiagnosisGenerator(_RepairBackend(self._gateway)).generate(
                request, initial_candidate=primary
            )
            if generated.status != "completed":
                failure = (
                    CloudFailureCode.REPAIR_EXHAUSTION
                    if generated.generation_attempts > 1
                    else CloudFailureCode.DIAGNOSIS_VALIDATION
                )
                if generated.generation_attempts > 1:
                    attempts.append(
                        _attempt(
                            DifyAttemptKind.CONTRACT_REPAIR,
                            generated.run_ids[-1],
                            AttemptStatus.FAILED,
                        )
                    )
                raise self._finish_failure(
                    receipt,
                    status=ReceiptStatus.FAILED,
                    code=failure,
                    attempts=tuple(attempts),
                )
            if generated.generation_attempts > 1:
                attempts.append(
                    _attempt(
                        DifyAttemptKind.CONTRACT_REPAIR,
                        generated.run_ids[-1],
                        AttemptStatus.SUCCEEDED,
                    )
                )
            idempotency_key, run_id = derive_run_identities(
                facts, routing, envelope.contract.knowledge_build_id
            )
            outcome = DiagnosisRunOutcome(
                status=WorkflowStatus.COMPLETED,
                execution_backend="dify",
                backend="dify",
                case_id=facts.case_id,
                revision=facts.revision,
                facts_sha256=facts.facts_sha256,
                run_id=run_id,
                idempotency_key=idempotency_key,
                completed_stages=[
                    "input_approved",
                    "extracted",
                    "facts_confirmed",
                    "provisional_routed",
                    "sufficiency_checked",
                    "final_routed",
                    "retrieved",
                    "generated",
                    "validated",
                    "published",
                ],
                extraction=extraction,
                facts=facts,
                routing=routing,
                sufficiency=sufficiency,
                evidence=evidence,
                diagnosis=generated.diagnosis,
                knowledge_build_id=envelope.contract.knowledge_build_id,
                generation_attempts=generated.generation_attempts,
                transport_attempts=1,
            )
            validate_diagnosis_outcome(outcome)
        except CloudWorkflowError:
            raise
        except LookupError:
            raise self._finish_failure(
                receipt,
                status=ReceiptStatus.FAILED,
                code=CloudFailureCode.KNOWLEDGE_READBACK,
                attempts=tuple(attempts),
            ) from None
        except _WorkflowEnvelopeInvalid:
            raise self._finish_failure(
                receipt,
                status=ReceiptStatus.FAILED,
                code=CloudFailureCode.WORKFLOW_ENVELOPE,
                attempts=tuple(attempts),
            ) from None
        except Exception:
            raise self._finish_failure(
                receipt,
                status=ReceiptStatus.FAILED,
                code=CloudFailureCode.DIAGNOSIS_VALIDATION,
                attempts=tuple(attempts),
            ) from None

        self._receipts.finish(
            receipt.receipt_id,
            status=ReceiptStatus.SUCCEEDED,
            terminal_at=self._clock(),
            attempts=tuple(attempts),
            usage=primary.usage,
            accepted_result_id=outcome.run_id,
        )
        return outcome
