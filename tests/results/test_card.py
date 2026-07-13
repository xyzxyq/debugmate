from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from debugmate.results.card import (
    CANVAS_WIDTH,
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
    source = next(p for p in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")) if p.is_file())
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


def test_font_and_layout_are_bound_and_deterministic(completed_source_bundle, tmp_path: Path) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    assert verify_prepared_font(presentation, context).sha256 == presentation.font_sha256
    first = measure_card(presentation, context)
    second = measure_card(presentation, context)
    assert first == second
    assert first.canvas_width == CANVAS_WIDTH == 1600
    assert first.canvas_height > 0
    assert [section.section_id for section in first.sections] == [
        "phenomenon", "causes", "checks", "fixes", "verification"
    ]
    for section in first.sections:
        assert section.x >= 0 and section.y >= 0
        assert section.x + section.width <= first.canvas_width
        assert section.y + section.height <= first.canvas_height
        assert all(line.width <= section.content_width for line in section.lines)


def test_font_change_and_profile_mismatch_fail_closed(completed_source_bundle, tmp_path: Path) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    context.resolved_font.path.write_bytes(context.resolved_font.path.read_bytes() + b"changed")
    with pytest.raises(CardRenderFailure, match="png_layout_failed"):
        measure_card(presentation, context)


def test_renderer_writes_deterministic_clean_rgb_png(completed_source_bundle, tmp_path: Path) -> None:
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


def test_failure_is_safe_partial_and_cleans_target(completed_source_bundle, tmp_path: Path, monkeypatch) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    target = tmp_path / "card.png"
    monkeypatch.setattr("debugmate.results.card.MAX_PNG_HEIGHT", 1)
    with pytest.raises(CardRenderFailure) as caught:
        render_card(presentation, context, target=target)
    assert caught.value.code == "png_layout_failed"
    assert caught.value.failed_stage == caught.value.retry_scope == "card"
    assert caught.value.availability == ArtifactAvailability(report=True, card=False, recap_text=True, audio=True)
    assert not target.exists()
    assert not list(tmp_path.glob(".card.png.*.tmp"))
    assert str(tmp_path) not in str(caught.value)


def test_layout_golden_is_font_hash_qualified(completed_source_bundle, tmp_path: Path) -> None:
    presentation, context = _card_inputs(completed_source_bundle, tmp_path)
    layout = measure_card(presentation, context)
    payload = layout.model_dump(mode="json")
    golden = json.loads((Path(__file__).parent / "golden" / "card-layout.json").read_text(encoding="utf-8"))
    assert payload["canvas_width"] == golden["canvas_width"]
    assert payload["section_order"] == golden["section_order"]
    assert len(payload["sections"]) == golden["section_count"]
    assert payload["font_sha256"] == context.resolved_font.sha256
