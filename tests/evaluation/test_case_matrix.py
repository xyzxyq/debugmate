from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.evaluation.contracts import CaseRegistry


CASES_PATH = Path("evaluation/phase9/cases.json")


def load_registry() -> CaseRegistry:
    return CaseRegistry.model_validate_json(CASES_PATH.read_text(encoding="utf-8"))


def test_registry_has_exactly_four_locked_cases_and_coverage_tags() -> None:
    registry = load_registry()

    assert [case.case_id for case in registry.cases] == [
        "P9-C01-live-private",
        "P9-C02-insufficient",
        "P9-C03-long-replay",
        "P9-C04-fallback-failure",
    ]
    assert registry.coverage_tags == {
        "live_success",
        "insufficient_data",
        "long_content",
        "privacy",
        "fallback_or_failure",
    }


def test_insufficient_information_cannot_claim_diagnosis_artifacts() -> None:
    registry = load_registry()
    insufficient = registry.case_for("P9-C02-insufficient")

    assert insufficient.actual_status == "insufficient_data"
    assert insufficient.availability.report is False
    assert insufficient.availability.card_png is False
    assert insufficient.availability.recap_mp3 is False
    assert insufficient.availability.evidence_zip is False


def test_local_fallback_partial_row_has_only_established_audio_unavailable_state() -> None:
    registry = load_registry()
    fallback = registry.case_for("P9-C04-fallback-failure")

    assert fallback.execution_backend == "local_fallback"
    assert fallback.actual_status == "partial"
    assert fallback.availability.report is True
    assert fallback.availability.card_png is True
    assert fallback.availability.recap_mp3 is True
    assert fallback.availability.evidence_zip is True
    assert fallback.availability.audio is False
    assert fallback.retry_scope == "audio"


def test_registry_rejects_fabricated_insufficient_artifact() -> None:
    registry = load_registry()
    data = registry.model_dump(mode="json")
    insufficient = next(case for case in data["cases"] if case["case_id"] == "P9-C02-insufficient")
    insufficient["availability"]["report"] = True

    with pytest.raises(ValidationError):
        CaseRegistry.model_validate(data)
