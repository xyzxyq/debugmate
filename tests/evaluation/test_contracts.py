from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.evaluation.contracts import (
    CaseEvaluation,
    CaseRegistry,
    EvaluationPath,
    Phase8SourceEvidence,
)


CASES_PATH = Path("evaluation/phase9/cases.json")


def load_registry() -> CaseRegistry:
    return CaseRegistry.model_validate_json(CASES_PATH.read_text(encoding="utf-8"))


def test_strict_models_reject_extra_fields_and_invalid_hashes() -> None:
    registry = load_registry()
    row = registry.cases[0].model_dump(mode="json")

    with pytest.raises(ValidationError):
        CaseEvaluation.model_validate({**row, "unexpected": "forbidden"})

    bad_hash = {**row, "source_sha256": "not-a-sha256"}
    with pytest.raises(ValidationError):
        CaseEvaluation.model_validate(bad_hash)


@pytest.mark.parametrize(
    "value",
    [
        "../evidence/dify-live/phase8/manifest.json",
        "evidence\\dify-live\\phase8\\manifest.json",
        "evidence/course-v0.1/manifest.json",
        "evidence/dify-live/phase8/approval.json",
        "deliverables/phase10/final-video.mp4",
    ],
)
def test_repository_references_reject_non_current_or_unsafe_paths(value: str) -> None:
    with pytest.raises(ValidationError):
        EvaluationPath(path=value)


def test_live_case_requires_current_phase8_summary_and_formal_manifest() -> None:
    registry = load_registry()
    live = registry.case_for("P9-C01-live-private")

    assert live.actual_status == "blocked"
    assert isinstance(live.phase8_source, Phase8SourceEvidence)
    assert live.phase8_source.summary_path == ".planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md"
    assert live.phase8_source.manifest_path == "evidence/dify-live/phase8/manifest.json"
    assert live.can_claim_live_success() is False


def test_duplicate_case_keys_and_unbounded_fields_are_rejected() -> None:
    registry = load_registry()
    data = registry.model_dump(mode="json")
    data["cases"].append(data["cases"][0])

    with pytest.raises(ValidationError):
        CaseRegistry.model_validate(data)

    long_limitation = "x" * 1_001
    data = registry.model_dump(mode="json")
    data["cases"][0]["limitation"] = long_limitation
    with pytest.raises(ValidationError):
        CaseRegistry.model_validate(data)
