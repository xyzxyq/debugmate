from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin
from pydantic import ValidationError

from debugmate.hashing import sha256_file
from debugmate.privacy.image_redactor import (
    OcrUnavailable,
    UnsafeRedactionPath,
    redact_screenshot,
)
from debugmate.privacy.ocr import OcrToken


class FakeOcr:
    def __init__(self, tokens: list[OcrToken]) -> None:
        self.tokens = tokens
        self.calls: list[Path] = []

    def recognize(self, path: Path) -> list[OcrToken]:
        self.calls.append(path)
        return self.tokens


class FailingOcr:
    def recognize(self, path: Path) -> list[OcrToken]:
        raise RuntimeError(f"OCR failed for {path.resolve()}")


def write_source(directory: Path, *, metadata: bool = False) -> Path:
    path = directory / "source.png"
    image = Image.new("RGB", (200, 80), (255, 255, 255))
    pnginfo = None
    if metadata:
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("secret", "student@example.com")
    image.save(path, format="PNG", pnginfo=pnginfo)
    return path


def sensitive_token() -> OcrToken:
    return OcrToken(
        text=r"C:\Users\student\secret.py",
        box=((10, 10), (180, 10), (180, 35), (10, 35)),
        score=0.99,
    )


def test_sensitive_ocr_box_is_opaque_and_audit_has_no_text(tmp_path: Path) -> None:
    source = write_source(tmp_path)
    output = tmp_path / "redacted.png"
    result = redact_screenshot(source, output, FakeOcr([sensitive_token()]))

    with Image.open(output) as image:
        pixels = image.convert("RGB")
        for x in range(7, 184):
            for y in range(7, 39):
                assert pixels.getpixel((x, y)) == (0, 0, 0)
        adjacent_points = (
            [(6, y) for y in range(7, 39)]
            + [(184, y) for y in range(7, 39)]
            + [(x, 6) for x in range(7, 184)]
            + [(x, 39) for x in range(7, 184)]
        )
        for point in adjacent_points:
            assert pixels.getpixel(point) == (255, 255, 255)
    serialized = result.model_dump_json()
    assert "student" not in serialized
    assert str(source) not in serialized
    assert len(result.findings) == 1
    assert result.findings[0].box == (7, 7, 183, 38)
    assert result.output_sha256 == sha256_file(output)


def test_expanded_box_is_clamped_to_image_bounds(tmp_path: Path) -> None:
    source = write_source(tmp_path)
    output = tmp_path / "redacted.png"
    token = OcrToken(
        text="mail=user@example.com",
        box=((-5, -4), (8, -4), (8, 6), (-5, 6)),
        score=0.8,
    )

    result = redact_screenshot(source, output, FakeOcr([token]))

    assert result.findings[0].box == (0, 0, 11, 9)
    with Image.open(output) as image:
        assert image.convert("RGB").getpixel((0, 0)) == (0, 0, 0)


@pytest.mark.parametrize(
    "box",
    [
        ((-20, 10), (-10, 10), (-10, 20), (-20, 20)),
        ((210, 10), (220, 10), (220, 20), (210, 20)),
        ((10, -20), (20, -20), (20, -10), (10, -10)),
        ((10, 90), (20, 90), (20, 100), (10, 100)),
    ],
    ids=("left", "right", "above", "below"),
)
def test_fully_outside_sensitive_box_fails_closed(
    tmp_path: Path,
    box: tuple[tuple[int, int], tuple[int, int], tuple[int, int], tuple[int, int]],
) -> None:
    source = write_source(tmp_path)
    token = OcrToken(text=r"C:\Users\student\secret.py", box=box, score=0.99)
    fresh_output = tmp_path / "fresh.png"
    existing_output = tmp_path / "existing.png"
    existing_output.write_bytes(b"previous-safe-output")

    for output in (fresh_output, existing_output):
        with pytest.raises(OcrUnavailable) as caught:
            redact_screenshot(source, output, FakeOcr([token]))
        message = str(caught.value)
        assert token.text not in message
        assert str(source) not in message

    assert not fresh_output.exists()
    assert existing_output.read_bytes() == b"previous-safe-output"


def test_same_input_and_tokens_produce_identical_png_bytes(tmp_path: Path) -> None:
    source = write_source(tmp_path, metadata=True)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    first_result = redact_screenshot(source, first, FakeOcr([sensitive_token()]))
    second_result = redact_screenshot(source, second, FakeOcr([sensitive_token()]))

    assert first.read_bytes() == second.read_bytes()
    assert first_result.output_sha256 == second_result.output_sha256
    with Image.open(first) as image:
        assert image.mode == "RGB"
        assert image.info == {}
        assert image.getexif() == {}


def test_non_sensitive_tokens_still_produce_normalized_png(tmp_path: Path) -> None:
    source = write_source(tmp_path, metadata=True)
    output = tmp_path / "redacted.png"
    token = OcrToken(
        text="ModuleNotFoundError",
        box=((1, 1), (100, 1), (100, 20), (1, 20)),
        score=0.95,
    )

    result = redact_screenshot(source, output, FakeOcr([token]))

    assert not result.findings
    with Image.open(output) as image:
        assert image.format == "PNG"
        assert image.info == {}


def test_backend_failure_is_safe_and_never_copies_source(tmp_path: Path) -> None:
    source = write_source(tmp_path)
    output = tmp_path / "redacted.png"

    with pytest.raises(OcrUnavailable) as caught:
        redact_screenshot(source, output, FailingOcr())

    assert not output.exists()
    assert str(source.resolve()) not in str(caught.value)
    assert not any(item.name.startswith(f".{output.name}.") for item in tmp_path.iterdir())


def test_backend_failure_preserves_preexisting_output(tmp_path: Path) -> None:
    source = write_source(tmp_path)
    output = tmp_path / "redacted.png"
    output.write_bytes(b"previous-safe-output")

    with pytest.raises(OcrUnavailable):
        redact_screenshot(source, output, FailingOcr())

    assert output.read_bytes() == b"previous-safe-output"


def test_source_and_output_must_differ(tmp_path: Path) -> None:
    source = write_source(tmp_path)

    with pytest.raises(UnsafeRedactionPath):
        redact_screenshot(source, source, FakeOcr([sensitive_token()]))

    with Image.open(source) as image:
        assert image.format == "PNG"


def test_audit_contract_is_strict_and_immutable(tmp_path: Path) -> None:
    source = write_source(tmp_path)
    result = redact_screenshot(source, tmp_path / "redacted.png", FakeOcr([sensitive_token()]))
    finding = result.findings[0]

    with pytest.raises(ValidationError):
        finding.score = 0.1
    with pytest.raises(ValidationError):
        type(finding).model_validate({**finding.model_dump(), "text": "secret"})
