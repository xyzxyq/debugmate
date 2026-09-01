"""Render the Remotion visual composition and mux the verified audio timeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOTION = ROOT / "video" / "remotion"
CLI = REMOTION / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
BUILD = ROOT / ".artifacts" / "remotion-video-v0.1"
VISUAL = BUILD / "visual.mp4"
OUTPUT = ROOT / "deliverables" / "DebugMate-V0.1-demo.mp4"
SUBTITLES = ROOT / "deliverables" / "DebugMate-V0.1-subtitles.srt"
MANIFEST = ROOT / "deliverables" / "video-manifest.json"
FPS = 30
PAUSE_SECONDS = 0.8


def run(
    command: list[str], *, cwd: Path = ROOT, timeout: int = 1800
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode:
        details = (completed.stderr or completed.stdout)[-3000:]
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{details}")
    return completed


def probe(path: Path) -> dict[str, object]:
    result = run(
        ["ffprobe.exe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        timeout=60,
    )
    return json.loads(result.stdout)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def render_visual() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    run(
        [
            "node",
            str(CLI),
            "render",
            "DebugMateV01Visual",
            str(VISUAL),
            "--concurrency=4",
        ],
        cwd=REMOTION,
        timeout=3600,
    )


def mux_audio() -> None:
    visual_data = probe(VISUAL)
    if any(stream["codec_type"] == "audio" for stream in visual_data["streams"]):
        _, visual_mean = detect_volumes(VISUAL)
    else:
        visual_mean = -100.0
    if visual_mean > -60:
        OUTPUT.unlink(missing_ok=True)
        run(
            [
                "ffmpeg.exe",
                "-y",
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(VISUAL),
                "-map",
                "0",
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(OUTPUT),
            ],
            timeout=300,
        )
        return
    audio_paths = [
        REMOTION / "public" / "audio" / f"scene-{index:02d}.mp3" for index in range(1, 9)
    ]
    bed = REMOTION / "public" / "audio" / "ambient-bed.mp3"
    durations = []
    for path in audio_paths:
        data = probe(path)
        durations.append(float(data["format"]["duration"]))

    input_paths = [str(VISUAL), *[str(path) for path in audio_paths], str(bed)]
    filters: list[str] = []
    start_ms = 0
    for index, duration in enumerate(durations, start=1):
        input_index = index
        filters.append(f"[{input_index}:a]adelay={start_ms}|{start_ms},volume=1[a{index}]")
        start_ms += round((duration + PAUSE_SECONDS) * 1000)
    voice_inputs = "".join(f"[a{index}]" for index in range(1, 9))
    filters.append(
        f"{voice_inputs}amix=inputs=8:duration=longest:dropout_transition=0:normalize=0[voice]"
    )
    filters.append("[9:a]volume=0.07[bed]")
    filters.append(
        "[voice][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aoutmix]"
    )
    filters.append("[aoutmix]apad=pad_dur=2[aout]")

    OUTPUT.unlink(missing_ok=True)
    run(
        [
            "ffmpeg.exe",
            "-y",
            "-nostdin",
            "-v",
            "error",
            *sum((["-i", path] for path in input_paths), []),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-shortest",
            "-movflags",
            "+faststart",
            str(OUTPUT),
        ],
        timeout=600,
    )


def detect_volumes(path: Path) -> tuple[float, float]:
    volume_result = subprocess.run(
        ["ffmpeg.exe", "-v", "info", "-i", str(path), "-af", "volumedetect", "-f", "null", "NUL"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if volume_result.returncode:
        raise RuntimeError(volume_result.stderr[-2000:])
    max_match = re.search(r"max_volume:\s+(-?\d+(?:\.\d+)?) dB", volume_result.stderr)
    mean_match = re.search(r"mean_volume:\s+(-?\d+(?:\.\d+)?) dB", volume_result.stderr)
    if not max_match or not mean_match:
        raise RuntimeError("FFmpeg did not report audio volume")
    return float(max_match.group(1)), float(mean_match.group(1))


def verify_audio(path: Path) -> tuple[dict[str, object], float, float]:
    data = probe(path)
    streams = data["streams"]
    video = next((stream for stream in streams if stream["codec_type"] == "video"), None)
    audio = next((stream for stream in streams if stream["codec_type"] == "audio"), None)
    if video is None or audio is None:
        raise RuntimeError("Final MP4 must contain both video and audio streams")
    if video.get("width") != 1920 or video.get("height") != 1080:
        raise RuntimeError(
            f"Unexpected video dimensions: {video.get('width')}x{video.get('height')}"
        )
    if audio.get("codec_name") != "aac":
        raise RuntimeError(f"Unexpected audio codec: {audio.get('codec_name')}")
    duration = float(data["format"]["duration"])
    max_volume, mean_volume = detect_volumes(path)
    if max_volume > -0.1:
        raise RuntimeError(f"Audio may clip: max_volume={max_volume} dB")
    if mean_volume < -60:
        raise RuntimeError(f"Audio appears silent: mean_volume={mean_volume} dB")
    return data, duration, mean_volume


def write_manifest(data: dict[str, object], duration: float, mean_volume: float) -> None:
    audio_stream = next(stream for stream in data["streams"] if stream["codec_type"] == "audio")
    video_stream = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
    payload = {
        "schema_version": "debugmate-course-video-2.0",
        "generated_on": datetime.now(UTC).date().isoformat(),
        "renderer": "Remotion 4.0.506 composition with embedded audio layers",
        "composition": "DebugMateV01Visual",
        "video": {
            "path": "deliverables/DebugMate-V0.1-demo.mp4",
            "bytes": OUTPUT.stat().st_size,
            "sha256": sha256(OUTPUT),
            "duration_seconds": round(duration, 3),
            "resolution": f"{video_stream['width']}x{video_stream['height']}",
            "fps": 30,
            "video_codec": video_stream["codec_name"],
            "audio_codec": audio_stream["codec_name"],
            "audio_sample_rate": audio_stream.get("sample_rate"),
            "audio_channels": audio_stream.get("channels"),
            "audio_mean_volume_db": round(mean_volume, 2),
            "tts_backend": "edge-tts",
            "voice": "zh-CN-XiaoxiaoNeural",
            "voice_rate": "+5%",
            "background_audio": "original low-volume ambient bed",
        },
        "subtitles": {
            "path": "deliverables/DebugMate-V0.1-subtitles.srt",
            "bytes": SUBTITLES.stat().st_size,
            "sha256": sha256(SUBTITLES),
        },
        "scenes": 8,
        "source_script": "docs/course/video-script.md",
        "visual_identity": "video/DESIGN.md",
        "audio_source": (
            "video/remotion/public/audio/scene-01.mp3 ... scene-08.mp3 + ambient-bed.mp3"
        ),
        "truth_boundary": (
            "Dify live, local fallback, and fixed replay remain explicitly distinguished"
        ),
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Reuse an existing Remotion visual render in .artifacts",
    )
    args = parser.parse_args()
    if not args.skip_render:
        render_visual()
    if not VISUAL.is_file() or VISUAL.stat().st_size == 0:
        raise RuntimeError(f"Visual render is missing or empty: {VISUAL}")
    mux_audio()
    data, duration, mean_volume = verify_audio(OUTPUT)
    write_manifest(data, duration, mean_volume)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "duration_seconds": round(duration, 3),
                "mean_volume_db": mean_volume,
                "sha256": sha256(OUTPUT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
