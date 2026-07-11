"""Reproducible, immutable builds of curated diagnostic knowledge notes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final, Literal

import httpx
from pydantic import Field

from debugmate.contracts import ErrorCategory
from debugmate.knowledge.extractor import EXTRACTOR_VERSION, extract_sections
from debugmate.knowledge.fetcher import fetch_source
from debugmate.knowledge.models import KnowledgeSource, SourceRegistry, StrictKnowledgeModel
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


def _manifest_error(message: str) -> ImmutableBuildCollision:
    return ImmutableBuildCollision(f"existing build manifest is invalid: {message}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise _manifest_error(message)


_SOURCE_IDENTITY_FIELDS: Final = (
    "source_id",
    "title",
    "url",
    "product",
    "version_scope",
    "platform",
    "allowed_domain",
    "heading_patterns",
    "error_categories",
    "license_or_terms_note",
    "selection_reason",
    "sha256",
    "final_url",
    "status_code",
)


def _source_identity_hash(source: dict[str, object]) -> str:
    return _hash_json({field: source[field] for field in _SOURCE_IDENTITY_FIELDS})


def _build_identity(manifest: dict[str, object]) -> dict[str, object]:
    sources = manifest["sources"]
    notes = manifest["notes"]
    failures = manifest["failures"]
    assert isinstance(sources, list)
    assert isinstance(notes, list)
    assert isinstance(failures, list)
    return {
        "registry_version": manifest["registry_version"],
        "source_hashes": [
            {
                "source_id": source["source_id"],
                "sha256": _source_identity_hash(source),
            }
            for source in sources
        ],
        "note_hashes": [
            {"source_id": note["source_id"], "sha256": note["note_sha256"]}
            for note in notes
        ],
        "failed_sources": failures,
        "extractor_version": manifest["extractor_version"],
        "generator_version": manifest["generator_version"],
        "chunk_settings": manifest["chunk_settings"],
    }


def _content_identity(manifest: dict[str, object]) -> dict[str, object]:
    notes = manifest["notes"]
    assert isinstance(notes, list)
    return {
        "build_id": manifest["build_id"],
        "status": manifest["status"],
        "notes": [record["note_sha256"] for record in notes],
        "failures": manifest["failures"],
    }


def _validated_manifest(file: Path) -> dict[str, object]:
    try:
        manifest = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _manifest_error("not valid UTF-8 JSON") from error
    _require(isinstance(manifest, dict), "root must be an object")
    required = {
        "build_id",
        "content_hash",
        "registry_version",
        "status",
        "syncable",
        "extractor_version",
        "generator_version",
        "chunk_settings",
        "document_count",
        "categories",
        "sources",
        "notes",
        "failures",
    }
    _require(set(manifest) == required, "fields do not match the build contract")
    digest = re.compile(r"^[0-9a-f]{64}$")
    _require(isinstance(manifest["build_id"], str), "build_id must be text")
    _require(digest.fullmatch(manifest["build_id"]) is not None, "invalid build_id")
    _require(isinstance(manifest["content_hash"], str), "content_hash must be text")
    _require(
        digest.fullmatch(manifest["content_hash"]) is not None,
        "invalid content_hash",
    )
    _require(manifest["status"] in {"ready", "failed"}, "invalid status")
    _require(type(manifest["syncable"]) is bool, "syncable must be boolean")
    _require(
        manifest["chunk_settings"] == {"size": CHUNK_SIZE, "overlap": CHUNK_OVERLAP},
        "invalid chunk settings",
    )
    _require(isinstance(manifest["categories"], list), "categories must be a list")
    sources = manifest["sources"]
    notes = manifest["notes"]
    failures = manifest["failures"]
    _require(isinstance(sources, list), "sources must be a list")
    _require(isinstance(notes, list), "notes must be a list")
    _require(isinstance(failures, list), "failures must be a list")
    _require(
        type(manifest["document_count"]) is int
        and manifest["document_count"] == len(notes),
        "document_count does not match notes",
    )

    source_by_id: dict[str, dict[str, object]] = {}
    source_fields = {
        "source_id",
        "title",
        "url",
        "product",
        "version_scope",
        "platform",
        "allowed_domain",
        "heading_patterns",
        "error_categories",
        "license_or_terms_note",
        "selection_reason",
        "sha256",
        "final_url",
        "status_code",
        "etag",
        "last_modified",
        "retrieved_at",
    }
    for source in sources:
        _require(isinstance(source, dict), "source records must be objects")
        _require(set(source) == source_fields, "source record fields are invalid")
        source_id = source["source_id"]
        _require(isinstance(source_id, str) and bool(source_id), "invalid source_id")
        _require(source_id not in source_by_id, "duplicate source_id")
        _require(
            isinstance(source["url"], str)
            and source["url"].startswith("https://"),
            "invalid source url",
        )
        _require(
            source["final_url"] == source["url"],
            "final_url must match url",
        )
        _require(
            isinstance(source["sha256"], str)
            and digest.fullmatch(source["sha256"]) is not None,
            "invalid source sha256",
        )
        try:
            KnowledgeSource.model_validate(
                {
                    field: (
                        [ErrorCategory(value) for value in source[field]]
                        if field == "error_categories"
                        else source[field]
                    )
                    for field in KnowledgeSource.model_fields
                },
                strict=True,
            )
        except Exception as error:
            raise _manifest_error("source registry metadata is invalid") from error
        _require(source["status_code"] == 200, "invalid source status_code")
        _require(
            source["etag"] is None or isinstance(source["etag"], str),
            "invalid source etag",
        )
        _require(
            source["last_modified"] is None
            or isinstance(source["last_modified"], str),
            "invalid source last_modified",
        )
        retrieved_at = source["retrieved_at"]
        _require(
            isinstance(retrieved_at, str) and retrieved_at.endswith("Z"),
            "retrieved_at must be UTC",
        )
        try:
            parsed_retrieved_at = datetime.fromisoformat(
                retrieved_at.removesuffix("Z") + "+00:00"
            )
        except ValueError as error:
            raise _manifest_error("retrieved_at is not an ISO timestamp") from error
        _require(
            parsed_retrieved_at.utcoffset() == timedelta(0),
            "retrieved_at must be UTC",
        )
        source_by_id[source_id] = source

    seen_note_paths: set[str] = set()
    note_fields = {
        "source_id",
        "path",
        "note_sha256",
        "source_sha256",
        "categories",
        "locators",
    }
    for note in notes:
        _require(isinstance(note, dict), "note records must be objects")
        _require(set(note) == note_fields, "note record fields are invalid")
        source_id = note["source_id"]
        _require(source_id in source_by_id, "note source is absent from sources")
        expected_path = f"notes/{source_id}.md"
        _require(note["path"] == expected_path, "note path is not canonical")
        _require(expected_path not in seen_note_paths, "duplicate note path")
        seen_note_paths.add(expected_path)
        _require(
            isinstance(note["note_sha256"], str)
            and digest.fullmatch(note["note_sha256"]) is not None,
            "invalid note_sha256",
        )
        _require(
            note["source_sha256"] == source_by_id[source_id]["sha256"],
            "note source hash mismatch",
        )
        _require(isinstance(note["categories"], list), "invalid note categories")
        _require(
            isinstance(note["locators"], list)
            and bool(note["locators"])
            and all(
                isinstance(locator, str) and locator.startswith("#")
                for locator in note["locators"]
            ),
            "invalid note locators",
        )
        note_path = file.parent / expected_path
        _require(
            note_path.is_file()
            and not note_path.is_symlink()
            and hashlib.sha256(note_path.read_bytes()).hexdigest()
            == note["note_sha256"],
            "note bytes do not match note_sha256",
        )
    _require(
        manifest["build_id"] == _hash_json(_build_identity(manifest)),
        "build_id does not match source and note identities",
    )
    _require(
        manifest["content_hash"] == _hash_json(_content_identity(manifest)),
        "content_hash does not match build contents",
    )
    return manifest


def _immutable_file_hash(file: Path, relative_path: str) -> str:
    if relative_path == "manifest.json":
        manifest = _validated_manifest(file)
        for source in manifest["sources"]:
            source.pop("etag")
            source.pop("last_modified")
            source.pop("retrieved_at")
        return _hash_json(manifest)
    return hashlib.sha256(file.read_bytes()).hexdigest()


def _expected_core_files(temp_path: Path) -> dict[str, str]:
    files = [temp_path / "manifest.json", *(temp_path / "notes").glob("*.md")]
    expected: dict[str, str] = {}
    for file in sorted(files):
        relative_path = file.relative_to(temp_path).as_posix()
        expected[relative_path] = _immutable_file_hash(file, relative_path)
    return expected


def _assert_same_immutable_build(destination: Path, expected: dict[str, str]) -> None:
    notes_path = destination / "notes"
    if not notes_path.is_dir() or notes_path.is_symlink():
        raise ImmutableBuildCollision(
            f"existing build {destination.name} has no regular notes directory"
        )
    expected_note_paths = set(expected) - {"manifest.json"}
    actual_note_paths: set[str] = set()
    for entry in notes_path.rglob("*"):
        relative_path = entry.relative_to(destination).as_posix()
        if entry.is_dir() or entry.is_symlink() or not entry.is_file():
            raise ImmutableBuildCollision(
                f"existing build {destination.name} has unmanifested notes entry {relative_path}"
            )
        actual_note_paths.add(relative_path)
    if actual_note_paths != expected_note_paths:
        raise ImmutableBuildCollision(
            f"existing build {destination.name} notes do not match the manifest"
        )

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
                    **source.model_dump(mode="json"),
                    "sha256": fetched.sha256,
                    "source_id": source.source_id,
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
    manifest = {
        "build_id": "0" * 64,
        "content_hash": "0" * 64,
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
    build_id = _hash_json(_build_identity(manifest))
    manifest["build_id"] = build_id
    content_hash = _hash_json(_content_identity(manifest))
    manifest["content_hash"] = content_hash

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
