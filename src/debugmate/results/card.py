"""Deterministic Pillow diagnosis card bound to one prepared generation context."""

from __future__ import annotations

import os
import struct
import uuid
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from pydantic import Field

from debugmate.hashing import canonical_json_bytes, sha256_file
from debugmate.results.contracts import (
    ArtifactAvailability,
    ArtifactIdentity,
    PreparedGenerationContext,
    ResolvedFont,
    StrictFrozenModel,
)
from debugmate.results.presentation import PresentationModel, _validated_presentation

CANVAS_WIDTH = 1600
MAX_PNG_HEIGHT = 12_000
MAX_PNG_PIXELS = CANVAS_WIDTH * MAX_PNG_HEIGHT
MAX_CARD_TEXT_CHARS = 48_000
MAX_CARD_ITEMS = 256
MARGIN = 88
PADDING = 36
SECTION_GAP = 28
TITLE_SIZE = 54
HEADING_SIZE = 34
BODY_SIZE = 27
LINE_GAP = 12
CARD_RENDERER_VERSION = "pillow-card-v1"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_ALLOWED_CHUNKS = {b"IHDR", b"IDAT", b"IEND"}


class CardRenderFailure(ValueError):
    """Value-free visual failure safe to expose in a partial result."""

    def __init__(self, code: Literal["png_layout_failed", "png_render_failed", "png_verify_failed"]):
        self.code = code
        self.failed_stage = "card"
        self.retry_scope = "card"
        self.availability = ArtifactAvailability(
            report=True, card=False, recap_text=True, audio=True
        )
        super().__init__(code)


class CardLine(StrictFrozenModel):
    text: str
    x: int = Field(strict=True, ge=0)
    y: int = Field(strict=True, ge=0)
    width: int = Field(strict=True, ge=0)
    height: int = Field(strict=True, gt=0)


class CardSection(StrictFrozenModel):
    section_id: str
    title: str
    x: int = Field(strict=True, ge=0)
    y: int = Field(strict=True, ge=0)
    width: int = Field(strict=True, gt=0)
    height: int = Field(strict=True, gt=0)
    content_width: int = Field(strict=True, gt=0)
    lines: tuple[CardLine, ...]


class CardLayout(StrictFrozenModel):
    identity: ArtifactIdentity
    renderer_version: Literal["pillow-card-v1"] = CARD_RENDERER_VERSION
    font_name: str
    font_sha256: str
    canvas_width: int = CANVAS_WIDTH
    canvas_height: int = Field(strict=True, gt=0)
    section_order: tuple[str, ...]
    sections: tuple[CardSection, ...]


class CardCandidate(StrictFrozenModel):
    identity: ArtifactIdentity
    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(strict=True, gt=0)
    width: int = CANVAS_WIDTH
    height: int = Field(strict=True, gt=0)
    mode: Literal["RGB"] = "RGB"
    frames: Literal[1] = 1
    renderer_version: Literal["pillow-card-v1"] = CARD_RENDERER_VERSION
    font_name: str
    font_sha256: str


def _strict_context(context: object) -> PreparedGenerationContext:
    if not isinstance(context, PreparedGenerationContext):
        raise TypeError("context type")
    return PreparedGenerationContext.model_validate_json(
        canonical_json_bytes(context.model_dump(mode="json")), strict=True
    )


def verify_prepared_font(
    presentation: PresentationModel, context: PreparedGenerationContext
) -> ResolvedFont:
    """Recheck the exact prepared bytes without resolving or substituting a font."""

    try:
        model = _validated_presentation(presentation)
        prepared = _strict_context(context)
        profile = prepared.generation_profile
        font = prepared.resolved_font
        if (
            model.identity.generation_version != profile.generation_version
            or model.card_contract_version != profile.card_contract_version
            or model.report_contract_version != profile.report_contract_version
            or model.recap_contract_version != profile.recap_contract_version
            or model.font_name != font.name
            or model.font_sha256 != font.sha256
            or profile.font_name != font.name
            or profile.font_sha256 != font.sha256
        ):
            raise ValueError("identity mismatch")
        return font
    except Exception:
        failure = CardRenderFailure("png_layout_failed")
    raise failure from None


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(path), size=size, layout_engine=ImageFont.Layout.BASIC)
    except Exception:
        failure = CardRenderFailure("png_layout_failed")
    raise failure from None


def _text_size(font: ImageFont.FreeTypeFont, text: str) -> tuple[int, int]:
    left, top, right, bottom = font.getbbox(text or " ")
    return max(0, right - left), max(1, bottom - top)


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> tuple[str, ...]:
    if not text:
        return ("-",)
    output: list[str] = []
    for paragraph in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        current = ""
        for char in paragraph or " ":
            candidate = current + char
            if current and font.getlength(candidate) > max_width:
                output.append(current)
                current = char
            else:
                current = candidate
        output.append(current or " ")
    if any(font.getlength(line) > max_width for line in output):
        raise CardRenderFailure("png_layout_failed")
    return tuple(output)


def _command_lines(prefix: str, items: tuple[object, ...]) -> list[str]:
    values: list[str] = []
    for index, item in enumerate(items, 1):
        values.extend(
            (
                f"{prefix}{index} · {item.platform}: {item.command}",
                f"影响：{item.impact}；预期：{item.expected_result}；回滚：{item.rollback}",
            )
        )
    return values or ["暂无"]


def _sections(presentation: PresentationModel) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    facts = tuple(
        f"{item.fact_id} · {item.field_id}: {item.value}（置信度 {item.confidence:.2f}）"
        for item in presentation.observed_facts
    ) or ("暂无",)
    causes = tuple(
        f"{item.candidate_id} · {item.claim_label}: {item.cause}（置信度 {item.confidence:.2f}）"
        for item in presentation.root_causes
    ) or ("暂无",)
    return (
        ("phenomenon", "现象与已观察事实", facts),
        ("causes", "根因候选与依据", causes),
        ("checks", "检查步骤", tuple(_command_lines("检查 ", presentation.checks))),
        ("fixes", "修复步骤", tuple(_command_lines("修复 ", presentation.fixes))),
        (
            "verification",
            "验证步骤",
            tuple(_command_lines("验证 ", presentation.verification_steps)),
        ),
    )


def measure_card(
    presentation: PresentationModel, context: PreparedGenerationContext
) -> CardLayout:
    """Build and validate the complete layout tree before allocating pixels."""

    font_record = verify_prepared_font(presentation, context)
    body = _font(font_record.path, BODY_SIZE)
    heading = _font(font_record.path, HEADING_SIZE)
    content_width = CANVAS_WIDTH - 2 * (MARGIN + PADDING)
    definitions = _sections(presentation)
    all_values = [value for _, _, values in definitions for value in values]
    if len(all_values) > MAX_CARD_ITEMS or sum(map(len, all_values)) > MAX_CARD_TEXT_CHARS:
        raise CardRenderFailure("png_layout_failed")
    y = MARGIN + TITLE_SIZE + 48
    sections: list[CardSection] = []
    for section_id, title, values in definitions:
        line_texts = tuple(line for value in values for line in _wrap(value, body, content_width))
        heading_height = _text_size(heading, title)[1]
        line_height = max(_text_size(body, line)[1] for line in line_texts)
        height = PADDING + heading_height + 24 + len(line_texts) * (line_height + LINE_GAP) + PADDING
        lines = tuple(
            CardLine(
                text=line,
                x=MARGIN + PADDING,
                y=y + PADDING + heading_height + 24 + index * (line_height + LINE_GAP),
                width=int(body.getlength(line)),
                height=line_height,
            )
            for index, line in enumerate(line_texts)
        )
        sections.append(
            CardSection(
                section_id=section_id,
                title=title,
                x=MARGIN,
                y=y,
                width=CANVAS_WIDTH - 2 * MARGIN,
                height=height,
                content_width=content_width,
                lines=lines,
            )
        )
        y += height + SECTION_GAP
    canvas_height = y - SECTION_GAP + MARGIN
    if canvas_height > MAX_PNG_HEIGHT or CANVAS_WIDTH * canvas_height > MAX_PNG_PIXELS:
        raise CardRenderFailure("png_layout_failed")
    return CardLayout(
        identity=presentation.identity,
        font_name=font_record.name,
        font_sha256=font_record.sha256,
        canvas_height=canvas_height,
        section_order=tuple(item[0] for item in definitions),
        sections=tuple(sections),
    )


def _png_chunks(payload: bytes) -> tuple[bytes, ...]:
    if not payload.startswith(_PNG_SIGNATURE):
        raise CardRenderFailure("png_verify_failed")
    offset = len(_PNG_SIGNATURE)
    chunks: list[bytes] = []
    while offset < len(payload):
        if offset + 12 > len(payload):
            raise CardRenderFailure("png_verify_failed")
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        kind = payload[offset + 4 : offset + 8]
        offset += 12 + length
        if offset > len(payload):
            raise CardRenderFailure("png_verify_failed")
        chunks.append(kind)
        if kind == b"IEND":
            break
    if offset != len(payload) or not chunks or chunks[-1] != b"IEND":
        raise CardRenderFailure("png_verify_failed")
    return tuple(chunks)


def verify_card_png(path: Path, *, expected_size: tuple[int, int]) -> None:
    """Verify bytes and decoded pixels from the final disk path."""

    try:
        payload = path.read_bytes()
        chunks = _png_chunks(payload)
        if any(chunk not in _PNG_ALLOWED_CHUNKS for chunk in chunks):
            raise ValueError("metadata")
        with Image.open(path) as image:
            if (
                image.format != "PNG"
                or image.mode != "RGB"
                or getattr(image, "n_frames", 1) != 1
                or image.size != expected_size
                or image.info != {}
            ):
                raise ValueError("shape")
            image.load()
    except CardRenderFailure:
        raise
    except Exception:
        failure = CardRenderFailure("png_verify_failed")
        raise failure from None


def render_card(
    presentation: PresentationModel,
    context: PreparedGenerationContext,
    *,
    target: Path,
) -> CardCandidate:
    """Paint a validated layout, sanitize to pixels, atomically place and reopen it."""

    target = Path(target)
    temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        layout = measure_card(presentation, context)
        font_record = verify_prepared_font(presentation, context)
        title_font = _font(font_record.path, TITLE_SIZE)
        heading_font = _font(font_record.path, HEADING_SIZE)
        body_font = _font(font_record.path, BODY_SIZE)
        image = Image.new("RGB", (layout.canvas_width, layout.canvas_height), "#F4F7FB")
        draw = ImageDraw.Draw(image)
        draw.text((MARGIN, MARGIN), "DebugMate 诊断卡", font=title_font, fill="#13213C")
        for section in layout.sections:
            box = (section.x, section.y, section.x + section.width, section.y + section.height)
            draw.rounded_rectangle(box, radius=20, fill="#FFFFFF", outline="#CCD6E5", width=2)
            draw.text(
                (section.x + PADDING, section.y + PADDING),
                section.title,
                font=heading_font,
                fill="#2457A7",
            )
            for line in section.lines:
                draw.text((line.x, line.y), line.text, font=body_font, fill="#1D2738")
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(temporary, format="PNG", optimize=False, compress_level=9)
        with Image.open(temporary) as decoded:
            pixels = decoded.convert("RGB")
            pixels.load()
        pixels.save(temporary, format="PNG", optimize=False, compress_level=9)
        verify_card_png(temporary, expected_size=(layout.canvas_width, layout.canvas_height))
        if target.exists():
            raise FileExistsError("card target already exists")
        os.replace(temporary, target)
        verify_card_png(target, expected_size=(layout.canvas_width, layout.canvas_height))
        return CardCandidate(
            identity=layout.identity,
            path=target,
            sha256=sha256_file(target),
            bytes=target.stat().st_size,
            height=layout.canvas_height,
            font_name=layout.font_name,
            font_sha256=layout.font_sha256,
        )
    except CardRenderFailure:
        raise
    except Exception:
        failure = CardRenderFailure("png_render_failed")
        raise failure from None
    finally:
        temporary.unlink(missing_ok=True)
