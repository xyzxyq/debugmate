"""Local Windows SAPI-to-WAV-to-tag-free-MP3 adapter."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import (
    AudioCandidate,
    RateProfile,
    TtsAdapterError,
    TtsRequestIdentity,
)


class SapiTtsAdapter:
    backend = "sapi"
    voice = "Microsoft Huihui Desktop"
    _RATES = {RateProfile.NORMAL: 2, RateProfile.FASTER: 4}

    def __init__(
        self,
        *,
        project_root: Path | None = None,
        powershell: str = "powershell.exe",
        ffmpeg: str = "ffmpeg.exe",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._root = project_root or Path(__file__).resolve().parents[4]
        self._script = self._root / "scripts" / "sapi-synthesize.ps1"
        self._powershell = powershell
        self._ffmpeg = ffmpeg
        self._timeout = timeout_seconds

    def synthesize(
        self,
        text: SafeRecapText,
        target: Path,
        request_identity: TtsRequestIdentity,
        rate_profile: RateProfile,
    ) -> AudioCandidate:
        del request_identity
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix="sapi-", dir=target.parent) as temp_name:
                temp = Path(temp_name)
                input_file, wave_file = temp / "recap.txt", temp / "recap.wav"
                input_file.write_bytes(text.text.encode("utf-8"))
                subprocess.run(
                    [
                        self._powershell,
                        "-NoProfile",
                        "-NonInteractive",
                        "-File",
                        str(self._script),
                        "-InputTextFile",
                        str(input_file),
                        "-OutputWaveFile",
                        str(wave_file),
                        "-Voice",
                        self.voice,
                        "-Rate",
                        str(self._RATES[rate_profile]),
                    ],
                    check=True,
                    capture_output=True,
                    shell=False,
                    timeout=self._timeout,
                )
                subprocess.run(
                    [
                        self._ffmpeg,
                        "-nostdin",
                        "-v",
                        "error",
                        "-y",
                        "-i",
                        str(wave_file),
                        "-map_metadata",
                        "-1",
                        "-id3v2_version",
                        "0",
                        "-write_xing",
                        "0",
                        "-ac",
                        "1",
                        "-codec:a",
                        "libmp3lame",
                        str(target),
                    ],
                    check=True,
                    capture_output=True,
                    shell=False,
                    timeout=self._timeout,
                )
        except (OSError, subprocess.SubprocessError):
            target.unlink(missing_ok=True)
            raise TtsAdapterError() from None
        return AudioCandidate(
            backend=self.backend, rate_profile=rate_profile, path=target, voice=self.voice
        )
