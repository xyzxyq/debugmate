"""Deletion-safe Dify synchronization plans for knowledge builds."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Annotated, Literal

import httpx
from pydantic import Field, model_validator

from debugmate.knowledge.build import KnowledgeBuild
from debugmate.knowledge.coverage import build_path, load_build_manifest
from debugmate.knowledge.models import StrictKnowledgeModel

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]+$")]


class KnowledgeSyncError(RuntimeError):
    """Base error for unsafe synchronization attempts."""


class UnsyncableBuild(KnowledgeSyncError):
    """Raised when a failed or empty build is selected for synchronization."""


class SyncConfirmationRequired(KnowledgeSyncError):
    """Raised before deletes when explicit confirmation is absent."""


class MissingDatasetKey(KnowledgeSyncError):
    """Raised before real execution when the Dify dataset key is absent."""


class RemoteDocument(StrictKnowledgeModel):
    source_id: str = Field(min_length=1)
    content_sha256: Sha256
    document_id: Identifier


class RemoteManifest(StrictKnowledgeModel):
    documents: list[RemoteDocument]

    @model_validator(mode="after")
    def reject_duplicates(self) -> RemoteManifest:
        source_ids = [document.source_id for document in self.documents]
        document_ids = [document.document_id for document in self.documents]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("remote source IDs must be unique")
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("remote document IDs must be unique")
        return self


class SyncItem(StrictKnowledgeModel):
    action: Literal["create", "update", "unchanged", "delete"]
    source_id: str = Field(min_length=1)
    content_sha256: Sha256
    local_path: Path | None = None
    remote_document_id: str | None = None


class SyncPlan(StrictKnowledgeModel):
    build_id: Sha256
    build_path: Path
    creates: list[SyncItem]
    updates: list[SyncItem]
    unchanged: list[SyncItem]
    deletes: list[SyncItem]


class SyncExecutionResult(StrictKnowledgeModel):
    build_id: Sha256
    executed: bool
    operation_count: int = Field(ge=0)


def _remote_manifest(value: RemoteManifest | dict[str, object]) -> RemoteManifest:
    if isinstance(value, RemoteManifest):
        return value
    return RemoteManifest.model_validate(value, strict=True)


def create_sync_plan(
    build: KnowledgeBuild | Path,
    remote_manifest: RemoteManifest | dict[str, object],
) -> SyncPlan:
    """Compare local and remote hashes without contacting Dify."""

    path = build_path(build)
    manifest = load_build_manifest(build)
    if manifest.get("status") != "ready" or manifest.get("syncable") is not True:
        raise UnsyncableBuild("only a ready, syncable knowledge build can be planned")
    remote = _remote_manifest(remote_manifest)
    remote_by_source = {document.source_id: document for document in remote.documents}
    local_notes = manifest.get("notes", [])
    if not isinstance(local_notes, list):
        raise ValueError("knowledge build notes must be a list")

    creates: list[SyncItem] = []
    updates: list[SyncItem] = []
    unchanged: list[SyncItem] = []
    local_source_ids: set[str] = set()
    for note in sorted(local_notes, key=lambda value: str(value["source_id"])):
        if not isinstance(note, dict):
            raise ValueError("knowledge build note records must be objects")
        source_id = str(note["source_id"])
        if source_id in local_source_ids:
            raise ValueError("knowledge build source IDs must be unique")
        local_source_ids.add(source_id)
        content_sha256 = str(note["note_sha256"])
        expected_relative_path = f"notes/{source_id}.md"
        if note.get("path") != expected_relative_path:
            raise ValueError("knowledge build note path is not canonical")
        local_path = path / expected_relative_path
        if (
            not local_path.is_file()
            or local_path.is_symlink()
            or hashlib.sha256(local_path.read_bytes()).hexdigest() != content_sha256
        ):
            raise ValueError(f"knowledge build note is missing or changed: {source_id}")
        existing = remote_by_source.get(source_id)
        if existing is None:
            creates.append(
                SyncItem(
                    action="create",
                    source_id=source_id,
                    content_sha256=content_sha256,
                    local_path=local_path,
                )
            )
        elif existing.content_sha256 == content_sha256:
            unchanged.append(
                SyncItem(
                    action="unchanged",
                    source_id=source_id,
                    content_sha256=content_sha256,
                    local_path=local_path,
                    remote_document_id=existing.document_id,
                )
            )
        else:
            updates.append(
                SyncItem(
                    action="update",
                    source_id=source_id,
                    content_sha256=content_sha256,
                    local_path=local_path,
                    remote_document_id=existing.document_id,
                )
            )

    deletes = [
        SyncItem(
            action="delete",
            source_id=document.source_id,
            content_sha256=document.content_sha256,
            remote_document_id=document.document_id,
        )
        for document in sorted(remote.documents, key=lambda value: value.source_id)
        if document.source_id not in local_source_ids
    ]
    return SyncPlan(
        build_id=str(manifest["build_id"]),
        build_path=path,
        creates=creates,
        updates=updates,
        unchanged=unchanged,
        deletes=deletes,
    )


def _note_text(item: SyncItem) -> str:
    if (
        item.local_path is None
        or not item.local_path.is_file()
        or item.local_path.is_symlink()
    ):
        raise KnowledgeSyncError(f"local note is missing for {item.source_id!r}")
    raw = item.local_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item.content_sha256:
        raise KnowledgeSyncError(f"local note changed after planning: {item.source_id!r}")
    return raw.decode("utf-8")


def execute_sync(
    plan: SyncPlan,
    *,
    client: httpx.Client,
    dataset_key: str | None = None,
    dataset_id: Identifier | None = None,
    confirm_delete: bool = False,
    dry_run: bool = True,
) -> SyncExecutionResult:
    """Execute an explicit cloud sync; dry-run is guaranteed transport-free."""

    operation_count = len(plan.creates) + len(plan.updates) + len(plan.deletes)
    if dry_run:
        return SyncExecutionResult(
            build_id=plan.build_id,
            executed=False,
            operation_count=operation_count,
        )
    if not dataset_key or not dataset_key.strip():
        raise MissingDatasetKey("DIFY_DATASET_API_KEY is required for real sync")
    if not dataset_id or re.fullmatch(r"[A-Za-z0-9_-]+", dataset_id) is None:
        raise KnowledgeSyncError("dataset_id must be a safe non-empty identifier")
    if plan.deletes and not confirm_delete:
        raise SyncConfirmationRequired(
            "remote deletions require explicit confirm_delete=True"
        )

    headers = {"Authorization": f"Bearer {dataset_key}"}
    for item in plan.creates:
        response = client.post(
            f"datasets/{dataset_id}/document/create-by-text",
            headers=headers,
            json={"name": item.source_id, "text": _note_text(item)},
        )
        response.raise_for_status()
    for item in plan.updates:
        response = client.post(
            f"datasets/{dataset_id}/documents/{item.remote_document_id}/update-by-text",
            headers=headers,
            json={"name": item.source_id, "text": _note_text(item)},
        )
        response.raise_for_status()
    for item in plan.deletes:
        response = client.delete(
            f"datasets/{dataset_id}/documents/{item.remote_document_id}",
            headers=headers,
        )
        response.raise_for_status()
    return SyncExecutionResult(
        build_id=plan.build_id,
        executed=True,
        operation_count=operation_count,
    )


__all__ = [
    "KnowledgeSyncError",
    "MissingDatasetKey",
    "RemoteDocument",
    "RemoteManifest",
    "SyncConfirmationRequired",
    "SyncExecutionResult",
    "SyncItem",
    "SyncPlan",
    "UnsyncableBuild",
    "create_sync_plan",
    "execute_sync",
]
