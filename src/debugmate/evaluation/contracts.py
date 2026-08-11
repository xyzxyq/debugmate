"""Strict, safe contracts for Phase 09 current-evidence evaluation."""

from __future__ import annotations

import re
import stat
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from debugmate.cloud.contracts import ExecutionBackend, ExecutionBackendValue
from debugmate.hashing import sha256_file
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.contracts import StrictFrozenModel

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SHA256_PATTERN = r"^[0-9a-f]{64}$"
Sha256 = Annotated[str, Field(pattern=SHA256_PATTERN)]

_ALLOWED_REFERENCE_ROOTS = (
    ".planning/phases/08-dify-unified-live-chain/",
    "evidence/dify-live/phase8/",
    "fixtures/replay/",
    "tests/fixtures/diagnosis/",
    "tests/results/",
    "prompts/",
    "platform/dify/",
)
_FORBIDDEN_REFERENCE_MARKERS = {
    "approval",
    "approvals",
    "raw",
    "provider",
    "providers",
    "course-v0.1",
    "deliverables",
}
_FROZEN_SUFFIXES = {".mp4", ".pptx", ".srt"}


class EvaluationPath(StrictFrozenModel):
    """A safe, current repository-relative reference without any raw payload."""

    path: str = Field(min_length=1, max_length=256)

    @field_validator("path")
    @classmethod
    def normalized_allowed_relative_path(cls, value: str) -> str:
        parsed = PurePosixPath(value)
        lower_parts = tuple(part.lower() for part in parsed.parts)
        if (
            "\\" in value
            or parsed.is_absolute()
            or re.match(r"^[A-Za-z]:", value)
            or any(part in {"", ".", ".."} for part in parsed.parts)
            or parsed.as_posix() != value
            or not value.startswith(_ALLOWED_REFERENCE_ROOTS)
            or any(
                marker in part for marker in _FORBIDDEN_REFERENCE_MARKERS for part in lower_parts
            )
            or parsed.suffix.lower() in _FROZEN_SUFFIXES
        ):
            raise ValueError("evaluation path is not an allowlisted current repository path")
        return value

    def resolve(self, repository_root: Path = PROJECT_ROOT) -> Path:
        root = repository_root.resolve()
        candidate = (root / self.path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ValueError("evaluation path escapes repository root") from error
        return candidate

    def is_regular_file(self, repository_root: Path = PROJECT_ROOT) -> bool:
        try:
            candidate = self.resolve(repository_root)
            if candidate.is_symlink() or not candidate.is_file():
                return False
            metadata = candidate.stat(follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                return False
            return not bool(getattr(metadata, "st_file_attributes", 0) & 0x400)
        except OSError:
            return False


class HashBoundRepositoryReference(StrictFrozenModel):
    """A repository file reference that can be re-verified by SHA-256."""

    path: EvaluationPath
    sha256: Sha256

    def is_verified(self, repository_root: Path = PROJECT_ROOT) -> bool:
        if not self.path.is_regular_file(repository_root):
            return False
        try:
            return sha256_file(self.path.resolve(repository_root)) == self.sha256
        except OSError:
            return False


class CaseTerminalStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    INSUFFICIENT_DATA = "insufficient_data"
    FAILED = "failed"


class CaseProvenance(StrEnum):
    REAL_LIVE = "real_live"
    EXPLICIT_REPLAY = "explicit_replay"
    LOCAL_FALLBACK = "local_fallback"


class CoverageTag(StrEnum):
    LIVE_SUCCESS = "live_success"
    INSUFFICIENT_DATA = "insufficient_data"
    LONG_CONTENT = "long_content"
    PRIVACY = "privacy"
    FALLBACK_OR_FAILURE = "fallback_or_failure"


class EvaluationAvailability(StrictFrozenModel):
    """Declared result availability, including the partial archive but never raw bytes."""

    report: bool = False
    card: bool = False
    recap_text: bool = False
    audio: bool = False
    bundle: bool = False

    def any(self) -> bool:
        return any((self.report, self.card, self.recap_text, self.audio, self.bundle))


class PrivacySummary(StrictFrozenModel):
    status: Literal["pass", "blocked"]
    safe_scan_sha256: Sha256
    finding_count: int = Field(ge=0, le=64)

    @model_validator(mode="after")
    def truthful_privacy_status(self) -> PrivacySummary:
        if self.status == "pass" and self.finding_count:
            raise ValueError("privacy pass cannot carry findings")
        return self


class CitationSummary(StrictFrozenModel):
    status: Literal["verified", "not_applicable", "blocked"]
    count: int = Field(ge=0, le=16)

    @model_validator(mode="after")
    def truthful_citation_status(self) -> CitationSummary:
        if self.status == "verified" and not self.count:
            raise ValueError("verified citations require at least one citation")
        if self.status != "verified" and self.count:
            raise ValueError("unverified citations cannot carry a count")
        return self


class Phase8SourceEvidence(StrictFrozenModel):
    """The exact current Phase 08 acceptance source, never historical evidence."""

    acceptance_plan: HashBoundRepositoryReference
    summary_path: EvaluationPath
    summary_sha256: Sha256 | None = None
    manifest_path: EvaluationPath
    manifest_sha256: Sha256 | None = None

    @model_validator(mode="after")
    def formal_paths_are_exact(self) -> Phase8SourceEvidence:
        if self.acceptance_plan.path.path != (
            ".planning/phases/08-dify-unified-live-chain/08-07-PLAN.md"
        ):
            raise ValueError("Phase 08 source must bind the formal acceptance plan")
        if self.summary_path.path != ".planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md":
            raise ValueError("Phase 08 source must bind the formal acceptance summary")
        if self.manifest_path.path != "evidence/dify-live/phase8/manifest.json":
            raise ValueError("Phase 08 source must bind the formal live manifest")
        if (self.summary_sha256 is None) != (self.manifest_sha256 is None):
            raise ValueError("Phase 08 summary and manifest hashes must be present together")
        return self

    def is_current_valid(self, repository_root: Path = PROJECT_ROOT) -> bool:
        if self.summary_sha256 is None or self.manifest_sha256 is None:
            return False
        if not self.acceptance_plan.is_verified(repository_root):
            return False
        paths = (
            (self.summary_path, self.summary_sha256),
            (self.manifest_path, self.manifest_sha256),
        )
        for path, expected_hash in paths:
            if not path.is_regular_file(repository_root):
                return False
            try:
                if sha256_file(path.resolve(repository_root)) != expected_hash:
                    return False
            except OSError:
                return False
        return True


class CaseEvaluation(StrictFrozenModel):
    """One bounded representative-case declaration and its honest current state."""

    case_id: str = Field(
        pattern=r"^P9-C0[1-4]-(?:live-private|insufficient|long-replay|fallback-failure)$"
    )
    coverage: tuple[CoverageTag, ...] = Field(min_length=1, max_length=5)
    source_path: EvaluationPath
    source_sha256: Sha256
    mode: Literal["live", "replay"]
    execution_backend: ExecutionBackendValue
    provenance: CaseProvenance
    expected_status: CaseTerminalStatus
    actual_status: CaseTerminalStatus
    availability: EvaluationAvailability
    privacy: PrivacySummary
    citations: CitationSummary
    limitation: str = Field(min_length=1, max_length=1_000)
    retry_scope: Literal["none", "audio"] = "none"
    phase8_source: Phase8SourceEvidence | None = None

    @field_validator("coverage")
    @classmethod
    def unique_coverage(cls, value: tuple[CoverageTag, ...]) -> tuple[CoverageTag, ...]:
        if len(value) != len(set(value)):
            raise ValueError("coverage tags must be unique")
        return value

    @field_validator("limitation")
    @classmethod
    def safe_limited_text(cls, value: str) -> str:
        assert_export_safe(value)
        return value

    @model_validator(mode="after")
    def terminal_state_is_truthful(self) -> CaseEvaluation:
        if self.case_id == "P9-C01-live-private":
            if (
                self.mode != "live"
                or self.execution_backend is not ExecutionBackend.DIFY
                or self.provenance is not CaseProvenance.REAL_LIVE
                or self.expected_status is not CaseTerminalStatus.COMPLETED
                or {CoverageTag.LIVE_SUCCESS, CoverageTag.PRIVACY} - set(self.coverage)
                or self.phase8_source is None
            ):
                raise ValueError("P9-C01 must remain a Dify live source bound to Phase 08")
            if (
                self.actual_status is CaseTerminalStatus.COMPLETED
                and not self.can_claim_live_success()
            ):
                raise ValueError(
                    "P9-C01 cannot claim live success without current Phase 08 evidence"
                )
        elif self.phase8_source is not None:
            raise ValueError("only P9-C01 may reference Phase 08 formal evidence")

        if self.case_id == "P9-C02-insufficient" and (
            self.expected_status is not CaseTerminalStatus.INSUFFICIENT_DATA
            or self.actual_status is not CaseTerminalStatus.INSUFFICIENT_DATA
            or self.availability.any()
            or self.citations.status != "not_applicable"
        ):
            raise ValueError("insufficient-information rows cannot claim diagnosis artifacts")
        if self.case_id == "P9-C03-long-replay" and (
            self.mode != "replay"
            or self.execution_backend is not ExecutionBackend.REPLAY
            or self.provenance is not CaseProvenance.EXPLICIT_REPLAY
            or CoverageTag.LONG_CONTENT not in self.coverage
        ):
            raise ValueError("P9-C03 must remain an explicit replay long-content case")
        if self.case_id == "P9-C04-fallback-failure":
            expected = EvaluationAvailability(
                report=True, card=True, recap_text=True, audio=False, bundle=True
            )
            if (
                self.mode != "live"
                or self.execution_backend is not ExecutionBackend.LOCAL_FALLBACK
                or self.provenance is not CaseProvenance.LOCAL_FALLBACK
                or self.expected_status is not CaseTerminalStatus.PARTIAL
                or self.actual_status is not CaseTerminalStatus.PARTIAL
                or self.availability != expected
                or self.retry_scope != "audio"
                or CoverageTag.FALLBACK_OR_FAILURE not in self.coverage
            ):
                raise ValueError("P9-C04 must preserve the established audio-partial contract")
        return self

    def can_claim_live_success(self, repository_root: Path = PROJECT_ROOT) -> bool:
        return (
            self.case_id == "P9-C01-live-private"
            and self.actual_status is CaseTerminalStatus.COMPLETED
            and self.phase8_source is not None
            and self.phase8_source.is_current_valid(repository_root)
        )


class CaseRegistry(StrictFrozenModel):
    registry_version: Literal["phase9-evaluation-1.0"]
    cases: tuple[CaseEvaluation, ...] = Field(min_length=3, max_length=5)

    @model_validator(mode="after")
    def exact_locked_matrix(self) -> CaseRegistry:
        required_ids = (
            "P9-C01-live-private",
            "P9-C02-insufficient",
            "P9-C03-long-replay",
            "P9-C04-fallback-failure",
        )
        case_ids = tuple(case.case_id for case in self.cases)
        if case_ids != required_ids:
            raise ValueError("Phase 09 registry must contain the exact four locked cases in order")
        if self.coverage_tags != {
            CoverageTag.LIVE_SUCCESS,
            CoverageTag.INSUFFICIENT_DATA,
            CoverageTag.LONG_CONTENT,
            CoverageTag.PRIVACY,
            CoverageTag.FALLBACK_OR_FAILURE,
        }:
            raise ValueError("Phase 09 registry must cover the exact locked tag set")
        return self

    @property
    def coverage_tags(self) -> set[CoverageTag]:
        return {tag for case in self.cases for tag in case.coverage}

    def case_for(self, case_id: str) -> CaseEvaluation:
        for case in self.cases:
            if case.case_id == case_id:
                return case
        raise KeyError(case_id)


class Phase10SourceManifest(StrictFrozenModel):
    """A bounded, claim-safe input set for later media work; it creates no media."""

    manifest_version: Literal["phase10-source-1.0"] = "phase10-source-1.0"
    cases: tuple[CaseEvaluation, ...] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def only_eligible_case_sources(self) -> Phase10SourceManifest:
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("Phase 10 source cases must be unique")
        if any(
            case.actual_status not in {CaseTerminalStatus.COMPLETED, CaseTerminalStatus.PARTIAL}
            for case in self.cases
        ):
            raise ValueError("Phase 10 source manifest cannot include blocked or insufficient rows")
        return self


class PromptProvenance(StrEnum):
    GENERATED_LIVE = "generated_live"
    VERIFIED_CONTRACT = "verified_contract"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class PromptComparison(StrictFrozenModel):
    """Placeholder public seam extended with full V1-V4 contracts in Task 2."""

    comparison_version: Literal["phase9-prompt-comparison-1.0"]
