from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "docs" / "course" / "video-script.md"
BUILD_DIR = ROOT / ".artifacts" / "course-video-v0.1"
OUTPUT = ROOT / "deliverables" / "DebugMate-V0.1-demo.mp4"
SUBTITLES = ROOT / "deliverables" / "DebugMate-V0.1-subtitles.srt"
MANIFEST = ROOT / "deliverables" / "video-manifest.json"
SAPI_SCRIPT = ROOT / "scripts" / "sapi-synthesize.ps1"
SCREENSHOTS = ROOT / "evidence" / "course-v0.1" / "screenshots"

WIDTH = 1920
HEIGHT = 1080
BG = (18, 43, 70)
FG = (241, 245, 247)
ACCENT = (235, 113, 62)
TEAL = (43, 166, 181)
MUTED = (175, 195, 209)
PANEL = (29, 59, 88)

TITLE_FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")
BODY_FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
MONO_FONT = Path(r"C:\Windows\Fonts\consola.ttf")

SCENE_META = [
    ("项目开场", ["AI/Python 报错诊断与复盘", "有依据 · 可执行 · 说明不确定性"]),
    ("目标与工具", ["课程第二类：多模态智能体", "Dify 可选增强 + 本地 Python 稳定闭环"]),
    ("知识库与隐私", ["17 个官方技术来源", "自动脱敏 + 上传前预览确认"]),
    ("提示词 V1–V4", ["从自然语言回答到严格 JSON", "引用、置信度、安全与多模态一致性"]),
    ("完整工作台演示", ["脱敏输入 · 事实与引用", "报告 · PNG · MP3 · ZIP"]),
    ("部分完成与降级", ["TTS 失败只重试语音", "PNG 失败保留报告与语音"]),
    ("代表性工程验证", ["58 个界面/状态测试", "264 个结果模块测试 · 真实 Edge 下载"]),
    ("局限、改进与总结", ["V0.1 本地课程演示版", "把“修好一次”变成“理解并复盘一次”"]),
]


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, font_obj, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if draw.textbbox((0, 0), candidate, font=font_obj)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def draw_background(image: Image.Image) -> ImageDraw.ImageDraw:
    draw = ImageDraw.Draw(image)
    for x in range(0, WIDTH, 120):
        draw.line((x, 0, x, HEIGHT), fill=(25, 54, 82), width=1)
    for y in range(0, HEIGHT, 120):
        draw.line((0, y, WIDTH, y), fill=(25, 54, 82), width=1)
    draw.ellipse((1420, -260, 2130, 450), fill=(20, 73, 96))
    draw.ellipse((-240, 770, 420, 1430), fill=(47, 67, 85))
    draw.rectangle((80, 76, 96, 1004), fill=ACCENT)
    return draw


def add_header(draw: ImageDraw.ImageDraw, index: int, title: str) -> None:
    draw.text((150, 90), f"DEBUGMATE / V0.1 / {index:02d}", font=font(MONO_FONT, 26), fill=TEAL)
    draw.text((150, 150), title, font=font(TITLE_FONT, 72), fill=FG)
    draw.line((150, 250, 950, 250), fill=ACCENT, width=8)


def add_summary(draw: ImageDraw.ImageDraw, bullets: list[str], y: int = 330) -> None:
    body = font(BODY_FONT, 42)
    for item in bullets:
        draw.ellipse((158, y + 16, 178, y + 36), fill=ACCENT)
        for line in wrap(draw, item, body, 1180):
            draw.text((205, y), line, font=body, fill=FG)
            y += 58
        y += 34


def add_footer(draw: ImageDraw.ImageDraw) -> None:
    draw.text(
        (150, 1008),
        "《校外实训》课程项目 · Windows 本地演示 · 真实截图与确定性产物",
        font=font(BODY_FONT, 24),
        fill=MUTED,
    )


def screenshot_panel(image: Image.Image, path: Path, box: tuple[int, int, int, int]) -> None:
    with Image.open(path) as source:
        source = source.convert("RGB")
        top = source.crop((0, 0, source.width, int(source.height * 0.55)))
        fitted = ImageOps.fit(
            top, (box[2] - box[0], box[3] - box[1]), method=Image.Resampling.LANCZOS
        )
        image.paste(fitted, (box[0], box[1]))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(box, radius=22, outline=TEAL, width=5)


def build_scene(index: int, title: str, bullets: list[str], output: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = draw_background(image)
    add_header(draw, index, title)

    if index == 1:
        draw.text((150, 350), "多模态报错诊断", font=font(TITLE_FONT, 94), fill=FG)
        draw.text((150, 475), "与复盘智能体", font=font(TITLE_FONT, 94), fill=ACCENT)
        add_summary(draw, bullets, 690)
    elif index == 4:
        labels = [("V1", "能回答"), ("V2", "有引用"), ("V3", "可校验"), ("V4", "可派生")]
        x = 155
        for version, label in labels:
            draw.rounded_rectangle(
                (x, 370, x + 350, 650), radius=24, fill=PANEL, outline=TEAL, width=3
            )
            draw.text((x + 34, 410), version, font=font(MONO_FONT, 58), fill=ACCENT)
            draw.text((x + 34, 520), label, font=font(TITLE_FONT, 44), fill=FG)
            x += 410
        add_summary(draw, bullets, 755)
    elif index == 5:
        screenshot_panel(
            image,
            SCREENSHOTS / "01-completed-overview.png",
            (820, 290, 1810, 890),
        )
        add_summary(draw, bullets, 355)
        draw.text((155, 720), "同一 source_run_id", font=font(MONO_FONT, 34), fill=TEAL)
        draw.text((155, 785), "→ REPORT  → PNG  → MP3  → ZIP", font=font(MONO_FONT, 34), fill=FG)
    elif index == 6:
        screenshot_panel(image, SCREENSHOTS / "02-tts-partial.png", (100, 315, 930, 855))
        screenshot_panel(image, SCREENSHOTS / "03-card-partial.png", (990, 315, 1820, 855))
        add_summary(draw, bullets, 880)
    elif index == 7:
        metrics = [
            ("58", "界面与状态"),
            ("264", "结果模块"),
            ("4+", "真实 Edge"),
            ("1", "ZIP 同次运行"),
        ]
        x = 150
        for value, label in metrics:
            draw.rounded_rectangle(
                (x, 350, x + 370, 670), radius=26, fill=PANEL, outline=TEAL, width=3
            )
            draw.text((x + 35, 390), value, font=font(MONO_FONT, 76), fill=ACCENT)
            draw.text((x + 35, 535), label, font=font(TITLE_FONT, 34), fill=FG)
            x += 430
        add_summary(draw, bullets, 760)
    else:
        add_summary(draw, bullets, 360)
        if index == 8:
            draw.rounded_rectangle(
                (150, 660, 1760, 865), radius=28, fill=PANEL, outline=ACCENT, width=4
            )
            closing = "隐私确认 + 官方知识 + 结构化诊断\n文字报告 + PNG + MP3 + ZIP"
            y = 700
            for line in closing.splitlines():
                draw.text((220, y), line, font=font(TITLE_FONT, 48), fill=FG)
                y += 72
    add_footer(draw)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def parse_sections() -> list[tuple[str, str]]:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    parts = re.split(r"^##\s+", text, flags=re.MULTILINE)[1:]
    sections: list[tuple[str, str]] = []
    for part in parts:
        heading, _, body = part.partition("\n")
        narration = " ".join(
            line.strip()
            for line in body.splitlines()
            if line.strip() and not line.lstrip().startswith(">")
        )
        sections.append((heading.strip(), narration))
    if len(sections) != len(SCENE_META):
        raise RuntimeError(f"expected {len(SCENE_META)} narration sections, got {len(sections)}")
    return sections


def run(command: list[str], *, input_bytes: bytes | None = None, timeout: int = 180) -> bytes:
    completed = subprocess.run(
        command,
        input=input_bytes,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace")[-1000:])
    return completed.stdout


def duration(path: Path) -> float:
    payload = run(
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
    return float(json.loads(payload)["format"]["duration"])


def timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    sections = parse_sections()
    scene_videos: list[Path] = []
    subtitle_lines: list[str] = []
    elapsed = 0.0

    for index, ((heading, narration), (title, bullets)) in enumerate(
        zip(sections, SCENE_META, strict=True), start=1
    ):
        image_path = BUILD_DIR / f"scene-{index:02d}.png"
        wav_path = BUILD_DIR / f"scene-{index:02d}.wav"
        video_path = BUILD_DIR / f"scene-{index:02d}.mp4"
        build_scene(index, title, bullets, image_path)

        wav_bytes = run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(SAPI_SCRIPT),
                "-Voice",
                "Microsoft Huihui Desktop",
                "-Rate",
                "2",
            ],
            input_bytes=narration.encode("utf-8"),
            timeout=180,
        )
        if not wav_bytes.startswith(b"RIFF"):
            raise RuntimeError("SAPI did not return a WAV stream")
        wav_path.write_bytes(wav_bytes)
        audio_duration = duration(wav_path)
        clip_duration = audio_duration + 1.0
        fade_out = max(0.5, clip_duration - 0.55)
        run(
            [
                "ffmpeg.exe",
                "-y",
                "-nostdin",
                "-v",
                "error",
                "-loop",
                "1",
                "-framerate",
                "30",
                "-i",
                str(image_path),
                "-i",
                str(wav_path),
                "-vf",
                f"fade=t=in:st=0:d=0.45,fade=t=out:st={fade_out:.3f}:d=0.5",
                "-af",
                (
                    "afade=t=in:st=0:d=0.15,"
                    f"afade=t=out:st={max(0.1, audio_duration - 0.35):.3f}:d=0.3"
                ),
                "-t",
                f"{clip_duration:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "20",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "44100",
                "-movflags",
                "+faststart",
                str(video_path),
            ],
            timeout=300,
        )
        scene_videos.append(video_path)
        subtitle_lines.extend(
            [
                str(index),
                f"{timestamp(elapsed)} --> {timestamp(elapsed + audio_duration)}",
                f"{heading}\n{narration}",
                "",
            ]
        )
        elapsed += clip_duration

    concat_path = BUILD_DIR / "concat.txt"
    concat_path.write_text(
        "\n".join(f"file '{path.as_posix()}'" for path in scene_videos) + "\n",
        encoding="utf-8",
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg.exe",
            "-y",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(OUTPUT),
        ],
        timeout=300,
    )
    SUBTITLES.write_text("\n".join(subtitle_lines), encoding="utf-8")
    total_duration = duration(OUTPUT)
    if total_duration <= 180:
        raise RuntimeError(f"course video is too short: {total_duration:.3f}s")
    manifest = {
        "schema_version": "debugmate-course-video-1.0",
        "generated_on": "2026-07-19",
        "video": {
            "path": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
            "bytes": OUTPUT.stat().st_size,
            "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
            "duration_seconds": round(total_duration, 3),
            "resolution": "1920x1080",
            "fps": 30,
            "video_codec": "h264",
            "audio_codec": "aac",
            "tts_backend": "Windows SAPI",
            "voice": "Microsoft Huihui Desktop",
        },
        "subtitles": {
            "path": str(SUBTITLES.relative_to(ROOT)).replace("\\", "/"),
            "bytes": SUBTITLES.stat().st_size,
            "sha256": hashlib.sha256(SUBTITLES.read_bytes()).hexdigest(),
        },
        "scenes": len(scene_videos),
        "source_script": "docs/course/video-script.md",
        "visual_identity": "video/DESIGN.md",
        "hyperframes_attempt": "timed_out_during_doctor; deterministic local fallback used",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
