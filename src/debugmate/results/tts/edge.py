"""Fixed-voice edge-tts fallback adapter."""

from __future__ import annotations

import math
import sys
from pathlib import Path

from debugmate.results.media import ProcessOutputLimitExceeded, _run_bounded_process
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import (
    AudioPayload,
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
        request_identity: TtsRequestIdentity,
        rate_profile: RateProfile,
    ) -> AudioPayload:
        text, request_identity = validate_tts_request(text, request_identity)
        try:
            returncode, payload = _run_bounded_process(
                _edge_worker_command(self._RATES[rate_profile]),
                timeout_seconds=self._timeout_seconds,
                max_output_bytes=8_000_000,
                input_bytes=text.text.encode("utf-8"),
                max_input_bytes=16 * 1024,
            )
        except (OSError, ValueError, ProcessOutputLimitExceeded, Exception):
            raise TtsAdapterError() from None
        if returncode != 0 or not payload:
            raise TtsAdapterError() from None
        return AudioPayload(
            backend=self.backend,
            rate_profile=rate_profile,
            request_identity=request_identity,
            audio_bytes=payload,
            voice=self.voice,
        )


def _edge_worker_command(rate: str) -> list[str]:
    """Return the fixed, isolated worker argv used by the production adapter."""

    interpreter = Path(sys.executable).resolve(strict=True)
    if not interpreter.is_file() or rate not in EdgeTtsAdapter._RATES.values():
        raise OSError
    return [
        str(interpreter),
        "-I",
        "-m",
        "debugmate.results.tts.edge_worker",
        "--voice",
        EdgeTtsAdapter.voice,
        "--rate",
        rate,
    ]
