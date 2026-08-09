from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.cloud.contracts import (
    DifyAttempt,
    DifyAttemptKind,
    DifyRunEnvelope,
    DifyUsage,
    ExecutionBackend,
)


DIAGNOSIS_FIXTURE = Path("fixtures/cases/module_not_found/diagnosis.json")


def _envelope_payload() -> dict[str, object]:
    diagnosis = json.loads(DIAGNOSIS_FIXTURE.read_text(encoding="utf-8"))
    return {
        "envelope_version": "1.0.0",
        "case_id": diagnosis["case_id"],
        "diagnosis": diagnosis,
        "extraction_facts": diagnosis["observed_facts"],
        "retrieval_trace": {
            "knowledge_build_id": "3" * 64,
            "run_fingerprint": "4" * 64,
            "node_fingerprint": "5" * 64,
            "hits": [
                {
                    "chunk_fingerprint": "6" * 64,
                    "source_id": "python-exceptions",
                    "source_title": "Python Exceptions",
                    "source_url": "https://docs.python.org/3/library/exceptions.html",
                    "locator": "ModuleNotFoundError",
                    "content_summary": "The requested module could not be located.",
                    "relevance_score": 0.95,
                }
            ],
        },
        "contract": {
            "schema_version": "1.1.0",
            "prompt_version": "diagnosis-v1",
            "knowledge_build_id": "3" * 64,
            "dsl_semantic_sha256": "7" * 64,
        },
    }


def test_run_envelope_accepts_only_bounded_same_run_contract() -> None:
    envelope = DifyRunEnvelope.model_validate(_envelope_payload(), strict=True)

    assert envelope.envelope_version == "1.0.0"
    assert envelope.diagnosis.schema_version == "1.1.0"
    assert envelope.case_id == envelope.diagnosis.case_id
    assert envelope.contract.knowledge_build_id == envelope.retrieval_trace.knowledge_build_id
    assert len(envelope.retrieval_trace.hits) == 1

    with pytest.raises(ValidationError):
        DifyRunEnvelope.model_validate(_envelope_payload() | {"provider_body": {}}, strict=True)


def test_run_envelope_rejects_oversized_duplicate_or_too_many_hits() -> None:
    payload = _envelope_payload()
    trace = payload["retrieval_trace"]
    assert isinstance(trace, dict)
    hit = trace["hits"][0]
    assert isinstance(hit, dict)

    oversized = json.loads(json.dumps(payload))
    oversized["retrieval_trace"]["hits"][0]["content_summary"] = "x" * 2001
    with pytest.raises(ValidationError):
        DifyRunEnvelope.model_validate(oversized, strict=True)

    duplicate = json.loads(json.dumps(payload))
    duplicate["retrieval_trace"]["hits"] = [hit, hit]
    with pytest.raises(ValidationError, match="duplicate"):
        DifyRunEnvelope.model_validate(duplicate, strict=True)

    too_many = json.loads(json.dumps(payload))
    too_many["retrieval_trace"]["hits"] = [
        hit | {"chunk_fingerprint": f"{index:064x}"} for index in range(5)
    ]
    with pytest.raises(ValidationError):
        DifyRunEnvelope.model_validate(too_many, strict=True)


def test_run_envelope_rejects_case_build_and_fact_drift() -> None:
    for mutation in ("case", "build", "facts"):
        payload = json.loads(json.dumps(_envelope_payload()))
        if mutation == "case":
            payload["case_id"] = "case_ffffffffffffffffffffffffffffffff"
        elif mutation == "build":
            payload["contract"]["knowledge_build_id"] = "8" * 64
        else:
            payload["extraction_facts"] = []
        with pytest.raises(ValidationError):
            DifyRunEnvelope.model_validate(payload, strict=True)


def test_usage_is_reported_or_literal_not_reported_without_synthetic_zero() -> None:
    absent = DifyUsage()
    reported = DifyUsage(total_tokens=123, total_steps=6, elapsed_time=18.5)

    assert absent.model_dump(mode="json") == {
        "total_tokens": "not_reported",
        "total_steps": "not_reported",
        "elapsed_time": "not_reported",
        "total_price": "not_reported",
    }
    assert reported.total_tokens == 123
    assert reported.total_steps == 6
    assert reported.elapsed_time == 18.5
    assert reported.total_price == "not_reported"
    with pytest.raises(ValidationError):
        DifyUsage(total_tokens=-1)
    with pytest.raises(ValidationError):
        DifyUsage(total_tokens=True)


def test_attempts_and_execution_backends_have_only_safe_bounded_values() -> None:
    assert {item.value for item in ExecutionBackend} == {
        "dify",
        "local_fallback",
        "replay",
    }
    assert {item.value for item in DifyAttemptKind} == {
        "upload",
        "workflow",
        "contract_repair",
    }
    attempt = DifyAttempt(
        kind=DifyAttemptKind.WORKFLOW,
        attempt_fingerprint="a" * 64,
        status="succeeded",
        latency_ms=250,
    )
    assert set(attempt.model_dump(mode="json")) == {
        "kind",
        "attempt_fingerprint",
        "status",
        "latency_ms",
    }
    with pytest.raises(ValidationError):
        DifyAttempt(
            kind=DifyAttemptKind.WORKFLOW,
            attempt_fingerprint="a" * 64,
            status="succeeded",
            latency_ms=250,
            raw_remote_id="0613e0ab-124e-46eb-b6ff-13cebf0059a1",
        )
