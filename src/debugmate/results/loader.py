"""Fail-closed loader for completed Phase 3 diagnosis sources."""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Literal

from pydantic import Field

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
    node_states: dict[str, str]


class LoadedDiagnosisSource(StrictFrozenModel):
    case_id: str = Field(pattern=r"^case_[0-9a-f]{32}$")
    source_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    diagnosis_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: DiagnosisRunOutcome
    diagnosis: DiagnosisRecord
    source_manifest: SourceManifestSummary


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
            manifest.knowledge_version == outcome.knowledge_build_id,
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
    except Exception as exc:
        raise ResultLoadError("source_outcome_invalid", "source") from exc

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
    except ResultLoadError:
        raise
    except Exception as exc:
        raise ResultLoadError("source_bundle_invalid", "source") from exc

    try:
        diagnosis = DiagnosisRecord.model_validate_json(
            (bundle / "diagnosis.json").read_bytes(), strict=True
        )
        if diagnosis != strict.diagnosis:
            raise ValueError("diagnosis differs from completed outcome")
        diagnosis_sha256 = sha256_bytes(
            canonical_json_bytes(diagnosis.model_dump(mode="json"))
        )
    except Exception as exc:
        raise ResultLoadError("diagnosis_identity_mismatch", "identity") from exc

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
        node_states=manifest.node_states,
    )
    return LoadedDiagnosisSource(
        case_id=strict.case_id,
        source_run_id=strict.run_id,
        diagnosis_sha256=diagnosis_sha256,
        outcome=strict,
        diagnosis=diagnosis,
        source_manifest=summary,
    )


def atomic_replace_directory(source: Path, target: Path) -> None:
    """Small replace seam kept here so storage tests can exercise the same boundary."""

    os.replace(source, target)
