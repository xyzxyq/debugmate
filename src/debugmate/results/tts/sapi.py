"""Local Windows SAPI-to-WAV-to-tag-free-MP3 adapter."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

from debugmate.results.media import FFMPEG_EXECUTABLE, _run_bounded_process
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import (
    AudioCandidate,
    RateProfile,
    TtsAdapterError,
    TtsRequestIdentity,
)
from debugmate.results.tts.validation import validate_tts_request


class SapiTtsAdapter:
    backend = "sapi"
    voice = "Microsoft Huihui Desktop"
    _RATES = {RateProfile.NORMAL: 2, RateProfile.FASTER: 4}
    _MAX_PROCESS_OUTPUT_BYTES = 64 * 1024

    def __init__(
        self,
        *,
        project_root: Path | None = None,
        powershell: str = "powershell.exe",
        ffmpeg: str = "ffmpeg.exe",
        timeout_seconds: float = 90.0,
    ) -> None:
        trusted_root = Path(__file__).resolve().parents[4]
        try:
            trusted_root = trusted_root.resolve(strict=True)
            requested_root = (project_root or trusted_root).resolve(strict=True)
            if requested_root != trusted_root:
                raise ValueError
            if powershell.casefold() != "powershell.exe" or ffmpeg.casefold() != "ffmpeg.exe":
                raise ValueError
            script = trusted_root / "scripts" / "sapi-synthesize.ps1"
            if not _is_trusted_repository_file(script, trusted_root):
                raise ValueError
            system_directory = Path(os.environ["SYSTEMROOT"]) / "System32"
            powershell_path = system_directory / "WindowsPowerShell" / "v1.0" / "powershell.exe"
            if not _is_regular_file(powershell_path):
                raise ValueError
        except (KeyError, OSError, ValueError):
            raise ValueError("tts_sapi_config_invalid") from None
        self._script = script
        self._powershell = str(powershell_path)
        self._ffmpeg = FFMPEG_EXECUTABLE
        self._timeout = timeout_seconds

    def synthesize(
        self,
        text: SafeRecapText,
        target: Path,
        request_identity: TtsRequestIdentity,
        rate_profile: RateProfile,
    ) -> AudioCandidate:
        text, request_identity = validate_tts_request(text, request_identity)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix="sapi-", dir=target.parent) as temp_name:
                temp = Path(temp_name)
                input_file, wave_file = temp / "recap.txt", temp / "recap.wav"
                input_file.write_bytes(text.text.encode("utf-8"))
                powershell_returncode, powershell_output = _run_bounded_process(
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
                    timeout_seconds=self._timeout,
                    max_output_bytes=self._MAX_PROCESS_OUTPUT_BYTES,
                )
                if (
                    powershell_returncode != 0
                    or len(powershell_output) > self._MAX_PROCESS_OUTPUT_BYTES
                    or not _is_regular_file(wave_file)
                ):
                    raise RuntimeError("sapi_process_failed")
                ffmpeg_returncode, ffmpeg_output = _run_bounded_process(
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
                        "-metadata",
                        "encoder=",
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
                    timeout_seconds=self._timeout,
                    max_output_bytes=self._MAX_PROCESS_OUTPUT_BYTES,
                )
                if (
                    ffmpeg_returncode != 0
                    or len(ffmpeg_output) > self._MAX_PROCESS_OUTPUT_BYTES
                    or not _is_regular_file(target)
                ):
                    raise RuntimeError("ffmpeg_process_failed")
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


def _is_regular_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and stat.S_ISREG(path.stat().st_mode)
    except OSError:
        return False


def _is_trusted_repository_file(path: Path, root: Path) -> bool:
    try:
        candidate = path.resolve(strict=True)
        candidate.relative_to(root)
        current = path
        while True:
            if current.is_symlink() or not _is_regular_file(current) and current == path:
                return False
            if current == root:
                return _is_regular_file(candidate)
            current = current.parent
    except (OSError, ValueError):
        return False
