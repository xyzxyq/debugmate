"""Validated screenshot contract and deterministic local image checks."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field

from debugmate.hashing import sha256_bytes
from debugmate.privacy.models import Sha256

MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024
MAX_SCREENSHOT_PIXELS = 20_000_000


class InvalidScreenshot(ValueError):
    """Raised when local screenshot validation rejects an input."""


class ValidatedImage(BaseModel):
    """Canonical, immutable facts derived from verified screenshot bytes."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    width: int = Field(strict=True, gt=0)
    height: int = Field(strict=True, gt=0)
    format: Literal["PNG", "JPEG"]
    source_sha256: Sha256


def validate_screenshot(path: Path) -> ValidatedImage:
    """Verify screenshot bytes and enforce the local upload safety limits."""

    candidate = Path(path)
    try:
        with candidate.open("rb") as source:
            source_bytes = source.read(MAX_SCREENSHOT_BYTES + 1)
    except OSError:
        raise InvalidScreenshot("screenshot bytes could not be read") from None

    if len(source_bytes) > MAX_SCREENSHOT_BYTES:
        raise InvalidScreenshot("screenshot exceeds the 10 MiB limit")

    try:
        with Image.open(BytesIO(source_bytes)) as image:
            image.verify()

        with Image.open(BytesIO(source_bytes)) as image:
            image_format = image.format
            width, height = image.size
    except (OSError, UnidentifiedImageError, ValueError):
        raise InvalidScreenshot("screenshot bytes are not a valid image") from None

    if image_format not in {"PNG", "JPEG"}:
        raise InvalidScreenshot("screenshot format must be PNG or JPEG")
    if width <= 0 or height <= 0:
        raise InvalidScreenshot("screenshot dimensions must be positive")
    if width * height > MAX_SCREENSHOT_PIXELS:
        raise InvalidScreenshot("screenshot exceeds the 20 megapixels limit")

    return ValidatedImage(
        width=width,
        height=height,
        format=image_format,
        source_sha256=sha256_bytes(source_bytes),
    )
