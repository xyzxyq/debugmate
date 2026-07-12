"""Versioned deterministic routing over confirmed case facts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from debugmate.contracts import ErrorCategory
from debugmate.diagnosis.extraction import CaseFacts, FieldId, StrictFrozenModel

ROUTER_RULE_VERSION = "router-v1"
ROUTING_THRESHOLD = 0.80


class DecisionStage(StrEnum):
    PROVISIONAL = "provisional"
    FINAL = "final"


class RouteCandidate(StrictFrozenModel):
    rule_id: str = Field(min_length=1)
    category: ErrorCategory
    score: float = Field(strict=True, ge=0.0, le=1.0)
    fact_ids: list[str]


class RoutingDecision(StrictFrozenModel):
    decision_stage: DecisionStage
    rule_version: str = Field(min_length=1)
    category: ErrorCategory
    candidates: list[RouteCandidate]
    reason: str = Field(min_length=1)
    model_category: Annotated[ErrorCategory | None, Field(strict=False)] = None


_EXCEPTION_RULES: dict[str, tuple[str, ErrorCategory]] = {
    "modulenotfounderror": ("exception.module-not-found", ErrorCategory.DEPENDENCY_ENVIRONMENT),
    "importerror": ("exception.import-error", ErrorCategory.DEPENDENCY_ENVIRONMENT),
    "permissionerror": ("exception.permission", ErrorCategory.PATH_PERMISSION),
    "filenotfounderror": ("exception.file-not-found", ErrorCategory.PATH_PERMISSION),
    "typeerror": ("exception.type-error", ErrorCategory.PYTHON_RUNTIME),
    "attributeerror": ("exception.attribute-error", ErrorCategory.PYTHON_RUNTIME),
    "valueerror": ("exception.value-error", ErrorCategory.PYTHON_RUNTIME),
}

_TEXT_RULES: tuple[tuple[str, str, ErrorCategory, float], ...] = (
    ("trace.cuda-out-of-memory", "cuda out of memory", ErrorCategory.CUDA_MEMORY, 0.98),
    (
        "trace.tensor-shape-multiply",
        "shapes cannot be multiplied",
        ErrorCategory.TENSOR_SHAPE_DTYPE,
        0.96,
    ),
    ("trace.tensor-size-mismatch", "size mismatch", ErrorCategory.TENSOR_SHAPE_DTYPE, 0.90),
    ("trace.state-dict-load", "loading state_dict", ErrorCategory.MODEL_LOADING, 0.96),
    ("trace.checkpoint-load", "checkpoint load", ErrorCategory.MODEL_LOADING, 0.90),
    ("trace.access-denied", "access is denied", ErrorCategory.PATH_PERMISSION, 0.94),
)


def _strict_facts(value: CaseFacts) -> CaseFacts:
    if not isinstance(value, CaseFacts):
        raise TypeError("route_case requires CaseFacts")
    return CaseFacts.model_validate(value.model_dump(), strict=True)


def route_case(
    facts: CaseFacts,
    *,
    decision_stage: DecisionStage,
    model_category: ErrorCategory | None = None,
) -> RoutingDecision:
    """Return a reproducible six-class or unknown decision without model authority."""

    facts = _strict_facts(facts)
    stage = DecisionStage(decision_stage)
    untrusted_model_category = ErrorCategory(model_category) if model_category is not None else None
    candidates: list[RouteCandidate] = []

    for fact in facts.facts:
        normalized = fact.value.casefold()
        if fact.field_id is FieldId.EXCEPTION_TYPE:
            short_name = normalized.rsplit(".", 1)[-1]
            if matched := _EXCEPTION_RULES.get(short_name):
                rule_id, category = matched
                candidates.append(
                    RouteCandidate(
                        rule_id=rule_id,
                        category=category,
                        score=1.0,
                        fact_ids=[fact.fact_id],
                    )
                )
        if fact.field_id is FieldId.TRACEBACK_KEY_LINE:
            for rule_id, needle, category, score in _TEXT_RULES:
                if needle in normalized:
                    candidates.append(
                        RouteCandidate(
                            rule_id=rule_id,
                            category=category,
                            score=score,
                            fact_ids=[fact.fact_id],
                        )
                    )
        if fact.field_id is FieldId.DEVICE and "cuda" in normalized:
            candidates.append(
                RouteCandidate(
                    rule_id="device.cuda-context-only",
                    category=ErrorCategory.CUDA_MEMORY,
                    score=0.35,
                    fact_ids=[fact.fact_id],
                )
            )

    candidates.sort(
        key=lambda item: (-item.score, item.category.value, item.rule_id, item.fact_ids)
    )
    strong_categories = {item.category for item in candidates if item.score >= ROUTING_THRESHOLD}
    if len(strong_categories) > 1:
        category = ErrorCategory.UNKNOWN
        reason = "conflicting strong local rules"
    elif len(strong_categories) == 1:
        category = next(iter(strong_categories))
        reason = "matched deterministic local rule"
    elif candidates:
        category = ErrorCategory.UNKNOWN
        reason = "local rule score below threshold"
    else:
        category = ErrorCategory.UNKNOWN
        reason = "no deterministic local rule matched"

    return RoutingDecision(
        decision_stage=stage,
        rule_version=ROUTER_RULE_VERSION,
        category=category,
        candidates=candidates,
        reason=reason,
        model_category=untrusted_model_category,
    )
