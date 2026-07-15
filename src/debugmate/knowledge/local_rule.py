"""Strict offline loading and retrieval for the committed local-rule snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, ValidationError, field_validator, model_validator

from debugmate.contracts import CommandStep, ErrorCategory, EvidenceAnchor
from debugmate.diagnosis.evidence_binding import bind_retrieval_evidence
from debugmate.diagnosis.extraction import CaseFacts, FieldId
from debugmate.diagnosis.routing import RoutingDecision
from debugmate.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from debugmate.knowledge.models import StrictKnowledgeModel
from debugmate.knowledge.retrieval import RetrievalHit, RetrievalTrace

SNAPSHOT_RELATIVE_PATH = Path("knowledge/snapshots/local-rule")
MANIFEST_NAME = "manifest.json"
PAYLOAD_NAME = "module-not-found.json"
OFFICIAL_SOURCE_URL = "https://docs.python.org/3/library/exceptions.html"
OFFICIAL_LOCATOR = "ModuleNotFoundError"

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class LocalRuleSnapshotError(ValueError):
    """Raised when the committed local-rule snapshot cannot be trusted."""


class _ManifestFile(StrictKnowledgeModel):
    file: Literal["module-not-found.json"]
    sha256: Sha256


class _SnapshotManifest(StrictKnowledgeModel):
    snapshot_version: Literal["1.0.0"]
    backend: Literal["local-rule-v1"]
    knowledge_build_id: Sha256
    files: list[_ManifestFile]

    @model_validator(mode="after")
    def require_single_payload(self) -> Self:
        if len(self.files) != 1:
            raise ValueError("local-rule manifest must track exactly one payload")
        return self


class LocalRuleMatch(StrictKnowledgeModel):
    category: Literal[ErrorCategory.DEPENDENCY_ENVIRONMENT]
    exception_type: Literal["ModuleNotFoundError"]


class LocalRuleRetrieval(StrictKnowledgeModel):
    chunk_id: Literal["python-exceptions:module-not-found-error"]
    content_summary: Annotated[str, Field(min_length=1, max_length=500)]
    source_id: Literal["python-exceptions"]
    source_url: Literal["https://docs.python.org/3/library/exceptions.html"]
    locator: Literal["ModuleNotFoundError"]
    relevance_score: Literal[1.0]

    @field_validator("content_summary")
    @classmethod
    def reject_blank_summary(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content_summary must not be blank")
        return value


class LocalRuleCommand(StrictKnowledgeModel):
    command: str
    platform: Literal["platform_agnostic"]
    impact: str
    expected_result: str
    rollback: str

    @model_validator(mode="after")
    def require_safe_inert_metadata(self) -> Self:
        CommandStep.model_validate_json(
            json.dumps(self.model_dump(mode="json"), ensure_ascii=False), strict=True
        )
        return self


class LocalRuleResponse(StrictKnowledgeModel):
    diagnosis: Annotated[str, Field(min_length=1)]
    commands: Annotated[list[LocalRuleCommand], Field(min_length=1)]

    @field_validator("diagnosis")
    @classmethod
    def reject_blank_diagnosis(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("diagnosis must not be blank")
        return value


class LocalRule(StrictKnowledgeModel):
    rule_version: Literal["module-not-found-v1"]
    match: LocalRuleMatch
    retrieval: LocalRuleRetrieval
    response: LocalRuleResponse


class LocalRuleSnapshot(StrictKnowledgeModel):
    version: Literal["local-rule-v1"]
    knowledge_build_id: Sha256
    manifest_path: Path
    payload_path: Path
    rule: LocalRule


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LocalRuleSnapshotError(f"invalid {label} JSON: {error}") from error
    if not isinstance(value, dict):
        raise LocalRuleSnapshotError(f"{label} must be a JSON object")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], *, label: str) -> None:
    if set(value) != expected:
        raise LocalRuleSnapshotError(f"{label} contains missing or unknown keys")


def _confined_path(root: Path, relative: Path, *, label: str) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise LocalRuleSnapshotError(f"{label} path escapes the local-rule snapshot")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise LocalRuleSnapshotError(f"{label} path escapes the local-rule snapshot") from error
    return candidate


def load_local_rule_snapshot(project_root: Path) -> LocalRuleSnapshot:
    """Load the one committed local-rule snapshot without network access."""

    try:
        root = project_root.resolve()
        snapshot_dir = (root / SNAPSHOT_RELATIVE_PATH).resolve()
        snapshot_dir.relative_to(root)
    except (OSError, RuntimeError, ValueError) as error:
        raise LocalRuleSnapshotError(
            "local-rule snapshot directory escapes project root"
        ) from error
    if not snapshot_dir.is_dir():
        raise LocalRuleSnapshotError("local-rule snapshot directory is missing")

    manifest_path = _confined_path(snapshot_dir, Path(MANIFEST_NAME), label="manifest")
    raw_manifest = _load_json_object(manifest_path, label="manifest")
    _require_exact_keys(
        raw_manifest,
        {"snapshot_version", "backend", "knowledge_build_id", "files"},
        label="manifest",
    )
    raw_files = raw_manifest.get("files")
    if not isinstance(raw_files, list) or len(raw_files) != 1 or not isinstance(
        raw_files[0], dict
    ):
        raise LocalRuleSnapshotError("manifest files must contain exactly one object")
    _require_exact_keys(raw_files[0], {"file", "sha256"}, label="manifest file")
    payload_file = raw_files[0].get("file")
    if not isinstance(payload_file, str):
        raise LocalRuleSnapshotError("manifest payload file must be text")
    payload_path = _confined_path(snapshot_dir, Path(payload_file), label="payload")

    unresolved_payload = snapshot_dir / payload_file
    if unresolved_payload.is_symlink():
        raise LocalRuleSnapshotError("local-rule payload must not be a symlink")
    try:
        json_paths = list(snapshot_dir.glob("*.json"))
    except OSError as error:
        raise LocalRuleSnapshotError("unable to enumerate local-rule JSON files") from error
    tracked_names = {MANIFEST_NAME, Path(payload_file).name}
    if untracked := [path for path in json_paths if path.name not in tracked_names]:
        names = sorted(path.name for path in untracked)
        raise LocalRuleSnapshotError(f"untracked local-rule JSON files: {names}")
    if not payload_path.is_file():
        raise LocalRuleSnapshotError("local-rule payload is missing")

    expected_sha256 = raw_files[0].get("sha256")
    try:
        actual_sha256 = sha256_file(payload_path)
    except OSError as error:
        raise LocalRuleSnapshotError("unable to read local-rule payload for sha256") from error
    if actual_sha256 != expected_sha256:
        raise LocalRuleSnapshotError("local-rule payload sha256 mismatch")

    raw_payload = _load_json_object(payload_path, label="payload")
    _require_exact_keys(
        raw_payload,
        {"rule_version", "match", "retrieval", "response"},
        label="payload",
    )
    try:
        manifest = _SnapshotManifest.model_validate(raw_manifest, strict=True)
        rule = LocalRule.model_validate(raw_payload, strict=True)
        RetrievalHit.require_https_source_url(rule.retrieval.source_url)
        snapshot = LocalRuleSnapshot(
            version="local-rule-v1",
            knowledge_build_id=manifest.knowledge_build_id,
            manifest_path=manifest_path,
            payload_path=payload_path,
            rule=rule,
        )
    except (ValidationError, ValueError) as error:
        raise LocalRuleSnapshotError(f"invalid local-rule snapshot: {error}") from error
    return snapshot


@dataclass(frozen=True, slots=True)
class LocalRuleRetrievalProvider:
    """Return the committed official anchor for the one supported local route."""

    snapshot: LocalRuleSnapshot

    @property
    def knowledge_build_id(self) -> str:
        return self.snapshot.knowledge_build_id

    def retrieve(
        self, facts: CaseFacts, routing: RoutingDecision
    ) -> list[EvidenceAnchor]:
        strict_facts = CaseFacts.model_validate(facts.model_dump(), strict=True)
        strict_routing = RoutingDecision.model_validate(routing.model_dump(), strict=True)
        rule = self.snapshot.rule
        if strict_routing.category is not ErrorCategory.DEPENDENCY_ENVIRONMENT:
            return []
        exception_names = {
            fact.value.rsplit(".", 1)[-1]
            for fact in strict_facts.facts
            if fact.field_id is FieldId.EXCEPTION_TYPE
        }
        if rule.match.exception_type not in exception_names:
            return []

        hit = RetrievalHit(
            chunk_id=rule.retrieval.chunk_id,
            content_summary=rule.retrieval.content_summary,
            source_id=rule.retrieval.source_id,
            source_url=rule.retrieval.source_url,
            locator=rule.retrieval.locator,
            relevance_score=rule.retrieval.relevance_score,
        )
        query_sha256 = sha256_bytes(
            canonical_json_bytes(
                {
                    "facts_sha256": strict_facts.facts_sha256,
                    "category": strict_routing.category.value,
                    "rule_version": strict_routing.rule_version,
                }
            )
        )
        trace = RetrievalTrace(
            case_id=strict_facts.case_id,
            query_sha256=query_sha256,
            knowledge_build_id=self.snapshot.knowledge_build_id,
            retrieved_at_utc=datetime.now(UTC),
            hits=[hit],
        )
        build_manifest = {
            "build_id": self.snapshot.knowledge_build_id,
            "sources": [
                {
                    "source_id": hit.source_id,
                    "url": hit.source_url,
                    "retrieved_at": "2026-07-15T00:00:00Z",
                }
            ],
            "notes": [{"source_id": hit.source_id, "locators": [hit.locator]}],
        }
        return bind_retrieval_evidence(
            trace,
            case_id=strict_facts.case_id,
            expected_build_id=self.snapshot.knowledge_build_id,
            build_manifest=build_manifest,
        )
