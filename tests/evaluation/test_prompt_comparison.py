from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.evaluation.contracts import (
    PromptComparison,
    PromptComparisonInput,
    PromptCriteriaRegistry,
    PromptProvenance,
)

CRITERIA_PATH = Path("evaluation/phase9/prompt-criteria.json")
SOURCE_PLAN = ".planning/phases/08-dify-unified-live-chain/08-07-PLAN.md"
SOURCE_PLAN_HASH = "f2d131057d2b989f3640f21931f1d45d94912e97e1a2d8a9029ba0b1b2c3bc2b"
ACCEPTED_V1 = Path("evidence/evaluation/phase9/accepted-v1-contract.json")
PROVIDER_V2 = Path("evidence/evaluation/phase9/run-v2.json")


def load_criteria() -> PromptCriteriaRegistry:
    return PromptCriteriaRegistry.model_validate_json(CRITERIA_PATH.read_text(encoding="utf-8"))


def hash_value(character: str) -> str:
    return character * 64


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def comparison_payload() -> dict[str, object]:
    criteria = load_criteria()
    common_input = {
        "case_id": "P9-C01-live-private",
        "sanitized_input_sha256": hash_value("1"),
        "facts_sha256": hash_value("2"),
        "retrieval_trace_sha256": hash_value("3"),
        "knowledge_build_id": hash_value("4"),
        "schema_sha256": hash_value("5"),
    }
    accepted = {
        "conclusion": {
            "code": "evidence_bound_diagnosis",
            "summary": (
                "The fixed sanitized case remains bound to validated facts and retrieval evidence."
            ),
        },
        "accepted_diagnosis_sha256": hash_value("6"),
        "accepted_result_sha256": hash_value("7"),
        "candidate_sha256": hash_value("8"),
    }
    source_evidence = {
        "kind": "accepted_v1_contract",
        "reference": {
            "path": {"path": ACCEPTED_V1.as_posix()},
            "sha256": file_hash(ACCEPTED_V1),
        },
    }
    rows: list[dict[str, object]] = []
    for criterion in criteria.rows:
        rows.append(
            {
                "version": criterion.version,
                "prompt_file": criterion.prompt_file.model_dump(mode="json"),
                "common_input": common_input,
                "conclusion": accepted["conclusion"],
                "accepted_diagnosis_sha256": accepted["accepted_diagnosis_sha256"],
                "accepted_result_sha256": accepted["accepted_result_sha256"],
                "candidate_sha256": accepted["candidate_sha256"],
                "source_evidence": source_evidence,
                "provenance": "verified_contract" if criterion.version == "v1" else "blocked",
                "status": "accepted" if criterion.version == "v1" else "blocked",
            }
        )
    return {
        "comparison_version": "phase9-prompt-comparison-1.0",
        "common_input": common_input,
        "accepted_v1": accepted,
        "rows": rows,
    }


def test_prompt_criteria_have_exact_current_v1_to_v4_files_and_safe_rationales() -> None:
    criteria = load_criteria()

    assert [row.version for row in criteria.rows] == ["v1", "v2", "v3", "v4"]
    assert [row.prompt_file.path.path for row in criteria.rows] == [
        "prompts/v1-baseline.md",
        "prompts/v2-citations.md",
        "prompts/v3-reliability.md",
        "prompts/v4-course-release.md",
    ]
    assert all(row.prompt_file.is_verified() for row in criteria.rows)
    assert all(row.objective and row.adoption_rationale and row.limitation for row in criteria.rows)


def test_comparison_requires_exactly_four_rows_with_one_immutable_common_input() -> None:
    comparison = PromptComparison.model_validate(comparison_payload())

    assert isinstance(comparison.common_input, PromptComparisonInput)
    assert all(row.common_input == comparison.common_input for row in comparison.rows)
    assert {row.version for row in comparison.rows} == {"v1", "v2", "v3", "v4"}


@pytest.mark.parametrize(
    "field",
    [
        "case_id",
        "sanitized_input_sha256",
        "facts_sha256",
        "retrieval_trace_sha256",
        "knowledge_build_id",
        "schema_sha256",
    ],
)
def test_comparison_rejects_common_input_drift(field: str) -> None:
    payload = comparison_payload()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[1]["common_input"] = {**rows[1]["common_input"], field: hash_value("f")}

    with pytest.raises(ValidationError):
        PromptComparison.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    ["accepted_diagnosis_sha256", "accepted_result_sha256", "candidate_sha256"],
)
def test_verified_contract_rejects_accepted_output_hash_drift(field: str) -> None:
    payload = comparison_payload()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[2][field] = hash_value("f")

    with pytest.raises(ValidationError):
        PromptComparison.model_validate(payload)


def test_verified_contract_cannot_serialize_as_a_generated_live_claim() -> None:
    comparison = PromptComparison.model_validate(comparison_payload())
    assert comparison.rows[0].provenance is PromptProvenance.VERIFIED_CONTRACT
    assert comparison.rows[0].model_dump(mode="json")["provenance"] == "verified_contract"

    payload = comparison_payload()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[1]["provenance"] = "generated_live"

    with pytest.raises(ValidationError):
        PromptComparison.model_validate(payload)


def test_generated_live_requires_its_provider_manifest_to_bind_every_row_identity() -> None:
    payload = comparison_payload()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[1]["source_evidence"] = {
        "kind": "evaluation_provider_run",
        "reference": {
            "path": {"path": PROVIDER_V2.as_posix()},
            "sha256": file_hash(PROVIDER_V2),
        },
    }
    rows[1]["provenance"] = "generated_live"
    rows[1]["status"] = "accepted"

    comparison = PromptComparison.model_validate(payload)
    assert comparison.rows[1].provenance is PromptProvenance.GENERATED_LIVE

    rows[1]["candidate_sha256"] = hash_value("f")
    with pytest.raises(ValidationError, match="does not prove"):
        PromptComparison.model_validate(payload)


def test_accepted_v1_contract_rejects_any_other_hash_bound_source() -> None:
    payload = comparison_payload()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[0]["source_evidence"] = {
        "kind": "accepted_v1_contract",
        "reference": {"path": {"path": SOURCE_PLAN}, "sha256": SOURCE_PLAN_HASH},
    }

    with pytest.raises(ValidationError, match="exact accepted V1"):
        PromptComparison.model_validate(payload)


def test_prompt_file_hash_or_source_evidence_drift_rejects_comparison() -> None:
    payload = comparison_payload()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[0]["prompt_file"]["sha256"] = hash_value("f")
    with pytest.raises(ValidationError):
        PromptComparison.model_validate(payload)

    payload = comparison_payload()
    rows = payload["rows"]
    assert isinstance(rows, list)
    rows[3]["source_evidence"]["reference"]["sha256"] = hash_value("f")
    with pytest.raises(ValidationError):
        PromptComparison.model_validate(payload)
