"""Fail-closed loader for completed Phase 3 diagnosis sources."""

from __future__ import annotations

import os
import threading
import warnings
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field

from debugmate.cloud.contracts import ExecutionBackendValue
from debugmate.contracts import DiagnosisRecord
from debugmate.diagnosis.workflow import (
    DiagnosisRunOutcome,
    WorkflowStatus,
    validate_diagnosis_outcome,
)
from debugmate.evidence import RunManifest, RunStatus, verify_bundle
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.results.contracts import StrictFrozenModel

LoadErrorCode = Literal[
    "source_bundle_invalid",
    "source_outcome_invalid",
    "outcome_store_invalid",
    "diagnosis_identity_mismatch",
]


class ResultLoadError(ValueError):
    """Value-free error crossing from source storage into result/UI code."""

    def __init__(self, code: LoadErrorCode, stage: Literal["source", "store", "identity"]):
        self.code = code
        self.stage = stage
        super().__init__("result source validation failed")


class SourceManifestSummary(StrictFrozenModel):
    manifest_version: Literal["1.0.0"]
    case_id: str = Field(pattern=r"^case_[0-9a-f]{32}$")
    run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    facts_revision: int = Field(strict=True, ge=0)
    facts_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    routing_rule_version: str = Field(min_length=1)
    knowledge_build_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: Literal["1.1.0"]
    prompt_version: str = Field(min_length=1)
    workflow_version: str = Field(min_length=1)
    node_states: tuple[NodeStateEntry, ...]


class NodeStateEntry(StrictFrozenModel):
    stage: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")
    state: Literal["completed", "inherited"]


class LoadedDiagnosisSource(StrictFrozenModel):
    case_id: str = Field(pattern=r"^case_[0-9a-f]{32}$")
    source_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    diagnosis_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_backend: ExecutionBackendValue
    outcome: DiagnosisRunOutcome
    diagnosis: DiagnosisRecord
    source_manifest: SourceManifestSummary


@dataclass(frozen=True, slots=True)
class _IssuedSourceCapability:
    """Private proof that one exact source object came from the strict loader.

    The public Pydantic model is intentionally serialisable for diagnostics,
    but that makes it unsuitable as an in-process authority.  Keep the
    evidence-root binding and canonical Phase 3 snapshot outside that model so
    ``model_copy``/``model_construct`` and post-construction mutation cannot
    inherit source authority.
    """

    owner_ref: weakref.ReferenceType[LoadedDiagnosisSource]
    source_bytes: bytes
    outcome_bytes: bytes
    evidence_root: Path
    proof_sha256: str


_SOURCE_CAPABILITY_LOCK = threading.RLock()
_SOURCE_CAPABILITIES: dict[int, _IssuedSourceCapability] = {}


def _forget_issued_source(
    key: int, reference: weakref.ReferenceType[LoadedDiagnosisSource]
) -> None:
    with _SOURCE_CAPABILITY_LOCK:
        current = _SOURCE_CAPABILITIES.get(key)
        if current is not None and current.owner_ref is reference:
            _SOURCE_CAPABILITIES.pop(key, None)


def _issue_source_capability(
    source: LoadedDiagnosisSource, *, outcome: DiagnosisRunOutcome, evidence_root: Path
) -> None:
    """Register only the exact loader return object with its proof snapshot."""

    key = id(source)
    source_bytes = canonical_json_bytes(source.model_dump(mode="json"))
    outcome_bytes = canonical_json_bytes(outcome.model_dump(mode="json"))
    root = Path(evidence_root)
    reference = weakref.ref(
        source, lambda current, identity=key: _forget_issued_source(identity, current)
    )
    proof = sha256_bytes(
        canonical_json_bytes(
            {
                "source": sha256_bytes(source_bytes),
                "outcome": sha256_bytes(outcome_bytes),
                "evidence_root": str(root),
            }
        )
    )
    capability = _IssuedSourceCapability(
        owner_ref=reference,
        source_bytes=source_bytes,
        outcome_bytes=outcome_bytes,
        evidence_root=root,
        proof_sha256=proof,
    )
    with _SOURCE_CAPABILITY_LOCK:
        _SOURCE_CAPABILITIES[key] = capability


def issued_source_snapshot(
    value: object, *, reverify: bool
) -> tuple[LoadedDiagnosisSource, str]:
    """Return the exact loader-issued snapshot, optionally rechecking Phase 3.

    The caller's object must still serialise byte-for-byte to the issued
    snapshot.  This catches ``object.__setattr__`` as well as copied/rebuilt
    values, while the optional replay of :func:`load_verified_outcome` proves
    the Phase 3 bundle remains current immediately before publication.
    """

    if not isinstance(value, LoadedDiagnosisSource):
        raise ResultLoadError("source_outcome_invalid", "source")
    try:
        current_bytes = canonical_json_bytes(value.model_dump(mode="json"))
        with _SOURCE_CAPABILITY_LOCK:
            capability = _SOURCE_CAPABILITIES.get(id(value))
        if (
            capability is None
            or capability.owner_ref() is not value
            or current_bytes != capability.source_bytes
        ):
            raise ValueError("source capability")
        snapshot = LoadedDiagnosisSource.model_validate_json(capability.source_bytes, strict=True)
        if reverify:
            outcome = DiagnosisRunOutcome.model_validate_json(capability.outcome_bytes, strict=True)
            reloaded = load_verified_outcome(outcome, evidence_root=capability.evidence_root)
            if canonical_json_bytes(reloaded.model_dump(mode="json")) != capability.source_bytes:
                raise ValueError("source changed")
        return snapshot, capability.proof_sha256
    except ResultLoadError:
        raise
    except Exception:
        raise ResultLoadError("source_bundle_invalid", "source") from None


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(path.stat(follow_symlinks=False).st_file_attributes & 0x400)
    except (AttributeError, FileNotFoundError, OSError):
        return False


def _safe_directory(path: Path) -> bool:
    if not path.is_absolute() or not path.is_dir() or _is_link_or_reparse(path):
        return False
    return not _has_unsafe_ancestor(path)


def _has_unsafe_ancestor(path: Path) -> bool:
    current = path
    while current != current.parent:
        if _is_link_or_reparse(current):
            return True
        current = current.parent
    return _is_link_or_reparse(current)


def _strict_outcome(value: DiagnosisRunOutcome) -> DiagnosisRunOutcome:
    if not isinstance(value, DiagnosisRunOutcome):
        raise TypeError("outcome type is invalid")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        raw = canonical_json_bytes(value.model_dump(mode="json"))
    outcome = DiagnosisRunOutcome.model_validate_json(raw, strict=True)
    validate_diagnosis_outcome(outcome)
    return outcome


def _expected_node_states(outcome: DiagnosisRunOutcome) -> dict[str, str]:
    states = {stage: "inherited" for stage in outcome.inherited_stages}
    states.update({stage: "completed" for stage in outcome.completed_stages})
    return states


def _manifest_matches(outcome: DiagnosisRunOutcome, manifest: RunManifest) -> bool:
    return all(
        (
            manifest.status is RunStatus.PASSED,
            manifest.case_id == outcome.case_id,
            manifest.run_id == outcome.run_id,
            manifest.facts_revision == outcome.revision,
            manifest.facts_sha256 == outcome.facts_sha256,
            manifest.input_sha256 == outcome.facts_sha256,
            manifest.routing_rule_version == outcome.routing.rule_version,
            manifest.knowledge_build_id == outcome.knowledge_build_id,
            manifest.knowledge_version
            == (
                "local-rule-v1"
                if outcome.backend == "local-rule-v1"
                else outcome.knowledge_build_id
            ),
            manifest.schema_version == outcome.schema_version,
            manifest.prompt_version == outcome.prompt_version,
            manifest.workflow_version == outcome.workflow_version,
            manifest.node_states == _expected_node_states(outcome),
            manifest.generation_attempts == outcome.generation_attempts,
            manifest.transport_attempts == outcome.transport_attempts,
            manifest.source_run_id == outcome.source_run_id,
        )
    )


def load_verified_outcome(
    outcome: DiagnosisRunOutcome, *, evidence_root: Path
) -> LoadedDiagnosisSource:
    """Load one completed outcome only after strict source and identity verification."""

    try:
        strict = _strict_outcome(outcome)
        if strict.status is not WorkflowStatus.COMPLETED or strict.diagnosis is None:
            raise ValueError("outcome is not completed")
    except Exception:
        outcome_error = ResultLoadError("source_outcome_invalid", "source")
    else:
        outcome_error = None
    if outcome_error is not None:
        raise outcome_error from None

    root = Path(evidence_root)
    bundle = root / strict.case_id / strict.run_id
    try:
        if not _safe_directory(root) or not _safe_directory(bundle):
            raise ValueError("unsafe source boundary")
        if bundle.resolve().relative_to(root.resolve()) != Path(strict.case_id) / strict.run_id:
            raise ValueError("source identity path mismatch")
        verification = verify_bundle(bundle)
        if not verification.ok or verification.manifest is None:
            raise ValueError("source bundle verification failed")
        manifest = verification.manifest
        if not _manifest_matches(strict, manifest):
            raise ValueError("source manifest identity mismatch")
    except Exception:
        bundle_error = ResultLoadError("source_bundle_invalid", "source")
    else:
        bundle_error = None
    if bundle_error is not None:
        raise bundle_error from None

    try:
        diagnosis = DiagnosisRecord.model_validate_json(
            (bundle / "diagnosis.json").read_bytes(), strict=True
        )
        if diagnosis != strict.diagnosis:
            raise ValueError("diagnosis differs from completed outcome")
        diagnosis_sha256 = sha256_bytes(
            canonical_json_bytes(diagnosis.model_dump(mode="json"))
        )
    except Exception:
        identity_error = ResultLoadError("diagnosis_identity_mismatch", "identity")
    else:
        identity_error = None
    if identity_error is not None:
        raise identity_error from None

    summary = SourceManifestSummary(
        manifest_version=manifest.manifest_version,
        case_id=manifest.case_id,
        run_id=manifest.run_id,
        facts_revision=manifest.facts_revision,
        facts_sha256=manifest.facts_sha256,
        routing_rule_version=manifest.routing_rule_version,
        knowledge_build_id=manifest.knowledge_build_id,
        schema_version=manifest.schema_version,
        prompt_version=manifest.prompt_version,
        workflow_version=manifest.workflow_version,
        node_states=tuple(
            NodeStateEntry(stage=stage, state=state)
            for stage, state in sorted(manifest.node_states.items())
        ),
    )
    result = LoadedDiagnosisSource(
        case_id=strict.case_id,
        source_run_id=strict.run_id,
        diagnosis_sha256=diagnosis_sha256,
        execution_backend=strict.execution_backend,
        outcome=strict,
        diagnosis=diagnosis,
        source_manifest=summary,
    )
    _issue_source_capability(result, outcome=strict, evidence_root=root)
    return result


def atomic_replace_directory(source: Path, target: Path) -> None:
    """Small replace seam kept here so storage tests can exercise the same boundary."""

    os.replace(source, target)
