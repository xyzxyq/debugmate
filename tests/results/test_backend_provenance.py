from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.results.test_contracts import _completed_manifest, _identity, _successful_audio

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.results.consistency import validate_result_candidates
from debugmate.results.contracts import (
    ArtifactAvailability,
    AudioAttempt,
    AudioResult,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.publisher import TrustedResultRoot, publish_result_bundle
from debugmate.results.verifier import _result_id_from_manifest


def test_result_mode_remains_orthogonal_to_execution_backend() -> None:
    assert {mode.value for mode in ResultMode} == {"live", "replay"}
    live = ResultViewState(
        mode=ResultMode.LIVE,
        execution_backend=ExecutionBackend.LOCAL_FALLBACK,
        status=ResultStatus.IDLE,
        availability=ArtifactAvailability(),
    )
    assert live.execution_backend is ExecutionBackend.LOCAL_FALLBACK


@pytest.mark.parametrize(
    ("mode", "backend", "fixture"),
    [
        (ResultMode.LIVE, ExecutionBackend.REPLAY, {}),
        (
            ResultMode.REPLAY,
            ExecutionBackend.DIFY,
            {"fixture_id": "module-not-found", "fixture_name": "ModuleNotFoundError"},
        ),
    ],
)
def test_view_rejects_mode_backend_cross_products(
    mode: ResultMode,
    backend: ExecutionBackend,
    fixture: dict[str, str],
) -> None:
    with pytest.raises(ValidationError, match="execution backend"):
        ResultViewState(
            mode=mode,
            execution_backend=backend,
            status=ResultStatus.IDLE,
            availability=ArtifactAvailability(),
            **fixture,
        )


def test_view_requires_backend_instead_of_inferring_from_audio_or_files() -> None:
    with pytest.raises(ValidationError, match="execution_backend"):
        ResultViewState(
            mode=ResultMode.LIVE,
            status=ResultStatus.IDLE,
            availability=ArtifactAvailability(),
        )


def test_dify_execution_survives_independent_sapi_audio_fallback() -> None:
    base = _completed_manifest(execution_backend=ExecutionBackend.DIFY)
    audio = AudioResult(
        identity=base.identity,
        available=True,
        backend="sapi",
        fallback_used=True,
        attempts=(
            AudioAttempt(
                backend="dify",
                rate_profile="normal",
                succeeded=False,
                safe_error_code="tts_backend_failed",
            ),
            AudioAttempt(
                backend="sapi",
                rate_profile="normal",
                succeeded=True,
                duration_ms=40_000,
                sha256="7" * 64,
            ),
        ),
        duration_ms=40_000,
        sha256="7" * 64,
    )
    manifest = _completed_manifest(
        execution_backend=ExecutionBackend.DIFY,
        audio=audio,
    )
    assert manifest.execution_backend is ExecutionBackend.DIFY
    assert manifest.audio is not None
    assert manifest.audio.backend == "sapi"


def test_publisher_backend_is_manifest_truth_and_cache_discriminator(
    candidates: tuple[object, ...], tmp_path,
) -> None:
    root = TrustedResultRoot.for_testing(tmp_path / "results")
    candidate = validate_result_candidates(*candidates)
    dify = publish_result_bundle(
        root,
        candidate,
        mode=ResultMode.LIVE,
        execution_backend=ExecutionBackend.DIFY,
    )
    values = {
        record.kind: (dify.path / record.path).read_bytes()
        for record in dify.manifest.artifacts
    }
    local_result_id = _result_id_from_manifest(
        dify.manifest.model_copy(
            update={"execution_backend": ExecutionBackend.LOCAL_FALLBACK}
        ),
        values,
    )
    assert dify.manifest.execution_backend is ExecutionBackend.DIFY
    assert local_result_id != dify.manifest.result_id


def test_running_partial_and_failed_states_preserve_explicit_backend() -> None:
    identity = _identity()
    audio_failure = SafeFailure(
        code="tts_failed", failed_stage="audio", retry_scope="audio"
    )
    states = (
        ResultViewState(
            mode=ResultMode.LIVE,
            execution_backend=ExecutionBackend.DIFY,
            status=ResultStatus.RUNNING,
            availability=ArtifactAvailability(),
            current_stage="source",
        ),
        ResultViewState(
            mode=ResultMode.LIVE,
            execution_backend=ExecutionBackend.DIFY,
            status=ResultStatus.PARTIAL,
            identity=identity,
            result_id="result_" + "6" * 32,
            availability=ArtifactAvailability(
                report=True, card=False, recap_text=True, audio=True
            ),
            failure=SafeFailure(
                code="png_layout_failed", failed_stage="card", retry_scope="card"
            ),
            audio=_successful_audio(identity),
        ),
        ResultViewState(
            mode=ResultMode.LIVE,
            execution_backend=ExecutionBackend.DIFY,
            status=ResultStatus.PARTIAL,
            identity=identity,
            result_id="result_" + "7" * 32,
            availability=ArtifactAvailability(
                report=True, card=True, recap_text=True, audio=False
            ),
            failure=audio_failure,
            audio=AudioResult(
                identity=identity,
                available=False,
                attempts=(
                    AudioAttempt(
                        backend="sapi",
                        rate_profile="normal",
                        succeeded=False,
                        safe_error_code="tts_backend_failed",
                    ),
                ),
                failure=audio_failure,
            ),
        ),
        ResultViewState(
            mode=ResultMode.LIVE,
            execution_backend=ExecutionBackend.DIFY,
            status=ResultStatus.FAILED,
            availability=ArtifactAvailability(),
            failure=SafeFailure(
                code="workflow_failed", failed_stage="workflow", retry_scope="input"
            ),
        ),
    )
    assert {state.execution_backend for state in states} == {ExecutionBackend.DIFY}
    assert states[-1].availability.any() is False
