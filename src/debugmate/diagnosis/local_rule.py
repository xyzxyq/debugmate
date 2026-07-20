"""Deterministic generation from the committed local-rule snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from debugmate.contracts import (
    ClaimKind,
    CommandPlatform,
    CommandStep,
    DiagnosisRecord,
    ErrorCategory,
    RootCauseCandidate,
    SupportLink,
    SupportType,
)
from debugmate.diagnosis.extraction import FieldId
from debugmate.diagnosis.generation import (
    GenerationCompleted,
    GenerationRequest,
)
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.knowledge.local_rule import LocalRuleSnapshot


class LocalRuleGenerationError(ValueError):
    """Value-free rejection when a request is outside the one local rule."""


def _request_id(prefix: str, request: GenerationRequest) -> str:
    digest = sha256_bytes(canonical_json_bytes(request.model_dump(mode="json")))
    return f"{prefix}_{digest[:32]}"


@dataclass(frozen=True, slots=True)
class LocalRuleGenerationProvider:
    """Build one strict diagnosis without a model, fixture, or network call."""

    snapshot: LocalRuleSnapshot
    backend_name = "local-rule-v1"

    def generate(self, request: GenerationRequest) -> GenerationCompleted:
        checked = GenerationRequest.model_validate(request.model_dump(), strict=True)
        rule = self.snapshot.rule
        exception_facts = [
            fact
            for fact in checked.observed_facts
            if fact.field_id == FieldId.EXCEPTION_TYPE.value
            and fact.value.rsplit(".", 1)[-1] == rule.match.exception_type
        ]
        expected_evidence = rule.retrieval
        matching_evidence = [
            anchor
            for anchor in checked.evidence
            if anchor.chunk_id == expected_evidence.chunk_id
            and anchor.content_summary == expected_evidence.content_summary
            and anchor.source_id == expected_evidence.source_id
            and anchor.source_url == expected_evidence.source_url
            and anchor.locator == expected_evidence.locator
            and anchor.relevance_score == expected_evidence.relevance_score
            and anchor.knowledge_build_id == self.snapshot.knowledge_build_id
        ]
        if (
            checked.routing.category is not ErrorCategory.DEPENDENCY_ENVIRONMENT
            or checked.knowledge_build_id != self.snapshot.knowledge_build_id
            or len(exception_facts) != 1
            or len(checked.evidence) != 1
            or len(matching_evidence) != 1
        ):
            raise LocalRuleGenerationError("local_rule_no_match") from None

        fact_ids = [fact.fact_id for fact in checked.observed_facts]
        evidence_ids = [anchor.evidence_id for anchor in checked.evidence]
        candidate_id = _request_id("candidate", checked)
        commands = [
            CommandStep(
                command=command.command,
                platform=CommandPlatform(command.platform),
                impact=command.impact,
                expected_result=command.expected_result,
                rollback=command.rollback,
            )
            for command in rule.response.commands
        ]
        record = DiagnosisRecord.model_validate(
            {
                "schema_version": checked.schema_version,
                "case_id": checked.case_id,
                "category": checked.routing.category,
                "observed_facts": checked.observed_facts,
                "evidence": checked.evidence,
                "support_links": [
                    SupportLink(
                        fact_ids=fact_ids,
                        evidence_ids=evidence_ids,
                        support_type=SupportType.SUPPORTS,
                    )
                ],
                "root_cause_candidates": [
                    RootCauseCandidate(
                        candidate_id=candidate_id,
                        cause=rule.response.diagnosis,
                        claim_kind=ClaimKind.GROUNDED,
                        fact_ids=fact_ids,
                        evidence_ids=evidence_ids,
                        confidence=0.9,
                        applicability=rule.response.diagnosis,
                        counterevidence_or_limits=rule.response.diagnosis,
                    )
                ],
                "missing_information": [],
                "checks": commands,
                "fixes": [],
                "verification_steps": commands,
                "confidence": 0.9,
                "limitations": [rule.response.diagnosis],
                "recap_text": rule.response.diagnosis,
            },
            strict=True,
        )
        return GenerationCompleted(
            diagnosis=record,
            generation_attempts=1,
            run_ids=[f"local-rule:{rule.rule_version}"],
        )
