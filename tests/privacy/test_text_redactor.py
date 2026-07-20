import pytest

from debugmate.contracts import new_case_id
from debugmate.privacy.models import InputEnvelope, SecretKind
from debugmate.privacy.text_redactor import apply_candidates, redact_input, scan_text


def valid_input(**updates: object) -> InputEnvelope:
    values: dict[str, object] = {
        "case_id": new_case_id(),
        "error_text": "RuntimeError: demo failure",
        "screenshot_path": None,
        "code": None,
        "environment": {},
    }
    values.update(updates)
    return InputEnvelope.model_validate(values)


@pytest.mark.parametrize(
    ("sample", "marker"),
    [
        ("token=ghp_abcdefghijklmnopqrstuvwxyz123456", "[REDACTED:TOKEN]"),
        ("mail=user@example.com", "[REDACTED:EMAIL]"),
        (r"C:\Users\student\project\main.py", "[REDACTED:WINDOWS_PATH]"),
        ("/home/student/project/main.py", "[REDACTED:UNIX_PATH]"),
        ("password = demo_password_123", "[REDACTED:PASSWORD]"),
        ("host=192.168.10.12", "[REDACTED:PRIVATE_HOST]"),
    ],
)
def test_sensitive_values_are_replaced(sample: str, marker: str) -> None:
    preview = redact_input(valid_input(error_text=sample))
    assert preview.redacted.error_text is not None
    assert marker in preview.redacted.error_text
    assert sample not in preview.model_dump_json()


def test_crlf_and_chinese_context_are_preserved_around_redaction() -> None:
    value = "追踪信息：\r\n  File C:\\Users\\student\\main.py\r\n错误结束"
    preview = redact_input(valid_input(error_text=value))
    assert preview.redacted.error_text == (
        "追踪信息：\r\n  File [REDACTED:WINDOWS_PATH]\r\n错误结束"
    )


def test_higher_priority_password_rule_wins_overlap_with_token() -> None:
    value = "password=ghp_abcdefghijklmnopqrstuvwxyz123456"
    candidates = scan_text("error_text", value)
    assert len(candidates) == 1
    assert candidates[0].kind is SecretKind.PASSWORD
    assert apply_candidates(value, candidates) == "[REDACTED:PASSWORD]"


def test_private_key_priority_wins_even_in_password_named_field() -> None:
    value = "-----BEGIN PRIVATE KEY-----\nabc123\n-----END PRIVATE KEY-----"
    candidates = scan_text("environment.password", value)
    assert len(candidates) == 1
    assert candidates[0].kind is SecretKind.PRIVATE_KEY


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        ("Authorization: Bearer abcdefghijklmnop", SecretKind.TOKEN),
        ("username=private_student", SecretKind.USERNAME),
        ("abcDEF1234567890abcDEF1234567890", SecretKind.HIGH_ENTROPY),
    ],
)
def test_remaining_ordered_rules_are_active(value: str, kind: SecretKind) -> None:
    assert [item.kind for item in scan_text("error_text", value)] == [kind]


def test_all_text_fields_are_scanned_without_retaining_sentinel() -> None:
    sentinel_email = "student@example.com"
    sentinel_user = "private_student"
    preview = redact_input(
        valid_input(
            error_text="ImportError",
            code=f"notify('{sentinel_email}')",
            environment={"USERNAME": sentinel_user, "PYTHON": "3.13.5"},
        )
    )
    assert preview.redacted.code == "notify('[REDACTED:EMAIL]')"
    assert preview.redacted.environment == {
        "USERNAME": "[REDACTED:USERNAME]",
        "PYTHON": "3.13.5",
    }
    serialized = preview.model_dump_json()
    assert sentinel_email not in serialized
    assert sentinel_user not in serialized
    assert preview.audit.candidate_count == 2


def test_prefixed_secret_environment_keys_are_redacted_even_for_short_values() -> None:
    preview = redact_input(
        valid_input(
            environment={
                "OPENAI_API_KEY": "short_key_123",
                "DB_PASSWORD": "short_password",
            }
        )
    )
    assert preview.redacted.environment == {
        "DB_PASSWORD": "[REDACTED:PASSWORD]",
        "OPENAI_API_KEY": "[REDACTED:TOKEN]",
    }


def test_empty_optional_fields_stay_empty() -> None:
    preview = redact_input(valid_input(code=None, environment={}))
    assert preview.redacted.code is None
    assert preview.redacted.environment == {}
    assert preview.redacted.redacted_screenshot_path is None
    assert preview.redacted.redacted_screenshot_sha256 is None


def test_same_input_has_stable_source_and_preview_hashes() -> None:
    value = valid_input(error_text="mail=student@example.com")
    first = redact_input(value)
    second = redact_input(value)
    assert first.source_hash == second.source_hash
    assert first.preview_hash == second.preview_hash
    assert first.created_at_utc <= second.created_at_utc


def test_candidates_are_value_free_and_deterministically_ordered() -> None:
    value = valid_input(
        error_text="mail=b@example.com then a@example.com",
        code="token=ghp_abcdefghijklmnopqrstuvwxyz123456",
    )
    preview = redact_input(value)
    ordering = [
        (item.field, item.start, item.end, item.rule_id) for item in preview.candidates
    ]
    assert ordering == sorted(ordering)
    assert all(len(item.match_sha256) == 64 for item in preview.candidates)
    assert "b@example.com" not in preview.model_dump_json()
    assert "a@example.com" not in preview.model_dump_json()
