from __future__ import annotations

import pytest
from pydantic import ValidationError

from debugmate.settings import DebugMateSettings


def test_complete_application_configuration_is_local_and_strict() -> None:
    configured = DebugMateSettings.from_env(
        {
            "DIFY_API_KEY": "fixture-app-key",
            "DIFY_BASE_URL": "https://api.dify.ai/v1",
            "DIFY_USER": "debugmate-stable",
        }
    )
    incomplete = DebugMateSettings.from_env({})

    assert configured.dify_application_configured is True
    assert configured.cloud_configured is True
    assert incomplete.dify_application_configured is False


@pytest.mark.parametrize(
    "base_url",
    [
        "http://api.dify.ai/v1",
        "https://user@example.invalid/v1",
        "https://api.dify.ai/v1?redirect=https://example.invalid",
        "https://api.dify.ai/v1#fragment",
        "https://example.invalid/v1",
        "https://api.dify.ai/v2",
    ],
)
def test_production_base_url_rejects_noncanonical_origins(base_url: str) -> None:
    with pytest.raises(ValidationError):
        DebugMateSettings.from_env(
            {"DIFY_API_KEY": "fixture-app-key", "DIFY_BASE_URL": base_url}
        )

