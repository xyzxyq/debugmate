"""Deterministic hashing and safe artifact-path helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class UnsafeArtifactPath(ValueError):
    """Raised when an artifact path could escape its evidence root."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically without escaping Unicode."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_artifact_path(root: Path, relative_path: Path) -> Path:
    """Resolve a relative artifact path and prove it remains under root."""

    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise UnsafeArtifactPath("artifact path must be relative and contain no parent traversal")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative_path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as error:
        raise UnsafeArtifactPath("artifact path escapes the evidence root") from error
    return candidate


def artifact_metadata(root: Path, path: Path, mime_type: str) -> dict[str, object]:
    """Return portable metadata for one existing artifact under root."""

    candidate = resolve_artifact_path(root, path)
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return {
        "path": path.as_posix(),
        "mime_type": mime_type,
        "bytes": candidate.stat().st_size,
        "sha256": sha256_file(candidate),
    }
