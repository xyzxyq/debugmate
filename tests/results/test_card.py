from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from debugmate.results.card import (
    CANVAS_WIDTH,
    MAX_PNG_BYTES,
    CardRenderFailure,
    measure_card,
    render_card,
    verify_card_png,
    verify_prepared_font,
)
from debugmate.results.contracts import ArtifactAvailability
from debugmate.results.font import prepare_generation_context
from debugmate.results.loader import load_verified_outcome
from debugmate.results.presentation import build_presentation


def _font_copy(tmp_path: Path) -> Path:
    source = next(
        p
        for p in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf"))
        if p.is_file()
    )
    target = tmp_path / "assets" / "fonts" / source.name
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    return target


def _card_inputs(completed_source_bundle, tmp_path: Path):
    outcome, source = completed_source_bundle
    font = _font_copy(tmp_path)
    context = prepare_generation_context(
        project_root=tmp_path,
        project_font_candidates=(f"assets/fonts/{font.name}",),
        windows_font_candidates=(),
    )
    loaded = load_verified_outcome(outcome, evidence_root=source.parents[1])
    return build_presentation(loaded, context), context


def test_font_and_layout_are_bound_and_deterministic(
    completed_source_bundle, tmp_path: Path
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    assert verify_prepared_font(presentation, context).sha256 == presentation.font_sha256
    first = measure_card(presentation, context)
    second = measure_card(presentation, context)
    assert first == second
    assert first.canvas_width == CANVAS_WIDTH == 1600
    assert first.canvas_height > 0
    assert first.title == "DebugMate 诊断卡"
    assert presentation.identity.case_id[-8:] in first.identity_bar
    assert presentation.identity.generation_version in first.identity_bar
    assert [section.section_id for section in first.sections] == [
        "phenomenon",
        "causes",
        "checks",
        "fixes",
        "verification",
    ]
    for section in first.sections:
        assert section.x >= 0 and section.y >= 0
        assert section.x + section.width <= first.canvas_width
        assert section.y + section.height <= first.canvas_height
        assert all(line.width <= section.content_width for line in section.lines)
    causes = next(item for item in first.sections if item.section_id == "causes")
    assert all(
        evidence_id in "\n".join(line.text for line in causes.lines)
        for evidence_id in (item.evidence_id for item in presentation.citations)
    )


def test_font_change_and_profile_mismatch_fail_closed(
    completed_source_bundle, tmp_path: Path
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    context.resolved_font.path.write_bytes(context.resolved_font.path.read_bytes() + b"changed")
    with pytest.raises(CardRenderFailure, match="png_layout_failed"):
        measure_card(presentation, context)


def test_renderer_writes_deterministic_clean_rgb_png(
    completed_source_bundle, tmp_path: Path
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    first = render_card(presentation, context, target=tmp_path / "one.png")
    second = render_card(presentation, context, target=tmp_path / "two.png")
    assert first.sha256 == second.sha256
    assert (tmp_path / "one.png").read_bytes() == (tmp_path / "two.png").read_bytes()
    with Image.open(first.path) as image:
        assert image.format == "PNG"
        assert image.mode == "RGB"
        assert image.n_frames == 1
        assert image.width == 1600
        assert image.info == {}
    assert first.identity == presentation.identity
    assert first.font_sha256 == context.resolved_font.sha256


def test_png_verifier_rejects_metadata_and_animation_like_chunks(tmp_path: Path) -> None:
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "hidden")
    bad = tmp_path / "bad.png"
    Image.new("RGB", (1600, 10), "white").save(bad, pnginfo=metadata)
    with pytest.raises(CardRenderFailure, match="png_verify_failed"):
        verify_card_png(bad, expected_size=(1600, 10))
    payload = bad.read_bytes().replace(b"tEXt", b"acTL", 1)
    bad.write_bytes(payload)
    with pytest.raises(CardRenderFailure, match="png_verify_failed"):
        verify_card_png(bad, expected_size=(1600, 10))


def test_png_verifier_rejects_real_apng(tmp_path: Path) -> None:
    bad = tmp_path / "animated.png"
    frames = [Image.new("RGB", (1600, 10), color) for color in ("white", "black")]
    frames[0].save(bad, save_all=True, append_images=frames[1:], duration=10, loop=0)
    with pytest.raises(CardRenderFailure, match="png_verify_failed"):
        verify_card_png(bad, expected_size=(1600, 10))


def _chunks(payload: bytes) -> list[tuple[bytes, bytes]]:
    offset = 8
    result = []
    while offset < len(payload):
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        kind = payload[offset + 4 : offset + 8]
        data = payload[offset + 8 : offset + 8 + length]
        result.append((kind, data))
        offset += 12 + length
    return result


def _png(parts: list[tuple[bytes, bytes]]) -> bytes:
    output = bytearray(b"\x89PNG\r\n\x1a\n")
    for kind, data in parts:
        output.extend(struct.pack(">I", len(data)))
        output.extend(kind)
        output.extend(data)
        output.extend(struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    return bytes(output)


def test_png_verifier_rejects_crc_duplicate_split_and_order_attacks(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (1600, 10), "white").save(source)
    original = source.read_bytes()
    parts = _chunks(original)
    ihdr = next(item for item in parts if item[0] == b"IHDR")
    idat = next(item for item in parts if item[0] == b"IDAT")
    iend = next(item for item in parts if item[0] == b"IEND")
    attacks = [
        original[:-1] + bytes([original[-1] ^ 1]),
        _png([ihdr, ihdr, idat, iend]),
        _png([ihdr, (b"IDAT", idat[1][:1]), (b"IDAT", idat[1][1:]), iend]),
        _png([ihdr, iend, idat]),
        _png([ihdr, idat, iend, iend]),
    ]
    for index, payload in enumerate(attacks):
        target = tmp_path / f"attack-{index}.png"
        target.write_bytes(payload)
        with pytest.raises(CardRenderFailure, match="png_verify_failed"):
            verify_card_png(target, expected_size=(1600, 10))


def test_png_resource_limits_are_checked_before_decode(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.png"
    with oversized.open("wb") as stream:
        stream.write(b"\x89PNG\r\n\x1a\n")
        stream.seek(MAX_PNG_BYTES)
        stream.write(b"x")
    with pytest.raises(CardRenderFailure, match="png_verify_failed"):
        verify_card_png(oversized, expected_size=(1600, 10))

    wrong_width = tmp_path / "wrong-width.png"
    Image.new("RGB", (1599, 10), "white").save(wrong_width)
    with pytest.raises(CardRenderFailure, match="png_verify_failed"):
        verify_card_png(wrong_width, expected_size=(1599, 10))

    huge = tmp_path / "huge-header.png"
    ihdr = struct.pack(">IIBBBBB", 1600, 20_000, 8, 2, 0, 0, 0)
    huge.write_bytes(_png([(b"IHDR", ihdr), (b"IDAT", b"x"), (b"IEND", b"")]))
    with pytest.raises(CardRenderFailure, match="png_verify_failed"):
        verify_card_png(huge, expected_size=(1600, 20_000))


def test_final_disk_verify_failure_removes_success_looking_target(
    completed_source_bundle, tmp_path: Path, monkeypatch
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    target = tmp_path / "card.png"
    from debugmate.results import card

    original = card.verify_card_png
    calls = 0

    def fail_second(path: Path, *, expected_size: tuple[int, int]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise CardRenderFailure("png_verify_failed")
        original(path, expected_size=expected_size)

    monkeypatch.setattr(card, "verify_card_png", fail_second)
    with pytest.raises(CardRenderFailure, match="png_verify_failed"):
        render_card(presentation, context, target=target)
    assert not target.exists()


def test_failure_is_safe_partial_and_cleans_target(
    completed_source_bundle, tmp_path: Path, monkeypatch
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    target = tmp_path / "card.png"
    monkeypatch.setattr("debugmate.results.card.MAX_PNG_HEIGHT", 1)
    with pytest.raises(CardRenderFailure) as caught:
        render_card(presentation, context, target=target)
    assert caught.value.code == "png_layout_failed"
    assert caught.value.failed_stage == caught.value.retry_scope == "card"
    assert caught.value.availability == ArtifactAvailability(
        report=True, card=False, recap_text=True, audio=True
    )
    assert not target.exists()
    assert not list(tmp_path.glob(".card.png.*.tmp"))
    assert str(tmp_path) not in str(caught.value)


def test_height_and_pixel_limits_accept_exact_and_reject_plus_one(
    completed_source_bundle, tmp_path: Path, monkeypatch
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    from debugmate.results import card

    baseline = measure_card(presentation, context)
    monkeypatch.setattr(card, "MAX_PNG_HEIGHT", baseline.canvas_height)
    monkeypatch.setattr(card, "MAX_PNG_PIXELS", 1600 * baseline.canvas_height)
    assert measure_card(presentation, context).canvas_height == baseline.canvas_height
    monkeypatch.setattr(card, "MAX_PNG_HEIGHT", baseline.canvas_height - 1)
    with pytest.raises(CardRenderFailure, match="png_layout_failed"):
        measure_card(presentation, context)
    monkeypatch.setattr(card, "MAX_PNG_HEIGHT", baseline.canvas_height)
    monkeypatch.setattr(card, "MAX_PNG_PIXELS", 1600 * baseline.canvas_height - 1)
    with pytest.raises(CardRenderFailure, match="png_layout_failed"):
        measure_card(presentation, context)


def test_item_limit_accepts_exact_and_rejects_plus_one(
    completed_source_bundle, tmp_path: Path, monkeypatch
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    from debugmate.results import card

    def definitions(count: int):
        return (("phenomenon", "现象", tuple("x" for _ in range(count))),)

    monkeypatch.setattr(card, "MAX_PNG_HEIGHT", 100_000)
    monkeypatch.setattr(card, "MAX_PNG_PIXELS", 160_000_000)
    monkeypatch.setattr(card, "_sections", lambda _: definitions(card.MAX_CARD_ITEMS))
    assert measure_card(presentation, context).sections[0].lines
    monkeypatch.setattr(card, "_sections", lambda _: definitions(card.MAX_CARD_ITEMS + 1))
    with pytest.raises(CardRenderFailure, match="png_layout_failed"):
        measure_card(presentation, context)


def test_text_limit_and_multilingual_long_tokens_are_measured(
    completed_source_bundle, tmp_path: Path, monkeypatch
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    from debugmate.results import card

    monkeypatch.setattr(card, "MAX_PNG_HEIGHT", 100_000)
    monkeypatch.setattr(card, "MAX_PNG_PIXELS", 160_000_000)
    mixed = "中文报错 " + "C:/fictional/" + "A" * 500 + " --flag=value"
    monkeypatch.setattr(card, "_sections", lambda _: (("phenomenon", "现象", (mixed,)),))
    layout = measure_card(presentation, context)
    assert len(layout.sections[0].lines) > 1
    assert all(line.width <= layout.sections[0].content_width for line in layout.sections[0].lines)

    monkeypatch.setattr(card, "MAX_CARD_TEXT_CHARS", len(mixed) - 1)
    with pytest.raises(CardRenderFailure, match="png_layout_failed"):
        measure_card(presentation, context)


def test_paint_exception_is_value_free_and_cleans_temp(
    completed_source_bundle, tmp_path: Path, monkeypatch
) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    target = tmp_path / "card.png"

    def explode(*args, **kwargs):
        raise RuntimeError(f"sensitive {tmp_path}")

    monkeypatch.setattr("debugmate.results.card.Image.new", explode)
    with pytest.raises(CardRenderFailure, match="png_render_failed") as caught:
        render_card(presentation, context, target=target)
    assert str(tmp_path) not in str(caught.value)
    assert not target.exists()
    assert not list(tmp_path.glob(".card.png.*.tmp"))


def test_layout_golden_is_font_hash_qualified(completed_source_bundle, tmp_path: Path) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    layout = measure_card(presentation, context)
    payload = layout.model_dump(mode="json")
    golden = json.loads(
        (Path(__file__).parent / "golden" / "card-layout.json").read_text(encoding="utf-8")
    )
    assert payload["canvas_width"] == golden["canvas_width"]
    assert payload["section_order"] == golden["section_order"]
    assert len(payload["sections"]) == golden["section_count"]
    assert payload["font_sha256"] == context.resolved_font.sha256
