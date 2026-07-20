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

from debugmate.contracts import ErrorCategory
from debugmate.knowledge.build import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    KnowledgeBuild,
    _validated_manifest,
)
from debugmate.knowledge.coverage import build_path
from debugmate.knowledge.models import ProductFamily, StrictKnowledgeModel

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


class DifySyncConfig(StrictKnowledgeModel):
    """Versioned Dify indexing and retrieval settings bound to every plan."""

    chunk_size: Literal[800] = CHUNK_SIZE
    chunk_overlap: Literal[120] = CHUNK_OVERLAP
    indexing_technique: Literal["high_quality"] = "high_quality"
    retrieval_method: Literal["semantic_search"] = "semantic_search"
    top_k: Literal[3] = 3
    score_threshold_enabled: Literal[True] = True
    score_threshold: Literal[0.5] = 0.5


class SourceSyncMetadata(StrictKnowledgeModel):
    """Auditable source metadata persisted with each Dify document."""

    source_id: Identifier
    title: str = Field(min_length=1)
    source_url: str = Field(pattern=r"^https://")
    source_sha256: Sha256
    product: ProductFamily
    version_scope: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    allowed_domain: str = Field(min_length=1)
    heading_patterns: list[str] = Field(min_length=1)
    error_categories: list[ErrorCategory] = Field(min_length=1)
    license_or_terms_note: str = Field(min_length=1)
    selection_reason: str = Field(min_length=1)
    retrieved_at: str = Field(pattern=r"Z$")


class RemoteDocument(StrictKnowledgeModel):
    source_id: Identifier
    content_sha256: Sha256
    document_id: Identifier
    source_metadata: SourceSyncMetadata | None = None


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
    source_metadata: SourceSyncMetadata | None = None

    @model_validator(mode="after")
    def require_action_fields(self) -> SyncItem:
        if self.action == "create":
            valid = (
                self.local_path is not None
                and self.remote_document_id is None
                and self.source_metadata is not None
            )
        elif self.action in {"update", "unchanged"}:
            valid = (
                self.local_path is not None
                and self.remote_document_id is not None
                and self.source_metadata is not None
            )
        else:
            valid = (
                self.local_path is None
                and self.remote_document_id is not None
                and self.source_metadata is None
            )
        if not valid:
            raise ValueError(f"fields are inconsistent with sync action {self.action!r}")
        return self


class SyncPlan(StrictKnowledgeModel):
    build_id: Sha256
    build_hash: Sha256
    build_path: Path
    document_count: int = Field(default=0, ge=0)
    source_manifest_hash: Sha256 = "0" * 64
    config: DifySyncConfig = DifySyncConfig()
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
            if item.source_metadata is None or item.source_metadata.source_id != item.source_id:
                raise ValueError("source metadata is not bound to the sync item")
        if self.document_count != len(self.creates) + len(self.updates) + len(self.unchanged):
            raise ValueError("document_count must match local sync documents")
        return self


class SyncExecutionResult(StrictKnowledgeModel):
    build_id: Sha256
    executed: bool
    operation_count: int = Field(ge=0)
    readback_verified: bool = False


class DifyReadbackDocument(StrictKnowledgeModel):
    source_id: Identifier
    content_sha256: Sha256
    document_id: Identifier
    source_metadata: SourceSyncMetadata


class DifyReadbackManifest(StrictKnowledgeModel):
    document_count: int = Field(ge=0)
    documents: list[DifyReadbackDocument]
    config: DifySyncConfig

    @model_validator(mode="after")
    def require_exact_count_and_unique_documents(self) -> DifyReadbackManifest:
        if self.document_count != len(self.documents):
            raise ValueError("document_count does not match readback documents")
        source_ids = [document.source_id for document in self.documents]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("readback source IDs must be unique")
        return self


@dataclass(frozen=True)
class _PreparedCreate:
    source_id: str
    text: str
    source_metadata: SourceSyncMetadata


@dataclass(frozen=True)
class _PreparedUpdate:
    source_id: str
    remote_document_id: str
    text: str
    source_metadata: SourceSyncMetadata


@dataclass(frozen=True)
class _PreparedDelete:
    remote_document_id: str


@dataclass(frozen=True)
class _PreparedSync:
    build_id: str
    creates: tuple[_PreparedCreate, ...]
    updates: tuple[_PreparedUpdate, ...]
    deletes: tuple[_PreparedDelete, ...]
    config: DifySyncConfig

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


def _source_manifest_hash(metadata_by_id: dict[str, SourceSyncMetadata]) -> str:
    return hashlib.sha256(
        json.dumps(
            [
                metadata_by_id[source_id].model_dump(mode="json")
                for source_id in sorted(metadata_by_id)
            ],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _metadata_from_source_record(source: dict[str, object]) -> SourceSyncMetadata:
    return SourceSyncMetadata.model_validate(
        {
            "source_id": source["source_id"],
            "title": source["title"],
            "source_url": source["url"],
            "source_sha256": source["sha256"],
            "product": source["product"],
            "version_scope": source["version_scope"],
            "platform": source["platform"],
            "allowed_domain": source["allowed_domain"],
            "heading_patterns": source["heading_patterns"],
            "error_categories": [
                ErrorCategory(value) for value in source["error_categories"]
            ],
            "license_or_terms_note": source["license_or_terms_note"],
            "selection_reason": source["selection_reason"],
            "retrieved_at": source["retrieved_at"],
        },
        strict=True,
    )


def create_sync_plan(
    build: KnowledgeBuild | Path,
    remote_manifest: RemoteManifest | dict[str, object],
) -> SyncPlan:
    """Compare local and remote hashes without contacting Dify."""

    path = build_path(build).absolute()
    if path.is_symlink():
        raise ValueError("knowledge build path cannot be a symlink")
    try:
        manifest = _validated_manifest(path / "manifest.json")
    except Exception as error:
        raise KnowledgeSyncError(
            f"current knowledge build manifest identity is invalid: {error}"
        ) from error
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
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        raise ValueError("knowledge build sources must be a list")
    source_metadata_by_id = {
        str(source["source_id"]): _metadata_from_source_record(source)
        for source in sources
        if isinstance(source, dict)
    }
    for note in sorted(local_notes, key=lambda value: str(value["source_id"])):
        if not isinstance(note, dict):
            raise ValueError("knowledge build note records must be objects")
        source_id = str(note["source_id"])
        if source_id in local_source_ids:
            raise ValueError("knowledge build source IDs must be unique")
        local_source_ids.add(source_id)
        content_sha256 = str(note["note_sha256"])
        source_metadata = source_metadata_by_id.get(source_id)
        if source_metadata is None:
            raise ValueError("knowledge note has no bound source metadata")
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
                    source_metadata=source_metadata,
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
                    source_metadata=source_metadata,
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
                    source_metadata=source_metadata,
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
            document_count=len(local_notes),
            source_manifest_hash=_source_manifest_hash(source_metadata_by_id),
            config=DifySyncConfig(),
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
        raise KnowledgeSyncError(
            f"current knowledge build identity is invalid or changed: {error}"
        ) from error
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
    manifest_sources = manifest.get("sources")
    if not isinstance(manifest_sources, list):
        raise KnowledgeSyncError("current knowledge build sources are invalid")
    current_source_metadata = {
        str(source["source_id"]): _metadata_from_source_record(source)
        for source in manifest_sources
        if isinstance(source, dict)
    }
    if _source_manifest_hash(current_source_metadata) != plan.source_manifest_hash:
        raise KnowledgeSyncError("source metadata changed after synchronization planning")
    local_items = (*creates_items, *updates_items, *unchanged_items)
    if {item.source_id for item in local_items} != set(note_by_source):
        raise KnowledgeSyncError("sync plan note set no longer matches the current build")

    text_by_source: dict[str, str] = {}
    for item in local_items:
        record = note_by_source[item.source_id]
        if item.source_metadata != current_source_metadata.get(item.source_id):
            raise KnowledgeSyncError(
                f"source metadata changed for {item.source_id!r}"
            )
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
        _PreparedCreate(
            item.source_id,
            text_by_source[item.source_id],
            item.source_metadata,
        )
        for item in creates_items
        if item.source_metadata is not None
    )
    updates = tuple(
        _PreparedUpdate(
            item.source_id,
            str(item.remote_document_id),
            text_by_source[item.source_id],
            item.source_metadata,
        )
        for item in updates_items
        if item.source_metadata is not None
    )
    deletes = tuple(
        _PreparedDelete(str(item.remote_document_id)) for item in deletes_items
    )
    return _PreparedSync(
        build_id=plan.build_id,
        creates=creates,
        updates=updates,
        deletes=deletes,
        config=plan.config,
    )


def _dify_document_payload(
    source_id: str,
    text: str,
    metadata: SourceSyncMetadata,
    config: DifySyncConfig,
) -> dict[str, object]:
    return {
        "name": source_id,
        "text": text,
        "indexing_technique": config.indexing_technique,
        "doc_form": "text_model",
        "doc_metadata": metadata.model_dump(mode="json"),
        "process_rule": {
            "mode": "custom",
            "rules": {
                "pre_processing_rules": [],
                "segmentation": {
                    "separator": "\n",
                    "max_tokens": config.chunk_size,
                    "chunk_overlap": config.chunk_overlap,
                },
            },
        },
        "retrieval_model": {
            "search_method": config.retrieval_method,
            "reranking_enable": False,
            "top_k": config.top_k,
            "score_threshold_enabled": config.score_threshold_enabled,
            "score_threshold": config.score_threshold,
        },
    }


def verify_remote_readback(
    plan: SyncPlan,
    readback: DifyReadbackManifest | dict[str, object],
) -> DifyReadbackManifest:
    """Verify Dify's post-sync state against the complete sealed local contract."""

    _require_sealed_plan(plan)
    remote = (
        readback
        if isinstance(readback, DifyReadbackManifest)
        else DifyReadbackManifest.model_validate(readback, strict=True)
    )
    if remote.document_count != plan.document_count:
        raise KnowledgeSyncError("remote document count does not match sync plan")
    if remote.config != plan.config:
        raise KnowledgeSyncError("remote process/retrieval configuration does not match sync plan")
    expected = {
        item.source_id: (item.content_sha256, item.source_metadata)
        for item in (*plan.creates, *plan.updates, *plan.unchanged)
    }
    actual = {
        item.source_id: (item.content_sha256, item.source_metadata)
        for item in remote.documents
    }
    if actual != expected:
        raise KnowledgeSyncError("remote source metadata or content hashes do not match sync plan")
    return remote


def execute_sync(
    plan: SyncPlan,
    *,
    client: httpx.Client,
    dataset_key: str | None = None,
    dataset_id: Identifier | None = None,
    confirm_delete: bool = False,
    dry_run: bool = True,
    readback_manifest: DifyReadbackManifest | dict[str, object] | None = None,
) -> SyncExecutionResult:
    """Execute an explicit cloud sync; dry-run is guaranteed transport-free."""

    prepared = _prepare_sync(plan)
    if dry_run:
        readback_verified = False
        if readback_manifest is not None:
            verify_remote_readback(plan, readback_manifest)
            readback_verified = True
        return SyncExecutionResult(
            build_id=prepared.build_id,
            executed=False,
            operation_count=prepared.operation_count,
            readback_verified=readback_verified,
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
            json=_dify_document_payload(
                item.source_id, item.text, item.source_metadata, prepared.config
            ),
        )
        response.raise_for_status()
    for item in prepared.updates:
        response = client.post(
            f"datasets/{dataset_id}/documents/{item.remote_document_id}/update-by-text",
            headers=headers,
            json=_dify_document_payload(
                item.source_id, item.text, item.source_metadata, prepared.config
            ),
        )
        response.raise_for_status()
    for item in prepared.deletes:
        response = client.delete(
            f"datasets/{dataset_id}/documents/{item.remote_document_id}",
            headers=headers,
        )
        response.raise_for_status()
    readback_verified = False
    if readback_manifest is not None:
        verify_remote_readback(plan, readback_manifest)
        readback_verified = True
    return SyncExecutionResult(
        build_id=prepared.build_id,
        executed=True,
        operation_count=prepared.operation_count,
        readback_verified=readback_verified,
    )


__all__ = [
    "KnowledgeSyncError",
    "DifyReadbackManifest",
    "DifySyncConfig",
    "MissingDatasetKey",
    "RemoteDocument",
    "RemoteManifest",
    "SyncConfirmationRequired",
    "SyncExecutionResult",
    "SyncItem",
    "SyncPlan",
    "SourceSyncMetadata",
    "UnsyncableBuild",
    "create_sync_plan",
    "execute_sync",
    "verify_remote_readback",
]
