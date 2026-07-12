from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.adapters.base import DiagnosisBackend
from debugmate.adapters.fixture import (
    FixtureBackend,
    FixtureCapabilityUnavailable,
    FixtureNotFound,
)
from debugmate.contracts import CapabilityStatus, DiagnosisRecord, new_case_id

FIXTURES_ROOT = Path(__file__).parents[1] / "fixtures" / "cases"


def test_fixture_backend_implements_runtime_protocol() -> None:
    backend = FixtureBackend(FIXTURES_ROOT)

    assert isinstance(backend, DiagnosisBackend)


def test_fixture_diagnosis_is_schema_valid_and_propagates_case_id() -> None:
    backend = FixtureBackend(FIXTURES_ROOT)
    case_id = new_case_id()

    result = backend.run_workflow({"case_id": case_id}, user="debugmate-test")

    assert result.backend == "fixture"
    assert result.run_id == "fixture:module_not_found"
    assert isinstance(result.diagnosis, DiagnosisRecord)
    assert result.diagnosis.case_id == case_id
    assert result.diagnosis.category.value == "dependency_environment"
    assert "demo_missing_pkg" in result.diagnosis.observed_facts[0].value


def test_fixture_content_is_stable_apart_from_case_id() -> None:
    backend = FixtureBackend(FIXTURES_ROOT)

    first = backend.run_workflow({"case_id": new_case_id()}, user="one").diagnosis.model_dump()
    second = backend.run_workflow({"case_id": new_case_id()}, user="two").diagnosis.model_dump()
    first.pop("case_id")
    second.pop("case_id")

    assert first == second


def test_fixture_input_uses_explicit_redacted_windows_path() -> None:
    payload = json.loads(
        (FIXTURES_ROOT / "module_not_found" / "input.json").read_text(encoding="utf-8")
    )

    assert payload["error_type"] == "ModuleNotFoundError"
    assert payload["path"] == "[REDACTED:WINDOWS_PATH]"
    assert "demo_missing_pkg" in payload["error_text"]


def test_missing_fixture_raises_typed_error() -> None:
    backend = FixtureBackend(FIXTURES_ROOT, case_name="does_not_exist")

    with pytest.raises(FixtureNotFound, match="does_not_exist"):
        backend.run_workflow({"case_id": new_case_id()}, user="debugmate-test")


def test_invalid_case_id_is_rejected() -> None:
    backend = FixtureBackend(FIXTURES_ROOT)

    with pytest.raises(ValidationError):
        backend.run_workflow({"case_id": "case_invalid"}, user="debugmate-test")


def test_cloud_only_fixture_capabilities_are_never_pass() -> None:
    probe = FixtureBackend(FIXTURES_ROOT).capability_probe()

    assert probe.backend == "fixture"
    assert set(probe.capabilities) == {f"C{index:02d}" for index in range(1, 8)}
    assert set(probe.capabilities.values()) == {CapabilityStatus.NOT_TESTED}


def test_fixture_tts_is_explicitly_unavailable() -> None:
    backend = FixtureBackend(FIXTURES_ROOT)

    with pytest.raises(FixtureCapabilityUnavailable, match="audio"):
        backend.synthesize_audio("hello", user="debugmate-test")


def test_fixture_upload_requires_an_existing_file(tmp_path: Path) -> None:
    backend = FixtureBackend(FIXTURES_ROOT)

    with pytest.raises(FileNotFoundError):
        backend.upload_file(tmp_path / "missing.png", user="debugmate-test")

    source = tmp_path / "fixture.txt"
    source.write_text("fictional", encoding="utf-8")
    result = backend.upload_file(source, user="debugmate-test")
    assert result.backend == "fixture"
    assert result.file_id == "fixture:fixture.txt"


def test_fixture_files_and_results_contain_no_sensitive_patterns() -> None:
    backend = FixtureBackend(FIXTURES_ROOT)
    result = backend.run_workflow({"case_id": new_case_id()}, user="debugmate-test")
    tracked_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (FIXTURES_ROOT / "module_not_found").glob("*.json")
    )
    serialized = result.diagnosis.model_dump_json()
    forbidden = [
        r"sk-[A-Za-z0-9_-]{8,}",
        r"Bearer ",
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        r"20795",
        r"DIFY_API_KEY\s*[:=]\s*[^\"\s]+",
    ]

    for pattern in forbidden:
        assert re.search(pattern, tracked_text + serialized) is None
