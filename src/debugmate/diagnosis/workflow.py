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
WORKFLOW_VERSION = "diagnosis-workflow-v1"


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
    inherited_stages: list[str] = Field(default_factory=list)
    source_run_id: str | None = Field(default=None, pattern=r"^run_[0-9a-f]{32}$")
    extraction: ExtractionRecord | None = None
    facts: CaseFacts
    routing: RoutingDecision
    sufficiency: SufficiencyResult
    questions: list[object] = Field(default_factory=list)
    evidence: list[EvidenceAnchor] = Field(default_factory=list)
    diagnosis: DiagnosisRecord | None = None
    generation_failure: GenerationFailed | None = None
    knowledge_build_id: str
    schema_version: str = SCHEMA_VERSION
    prompt_version: str = PROMPT_VERSION
    workflow_version: str = WORKFLOW_VERSION
    generation_attempts: int = Field(strict=True, ge=0)
    transport_attempts: int = Field(strict=True, ge=0)


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


def derive_run_identities(
    facts: CaseFacts, routing: RoutingDecision, build_id: str
) -> tuple[str, str]:
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


_STAGES_BY_STATUS: dict[WorkflowStatus, list[str]] = {
    WorkflowStatus.NEEDS_INFORMATION: [
        "input_approved",
        "extracted",
        "facts_confirmed",
        "provisional_routed",
        "sufficiency_checked",
    ],
    WorkflowStatus.INSUFFICIENT_INFORMATION: [
        "input_approved",
        "extracted",
        "facts_confirmed",
        "provisional_routed",
        "sufficiency_checked",
        "final_routed",
    ],
    WorkflowStatus.GENERATION_FAILED: [
        "input_approved",
        "extracted",
        "facts_confirmed",
        "provisional_routed",
        "sufficiency_checked",
        "final_routed",
        "retrieved",
        "generated",
    ],
    WorkflowStatus.COMPLETED: [
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
}


def validate_diagnosis_outcome(outcome: DiagnosisRunOutcome) -> None:
    """Validate public workflow identity, versions, and the exact legal stage path."""

    expected_versions = (SCHEMA_VERSION, PROMPT_VERSION, WORKFLOW_VERSION)
    actual_versions = (
        outcome.schema_version,
        outcome.prompt_version,
        outcome.workflow_version,
    )
    if actual_versions != expected_versions:
        raise ValueError("outcome version metadata does not match publisher contract")
    expected_idempotency, expected_run = derive_run_identities(
        outcome.facts, outcome.routing, outcome.knowledge_build_id
    )
    if not hmac.compare_digest(outcome.idempotency_key, expected_idempotency):
        raise ValueError("outcome idempotency_key does not match immutable workflow state")
    if not hmac.compare_digest(outcome.run_id, expected_run):
        raise ValueError("outcome run_id does not match immutable workflow state")
    expected_stages = _STAGES_BY_STATUS[outcome.status]
    if outcome.inherited_stages:
        if outcome.inherited_stages != expected_stages[:3] or outcome.source_run_id is None:
            raise ValueError("outcome inherited stages require valid correction lineage")
        expected_stages = ["facts_corrected", *expected_stages[3:]]
    elif outcome.source_run_id is not None:
        raise ValueError("outcome source run requires inherited stages")
    if outcome.completed_stages != expected_stages:
        raise ValueError("outcome completed_stages do not match its status")
    if outcome.case_id != outcome.facts.case_id:
        raise ValueError("outcome case ID does not match immutable facts")
    if outcome.extraction is not None and outcome.extraction.case_id != outcome.case_id:
        raise ValueError("outcome extraction does not match its case")
    if outcome.status is WorkflowStatus.NEEDS_INFORMATION:
        if not isinstance(outcome.sufficiency, NeedsInformation) or not outcome.questions:
            raise ValueError("needs-information outcome requires issued questions")
        if outcome.evidence or outcome.diagnosis or outcome.generation_failure:
            raise ValueError("needs-information outcome contains downstream fields")
    elif outcome.status is WorkflowStatus.INSUFFICIENT_INFORMATION:
        if not isinstance(outcome.sufficiency, InsufficientInformation):
            raise ValueError("insufficient-information outcome requires final insufficiency")
        if outcome.questions or outcome.evidence or outcome.diagnosis or outcome.generation_failure:
            raise ValueError("insufficient-information outcome contains downstream fields")
    elif outcome.status is WorkflowStatus.GENERATION_FAILED:
        if outcome.generation_failure is None or outcome.diagnosis is not None:
            raise ValueError("generation-failed outcome requires only a typed failure")
        if outcome.questions:
            raise ValueError("generation-failed outcome cannot retain questions")
    elif outcome.diagnosis is None or outcome.generation_failure is not None or outcome.questions:
        raise ValueError("completed outcome requires only a validated diagnosis")


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
        inherited_stages: list[str] | None = None,
        source_run_id: str | None = None,
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
                inherited_stages=inherited_stages,
                source_run_id=source_run_id,
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
                inherited_stages=inherited_stages,
                source_run_id=source_run_id,
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
                generation_attempts=generated.generation_attempts,
                transport_attempts=getattr(generated, "transport_attempts", 0),
                inherited_stages=inherited_stages,
                source_run_id=source_run_id,
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
            generation_attempts=generated.generation_attempts,
            transport_attempts=getattr(generated, "transport_attempts", 0),
            inherited_stages=inherited_stages,
            source_run_id=source_run_id,
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
        generation_attempts: int = 0,
        transport_attempts: int = 0,
        inherited_stages: list[str] | None = None,
        source_run_id: str | None = None,
    ) -> DiagnosisRunOutcome:
        idempotency_key, run_id = derive_run_identities(
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
            inherited_stages=list(inherited_stages or []),
            source_run_id=source_run_id,
            extraction=extraction,
            facts=facts,
            routing=routing,
            sufficiency=sufficiency,
            questions=questions or [],
            evidence=evidence or [],
            diagnosis=diagnosis,
            generation_failure=generation_failure,
            knowledge_build_id=self._retrieval_provider.knowledge_build_id,
            generation_attempts=generation_attempts,
            transport_attempts=transport_attempts,
        )

    def publish(self, outcome: DiagnosisRunOutcome, output_root: Path) -> Path:
        """Publish an already produced outcome through the fail-closed evidence boundary."""

        from debugmate.evidence import publish_diagnosis_evidence

        return publish_diagnosis_evidence(outcome, output_root)

    def rerun(
        self, previous: DiagnosisRunOutcome, overlay: CorrectionOverlay
    ) -> DiagnosisRunOutcome:
        previous = DiagnosisRunOutcome.model_validate(previous.model_dump(), strict=True)
        validate_diagnosis_outcome(previous)
        revised = apply_correction(previous.facts, overlay)
        return self._from_facts(
            revised,
            stages=["facts_corrected"],
            extraction=previous.extraction,
            inherited_stages=["input_approved", "extracted", "facts_confirmed"],
            source_run_id=previous.run_id,
        )
