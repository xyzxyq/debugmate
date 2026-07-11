"""Lazy, value-safe adapter for RapidOCR 3.9.x output objects."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from numbers import Real
from pathlib import Path
from typing import Any

from debugmate.privacy.image_redactor import OcrUnavailable
from debugmate.privacy.ocr import OcrToken

EngineFactory = Callable[[], Any]


def _default_factory() -> Any:
    from rapidocr import RapidOCR

    return RapidOCR()


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes, bytearray, dict)):
        raise TypeError
    return list(value)


def _coordinate(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError
    number = float(value)
    if not math.isfinite(number):
        raise ValueError
    # Python's round is deterministic round-half-to-even; make that policy explicit.
    return round(number)


def _normalize(result: Any) -> list[OcrToken]:
    boxes = _items(result.boxes)
    texts = _items(result.txts)
    scores = _items(result.scores)
    if not (len(boxes) == len(texts) == len(scores)):
        raise ValueError

    tokens: list[OcrToken] = []
    for raw_box, text, raw_score in zip(boxes, texts, scores, strict=True):
        points = _items(raw_box)
        if len(points) != 4 or not isinstance(text, str) or not text:
            raise ValueError
        box: list[tuple[int, int]] = []
        for raw_point in points:
            point = _items(raw_point)
            if len(point) != 2:
                raise ValueError
            box.append((_coordinate(point[0]), _coordinate(point[1])))
        if isinstance(raw_score, bool) or not isinstance(raw_score, Real):
            raise TypeError
        score = float(raw_score)
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError
        tokens.append(OcrToken(text=text, box=tuple(box), score=score))  # type: ignore[arg-type]
    return tokens


@dataclass(slots=True)
class RapidOcrBackend:
    """Instantiate the OCR model only on first recognition, never in repr output."""

    factory: EngineFactory = field(default=_default_factory, repr=False)
    engine: Any | None = field(default=None, repr=False)

    def recognize(self, path: Path) -> list[OcrToken]:
        try:
            if self.engine is None:
                self.engine = self.factory()
            result = self.engine(str(path))
            return _normalize(result)
        except Exception:
            raise OcrUnavailable("local OCR is unavailable") from None
