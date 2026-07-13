from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.results.contracts import (
    ArtifactAvailability,
    ArtifactIdentity,
    ArtifactRecord,
    AudioAttempt,
    AudioResult,
    PreparedGenerationContext,
    ResultManifest,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.font import prepare_generation_context
ROOT = Path(__file__).resolve().parents[2]
CASE_ID = "case_" + "1" * 32
RUN_ID = "run_" + "2" * 32
SHA = "3" * 64


def _identity(**changes: object) -> ArtifactIdentity:
    return ArtifactIdentity(
        case_id=CASE_ID,
        source_run_id=RUN_ID,
        diagnosis_sha256=SHA,
        schema_version="1.1.0",
        generation_version="gen_" + "4" * 32,
        **changes,
    )


def _artifact(kind: str, path: str) -> ArtifactRecord:
    return ArtifactRecord(
        kind=kind,
        path=path,
        mime_type="application/octet-stream",
        bytes=1,
        sha256="5" * 64,
        identity=_identity(),
    )


def test_dependency_versions_are_exactly_pinned_and_installed() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set(config["project"]["dependencies"])
    assert "gradio==6.20.0" in dependencies
    assert "edge-tts==7.2.8" in dependencies
    assert "playwright==1.61.0" in dependencies
    assert importlib.metadata.version("gradio") == "6.20.0"
    assert importlib.metadata.version("edge-tts") == "7.2.8"
    assert importlib.metadata.version("playwright") == "1.61.0"


def test_default_marker_expression_excludes_external_and_real_media_gates() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = config["tool"]["pytest"]["ini_options"]["addopts"]
    for marker in ("cloud", "ocr", "network", "browser", "tts"):
        assert f"not {marker}" in addopts


def test_unmarked_fake_media_test_is_collected_by_default() -> None:
    assert b"ID3".startswith(b"ID3")


def test_committed_replay_fixture_strictly_validates_and_verifies(
    completed_source_bundle,
) -> None:
    outcome, source = completed_source_bundle
    index = json.loads((ROOT / "fixtures/replay/index.json").read_text(encoding="utf-8"))
    row = index["fixtures"][0]
    assert row["fixture_id"] == "module-not-found"
    assert row["case_id"] == outcome.case_id
    assert row["run_id"] == outcome.run_id
    assert row["outcome_path"] == "module-not-found/outcome.json"
    assert row["source_path"].startswith("module-not-found/source/case_")
    assert ":" not in row["outcome_path"] and ":" not in row["source_path"]
    assert source.name == outcome.run_id


def test_replay_fixture_regeneration_is_canonical(tmp_path: Path) -> None:
    target = tmp_path / "replay"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate-replay-fixture.py"), str(target)],
        cwd=ROOT,
        check=True,
    )
    committed = ROOT / "fixtures/replay/module-not-found"
    outcome = json.loads((committed / "outcome.json").read_text(encoding="utf-8"))
    source_prefix = f"source/{outcome['case_id']}/{outcome['run_id']}/"
    for name in (
        "outcome.json",
        source_prefix + "extraction.json",
        source_prefix + "case-facts.json",
        source_prefix + "sufficiency.json",
        source_prefix + "routing.json",
        source_prefix + "retrieval.json",
        source_prefix + "diagnosis.json",
        source_prefix + "manifest.json",
    ):
        assert (target / "module-not-found" / name).read_bytes() == (committed / name).read_bytes()


def test_artifact_identity_is_strict_frozen_and_version_locked() -> None:
    identity = _identity()
    with pytest.raises(ValidationError):
        ArtifactIdentity.model_validate({**identity.model_dump(), "extra": True}, strict=True)
    with pytest.raises(ValidationError):
        ArtifactIdentity.model_validate({**identity.model_dump(), "case_id": 1}, strict=True)
    with pytest.raises(ValidationError):
        _identity(schema_version="9.9.9")
    with pytest.raises(ValidationError):
        _identity(diagnosis_sha256="bad")
    with pytest.raises(ValidationError):
        _identity(source_run_id="run_bad")
    with pytest.raises(ValidationError):
        identity.generation_version = "changed"


def test_prepared_generation_context_binds_exact_font_and_profile(tmp_path: Path) -> None:
    font = tmp_path / "assets/fonts/course.ttf"
    font.parent.mkdir(parents=True)
    font.write_bytes(b"fictional-font-v1")
    context = prepare_generation_context(
        project_root=tmp_path,
        project_font_candidates=("assets/fonts/course.ttf",),
        windows_font_candidates=(),
    )
    assert context.generation_profile.font_name == context.resolved_font.name
    assert context.generation_profile.font_sha256 == context.resolved_font.sha256
    same = PreparedGenerationContext.model_validate(context.model_dump(), strict=True)
    assert same == context
    with pytest.raises(ValidationError):
        PreparedGenerationContext(
            generation_profile=context.generation_profile.model_copy(
                update={"font_sha256": "f" * 64}
            ),
            resolved_font=context.resolved_font,
        )


def test_font_preparation_prefers_project_and_rejects_links(tmp_path: Path) -> None:
    project_font = tmp_path / "fonts/project.ttf"
    project_font.parent.mkdir()
    project_font.write_bytes(b"project")
    windows_font = tmp_path / "windows.ttf"
    windows_font.write_bytes(b"windows")
    context = prepare_generation_context(
        project_root=tmp_path,
        project_font_candidates=("fonts/project.ttf",),
        windows_font_candidates=(windows_font,),
    )
    assert context.resolved_font.path == project_font.resolve()
    link = tmp_path / "fonts/link.ttf"
    try:
        link.symlink_to(project_font)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ValueError, match="font"):
        prepare_generation_context(
            project_root=tmp_path,
            project_font_candidates=("fonts/link.ttf",),
            windows_font_candidates=(),
        )


@pytest.mark.parametrize(
    "status,availability,failure",
    [
        (ResultStatus.COMPLETED, ArtifactAvailability(), None),
        (
            ResultStatus.PARTIAL,
            ArtifactAvailability(report=True, card=True, recap_text=True, audio=True),
            SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="audio"),
        ),
        (ResultStatus.FAILED, ArtifactAvailability(report=True), None),
    ],
)
def test_manifest_rejects_illegal_terminal_availability(status, availability, failure) -> None:
    with pytest.raises(ValidationError):
        ResultManifest(
            manifest_version="1.0.0",
            result_id="result_" + "6" * 32,
            identity=_identity(),
            mode=ResultMode.LIVE,
            status=status,
            availability=availability,
            artifacts=[],
            failure=failure,
        )


def test_replay_requires_fixture_identity_independent_of_status() -> None:
    with pytest.raises(ValidationError):
        ResultViewState(
            mode=ResultMode.REPLAY,
            status=ResultStatus.IDLE,
            availability=ArtifactAvailability(),
        )


def test_fallback_audio_requires_attempt_history() -> None:
    with pytest.raises(ValidationError):
        AudioResult(
            identity=_identity(),
            available=True,
            backend="edge_tts",
            fallback_used=True,
            attempts=[],
            duration_ms=40_000,
            sha256="7" * 64,
        )
    attempt = AudioAttempt(
        backend="edge_tts",
        rate_profile="default",
        succeeded=True,
        duration_ms=40_000,
        sha256="7" * 64,
    )
    assert attempt.succeeded is True


def test_manifest_rejects_duplicate_or_hash_cycle_members() -> None:
    duplicate = _artifact("report", "report.md")
    with pytest.raises(ValidationError):
        ResultManifest(
            manifest_version="1.0.0",
            result_id="result_" + "6" * 32,
            identity=_identity(),
            mode=ResultMode.LIVE,
            status=ResultStatus.PARTIAL,
            availability=ArtifactAvailability(report=True),
            artifacts=[duplicate, duplicate],
            failure=SafeFailure(
                code="png_layout_failed", failed_stage="card", retry_scope="card"
            ),
        )
    for reserved in ("result-manifest.json", "checksums.sha256", "result.zip", "publication.json"):
        with pytest.raises(ValidationError):
            _artifact("report", reserved)


def test_public_failures_have_no_raw_error_or_path_fields() -> None:
    failure = SafeFailure(code="source_bundle_invalid", failed_stage="source", retry_scope="source")
    assert set(failure.model_dump()) == {"code", "failed_stage", "retry_scope"}
    with pytest.raises(ValidationError):
        SafeFailure.model_validate(
            {**failure.model_dump(), "raw_exception": "secret", "path": "C:/Users/private"},
            strict=True,
        )
