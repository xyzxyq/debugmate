"""Fail-closed collection of current evidence for the Phase 09 ledgers.

The collector deliberately keeps only claim-safe references and fingerprints.
It never promotes raw provider payloads, paths outside the repository, or media
whose result bundle has not been reopened through the product verifier.
"""

from __future__ import annotations

import json
import re
import stat
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from debugmate.diagnosis.evidence_binding import bind_retrieval_evidence
from debugmate.diagnosis.workflow import DiagnosisRunOutcome, validate_diagnosis_outcome
from debugmate.evaluation.contracts import (
    PROJECT_ROOT,
    CaseEvaluation,
    CaseRegistry,
    CaseTerminalStatus,
    EvaluationAvailability,
    Phase8SourceEvidence,
)
from debugmate.hashing import sha256_file
from debugmate.knowledge.sync import DifyReadbackAttestation
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.contracts import StrictFrozenModel
from debugmate.results.verifier import ResultVerificationError, verify_result_bundle

_PHASE8_SUMMARY = ".planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md"
_PHASE8_MANIFEST = "evidence/dify-live/phase8/manifest.json"
_EVALUATION_ROOT = Path("evidence/evaluation/phase9")
_PHASE8_REQUIRED_ARTIFACTS = frozenset(
    {
        "knowledge-readback.json",
        "live-run.json",
        "report.md",
        "card.png",
        "recap.mp3",
        "result.zip",
    }
)


class Phase8ArtifactHash(StrictFrozenModel):
    path: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]{1,63}$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Phase8JUnitSummary(StrictFrozenModel):
    tests: int = Field(ge=1, le=10_000)
    failures: Literal[0]
    errors: Literal[0]
    skipped: Literal[0]


class Phase8FormalManifest(StrictFrozenModel):
    schema_version: Literal["phase8-formal-acceptance-1.0"]
    qa_run_id: str = Field(pattern=r"^p8qa_[0-9a-f]{32}$")
    evidence_time_utc: str = Field(
        pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    )
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    worktree_scope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    backend: Literal["dify"]
    cloud_junit: Phase8JUnitSummary
    edge_junit: Phase8JUnitSummary
    artifacts: tuple[Phase8ArtifactHash, ...] = Field(min_length=6, max_length=6)

    @model_validator(mode="after")
    def exact_inner_artifacts(self) -> Phase8FormalManifest:
        paths = [artifact.path for artifact in self.artifacts]
        if len(paths) != len(set(paths)) or set(paths) != _PHASE8_REQUIRED_ARTIFACTS:
            raise ValueError("Phase 08 formal artifact inventory is not exact")
        return self


class Phase8LiveRun(StrictFrozenModel):
    schema_version: Literal["phase8-live-run-1.0"]
    qa_run_id: str = Field(pattern=r"^p8qa_[0-9a-f]{32}$")
    backend: Literal["dify"]
    case_id: str = Field(pattern=r"^case_[0-9a-f]{32}$")
    status: Literal["completed"]
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    knowledge_build_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    facts_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retrieval_trace_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnosis_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_id: str = Field(pattern=r"^result_[0-9a-f]{32}$")
    artifact_sha256: dict[str, str]

    @model_validator(mode="after")
    def exact_output_hashes(self) -> Phase8LiveRun:
        expected = {"report.md", "card.png", "recap.mp3", "result.zip"}
        if set(self.artifact_sha256) != expected or any(
            re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in self.artifact_sha256.values()
        ):
            raise ValueError("Phase 08 live run output hashes are not exact")
        return self


class Phase8SourceValidation(StrictFrozenModel):
    """Safe result of reopening the one allowed Phase 08 formal source."""

    valid: bool
    reason: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    summary_path: Literal[_PHASE8_SUMMARY] = _PHASE8_SUMMARY
    manifest_path: Literal[_PHASE8_MANIFEST] = _PHASE8_MANIFEST


class CollectedCaseSource(StrictFrozenModel):
    """An allowlisted evaluation row with an explicit promotion decision."""

    case_id: str = Field(
        pattern=r"^P9-C0[1-4]-(?:live-private|insufficient|long-replay|fallback-failure)$"
    )
    source_path: str = Field(min_length=1, max_length=256)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    actual_status: CaseTerminalStatus
    execution_backend: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")
    provenance: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    availability: EvaluationAvailability
    privacy_status: Literal["pass", "blocked"]
    citation_status: Literal["verified", "not_applicable", "blocked"]
    citation_count: int = Field(ge=0, le=16)
    limitation: str = Field(min_length=1, max_length=1_000)
    result_bundle_path: str | None = Field(default=None, max_length=256)
    phase10_eligible: bool
    exclusion_reasons: tuple[str, ...] = Field(max_length=12)

    @model_validator(mode="after")
    def safe_and_truthful(self) -> CollectedCaseSource:
        assert_export_safe(self.model_dump(mode="json", exclude={"result_bundle_path"}))
        if self.result_bundle_path is not None and re.fullmatch(
            r"evidence/evaluation/phase9/P9-C0[1-4]-(?:live-private|insufficient|long-replay|fallback-failure)/"
            r"case_[0-9a-f]{32}/result_[0-9a-f]{32}",
            self.result_bundle_path,
        ) is None:
            raise ValueError("result bundle path is not a native staged identity")
        if self.phase10_eligible and self.exclusion_reasons:
            raise ValueError("eligible rows cannot retain exclusion reasons")
        if not self.phase10_eligible and not self.exclusion_reasons:
            raise ValueError("ineligible rows require at least one stable exclusion reason")
        if self.actual_status is CaseTerminalStatus.INSUFFICIENT_DATA and self.availability.any():
            raise ValueError("insufficient rows cannot expose result artifacts")
        return self


class Phase10SourceLedger(StrictFrozenModel):
    """The intentionally small source set that a later Phase may consume."""

    manifest_version: Literal["phase10-source-1.0"] = "phase10-source-1.0"
    cases: tuple[CollectedCaseSource, ...] = Field(default=(), max_length=4)

    @model_validator(mode="after")
    def contains_only_eligible_rows(self) -> Phase10SourceLedger:
        if any(not case.phase10_eligible for case in self.cases):
            raise ValueError("Phase 10 ledger may contain only eligible rows")
        assert_export_safe(self.model_dump(mode="json"))
        return self


def _phase8_regular_file(root: Path, name: str) -> Path:
    candidate = root / name
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root.resolve())
    metadata = candidate.stat(follow_symlinks=False)
    if (
        candidate.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or bool(getattr(metadata, "st_file_attributes", 0) & 0x400)
    ):
        raise ValueError("Phase 08 formal artifact is not a regular file")
    return candidate


def _phase8_checksums(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([a-z0-9][a-z0-9.-]{1,63})", line)
        if match is None or match.group(2) in records:
            raise ValueError("Phase 08 checksums are invalid")
        records[match.group(2)] = match.group(1)
    return records


def _validate_phase8_formal_manifest(path: Path) -> Phase8FormalManifest:
    root = path.parent.resolve()
    manifest_path = _phase8_regular_file(root, "manifest.json")
    manifest = Phase8FormalManifest.model_validate_json(manifest_path.read_bytes(), strict=True)
    artifact_hashes = {artifact.path: artifact.sha256 for artifact in manifest.artifacts}
    for name, expected_hash in artifact_hashes.items():
        if sha256_file(_phase8_regular_file(root, name)) != expected_hash:
            raise ValueError("Phase 08 formal artifact hash mismatch")

    checksums_path = _phase8_regular_file(root, "checksums.sha256")
    checksums = _phase8_checksums(checksums_path)
    expected_names = {"manifest.json", *_PHASE8_REQUIRED_ARTIFACTS}
    if set(checksums) != expected_names or any(
        sha256_file(_phase8_regular_file(root, name)) != digest
        for name, digest in checksums.items()
    ):
        raise ValueError("Phase 08 formal checksums mismatch")

    live = Phase8LiveRun.model_validate_json(
        _phase8_regular_file(root, "live-run.json").read_bytes(), strict=True
    )
    readback = DifyReadbackAttestation.model_validate_json(
        _phase8_regular_file(root, "knowledge-readback.json").read_bytes(), strict=True
    )
    if (
        live.qa_run_id != manifest.qa_run_id
        or live.knowledge_build_id != readback.knowledge_build_id
        or any(live.artifact_sha256[name] != artifact_hashes[name] for name in live.artifact_sha256)
    ):
        raise ValueError("Phase 08 formal identity binding mismatch")
    return manifest


def validate_phase8_live_source(
    source: Phase8SourceEvidence, *, repository_root: Path = PROJECT_ROOT
) -> Phase8SourceValidation:
    """Require the exact published Phase 08 receipt before a live claim is possible."""

    root = Path(repository_root).resolve()
    summary = source.summary_path.resolve(root)
    manifest = source.manifest_path.resolve(root)
    if not summary.is_file() or not manifest.is_file():
        return Phase8SourceValidation(valid=False, reason="phase8_formal_evidence_missing")
    if not source.is_current_valid(root):
        return Phase8SourceValidation(valid=False, reason="phase8_formal_hash_mismatch")

    try:
        formal = _validate_phase8_formal_manifest(manifest)
    except (OSError, UnicodeError, ValueError):
        return Phase8SourceValidation(valid=False, reason="phase8_manifest_invalid")
    if formal.backend != "dify":
        return Phase8SourceValidation(valid=False, reason="phase8_backend_mismatch")
    return Phase8SourceValidation(valid=True, reason="current_phase8_source_verified")


def _bounded_result_bundle_path(
    case: CaseEvaluation, repository_root: Path
) -> tuple[Path | None, str]:
    """Discover exactly one native product-case/result identity below the locked P9 root."""

    staging = repository_root / _EVALUATION_ROOT / case.case_id
    if not staging.is_dir() or staging.is_symlink():
        return None, "result_bundle_missing"
    candidates: list[Path] = []
    try:
        case_directories = list(staging.iterdir())
        if len(case_directories) > 8:
            return None, "result_bundle_ambiguous"
        for case_directory in case_directories:
            metadata = case_directory.stat(follow_symlinks=False)
            if (
                case_directory.is_symlink()
                or not stat.S_ISDIR(metadata.st_mode)
                or bool(getattr(metadata, "st_file_attributes", 0) & 0x400)
                or re.fullmatch(r"case_[0-9a-f]{32}", case_directory.name) is None
            ):
                continue
            result_directories = list(case_directory.iterdir())
            if len(result_directories) > 8:
                return None, "result_bundle_ambiguous"
            for result_directory in result_directories:
                result_metadata = result_directory.stat(follow_symlinks=False)
                if (
                    not result_directory.is_symlink()
                    and stat.S_ISDIR(result_metadata.st_mode)
                    and not bool(getattr(result_metadata, "st_file_attributes", 0) & 0x400)
                    and re.fullmatch(r"result_[0-9a-f]{32}", result_directory.name)
                    is not None
                ):
                    candidates.append(result_directory)
    except OSError:
        return None, "result_bundle_invalid"
    if not candidates:
        return None, "result_bundle_missing"
    if len(candidates) != 1:
        return None, "result_bundle_ambiguous"
    return candidates[0], "result_bundle_discovered"


def _result_bundle_is_valid(
    case: CaseEvaluation, repository_root: Path
) -> tuple[bool, str, str | None]:
    """Delegate all result/media/citation checks to the existing product verifier."""

    bundle_path, discovery_reason = _bounded_result_bundle_path(case, repository_root)
    if bundle_path is None:
        return False, discovery_reason, None
    relative = bundle_path.relative_to(repository_root).as_posix()
    try:
        verified = verify_result_bundle(bundle_path)
    except (OSError, ResultVerificationError, ValueError):
        return False, "result_bundle_invalid", relative

    manifest = verified.manifest
    if (
        manifest.identity.case_id != bundle_path.parent.name
        or manifest.result_id != bundle_path.name
    ):
        return False, "result_identity_mismatch", relative
    if manifest.execution_backend.value != case.execution_backend.value:
        return False, "result_backend_mismatch", relative
    if manifest.status.value != case.actual_status.value:
        return False, "result_status_mismatch", relative
    expected_availability = {
        "report": case.availability.report,
        "card": case.availability.card,
        "recap_text": case.availability.recap_text,
        "audio": case.availability.audio,
    }
    if (
        manifest.availability.model_dump(mode="json") != expected_availability
        or not case.availability.bundle
    ):
        return False, "result_availability_mismatch", relative
    return True, "result_bundle_verified", relative


def _source_file_is_current(case: CaseEvaluation, repository_root: Path) -> bool:
    path = case.source_path.resolve(repository_root)
    try:
        return (
            case.source_path.is_regular_file(repository_root)
            and sha256_file(path) == case.source_sha256
        )
    except OSError:
        return False


def _validate_staged_outcome(case: CaseEvaluation, repository_root: Path) -> str | None:
    """Reopen optional staged workflow evidence without treating it as display text."""

    outcome_path = repository_root / _EVALUATION_ROOT / case.case_id / "outcome.json"
    if not outcome_path.is_file() or outcome_path.is_symlink():
        return None
    try:
        outcome = DiagnosisRunOutcome.model_validate_json(outcome_path.read_text(encoding="utf-8"))
        validate_diagnosis_outcome(outcome)
        retrieval_path = outcome_path.with_name("retrieval.json")
        build_path = outcome_path.with_name("knowledge-build.json")
        if retrieval_path.is_file() and build_path.is_file():
            retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
            build = json.loads(build_path.read_text(encoding="utf-8"))
            bind_retrieval_evidence(
                retrieval,
                case_id=outcome.case_id,
                expected_build_id=outcome.knowledge_build_id,
                build_manifest=build,
            )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return "diagnosis_evidence_invalid"
    return None


def _base_row(
    case: CaseEvaluation,
    *,
    phase10_eligible: bool,
    exclusion_reasons: tuple[str, ...],
    result_bundle_path: str | None = None,
) -> CollectedCaseSource:
    return CollectedCaseSource(
        case_id=case.case_id,
        source_path=case.source_path.path,
        source_sha256=case.source_sha256,
        actual_status=case.actual_status,
        execution_backend=case.execution_backend.value,
        provenance=case.provenance.value,
        availability=case.availability,
        privacy_status=case.privacy.status,
        citation_status=case.citations.status,
        citation_count=case.citations.count,
        limitation=case.limitation,
        result_bundle_path=result_bundle_path,
        phase10_eligible=phase10_eligible,
        exclusion_reasons=exclusion_reasons,
    )


def collect_phase9_cases(
    registry: CaseRegistry, *, repository_root: Path = PROJECT_ROOT
) -> tuple[CollectedCaseSource, ...]:
    """Collect the locked matrix, keeping unsafe or stale cases explicitly ineligible."""

    root = Path(repository_root).resolve()
    collected: list[CollectedCaseSource] = []
    for case in registry.cases:
        if case.actual_status is CaseTerminalStatus.INSUFFICIENT_DATA:
            collected.append(
                _base_row(case, phase10_eligible=False, exclusion_reasons=("insufficient_data",))
            )
            continue
        if not _source_file_is_current(case, root):
            collected.append(
                _base_row(case, phase10_eligible=False, exclusion_reasons=("source_hash_mismatch",))
            )
            continue
        try:
            assert_export_safe(case.model_dump(mode="json"))
        except ValueError:
            collected.append(
                _base_row(case, phase10_eligible=False, exclusion_reasons=("privacy_scan_failed",))
            )
            continue
        if case.case_id == "P9-C01-live-private":
            assert case.phase8_source is not None
            phase8 = validate_phase8_live_source(case.phase8_source, repository_root=root)
            if not phase8.valid:
                collected.append(
                    _base_row(case, phase10_eligible=False, exclusion_reasons=(phase8.reason,))
                )
                continue
        if case.privacy.status != "pass":
            collected.append(
                _base_row(case, phase10_eligible=False, exclusion_reasons=("privacy_not_passed",))
            )
            continue
        if case.citations.status != "verified":
            collected.append(
                _base_row(
                    case,
                    phase10_eligible=False,
                    exclusion_reasons=("citations_not_verified",),
                )
            )
            continue
        outcome_reason = _validate_staged_outcome(case, root)
        if outcome_reason is not None:
            collected.append(
                _base_row(case, phase10_eligible=False, exclusion_reasons=(outcome_reason,))
            )
            continue
        result_valid, result_reason, result_path = _result_bundle_is_valid(case, root)
        if not result_valid:
            collected.append(
                _base_row(
                    case,
                    phase10_eligible=False,
                    exclusion_reasons=(result_reason,),
                    result_bundle_path=result_path,
                )
            )
            continue
        if case.actual_status is not CaseTerminalStatus.COMPLETED or not case.availability.audio:
            collected.append(
                _base_row(
                    case,
                    phase10_eligible=False,
                    exclusion_reasons=("media_not_available",),
                    result_bundle_path=result_path,
                )
            )
            continue
        collected.append(
            _base_row(
                case,
                phase10_eligible=True,
                exclusion_reasons=(),
                result_bundle_path=result_path,
            )
        )
    return tuple(collected)


def build_phase10_source_manifest(
    rows: tuple[CollectedCaseSource, ...],
) -> Phase10SourceLedger:
    """Reduce a complete evaluation ledger to the subset safe for a future media phase."""

    eligible = tuple(row for row in rows if row.phase10_eligible)
    return Phase10SourceLedger(cases=eligible)
