from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from debugmate.diagnosis.workflow import DiagnosisRunOutcome
from debugmate.results.consistency import validate_result_candidates
from debugmate.results.outcome_store import DiagnosisOutcomeStore
from debugmate.results.publisher import TrustedResultRoot, publish_result_bundle


def _service(tmp_path: Path, candidates):
    from debugmate.results.service import ResultApplicationService

    candidate = validate_result_candidates(*candidates)
    root = TrustedResultRoot.for_testing(tmp_path / "results")

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
        workflow=None,
        evidence_root=tmp_path / "evidence",
        outcome_store=DiagnosisOutcomeStore(tmp_path / "outcomes"),
        results_root=root,
        replay_root=Path(__file__).resolve().parents[2] / "fixtures" / "replay",
        composer=compose,
    )


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
