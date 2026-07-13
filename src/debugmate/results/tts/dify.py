"""Bounded Dify text-to-audio adapter."""

from __future__ import annotations

from pathlib import Path

import httpx

from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import (
    AudioCandidate,
    RateProfile,
    TtsAdapterError,
    TtsRequestIdentity,
)
from debugmate.settings import DebugMateSettings


class DifyTtsAdapter:
    backend = "dify"

    def __init__(
        self,
        settings: DebugMateSettings,
        *,
        client: httpx.Client | None = None,
        max_bytes: int = 8_000_000,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=httpx.Timeout(30.0))
        self._max_bytes = max_bytes

    def synthesize(
        self,
        text: SafeRecapText,
        target: Path,
        request_identity: TtsRequestIdentity,
        rate_profile: RateProfile,
    ) -> AudioCandidate:
        del request_identity
        if self._settings.dify_api_key is None:
            raise TtsAdapterError("tts_not_configured")
        try:
            with self._client.stream(
                "POST",
                f"{self._settings.dify_base_url.rstrip('/')}/text-to-audio",
                headers={
                    "Authorization": f"Bearer {self._settings.dify_api_key.get_secret_value()}"
                },
                json={"text": text.text, "user": self._settings.dify_user},
            ) as response:
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if response.status_code >= 300 or content_type not in {
                    "audio/mpeg",
                    "audio/mp3",
                }:
                    raise TtsAdapterError() from None
                payload = bytearray()
                for chunk in response.iter_bytes():
                    if len(payload) + len(chunk) > self._max_bytes:
                        raise TtsAdapterError() from None
                    payload.extend(chunk)
        except httpx.HTTPError:
            raise TtsAdapterError() from None
        if not payload:
            raise TtsAdapterError() from None
        target.write_bytes(payload)
        return AudioCandidate(backend=self.backend, rate_profile=rate_profile, path=target)
