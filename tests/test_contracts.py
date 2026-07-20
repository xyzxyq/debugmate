from __future__ import annotations

import re

import pytest
from pydantic import ValidationError
from tests.diagnosis.test_contract_v11 import valid_command, valid_record

from debugmate.contracts import (
    CASE_ID_PATTERN,
    SCHEMA_VERSION,
    CapabilityStatus,
    CommandStep,
    DiagnosisRecord,
    ErrorCategory,
    diagnosis_schema,
    new_case_id,
    schema_sha256,
)


def test_new_case_ids_are_unique_and_match_contract() -> None:
    case_ids = {new_case_id() for _ in range(50)}

    assert len(case_ids) == 50
    assert all(re.fullmatch(CASE_ID_PATTERN, case_id) for case_id in case_ids)


def test_diagnosis_record_round_trips_strictly() -> None:
    record = DiagnosisRecord.model_validate(valid_record())
    restored = DiagnosisRecord.model_validate_json(record.model_dump_json())

    assert restored == record
    assert record.category is ErrorCategory.DEPENDENCY_ENVIRONMENT


def test_diagnosis_record_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        DiagnosisRecord.model_validate({**valid_record(), "unexpected": True})


@pytest.mark.parametrize(
    "case_id",
    [
        "case_0123456789ABCDEF0123456789ABCDEF",
        "case_short",
        "0123456789abcdef0123456789abcdef",
        "case_0123456789abcdef0123456789abcdeg",
    ],
)
def test_invalid_case_ids_are_rejected(case_id: str) -> None:
    with pytest.raises(ValidationError):
        DiagnosisRecord.model_validate({**valid_record(), "case_id": case_id})


@pytest.mark.parametrize("confidence", ["0.8", -0.01, 1.01])
def test_invalid_confidence_is_rejected(confidence: object) -> None:
    with pytest.raises(ValidationError):
        DiagnosisRecord.model_validate({**valid_record(), "confidence": confidence})


def test_command_requires_rollback_and_has_no_execution_api() -> None:
    payload = valid_command()
    payload.pop("rollback")

    with pytest.raises(ValidationError):
        CommandStep.model_validate(payload)

    command = CommandStep.model_validate(valid_command())
    assert not hasattr(command, "execute")
    assert not hasattr(command, "run")


def test_missing_field_and_schema_version_mismatch_are_rejected() -> None:
    missing = valid_record()
    missing.pop("recap_text")

    with pytest.raises(ValidationError):
        DiagnosisRecord.model_validate(missing)
    with pytest.raises(ValidationError):
        DiagnosisRecord.model_validate({**valid_record(), "schema_version": "2.0.0"})


def test_capability_status_values_are_stable() -> None:
    assert [status.value for status in CapabilityStatus] == [
        "pass",
        "fail",
        "blocked",
        "not-tested",
    ]


def test_generated_schema_and_hash_are_deterministic() -> None:
    assert SCHEMA_VERSION == "1.1.0"
    assert diagnosis_schema() == DiagnosisRecord.model_json_schema()
    assert schema_sha256() == schema_sha256()
    assert re.fullmatch(r"[0-9a-f]{64}", schema_sha256())
