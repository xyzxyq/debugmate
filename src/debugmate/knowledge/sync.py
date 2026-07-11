"""Deletion-safe Dify synchronization plans for knowledge builds."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import httpx
from pydantic import Field, PrivateAttr, model_validator

from debugmate.knowledge.build import KnowledgeBuild, _validated_manifest
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
    source_id: Identifier
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
    source_id: Identifier
    content_sha256: Sha256
    local_path: Path | None = None
    remote_document_id: Identifier | None = None

    @model_validator(mode="after")
    def require_action_fields(self) -> SyncItem:
        if self.action == "create":
            valid = self.local_path is not None and self.remote_document_id is None
        elif self.action in {"update", "unchanged"}:
            valid = self.local_path is not None and self.remote_document_id is not None
        else:
            valid = self.local_path is None and self.remote_document_id is not None
        if not valid:
            raise ValueError(f"fields are inconsistent with sync action {self.action!r}")
        return self


class SyncPlan(StrictKnowledgeModel):
    build_id: Sha256
    build_hash: Sha256
    build_path: Path
    creates: list[SyncItem]
    updates: list[SyncItem]
    unchanged: list[SyncItem]
    deletes: list[SyncItem]
    _integrity_sha256: str | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def require_self_consistent_operations(self) -> SyncPlan:
        if not self.build_path.is_absolute():
            raise ValueError("build_path must be absolute")
        if self.build_path.name != self.build_id:
            raise ValueError("build_path must end with build_id")
        groups = {
            "create": self.creates,
            "update": self.updates,
            "unchanged": self.unchanged,
            "delete": self.deletes,
        }
        all_items: list[SyncItem] = []
        for expected_action, items in groups.items():
            if any(item.action != expected_action for item in items):
                raise ValueError(f"{expected_action} list contains a different action")
            source_ids = [item.source_id for item in items]
            if source_ids != sorted(source_ids):
                raise ValueError(f"{expected_action} list must be sorted by source_id")
            all_items.extend(items)
        source_ids = [item.source_id for item in all_items]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("sync plan source IDs must be unique across actions")
        remote_ids = [
            item.remote_document_id
            for item in all_items
            if item.remote_document_id is not None
        ]
        if len(remote_ids) != len(set(remote_ids)):
            raise ValueError("sync plan remote document IDs must be unique")
        for item in (*self.creates, *self.updates, *self.unchanged):
            expected_path = self.build_path / "notes" / f"{item.source_id}.md"
            if item.local_path != expected_path:
                raise ValueError("local note path is not bound to build_path")
        return self


class SyncExecutionResult(StrictKnowledgeModel):
    build_id: Sha256
    executed: bool
    operation_count: int = Field(ge=0)


@dataclass(frozen=True)
class _PreparedCreate:
    source_id: str
    text: str


@dataclass(frozen=True)
class _PreparedUpdate:
    source_id: str
    remote_document_id: str
    text: str


@dataclass(frozen=True)
class _PreparedDelete:
    remote_document_id: str


@dataclass(frozen=True)
class _PreparedSync:
    build_id: str
    creates: tuple[_PreparedCreate, ...]
    updates: tuple[_PreparedUpdate, ...]
    deletes: tuple[_PreparedDelete, ...]

    @property
    def operation_count(self) -> int:
        return len(self.creates) + len(self.updates) + len(self.deletes)


def _plan_digest(plan: SyncPlan) -> str:
    payload = json.dumps(
        plan.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _seal_plan(plan: SyncPlan) -> SyncPlan:
    plan._integrity_sha256 = _plan_digest(plan)
    return plan


def _require_sealed_plan(plan: SyncPlan) -> None:
    if plan._integrity_sha256 is None or plan._integrity_sha256 != _plan_digest(plan):
        raise KnowledgeSyncError(
            "sync plan was not created by create_sync_plan or was changed afterwards"
        )
    try:
        SyncPlan.model_validate(plan.model_dump(mode="python"), strict=True)
    except Exception as error:
        raise KnowledgeSyncError("sync plan is structurally invalid") from error


def _remote_manifest(value: RemoteManifest | dict[str, object]) -> RemoteManifest:
    if isinstance(value, RemoteManifest):
        return value
    return RemoteManifest.model_validate(value, strict=True)


def create_sync_plan(
    build: KnowledgeBuild | Path,
    remote_manifest: RemoteManifest | dict[str, object],
) -> SyncPlan:
    """Compare local and remote hashes without contacting Dify."""

    path = build_path(build).absolute()
    if path.is_symlink():
        raise ValueError("knowledge build path cannot be a symlink")
    manifest = load_build_manifest(path)
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
    return _seal_plan(
        SyncPlan(
            build_id=str(manifest["build_id"]),
            build_hash=str(manifest["content_hash"]),
            build_path=path,
            creates=creates,
            updates=updates,
            unchanged=unchanged,
            deletes=deletes,
        )
    )


def _prepare_sync(plan: SyncPlan) -> _PreparedSync:
    """Validate the complete plan/build and snapshot all writes before HTTP."""

    _require_sealed_plan(plan)
    creates_items = tuple(plan.creates)
    updates_items = tuple(plan.updates)
    unchanged_items = tuple(plan.unchanged)
    deletes_items = tuple(plan.deletes)
    _require_sealed_plan(plan)
    build_path_value = plan.build_path
    notes_path = build_path_value / "notes"
    if (
        not build_path_value.is_dir()
        or build_path_value.is_symlink()
        or not notes_path.is_dir()
        or notes_path.is_symlink()
    ):
        raise KnowledgeSyncError("sync plan build path is missing or unsafe")
    try:
        build_root = build_path_value.resolve(strict=True)
        notes_root = notes_path.resolve(strict=True)
    except OSError as error:
        raise KnowledgeSyncError("sync plan build path cannot be resolved") from error
    if notes_root.parent != build_root:
        raise KnowledgeSyncError("knowledge notes directory escapes the build path")

    manifest_path = build_path_value / "manifest.json"
    try:
        manifest_before = manifest_path.read_bytes()
        manifest = _validated_manifest(manifest_path)
    except Exception as error:
        raise KnowledgeSyncError("current knowledge build manifest is invalid") from error
    if (
        manifest.get("status") != "ready"
        or manifest.get("syncable") is not True
        or manifest.get("build_id") != plan.build_id
        or manifest.get("content_hash") != plan.build_hash
    ):
        raise KnowledgeSyncError("sync plan no longer matches the current build identity")

    manifest_notes = manifest.get("notes")
    if not isinstance(manifest_notes, list):
        raise KnowledgeSyncError("current knowledge build notes are invalid")
    note_by_source = {
        str(record["source_id"]): record
        for record in manifest_notes
        if isinstance(record, dict)
    }
    local_items = (*creates_items, *updates_items, *unchanged_items)
    if {item.source_id for item in local_items} != set(note_by_source):
        raise KnowledgeSyncError("sync plan note set no longer matches the current build")

    text_by_source: dict[str, str] = {}
    for item in local_items:
        record = note_by_source[item.source_id]
        expected_path = notes_path / f"{item.source_id}.md"
        if (
            record.get("path") != f"notes/{item.source_id}.md"
            or record.get("note_sha256") != item.content_sha256
            or item.local_path != expected_path
            or item.local_path is None
            or not item.local_path.is_file()
            or item.local_path.is_symlink()
        ):
            raise KnowledgeSyncError(
                f"sync plan note binding changed for {item.source_id!r}"
            )
        try:
            resolved_note = item.local_path.resolve(strict=True)
        except OSError as error:
            raise KnowledgeSyncError(
                f"local note cannot be resolved for {item.source_id!r}"
            ) from error
        if resolved_note.parent != notes_root:
            raise KnowledgeSyncError(f"local note escapes build path: {item.source_id!r}")
        raw = item.local_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item.content_sha256:
            raise KnowledgeSyncError(
                f"local note changed after planning: {item.source_id!r}"
            )
        try:
            text_by_source[item.source_id] = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise KnowledgeSyncError(
                f"local note is not UTF-8: {item.source_id!r}"
            ) from error

    if (
        manifest_path.read_bytes() != manifest_before
        or build_path_value.is_symlink()
        or notes_path.is_symlink()
    ):
        raise KnowledgeSyncError("knowledge build changed while preparing synchronization")
    _require_sealed_plan(plan)

    creates = tuple(
        _PreparedCreate(item.source_id, text_by_source[item.source_id])
        for item in creates_items
    )
    updates = tuple(
        _PreparedUpdate(
            item.source_id,
            str(item.remote_document_id),
            text_by_source[item.source_id],
        )
        for item in updates_items
    )
    deletes = tuple(
        _PreparedDelete(str(item.remote_document_id)) for item in deletes_items
    )
    return _PreparedSync(
        build_id=plan.build_id,
        creates=creates,
        updates=updates,
        deletes=deletes,
    )


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

    prepared = _prepare_sync(plan)
    if dry_run:
        return SyncExecutionResult(
            build_id=prepared.build_id,
            executed=False,
            operation_count=prepared.operation_count,
        )
    if not dataset_key or not dataset_key.strip():
        raise MissingDatasetKey("DIFY_DATASET_API_KEY is required for real sync")
    if not dataset_id or re.fullmatch(r"[A-Za-z0-9_-]+", dataset_id) is None:
        raise KnowledgeSyncError("dataset_id must be a safe non-empty identifier")
    if prepared.deletes and not confirm_delete:
        raise SyncConfirmationRequired(
            "remote deletions require explicit confirm_delete=True"
        )

    headers = {"Authorization": f"Bearer {dataset_key}"}
    for item in prepared.creates:
        response = client.post(
            f"datasets/{dataset_id}/document/create-by-text",
            headers=headers,
            json={"name": item.source_id, "text": item.text},
        )
        response.raise_for_status()
    for item in prepared.updates:
        response = client.post(
            f"datasets/{dataset_id}/documents/{item.remote_document_id}/update-by-text",
            headers=headers,
            json={"name": item.source_id, "text": item.text},
        )
        response.raise_for_status()
    for item in prepared.deletes:
        response = client.delete(
            f"datasets/{dataset_id}/documents/{item.remote_document_id}",
            headers=headers,
        )
        response.raise_for_status()
    return SyncExecutionResult(
        build_id=prepared.build_id,
        executed=True,
        operation_count=prepared.operation_count,
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
