from __future__ import annotations

from pathlib import Path

import pytest

from debugmate.hashing import sha256_bytes
from debugmate.results import audio as audio_module
from debugmate.results import consistency as consistency_module
from debugmate.results.audio import TtsFallbackChain, TrustedCandidateRoot
from debugmate.results.card import render_card
from debugmate.results.font import prepare_generation_context
from debugmate.results.loader import load_verified_outcome
from debugmate.results.media import MediaProbe
from debugmate.results.presentation import build_presentation
from debugmate.results.recap import compose_recap
from debugmate.results.report import render_citations, render_report
from debugmate.results.tts.base import AudioPayload, RateProfile, TtsRequestIdentity


def _font_copy(tmp_path: Path) -> Path:
    source = next(
        path
        for path in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf"))
        if path.is_file()
    )
    target = tmp_path / "fonts" / source.name
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    return target


class _AudioAdapter:
    backend = "dify"

    def synthesize(self, _text, request: TtsRequestIdentity, rate: RateProfile) -> AudioPayload:
        return AudioPayload(
            backend=self.backend,
            rate_profile=rate,
            request_identity=request,
            audio_bytes=b"\xff\xfb" + b"test-audio" * 32,
            voice=None,
        )


class _FailAdapter:
    def __init__(self, backend: str) -> None:
        self.backend = backend

    def synthesize(self, *_arguments: object) -> AudioPayload:
        raise RuntimeError("offline")


def _probe(path: Path, **_kwargs: object) -> MediaProbe:
    return MediaProbe(
        duration_ms=45_000,
        codec="mp3",
        channels=1,
        bytes=path.stat().st_size,
        sha256=sha256_bytes(path.read_bytes()),
    )


@pytest.fixture
def candidates(completed_source_bundle, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    outcome, source_path = completed_source_bundle
    font = _font_copy(tmp_path)
    context = prepare_generation_context(
        project_root=tmp_path,
        project_font_candidates=(f"fonts/{font.name}",),
        windows_font_candidates=(),
    )
    source = load_verified_outcome(outcome, evidence_root=source_path.parents[1])
    presentation = build_presentation(source, context)
    report = render_report(presentation)
    citations = render_citations(presentation)
    recap = compose_recap(presentation)
    card = render_card(presentation, context, target=tmp_path / "card.png")
    monkeypatch.setattr(audio_module, "probe_mp3", _probe)
    monkeypatch.setattr(audio_module, "canonicalize_mp3", lambda value, **_kwargs: value)
    monkeypatch.setattr(consistency_module, "probe_mp3", _probe)
    request = TtsRequestIdentity(
        case_id=recap.identity.case_id,
        source_run_id=recap.identity.source_run_id,
        diagnosis_sha256=recap.identity.diagnosis_sha256,
        generation_version=recap.identity.generation_version,
        recap_sha256=recap.sha256,
    )
    audio = TtsFallbackChain(
        (_AudioAdapter(), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
    ).synthesize(recap, request, TrustedCandidateRoot.for_testing(tmp_path / "private"))
    return source, presentation, report, citations, card, recap, audio


def test_gate_revalidates_all_modalities_and_consumes_only_one_verified_audio_handoff(candidates):
    source, presentation, report, citations, card, recap, audio = candidates

    validated = consistency_module.validate_result_candidates(
        source, presentation, report, citations, card, recap, audio
    )

    assert validated.identity == presentation.identity
    assert validated.availability.all() is True
    assert validated.status.value == "completed"
    assert validated.audio_bytes == b"\xff\xfb" + b"test-audio" * 32
    assert not hasattr(validated, "card_path")
    with pytest.raises(Exception):
        audio.handoff.take_verified_bytes(audio.audio)


@pytest.mark.parametrize("field", ["case_id", "source_run_id", "diagnosis_sha256", "generation_version"])
def test_gate_rejects_each_shared_identity_drift(candidates, field: str):
    source, presentation, report, citations, card, recap, audio = candidates
    bad_identity = report.identity.model_copy(update={field: getattr(report.identity, field)[:-1] + "0"})
    forged_report = report.model_copy(update={"identity": bad_identity})

    with pytest.raises(consistency_module.ResultConsistencyError, match="artifact_identity_mismatch"):
        consistency_module.validate_result_candidates(
            source, presentation, forged_report, citations, card, recap, audio
        )


def test_gate_rejects_modified_card_before_publication(candidates):
    source, presentation, report, citations, card, recap, audio = candidates
    card.path.write_bytes(card.path.read_bytes() + b"tamper")

    with pytest.raises(consistency_module.ResultConsistencyError, match="card_verify_failed"):
        consistency_module.validate_result_candidates(
            source, presentation, report, citations, card, recap, audio
        )


def test_gate_allows_only_explicit_audio_partial(candidates):
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
        TrustedCandidateRoot.for_testing(Path(card.path).parent / "partial-private"),
    )

    validated = consistency_module.validate_result_candidates(
        source, presentation, report, citations, card, recap, unavailable
    )

    assert validated.status.value == "partial"
    assert validated.failure.failed_stage == "audio"
    assert validated.availability.audio is False
