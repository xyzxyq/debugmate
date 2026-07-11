"""Deterministic coverage reporting for immutable knowledge builds."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from debugmate.contracts import ErrorCategory
from debugmate.knowledge.build import KnowledgeBuild
from debugmate.knowledge.models import StrictKnowledgeModel


class CategoryCoverage(StrictKnowledgeModel):
    """Auditable coverage counts for one stable error category."""

    source_count: int = Field(ge=0)
    note_count: int = Field(ge=0)
    locator_count: int = Field(ge=0)
    last_fetched_utc: str | None
    current_build_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class CoverageReport(StrictKnowledgeModel):
    """Coverage for every category, including deterministic blind spots."""

    build_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    build_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    categories: dict[ErrorCategory, CategoryCoverage]
    blind_spots: list[str]


def build_path(build: KnowledgeBuild | Path) -> Path:
    """Resolve the immutable build directory from a build object or path."""

    return build.path if isinstance(build, KnowledgeBuild) else build


def load_build_manifest(build: KnowledgeBuild | Path) -> dict[str, object]:
    """Load the manifest emitted by the authoritative build pipeline."""

    path = build_path(build) / "manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("knowledge build manifest root must be an object")
    return value


def coverage_report(build: KnowledgeBuild | Path) -> CoverageReport:
    """Report source, note and locator coverage for every ``ErrorCategory``."""

    manifest = load_build_manifest(build)
    build_id = str(manifest["build_id"])
    build_hash = str(manifest["content_hash"])
    sources = manifest.get("sources", [])
    notes = manifest.get("notes", [])
    if not isinstance(sources, list) or not isinstance(notes, list):
        raise ValueError("knowledge build manifest sources and notes must be lists")

    source_times = {
        str(source["source_id"]): str(source["retrieved_at"])
        for source in sources
        if isinstance(source, dict)
    }
    categories: dict[ErrorCategory, CategoryCoverage] = {}
    for category in ErrorCategory:
        matching_notes = [
            note
            for note in notes
            if isinstance(note, dict)
            and category.value in note.get("categories", [])
        ]
        source_ids = sorted({str(note["source_id"]) for note in matching_notes})
        locator_count = sum(
            len(note.get("locators", []))
            for note in matching_notes
            if isinstance(note.get("locators", []), list)
        )
        fetched = sorted(
            source_times[source_id]
            for source_id in source_ids
            if source_id in source_times
        )
        categories[category] = CategoryCoverage(
            source_count=len(source_ids),
            note_count=len(matching_notes),
            locator_count=locator_count,
            last_fetched_utc=fetched[-1] if fetched else None,
            current_build_hash=build_hash,
        )

    blind_spots = sorted(
        category.value
        for category, stats in categories.items()
        if stats.note_count == 0 or stats.locator_count == 0
    )
    return CoverageReport(
        build_id=build_id,
        build_hash=build_hash,
        categories=categories,
        blind_spots=blind_spots,
    )


__all__ = [
    "CategoryCoverage",
    "CoverageReport",
    "coverage_report",
    "load_build_manifest",
]
