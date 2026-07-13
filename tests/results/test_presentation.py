from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.hashing import canonical_json_bytes
from debugmate.results.font import prepare_generation_context
from debugmate.results.loader import load_verified_outcome
from debugmate.results.presentation import PresentationBuildError, build_presentation


def _loaded(completed_source_bundle):
    outcome, source = completed_source_bundle
    return load_verified_outcome(outcome, evidence_root=source.parents[1])


def _context(tmp_path: Path):
    font = tmp_path / "assets" / "fonts" / "course.ttf"
    font.parent.mkdir(parents=True)
    font.write_bytes(b"debugmate-fictional-course-font-v1")
    return prepare_generation_context(
        project_root=tmp_path,
        project_font_candidates=("assets/fonts/course.ttf",),
        windows_font_candidates=(),
    )


def test_projection_is_frozen_deterministic_and_binds_complete_context(
    completed_source_bundle, tmp_path: Path
) -> None:
    loaded = _loaded(completed_source_bundle)
    context = _context(tmp_path)

    first = build_presentation(loaded, context)
    second = build_presentation(loaded, context)

    assert canonical_json_bytes(first.model_dump(mode="json")) == canonical_json_bytes(
        second.model_dump(mode="json")
    )
    assert first.identity.case_id == loaded.case_id
    assert first.identity.source_run_id == loaded.source_run_id
    assert first.identity.diagnosis_sha256 == loaded.diagnosis_sha256
    assert first.identity.generation_version == context.generation_profile.generation_version
    assert first.report_contract_version == context.generation_profile.report_contract_version
    assert first.card_contract_version == context.generation_profile.card_contract_version
    assert first.recap_contract_version == context.generation_profile.recap_contract_version
    assert first.font_sha256 == context.resolved_font.sha256
    with pytest.raises(ValidationError):
        first.confidence = 0.1


def test_projection_retains_ids_relations_and_technical_literals(
    completed_source_bundle, tmp_path: Path
) -> None:
    loaded = _loaded(completed_source_bundle)
    presentation = build_presentation(loaded, _context(tmp_path))
    diagnosis = loaded.diagnosis

    assert [item.fact_id for item in presentation.observed_facts] == sorted(
        item.fact_id for item in diagnosis.observed_facts
    )
    assert [item.evidence_id for item in presentation.citations] == sorted(
        item.evidence_id for item in diagnosis.evidence
    )
    assert {item.value for item in presentation.observed_facts} == {
        item.value for item in diagnosis.observed_facts
    }
    assert [item.command for item in presentation.checks] == [
        item.command for item in diagnosis.checks
    ]
    assert [item.command for item in presentation.fixes] == [
        item.command for item in diagnosis.fixes
    ]
    assert [item.command for item in presentation.verification_steps] == [
        item.command for item in diagnosis.verification_steps
    ]
    assert presentation.recap_text == diagnosis.recap_text
    assert presentation.category == diagnosis.category


@pytest.mark.parametrize("bad_source", [None, {}, object()])
def test_projection_accepts_only_loaded_source(
    completed_source_bundle, tmp_path: Path, bad_source: object
) -> None:
    with pytest.raises(PresentationBuildError, match="presentation_build_failed"):
        build_presentation(bad_source, _context(tmp_path))  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_context", [None, {}, object()])
def test_projection_requires_one_prepared_context(
    completed_source_bundle, tmp_path: Path, bad_context: object
) -> None:
    with pytest.raises(PresentationBuildError, match="presentation_build_failed"):
        build_presentation(_loaded(completed_source_bundle), bad_context)  # type: ignore[arg-type]


def test_projection_rejects_font_changed_after_preparation(
    completed_source_bundle, tmp_path: Path
) -> None:
    context = _context(tmp_path)
    context.resolved_font.path.write_bytes(b"changed-after-preparation")
    with pytest.raises(PresentationBuildError, match="presentation_build_failed") as caught:
        build_presentation(_loaded(completed_source_bundle), context)
    assert "changed-after-preparation" not in str(caught.value)


def test_projection_rejects_source_whose_diagnosis_no_longer_matches_outcome(
    completed_source_bundle, tmp_path: Path
) -> None:
    loaded = _loaded(completed_source_bundle)
    forged = loaded.model_copy(
        update={
            "diagnosis": loaded.diagnosis.model_copy(
                update={"recap_text": "forged presentation input"}
            )
        }
    )
    with pytest.raises(PresentationBuildError, match="presentation_build_failed"):
        build_presentation(forged, _context(tmp_path))
