"""Secret-safe environment settings for local and cloud adapters."""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


def _random_approval_key() -> SecretStr:
    return SecretStr(secrets.token_urlsafe(32))


class DebugMateSettings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    dify_base_url: str = "https://api.dify.ai/v1"
    dify_api_key: SecretStr | None = None
    dify_dataset_api_key: SecretStr | None = None
    dify_user: str = "debugmate-local"
    approval_key: SecretStr = Field(default_factory=_random_approval_key)

    @field_validator("dify_base_url")
    @classmethod
    def require_canonical_dify_application_url(cls, value: str) -> str:
        """Restrict bearer-bearing application requests to the Dify Cloud API."""

        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.dify.ai"
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path != "/v1"
            or value not in {"https://api.dify.ai/v1", "https://api.dify.ai:443/v1"}
        ):
            raise ValueError("Dify base URL must be the approved HTTPS application endpoint")
        return value.rstrip("/")

    @field_validator("approval_key")
    @classmethod
    def require_strong_approval_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("approval key is too short")
        return value

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> DebugMateSettings:
        source = os.environ if environ is None else environ
        api_key = source.get("DIFY_API_KEY") or None
        dataset_key = source.get("DIFY_DATASET_API_KEY") or None
        approval_key = source.get("DEBUGMATE_APPROVAL_KEY") or secrets.token_urlsafe(32)
        return cls(
            dify_base_url=source.get("DIFY_BASE_URL") or "https://api.dify.ai/v1",
            dify_api_key=SecretStr(api_key) if api_key else None,
            dify_dataset_api_key=SecretStr(dataset_key) if dataset_key else None,
            dify_user=source.get("DIFY_USER") or "debugmate-local",
            approval_key=SecretStr(approval_key),
        )

    @property
    def approval_key_bytes(self) -> bytes:
        return self.approval_key.get_secret_value().encode("utf-8")

    @property
    def cloud_configured(self) -> bool:
        return self.dify_application_configured

    @property
    def dify_application_configured(self) -> bool:
        """Return configuration readiness without probing Dify or consuming quota."""

        return self.dify_api_key is not None and bool(self.dify_user.strip())

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
