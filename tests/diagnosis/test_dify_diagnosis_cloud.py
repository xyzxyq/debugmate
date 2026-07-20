from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from debugmate.adapters.dify import DifyBackend
from debugmate.contracts import DiagnosisRecord, new_case_id
from debugmate.diagnosis.generation import DiagnosisGenerator, GenerationRequest
from debugmate.diagnosis.routing import DecisionStage, RoutingDecision
from debugmate.settings import DebugMateSettings


@pytest.mark.cloud
def test_real_dify_candidate_is_locally_validated_or_repaired_once() -> None:
    settings = DebugMateSettings.from_env()
    app_ready = os.environ.get("DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED") == "1"
    if not settings.cloud_configured or not app_ready:
        pytest.skip("Dify diagnosis credentials/app configuration are not available")

    case_id = new_case_id()
    root = Path(__file__).resolve().parents[2]
    input_payload = json.loads(
        (root / "fixtures" / "cases" / "module_not_found" / "input.json").read_text(
            encoding="utf-8"
        )
    )
    expected_payload = json.loads(
        (root / "fixtures" / "cases" / "module_not_found" / "diagnosis.json").read_text(
            encoding="utf-8"
        )
    )
    expected_payload["case_id"] = case_id
    expected = DiagnosisRecord.model_validate_json(json.dumps(expected_payload), strict=True)
    request = GenerationRequest(
        case_id=case_id,
        observed_facts=expected.observed_facts,
        evidence=expected.evidence,
        routing=RoutingDecision(
            decision_stage=DecisionStage.FINAL,
            rule_version="cloud-smoke-v1",
            category=expected.category,
            candidates=[],
            reason="committed synthetic cloud smoke fixture",
        ),
        knowledge_build_id=expected.evidence[0].knowledge_build_id,
        schema_version="1.1.0",
        prompt_version="diagnosis-v1",
    )
    backend = DifyBackend(settings)
    candidate = backend.run_workflow(
        {
            "case_id": case_id,
            "error_text": input_payload["error_text"],
            "code": input_payload.get("code"),
            "environment": input_payload.get("environment"),
            "generation_request": request.model_dump(mode="json"),
        },
        settings.dify_user,
    )

    outcome = DiagnosisGenerator(backend, user=settings.dify_user).generate(
        request, initial_candidate=candidate
    )

    assert outcome.status == "completed"
    assert outcome.generation_attempts <= 2
    assert candidate.backend == "dify"
