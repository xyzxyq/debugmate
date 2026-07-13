"""Fixed-voice edge-tts fallback adapter."""

from __future__ import annotations

import asyncio
import math
from contextlib import suppress
from pathlib import Path

import edge_tts

from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import (
    AudioCandidate,
    RateProfile,
    TtsAdapterError,
    TtsRequestIdentity,
)
from debugmate.results.tts.validation import validate_tts_request


class EdgeTtsAdapter:
    backend = "edge_tts"
    voice = "zh-CN-XiaoxiaoNeural"
    _RATES = {RateProfile.NORMAL: "-10%", RateProfile.FASTER: "+10%"}

    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        if not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds):
            raise ValueError("tts_edge_config_invalid") from None
        if timeout_seconds <= 0:
            raise ValueError("tts_edge_config_invalid") from None
        self._timeout_seconds = float(timeout_seconds)

    def synthesize(
        self,
        text: SafeRecapText,
        target: Path,
        request_identity: TtsRequestIdentity,
        rate_profile: RateProfile,
    ) -> AudioCandidate:
        text, request_identity = validate_tts_request(text, request_identity)
        try:
            asyncio.run(
                self._save_with_timeout(
                    edge_tts.Communicate(
                        text.text, self.voice, rate=self._RATES[rate_profile]
                    ),
                    target,
                )
            )
        except Exception:
            with suppress(OSError):
                target.unlink(missing_ok=True)
            raise TtsAdapterError() from None
        return AudioCandidate(
            backend=self.backend,
            rate_profile=rate_profile,
            path=target,
            request_identity=request_identity,
            voice=self.voice,
        )

    async def _save_with_timeout(self, communicate: object, target: Path) -> None:
        """Bound a remote save and finish cancellation before closing the loop."""

        task = asyncio.create_task(communicate.save(str(target)))
        try:
            await asyncio.wait_for(task, self._timeout_seconds)
        except TimeoutError:
            task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await task
            raise
