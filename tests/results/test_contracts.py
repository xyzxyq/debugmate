from __future__ import annotations

import importlib.metadata
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.results.contracts import (
    ArtifactAvailability,
    ArtifactIdentity,
    ArtifactRecord,
    AudioAttempt,
    AudioResult,
    GenerationProfile,
    PreparedGenerationContext,
    ResolvedFont,
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
    payload = dict(
        case_id=CASE_ID,
        source_run_id=RUN_ID,
        diagnosis_sha256=SHA,
        schema_version="1.1.0",
        generation_version="gen_" + "4" * 32,
    )
    payload.update(changes)
    return ArtifactIdentity(**payload)


def _artifact(kind: str, path: str, *, sha256: str = "5" * 64) -> ArtifactRecord:
    return ArtifactRecord(
        kind=kind,
        path=path,
        mime_type="application/octet-stream",
        bytes=1,
        sha256=sha256,
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
    target.mkdir()
    committed_index = json.loads(
        (ROOT / "fixtures/replay/index.json").read_text(encoding="utf-8")
    )
    (target / "index.json").write_text(
        json.dumps(committed_index, ensure_ascii=False), encoding="utf-8"
    )
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
    regenerated_index = json.loads((target / "index.json").read_text(encoding="utf-8"))
    assert [item["fixture_id"] for item in regenerated_index["fixtures"]] == [
        "module-not-found",
        "long-content",
    ]
    assert regenerated_index["fixtures"][1] == committed_index["fixtures"][1]


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


def test_prepared_context_recomputes_font_hash_and_rejects_missing_or_directory(
    tmp_path: Path,
) -> None:
    font = tmp_path / "font.ttf"
    font.write_bytes(b"trusted-font")
    forged_hash = "f" * 64
    forged_profile = GenerationProfile.create(
        report_contract_version="report-v1",
        card_contract_version="card-v1",
        recap_contract_version="recap-v1",
        font_name=font.name,
        font_sha256=forged_hash,
    )
    with pytest.raises(ValidationError, match="font"):
        PreparedGenerationContext(
            generation_profile=forged_profile,
            resolved_font=ResolvedFont(
                name=font.name,
                path=font,
                confinement_root=tmp_path,
                sha256=forged_hash,
                source="project",
            ),
        )
    for unsafe in (tmp_path / "missing.ttf", tmp_path):
        with pytest.raises(ValidationError, match="font"):
            ResolvedFont(
                name="font.ttf",
                path=unsafe,
                confinement_root=tmp_path,
                sha256=forged_hash,
                source="project",
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


def test_font_preparation_ignores_foreign_platform_absolute_candidates(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="no approved font"):
        prepare_generation_context(
            project_root=tmp_path,
            project_font_candidates=(),
            windows_font_candidates=(Path("C:/Windows/Fonts/missing.ttf"),),
        )


def test_font_preparation_rejects_linked_root_and_linked_ancestor(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    (actual / "child").mkdir(parents=True)
    (actual / "child/font.ttf").write_bytes(b"font")
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    for root in (linked, linked / "child"):
        with pytest.raises(ValueError, match="font|root|link|reparse"):
            prepare_generation_context(
                project_root=root,
                project_font_candidates=(
                    "child/font.ttf" if root == linked else "font.ttf",
                ),
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
            manifest_version="1.1.0",
            result_id="result_" + "6" * 32,
            identity=_identity(),
            mode=ResultMode.LIVE,
            execution_backend=ExecutionBackend.LOCAL_FALLBACK,
            status=status,
            availability=availability,
            artifacts=(),
            failure=failure,
        )


def test_replay_requires_fixture_identity_independent_of_status() -> None:
    with pytest.raises(ValidationError):
        ResultViewState(
            mode=ResultMode.REPLAY,
            execution_backend=ExecutionBackend.REPLAY,
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
            attempts=(),
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
            manifest_version="1.1.0",
            result_id="result_" + "6" * 32,
            identity=_identity(),
            mode=ResultMode.LIVE,
            execution_backend=ExecutionBackend.LOCAL_FALLBACK,
            status=ResultStatus.PARTIAL,
            availability=ArtifactAvailability(report=True),
            artifacts=(duplicate, duplicate),
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


def _successful_audio(identity: ArtifactIdentity | None = None, *, sha256: str = "7" * 64):
    bound = identity or _identity()
    attempt = AudioAttempt(
        backend="edge_tts",
        rate_profile="default",
        succeeded=True,
        duration_ms=40_000,
        sha256=sha256,
    )
    return AudioResult(
        identity=bound,
        available=True,
        backend="edge_tts",
        attempts=(attempt,),
        duration_ms=40_000,
        sha256=sha256,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"availability": ArtifactAvailability(report=True)},
        {
            "failure": SafeFailure(
                code="source_bundle_invalid", failed_stage="source", retry_scope="source"
            )
        },
        {"current_stage": "source"},
        {"completed_stages": ("source",)},
        {"inherited_stages": ("source",)},
    ],
)
def test_idle_view_rejects_progress_and_result_state(changes: dict[str, object]) -> None:
    payload: dict[str, object] = {
        "mode": ResultMode.LIVE,
        "execution_backend": ExecutionBackend.LOCAL_FALLBACK,
        "status": ResultStatus.IDLE,
        "availability": ArtifactAvailability(),
    }
    payload.update(changes)
    with pytest.raises(ValidationError, match="idle view"):
        ResultViewState(**payload)


@pytest.mark.parametrize(
    "changes",
    [
        {"availability": ArtifactAvailability(report=True)},
        {
            "failure": SafeFailure(
                code="source_bundle_invalid", failed_stage="source", retry_scope="source"
            )
        },
        {"current_stage": None},
    ],
)
def test_running_view_rejects_terminal_state(changes: dict[str, object]) -> None:
    payload: dict[str, object] = {
        "mode": ResultMode.LIVE,
        "execution_backend": ExecutionBackend.LOCAL_FALLBACK,
        "status": ResultStatus.RUNNING,
        "availability": ArtifactAvailability(),
        "current_stage": "source",
        "completed_stages": ("input",),
    }
    payload.update(changes)
    with pytest.raises(ValidationError, match="running view"):
        ResultViewState(**payload)


@pytest.mark.parametrize(
    "status",
    [ResultStatus.COMPLETED, ResultStatus.PARTIAL, ResultStatus.FAILED],
)
def test_terminal_view_rejects_stale_current_stage(status: ResultStatus) -> None:
    identity = _identity()
    payload: dict[str, object] = {
        "mode": ResultMode.LIVE,
        "execution_backend": ExecutionBackend.LOCAL_FALLBACK,
        "status": status,
        "availability": ArtifactAvailability(),
        "current_stage": "audio",
    }
    if status is ResultStatus.COMPLETED:
        payload.update(
            identity=identity,
            result_id="result_" + "6" * 32,
            availability=ArtifactAvailability(
                report=True, card=True, recap_text=True, audio=True
            ),
            audio=_successful_audio(identity),
        )
    elif status is ResultStatus.PARTIAL:
        failure = SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="audio")
        payload.update(
            identity=identity,
            result_id="result_" + "6" * 32,
            availability=ArtifactAvailability(report=True, card=True, recap_text=True),
            failure=failure,
            audio=AudioResult(
                identity=identity,
                available=False,
                attempts=(
                    AudioAttempt(
                        backend="edge_tts",
                        rate_profile="default",
                        succeeded=False,
                        safe_error_code="tts_backend_failed",
                    ),
                ),
                failure=failure,
            ),
        )
    else:
        payload["failure"] = SafeFailure(
            code="source_bundle_invalid", failed_stage="source", retry_scope="source"
        )
    with pytest.raises(ValidationError, match="terminal view"):
        ResultViewState(**payload)


def _completed_manifest(**changes: object) -> ResultManifest:
    identity = _identity()
    payload = {
        "manifest_version": "1.1.0",
        "result_id": "result_" + "6" * 32,
        "identity": identity,
        "mode": ResultMode.LIVE,
        "execution_backend": ExecutionBackend.LOCAL_FALLBACK,
        "status": ResultStatus.COMPLETED,
        "availability": ArtifactAvailability(
            report=True, card=True, recap_text=True, audio=True
        ),
        "artifacts": (
            _artifact("report", "report.md"),
            _artifact("card", "card.png"),
            _artifact("recap_text", "recap.txt"),
            _artifact("audio", "recap.mp3", sha256="7" * 64),
        ),
        "audio": _successful_audio(identity),
        "completed_stages": ("source", "report", "card", "audio"),
    }
    payload.update(changes)
    return ResultManifest(**payload)


def test_manifest_binds_availability_to_exact_artifact_kinds_and_audio() -> None:
    assert _completed_manifest().status is ResultStatus.COMPLETED
    valid = _completed_manifest()
    for changes in (
        {"artifacts": valid.artifacts[:-1]},
        {"audio": None},
        {"audio": _successful_audio(sha256="8" * 64)},
        {"artifacts": (*valid.artifacts, _artifact("audio", "other.mp3", sha256="7" * 64))},
    ):
        with pytest.raises(ValidationError):
            _completed_manifest(**changes)


def test_partial_manifest_allows_only_explicit_card_or_audio_failure_subset() -> None:
    identity = _identity()
    audio_failure = SafeFailure(
        code="tts_failed", failed_stage="audio", retry_scope="audio"
    )
    failed_attempt = AudioAttempt(
        backend="edge_tts",
        rate_profile="default",
        succeeded=False,
        safe_error_code="tts_backend_failed",
    )
    partial = ResultManifest(
        manifest_version="1.1.0",
        result_id="result_" + "6" * 32,
        identity=identity,
        mode=ResultMode.LIVE,
        execution_backend=ExecutionBackend.LOCAL_FALLBACK,
        status=ResultStatus.PARTIAL,
        availability=ArtifactAvailability(report=True, card=True, recap_text=True),
        artifacts=(
            _artifact("report", "report.md"),
            _artifact("card", "card.png"),
            _artifact("recap_text", "recap.txt"),
        ),
        failure=audio_failure,
        audio=AudioResult(
            identity=identity,
            available=False,
            attempts=(failed_attempt,),
            failure=audio_failure,
        ),
    )
    assert partial.status is ResultStatus.PARTIAL
    with pytest.raises(ValidationError):
        ResultManifest.model_validate(
            {
                **partial.model_dump(),
                "availability": ArtifactAvailability(report=True).model_dump(),
                "artifacts": (_artifact("report", "report.md").model_dump(),),
            },
            strict=True,
        )


def test_result_contract_collections_are_deeply_immutable_and_roundtrip_stably() -> None:
    manifest = _completed_manifest()
    with pytest.raises(AttributeError):
        manifest.artifacts.append(_artifact("citations", "citations.json"))
    with pytest.raises(AttributeError):
        manifest.completed_stages.append("publish")
    assert manifest.audio is not None
    with pytest.raises(AttributeError):
        manifest.audio.attempts.append(
            AudioAttempt(
                backend="edge_tts",
                rate_profile="default",
                succeeded=False,
                safe_error_code="late_mutation",
            )
        )
    from debugmate.hashing import canonical_json_bytes

    first = canonical_json_bytes(manifest.model_dump(mode="json"))
    restored = ResultManifest.model_validate_json(first, strict=True)
    assert canonical_json_bytes(restored.model_dump(mode="json")) == first


def test_terminal_view_state_carries_only_verified_result_and_audio_metadata() -> None:
    """The pure UI mapping cannot infer a result ID or fallback from a path."""

    identity = _identity()
    first_attempt = AudioAttempt(
        backend="dify",
        rate_profile="normal",
        succeeded=False,
        safe_error_code="tts_backend_failed",
    )
    final_attempt = AudioAttempt(
        backend="edge_tts",
        rate_profile="faster",
        succeeded=True,
        duration_ms=40_000,
        sha256="7" * 64,
    )
    audio = AudioResult(
        identity=identity,
        available=True,
        backend="edge_tts",
        fallback_used=True,
        attempts=(first_attempt, final_attempt),
        duration_ms=40_000,
        sha256="7" * 64,
    )
    view = ResultViewState(
        mode=ResultMode.REPLAY,
        execution_backend=ExecutionBackend.REPLAY,
        fixture_id="module-not-found",
        fixture_name="ModuleNotFoundError：缺少虚构依赖包",
        status=ResultStatus.COMPLETED,
        identity=identity,
        result_id="result_" + "6" * 32,
        availability=ArtifactAvailability(report=True, card=True, recap_text=True, audio=True),
        audio=audio,
    )
    assert view.result_id == "result_" + "6" * 32
    assert view.audio is not None and view.audio.fallback_used is True

    with pytest.raises(ValidationError):
        ResultViewState(
            mode=ResultMode.LIVE,
            execution_backend=ExecutionBackend.LOCAL_FALLBACK,
            status=ResultStatus.COMPLETED,
            identity=identity,
            availability=ArtifactAvailability(report=True, card=True, recap_text=True, audio=True),
            audio=audio,
        )
