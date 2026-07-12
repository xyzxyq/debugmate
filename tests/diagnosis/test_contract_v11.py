from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.contracts import (
    DiagnosisRecord,
    DiagnosisRecordV100,
    EvidenceAnchor,
    ObservedFact,
    RootCauseCandidate,
    SupportLink,
    diagnosis_schema,
)
from debugmate.diagnosis.migrations import migrate_v100_to_v110

ROOT = Path(__file__).resolve().parents[2]


def valid_command() -> dict[str, str]:
    return {
        "command": "python -m pip show demo_missing_pkg",
        "platform": "windows_powershell",
        "impact": "read-only",
        "expected_result": "Package metadata or a not-found message is displayed.",
        "rollback": "No rollback is needed for a read-only command.",
    }


def valid_record() -> dict[str, object]:
    return {
        "schema_version": "1.1.0",
        "case_id": "case_0123456789abcdef0123456789abcdef",
        "category": "dependency_environment",
        "observed_facts": [
            {
                "fact_id": "fact_11111111111111111111111111111111",
                "field_id": "exception_type",
                "value": "ModuleNotFoundError",
                "source_kind": "text",
                "confidence": 1.0,
                "locator": "error_text:line:1",
            }
        ],
        "evidence": [
            {
                "evidence_id": "evidence_22222222222222222222222222222222",
                "chunk_id": "python-exceptions:module-not-found",
                "content_summary": "ModuleNotFoundError is raised when a module cannot be located.",
                "source_id": "python-exceptions",
                "source_url": "https://docs.python.org/3/library/exceptions.html",
                "locator": "ModuleNotFoundError",
                "relevance_score": 0.95,
                "knowledge_build_id": "kb_33333333333333333333333333333333",
            }
        ],
        "support_links": [
            {
                "fact_ids": ["fact_11111111111111111111111111111111"],
                "evidence_ids": ["evidence_22222222222222222222222222222222"],
                "support_type": "supports",
            }
        ],
        "root_cause_candidates": [
            {
                "candidate_id": "candidate_44444444444444444444444444444444",
                "cause": "The package is absent from the active environment.",
                "claim_kind": "grounded",
                "fact_ids": ["fact_11111111111111111111111111111111"],
                "evidence_ids": ["evidence_22222222222222222222222222222222"],
                "confidence": 0.9,
                "applicability": "The traceback comes from the active interpreter.",
                "counterevidence_or_limits": "The active environment has not yet been inspected.",
            }
        ],
        "missing_information": ["The intended virtual environment is unknown."],
        "checks": [valid_command()],
        "fixes": [valid_command()],
        "verification_steps": [valid_command()],
        "confidence": 0.86,
        "limitations": ["No live environment was inspected."],
        "recap_text": "Confirm the active interpreter before changing its environment.",
    }


def legacy_record() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "case_id": "case_0123456789abcdef0123456789abcdef",
        "category": "dependency_environment",
        "observed_facts": ["Python raised ModuleNotFoundError."],
        "root_cause_candidates": [
            {
                "cause": "The package is absent from the active environment.",
                "supporting_facts": ["pip show did not find the package."],
                "confidence": 0.9,
            }
        ],
        "missing_information": ["The intended virtual environment is unknown."],
        "checks": [{**valid_command(), "platform": "windows-powershell"}],
        "fixes": [{**valid_command(), "platform": "windows-powershell"}],
        "verification_steps": [{**valid_command(), "platform": "windows-powershell"}],
        "confidence": 0.86,
        "limitations": ["No live environment was inspected."],
        "recap_text": "Confirm the active interpreter before changing its environment.",
        "citations": [
            {
                "source_id": "python-exceptions",
                "title": "Python exceptions",
                "url": "https://docs.python.org/3/library/exceptions.html",
                "locator": "ModuleNotFoundError",
                "excerpt": "Module import failed.",
            }
        ],
    }


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (ObservedFact, valid_record()["observed_facts"][0]),  # type: ignore[index]
        (EvidenceAnchor, valid_record()["evidence"][0]),  # type: ignore[index]
        (SupportLink, valid_record()["support_links"][0]),  # type: ignore[index]
        (RootCauseCandidate, valid_record()["root_cause_candidates"][0]),  # type: ignore[index]
    ],
)
def test_v110_nested_contracts_reject_extra_fields(
    model: type[object], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({**payload, "unexpected": True})  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("path", "wrong_value"),
    [
        (("observed_facts", 0, "confidence"), "1.0"),
        (("evidence", 0, "relevance_score"), "0.95"),
        (("root_cause_candidates", 0, "fact_ids"), "fact_not_a_list"),
    ],
)
def test_v110_rejects_wrong_primitive_types(path: tuple[object, ...], wrong_value: object) -> None:
    payload = deepcopy(valid_record())
    target: object = payload
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = wrong_value  # type: ignore[index]

    with pytest.raises(ValidationError):
        DiagnosisRecord.model_validate(payload)


@pytest.mark.parametrize("collection", ["observed_facts", "evidence", "root_cause_candidates"])
def test_v110_rejects_duplicate_stable_ids(collection: str) -> None:
    payload = valid_record()
    payload[collection] = [*payload[collection], deepcopy(payload[collection][0])]  # type: ignore[index]

    with pytest.raises(ValidationError, match="duplicate"):
        DiagnosisRecord.model_validate(payload)


@pytest.mark.parametrize(
    ("container", "field"),
    [
        ("support_links", "fact_ids"),
        ("support_links", "evidence_ids"),
        ("root_cause_candidates", "fact_ids"),
        ("root_cause_candidates", "evidence_ids"),
    ],
)
def test_v110_rejects_dangling_graph_links(container: str, field: str) -> None:
    payload = valid_record()
    payload[container][0][field] = [f"{field[:-4]}_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]  # type: ignore[index]

    with pytest.raises(ValidationError, match="unknown"):
        DiagnosisRecord.model_validate(payload)


def test_grounded_candidate_requires_fact_evidence_and_matching_support_link() -> None:
    payload = valid_record()
    payload["root_cause_candidates"][0]["evidence_ids"] = []  # type: ignore[index]
    with pytest.raises(ValidationError, match="grounded"):
        DiagnosisRecord.model_validate(payload)

    payload = valid_record()
    payload["support_links"] = []
    with pytest.raises(ValidationError, match="support"):
        DiagnosisRecord.model_validate(payload)


def test_inference_candidate_may_be_ungrounded_but_requires_limits() -> None:
    payload = valid_record()
    candidate = payload["root_cause_candidates"][0]  # type: ignore[index]
    candidate.update(
        claim_kind="inference",
        evidence_ids=[],
        applicability="Only if this interpreter owns the failing process.",
        counterevidence_or_limits="Package presence has not been checked.",
    )
    payload["support_links"] = []

    assert DiagnosisRecord.model_validate(payload).root_cause_candidates[0].claim_kind == "inference"

    candidate["counterevidence_or_limits"] = " "
    with pytest.raises(ValidationError):
        DiagnosisRecord.model_validate(payload)


def test_committed_v110_schema_matches_canonical_generated_schema() -> None:
    committed = json.loads(
        (ROOT / "contracts" / "diagnosis-record-v1.1.schema.json").read_text(encoding="utf-8")
    )
    assert committed == diagnosis_schema()


def test_frozen_v100_loader_rejects_v110_fields() -> None:
    payload = legacy_record()
    payload["evidence"] = []

    with pytest.raises(ValidationError):
        DiagnosisRecordV100.model_validate(payload)


def test_v100_migration_is_deterministic_and_conservative() -> None:
    legacy = DiagnosisRecordV100.model_validate(legacy_record())

    first = migrate_v100_to_v110(legacy)
    second = migrate_v100_to_v110(legacy)

    assert first.model_dump_json() == second.model_dump_json()
    assert first.schema_version == "1.1.0"
    assert first.observed_facts[0].fact_id.startswith("fact_")
    assert first.evidence[0].evidence_id.startswith("evidence_")
    assert first.root_cause_candidates[0].candidate_id.startswith("candidate_")
    assert first.root_cause_candidates[0].claim_kind == "inference"
    assert first.root_cause_candidates[0].evidence_ids == []
    assert first.support_links == []
