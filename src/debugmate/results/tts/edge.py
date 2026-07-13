"""Fixed-voice edge-tts fallback adapter."""

from __future__ import annotations

import asyncio
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
                edge_tts.Communicate(text.text, self.voice, rate=self._RATES[rate_profile]).save(
                    str(target)
                )
            )
        except Exception:
            target.unlink(missing_ok=True)
            raise TtsAdapterError() from None
        return AudioCandidate(
            backend=self.backend,
            rate_profile=rate_profile,
            path=target,
            request_identity=request_identity,
            voice=self.voice,
        )
