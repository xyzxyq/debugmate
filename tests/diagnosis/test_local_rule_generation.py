from __future__ import annotations

from pathlib import Path

import pytest

from debugmate.contracts import new_case_id
from debugmate.diagnosis.extraction import build_case_facts
from debugmate.diagnosis.generation import GenerationCompleted, GenerationRequest
from debugmate.diagnosis.local_rule import LocalRuleGenerationProvider
from debugmate.diagnosis.providers import ProductionExtractionProvider
from debugmate.diagnosis.routing import DecisionStage, route_case
from debugmate.knowledge.local_rule import (
    LocalRuleRetrievalProvider,
    load_local_rule_snapshot,
)
from debugmate.privacy.approval import approve_preview
from debugmate.privacy.models import InputEnvelope
from debugmate.privacy.text_redactor import redact_input


class _NoopOcr:
    def recognize(self, _path: Path) -> list[object]:
        return []


def _request(tmp_path: Path, *, error_text: str) -> GenerationRequest:
    case_id = new_case_id()
    key = b"local-rule-generation-test-key!!"
    approved = approve_preview(
        redact_input(
            InputEnvelope(
                case_id=case_id,
                error_text=error_text,
                environment={"python": "3.13.5"},
            )
        ),
        key,
    )
    extraction = ProductionExtractionProvider(
        redacted_root=tmp_path / "redacted", ocr_backend=_NoopOcr()
    ).extract(approved)
    facts = build_case_facts(extraction)
    routing = route_case(facts, decision_stage=DecisionStage.FINAL)
    snapshot = load_local_rule_snapshot(Path.cwd())
    evidence = LocalRuleRetrievalProvider(snapshot).retrieve(facts, routing)
    return GenerationRequest(
        case_id=case_id,
        observed_facts=[
            {
                "fact_id": fact.fact_id,
                "field_id": fact.field_id.value,
                "value": fact.value,
                "source_kind": fact.source_kinds[0].value,
                "confidence": fact.confidence,
                "locator": f"fact:{fact.fact_id}",
            }
            for fact in facts.facts
        ],
        evidence=evidence,
        routing=routing,
        knowledge_build_id=snapshot.knowledge_build_id,
        schema_version="1.1.0",
        prompt_version="diagnosis-v1",
    )


def test_local_rule_generation_uses_only_fresh_request_identity(tmp_path: Path) -> None:
    snapshot = load_local_rule_snapshot(Path.cwd())
    request = _request(
        tmp_path,
        error_text="ModuleNotFoundError: No module named 'fictional_pkg'",
    )

    completed = LocalRuleGenerationProvider(snapshot).generate(request)

    assert isinstance(completed, GenerationCompleted)
    assert completed.diagnosis.case_id == request.case_id
    assert completed.diagnosis.observed_facts == request.observed_facts
    assert completed.diagnosis.evidence == request.evidence
    assert completed.generation_attempts == 1
    assert completed.run_ids == ["local-rule:module-not-found-v1"]


def test_local_rule_generation_rejects_nonmatching_request_without_values(
    tmp_path: Path,
) -> None:
    snapshot = load_local_rule_snapshot(Path.cwd())
    request = _request(tmp_path, error_text="ValueError: invalid fictional value")

    with pytest.raises(ValueError, match="^local_rule_no_match$") as caught:
        LocalRuleGenerationProvider(snapshot).generate(request)

    assert "ValueError" not in repr(caught.value)
