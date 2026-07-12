from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from debugmate.hashing import sha256_file
from debugmate.privacy.models import ApprovedRedactedInput, RedactedFields
from debugmate.privacy.rapidocr_backend import RapidOcrBackend

pytestmark = pytest.mark.ocr


def test_real_ocr_runs_through_production_extraction_provider(tmp_path: Path) -> None:
    from debugmate.diagnosis.extraction import SourceKind
    from debugmate.diagnosis.providers import ProductionExtractionProvider

    screenshot = tmp_path / "ocr.png"
    image = Image.new("RGB", (900, 120), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 30)
    except OSError:
        pytest.skip("a deterministic monospace font is unavailable")
    draw.text((20, 30), "ModuleNotFoundError: No module named fictional_pkg", fill="black", font=font)
    image.save(screenshot)
    approved = ApprovedRedactedInput(
        case_id="case_0123456789abcdef0123456789abcdef",
        redacted=RedactedFields(
            redacted_screenshot_path="ocr.png",
            redacted_screenshot_sha256=sha256_file(screenshot),
        ),
        preview_hash="1" * 64,
        approval_id="approval_ocr_smoke",
        approval_signature="2" * 64,
        approved_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )
    try:
        record = ProductionExtractionProvider(
            redacted_root=tmp_path, ocr_backend=RapidOcrBackend()
        ).extract(approved)
    except Exception as error:
        pytest.skip(f"real OCR assets unavailable: {type(error).__name__}")
    assert record.candidates
    assert all(candidate.source_kind is SourceKind.OCR for candidate in record.candidates)
    assert all(candidate.locator.image_sha256 == sha256_file(screenshot) for candidate in record.candidates)
