"""Phase 08 live-generation invariants kept separate from provider transport tests."""

from debugmate.diagnosis.generation import MAX_REPAIR_ATTEMPTS, GenerationIssue


def test_live_generation_has_exactly_one_contract_repair_budget() -> None:
    assert MAX_REPAIR_ATTEMPTS == 1


def test_repair_issue_contract_exposes_only_safe_code_and_pointer() -> None:
    issue = GenerationIssue(code="schema_invalid", pointer="/recap_text")
    assert set(issue.model_dump(mode="json")) == {"code", "pointer"}
