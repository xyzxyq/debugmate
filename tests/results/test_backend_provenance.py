from __future__ import annotations

import pytest
from pydantic import ValidationError

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.results.contracts import ArtifactAvailability, ResultMode, ResultStatus, ResultViewState


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
