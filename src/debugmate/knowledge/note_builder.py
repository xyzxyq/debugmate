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

NOTE_GENERATOR_VERSION: Final = "1.0.3"
MAX_NOTE_BYTES: Final = 32_000
MAX_SECTIONS_PER_NOTE: Final = 8
MAX_SNIPPET_CHARACTERS: Final = 600


class NoteSummarizer(Protocol):
    """Reserved summarizer boundary, excluded from authoritative MVP notes."""

    def summarize(
        self,
        *,
        source: KnowledgeSource,
        sections: Sequence[ExtractedSection],
    ) -> Sequence[str]:
        """Return candidate text for a future entailment-verified side channel."""


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
    def inline_fence(match: re.Match[str]) -> str:
        code = re.sub(r"\s+", " ", match.group(1)).strip()
        return code

    inline_code = re.sub(
        r"```\s*(.*?)\s*```",
        inline_fence,
        text,
        flags=re.DOTALL,
    ).replace("`", "")
    normalized = re.sub(r"\s+", " ", inline_code).strip()
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"


def _fallback_facts(sections: Sequence[ExtractedSection]) -> list[str]:
    return [
        f"- {section.source_locator}：官方“{section.heading}”章节记录："
        f"{_short_text(section.text, 240)}"
        for section in sections[:MAX_SECTIONS_PER_NOTE]
    ]


def _render_markdown(
    source: KnowledgeSource,
    fetched: FetchedSource,
    sections: Sequence[ExtractedSection],
) -> str:
    selected = list(sections[:MAX_SECTIONS_PER_NOTE])
    locators = [section.source_locator for section in selected]
    facts = _fallback_facts(selected)
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
    # Lexical or locator checks cannot prove entailment. Until an entailment
    # verifier exists, candidate LLM text is deliberately neither called nor
    # persisted in authoritative/syncable notes.
    del summarizer
    markdown = _render_markdown(source, fetched, sections)
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
