"""Deterministic extraction of selected official-documentation sections."""

from __future__ import annotations

import hashlib
import re
from typing import Final

from bs4 import BeautifulSoup, NavigableString, Tag
from pydantic import Field

from debugmate.knowledge.models import KnowledgeSource, StrictKnowledgeModel

EXTRACTOR_VERSION: Final = "1.0.0"
MAX_SECTION_CHARACTERS: Final = 8_000
_HEADING_NAMES = {f"h{level}" for level in range(1, 7)}
_NOISE_SELECTORS = (
    "nav",
    "footer",
    "script",
    "style",
    "aside",
    "[role='navigation']",
    ".sidebar",
    ".sphinxsidebar",
    ".bd-sidebar",
    ".wy-nav-side",
    ".copybutton",
    ".copybtn",
    "button.copy",
    "button[data-clipboard-target]",
)


class SourceStructureChanged(RuntimeError):
    """Configured headings no longer yield publishable source content."""


class ExtractedSection(StrictKnowledgeModel):
    """One normalized, bounded section with an official-page anchor."""

    heading: str = Field(min_length=1)
    source_locator: str = Field(pattern=r"^#.+")
    text: str = Field(min_length=1, max_length=MAX_SECTION_CHARACTERS)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _normalize_inline(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_code(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _render_node(node: Tag | NavigableString) -> list[str]:
    if isinstance(node, NavigableString):
        text = _normalize_inline(str(node))
        return [text] if text else []

    if node.name == "pre":
        code = _normalize_code(node.get_text("", strip=False))
        return [f"```\n{code}\n```"] if code else []
    if node.name in _HEADING_NAMES:
        text = _normalize_inline(node.get_text(" ", strip=True))
        return [f"{'#' * int(node.name[1])} {text}"] if text else []
    if node.name in {"ul", "ol"}:
        rendered: list[str] = []
        ordered = node.name == "ol"
        for index, item in enumerate(node.find_all("li", recursive=False), start=1):
            text = _normalize_inline(item.get_text(" ", strip=True))
            if text:
                rendered.append(f"{index}. {text}" if ordered else f"- {text}")
        return rendered
    if node.name in {"p", "li", "dt", "dd", "blockquote"}:
        text = _normalize_inline(node.get_text(" ", strip=True))
        return [text] if text else []
    if node.name in {"div", "section", "article", "main"}:
        rendered = []
        for child in node.children:
            rendered.extend(_render_node(child))
        return rendered

    text = _normalize_inline(node.get_text(" ", strip=True))
    return [text] if text else []


def _heading_level(heading: Tag) -> int:
    return int(heading.name[1])


def _locator(heading: Tag, heading_text: str) -> str:
    anchor = heading.get("id")
    if not anchor:
        descendant = heading.find(id=True) or heading.find("a", attrs={"name": True})
        if descendant is not None:
            anchor = descendant.get("id") or descendant.get("name")
    if not anchor:
        anchor = re.sub(r"[^a-z0-9]+", "-", heading_text.casefold()).strip("-")
    return f"#{anchor or 'section'}"


def _bounded(text: str) -> str:
    if len(text) <= MAX_SECTION_CHARACTERS:
        return text
    bounded = text[:MAX_SECTION_CHARACTERS].rstrip()
    if bounded.count("```") % 2:
        bounded = f"{bounded[: MAX_SECTION_CHARACTERS - 4].rstrip()}\n```"
    return bounded


def _section_text(heading: Tag) -> str:
    level = _heading_level(heading)
    blocks: list[str] = []
    sibling = heading.next_sibling
    while sibling is not None:
        if (
            isinstance(sibling, Tag)
            and sibling.name in _HEADING_NAMES
            and _heading_level(sibling) <= level
        ):
            break
        blocks.extend(_render_node(sibling))
        sibling = sibling.next_sibling
    return _bounded("\n\n".join(block for block in blocks if block).strip())


def extract_sections(source: KnowledgeSource, html: str) -> list[ExtractedSection]:
    """Extract configured heading ranges into stable, deduplicated text sections."""

    soup = BeautifulSoup(html, "html.parser")
    for selector in _NOISE_SELECTORS:
        for element in soup.select(selector):
            element.decompose()

    try:
        patterns = [re.compile(pattern, re.IGNORECASE) for pattern in source.heading_patterns]
    except re.error as exc:
        raise SourceStructureChanged(
            f"invalid heading pattern for source {source.source_id!r}"
        ) from exc

    sections: list[ExtractedSection] = []
    seen_hashes: set[str] = set()
    for heading in soup.find_all(_HEADING_NAMES):
        heading_text = _normalize_inline(heading.get_text(" ", strip=True))
        if not heading_text or not any(pattern.search(heading_text) for pattern in patterns):
            continue
        text = _section_text(heading)
        if not text:
            continue
        text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text_sha256 in seen_hashes:
            continue
        seen_hashes.add(text_sha256)
        sections.append(
            ExtractedSection(
                heading=heading_text,
                source_locator=_locator(heading, heading_text),
                text=text,
                text_sha256=text_sha256,
            )
        )

    if not sections:
        raise SourceStructureChanged(
            f"source {source.source_id!r} no longer contains configured heading sections"
        )
    return sections


__all__ = [
    "EXTRACTOR_VERSION",
    "ExtractedSection",
    "SourceStructureChanged",
    "extract_sections",
]
