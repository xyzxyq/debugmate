from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from debugmate.results import media as media_module
from debugmate.results.media import (
    MediaProbeError,
    canonicalize_mp3_bytes,
    probe_mp3,
    trusted_media_tools,
)

FFMPEG = "ffmpeg"


def _ffmpeg(output: Path, *output_args: str, duration: float = 30.0) -> Path:
    command = [
        FFMPEG,
        "-v",
        "error",
        "-nostdin",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=16000:cl=mono",
        "-t",
        f"{duration:.3f}",
        *output_args,
        str(output),
    ]
    subprocess.run(command, check=True, shell=False, timeout=20)
    return output


def _tag_free_mp3(path: Path, duration: float) -> Path:
    fixture_duration = {
        # MP3 frame quantisation is real, but the public verifier is exact.  The
        # fixture input is therefore selected to probe inside (not beyond) each
        # requested inclusive boundary.
        30.0: 29.95,
        60.0: 59.90,
    }.get(duration, duration - 0.084)
    return _ffmpeg(
        path,
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
        "-b:a",
        "32k",
        duration=fixture_duration,
    )


def _assert_code(error: pytest.ExceptionInfo[MediaProbeError], code: str) -> None:
    assert error.value.code == code
    assert str(error.value) == code
    assert error.value.args == (code,)


@pytest.mark.parametrize("duration", [30.0, 45.0, 60.0])
def test_accepts_real_tag_free_mono_mp3_at_inclusive_boundaries(
    tmp_path: Path, duration: float
) -> None:
    media = _tag_free_mp3(tmp_path / f"valid-{duration}.mp3", duration)

    probe = probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000_000)

    assert probe.codec == "mp3"
    assert probe.channels == 1
    assert abs(probe.duration_ms - round(duration * 1000)) <= 50
    assert probe.bytes == media.stat().st_size
    assert len(probe.sha256) == 64


@pytest.mark.parametrize("duration", [29.9, 60.1])
def test_rejects_real_mp3_outside_duration_window(tmp_path: Path, duration: float) -> None:
    media = _tag_free_mp3(tmp_path / f"invalid-{duration}.mp3", duration)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000_000)

    _assert_code(error, "duration_out_of_range")


def test_rejects_corrupt_mpeg_header_without_exposing_path(tmp_path: Path) -> None:
    media = tmp_path / "private-corrupt.mp3"
    media.write_bytes(b"\xff\xfb" + b"not-an-mp3-frame" * 8)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000_000)

    _assert_code(error, "probe_failed")
    assert str(media) not in repr(error.value)


def test_rejects_non_mp3_media(tmp_path: Path) -> None:
    media = _ffmpeg(tmp_path / "audio.wav", "-ac", "1", "-codec:a", "pcm_s16le")

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000_000)

    _assert_code(error, "not_mpeg")


def test_rejects_real_id3_and_format_tags(tmp_path: Path) -> None:
    media = _ffmpeg(
        tmp_path / "tagged.mp3",
        "-metadata",
        "title=forbidden",
        "-id3v2_version",
        "3",
        "-ac",
        "1",
        "-codec:a",
        "libmp3lame",
    )

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000_000)

    _assert_code(error, "id3_forbidden")


def test_rejects_real_stream_tags(tmp_path: Path) -> None:
    media = _ffmpeg(
        tmp_path / "stream-tagged.mp3",
        "-metadata:s:a:0",
        "language=zho",
        "-ac",
        "1",
        "-codec:a",
        "libmp3lame",
    )

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000_000)

    assert error.value.code in {"id3_forbidden", "metadata_forbidden"}


def test_rejects_real_multiple_audio_streams(tmp_path: Path) -> None:
    media = tmp_path / "two-streams.mka"
    subprocess.run(
        [
            FFMPEG,
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-t",
            "30",
            "-map",
            "0:a",
            "-map",
            "1:a",
            "-codec:a",
            "libmp3lame",
            str(media),
        ],
        check=True,
        shell=False,
        timeout=20,
    )

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=2_000_000)

    _assert_code(error, "not_mpeg")


def test_rejects_oversize_before_running_ffprobe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    media = tmp_path / "large.mp3"
    media.write_bytes(b"\xff\xfb" + b"x" * 100)
    called = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(subprocess, "run", forbidden)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=100)

    _assert_code(error, "media_too_large")
    assert called is False


def test_maps_ffprobe_timeout_to_value_free_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    media = tmp_path / "timeout.mp3"
    media.write_bytes(b"\xff\xfb" + b"x" * 100)

    def timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="SECRET PATH", timeout=5, output="SECRET")

    monkeypatch.setattr(media_module, "_run_bounded_process", timeout)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000)

    _assert_code(error, "probe_timeout")
    assert "SECRET" not in repr(error.value)


@pytest.mark.parametrize(
    ("stdout", "code"),
    [
        ("not json", "probe_invalid"),
        ('{"format":{"duration":"30"},"streams":[]}', "audio_stream_invalid"),
        (
            '{"format":{"duration":"30"},"streams":'
            '[{"codec_type":"audio","codec_name":"aac","channels":1}]}',
            "codec_invalid",
        ),
        (
            '{"format":{"duration":"30"},"streams":'
            '[{"codec_type":"audio","codec_name":"mp3","channels":2}]}',
            "channels_invalid",
        ),
        (
            '{"format":{"duration":"30","tags":{"title":"x"}},"streams":'
            '[{"codec_type":"audio","codec_name":"mp3","channels":1}]}',
            "metadata_forbidden",
        ),
        (
            '{"format":{"duration":"30"},"streams":'
            '[{"codec_type":"audio","codec_name":"mp3","channels":1,'
            '"tags":{"language":"zho"}}]}',
            "metadata_forbidden",
        ),
    ],
)
def test_rejects_untrusted_ffprobe_shapes_with_fixed_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    code: str,
) -> None:
    media = tmp_path / "candidate.mp3"
    media.write_bytes(b"\xff\xfb" + b"x" * 100)

    def completed(command: list[str], **kwargs: object) -> tuple[int, bytes]:
        assert command[1:] == [
            "-v",
            "error",
            "-show_entries",
            "format=duration:format_tags:stream=index,codec_type,codec_name,channels:stream_tags",
            "-of",
            "json",
            str(media),
        ]
        assert kwargs["timeout_seconds"] == 5.0
        return 0, stdout.encode("utf-8")

    monkeypatch.setattr(media_module, "_run_bounded_process", completed)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000)

    _assert_code(error, code)
    assert "SECRET" not in repr(error.value)


def test_ffprobe_output_cap_maps_to_a_value_free_probe_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    media = tmp_path / "candidate.mp3"
    media.write_bytes(b"\xff\xfb" + b"x" * 100)

    def flood(*_args: object, **_kwargs: object) -> None:
        raise media_module.ProcessOutputLimitExceeded

    monkeypatch.setattr(media_module, "_run_bounded_process", flood)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000)

    _assert_code(error, "probe_invalid")


def test_canonicalize_reencodes_verified_mp3_and_drops_trailing_secret(tmp_path: Path) -> None:
    source = _tag_free_mp3(tmp_path / "source.mp3", 45.0)
    with source.open("ab") as handle:
        handle.write(b"HIDDEN_TRAILING_SECRET")
    canonical = canonicalize_mp3_bytes(
        source.read_bytes(),
        timeout_seconds=20.0,
        max_bytes=1_000_000,
    )
    target = tmp_path / "canonical-fixture.mp3"
    target.write_bytes(canonical)

    assert probe_mp3(target, timeout_seconds=5.0, max_bytes=1_000_000).bytes == len(canonical)
    assert b"HIDDEN_TRAILING_SECRET" not in canonical


def test_canonicalize_failure_does_not_return_partial_payload(
    tmp_path: Path,
) -> None:
    source = tmp_path / "invalid.mp3"
    source.write_bytes(b"not audio HIDDEN_SECRET")
    with pytest.raises(MediaProbeError) as error:
        canonicalize_mp3_bytes(
            source.read_bytes(),
            timeout_seconds=5.0,
            max_bytes=1_000_000,
        )

    _assert_code(error, "canonicalize_failed")


def test_production_media_tools_ignore_path_shadowing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The production resolver may not select an executable from mutable PATH."""

    shadow = tmp_path / "shadow-bin"
    shadow.mkdir()
    for executable in ("ffmpeg.exe", "ffprobe.exe"):
        (shadow / executable).write_bytes(b"not-a-real-tool")
    monkeypatch.setenv("PATH", str(shadow))

    tools = trusted_media_tools()

    assert tools.ffmpeg.is_absolute()
    assert tools.ffprobe.is_absolute()
    assert tools.ffmpeg.parent != shadow
    assert tools.ffprobe.parent != shadow
    assert tools.ffmpeg.name.casefold() == "ffmpeg.exe"
    assert tools.ffprobe.name.casefold() == "ffprobe.exe"


def test_media_resolver_rejects_same_size_mtime_restored_tamper_in_child_process(
    tmp_path: Path,
) -> None:
    """A process-local metadata cache must not bless a restored replacement."""

    local_app_data = tmp_path / "local-app-data"
    executable = local_app_data / media_module._WINGET_FFMPEG_BIN / "ffmpeg.exe"
    executable.parent.mkdir(parents=True)
    original = b"trusted-media-tool"
    replacement = b"untrusted-tool-xxx"
    assert len(original) == len(replacement)
    executable.write_bytes(original)
    original_stat = executable.stat()
    ready = tmp_path / "resolver-ready"
    proceed = tmp_path / "replace-now"
    helper = tmp_path / "resolver-child.py"
    helper.write_text(
        "\n".join(
            (
                "from pathlib import Path",
                "from debugmate.results import media",
                f"media._windows_local_app_data = lambda: Path({str(local_app_data)!r})",
                "media._EXPECTED_MEDIA_HASHES['ffmpeg.exe'] = "
                f"{hashlib.sha256(original).hexdigest()!r}",
                "media._verified_media_executable('ffmpeg.exe')",
                f"Path({str(ready)!r}).write_text('ready', encoding='utf-8')",
                f"while not Path({str(proceed)!r}).exists(): pass",
                "try:",
                "    media._verified_media_executable('ffmpeg.exe')",
                "except media.MediaProbeError:",
                "    raise SystemExit(0)",
                "raise SystemExit(1)",
            )
        ),
        encoding="utf-8",
    )
    child = subprocess.Popen(
        [sys.executable, str(helper)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False
    )
    try:
        for _ in range(200):
            if ready.exists():
                break
            time.sleep(0.01)
        else:  # pragma: no cover - protects the child-process test itself
            pytest.fail("resolver child did not reach the cached verification point")
        executable.write_bytes(replacement)
        os.utime(executable, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        proceed.write_text("go", encoding="utf-8")
        assert child.wait(timeout=10) == 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)


def test_bounded_runner_terminates_an_output_flood_before_persisting_it() -> None:
    """Child output must be terminated while streaming, not re-read after exit."""

    flood = (
        "import sys\n"
        "chunk = b'x' * 4096\n"
        "for _ in range(100000):\n"
        "    sys.stdout.buffer.write(chunk)\n"
        "    sys.stderr.buffer.write(chunk)\n"
        "    sys.stdout.buffer.flush()\n"
        "    sys.stderr.buffer.flush()\n"
    )

    with pytest.raises(media_module.ProcessOutputLimitExceeded):
        media_module._run_bounded_process(
            [sys.executable, "-c", flood], timeout_seconds=10.0, max_output_bytes=8_192
        )


@pytest.mark.parametrize("duration", [29.981, 60.001])
def test_duration_window_has_no_mpeg_tolerance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, duration: float
) -> None:
    """The public MP3 contract is exactly 30,000 through 60,000 milliseconds."""

    media = tmp_path / "candidate.mp3"
    media.write_bytes(b"\xff\xfb" + b"x" * 100)

    def completed(_command: list[str], **_kwargs: object) -> tuple[int, bytes]:
        return (
            0,
            (
                f'{{"format":{{"duration":"{duration}"}},"streams":'
                '[{"codec_type":"audio","codec_name":"mp3","channels":1}]}'
            ).encode(),
        )

    monkeypatch.setattr(media_module, "_run_bounded_process", completed)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000_000)

    _assert_code(error, "duration_out_of_range")
