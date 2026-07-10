"""Secret-safe environment settings for local and cloud adapters."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, SecretStr


class DebugMateSettings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    dify_base_url: str = "https://api.dify.ai/v1"
    dify_api_key: SecretStr | None = None
    dify_dataset_api_key: SecretStr | None = None
    dify_user: str = "debugmate-local"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> DebugMateSettings:
        source = os.environ if environ is None else environ
        api_key = source.get("DIFY_API_KEY") or None
        dataset_key = source.get("DIFY_DATASET_API_KEY") or None
        return cls(
            dify_base_url=source.get("DIFY_BASE_URL") or "https://api.dify.ai/v1",
            dify_api_key=SecretStr(api_key) if api_key else None,
            dify_dataset_api_key=SecretStr(dataset_key) if dataset_key else None,
            dify_user=source.get("DIFY_USER") or "debugmate-local",
        )

    @property
    def cloud_configured(self) -> bool:
        return self.dify_api_key is not None

    def safe_summary(self) -> dict[str, str | bool]:
        return {
            "dify_base_url": self.dify_base_url,
            "dify_user": self.dify_user,
            "dify_api_key_configured": self.dify_api_key is not None,
            "dify_dataset_api_key_configured": self.dify_dataset_api_key is not None,
            "cloud_configured": self.cloud_configured,
        }


def find_secret_leaks(value: Any, forbidden_values: Sequence[str]) -> list[str]:
    """Return value paths containing secrets without returning the secrets themselves."""

    secrets = tuple(secret for secret in forbidden_values if secret)
    if not secrets:
        return []

    leaks: list[str] = []

    def visit(current: Any, path: str) -> None:
        if isinstance(current, str):
            if any(secret in current for secret in secrets):
                leaks.append(path)
            return
        if isinstance(current, Mapping):
            for key, nested in current.items():
                visit(nested, f"{path}.{key}")
            return
        if isinstance(current, Sequence) and not isinstance(current, (bytes, bytearray)):
            for index, nested in enumerate(current):
                visit(nested, f"{path}[{index}]")

    visit(value, "$")
    return leaks
