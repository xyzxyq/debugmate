"""Strict, value-free verification for Phase 4 MP3 candidates."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from pydantic import Field

from debugmate.hashing import sha256_file
from debugmate.results.contracts import StrictFrozenModel

FFPROBE_EXECUTABLE = shutil.which("ffprobe") or "ffprobe"
FFMPEG_EXECUTABLE = shutil.which("ffmpeg") or "ffmpeg"
_MAX_PROBE_OUTPUT_BYTES = 1024 * 1024
_MAX_TRANSCODE_OUTPUT_BYTES = 64 * 1024
_MIN_DURATION_SECONDS = 30.0
_MAX_DURATION_SECONDS = 60.0
_MP3_FRAME_TOLERANCE_SECONDS = 0.02


class MediaProbeError(ValueError):
    """A public, fixed-code failure that never retains process or path values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MediaProbe(StrictFrozenModel):
    """Verified facts about one bounded, tag-free mono MP3 candidate."""

    duration_ms: int = Field(strict=True, ge=29_980, le=60_020)
    codec: str = Field(pattern=r"^mp3$")
    channels: int = Field(strict=True, ge=1, le=1)
    bytes: int = Field(strict=True, gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _fail(code: str) -> None:
    raise MediaProbeError(code) from None


def _has_tags(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)


def _run_bounded_process(
    command: list[str], *, timeout_seconds: float, max_output_bytes: int
) -> tuple[int, bytes]:
    """Run fixed argv while keeping child output out of Python heap until capped."""

    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            shell=False,
        )
        try:
            process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        stdout.seek(0)
        output = stdout.read(max_output_bytes + 1)
        return process.returncode, output


def probe_mp3(
    path: Path,
    *,
    timeout_seconds: float,
    max_bytes: int,
) -> MediaProbe:
    """Verify a bounded MP3 using a fixed ffprobe argv contract.

    Errors deliberately contain only a stable code. Process output, command lines,
    and filesystem paths are untrusted diagnostic material and are never retained.
    """

    candidate = Path(path)
    if timeout_seconds <= 0 or not math.isfinite(timeout_seconds):
        _fail("probe_config_invalid")
    if isinstance(max_bytes, bool) or max_bytes <= 0:
        _fail("probe_config_invalid")
    try:
        if not candidate.is_file():
            _fail("media_unreadable")
        byte_size = candidate.stat().st_size
        if byte_size <= 0:
            _fail("media_empty")
        if byte_size > max_bytes:
            _fail("media_too_large")
        with candidate.open("rb") as handle:
            signature = handle.read(3)
    except MediaProbeError:
        raise
    except OSError:
        _fail("media_unreadable")

    if signature == b"ID3":
        _fail("id3_forbidden")
    if len(signature) < 2 or signature[0] != 0xFF or signature[1] & 0xE0 != 0xE0:
        _fail("not_mpeg")

    command = [
        FFPROBE_EXECUTABLE,
        "-v",
        "error",
        "-show_entries",
        "format=duration:format_tags:stream=index,codec_type,codec_name,channels:stream_tags",
        "-of",
        "json",
        str(candidate),
    ]
    try:
        returncode, stdout_bytes = _run_bounded_process(
            command,
            timeout_seconds=timeout_seconds,
            max_output_bytes=_MAX_PROBE_OUTPUT_BYTES,
        )
    except subprocess.TimeoutExpired:
        _fail("probe_timeout")
    except (OSError, UnicodeError, ValueError):
        _fail("probe_failed")
    if returncode != 0:
        _fail("probe_failed")
    if len(stdout_bytes) > _MAX_PROBE_OUTPUT_BYTES:
        _fail("probe_invalid")
    try:
        payload = json.loads(stdout_bytes.decode("utf-8", errors="strict"))
    except (TypeError, json.JSONDecodeError, UnicodeError):
        _fail("probe_invalid")
    if not isinstance(payload, dict):
        _fail("probe_invalid")

    format_data = payload.get("format")
    streams = payload.get("streams")
    if not isinstance(format_data, dict) or not isinstance(streams, list):
        _fail("probe_invalid")
    if _has_tags(format_data.get("tags")):
        _fail("metadata_forbidden")
    if any(not isinstance(stream, dict) for stream in streams):
        _fail("probe_invalid")
    if any(_has_tags(stream.get("tags")) for stream in streams):
        _fail("metadata_forbidden")

    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(audio_streams) != 1:
        _fail("audio_stream_invalid")
    stream = audio_streams[0]
    if stream.get("codec_name") != "mp3":
        _fail("codec_invalid")
    if stream.get("channels") != 1:
        _fail("channels_invalid")
    try:
        duration = float(format_data["duration"])
    except (KeyError, TypeError, ValueError, OverflowError):
        _fail("duration_invalid")
    if not math.isfinite(duration) or duration <= 0:
        _fail("duration_invalid")
    # MPEG Layer III duration is frame-granular (36 ms at this sample rate), so
    # an exact source cutoff can probe up to half a frame either side of a bound.
    if duration < (_MIN_DURATION_SECONDS - _MP3_FRAME_TOLERANCE_SECONDS) or duration > (
        _MAX_DURATION_SECONDS + _MP3_FRAME_TOLERANCE_SECONDS
    ):
        _fail("duration_out_of_range")

    return MediaProbe(
        duration_ms=round(duration * 1000),
        codec="mp3",
        channels=1,
        bytes=byte_size,
        sha256=sha256_file(candidate),
    )


def canonicalize_mp3(
    source: Path,
    target: Path,
    *,
    timeout_seconds: float,
    max_bytes: int,
) -> MediaProbe:
    """Re-encode one candidate into the fixed, tag-free publication profile."""

    source_path = Path(source)
    target_path = Path(target)
    if timeout_seconds <= 0 or not math.isfinite(timeout_seconds):
        _fail("canonicalize_config_invalid")
    if isinstance(max_bytes, bool) or max_bytes <= 0 or source_path == target_path:
        _fail("canonicalize_config_invalid")
    try:
        if not source_path.is_file() or source_path.stat().st_size <= 0:
            _fail("canonicalize_failed")
        target_path.parent.mkdir(parents=True, exist_ok=True)
    except MediaProbeError:
        raise
    except OSError:
        _fail("canonicalize_failed")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{target_path.stem}-",
            suffix=".mp3",
            dir=target_path.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
        command = [
            FFMPEG_EXECUTABLE,
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
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
            str(temporary_path),
        ]
        returncode, output = _run_bounded_process(
            command,
            timeout_seconds=timeout_seconds,
            max_output_bytes=_MAX_TRANSCODE_OUTPUT_BYTES,
        )
        if returncode != 0 or len(output) > _MAX_TRANSCODE_OUTPUT_BYTES:
            _fail("canonicalize_failed")
        probe = probe_mp3(
            temporary_path,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )
        os.replace(temporary_path, target_path)
        temporary_path = None
        return probe
    except subprocess.TimeoutExpired:
        _fail("canonicalize_timeout")
    except MediaProbeError:
        raise
    except (OSError, ValueError):
        _fail("canonicalize_failed")
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
