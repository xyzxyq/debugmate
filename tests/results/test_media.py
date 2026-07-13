from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from debugmate.results.media import MediaProbeError, canonicalize_mp3, probe_mp3

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
        # Account for one deterministic MP3 frame of muxer padding so ffprobe
        # observes the requested boundary duration rather than the input cutoff.
        duration=duration - 0.084,
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

    monkeypatch.setattr(subprocess, "run", timeout)

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

    def completed(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[1:] == [
            "-v",
            "error",
            "-show_entries",
            "format=duration:format_tags:stream=index,codec_type,codec_name,channels:stream_tags",
            "-of",
            "json",
            str(media),
        ]
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 5.0
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="SECRET STDERR")

    monkeypatch.setattr(subprocess, "run", completed)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000)

    _assert_code(error, code)
    assert "SECRET" not in repr(error.value)


def test_ffprobe_output_is_file_bounded_before_python_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    media = tmp_path / "candidate.mp3"
    media.write_bytes(b"\xff\xfb" + b"x" * 100)

    class Process:
        returncode = 0

        def communicate(self, *, timeout: float) -> tuple[None, None]:
            assert timeout == 5.0
            return None, None

    def popen(command: list[str], **kwargs: object) -> Process:
        assert kwargs["shell"] is False
        assert kwargs["stdout"] is not subprocess.PIPE
        assert kwargs["stderr"] is not subprocess.PIPE
        stdout = kwargs["stdout"]
        assert hasattr(stdout, "write")
        stdout.write(b"x" * (1024 * 1024 + 1))  # type: ignore[union-attr]
        return Process()

    monkeypatch.setattr(subprocess, "Popen", popen)

    with pytest.raises(MediaProbeError) as error:
        probe_mp3(media, timeout_seconds=5.0, max_bytes=1_000)

    _assert_code(error, "probe_invalid")


def test_canonicalize_reencodes_tagged_mp3_and_drops_trailing_secret(tmp_path: Path) -> None:
    source = _ffmpeg(
        tmp_path / "tagged-source.mp3",
        "-metadata",
        "title=forbidden",
        "-ac",
        "1",
        "-codec:a",
        "libmp3lame",
        duration=45.0,
    )
    with source.open("ab") as handle:
        handle.write(b"HIDDEN_TRAILING_SECRET")
    target = tmp_path / "canonical.mp3"

    probe = canonicalize_mp3(
        source,
        target,
        timeout_seconds=20.0,
        max_bytes=1_000_000,
    )

    assert probe == probe_mp3(target, timeout_seconds=5.0, max_bytes=1_000_000)
    assert b"HIDDEN_TRAILING_SECRET" not in target.read_bytes()
    assert target != source


def test_canonicalize_failure_does_not_publish_partial_target(
    tmp_path: Path,
) -> None:
    source = tmp_path / "invalid.mp3"
    source.write_bytes(b"not audio HIDDEN_SECRET")
    target = tmp_path / "canonical.mp3"

    with pytest.raises(MediaProbeError) as error:
        canonicalize_mp3(
            source,
            target,
            timeout_seconds=5.0,
            max_bytes=1_000_000,
        )

    _assert_code(error, "canonicalize_failed")
    assert not target.exists()
