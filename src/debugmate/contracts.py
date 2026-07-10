"""Strict, platform-independent data contracts for DebugMate."""

from __future__ import annotations

import hashlib
import json
import uuid
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"
CASE_ID_PATTERN = r"^case_[0-9a-f]{32}$"

CaseId = Annotated[str, Field(pattern=CASE_ID_PATTERN)]
Confidence = Annotated[float, Field(strict=True, ge=0.0, le=1.0)]


class ErrorCategory(StrEnum):
    """Stable top-level error categories used by the workflow contract."""

    DEPENDENCY_ENVIRONMENT = "dependency_environment"
    PATH_PERMISSION = "path_permission"
    PYTHON_RUNTIME = "python_runtime"
    TENSOR_SHAPE_DTYPE = "tensor_shape_dtype"
    CUDA_MEMORY = "cuda_memory"
    MODEL_LOADING = "model_loading"
    UNKNOWN = "unknown"


class CapabilityStatus(StrEnum):
    """Result states shared by backend capability probes."""

    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_TESTED = "not-tested"


class StrictRecord(BaseModel):
    """Base configuration for all externally serialized records."""

    model_config = ConfigDict(strict=True, extra="forbid")


class RootCauseCandidate(StrictRecord):
    """One possible cause supported by observed facts."""

    cause: str
    supporting_facts: list[str]
    confidence: Confidence


class Citation(StrictRecord):
    """Traceable source reference for a diagnostic claim."""

    source_id: str
    title: str
    url: str
    locator: str
    excerpt: str


class CommandStep(StrictRecord):
    """A command recommendation stored as data and never executed here."""

    command: str
    platform: str
    impact: str
    expected_result: str
    rollback: str


class DiagnosisRecord(StrictRecord):
    """Versioned single source of truth for one diagnosis."""

    schema_version: Literal["1.0.0"]
    case_id: CaseId
    category: ErrorCategory
    observed_facts: list[str]
    root_cause_candidates: list[RootCauseCandidate]
    missing_information: list[str]
    checks: list[CommandStep]
    fixes: list[CommandStep]
    verification_steps: list[CommandStep]
    confidence: Confidence
    limitations: list[str]
    recap_text: str
    citations: list[Citation]


def new_case_id() -> str:
    """Return an opaque case identifier without time or user information."""

    return f"case_{uuid.uuid4().hex}"


def diagnosis_schema() -> dict[str, object]:
    """Return the generated JSON Schema for the diagnosis contract."""

    return DiagnosisRecord.model_json_schema()


def schema_sha256() -> str:
    """Return a deterministic SHA-256 for the generated JSON Schema."""

    canonical = json.dumps(
        diagnosis_schema(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
