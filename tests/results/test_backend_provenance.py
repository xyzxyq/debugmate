from __future__ import annotations

import pytest
from pydantic import ValidationError
from tests.results.test_contracts import _completed_manifest

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.results.contracts import (
    ArtifactAvailability,
    AudioAttempt,
    AudioResult,
    ResultMode,
    ResultStatus,
    ResultViewState,
)


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
