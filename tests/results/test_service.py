from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from debugmate.diagnosis.extraction import FieldId
from debugmate.diagnosis.workflow import DiagnosisRunOutcome
from debugmate.results.consistency import validate_result_candidates
from debugmate.results.outcome_store import DiagnosisOutcomeStore
from debugmate.results.publisher import TrustedResultRoot, publish_result_bundle
from debugmate.results.verifier import ResultVerificationError


def _service(tmp_path: Path, candidates=None, *, composer=None, workflow=None):
    from debugmate.results.service import ResultApplicationService

    root = TrustedResultRoot.for_testing(tmp_path / "results")
    if composer is None:
        assert candidates is not None
        candidate = validate_result_candidates(*candidates)

        def compose(source, *, mode, fixture_id, fixture_name):
            assert source.case_id == candidate.identity.case_id
            return publish_result_bundle(
                root,
                candidate,
                mode=mode,
                fixture_id=fixture_id,
                fixture_name=fixture_name,
            )

    return ResultApplicationService(
        workflow=workflow,
        evidence_root=tmp_path / "evidence",
        outcome_store=DiagnosisOutcomeStore(tmp_path / "outcomes"),
        results_root=root,
        replay_root=Path(__file__).resolve().parents[2] / "fixtures" / "replay",
        composer=compose if composer is None else composer,
    )


def _dynamic_composer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, fail_audio_once: bool = False
):
    from tests.results.conftest import _AudioAdapter, _FailAdapter, _font_copy, _probe

    from debugmate.results import audio as audio_module
    from debugmate.results import verifier as verifier_module
    from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
    from debugmate.results.card import render_card
    from debugmate.results.font import prepare_generation_context
    from debugmate.results.presentation import build_presentation
    from debugmate.results.recap import compose_recap
    from debugmate.results.report import render_citations, render_report
    from debugmate.results.tts.base import TtsRequestIdentity

    root = TrustedResultRoot.for_testing(tmp_path / "results")
    font = _font_copy(tmp_path)
    context = prepare_generation_context(
        project_root=tmp_path,
        project_font_candidates=(f"fonts/{font.name}",),
        windows_font_candidates=(),
    )
    monkeypatch.setattr(audio_module, "probe_mp3", _probe)
    monkeypatch.setattr(audio_module, "canonicalize_mp3", lambda value, **_kwargs: value)
    monkeypatch.setattr(verifier_module, "probe_mp3", _probe)

    calls = 0

    def compose(source, *, mode, fixture_id, fixture_name):
        nonlocal calls
        calls += 1
        presentation = build_presentation(source, context)
        report = render_report(presentation)
        citations = render_citations(presentation)
        recap = compose_recap(presentation)
        card = render_card(
            presentation,
            context,
            target=tmp_path / "cards" / f"{source.source_run_id}-{calls}.png",
        )
        adapters = (
            (_FailAdapter("dify"), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
            if fail_audio_once and calls == 1
            else (_AudioAdapter(), _FailAdapter("edge_tts"), _FailAdapter("sapi"))
        )
        audio = TtsFallbackChain(
            adapters
        ).synthesize(
            recap,
            TtsRequestIdentity(
                case_id=recap.identity.case_id,
                source_run_id=recap.identity.source_run_id,
                diagnosis_sha256=recap.identity.diagnosis_sha256,
                generation_version=recap.identity.generation_version,
                recap_sha256=recap.sha256,
            ),
            TrustedCandidateRoot.for_testing(tmp_path / "private"),
        )
        candidate = validate_result_candidates(
            source, presentation, report, citations, card, recap, audio
        )
        return publish_result_bundle(
            root,
            candidate,
            mode=mode,
            fixture_id=fixture_id,
            fixture_name=fixture_name,
        )

    return root, compose


def test_indexed_replay_imports_complete_outcome_publishes_new_verified_result_and_restores(
    candidates, tmp_path: Path
) -> None:
    service = _service(tmp_path, candidates)

    state = service.load_replay("module-not-found")

    assert state.mode.value == "replay"
    assert state.status.value == "completed"
    assert state.result_id is not None
    assert state.fixture_id == "module-not-found"
    restored = service.restore_result(state.identity.case_id, state.result_id)
    assert restored == state


def test_replay_composition_failure_retains_verified_fixture_identity_in_safe_state(
    tmp_path: Path
) -> None:
    def broken_composer(*_arguments, **_kwargs):
        raise TypeError("adapter misuse")

    service = _service(tmp_path, composer=broken_composer)

    state = service.load_replay("module-not-found")

    assert state.status.value == "failed"
    assert state.mode.value == "replay"
    assert state.fixture_id == "module-not-found"
    assert state.fixture_name == "ModuleNotFoundError：缺少虚构依赖包"
    assert state.failure.code == "result_composition_failed"
    assert "adapter misuse" not in repr(state)


def test_replay_invalid_fixture_and_ui_supplied_outcome_become_safe_failures(
    candidates, completed_source_bundle, tmp_path: Path
) -> None:
    service = _service(tmp_path, candidates)
    invalid = service.load_replay("../module-not-found")
    assert invalid.status.value == "failed"
    assert invalid.failure.code == "replay_bundle_invalid"
    assert ".." not in repr(invalid)

    outcome, _source = completed_source_bundle
    with pytest.raises(TypeError):
        service.diagnose_and_compose(outcome)
    assert isinstance(outcome, DiagnosisRunOutcome)


def test_correction_fields_are_read_only_ordered_values_from_a_verified_stored_run(
    candidates, tmp_path: Path
) -> None:
    service = _service(tmp_path, candidates)
    state = service.load_replay("module-not-found")
    assert state.identity is not None

    fields = service.correction_fields(state.identity.source_run_id)

    assert fields.source_run_id == state.identity.source_run_id
    assert fields.values[0] == "ModuleNotFoundError"
    assert len(fields.values) == 6
    with pytest.raises(Exception) as invalid:
        service.correction_fields("run_" + "g" * 32)
    assert "C:" not in repr(invalid.value)


def test_restore_rereads_full_outcome_store_and_refuses_a_tampered_record(
    candidates, tmp_path: Path
) -> None:
    service = _service(tmp_path, candidates)
    state = service.load_replay("module-not-found")
    assert state.identity is not None and state.result_id is not None

    record = tmp_path / "outcomes" / state.identity.source_run_id / "outcome.json"
    os.chmod(record, stat.S_IWRITE)
    record.write_text("{}", encoding="utf-8")
    restored = service.restore_result(state.identity.case_id, state.result_id)
    assert restored.status.value == "failed"
    assert restored.failure.code == "outcome_store_invalid"
    assert not hasattr(restored, "path")


def test_replay_correction_requires_confirmation_and_preserves_old_source_and_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A correction derived from a replay remains honestly replay-labelled."""

    from tests.diagnosis.test_workflow_e2e import _rows, _workflow

    from debugmate.results.service import CorrectionDraft

    workflow, *_ = _workflow(_rows()[0], tmp_path)
    _root, composer = _dynamic_composer(tmp_path, monkeypatch)
    service = _service(tmp_path, composer=composer, workflow=workflow)
    original = service.load_replay("module-not-found")
    assert original.identity is not None and original.result_id is not None

    draft = CorrectionDraft(
        field_id=FieldId.EXCEPTION_TYPE,
        replacement="ImportError",
        reason="已根据脱敏回溯确认。",
    )
    unconfirmed = service.correct_and_compose(original.identity.source_run_id, draft, False)
    assert unconfirmed == original

    no_op = service.correct_and_compose(
        original.identity.source_run_id,
        CorrectionDraft(
            field_id=FieldId.EXCEPTION_TYPE,
            replacement="ModuleNotFoundError",
            reason="无需修改。",
        ),
        True,
    )
    assert no_op == original

    corrected = service.correct_and_compose(original.identity.source_run_id, draft, True)
    assert corrected.status.value == "completed"
    assert corrected.mode.value == "replay"
    assert corrected.identity is not None
    assert corrected.identity.source_run_id != original.identity.source_run_id
    assert corrected.result_id != original.result_id
    assert service.restore_result(original.identity.case_id, original.result_id) == original


def test_download_returns_only_one_shot_verified_bytes_not_a_server_path(
    candidates, tmp_path: Path
) -> None:
    service = _service(tmp_path, candidates)
    state = service.load_replay("module-not-found")
    assert state.identity is not None and state.result_id is not None

    download = service.resolve_download(state.identity.case_id, state.result_id, "report")
    assert download.member_id == "report"
    assert not hasattr(download, "path")
    assert download.read_bytes().startswith(b"# DebugMate")
    with pytest.raises(ResultVerificationError):
        download.read_bytes()


def test_live_approved_input_runs_phase3_once_then_persists_source_before_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.diagnosis.test_workflow_e2e import _approved, _rows, _workflow

    row = _rows()[0]
    workflow, _extraction, _retrieval, generator = _workflow(row, tmp_path)
    _root, composer = _dynamic_composer(tmp_path, monkeypatch)
    service = _service(tmp_path, composer=composer, workflow=workflow)
    approved = _approved(str(row["case_id"]))

    first = service.diagnose_and_compose(approved)
    second = service.diagnose_and_compose(approved.model_dump_json())

    assert first.status.value == "completed"
    assert second == first
    assert first.identity is not None
    assert len(generator.calls) == 1
    assert (tmp_path / "evidence" / first.identity.case_id / first.identity.source_run_id).is_dir()
    assert (tmp_path / "outcomes" / first.identity.source_run_id / "outcome.json").is_file()


def test_retry_reverifies_a_partial_bundle_then_creates_a_distinct_full_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _root, composer = _dynamic_composer(tmp_path, monkeypatch, fail_audio_once=True)
    service = _service(tmp_path, composer=composer)

    partial = service.load_replay("module-not-found")
    assert partial.status.value == "partial"
    assert partial.failure is not None and partial.failure.retry_scope == "tts"
    assert partial.identity is not None and partial.result_id is not None

    retried = service.retry_stage(partial.identity.case_id, partial.result_id)
    assert retried.status.value == "completed"
    assert retried.result_id != partial.result_id
    assert retried.mode.value == "replay"
