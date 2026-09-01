"""Build Remotion assets, narration, captions, and timing for DebugMate V0.1."""

from __future__ import annotations

import html
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOTION_ROOT = ROOT / "video" / "remotion"
PUBLIC = REMOTION_ROOT / "public"
BUILD = ROOT / ".artifacts" / "remotion-video-v0.1"
SCRIPT_PATH = ROOT / "docs" / "course" / "video-script.md"
VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "+5%"
PAUSE_SECONDS = 0.8
FPS = 30
IMAGE_DIR = ROOT / "projects" / "debugmate-defense-ppt_ppt169_20260901" / "images"

ASSETS = {
    "terminal-module-not-found-redacted.png": IMAGE_DIR / "terminal-module-not-found-redacted.png",
    "01-completed-overview.png": IMAGE_DIR / "01-completed-overview.png",
    "02-tts-partial.png": IMAGE_DIR / "02-tts-partial.png",
    "03-card-partial.png": IMAGE_DIR / "03-card-partial.png",
    "card.png": IMAGE_DIR / "card.png",
}


def run(command: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode:
        details = (completed.stderr or completed.stdout)[-2000:]
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{details}")
    return completed


def parse_sections() -> list[str]:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    parts = re.split(r"^##\s+", text, flags=re.MULTILINE)[1:]
    sections = []
    for part in parts:
        _, _, body = part.partition("\n")
        narration = " ".join(
            line.strip()
            for line in body.splitlines()
            if line.strip() and not line.lstrip().startswith(">")
        )
        sections.append(narration)
    if len(sections) != 8:
        raise RuntimeError(f"Expected 8 narration sections, got {len(sections)}")
    return sections


def probe_duration(path: Path) -> float:
    result = run(
        [
            "ffprobe.exe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        timeout=30,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def parse_timestamp(value: str) -> int:
    clean = value.replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        hours = 0
    else:
        hours, minutes, seconds = parts
    return round((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000)


def parse_vtt(path: Path, offset_ms: int) -> list[dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    captions: list[dict[str, object]] = []
    for match in re.finditer(
        r"(?m)^(\d{2}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+(\d{2}:\d{2}(?::\d{2})?[.,]\d{3})\s*$\n(.+?)(?=\n\s*\n|\Z)",
        text,
        flags=re.DOTALL,
    ):
        start = offset_ms + parse_timestamp(match.group(1))
        end = offset_ms + parse_timestamp(match.group(2))
        rendered = re.sub(r"<[^>]+>", "", match.group(3)).replace("\n", " ").strip()
        rendered = html.unescape(rendered)
        if rendered and end > start:
            captions.append(
                {
                    "text": rendered,
                    "startMs": start,
                    "endMs": end,
                    "timestampMs": None,
                    "confidence": None,
                }
            )
    return captions


def srt_timestamp(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def write_srt(captions: list[dict[str, object]]) -> None:
    lines: list[str] = []
    for index, caption in enumerate(captions, start=1):
        timestamp = (
            f"{srt_timestamp(int(caption['startMs']))} --> {srt_timestamp(int(caption['endMs']))}"
        )
        lines.extend(
            [
                str(index),
                timestamp,
                str(caption["text"]),
                "",
            ]
        )
    (ROOT / "deliverables" / "DebugMate-V0.1-subtitles.srt").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def normalize_captions(captions: list[dict[str, object]]) -> list[dict[str, object]]:
    """Remove tiny VTT/scene-offset overlaps before exporting captions."""
    normalized: list[dict[str, object]] = []
    previous_end = 0
    for caption in captions:
        start = max(int(caption["startMs"]), previous_end)
        end = int(caption["endMs"])
        if end <= start:
            continue
        normalized.append({**caption, "startMs": start, "endMs": end})
        previous_end = end
    return normalized


def write_timing(timings: list[dict[str, object]], total_frames: int) -> None:
    lines = [
        "export type SceneTiming = {",
        "  id: number;",
        "  startFrame: number;",
        "  durationInFrames: number;",
        "  durationSeconds: number;",
        "};",
        "",
        "export const SCENE_TIMINGS: SceneTiming[] = [",
    ]
    for timing in timings:
        lines.append(
            f"  {{id: {timing['id']}, startFrame: {timing['startFrame']}, "
            f"durationInFrames: {timing['durationInFrames']}, "
            f"durationSeconds: {timing['durationSeconds']:.3f}}},"
        )
    lines.append("];")
    lines.append(f"export const TOTAL_FRAMES = {total_frames};")
    lines.append("")
    (REMOTION_ROOT / "src" / "timing.ts").write_text("\n".join(lines), encoding="utf-8")


def build_audio(sections: list[str]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    audio_dir = PUBLIC / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    timings: list[dict[str, object]] = []
    captions: list[dict[str, object]] = []
    start_frame = 0
    offset_ms = 0
    for index, narration in enumerate(sections, start=1):
        text_path = BUILD / f"narration-{index:02d}.txt"
        vtt_path = BUILD / f"scene-{index:02d}.vtt"
        audio_path = audio_dir / f"scene-{index:02d}.mp3"
        text_path.write_text(narration, encoding="utf-8")
        run(
            [
                sys.executable,
                "-m",
                "edge_tts",
                "--file",
                str(text_path),
                "--voice",
                VOICE,
                "--rate",
                RATE,
                "--volume",
                "+0%",
                "--pitch",
                "+0Hz",
                "--write-media",
                str(audio_path),
                "--write-subtitles",
                str(vtt_path),
            ],
            timeout=300,
        )
        duration_seconds = probe_duration(audio_path)
        scene_seconds = duration_seconds + PAUSE_SECONDS
        scene_frames = math.ceil(scene_seconds * FPS)
        timings.append(
            {
                "id": index,
                "startFrame": start_frame,
                "durationInFrames": scene_frames,
                "durationSeconds": scene_seconds,
            }
        )
        captions.extend(parse_vtt(vtt_path, offset_ms))
        start_frame += scene_frames
        offset_ms += round(scene_seconds * 1000)
    return timings, captions


def build_ambient_bed(duration_seconds: float) -> None:
    bed_path = PUBLIC / "audio" / "ambient-bed.mp3"
    run(
        [
            "ffmpeg.exe",
            "-y",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            (
                "aevalsrc=0.018*sin(2*PI*196*t)*(0.55+0.45*sin(2*PI*0.08*t))+"
                "0.012*sin(2*PI*293.66*t)*(0.55+0.45*sin(2*PI*0.11*t)):"
                f"s=48000:d={duration_seconds + 4:.3f}"
            ),
            "-af",
            f"afade=t=in:st=0:d=4,afade=t=out:st={max(0, duration_seconds - 5):.3f}:d=5,volume=0.7",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "96k",
            str(bed_path),
        ],
        timeout=120,
    )


def copy_assets() -> None:
    for name, source in ASSETS.items():
        if not source.is_file():
            raise RuntimeError(f"Required visual asset missing: {source}")
        shutil.copy2(source, PUBLIC / "assets" / name)


def main() -> int:
    sections = parse_sections()
    copy_assets()
    timings, captions = build_audio(sections)
    captions = normalize_captions(captions)
    total_frames = sum(int(timing["durationInFrames"]) for timing in timings)
    write_timing(timings, total_frames)
    (PUBLIC / "captions.json").write_text(
        json.dumps(captions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_srt(captions)
    build_ambient_bed(total_frames / FPS)
    print(
        json.dumps(
            {
                "voice": VOICE,
                "rate": RATE,
                "scenes": len(timings),
                "total_frames": total_frames,
                "duration_seconds": round(total_frames / FPS, 3),
                "captions": len(captions),
                "assets": sorted(ASSETS),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
