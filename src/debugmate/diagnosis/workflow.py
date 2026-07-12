"""Approval-gated, pausable diagnosis orchestration."""

from __future__ import annotations

import hmac
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import Field

from debugmate.contracts import DiagnosisRecord, EvidenceAnchor, ObservedFact
from debugmate.diagnosis.correction import CorrectionOverlay, apply_correction
from debugmate.diagnosis.extraction import (
    CaseFacts,
    ExtractionRecord,
    SourceKind,
    StrictFrozenModel,
    build_case_facts,
)
from debugmate.diagnosis.generation import GenerationFailed, GenerationRequest
from debugmate.diagnosis.providers import ExtractionProvider
from debugmate.diagnosis.routing import DecisionStage, RoutingDecision, route_case
from debugmate.diagnosis.sufficiency import (
    InsufficientInformation,
    NeedsInformation,
    SufficiencyResult,
    apply_followup_answers,
    evaluate_sufficiency,
)
from debugmate.hashing import (
    UnsafeArtifactPath,
    canonical_json_bytes,
    resolve_artifact_path,
    sha256_bytes,
    sha256_file,
)
from debugmate.privacy.approval import ApprovalInvalid, verify_approval
from debugmate.privacy.models import ApprovedRedactedInput

SCHEMA_VERSION = "1.1.0"
PROMPT_VERSION = "diagnosis-v1"


class RetrievalProvider(Protocol):
    knowledge_build_id: str

    def retrieve(self, facts: CaseFacts, routing: RoutingDecision) -> list[EvidenceAnchor]: ...


class GenerationProvider(Protocol):
    backend_name: str

    def generate(self, request: GenerationRequest) -> object: ...


class WorkflowStatus(StrEnum):
    NEEDS_INFORMATION = "needs_information"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    GENERATION_FAILED = "generation_failed"
    COMPLETED = "completed"


class DiagnosisRunOutcome(StrictFrozenModel):
    status: WorkflowStatus
    backend: str = Field(min_length=1)
    case_id: str
    revision: int = Field(strict=True, ge=0)
    facts_sha256: str
    run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    idempotency_key: str = Field(pattern=r"^idem_[0-9a-f]{32}$")
    completed_stages: list[str]
    extraction: ExtractionRecord | None = None
    facts: CaseFacts
    routing: RoutingDecision
    sufficiency: SufficiencyResult
    questions: list[object] = Field(default_factory=list)
    evidence: list[EvidenceAnchor] = Field(default_factory=list)
    diagnosis: DiagnosisRecord | None = None
    generation_failure: GenerationFailed | None = None


def _observed_facts(facts: CaseFacts) -> list[ObservedFact]:
    observed: list[ObservedFact] = []
    for fact in facts.facts:
        source = fact.source_kinds[0] if fact.source_kinds else SourceKind.USER
        observed.append(
            ObservedFact(
                fact_id=fact.fact_id,
                field_id=fact.field_id.value,
                value=fact.value,
                source_kind=source.value,
                confidence=fact.confidence,
                locator=f"fact:{fact.fact_id}",
            )
        )
    return observed


def _identities(facts: CaseFacts, routing: RoutingDecision, build_id: str) -> tuple[str, str]:
    identity = {
        "facts_sha256": facts.facts_sha256,
        "rule_version": routing.rule_version,
        "knowledge_build_id": build_id,
        "schema_version": SCHEMA_VERSION,
    }
    digest = sha256_bytes(canonical_json_bytes(identity))
    run_digest = sha256_bytes(
        canonical_json_bytes(
            {"case_id": facts.case_id, "revision": facts.revision, "identity": digest}
        )
    )
    return f"idem_{digest[:32]}", f"run_{run_digest[:32]}"


class DiagnosisWorkflow:
    """Verify approval and artifact binding before any workflow stage or provider call."""

    def __init__(
        self,
        *,
        extraction_provider: ExtractionProvider,
        retrieval_provider: RetrievalProvider,
        generator: GenerationProvider,
        approval_key: bytes | None,
        redacted_root: Path,
    ) -> None:
        self._extraction_provider = extraction_provider
        self._retrieval_provider = retrieval_provider
        self._generator = generator
        self._approval_key = approval_key
        self._redacted_root = Path(redacted_root)

    def _verify_entry(self, approved: ApprovedRedactedInput) -> None:
        if self._approval_key is None:
            raise ApprovalInvalid("approval key is not configured")
        verify_approval(approved, self._approval_key)
        redacted = approved.redacted
        if redacted.redacted_screenshot_path is None:
            return
        expected_hash = redacted.redacted_screenshot_sha256
        if expected_hash is None:
            raise ApprovalInvalid("approved screenshot hash is missing")
        try:
            path = resolve_artifact_path(
                self._redacted_root, Path(redacted.redacted_screenshot_path)
            )
        except UnsafeArtifactPath:
            raise ApprovalInvalid("approved screenshot path is unsafe") from None
        if not path.is_file():
            raise ApprovalInvalid("approved redacted screenshot is unavailable")
        if not hmac.compare_digest(sha256_file(path), expected_hash):
            raise ApprovalInvalid("approved redacted screenshot has changed")

    def run(
        self,
        approved: ApprovedRedactedInput,
        *,
        followup_answers: dict[object, str] | None = None,
    ) -> DiagnosisRunOutcome:
        self._verify_entry(approved)
        stages = ["input_approved"]
        extraction = self._extraction_provider.extract(approved)
        stages.append("extracted")
        facts = build_case_facts(extraction)
        stages.append("facts_confirmed")
        return self._from_facts(
            facts,
            stages=stages,
            extraction=extraction,
            followup_answers=followup_answers,
        )

    def _from_facts(
        self,
        facts: CaseFacts,
        *,
        stages: list[str],
        extraction: ExtractionRecord | None,
        followup_answers: dict[object, str] | None = None,
    ) -> DiagnosisRunOutcome:
        provisional = route_case(facts, decision_stage=DecisionStage.PROVISIONAL)
        stages.append("provisional_routed")
        sufficiency = evaluate_sufficiency(facts, provisional, followup_round=0)
        stages.append("sufficiency_checked")
        if isinstance(sufficiency, NeedsInformation) and not followup_answers:
            return self._outcome(
                WorkflowStatus.NEEDS_INFORMATION,
                facts,
                provisional,
                sufficiency,
                stages,
                extraction=extraction,
                questions=list(sufficiency.questions),
            )

        if isinstance(sufficiency, NeedsInformation):
            facts, final = apply_followup_answers(facts, sufficiency, followup_answers or {})
        else:
            final = route_case(facts, decision_stage=DecisionStage.FINAL)
        stages.append("final_routed")

        final_sufficiency = evaluate_sufficiency(
            facts,
            route_case(facts, decision_stage=DecisionStage.PROVISIONAL),
            followup_round=1,
        )
        if isinstance(final_sufficiency, InsufficientInformation):
            return self._outcome(
                WorkflowStatus.INSUFFICIENT_INFORMATION,
                facts,
                final,
                final_sufficiency,
                stages,
                extraction=extraction,
            )

        evidence = self._retrieval_provider.retrieve(facts, final)
        stages.append("retrieved")
        request = GenerationRequest(
            case_id=facts.case_id,
            observed_facts=_observed_facts(facts),
            evidence=evidence,
            routing=final,
            knowledge_build_id=self._retrieval_provider.knowledge_build_id,
            schema_version=SCHEMA_VERSION,
            prompt_version=PROMPT_VERSION,
        )
        generated = self._generator.generate(request)
        stages.append("generated")
        if getattr(generated, "status", None) == "generation_failed":
            return self._outcome(
                WorkflowStatus.GENERATION_FAILED,
                facts,
                final,
                final_sufficiency,
                stages,
                extraction=extraction,
                evidence=evidence,
                generation_failure=generated,
            )
        stages.extend(["validated", "published"])
        return self._outcome(
            WorkflowStatus.COMPLETED,
            facts,
            final,
            final_sufficiency,
            stages,
            extraction=extraction,
            evidence=evidence,
            diagnosis=generated.diagnosis,
        )

    def _outcome(
        self,
        status: WorkflowStatus,
        facts: CaseFacts,
        routing: RoutingDecision,
        sufficiency: SufficiencyResult,
        stages: list[str],
        *,
        extraction: ExtractionRecord | None,
        questions: list[object] | None = None,
        evidence: list[EvidenceAnchor] | None = None,
        diagnosis: DiagnosisRecord | None = None,
        generation_failure: GenerationFailed | None = None,
    ) -> DiagnosisRunOutcome:
        idempotency_key, run_id = _identities(
            facts, routing, self._retrieval_provider.knowledge_build_id
        )
        return DiagnosisRunOutcome(
            status=status,
            backend=self._generator.backend_name,
            case_id=facts.case_id,
            revision=facts.revision,
            facts_sha256=facts.facts_sha256,
            run_id=run_id,
            idempotency_key=idempotency_key,
            completed_stages=list(stages),
            extraction=extraction,
            facts=facts,
            routing=routing,
            sufficiency=sufficiency,
            questions=questions or [],
            evidence=evidence or [],
            diagnosis=diagnosis,
            generation_failure=generation_failure,
        )

    def rerun(
        self, previous: DiagnosisRunOutcome, overlay: CorrectionOverlay
    ) -> DiagnosisRunOutcome:
        previous = DiagnosisRunOutcome.model_validate(previous.model_dump(), strict=True)
        revised = apply_correction(previous.facts, overlay)
        return self._from_facts(
            revised,
            stages=["input_approved", "extracted", "facts_confirmed"],
            extraction=previous.extraction,
        )
