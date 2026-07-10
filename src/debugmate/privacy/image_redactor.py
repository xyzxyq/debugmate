"""Deterministic, irreversible screenshot redaction from local OCR findings."""

from __future__ import annotations

import secrets
from contextlib import suppress
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from debugmate.hashing import sha256_bytes, sha256_file
from debugmate.privacy.image_models import InvalidScreenshot, validate_screenshot
from debugmate.privacy.models import SecretKind, Sha256
from debugmate.privacy.ocr import OcrBackend
from debugmate.privacy.text_redactor import scan_text

BOX_EXPANSION_PIXELS = 3


class OcrUnavailable(RuntimeError):
    """Raised without raw OCR text or paths when local recognition fails."""


class UnsafeRedactionPath(ValueError):
    """Raised when output could overwrite the original screenshot."""


class RedactionWriteError(OSError):
    """Raised without local path details when the redacted image cannot be published."""


class ScreenshotFinding(BaseModel):
    """Value-free audit record for one sensitive OCR match."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    kind: SecretKind
    rule_id: str
    score: float = Field(strict=True, ge=0.0, le=1.0)
    box: tuple[int, int, int, int]
    match_sha256: Sha256


class ScreenshotRedactionResult(BaseModel):
    """Stable hashes and audit records for one locally redacted screenshot."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    source_sha256: Sha256
    output_sha256: Sha256
    width: int = Field(strict=True, gt=0)
    height: int = Field(strict=True, gt=0)
    findings: tuple[ScreenshotFinding, ...]


def _clamped_box(
    points: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    raw_left, raw_right = min(xs), max(xs)
    raw_top, raw_bottom = min(ys), max(ys)
    if (
        raw_right < 0
        or raw_left > width - 1
        or raw_bottom < 0
        or raw_top > height - 1
    ):
        raise OcrUnavailable("local OCR returned unusable geometry")
    left = min(max(raw_left - BOX_EXPANSION_PIXELS, 0), width - 1)
    top = min(max(raw_top - BOX_EXPANSION_PIXELS, 0), height - 1)
    right = min(max(raw_right + BOX_EXPANSION_PIXELS, 0), width - 1)
    bottom = min(max(raw_bottom + BOX_EXPANSION_PIXELS, 0), height - 1)
    return left, top, right, bottom


def _load_same_validated_bytes(source: Path, expected_sha256: str) -> bytes:
    try:
        source_bytes = source.read_bytes()
    except OSError:
        raise InvalidScreenshot("screenshot bytes could not be read") from None
    if sha256_bytes(source_bytes) != expected_sha256:
        raise InvalidScreenshot("screenshot changed during local processing")
    return source_bytes


def redact_screenshot(
    source: Path,
    output: Path,
    backend: OcrBackend,
) -> ScreenshotRedactionResult:
    """OCR locally, cover sensitive token boxes, and atomically publish a clean PNG."""

    source_path = Path(source)
    output_path = Path(output)
    if source_path.resolve() == output_path.resolve():
        raise UnsafeRedactionPath("redacted output must differ from the source screenshot")

    validated = validate_screenshot(source_path)
    try:
        tokens = backend.recognize(source_path)
    except Exception:
        raise OcrUnavailable("local OCR is unavailable") from None

    source_bytes = _load_same_validated_bytes(source_path, validated.source_sha256)
    try:
        with Image.open(BytesIO(source_bytes)) as opened:
            opened.load()
            converted = opened.convert("RGB")
            image = Image.new("RGB", converted.size, (255, 255, 255))
            image.paste(converted)
    except (OSError, UnidentifiedImageError, ValueError):
        raise InvalidScreenshot("screenshot bytes are not a valid image") from None

    draw = ImageDraw.Draw(image)
    findings: list[ScreenshotFinding] = []
    for token in tokens:
        candidates = scan_text("screenshot", token.text)
        if not candidates:
            continue
        box = _clamped_box(token.box, validated.width, validated.height)
        draw.rectangle(box, fill=(0, 0, 0))
        findings.extend(
            ScreenshotFinding(
                kind=candidate.kind,
                rule_id=candidate.rule_id,
                score=token.score,
                box=box,
                match_sha256=candidate.match_sha256,
            )
            for candidate in candidates
        )

    temp_path = output_path.with_name(
        f".{output_path.name}.{secrets.token_hex(8)}.tmp"
    )
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(temp_path, format="PNG", compress_level=9)
        output_sha256 = sha256_file(temp_path)
        result = ScreenshotRedactionResult(
            source_sha256=validated.source_sha256,
            output_sha256=output_sha256,
            width=validated.width,
            height=validated.height,
            findings=tuple(findings),
        )
        temp_path.replace(output_path)
        return result
    except OSError:
        raise RedactionWriteError("redacted screenshot could not be published") from None
    finally:
        with suppress(OSError):
            temp_path.unlink(missing_ok=True)
