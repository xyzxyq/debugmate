from __future__ import annotations

import json
from pathlib import Path

import pytest

from debugmate.diagnosis.workflow import DiagnosisRunOutcome
from debugmate.evidence import verify_bundle


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
