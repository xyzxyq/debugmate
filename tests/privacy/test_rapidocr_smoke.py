from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from debugmate.privacy.rapidocr_backend import RapidOcrBackend

pytestmark = pytest.mark.ocr


def test_real_rapidocr_adapter_recognizes_synthetic_windows_path(tmp_path: Path) -> None:
    source = tmp_path / "rapidocr-smoke.png"
    image = Image.new("RGB", (720, 100), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 32)
    draw.text((20, 25), r"C:\Users\student", fill="black", font=font)
    image.save(source)

    tokens = RapidOcrBackend().recognize(source)

    assert tokens
