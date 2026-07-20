"""Strict OCR contracts independent of any concrete recognition engine."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

Point = tuple[int, int]
OcrBox = tuple[Point, Point, Point, Point]


class OcrToken(BaseModel):
    """One immutable OCR result with a four-corner integer bounding box."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    text: str
    box: OcrBox
    score: float = Field(strict=True, ge=0.0, le=1.0)


@runtime_checkable
class OcrBackend(Protocol):
    """Port implemented by local OCR adapters without importing them here."""

    def recognize(self, path: Path) -> list[OcrToken]:
        """Recognize ordered tokens from a locally validated screenshot."""
        ...
