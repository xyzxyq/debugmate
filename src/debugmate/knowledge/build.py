"""Reproducible, immutable builds of curated diagnostic knowledge notes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Final, Literal

import httpx
from pydantic import Field

from debugmate.contracts import ErrorCategory
from debugmate.knowledge.extractor import EXTRACTOR_VERSION, extract_sections
from debugmate.knowledge.fetcher import fetch_source
from debugmate.knowledge.models import SourceRegistry, StrictKnowledgeModel
from debugmate.knowledge.note_builder import (
    NOTE_GENERATOR_VERSION,
    DiagnosticNote,
    NoteSummarizer,
    build_note,
)

CHUNK_SIZE: Final = 800
CHUNK_OVERLAP: Final = 120


class KnowledgeBuildError(RuntimeError):
    """Base error for an unsafe or inconsistent build operation."""


class ImmutableBuildCollision(KnowledgeBuildError):
    """An existing build ID contains bytes that do not match this build."""


class KnowledgeBuild(StrictKnowledgeModel):
    """Validated result returned after a build is atomically published."""

    build_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    path: Path
    status: Literal["ready", "failed"]
    syncable: bool
    notes: list[DiagnosticNote]
    failures: list[dict[str, str]]


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _hash_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _failure(source_id: str, error: Exception) -> dict[str, str]:
    return {
        "source_id": source_id,
        "error_type": type(error).__name__,
        "message": str(error),
    }


def _immutable_file_hash(file: Path, relative_path: str) -> str:
    if relative_path == "manifest.json":
        try:
            manifest = json.loads(file.read_text(encoding="utf-8"))
            for source in manifest.get("sources", []):
                source.pop("retrieved_at", None)
            return _hash_json(manifest)
        except (json.JSONDecodeError, AttributeError, TypeError) as error:
            raise ImmutableBuildCollision("build manifest is not valid JSON") from error
    return hashlib.sha256(file.read_bytes()).hexdigest()


def _expected_core_files(temp_path: Path) -> dict[str, str]:
    files = [temp_path / "manifest.json", *(temp_path / "notes").glob("*.md")]
    expected: dict[str, str] = {}
    for file in sorted(files):
        relative_path = file.relative_to(temp_path).as_posix()
        expected[relative_path] = _immutable_file_hash(file, relative_path)
    return expected


def _assert_same_immutable_build(destination: Path, expected: dict[str, str]) -> None:
    actual: dict[str, str] = {}
    for relative_path in expected:
        file = destination / relative_path
        if not file.is_file():
            raise ImmutableBuildCollision(
                f"existing build {destination.name} is missing {relative_path}"
            )
        actual[relative_path] = _immutable_file_hash(file, relative_path)
    if actual != expected:
        raise ImmutableBuildCollision(
            f"existing build {destination.name} does not match immutable content"
        )


def _publish_atomically(temp_path: Path, destination: Path) -> None:
    expected = _expected_core_files(temp_path)
    if destination.exists():
        _assert_same_immutable_build(destination, expected)
        shutil.rmtree(temp_path)
        return
    try:
        os.replace(temp_path, destination)
    except OSError:
        if destination.exists():
            _assert_same_immutable_build(destination, expected)
            shutil.rmtree(temp_path)
            return
        raise


def build_knowledge(
    registry: SourceRegistry,
    output_root: Path,
    client: httpx.Client,
    summarizer: NoteSummarizer | None = None,
) -> KnowledgeBuild:
    """Fetch, extract and atomically publish a deterministic knowledge build.

    Source failures are recorded instead of hidden. Any failure makes the build
    non-syncable, while successful sources still produce auditable short notes.
    """

    notes: list[DiagnosticNote] = []
    source_records: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for source in registry.sources:
        try:
            fetched = fetch_source(source, client)
            sections = extract_sections(source, fetched.html)
            note = build_note(source, fetched, sections, summarizer)
            notes.append(note)
            source_records.append(
                {
                    "source_id": source.source_id,
                    "source_url": source.url,
                    "source_sha256": fetched.sha256,
                    "final_url": fetched.final_url,
                    "status_code": fetched.status_code,
                    "etag": fetched.etag,
                    "last_modified": fetched.last_modified,
                    "retrieved_at": fetched.retrieved_at.isoformat().replace(
                        "+00:00", "Z"
                    ),
                }
            )
        except Exception as error:
            failures.append(_failure(source.source_id, error))

    notes.sort(key=lambda note: note.source_id)
    source_records.sort(key=lambda record: str(record["source_id"]))
    failures.sort(key=lambda failure: failure["source_id"])
    build_identity = {
        "registry_version": registry.registry_version,
        "source_hashes": [
            {
                "source_id": record["source_id"],
                "sha256": record["source_sha256"],
            }
            for record in source_records
        ],
        "note_hashes": [
            {
                "source_id": note.source_id,
                "sha256": note.content_sha256,
            }
            for note in notes
        ],
        "failed_sources": [
            {
                "source_id": failure["source_id"],
                "error_type": failure["error_type"],
                "message": failure["message"],
            }
            for failure in failures
        ],
        "extractor_version": EXTRACTOR_VERSION,
        "generator_version": NOTE_GENERATOR_VERSION,
        "chunk_settings": {"size": CHUNK_SIZE, "overlap": CHUNK_OVERLAP},
    }
    build_id = _hash_json(build_identity)
    status: Literal["ready", "failed"] = "failed" if failures else "ready"
    syncable = status == "ready" and bool(notes)
    categories = sorted(
        {
            category.value
            for note in notes
            for category in note.categories
            if isinstance(category, ErrorCategory)
        }
    )
    note_records = [
        {
            "source_id": note.source_id,
            "path": f"notes/{note.source_id}.md",
            "note_sha256": note.content_sha256,
            "source_sha256": note.source_sha256,
            "categories": [category.value for category in note.categories],
            "locators": note.locators,
        }
        for note in notes
    ]
    content_hash = _hash_json(
        {
            "build_id": build_id,
            "status": status,
            "notes": [record["note_sha256"] for record in note_records],
            "failures": failures,
        }
    )
    manifest = {
        "build_id": build_id,
        "content_hash": content_hash,
        "registry_version": registry.registry_version,
        "status": status,
        "syncable": syncable,
        "extractor_version": EXTRACTOR_VERSION,
        "generator_version": NOTE_GENERATOR_VERSION,
        "chunk_settings": {"size": CHUNK_SIZE, "overlap": CHUNK_OVERLAP},
        "document_count": len(notes),
        "categories": categories,
        "sources": source_records,
        "notes": note_records,
        "failures": failures,
    }

    output_root.mkdir(parents=True, exist_ok=True)
    temp_path = Path(tempfile.mkdtemp(prefix=".knowledge-build-", dir=output_root))
    try:
        notes_path = temp_path / "notes"
        notes_path.mkdir()
        for note in notes:
            (notes_path / f"{note.source_id}.md").write_text(
                note.markdown, encoding="utf-8", newline="\n"
            )
        (temp_path / "manifest.json").write_bytes(_canonical_json(manifest))
        destination = output_root / build_id
        _publish_atomically(temp_path, destination)
    except BaseException:
        if temp_path.exists():
            shutil.rmtree(temp_path)
        raise

    return KnowledgeBuild(
        build_id=build_id,
        content_hash=content_hash,
        path=destination,
        status=status,
        syncable=syncable,
        notes=notes,
        failures=failures,
    )


__all__ = [
    "CHUNK_OVERLAP",
    "CHUNK_SIZE",
    "ImmutableBuildCollision",
    "KnowledgeBuild",
    "KnowledgeBuildError",
    "build_knowledge",
]
