"""Local Windows SAPI-to-tag-free-MP3 adapter without external output paths."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from debugmate.results.media import (
    _run_bounded_process,
    trusted_media_tools,
)
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import (
    AudioPayload,
    RateProfile,
    TtsAdapterError,
    TtsRequestIdentity,
)
from debugmate.results.tts.validation import validate_tts_request


class SapiTtsAdapter:
    backend = "sapi"
    voice = "Microsoft Huihui Desktop"
    _RATES = {RateProfile.NORMAL: 2, RateProfile.FASTER: 4}
    _MAX_PROCESS_OUTPUT_BYTES = 8_000_000
    _MAX_RECAP_BYTES = 16 * 1024

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
            system_directory = _windows_system_directory()
            powershell_path = system_directory / "WindowsPowerShell" / "v1.0" / "powershell.exe"
            if not _is_regular_file(powershell_path):
                raise ValueError
            ffmpeg_path = trusted_media_tools().ffmpeg
            if not _is_regular_file(ffmpeg_path) or ffmpeg_path.name.casefold() != "ffmpeg.exe":
                raise ValueError
            if timeout_seconds <= 0:
                raise ValueError
        except (AttributeError, KeyError, OSError, ValueError):
            raise ValueError("tts_sapi_config_invalid") from None
        self._script = script
        self._powershell = str(powershell_path)
        self._ffmpeg = str(ffmpeg_path)
        self._timeout = float(timeout_seconds)

    def synthesize(
        self,
        text: SafeRecapText,
        request_identity: TtsRequestIdentity,
        rate_profile: RateProfile,
    ) -> AudioPayload:
        text, request_identity = validate_tts_request(text, request_identity)
        recap_bytes = text.text.encode("utf-8")
        if len(recap_bytes) > self._MAX_RECAP_BYTES:
            raise TtsAdapterError() from None
        failure: TtsAdapterError | None = None
        try:
            powershell_returncode, wav_bytes = _run_bounded_process(
                [
                    self._powershell,
                    "-NoProfile",
                    "-NonInteractive",
                    "-File",
                    str(self._script),
                    "-Voice",
                    self.voice,
                    "-Rate",
                    str(self._RATES[rate_profile]),
                ],
                timeout_seconds=self._timeout,
                max_output_bytes=self._MAX_PROCESS_OUTPUT_BYTES,
                input_bytes=recap_bytes,
                max_input_bytes=self._MAX_RECAP_BYTES,
            )
            if powershell_returncode != 0 or not wav_bytes.startswith(b"RIFF"):
                raise RuntimeError
            ffmpeg_returncode, mp3_bytes = _run_bounded_process(
                [
                    self._ffmpeg,
                    "-nostdin",
                    "-v",
                    "error",
                    "-i",
                    "pipe:0",
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
                    "-ar",
                    "16000",
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "32k",
                    "-f",
                    "mp3",
                    "pipe:1",
                ],
                timeout_seconds=self._timeout,
                max_output_bytes=self._MAX_PROCESS_OUTPUT_BYTES,
                input_bytes=wav_bytes,
                max_input_bytes=self._MAX_PROCESS_OUTPUT_BYTES,
            )
            if ffmpeg_returncode != 0 or not mp3_bytes:
                raise RuntimeError
        except Exception:
            # A TimeoutExpired instance can retain a full command and absolute
            # path.  Leave the ``except`` block before raising the replacement
            # so even exception context is value-free.
            failure = TtsAdapterError()
        if failure is not None:
            raise failure
        return AudioPayload(
            backend=self.backend,
            rate_profile=rate_profile,
            request_identity=request_identity,
            audio_bytes=mp3_bytes,
            voice=self.voice,
        )


def _is_regular_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and stat.S_ISREG(path.stat().st_mode)
    except OSError:
        return False


def _windows_system_directory() -> Path:
    """Use the Windows API rather than a caller-controlled SYSTEMROOT value."""

    if os.name != "nt":
        raise OSError("not windows")
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(32_768)
        length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
        if length == 0 or length >= len(buffer):
            raise OSError
        return Path(buffer.value)
    except (AttributeError, OSError):
        raise OSError("system directory unavailable") from None


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400)
    except OSError:
        return True


def _is_trusted_repository_file(path: Path, root: Path) -> bool:
    try:
        candidate = path.resolve(strict=True)
        candidate.relative_to(root)
        current = path
        while True:
            if _is_link_or_reparse(current):
                return False
            if current == root:
                return _is_regular_file(candidate)
            current = current.parent
    except (OSError, ValueError):
        return False
