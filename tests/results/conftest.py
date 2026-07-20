from __future__ import annotations

import json
from pathlib import Path

import pytest

from debugmate.diagnosis.workflow import DiagnosisRunOutcome
from debugmate.evidence import verify_bundle
from debugmate.hashing import sha256_bytes
from debugmate.results import audio as audio_module
from debugmate.results import verifier as verifier_module
from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
from debugmate.results.card import render_card
from debugmate.results.font import prepare_generation_context
from debugmate.results.loader import load_verified_outcome
from debugmate.results.media import MediaProbe
from debugmate.results.presentation import build_presentation
from debugmate.results.recap import compose_recap
from debugmate.results.report import render_citations, render_report
from debugmate.results.tts.base import AudioPayload, RateProfile, TtsRequestIdentity


@pytest.fixture
def replay_root() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "replay" / "module-not-found"


@pytest.fixture
def completed_source_bundle(replay_root: Path) -> tuple[DiagnosisRunOutcome, Path]:
    outcome = DiagnosisRunOutcome.model_validate_json(
        (replay_root / "outcome.json").read_text(encoding="utf-8"), strict=True
    )
    source = replay_root / "source" / outcome.case_id / outcome.run_id
    assert verify_bundle(source).ok is True
    return outcome, source


@pytest.fixture
def clone_manifest(completed_source_bundle, tmp_path: Path):
    _, source = completed_source_bundle
    payload = json.loads((source / "manifest.json").read_text(encoding="utf-8"))

    def clone(**changes: object) -> Path:
        target = tmp_path / "manifest.json"
        target.write_text(
            json.dumps({**payload, **changes}, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        return target

    return clone


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
    monkeypatch.setattr(verifier_module, "probe_mp3", _probe)
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
