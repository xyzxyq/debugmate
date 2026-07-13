"""Strict identities and state contracts for Phase 4 results."""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from debugmate.hashing import canonical_json_bytes, sha256_bytes

Sha256 = str


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class ResultStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class ResultMode(StrEnum):
    LIVE = "live"
    REPLAY = "replay"


class GenerationProfile(StrictFrozenModel):
    profile_version: Literal["1.0.0"] = "1.0.0"
    report_contract_version: str = Field(pattern=r"^[a-z][a-z0-9._-]{2,63}$")
    card_contract_version: str = Field(pattern=r"^[a-z][a-z0-9._-]{2,63}$")
    recap_contract_version: str = Field(pattern=r"^[a-z][a-z0-9._-]{2,63}$")
    font_name: str = Field(pattern=r"^[^/\\\x00]{1,128}$")
    font_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    generation_version: str = Field(pattern=r"^gen_[0-9a-f]{32}$")

    @staticmethod
    def version_for(payload: dict[str, object]) -> str:
        return f"gen_{sha256_bytes(canonical_json_bytes(payload))[:32]}"

    @classmethod
    def create(
        cls,
        *,
        report_contract_version: str,
        card_contract_version: str,
        recap_contract_version: str,
        font_name: str,
        font_sha256: str,
    ) -> GenerationProfile:
        payload = {
            "profile_version": "1.0.0",
            "report_contract_version": report_contract_version,
            "card_contract_version": card_contract_version,
            "recap_contract_version": recap_contract_version,
            "font_name": font_name,
            "font_sha256": font_sha256,
        }
        return cls(**payload, generation_version=cls.version_for(payload))

    @model_validator(mode="after")
    def canonical_generation_version(self) -> GenerationProfile:
        payload = self.model_dump(exclude={"generation_version"}, mode="json")
        if self.generation_version != self.version_for(payload):
            raise ValueError("generation version does not match the canonical profile")
        return self


class ResolvedFont(StrictFrozenModel):
    name: str = Field(pattern=r"^[^/\\\x00]{1,128}$")
    path: Path
    sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    source: Literal["project", "windows"]

    @model_validator(mode="after")
    def absolute_non_link_path(self) -> ResolvedFont:
        if not self.path.is_absolute() or self.path.is_symlink():
            raise ValueError("resolved font path must be an absolute non-link path")
        return self


class PreparedGenerationContext(StrictFrozenModel):
    generation_profile: GenerationProfile
    resolved_font: ResolvedFont

    @model_validator(mode="after")
    def bind_profile_to_font(self) -> PreparedGenerationContext:
        if (
            self.generation_profile.font_name != self.resolved_font.name
            or self.generation_profile.font_sha256 != self.resolved_font.sha256
        ):
            raise ValueError("generation profile does not match its resolved font")
        return self


class ArtifactIdentity(StrictFrozenModel):
    case_id: str = Field(pattern=r"^case_[0-9a-f]{32}$")
    source_run_id: str = Field(pattern=r"^run_[0-9a-f]{32}$")
    diagnosis_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: Literal["1.1.0"]
    generation_version: str = Field(pattern=r"^gen_[0-9a-f]{32}$")


ArtifactKind = Literal[
    "diagnosis", "report", "card", "recap_text", "audio", "citations", "source_manifest"
]
_RESERVED_MEMBERS = {
    "result-manifest.json",
    "checksums.sha256",
    "result.zip",
    "publication.json",
}


class ArtifactRecord(StrictFrozenModel):
    kind: ArtifactKind
    path: str = Field(min_length=1, max_length=256)
    mime_type: str = Field(pattern=r"^[a-z0-9.+-]+/[a-z0-9.+-]+$")
    bytes: int = Field(strict=True, ge=0)
    sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    identity: ArtifactIdentity

    @model_validator(mode="after")
    def portable_acyclic_member(self) -> ArtifactRecord:
        value = PurePosixPath(self.path)
        if (
            value.is_absolute()
            or "\\" in self.path
            or ":" in self.path
            or any(part in {"", ".", ".."} for part in value.parts)
            or self.path in _RESERVED_MEMBERS
        ):
            raise ValueError("artifact path is not a portable business payload member")
        return self


class ArtifactAvailability(StrictFrozenModel):
    report: bool = False
    card: bool = False
    recap_text: bool = False
    audio: bool = False

    def any(self) -> bool:
        return any((self.report, self.card, self.recap_text, self.audio))

    def all(self) -> bool:
        return all((self.report, self.card, self.recap_text, self.audio))


class SafeFailure(StrictFrozenModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")
    failed_stage: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")
    retry_scope: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")


class AudioAttempt(StrictFrozenModel):
    backend: str = Field(pattern=r"^[a-z][a-z0-9_]{1,31}$")
    rate_profile: str = Field(pattern=r"^[a-z0-9_+%-]{1,31}$")
    succeeded: bool
    safe_error_code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{2,63}$")
    duration_ms: int | None = Field(default=None, strict=True, ge=0)
    sha256: Sha256 | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def result_shape(self) -> AudioAttempt:
        if self.succeeded and (self.safe_error_code or self.duration_ms is None or not self.sha256):
            raise ValueError("successful audio attempt requires only duration and hash")
        if not self.succeeded and not self.safe_error_code:
            raise ValueError("failed audio attempt requires a safe error code")
        return self


class AudioResult(StrictFrozenModel):
    identity: ArtifactIdentity
    available: bool
    backend: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{1,31}$")
    fallback_used: bool = False
    attempts: list[AudioAttempt]
    duration_ms: int | None = Field(default=None, strict=True, ge=0)
    sha256: Sha256 | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    failure: SafeFailure | None = None

    @model_validator(mode="after")
    def consistent_attempts(self) -> AudioResult:
        if self.available:
            if not (self.backend and self.duration_ms is not None and self.sha256):
                raise ValueError("available audio requires backend, duration and hash")
            if not self.attempts or not self.attempts[-1].succeeded:
                raise ValueError("available audio requires a successful final attempt")
            if self.failure is not None:
                raise ValueError("available audio cannot carry a terminal failure")
        elif self.failure is None:
            raise ValueError("unavailable audio requires a safe failure")
        if self.fallback_used and len(self.attempts) < 2:
            raise ValueError("fallback audio requires complete attempt history")
        return self


class ResultManifest(StrictFrozenModel):
    manifest_version: Literal["1.0.0"]
    result_id: str = Field(pattern=r"^result_[0-9a-f]{32}$")
    identity: ArtifactIdentity
    mode: ResultMode
    status: ResultStatus
    fixture_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")
    fixture_name: str | None = Field(default=None, min_length=1, max_length=128)
    availability: ArtifactAvailability
    artifacts: list[ArtifactRecord]
    failure: SafeFailure | None = None
    completed_stages: list[str] = Field(default_factory=list)
    inherited_stages: list[str] = Field(default_factory=list)
    audio: AudioResult | None = None

    @model_validator(mode="after")
    def terminal_publication_state(self) -> ResultManifest:
        if self.status not in {ResultStatus.COMPLETED, ResultStatus.PARTIAL, ResultStatus.FAILED}:
            raise ValueError("result manifest must describe a terminal publication")
        _validate_mode(self.mode, self.fixture_id, self.fixture_name)
        if self.status is ResultStatus.COMPLETED and (
            not self.availability.all() or self.failure is not None
        ):
            raise ValueError("completed result requires every artifact and no failure")
        if self.status is ResultStatus.PARTIAL and (
            not self.availability.any() or self.availability.all() or self.failure is None
        ):
            raise ValueError("partial result requires some artifacts and a safe failure")
        if self.status is ResultStatus.FAILED and (
            self.availability.any() or self.failure is None or self.artifacts
        ):
            raise ValueError("failed result cannot expose artifacts and requires a safe failure")
        paths = [item.path for item in self.artifacts]
        kinds = [item.kind for item in self.artifacts]
        if len(paths) != len(set(paths)) or len(kinds) != len(set(kinds)):
            raise ValueError("artifact members must be unique")
        if any(item.identity != self.identity for item in self.artifacts):
            raise ValueError("artifact identity does not match result identity")
        return self


class ResultViewState(StrictFrozenModel):
    mode: ResultMode
    status: ResultStatus
    fixture_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")
    fixture_name: str | None = Field(default=None, min_length=1, max_length=128)
    identity: ArtifactIdentity | None = None
    availability: ArtifactAvailability
    failure: SafeFailure | None = None
    current_stage: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{1,31}$")
    completed_stages: list[str] = Field(default_factory=list)
    inherited_stages: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def honest_view_state(self) -> ResultViewState:
        _validate_mode(self.mode, self.fixture_id, self.fixture_name)
        if self.status is ResultStatus.COMPLETED and (
            self.identity is None or not self.availability.all() or self.failure is not None
        ):
            raise ValueError("completed view requires verified complete identity")
        if self.status is ResultStatus.PARTIAL and (
            self.identity is None
            or not self.availability.any()
            or self.availability.all()
            or self.failure is None
        ):
            raise ValueError("partial view requires verified partial artifacts and failure")
        if self.status is ResultStatus.FAILED and (
            self.failure is None or self.availability.any()
        ):
            raise ValueError("failed view requires only a safe failure")
        if self.status is ResultStatus.RUNNING and not self.current_stage:
            raise ValueError("running view requires a current stage")
        return self


def _validate_mode(mode: ResultMode, fixture_id: str | None, fixture_name: str | None) -> None:
    if mode is ResultMode.REPLAY and not (fixture_id and fixture_name):
        raise ValueError("replay mode requires fixture identity")
    if mode is ResultMode.LIVE and (fixture_id is not None or fixture_name is not None):
        raise ValueError("live mode cannot carry replay identity")


def is_safe_stage(value: str) -> bool:
    """Narrow helper retained for UI adapters without exposing a path or exception."""

    return re.fullmatch(r"[a-z][a-z0-9_]{1,31}", value) is not None
