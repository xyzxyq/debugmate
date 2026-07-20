"""Finite, category-aware information sufficiency policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from debugmate.contracts import ErrorCategory
from debugmate.diagnosis.extraction import (
    CaseFact,
    CaseFacts,
    FieldId,
    SourceKind,
    StrictFrozenModel,
    fact_id_for,
    facts_hash,
    normalize_value,
)
from debugmate.diagnosis.routing import DecisionStage, RoutingDecision, route_case
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.privacy.output_scan import assert_export_safe

MAX_QUESTIONS = 3
MAX_FOLLOWUP_ROUNDS = 1
SUFFICIENCY_POLICY_VERSION = "sufficiency-v1"


@dataclass(frozen=True)
class _Matrix:
    required: tuple[FieldId, ...]
    high_value: tuple[FieldId, ...]
    optional: tuple[FieldId, ...]


_MATRICES: dict[ErrorCategory, _Matrix] = {
    ErrorCategory.DEPENDENCY_ENVIRONMENT: _Matrix(
        required=(FieldId.EXCEPTION_TYPE, FieldId.TRACEBACK_KEY_LINE),
        high_value=(FieldId.PACKAGE, FieldId.VERSION),
        optional=(FieldId.PATH, FieldId.DEVICE),
    ),
    ErrorCategory.PATH_PERMISSION: _Matrix(
        required=(FieldId.EXCEPTION_TYPE, FieldId.TRACEBACK_KEY_LINE, FieldId.PATH),
        high_value=(FieldId.VERSION,),
        optional=(FieldId.PACKAGE, FieldId.DEVICE),
    ),
    ErrorCategory.PYTHON_RUNTIME: _Matrix(
        required=(FieldId.EXCEPTION_TYPE, FieldId.TRACEBACK_KEY_LINE),
        high_value=(FieldId.PACKAGE, FieldId.VERSION),
        optional=(FieldId.PATH, FieldId.DEVICE),
    ),
    ErrorCategory.TENSOR_SHAPE_DTYPE: _Matrix(
        required=(FieldId.TRACEBACK_KEY_LINE,),
        high_value=(FieldId.DEVICE, FieldId.VERSION),
        optional=(FieldId.PACKAGE, FieldId.PATH, FieldId.EXCEPTION_TYPE),
    ),
    ErrorCategory.CUDA_MEMORY: _Matrix(
        required=(FieldId.TRACEBACK_KEY_LINE, FieldId.DEVICE),
        high_value=(FieldId.VERSION, FieldId.PACKAGE),
        optional=(FieldId.PATH, FieldId.EXCEPTION_TYPE),
    ),
    ErrorCategory.MODEL_LOADING: _Matrix(
        required=(FieldId.TRACEBACK_KEY_LINE, FieldId.PATH),
        high_value=(FieldId.PACKAGE, FieldId.VERSION),
        optional=(FieldId.DEVICE, FieldId.EXCEPTION_TYPE),
    ),
    ErrorCategory.UNKNOWN: _Matrix(
        required=(FieldId.EXCEPTION_TYPE, FieldId.TRACEBACK_KEY_LINE),
        high_value=(FieldId.DEVICE, FieldId.PATH, FieldId.PACKAGE, FieldId.VERSION),
        optional=(),
    ),
}

_EXPECTED_FORMAT: dict[FieldId, str] = {
    FieldId.EXCEPTION_TYPE: "Python exception class, for example ModuleNotFoundError",
    FieldId.TRACEBACK_KEY_LINE: "one redacted traceback line containing the failure",
    FieldId.PACKAGE: "package or framework name",
    FieldId.VERSION: "package or runtime version",
    FieldId.DEVICE: "cpu, cuda:N, mps, or other device identifier",
    FieldId.PATH: "redacted file or checkpoint path",
}

_REASONS: dict[FieldId, str] = {
    FieldId.EXCEPTION_TYPE: "The exception class can change deterministic routing.",
    FieldId.TRACEBACK_KEY_LINE: "The key line can change routing and root-cause ranking.",
    FieldId.PACKAGE: "The package narrows applicable dependency and model checks.",
    FieldId.VERSION: "The version narrows compatibility checks.",
    FieldId.DEVICE: "The device changes hardware-specific checks and safe guidance.",
    FieldId.PATH: "The redacted path distinguishes access and loading contexts.",
}


class FollowupQuestion(StrictFrozenModel):
    question_id: str = Field(pattern=r"^question_[0-9a-f]{32}$")
    field_id: FieldId
    expected_format: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class Ready(StrictFrozenModel):
    status: Literal["ready"] = "ready"
    policy_version: str = SUFFICIENCY_POLICY_VERSION
    known_fact_ids: list[str]


class NeedsInformation(StrictFrozenModel):
    status: Literal["needs_information"] = "needs_information"
    policy_version: str = SUFFICIENCY_POLICY_VERSION
    followup_round: Literal[0] = 0
    known_fact_ids: list[str]
    missing_field_ids: list[FieldId]
    questions: list[FollowupQuestion]


class InsufficientInformation(StrictFrozenModel):
    status: Literal["insufficient_information"] = "insufficient_information"
    policy_version: str = SUFFICIENCY_POLICY_VERSION
    known_fact_ids: list[str]
    missing_field_ids: list[FieldId]
    safe_checks: list[str]


SufficiencyResult = Ready | NeedsInformation | InsufficientInformation


def _question(field_id: FieldId, category: ErrorCategory) -> FollowupQuestion:
    digest = sha256_bytes(
        canonical_json_bytes(
            {
                "policy_version": SUFFICIENCY_POLICY_VERSION,
                "category": category.value,
                "field_id": field_id.value,
            }
        )
    )
    return FollowupQuestion(
        question_id=f"question_{digest[:32]}",
        field_id=field_id,
        expected_format=_EXPECTED_FORMAT[field_id],
        reason=_REASONS[field_id],
    )


def _priority(field_id: FieldId) -> tuple[int, int, int, str]:
    changes_route = field_id in {FieldId.EXCEPTION_TYPE, FieldId.TRACEBACK_KEY_LINE}
    changes_root_cause = field_id in {
        FieldId.EXCEPTION_TYPE,
        FieldId.TRACEBACK_KEY_LINE,
        FieldId.PACKAGE,
        FieldId.VERSION,
    }
    changes_safe_checks = field_id in {FieldId.DEVICE, FieldId.PATH}
    return (
        -int(changes_route),
        -int(changes_root_cause),
        -int(changes_safe_checks),
        field_id.value,
    )


def evaluate_sufficiency(
    facts: CaseFacts,
    provisional: RoutingDecision,
    *,
    followup_round: int,
    asked_field_ids: set[FieldId] | None = None,
) -> SufficiencyResult:
    """Evaluate only the matrix selected by a validated provisional route."""

    if not isinstance(facts, CaseFacts):
        raise TypeError("evaluate_sufficiency requires CaseFacts")
    if not isinstance(provisional, RoutingDecision):
        raise TypeError("evaluate_sufficiency requires RoutingDecision")
    facts = CaseFacts.model_validate(facts.model_dump(), strict=True)
    provisional = RoutingDecision.model_validate(provisional.model_dump(), strict=True)
    if provisional.decision_stage is not DecisionStage.PROVISIONAL:
        raise ValueError("sufficiency requires a provisional routing decision")
    if followup_round not in range(MAX_FOLLOWUP_ROUNDS + 1):
        raise ValueError("followup_round exceeds the finite policy")

    matrix = _MATRICES[provisional.category]
    present = {fact.field_id for fact in facts.facts}
    known_fact_ids = [fact.fact_id for fact in facts.facts]
    critical_missing = [field for field in matrix.required if field not in present]
    valuable_missing = [field for field in matrix.high_value if field not in present]
    missing = sorted({*critical_missing, *valuable_missing}, key=_priority)
    if not missing:
        return Ready(known_fact_ids=known_fact_ids)
    if followup_round == MAX_FOLLOWUP_ROUNDS:
        if critical_missing:
            return InsufficientInformation(
                known_fact_ids=known_fact_ids,
                missing_field_ids=missing,
                safe_checks=[
                    "Confirm the redacted exception and traceback without running commands.",
                    "Preserve the current environment before making any change.",
                ],
            )
        return Ready(known_fact_ids=known_fact_ids)

    already_asked = {FieldId(value) for value in (asked_field_ids or set())}
    askable = [field for field in missing if field not in already_asked]
    if not askable:
        return InsufficientInformation(
            known_fact_ids=known_fact_ids,
            missing_field_ids=missing,
            safe_checks=["Review the already requested redacted fields before continuing."],
        )
    selected = askable[:MAX_QUESTIONS]
    return NeedsInformation(
        known_fact_ids=known_fact_ids,
        missing_field_ids=missing,
        questions=[_question(field, provisional.category) for field in selected],
    )


def apply_followup_answers(
    facts: CaseFacts,
    assessment: NeedsInformation,
    answers: dict[FieldId, str],
) -> tuple[CaseFacts, RoutingDecision]:
    """Create an immutable facts revision, then perform the final route."""

    if not isinstance(facts, CaseFacts) or not isinstance(assessment, NeedsInformation):
        raise TypeError("follow-up answers require facts and needs-information assessment")
    facts = CaseFacts.model_validate(facts.model_dump(), strict=True)
    assessment = NeedsInformation.model_validate(assessment.model_dump(), strict=True)
    allowed = {question.field_id for question in assessment.questions}
    normalized_answers = {FieldId(field): value for field, value in answers.items()}
    if not normalized_answers or not set(normalized_answers) <= allowed:
        raise ValueError("answer does not target an issued question")
    present = {fact.field_id for fact in facts.facts}
    if set(normalized_answers) & present:
        raise ValueError("follow-up answer cannot overwrite an existing fact")

    revised_facts = list(facts.facts)
    for field_id, value in normalized_answers.items():
        normalized = normalize_value(field_id, value)
        assert_export_safe(normalized)
        revised_facts.append(
            CaseFact(
                fact_id=fact_id_for(field_id, normalized),
                field_id=field_id,
                value=normalized,
                provenance_candidate_ids=[],
                source_kinds=[SourceKind.USER],
                confidence=1.0,
            )
        )
    revised_facts.sort(key=lambda fact: fact.fact_id)
    revision = facts.revision + 1
    digest = facts_hash(
        facts.case_id,
        revision,
        revised_facts,
        facts.applied_corrections,
    )
    revised = CaseFacts(
        case_id=facts.case_id,
        revision=revision,
        facts_sha256=digest,
        facts=revised_facts,
        applied_corrections=list(facts.applied_corrections),
    )
    return revised, route_case(revised, decision_stage=DecisionStage.FINAL)
