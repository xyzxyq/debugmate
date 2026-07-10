from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from debugmate.contracts import new_case_id
from debugmate.privacy.models import (
    ApprovedRedactedInput,
    InputEnvelope,
    PreviewBundle,
    RedactedFields,
    RedactionAudit,
    SecretCandidate,
    SecretKind,
)


def candidate() -> SecretCandidate:
    return SecretCandidate(
        kind=SecretKind.EMAIL,
        field="error_text",
        start=5,
        end=21,
        rule_id="EMAIL",
        confidence=0.99,
        match_sha256="a" * 64,
    )


def redacted_fields() -> RedactedFields:
    return RedactedFields(
        error_text="mail=[REDACTED:EMAIL]",
        code=None,
        environment={"python": "3.13"},
        redacted_screenshot_path=None,
        redacted_screenshot_sha256=None,
    )


def preview_bundle() -> PreviewBundle:
    item = candidate()
    return PreviewBundle(
        case_id=new_case_id(),
        redacted=redacted_fields(),
        candidates=[item],
        audit=RedactionAudit(
            candidate_count=1,
            counts_by_kind={SecretKind.EMAIL: 1},
        ),
        source_hash="b" * 64,
        preview_hash="c" * 64,
        rule_version="privacy-rules-v1",
        created_at_utc=datetime.now(UTC),
    )


def test_input_requires_text_or_screenshot() -> None:
    with pytest.raises(ValidationError):
        InputEnvelope(
            case_id=new_case_id(),
            error_text=None,
            screenshot_path=None,
            code="print('x')",
            environment={},
        )


@pytest.mark.parametrize(
    ("error_text", "screenshot_path"),
    [("Traceback", None), (None, "redacted.png")],
)
def test_input_accepts_text_or_screenshot(
    error_text: str | None, screenshot_path: str | None
) -> None:
    value = InputEnvelope(
        case_id=new_case_id(),
        error_text=error_text,
        screenshot_path=screenshot_path,
    )
    assert value.error_text == error_text
    assert value.screenshot_path == screenshot_path


def test_raw_input_repr_hides_sensitive_values() -> None:
    sentinel = "SENTINEL_DO_NOT_LOG"
    value = InputEnvelope(
        case_id=new_case_id(),
        error_text=f"token={sentinel}",
        screenshot_path=f"C:/Users/{sentinel}/error.png",
        code=f"password = '{sentinel}'",
        environment={"username": sentinel},
    )
    assert sentinel not in repr(value)


def test_candidate_never_contains_raw_value() -> None:
    fields = set(SecretCandidate.model_fields)
    assert "raw_value" not in fields
    assert "matched_text" not in fields
    assert set(candidate().model_dump()) == {
        "kind",
        "field",
        "start",
        "end",
        "rule_id",
        "confidence",
        "match_sha256",
    }


def test_models_round_trip_strict_json() -> None:
    preview = preview_bundle()
    restored = PreviewBundle.model_validate_json(preview.model_dump_json())
    assert restored == preview

    approved = ApprovedRedactedInput(
        case_id=preview.case_id,
        redacted=preview.redacted,
        preview_hash=preview.preview_hash,
        approval_id="approval-1",
        approval_signature="d" * 64,
        approved_at_utc=datetime.now(UTC),
    )
    assert ApprovedRedactedInput.model_validate_json(approved.model_dump_json()) == approved


def test_extra_fields_and_wrong_types_are_rejected() -> None:
    with pytest.raises(ValidationError):
        SecretCandidate.model_validate({**candidate().model_dump(), "raw_value": "secret"})

    with pytest.raises(ValidationError):
        SecretCandidate.model_validate({**candidate().model_dump(), "confidence": "0.99"})

    with pytest.raises(ValidationError):
        RedactionAudit(candidate_count="1", counts_by_kind={SecretKind.EMAIL: 1})


def test_candidate_spans_and_hashes_are_validated() -> None:
    with pytest.raises(ValidationError):
        SecretCandidate(
            kind=SecretKind.EMAIL,
            field="error_text",
            start=10,
            end=5,
            rule_id="EMAIL",
            confidence=0.9,
            match_sha256="a" * 64,
        )

    with pytest.raises(ValidationError):
        SecretCandidate.model_validate(
            {**candidate().model_dump(), "match_sha256": "not-a-hash"}
        )


def test_preview_candidates_must_be_ordered() -> None:
    first = candidate()
    second = first.model_copy(update={"start": 1, "end": 3, "match_sha256": "e" * 64})
    with pytest.raises(ValidationError):
        PreviewBundle.model_validate(
            {
                **preview_bundle().model_dump(),
                "candidates": [first.model_dump(), second.model_dump()],
            }
        )
