from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from debugmate.knowledge.extractor import extract_sections
from debugmate.knowledge.fetcher import fetch_source
from debugmate.knowledge.models import KnowledgeSource, load_registry

ROOT = Path(__file__).resolve().parents[2]
SOURCES = load_registry(ROOT / "knowledge" / "sources.json").sources


@pytest.mark.cloud
@pytest.mark.parametrize("source", SOURCES, ids=lambda source: source.source_id)
def test_registered_official_source_is_direct_html_with_matching_sections(
    source: KnowledgeSource,
) -> None:
    """Opt-in drift probe: every registered URL is direct and still extractable."""

    with httpx.Client(
        follow_redirects=False,
        headers={"User-Agent": "DebugMate-Coursework-Knowledge-Probe/1.0"},
    ) as client:
        fetched = fetch_source(source, client)

    sections = extract_sections(source, fetched.html)

    assert fetched.final_url == source.url
    assert sections
