from __future__ import annotations

import pytest


def test_gate_revalidates_all_modalities_without_exposing_a_candidate_path(candidates):
    from debugmate.results import consistency as consistency_module

    source, presentation, report, citations, card, recap, audio = candidates

    validated = consistency_module.validate_result_candidates(
        source, presentation, report, citations, card, recap, audio
    )

    assert validated.identity == presentation.identity
    assert validated.availability.all() is True
    assert validated.status.value == "completed"
    assert validated.audio == audio.audio
    assert not hasattr(validated, "card_path")
    assert not hasattr(validated, "audio_bytes")


@pytest.mark.parametrize(
    "field",
    [
        "case_id",
        "source_run_id",
        "diagnosis_sha256",
        "schema_version",
        "generation_version",
    ],
)
def test_gate_rejects_each_shared_identity_drift(candidates, field: str):
    from debugmate.results import consistency as consistency_module

    source, presentation, report, citations, card, recap, audio = candidates
    original = getattr(report.identity, field)
    replacement = (
        "1.1.1"
        if field == "schema_version"
        else original[:-1] + ("f" if original[-1] != "f" else "e")
    )
    bad_identity = report.identity.model_copy(update={field: replacement})
    forged_report = report.model_copy(update={"identity": bad_identity})

    with pytest.raises(
        consistency_module.ResultConsistencyError,
        match="(?:artifact_identity_mismatch|report_verify_failed)",
    ):
        consistency_module.validate_result_candidates(
            source, presentation, forged_report, citations, card, recap, audio
        )


def test_gate_rejects_forged_citation_bytes_and_recap_text(candidates):
    from debugmate.results import consistency as consistency_module

    source, presentation, report, citations, card, recap, audio = candidates
    forged_citations = citations.model_copy(update={"json_bytes": b"{}"})
    with pytest.raises(consistency_module.ResultConsistencyError, match="citation_verify_failed"):
        consistency_module.validate_result_candidates(
            source, presentation, report, forged_citations, card, recap, audio
        )

    forged_recap = recap.model_copy(update={"text": recap.text + " unverified claim"})
    with pytest.raises(consistency_module.ResultConsistencyError, match="recap_verify_failed"):
        consistency_module.validate_result_candidates(
            source, presentation, report, citations, card, forged_recap, audio
        )


def test_gate_rejects_modified_card_before_publication(candidates):
    from debugmate.results import consistency as consistency_module

    source, presentation, report, citations, card, recap, audio = candidates
    card.path.write_bytes(card.path.read_bytes() + b"tamper")

    with pytest.raises(consistency_module.ResultConsistencyError, match="card_verify_failed"):
        consistency_module.validate_result_candidates(
            source, presentation, report, citations, card, recap, audio
        )


def test_gate_allows_only_explicit_audio_partial(candidates):
    from tests.results.conftest import _FailAdapter

    from debugmate.results import consistency as consistency_module
    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.tts.base import TtsRequestIdentity

    source, presentation, report, citations, card, recap, _audio = candidates
    unavailable = TtsFallbackChain(
        (_FailAdapter("dify"), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
    ).synthesize(
        recap,
        TtsRequestIdentity(
            case_id=recap.identity.case_id,
            source_run_id=recap.identity.source_run_id,
            diagnosis_sha256=recap.identity.diagnosis_sha256,
            generation_version=recap.identity.generation_version,
            recap_sha256=recap.sha256,
        ),
        TrustedCandidateRoot.for_testing(card.path.parent / "partial-private"),
    )

    validated = consistency_module.validate_result_candidates(
        source, presentation, report, citations, card, recap, unavailable
    )

    assert validated.status.value == "partial"
    assert validated.failure.failed_stage == "audio"
    assert validated.availability.audio is False
