"""Local publication authority for untrusted diagnosis candidates."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from debugmate.adapters.base import CandidateBackend
from debugmate.contracts import (
    CaseId,
    DiagnosisRecord,
    EvidenceAnchor,
    ObservedFact,
)
from debugmate.diagnosis.routing import DecisionStage, RoutingDecision
from debugmate.privacy.models import Sha256
from debugmate.privacy.output_scan import UnsafeExport, assert_export_safe

MAX_REPAIR_ATTEMPTS = 1


class StrictGenerationModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class GenerationRequest(StrictGenerationModel):
    """Validated local context allowed to cross the candidate-generation port."""

    case_id: CaseId
    observed_facts: list[ObservedFact]
    evidence: list[EvidenceAnchor]
    routing: RoutingDecision
    knowledge_build_id: Sha256
    schema_version: Literal["1.1.0"]
    prompt_version: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def require_final_bound_context(self) -> Self:
        if self.routing.decision_stage is not DecisionStage.FINAL:
            raise ValueError("generation requires a final routing decision")
        fact_ids = [fact.fact_id for fact in self.observed_facts]
        evidence_ids = [anchor.evidence_id for anchor in self.evidence]
        if not fact_ids or len(fact_ids) != len(set(fact_ids)):
            raise ValueError("generation facts must be nonempty and unique")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("generation evidence IDs must be unique")
        if any(
            anchor.knowledge_build_id != self.knowledge_build_id for anchor in self.evidence
        ):
            raise ValueError("generation evidence does not match the expected knowledge build")
        return self

    @property
    def fact_ids(self) -> tuple[str, ...]:
        return tuple(fact.fact_id for fact in self.observed_facts)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(anchor.evidence_id for anchor in self.evidence)


class IssueCode(StrEnum):
    JSON_PARSE_FAILED = "json_parse_failed"
    SCHEMA_INVALID = "schema_invalid"
    CASE_ID_MISMATCH = "case_id_mismatch"
    ROUTING_MISMATCH = "routing_mismatch"
    FACT_SET_MISMATCH = "fact_set_mismatch"
    EVIDENCE_SET_MISMATCH = "evidence_set_mismatch"
    KNOWLEDGE_BUILD_MISMATCH = "knowledge_build_mismatch"
    UNSAFE_COMMAND = "unsafe_command"
    PRIVACY_UNSAFE = "privacy_unsafe"


IssueCodeValue = Annotated[IssueCode, Field(strict=False)]


class GenerationIssue(StrictGenerationModel):
    code: IssueCodeValue
    pointer: str = Field(pattern=r"^(?:|(?:/(?:[^~/]|~[01])*)+)$")


class GenerationCompleted(StrictGenerationModel):
    status: Literal["completed"] = "completed"
    diagnosis: DiagnosisRecord
    generation_attempts: int = Field(strict=True, ge=1, le=MAX_REPAIR_ATTEMPTS + 1)
    run_ids: list[str]


class GenerationFailed(StrictGenerationModel):
    status: Literal["generation_failed"] = "generation_failed"
    issues: list[GenerationIssue]
    generation_attempts: int = Field(strict=True, ge=1, le=MAX_REPAIR_ATTEMPTS + 1)
    completed_stages: list[Literal["candidate_received", "local_validation"]]
    retry_scope: Literal["generation"] = "generation"
    run_ids: list[str]


GenerationOutcome = GenerationCompleted | GenerationFailed


def _pointer(loc: tuple[object, ...]) -> str:
    if not loc:
        return ""
    parts = [str(item).replace("~", "~0").replace("/", "~1") for item in loc]
    return "/" + "/".join(parts)


def _dedupe_issues(issues: list[GenerationIssue]) -> list[GenerationIssue]:
    unique = {(issue.code.value, issue.pointer): issue for issue in issues}
    return [unique[key] for key in sorted(unique)]


def _schema_issues(error: ValidationError) -> tuple[list[GenerationIssue], bool]:
    issues: list[GenerationIssue] = []
    repairable = True
    for detail in error.errors(include_input=False, include_context=False):
        loc = tuple(detail.get("loc", ()))
        message = str(detail.get("msg", ""))
        command_field = bool(loc) and loc[0] in {
            "checks",
            "fixes",
            "verification_steps",
        }
        if command_field and "unsafe command" in message:
            code = IssueCode.UNSAFE_COMMAND
            repairable = False
        else:
            code = IssueCode.SCHEMA_INVALID
        issues.append(GenerationIssue(code=code, pointer=_pointer(loc)))
    return _dedupe_issues(issues), repairable


def _safe_payload(payload: object) -> GenerationIssue | None:
    try:
        assert_export_safe(payload)
    except UnsafeExport:
        return GenerationIssue(code=IssueCode.PRIVACY_UNSAFE, pointer="")
    return None


def _parse_candidate(payload: object) -> tuple[object | None, list[GenerationIssue]]:
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            unsafe = _safe_payload(payload)
            if unsafe is not None:
                return None, [unsafe]
            return None, [
                GenerationIssue(code=IssueCode.JSON_PARSE_FAILED, pointer="")
            ]
    else:
        parsed = payload
    unsafe = _safe_payload(parsed)
    if unsafe is not None:
        return None, [unsafe]
    return parsed, []


def _semantic_issues(
    diagnosis: DiagnosisRecord, request: GenerationRequest
) -> list[GenerationIssue]:
    issues: list[GenerationIssue] = []
    if diagnosis.case_id != request.case_id:
        issues.append(GenerationIssue(code=IssueCode.CASE_ID_MISMATCH, pointer="/case_id"))
    if diagnosis.category != request.routing.category:
        issues.append(GenerationIssue(code=IssueCode.ROUTING_MISMATCH, pointer="/category"))

    expected_facts = {
        item.fact_id: item.model_dump(mode="json") for item in request.observed_facts
    }
    actual_facts = {
        item.fact_id: item.model_dump(mode="json") for item in diagnosis.observed_facts
    }
    if actual_facts != expected_facts:
        issues.append(
            GenerationIssue(code=IssueCode.FACT_SET_MISMATCH, pointer="/observed_facts")
        )

    expected_evidence = {
        item.evidence_id: item.model_dump(mode="json") for item in request.evidence
    }
    actual_evidence = {
        item.evidence_id: item.model_dump(mode="json") for item in diagnosis.evidence
    }
    if actual_evidence != expected_evidence:
        issues.append(
            GenerationIssue(code=IssueCode.EVIDENCE_SET_MISMATCH, pointer="/evidence")
        )
    if any(
        item.knowledge_build_id != request.knowledge_build_id for item in diagnosis.evidence
    ):
        issues.append(
            GenerationIssue(
                code=IssueCode.KNOWLEDGE_BUILD_MISMATCH,
                pointer="/evidence",
            )
        )
    return _dedupe_issues(issues)


def _validate_candidate(
    payload: object, request: GenerationRequest
) -> tuple[DiagnosisRecord | None, list[GenerationIssue], bool]:
    parsed, parse_issues = _parse_candidate(payload)
    if parse_issues:
        repairable = all(issue.code is not IssueCode.PRIVACY_UNSAFE for issue in parse_issues)
        return None, parse_issues, repairable
    try:
        diagnosis = DiagnosisRecord.model_validate_json(
            json.dumps(parsed, ensure_ascii=False, allow_nan=False), strict=True
        )
    except ValidationError as error:
        issues, repairable = _schema_issues(error)
        return None, issues, repairable
    issues = _semantic_issues(diagnosis, request)
    return (diagnosis if not issues else None), issues, True


class DiagnosisGenerator:
    """Validate candidate output locally and permit at most one contract repair."""

    def __init__(self, backend: CandidateBackend, *, user: str = "debugmate-local") -> None:
        self._backend = backend
        self._user = user

    def generate(self, request: GenerationRequest) -> GenerationOutcome:
        request = GenerationRequest.model_validate(request.model_dump(), strict=True)
        first_inputs: dict[str, object] = {
            "request_kind": "candidate_generation",
            "generation_request": request.model_dump(mode="json"),
        }
        first = self._backend.run_workflow(first_inputs, self._user)
        diagnosis, issues, repairable = _validate_candidate(
            first.candidate_payload, request
        )
        run_ids = [first.run_id]
        if diagnosis is not None:
            return GenerationCompleted(
                diagnosis=diagnosis,
                generation_attempts=1,
                run_ids=run_ids,
            )
        if not repairable:
            return GenerationFailed(
                issues=issues,
                generation_attempts=1,
                completed_stages=["candidate_received", "local_validation"],
                run_ids=run_ids,
            )

        repair_inputs: dict[str, object] = {
            "request_kind": "contract_repair",
            "schema_version": request.schema_version,
            "issues": [issue.model_dump(mode="json") for issue in issues],
            "candidate": first.candidate_payload,
        }
        second = self._backend.run_workflow(repair_inputs, self._user)
        run_ids.append(second.run_id)
        repaired, second_issues, unused_repairable = _validate_candidate(
            second.candidate_payload, request
        )
        del unused_repairable
        if repaired is not None:
            return GenerationCompleted(
                diagnosis=repaired,
                generation_attempts=MAX_REPAIR_ATTEMPTS + 1,
                run_ids=run_ids,
            )
        return GenerationFailed(
            issues=second_issues,
            generation_attempts=MAX_REPAIR_ATTEMPTS + 1,
            completed_stages=["candidate_received", "local_validation"],
            run_ids=run_ids,
        )
