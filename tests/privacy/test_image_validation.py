from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from typing import runtime_checkable

import pytest
from PIL import Image
from pydantic import ValidationError

from debugmate.privacy.image_models import (
    MAX_SCREENSHOT_BYTES,
    InvalidScreenshot,
    validate_screenshot,
)
from debugmate.privacy.ocr import OcrBackend, OcrToken


def write_image(
    directory: Path,
    *,
    size: tuple[int, int] = (16, 12),
    image_format: str = "PNG",
    name: str = "screenshot.png",
) -> Path:
    path = directory / name
    Image.new("RGB", size, "white").save(path, format=image_format)
    return path


def test_extension_cannot_disguise_non_image(tmp_path: Path) -> None:
    path = tmp_path / "fake.png"
    path.write_bytes(b"not an image")

    with pytest.raises(InvalidScreenshot) as exc_info:
        validate_screenshot(path)

    assert str(path.resolve()) not in str(exc_info.value)


def test_file_header_determines_canonical_format_not_extension(tmp_path: Path) -> None:
    path = write_image(tmp_path, image_format="JPEG", name="actually-jpeg.png")
    source_bytes = path.read_bytes()

    result = validate_screenshot(path)

    assert result.format == "JPEG"
    assert (result.width, result.height) == (16, 12)
    assert result.source_sha256 == hashlib.sha256(source_bytes).hexdigest()


def test_validation_and_hash_use_one_captured_byte_sequence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_image(tmp_path, size=(16, 12), image_format="JPEG", name="source.jpg")
    captured_path = write_image(tmp_path, size=(9, 7), name="captured.png")
    captured_bytes = captured_path.read_bytes()
    original_open = Path.open
    open_count = 0

    def controlled_open(self: Path, *args: object, **kwargs: object) -> object:
        nonlocal open_count
        if self == path:
            open_count += 1
            return BytesIO(captured_bytes)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", controlled_open)

    result = validate_screenshot(path)

    assert open_count == 1
    assert (result.width, result.height, result.format) == (9, 7, "PNG")
    assert result.source_sha256 == hashlib.sha256(captured_bytes).hexdigest()


def test_unsupported_verified_image_format_is_rejected(tmp_path: Path) -> None:
    path = write_image(tmp_path, image_format="GIF", name="screenshot.png")

    with pytest.raises(InvalidScreenshot, match="PNG or JPEG"):
        validate_screenshot(path)


def test_file_of_exactly_ten_mib_is_allowed(tmp_path: Path) -> None:
    path = write_image(tmp_path)
    source_bytes = path.read_bytes()
    path.write_bytes(source_bytes + b"\0" * (MAX_SCREENSHOT_BYTES - len(source_bytes)))

    result = validate_screenshot(path)

    assert result.source_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()


def test_file_larger_than_ten_mib_is_rejected_without_leaking_path(
    tmp_path: Path,
) -> None:
    path = write_image(tmp_path)
    source_bytes = path.read_bytes()
    path.write_bytes(source_bytes + b"\0" * (MAX_SCREENSHOT_BYTES + 1 - len(source_bytes)))

    with pytest.raises(InvalidScreenshot, match="10 MiB") as exc_info:
        validate_screenshot(path)

    assert str(path.resolve()) not in str(exc_info.value)


def test_read_failure_does_not_leak_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_image(tmp_path)

    def fail_open(self: Path, *args: object, **kwargs: object) -> object:
        if self == path:
            raise OSError(f"cannot read {path.resolve()}")
        return original_open(self, *args, **kwargs)

    original_open = Path.open
    monkeypatch.setattr(Path, "open", fail_open)

    with pytest.raises(InvalidScreenshot) as exc_info:
        validate_screenshot(path)

    assert str(path.resolve()) not in str(exc_info.value)


def test_large_dimensions_are_rejected(tmp_path: Path) -> None:
    path = write_image(tmp_path, size=(5000, 5000))

    with pytest.raises(InvalidScreenshot, match="20 megapixels"):
        validate_screenshot(path)


def test_non_positive_dimensions_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_image(tmp_path)

    class InvalidDimensions:
        format = "PNG"
        size = (0, 12)

        def __enter__(self) -> InvalidDimensions:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def verify(self) -> None:
            return None

    monkeypatch.setattr("debugmate.privacy.image_models.Image.open", lambda _: InvalidDimensions())

    with pytest.raises(InvalidScreenshot, match="positive"):
        validate_screenshot(path)


def test_ocr_token_is_strict_immutable_and_requires_four_integer_points() -> None:
    token = OcrToken(
        text="Traceback",
        box=((1, 2), (3, 4), (5, 6), (7, 8)),
        score=0.75,
    )

    with pytest.raises(ValidationError):
        token.text = "changed"
    with pytest.raises(ValidationError):
        OcrToken(text="x", box=((1, 2), (3, 4), (5, 6)), score=0.5)
    with pytest.raises(ValidationError):
        OcrToken(text="x", box=((1.0, 2), (3, 4), (5, 6), (7, 8)), score=0.5)
    with pytest.raises(ValidationError):
        OcrToken(text="x", box=((1, 2), (3, 4), (5, 6), (7, 8)), score=1.01)


def test_ocr_backend_is_runtime_checkable() -> None:
    assert getattr(OcrBackend, "_is_runtime_protocol", False)
    assert runtime_checkable(OcrBackend) is OcrBackend

    class Backend:
        def recognize(self, path: Path) -> list[OcrToken]:
            return []

    assert isinstance(Backend(), OcrBackend)


def test_validated_image_contract_is_strict_and_immutable(tmp_path: Path) -> None:
    result = validate_screenshot(write_image(tmp_path))

    with pytest.raises(ValidationError):
        result.width = 99
    with pytest.raises(ValidationError):
        type(result)(
            width="16",
            height=12,
            format="PNG",
            source_sha256=result.source_sha256,
        )
    with pytest.raises(ValidationError):
        type(result)(
            width=16,
            height=12,
            format="GIF",
            source_sha256=result.source_sha256,
        )
