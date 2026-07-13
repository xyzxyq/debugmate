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
        del request_identity, rate_profile
        if self._settings.dify_api_key is None:
            raise TtsAdapterError("tts_not_configured")
        try:
            response = self._client.post(
                f"{self._settings.dify_base_url.rstrip('/')}/text-to-audio",
                headers={
                    "Authorization": f"Bearer {self._settings.dify_api_key.get_secret_value()}"
                },
                json={"text": text.text, "user": self._settings.dify_user},
            )
        except httpx.HTTPError:
            raise TtsAdapterError() from None
        if response.status_code >= 300 or response.headers.get("content-type", "").split(";", 1)[
            0
        ].lower() not in {"audio/mpeg", "audio/mp3"}:
            raise TtsAdapterError() from None
        payload = response.content
        if not payload or len(payload) > self._max_bytes:
            raise TtsAdapterError() from None
        target.write_bytes(payload)
        return AudioCandidate(backend=self.backend, rate_profile=RateProfile.NORMAL, path=target)
