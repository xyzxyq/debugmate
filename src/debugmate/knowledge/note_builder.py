"""Grounded, deterministic diagnostic notes from extracted official sections."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from typing import Final, Protocol

from pydantic import Field

from debugmate.contracts import ErrorCategory
from debugmate.knowledge.extractor import ExtractedSection
from debugmate.knowledge.fetcher import FetchedSource
from debugmate.knowledge.models import KnowledgeSource, StrictKnowledgeModel

NOTE_GENERATOR_VERSION: Final = "1.0.1"
MAX_NOTE_BYTES: Final = 32_000
MAX_SECTIONS_PER_NOTE: Final = 8
MAX_SNIPPET_CHARACTERS: Final = 600
MAX_SUMMARY_BULLETS: Final = 8
MAX_SUMMARY_BULLET_CHARACTERS: Final = 1_000
_CHINESE_CHARACTER = re.compile(r"[\u3400-\u9fff]")
_LOCATOR_TOKEN = re.compile(r"(?<![\w-])#[A-Za-z0-9][A-Za-z0-9._:-]*(?![\w-])")
_ASCII_TERM = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[._-][A-Za-z0-9]+)*")


class NoteSummarizer(Protocol):
    """Optional grounded summarizer boundary; implementations may call an LLM."""

    def summarize(
        self,
        *,
        source: KnowledgeSource,
        sections: Sequence[ExtractedSection],
    ) -> Sequence[str]:
        """Return Chinese diagnostic bullets containing official source locators."""


class DiagnosticNote(StrictKnowledgeModel):
    """One bounded Markdown note derived from one fetched official source."""

    source_id: str = Field(min_length=1)
    source_url: str = Field(pattern=r"^https://")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    categories: list[ErrorCategory] = Field(min_length=1)
    locators: list[str] = Field(min_length=1)
    markdown: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _frontmatter_value(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _short_text(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"


def _fallback_facts(sections: Sequence[ExtractedSection]) -> list[str]:
    return [
        f"- {section.source_locator}：官方“{section.heading}”章节记录："
        f"{_short_text(section.text, 240)}"
        for section in sections[:MAX_SECTIONS_PER_NOTE]
    ]


def _validated_summary(
    summarizer: NoteSummarizer | None,
    source: KnowledgeSource,
    sections: Sequence[ExtractedSection],
) -> list[str] | None:
    if summarizer is None:
        return None
    try:
        bullets = list(summarizer.summarize(source=source, sections=sections))
    except Exception:
        return None
    if not bullets or len(bullets) > MAX_SUMMARY_BULLETS:
        return None
    sections_by_locator = {section.source_locator: section for section in sections}
    validated: list[str] = []
    for bullet in bullets:
        if not isinstance(bullet, str):
            return None
        normalized = bullet.strip()
        if normalized.startswith("- "):
            normalized = normalized[2:].strip()
        locator_tokens = _LOCATOR_TOKEN.findall(normalized)
        exact_locators = [
            locator for locator in locator_tokens if locator in sections_by_locator
        ]
        if (
            not normalized
            or len(normalized) > MAX_SUMMARY_BULLET_CHARACTERS
            or _CHINESE_CHARACTER.search(normalized) is None
            or len(locator_tokens) != 1
            or len(exact_locators) != 1
        ):
            return None
        locator = exact_locators[0]
        summary_without_locator = normalized.replace(locator, " ", 1)
        summary_terms = {
            term.casefold() for term in _ASCII_TERM.findall(summary_without_locator)
        }
        section = sections_by_locator[locator]
        source_terms = {
            term.casefold()
            for term in _ASCII_TERM.findall(f"{section.heading} {section.text}")
        }
        overlapping_terms = summary_terms & source_terms
        if (
            len(overlapping_terms) < 2
            or len(overlapping_terms) / max(len(summary_terms), 1) < 0.8
        ):
            return None
        validated.append(f"- {normalized}")
    return validated


def _render_markdown(
    source: KnowledgeSource,
    fetched: FetchedSource,
    sections: Sequence[ExtractedSection],
    summarizer: NoteSummarizer | None,
) -> str:
    selected = list(sections[:MAX_SECTIONS_PER_NOTE])
    locators = [section.source_locator for section in selected]
    facts = _fallback_facts(selected)
    optional_summary = _validated_summary(summarizer, source, selected)
    categories = [category.value for category in source.error_categories]
    lines = [
        "---",
        f"source_id: {_frontmatter_value(source.source_id)}",
        f"source_url: {_frontmatter_value(source.url)}",
        f"source_sha256: {_frontmatter_value(fetched.sha256)}",
        f"title: {_frontmatter_value(source.title)}",
        f"product: {_frontmatter_value(source.product)}",
        f"version_scope: {_frontmatter_value(source.version_scope)}",
        f"platform: {_frontmatter_value(source.platform)}",
        "categories:",
        *(f"  - {_frontmatter_value(category)}" for category in categories),
        "locators:",
        *(f"  - {_frontmatter_value(locator)}" for locator in locators),
        f"license_or_terms_note: {_frontmatter_value(source.license_or_terms_note)}",
        "---",
        "",
        f"# {source.title}",
        "",
        "## 症状与分类",
        "",
        f"- 适用分类：{', '.join(categories)}",
        f"- 选取理由：{source.selection_reason}",
        "",
        "## 诊断事实",
        "",
        *facts,
        *(
            [
                "",
                "### 可选摘要（释义）",
                "",
                "以下释义已通过来源锚点与术语重合校验，原始确定性事实仍保留在上方。",
                "",
                *optional_summary,
            ]
            if optional_summary is not None
            else []
        ),
        "",
        "## 检查建议",
        "",
        *(
            f"- 核对 {section.source_locator} 中的“{section.heading}”约束，"
            "再与当前报错、版本和运行环境逐项比对。"
            for section in selected
        ),
        "",
        "## 版本与平台限制",
        "",
        f"- 版本范围：{source.version_scope}",
        f"- 平台范围：{source.platform}",
        "- 超出上述范围时应降低结论置信度，并重新核验对应版本的官方文档。",
        "",
        "## 来源锚点",
        "",
        *(f"- [{section.heading}]({source.url}{section.source_locator})" for section in selected),
        "",
        "## 短摘录",
        "",
        *(
            f"- {section.source_locator}：{_short_text(section.text, MAX_SNIPPET_CHARACTERS)}"
            for section in selected
        ),
        "",
    ]
    markdown = "\n".join(lines)
    if len(markdown.encode("utf-8")) >= MAX_NOTE_BYTES:
        raise ValueError("bounded diagnostic note unexpectedly exceeds 32,000 bytes")
    return markdown


def build_note(
    source: KnowledgeSource,
    fetched: FetchedSource,
    sections: Sequence[ExtractedSection],
    summarizer: NoteSummarizer | None = None,
) -> DiagnosticNote:
    """Render a stable note while retaining hashes and official anchors."""

    if not sections:
        raise ValueError("a diagnostic note requires at least one extracted section")
    markdown = _render_markdown(source, fetched, sections, summarizer)
    return DiagnosticNote(
        source_id=source.source_id,
        source_url=source.url,
        source_sha256=fetched.sha256,
        categories=list(source.error_categories),
        locators=[section.source_locator for section in sections[:MAX_SECTIONS_PER_NOTE]],
        markdown=markdown,
        content_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
    )


__all__ = [
    "DiagnosticNote",
    "NOTE_GENERATOR_VERSION",
    "NoteSummarizer",
    "build_note",
]
