from __future__ import annotations

import pytest

from debugmate.contracts import ErrorCategory
from debugmate.diagnosis.extraction import (
    CaseFact,
    CaseFacts,
    FieldId,
    SourceKind,
    fact_id_for,
    facts_hash,
)
from debugmate.diagnosis.routing import route_case
from debugmate.diagnosis.sufficiency import (
    MAX_QUESTIONS,
    apply_followup_answers,
    evaluate_sufficiency,
)


CASE_ID = "case_44444444444444444444444444444444"


def _facts(**values: str) -> CaseFacts:
    items = [
        CaseFact(
            fact_id=fact_id_for(FieldId(field), value),
            field_id=FieldId(field),
            value=value,
            provenance_candidate_ids=[],
            source_kinds=[SourceKind.USER],
            confidence=1.0,
        )
        for field, value in values.items()
    ]
    items.sort(key=lambda item: item.fact_id)
    return CaseFacts(
        case_id=CASE_ID,
        revision=0,
        facts_sha256=facts_hash(CASE_ID, 0, items, []),
        facts=items,
        applied_corrections=[],
    )


@pytest.mark.parametrize(
    "values",
    [
        {"exception_type": "ModuleNotFoundError"},
        {"exception_type": "PermissionError"},
        {"exception_type": "TypeError"},
        {"traceback_key_line": "tensor shapes cannot be multiplied"},
        {"traceback_key_line": "CUDA out of memory"},
        {"traceback_key_line": "loading state_dict failed"},
        {"package": "fictional-package"},
    ],
)
def test_each_provisional_category_selects_a_bounded_matrix(values: dict[str, str]) -> None:
    facts = _facts(**values)
    provisional = route_case(facts, decision_stage="provisional")

    result = evaluate_sufficiency(facts, provisional, followup_round=0)

    assert result.status in {"ready", "needs_information"}
    if result.status == "needs_information":
        assert 1 <= len(result.questions) <= MAX_QUESTIONS
        assert len({question.field_id for question in result.questions}) == len(
            result.questions
        )
        assert all(question.question_id for question in result.questions)
        assert all(question.expected_format.strip() for question in result.questions)
        assert all(question.reason.strip() for question in result.questions)


def test_complete_facts_are_ready_and_output_is_deterministic() -> None:
    facts = _facts(
        exception_type="ModuleNotFoundError",
        traceback_key_line="No module named fictional_pkg",
        package="fictional-pkg",
        version="1.0.0",
        device="cpu",
        path="C:/Fictional/project/main.py",
    )
    provisional = route_case(facts, decision_stage="provisional")

    first = evaluate_sufficiency(facts, provisional, followup_round=0)
    second = evaluate_sufficiency(facts, provisional, followup_round=0)

    assert first.status == "ready"
    assert first.model_dump_json() == second.model_dump_json()


def test_more_than_three_missing_fields_are_ranked_and_capped() -> None:
    facts = _facts(package="fictional-package")
    provisional = route_case(facts, decision_stage="provisional")

    result = evaluate_sufficiency(facts, provisional, followup_round=0)

    assert result.status == "needs_information"
    assert [question.field_id for question in result.questions] == [
        FieldId.EXCEPTION_TYPE,
        FieldId.TRACEBACK_KEY_LINE,
        FieldId.DEVICE,
    ]


def test_asked_fields_are_never_repeated() -> None:
    facts = _facts(package="fictional-package")
    provisional = route_case(facts, decision_stage="provisional")

    result = evaluate_sufficiency(
        facts,
        provisional,
        followup_round=0,
        asked_field_ids={FieldId.EXCEPTION_TYPE, FieldId.TRACEBACK_KEY_LINE},
    )

    assert result.status == "needs_information"
    assert all(
        question.field_id not in {FieldId.EXCEPTION_TYPE, FieldId.TRACEBACK_KEY_LINE}
        for question in result.questions
    )


def test_round_one_with_critical_gap_is_explicitly_insufficient() -> None:
    facts = _facts(package="fictional-package")
    provisional = route_case(facts, decision_stage="provisional")

    result = evaluate_sufficiency(facts, provisional, followup_round=1)

    assert result.status == "insufficient_information"
    assert FieldId.EXCEPTION_TYPE in result.missing_field_ids
    assert result.known_fact_ids == [fact.fact_id for fact in facts.facts]
    assert result.safe_checks
    assert not hasattr(result, "root_cause")


def test_answer_creates_new_revision_before_final_route() -> None:
    facts = _facts(package="fictional-package")
    provisional = route_case(facts, decision_stage="provisional")
    assessment = evaluate_sufficiency(facts, provisional, followup_round=0)
    assert provisional.category is ErrorCategory.UNKNOWN
    assert assessment.status == "needs_information"

    revised, final = apply_followup_answers(
        facts,
        assessment,
        {FieldId.EXCEPTION_TYPE: "ModuleNotFoundError"},
    )

    assert revised.revision == facts.revision + 1
    assert revised.facts_sha256 != facts.facts_sha256
    assert final.decision_stage.value == "final"
    assert final.category is ErrorCategory.DEPENDENCY_ENVIRONMENT
    assert final.candidates[0].fact_ids[0] in {fact.fact_id for fact in revised.facts}
    assert all(fact.field_id is not FieldId.EXCEPTION_TYPE for fact in facts.facts)


def test_answers_are_limited_to_issued_field_questions() -> None:
    facts = _facts(package="fictional-package")
    provisional = route_case(facts, decision_stage="provisional")
    assessment = evaluate_sufficiency(facts, provisional, followup_round=0)

    with pytest.raises(ValueError, match="issued question"):
        apply_followup_answers(facts, assessment, {FieldId.PATH: "C:/Fictional/file.py"})
