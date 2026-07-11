"""Strict, privacy-safe retrieval traces and deterministic hit-rate evaluation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from debugmate.contracts import CaseId, ErrorCategory
from debugmate.knowledge.models import SourceRegistry, StrictKnowledgeModel

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
SourceId = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
NonEmpty = Annotated[str, Field(min_length=1)]


class RetrievalHit(StrictKnowledgeModel):
    """One auditable hit with only a bounded summary, never raw chunk content."""

    chunk_id: NonEmpty
    content_summary: Annotated[str, Field(min_length=1, max_length=500)]
    source_id: SourceId
    source_url: NonEmpty
    locator: NonEmpty
    relevance_score: Annotated[float, Field(strict=True, ge=0.0, le=1.0)]

    @field_validator("chunk_id", "content_summary", "locator")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("retrieval text fields must not be blank")
        return value

    @field_validator("source_url")
    @classmethod
    def require_https_source_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        try:
            port = parsed.port
        except ValueError as error:
            raise ValueError("source_url has an invalid port") from error
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or port not in (None, 443)
        ):
            raise ValueError("source_url must be a fragment-free HTTPS URL")
        return value

    @field_validator("relevance_score", mode="before")
    @classmethod
    def require_actual_float(cls, value: object) -> object:
        if type(value) is not float:
            raise ValueError("relevance_score must be a JSON floating-point number")
        return value


class RetrievalTrace(StrictKnowledgeModel):
    """Retrieval evidence bound to one case, query and immutable build."""

    case_id: CaseId
    query_sha256: Sha256
    knowledge_build_id: Sha256
    retrieved_at_utc: datetime
    hits: list[RetrievalHit]

    @model_validator(mode="after")
    def require_utc_unique_descending_hits(self) -> Self:
        if (
            self.retrieved_at_utc.tzinfo is None
            or self.retrieved_at_utc.utcoffset()
            != UTC.utcoffset(self.retrieved_at_utc)
        ):
            raise ValueError("retrieved_at_utc must be timezone-aware UTC")
        chunk_ids = [hit.chunk_id for hit in self.hits]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("retrieval hit chunk IDs must not contain duplicates")
        scores = [hit.relevance_score for hit in self.hits]
        if scores != sorted(scores, reverse=True):
            raise ValueError("retrieval hits must use descending relevance order")
        return self


class EvaluationCase(StrictKnowledgeModel):
    """One fictional, versioned retrieval query with expected source anchors."""

    case_id: CaseId
    category: ErrorCategory
    query: Annotated[str, Field(min_length=1, max_length=2_000)]
    expected_source_ids: Annotated[list[SourceId], Field(min_length=1)]
    expected_locators: Annotated[list[NonEmpty], Field(min_length=1)]

    @model_validator(mode="after")
    def require_unique_expectations(self) -> Self:
        if not self.query.strip():
            raise ValueError("evaluation query must not be blank")
        if len(self.expected_source_ids) != len(set(self.expected_source_ids)):
            raise ValueError("expected source IDs must be unique")
        if len(self.expected_locators) != len(set(self.expected_locators)):
            raise ValueError("expected locators must be unique")
        if any(not locator.strip() for locator in self.expected_locators):
            raise ValueError("expected locators must not be blank")
        return self


class CategoryRetrievalEvaluation(StrictKnowledgeModel):
    """Deterministic hit-rate aggregate for one error category."""

    case_count: int = Field(strict=True, ge=0)
    top_k_hit_count: int = Field(strict=True, ge=0)
    hit_rate: Annotated[float, Field(strict=True, ge=0.0, le=1.0)]
    uncovered_expected_sources: list[SourceId]
    last_source_update_utc: str | None


class RetrievalEvaluation(StrictKnowledgeModel):
    """Evaluation result across all stable DebugMate error categories."""

    knowledge_build_id: Sha256
    top_k: int = Field(strict=True, ge=1)
    by_category: dict[ErrorCategory, CategoryRetrievalEvaluation]
    blind_spots: list[str]


def _query_sha256(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


def _load_manifest(build_manifest: Path | dict[str, object]) -> dict[str, object]:
    if isinstance(build_manifest, Path):
        path = (
            build_manifest / "manifest.json"
            if build_manifest.is_dir()
            else build_manifest
        )
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = build_manifest
    if not isinstance(value, dict):
        raise ValueError("knowledge build manifest must be an object")
    return value


def _manifest_sources(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        raise ValueError("knowledge build manifest sources must be a list")
    by_id: dict[str, dict[str, object]] = {}
    for raw in sources:
        if not isinstance(raw, dict):
            raise ValueError("knowledge build sources must be objects")
        source_id = raw.get("source_id")
        source_url = raw.get("source_url")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("knowledge build source_id must be non-empty text")
        if source_id in by_id:
            raise ValueError("knowledge build contains duplicate source IDs")
        if not isinstance(source_url, str):
            raise ValueError("knowledge build source_url must be text")
        RetrievalHit.require_https_source_url(source_url)
        retrieved_at = raw.get("retrieved_at")
        if not isinstance(retrieved_at, str) or not retrieved_at.endswith("Z"):
            raise ValueError("knowledge build retrieved_at must be UTC text")
        try:
            parsed = datetime.fromisoformat(retrieved_at.removesuffix("Z") + "+00:00")
        except ValueError as error:
            raise ValueError("knowledge build retrieved_at must be ISO UTC") from error
        if parsed.utcoffset() != UTC.utcoffset(parsed):
            raise ValueError("knowledge build retrieved_at must be UTC")
        by_id[source_id] = raw
    return by_id


def validate_retrieval_trace(
    trace: RetrievalTrace,
    build_manifest: Path | dict[str, object],
    registry: SourceRegistry | None = None,
    case: EvaluationCase | None = None,
) -> RetrievalTrace:
    """Validate trace IDs and URLs against an immutable build and registry."""

    RetrievalTrace.model_validate(trace.model_dump(), strict=True)
    manifest = _load_manifest(build_manifest)
    build_id = manifest.get("build_id")
    if trace.knowledge_build_id != build_id:
        raise ValueError("retrieval trace knowledge build ID does not match manifest")
    build_sources = _manifest_sources(manifest)
    registry_sources = (
        {source.source_id: source for source in registry.sources}
        if registry is not None
        else None
    )
    for hit in trace.hits:
        built = build_sources.get(hit.source_id)
        if built is None:
            raise ValueError(f"retrieval source {hit.source_id!r} is absent from build")
        if hit.source_url != built["source_url"]:
            raise ValueError(f"retrieval source URL mismatch for {hit.source_id!r}")
        if registry_sources is not None:
            registered = registry_sources.get(hit.source_id)
            if registered is None:
                raise ValueError(
                    f"retrieval source {hit.source_id!r} is absent from registry"
                )
            if hit.source_url != registered.url:
                raise ValueError(f"registry URL mismatch for {hit.source_id!r}")
    if case is not None:
        if trace.case_id != case.case_id:
            raise ValueError("retrieval trace case ID does not match evaluation case")
        if trace.query_sha256 != _query_sha256(case.query):
            raise ValueError("retrieval trace query hash does not match evaluation query")
    return trace


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    """Load a strict versioned query set and reject duplicate case IDs."""

    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"version", "cases"}:
        raise ValueError("evaluation query file must contain only version and cases")
    if raw["version"] != "1.0.0" or not isinstance(raw["cases"], list):
        raise ValueError("evaluation query file has an unsupported contract")
    cases = [
        EvaluationCase.model_validate_json(json.dumps(item), strict=True)
        for item in raw["cases"]
    ]
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("evaluation query file contains duplicate case IDs")
    return cases


def load_retrieval_traces(path: Path) -> list[RetrievalTrace]:
    """Load strict retrieval trace fixtures from a bounded JSON envelope."""

    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"traces"}:
        raise ValueError("retrieval trace file must contain only traces")
    if not isinstance(raw["traces"], list):
        raise ValueError("retrieval traces must be a list")
    traces = [
        RetrievalTrace.model_validate_json(json.dumps(item), strict=True)
        for item in raw["traces"]
    ]
    case_ids = [trace.case_id for trace in traces]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("retrieval trace file contains duplicate case IDs")
    return traces


def evaluate_retrieval_cases(
    cases: list[EvaluationCase],
    traces: list[RetrievalTrace],
    *,
    build_manifest: Path | dict[str, object] | None = None,
    top_k: int = 3,
) -> RetrievalEvaluation:
    """Compute deterministic per-category top-k hit rates and blind spots."""

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("evaluation cases contain duplicate case IDs")
    trace_ids = [trace.case_id for trace in traces]
    if len(trace_ids) != len(set(trace_ids)):
        raise ValueError("retrieval traces contain duplicate case IDs")
    if set(case_ids) != set(trace_ids):
        raise ValueError("each evaluation case requires exactly one retrieval trace")
    if not traces:
        raise ValueError("at least one retrieval trace is required")

    manifest = _load_manifest(build_manifest) if build_manifest is not None else None
    build_id = traces[0].knowledge_build_id
    trace_by_case = {trace.case_id: trace for trace in traces}
    for case in cases:
        trace = trace_by_case[case.case_id]
        if trace.knowledge_build_id != build_id:
            raise ValueError("retrieval traces must bind to one knowledge build")
        if manifest is not None:
            validate_retrieval_trace(trace, manifest, case=case)
        elif trace.query_sha256 != _query_sha256(case.query):
            raise ValueError("retrieval trace query hash does not match evaluation query")

    source_records = _manifest_sources(manifest) if manifest is not None else {}
    if manifest is not None:
        expected_source_ids = {
            source_id for case in cases for source_id in case.expected_source_ids
        }
        absent_expected = sorted(expected_source_ids - set(source_records))
        if absent_expected:
            raise ValueError(
                "evaluation expected sources are absent from build: "
                + ", ".join(absent_expected)
            )
    by_category: dict[ErrorCategory, CategoryRetrievalEvaluation] = {}
    for category in ErrorCategory:
        category_cases = sorted(
            (case for case in cases if case.category is category),
            key=lambda case: case.case_id,
        )
        hit_count = 0
        expected_sources: set[str] = set()
        covered_sources: set[str] = set()
        updates: list[str] = []
        for case in category_cases:
            trace = trace_by_case[case.case_id]
            expected_sources.update(case.expected_source_ids)
            expected_pairs = {
                (source_id, locator)
                for source_id in case.expected_source_ids
                for locator in case.expected_locators
            }
            matched = {
                hit.source_id
                for hit in trace.hits[:top_k]
                if (hit.source_id, hit.locator) in expected_pairs
            }
            if matched:
                hit_count += 1
                covered_sources.update(matched)
            for source_id in case.expected_source_ids:
                retrieved_at = source_records.get(source_id, {}).get("retrieved_at")
                if isinstance(retrieved_at, str):
                    updates.append(retrieved_at)
        count = len(category_cases)
        by_category[category] = CategoryRetrievalEvaluation(
            case_count=count,
            top_k_hit_count=hit_count,
            hit_rate=float(hit_count / count) if count else 0.0,
            uncovered_expected_sources=sorted(expected_sources - covered_sources),
            last_source_update_utc=max(updates) if updates else None,
        )

    blind_spots = sorted(
        category.value
        for category, result in by_category.items()
        if result.case_count == 0 or result.hit_rate == 0.0
    )
    return RetrievalEvaluation(
        knowledge_build_id=build_id,
        top_k=top_k,
        by_category=by_category,
        blind_spots=blind_spots,
    )


__all__ = [
    "CategoryRetrievalEvaluation",
    "EvaluationCase",
    "RetrievalEvaluation",
    "RetrievalHit",
    "RetrievalTrace",
    "evaluate_retrieval_cases",
    "load_evaluation_cases",
    "load_retrieval_traces",
    "validate_retrieval_trace",
]
