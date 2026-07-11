"""Atomic, tamper-evident evidence bundles for DebugMate runs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from debugmate.contracts import CapabilityStatus, CaseId
from debugmate.hashing import (
    UnsafeArtifactPath,
    artifact_metadata,
    canonical_json_bytes,
    resolve_artifact_path,
)
from debugmate.privacy.output_scan import UnsafeExport, assert_export_safe

MANIFEST_VERSION = "1.0.0"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
Sha256 = Annotated[str, Field(pattern=SHA256_PATTERN)]


class UnsafeEvidenceContent(ValueError):
    """Raised when caller-provided failure text could expose sensitive data."""


class RunStatus(StrEnum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class ArtifactEntry(EvidenceRecord):
    path: str
    mime_type: str
    bytes: Annotated[int, Field(ge=0)]
    sha256: Sha256

    @field_validator("path")
    @classmethod
    def validate_portable_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or "\\" in value
            or value.startswith("/")
            or re.match(r"^[A-Za-z]:", value)
            or ".." in path.parts
            or path.as_posix() != value
        ):
            raise ValueError("artifact path must be a normalized relative POSIX path")
        return value


class CapabilityEvidence(EvidenceRecord):
    capability_id: Annotated[str, Field(pattern=r"^C0[1-7]$")]
    status: CapabilityStatus
    evidence_path: str | None = None
    sha256: Sha256 | None = None

    @model_validator(mode="after")
    def require_evidence_for_pass(self) -> CapabilityEvidence:
        if self.status is CapabilityStatus.PASS and not (self.evidence_path and self.sha256):
            raise ValueError("passed capability requires an evidence path and SHA-256")
        if self.evidence_path is not None:
            ArtifactEntry.validate_portable_path(self.evidence_path)
        return self


class RunManifest(EvidenceRecord):
    manifest_version: Annotated[str, Field(pattern=r"^1\.0\.0$")]
    case_id: CaseId
    status: RunStatus
    created_at_utc: datetime
    completed_at_utc: datetime
    backend: str
    workflow_version: str
    prompt_version: str
    schema_version: str
    knowledge_version: str
    input_sha256: Sha256
    run_id: str
    node_states: dict[str, str]
    latency_ms: Annotated[int, Field(ge=0)]
    token_usage: dict[str, Annotated[int, Field(ge=0)]]
    estimated_cost: Annotated[float, Field(ge=0.0)]
    artifacts: list[ArtifactEntry]
    probe_capabilities: list[CapabilityEvidence]
    error_code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")] | None = None
    safe_message: str | None = None

    @model_validator(mode="after")
    def validate_manifest_state(self) -> RunManifest:
        for timestamp in (self.created_at_utc, self.completed_at_utc):
            if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp):
                raise ValueError("manifest timestamps must be UTC aware")
        if self.completed_at_utc < self.created_at_utc:
            raise ValueError("completed_at_utc cannot precede created_at_utc")
        if len({artifact.path for artifact in self.artifacts}) != len(self.artifacts):
            raise ValueError("artifact paths must be unique")
        artifact_hashes = {artifact.path: artifact.sha256 for artifact in self.artifacts}
        for capability in self.probe_capabilities:
            if capability.status is CapabilityStatus.PASS and artifact_hashes.get(
                capability.evidence_path or ""
            ) != capability.sha256:
                raise ValueError(
                    "passed capability evidence must match a manifest artifact and SHA-256"
                )
        if self.status is RunStatus.FAILED and not (self.error_code and self.safe_message):
            raise ValueError("failed manifests require an error code and safe message")
        return self


class BundleVerification(EvidenceRecord):
    ok: bool
    issues: list[str]
    manifest: RunManifest | None = None


class EvidenceBundle:
    """Build one case under a temporary sibling and publish it atomically."""

    def __init__(self, root: Path, case_id: str, temp_path: Path, final_path: Path) -> None:
        self.root = root
        self.case_id = case_id
        self.temp_path = temp_path
        self.final_path = final_path
        self._mime_types: dict[str, str] = {}
        self._created_at = datetime.now(UTC)

    @classmethod
    def begin(cls, root: Path, case_id: str) -> EvidenceBundle:
        if re.fullmatch(r"case_[0-9a-f]{32}", case_id) is None:
            raise ValueError("invalid case_id")
        root.mkdir(parents=True, exist_ok=True)
        temp_path = root / f".tmp-{case_id}"
        final_path = root / case_id
        if temp_path.exists() or final_path.exists():
            raise FileExistsError(f"evidence bundle already exists for {case_id}")
        temp_path.mkdir()
        return cls(root, case_id, temp_path, final_path)

    def write_json(self, relative_path: str | Path, value: Any) -> Path:
        _assert_safe_export(value)
        return self.write_bytes(relative_path, canonical_json_bytes(value), "application/json")

    def write_retrieval_trace(self, trace: Any) -> Path:
        """Store the bounded retrieval contract, never provider raw chunks."""

        from debugmate.knowledge.retrieval import RetrievalTrace

        if not isinstance(trace, RetrievalTrace):
            raise TypeError("trace must be a validated RetrievalTrace")
        return self.write_json("retrieval.json", trace.model_dump(mode="json"))

    def write_bytes(self, relative_path: str | Path, value: bytes, mime_type: str) -> Path:
        path = Path(relative_path)
        target = resolve_artifact_path(self.temp_path, path)
        portable = path.as_posix()
        ArtifactEntry.validate_portable_path(portable)
        if portable == "manifest.json":
            raise UnsafeArtifactPath("manifest.json is reserved and written only during finalize")
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
        self._mime_types[portable] = mime_type
        return target

    def finalize(self, manifest: RunManifest) -> Path:
        if manifest.case_id != self.case_id:
            raise ValueError("manifest case_id does not match bundle")
        if manifest.status is RunStatus.RUNNING:
            raise ValueError("a running manifest cannot be published")
        if self.final_path.exists():
            raise FileExistsError(self.final_path)

        actual_paths = {
            path.relative_to(self.temp_path).as_posix()
            for path in self.temp_path.rglob("*")
            if path.is_file()
        }
        if actual_paths != set(self._mime_types):
            raise ValueError("temporary bundle contains untracked artifacts")

        artifacts = [
            ArtifactEntry.model_validate(
                artifact_metadata(self.temp_path, Path(path), self._mime_types[path])
            )
            for path in sorted(self._mime_types)
        ]
        final_manifest = RunManifest.model_validate(
            {**manifest.model_dump(), "artifacts": artifacts}
        )
        _assert_safe_export(final_manifest.model_dump(mode="json"))
        if _unsafe_manifest_value(final_manifest.model_dump(mode="json")):
            raise UnsafeEvidenceContent("manifest contains a forbidden sensitive marker or path")
        manifest_path = self.temp_path / "manifest.json"
        manifest_path.write_bytes(
            canonical_json_bytes(final_manifest.model_dump(mode="json")) + b"\n"
        )
        self.temp_path.replace(self.final_path)
        return self.final_path

    def fail(self, error_code: str, safe_message: str) -> Path:
        if re.search(r"authorization|bearer\s|traceback|api[_ -]?key|secret", safe_message, re.I):
            raise UnsafeEvidenceContent("failure message contains a forbidden sensitive marker")
        now = datetime.now(UTC)
        manifest = RunManifest(
            manifest_version=MANIFEST_VERSION,
            case_id=self.case_id,
            status=RunStatus.FAILED,
            created_at_utc=self._created_at,
            completed_at_utc=now,
            backend="local",
            workflow_version="unknown",
            prompt_version="unknown",
            schema_version="1.0.0",
            knowledge_version="unknown",
            input_sha256="0" * 64,
            run_id=f"local:{self.case_id}",
            node_states={},
            latency_ms=max(0, int((now - self._created_at).total_seconds() * 1000)),
            token_usage={},
            estimated_cost=0.0,
            artifacts=[],
            probe_capabilities=[],
            error_code=error_code,
            safe_message=safe_message,
        )
        return self.finalize(manifest)


def verify_bundle(path: Path) -> BundleVerification:
    """Recompute every listed artifact and reject missing or unlisted files."""

    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        return BundleVerification(ok=False, issues=["manifest.json is missing"])

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return BundleVerification(ok=False, issues=["manifest.json is invalid"])

    issues: list[str] = []
    if manifest.case_id != path.name:
        issues.append("manifest case_id does not match directory")
    if manifest.status is RunStatus.RUNNING:
        issues.append("published manifest cannot have running status")

    listed = {entry.path for entry in manifest.artifacts}
    actual = {
        item.relative_to(path).as_posix()
        for item in path.rglob("*")
        if item.is_file() and item.name != "manifest.json"
    }
    for entry in manifest.artifacts:
        try:
            candidate = resolve_artifact_path(path, Path(entry.path))
        except UnsafeArtifactPath:
            issues.append(f"unsafe artifact path: {entry.path}")
            continue
        if not candidate.is_file():
            issues.append(f"missing artifact: {entry.path}")
            continue
        metadata = artifact_metadata(path, Path(entry.path), entry.mime_type)
        if metadata["bytes"] != entry.bytes:
            issues.append(f"byte count mismatch: {entry.path}")
        if metadata["sha256"] != entry.sha256:
            issues.append(f"sha256 mismatch: {entry.path}")
    for unlisted in sorted(actual - listed):
        issues.append(f"unlisted artifact: {unlisted}")

    return BundleVerification(ok=not issues, issues=issues, manifest=manifest)


def _unsafe_manifest_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(
            re.search(r"authorization|bearer\s|api[_ -]?key|secret|traceback", value, re.I)
            or re.search(r"(?:^|\s)[A-Za-z]:[\\/]", value)
            or "/Users/" in value
            or "/home/" in value
        )
    if isinstance(value, Mapping):
        return any(_unsafe_manifest_value(nested) for nested in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return any(_unsafe_manifest_value(nested) for nested in value)
    return False


def _assert_safe_export(value: Any) -> None:
    try:
        assert_export_safe(value)
    except UnsafeExport as error:
        raise UnsafeEvidenceContent(str(error)) from None
