"""Strict, value-free verification for Phase 4 MP3 candidates."""

from __future__ import annotations

import json
import math
import os
import stat
import subprocess
import tempfile
import threading
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import Field

from debugmate.hashing import sha256_file
from debugmate.results.contracts import StrictFrozenModel

_MAX_PROBE_OUTPUT_BYTES = 1024 * 1024
_MAX_TRANSCODE_OUTPUT_BYTES = 64 * 1024
_MIN_DURATION_SECONDS = 30.0
_MAX_DURATION_SECONDS = 60.0
_MP3_FRAME_TOLERANCE_SECONDS = 0.02
_WINGET_FFMPEG_BIN = (
    Path("Microsoft")
    / "WinGet"
    / "Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-8.1-full_build"
    / "bin"
)
_EXPECTED_MEDIA_HASHES = {
    "ffmpeg.exe": "d1e2a156261ecc675081943197a85f08f2868784a0af499171ede89353edad31",
    "ffprobe.exe": "70872c3ffbc43d0b2c570f9837f54d6e9a832f4ca25463e9735b6a3ec0621478",
}


class MediaProbeError(ValueError):
    """A public, fixed-code failure that never retains process or path values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class TrustedMediaTools:
    """Verified absolute media executables; never a PATH-derived command."""

    ffmpeg: Path
    ffprobe: Path


def _windows_local_app_data() -> Path:
    """Read the Windows known folder directly, not an environment variable."""

    if os.name != "nt":
        raise MediaProbeError("media_tool_unavailable") from None
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(32_768)
        # CSIDL_LOCAL_APPDATA. This API returns the real Windows known folder and
        # does not honor a caller-controlled PATH/LOCALAPPDATA override.
        result = ctypes.windll.shell32.SHGetFolderPathW(None, 0x001C, None, 0, buffer)
        if result != 0 or not buffer.value:
            raise OSError
        return Path(buffer.value)
    except (AttributeError, OSError):
        raise MediaProbeError("media_tool_unavailable") from None


def _is_link_or_reparse(path: Path) -> bool:
    try:
        info = path.stat(follow_symlinks=False)
    except OSError:
        return True
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _is_regular_nonreparse(path: Path) -> bool:
    try:
        info = path.stat(follow_symlinks=False)
        return not _is_link_or_reparse(path) and stat.S_ISREG(info.st_mode)
    except OSError:
        return False


def _has_safe_ancestors(path: Path) -> bool:
    """Reject every symlink/reparse ancestor before executing a trusted tool."""

    current = path
    try:
        while True:
            info = current.stat(follow_symlinks=False)
            if current != path and not stat.S_ISDIR(info.st_mode):
                return False
            if _is_link_or_reparse(current):
                return False
            parent = current.parent
            if parent == current:
                return True
            current = parent
    except OSError:
        return False


def _verified_media_executable(name: str) -> Path:
    """Resolve only the pinned WinGet 8.1 binary and hash it on every call."""

    expected = _EXPECTED_MEDIA_HASHES[name]
    candidate = _windows_local_app_data() / _WINGET_FFMPEG_BIN / name
    if (
        not candidate.is_absolute()
        or not _is_regular_nonreparse(candidate)
        or not _has_safe_ancestors(candidate)
    ):
        raise MediaProbeError("media_tool_unavailable") from None
    try:
        if sha256_file(candidate) != expected:
            raise MediaProbeError("media_tool_unavailable") from None
    except OSError:
        raise MediaProbeError("media_tool_unavailable") from None
    # The hash is meaningful only while the exact regular, non-reparse file and
    # its ancestry still match the fixed resolver contract.
    if not _is_regular_nonreparse(candidate) or not _has_safe_ancestors(candidate):
        raise MediaProbeError("media_tool_unavailable") from None
    return candidate


def trusted_media_tools() -> TrustedMediaTools:
    """Return the exact verified binaries approved for the Windows course host."""

    return TrustedMediaTools(
        ffmpeg=_verified_media_executable("ffmpeg.exe"),
        ffprobe=_verified_media_executable("ffprobe.exe"),
    )


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


class ProcessOutputLimitExceeded(RuntimeError):
    """A fixed internal signal: child stdout or stderr crossed its hard cap."""


@dataclass
class _ExecutableLease:
    """A Windows file handle that prevents replacement while a tool starts."""

    handle: int | None

    def close(self) -> None:
        if self.handle is None:
            return
        handle, self.handle = self.handle, None
        if os.name == "nt":
            try:
                import ctypes

                ctypes.windll.kernel32.CloseHandle(handle)
            except (AttributeError, OSError):
                pass


@contextmanager
def _lease_verified_media_executable(name: str) -> Any:
    """Re-hash and hold one fixed executable from validation through ``Popen``.

    The no-write/no-delete share mode closes the practical Windows replacement
    race between hashing the path and starting the child.  Python's ``Popen``
    still receives a path, so a hostile kernel-level actor is outside this
    process boundary; the remediation report records that residual limit.
    """

    path = _verified_media_executable(name)
    lease = _ExecutableLease(handle=None)
    if os.name == "nt":
        try:
            import ctypes

            create_file = ctypes.windll.kernel32.CreateFileW
            create_file.argtypes = (
                ctypes.c_wchar_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_void_p,
            )
            create_file.restype = ctypes.c_void_p
            handle = create_file(
                str(path),
                0x80000000,  # GENERIC_READ
                0x00000001,  # FILE_SHARE_READ only; deny replacement/write
                None,
                3,  # OPEN_EXISTING
                0,
                None,
            )
            invalid_handle = ctypes.c_void_p(-1).value
            if handle in (None, invalid_handle):
                raise OSError
            lease = _ExecutableLease(handle=int(handle))
            # The handle's sharing mode now pins the bytes by name.  Recheck the
            # full resolver contract immediately before this path reaches Popen.
            if _verified_media_executable(name) != path:
                raise MediaProbeError("media_tool_unavailable")
        except (AttributeError, OSError, ValueError):
            lease.close()
            raise MediaProbeError("media_tool_unavailable") from None
    try:
        yield path
    finally:
        lease.close()


def _trusted_media_tool_name(command: list[str]) -> str | None:
    """Return a fixed media executable name or reject a lookalike command."""

    if not command:
        raise ValueError("empty process command")
    path = Path(command[0])
    name = path.name.casefold()
    if name not in _EXPECTED_MEDIA_HASHES:
        return None
    expected = _verified_media_executable(name)
    if path != expected:
        raise MediaProbeError("media_tool_unavailable")
    return name


def _run_bounded_process(
    command: list[str], *, timeout_seconds: float, max_output_bytes: int
) -> tuple[int, bytes]:
    """Run fixed argv with concurrent pipe draining and a hard per-stream cap."""

    tool_name = _trusted_media_tool_name(command)
    output_chunks: list[bytes] = []
    exceeded = threading.Event()
    reader_errors: list[BaseException] = []
    reader_lock = threading.Lock()

    def drain(stream: Any, *, capture: bool) -> None:
        consumed = 0
        try:
            while True:
                # At most one byte beyond the cap is ever read from either pipe;
                # no unbounded child output is written to disk or Python memory.
                remaining = max_output_bytes - consumed
                chunk = stream.read1(min(64 * 1024, max(1, remaining + 1)))
                if not chunk:
                    return
                consumed += len(chunk)
                if consumed > max_output_bytes:
                    exceeded.set()
                    if process.poll() is None:
                        process.kill()
                    return
                if capture:
                    output_chunks.append(chunk)
        except BaseException as exc:  # pragma: no cover - defensive process boundary
            with reader_lock:
                reader_errors.append(exc)

    with _lease_verified_media_executable(tool_name) if tool_name else _null_context():
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        assert process.stdout is not None and process.stderr is not None
        stdout_reader = threading.Thread(
            target=drain, args=(process.stdout,), kwargs={"capture": True}
        )
        stderr_reader = threading.Thread(
            target=drain, args=(process.stderr,), kwargs={"capture": False}
        )
        stdout_reader.start()
        stderr_reader.start()
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise
        finally:
            if exceeded.is_set() and process.poll() is None:
                process.kill()
        stdout_reader.join()
        stderr_reader.join()
    if reader_errors:
        raise OSError("bounded process stream failure") from None
    if exceeded.is_set():
        raise ProcessOutputLimitExceeded
    return process.returncode, b"".join(output_chunks)


@contextmanager
def _null_context() -> Any:
    yield


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

    try:
        ffprobe = trusted_media_tools().ffprobe
    except MediaProbeError:
        raise
    command = [
        str(ffprobe),
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
    except ProcessOutputLimitExceeded:
        _fail("probe_invalid")
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
        ffmpeg = trusted_media_tools().ffmpeg
        command = [
            str(ffmpeg),
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
    except ProcessOutputLimitExceeded:
        _fail("canonicalize_failed")
    except MediaProbeError:
        raise
    except (OSError, ValueError):
        _fail("canonicalize_failed")
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
