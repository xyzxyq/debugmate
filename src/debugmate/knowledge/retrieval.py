"""Strict, privacy-safe retrieval traces and deterministic hit-rate evaluation."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, NamedTuple, Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from debugmate.contracts import CaseId, ErrorCategory
from debugmate.knowledge.build import validate_knowledge_build
from debugmate.knowledge.models import SourceRegistry, StrictKnowledgeModel
from debugmate.privacy.output_scan import assert_export_safe

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
            or self.retrieved_at_utc.utcoffset() != UTC.utcoffset(self.retrieved_at_utc)
        ):
            raise ValueError("retrieved_at_utc must be timezone-aware UTC")
        chunk_ids = [hit.chunk_id for hit in self.hits]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("retrieval hit chunk IDs must not contain duplicates")
        scores = [hit.relevance_score for hit in self.hits]
        if scores != sorted(scores, reverse=True):
            raise ValueError("retrieval hits must use descending relevance order")
        return self


class ExpectedAnchor(StrictKnowledgeModel):
    """An expected retrieval locator bound to exactly one official source."""

    source_id: SourceId
    locator: NonEmpty

    @field_validator("locator")
    @classmethod
    def reject_blank_locator(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("expected locator must not be blank")
        return value


class EvaluationCase(StrictKnowledgeModel):
    """One fictional, versioned retrieval query with expected source anchors."""

    case_id: CaseId
    category: ErrorCategory
    query: Annotated[str, Field(min_length=1, max_length=2_000)]
    expected_anchors: Annotated[list[ExpectedAnchor], Field(min_length=1)]

    @model_validator(mode="after")
    def require_unique_expectations(self) -> Self:
        if not self.query.strip():
            raise ValueError("evaluation query must not be blank")
        anchors = [(anchor.source_id, anchor.locator) for anchor in self.expected_anchors]
        if len(anchors) != len(set(anchors)):
            raise ValueError("expected source anchors must be unique")
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


class OfflineRetrievalRun(StrictKnowledgeModel):
    """A reproducible local run over published structured notes."""

    backend: Literal["offline_fixture"] = "offline_fixture"
    knowledge_build_id: Sha256
    traces: list[RetrievalTrace]
    evaluation: RetrievalEvaluation

    @model_validator(mode="after")
    def bind_run_to_one_build(self) -> Self:
        if self.evaluation.knowledge_build_id != self.knowledge_build_id:
            raise ValueError("offline evaluation must match the run build")
        if any(trace.knowledge_build_id != self.knowledge_build_id for trace in self.traces):
            raise ValueError("offline traces must match the run build")
        return self


class RetrievalEvidencePaths(NamedTuple):
    """Paths written for reuse by the coverage command and course evidence."""

    traces: Path
    run: Path


def _query_sha256(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


def _load_manifest(build_manifest: Path | dict[str, object]) -> dict[str, object]:
    if isinstance(build_manifest, Path):
        path = build_manifest / "manifest.json" if build_manifest.is_dir() else build_manifest
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
        source_url = raw.get("url")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("knowledge build source_id must be non-empty text")
        if source_id in by_id:
            raise ValueError("knowledge build contains duplicate source IDs")
        if not isinstance(source_url, str):
            raise ValueError("knowledge build source url must be text")
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


def _manifest_note_locators(manifest: dict[str, object]) -> dict[str, set[str]]:
    notes = manifest.get("notes")
    if not isinstance(notes, list):
        raise ValueError("knowledge build manifest notes must be a list")
    by_source: dict[str, set[str]] = {}
    for raw in notes:
        if not isinstance(raw, dict):
            raise ValueError("knowledge build notes must be objects")
        source_id = raw.get("source_id")
        locators = raw.get("locators")
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("knowledge build note source_id must be non-empty text")
        if source_id in by_source:
            raise ValueError("knowledge build contains duplicate note source IDs")
        if (
            not isinstance(locators, list)
            or not locators
            or not all(isinstance(locator, str) and locator.strip() for locator in locators)
        ):
            raise ValueError("knowledge build note locators must be non-empty text")
        if len(locators) != len(set(locators)):
            raise ValueError("knowledge build note locators must be unique")
        by_source[source_id] = set(locators)
    return by_source


def _strict_case(value: object) -> EvaluationCase:
    payload = value.model_dump() if isinstance(value, EvaluationCase) else value
    return EvaluationCase.model_validate(payload, strict=True)


def _strict_trace(value: object) -> RetrievalTrace:
    payload = value.model_dump() if isinstance(value, RetrievalTrace) else value
    return RetrievalTrace.model_validate(payload, strict=True)


def validate_retrieval_trace(
    trace: RetrievalTrace,
    build_manifest: Path | dict[str, object],
    registry: SourceRegistry | None = None,
    case: EvaluationCase | None = None,
) -> RetrievalTrace:
    """Validate trace IDs and URLs against an immutable build and registry."""

    trace = _strict_trace(trace)
    case = _strict_case(case) if case is not None else None
    manifest = _load_manifest(build_manifest)
    build_id = manifest.get("build_id")
    if trace.knowledge_build_id != build_id:
        raise ValueError("retrieval trace knowledge build ID does not match manifest")
    build_sources = _manifest_sources(manifest)
    note_locators = _manifest_note_locators(manifest)
    registry_sources = (
        {source.source_id: source for source in registry.sources} if registry is not None else None
    )
    for hit in trace.hits:
        built = build_sources.get(hit.source_id)
        if built is None:
            raise ValueError(f"retrieval source {hit.source_id!r} is absent from build")
        if hit.source_url != built["url"]:
            raise ValueError(f"retrieval source URL mismatch for {hit.source_id!r}")
        if hit.locator not in note_locators.get(hit.source_id, set()):
            raise ValueError(f"retrieval locator is not published for source {hit.source_id!r}")
        if registry_sources is not None:
            registered = registry_sources.get(hit.source_id)
            if registered is None:
                raise ValueError(f"retrieval source {hit.source_id!r} is absent from registry")
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
        EvaluationCase.model_validate_json(json.dumps(item), strict=True) for item in raw["cases"]
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
        RetrievalTrace.model_validate_json(json.dumps(item), strict=True) for item in raw["traces"]
    ]
    case_ids = [trace.case_id for trace in traces]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("retrieval trace file contains duplicate case IDs")
    return traces


def evaluate_retrieval_cases(
    cases: list[EvaluationCase] | list[object],
    traces: list[RetrievalTrace] | list[object],
    *,
    build_manifest: Path | dict[str, object] | None = None,
    top_k: int = 3,
) -> RetrievalEvaluation:
    """Compute deterministic per-category top-k hit rates and blind spots."""

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    cases = [_strict_case(case) for case in cases]
    traces = [_strict_trace(trace) for trace in traces]
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
            expected_pairs = {
                (anchor.source_id, anchor.locator) for anchor in case.expected_anchors
            }
            expected_sources.update(source_id for source_id, _ in expected_pairs)
            matched = {
                hit.source_id
                for hit in trace.hits[:top_k]
                if (hit.source_id, hit.locator) in expected_pairs
            }
            if matched:
                hit_count += 1
                covered_sources.update(matched)
            for source_id in sorted({anchor.source_id for anchor in case.expected_anchors}):
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


def _note_summary(note_text: str, locator: str, source_id: str) -> str:
    """Return a bounded excerpt tied to a published locator, not a raw chunk."""

    candidates = [
        line.removeprefix(f"- {locator}").lstrip("：: ").strip()
        for line in note_text.splitlines()
        if line.startswith(f"- {locator}")
    ]
    summary = next((candidate for candidate in candidates if candidate), "")
    if not summary:
        summary = f"Structured diagnostic note for {source_id} at {locator}"
    summary = re.sub(r"\s+", " ", summary).strip()
    return summary[:500]


def _offline_retrieved_at(manifest: dict[str, object]) -> datetime:
    sources = _manifest_sources(manifest)
    timestamps = [
        datetime.fromisoformat(str(source["retrieved_at"]).removesuffix("Z") + "+00:00")
        for source in sources.values()
    ]
    if not timestamps:
        raise ValueError("offline retrieval requires at least one built source")
    return max(timestamps)


def run_offline_retrieval(
    cases: list[EvaluationCase] | list[object],
    build: Path,
    *,
    top_k: int = 3,
) -> OfflineRetrievalRun:
    """Retrieve from actual built notes using their audited category/anchor index.

    This intentionally small fixture backend does not claim semantic similarity or
    Dify behavior. A note is eligible only when its published category matches the
    evaluation case; absent categories produce honest empty traces.
    """

    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    strict_cases = [_strict_case(case) for case in cases]
    validated_build = validate_knowledge_build(build)
    manifest = validated_build.manifest
    build_id = manifest.get("build_id")
    if not isinstance(build_id, str):
        raise ValueError("knowledge build ID must be text")
    source_records = _manifest_sources(manifest)
    raw_notes = manifest.get("notes")
    if not isinstance(raw_notes, list):
        raise ValueError("knowledge build manifest notes must be a list")
    retrieved_at = _offline_retrieved_at(manifest)

    indexed_notes: list[tuple[str, str, list[str], set[ErrorCategory], str]] = []
    for raw_note in raw_notes:
        if not isinstance(raw_note, dict):
            raise ValueError("knowledge build notes must be objects")
        source_id = raw_note.get("source_id")
        relative_path = raw_note.get("path")
        locators = raw_note.get("locators")
        categories = raw_note.get("categories")
        if (
            not isinstance(source_id, str)
            or relative_path != f"notes/{source_id}.md"
            or not isinstance(locators, list)
            or not all(isinstance(locator, str) for locator in locators)
            or not isinstance(categories, list)
        ):
            raise ValueError("knowledge note index is invalid")
        try:
            note_text = validated_build.note_bytes[relative_path].decode("utf-8")
        except KeyError as error:
            raise ValueError(f"published note is missing: {relative_path}") from error
        except UnicodeDecodeError as error:
            raise ValueError(f"published note is not UTF-8: {relative_path}") from error
        strict_categories = {
            ErrorCategory(category) for category in categories if isinstance(category, str)
        }
        source_url = source_records[source_id]["url"]
        if not isinstance(source_url, str):
            raise ValueError("knowledge source URL must be text")
        indexed_notes.append((source_id, source_url, list(locators), strict_categories, note_text))

    traces: list[RetrievalTrace] = []
    for case in strict_cases:
        hits: list[RetrievalHit] = []
        for source_id, source_url, locators, categories, note_text in indexed_notes:
            if case.category not in categories:
                continue
            for index, locator in enumerate(locators):
                hits.append(
                    RetrievalHit(
                        chunk_id=f"{source_id}{locator}-{index}",
                        content_summary=_note_summary(note_text, locator, source_id),
                        source_id=source_id,
                        source_url=source_url,
                        locator=locator,
                        relevance_score=float(max(0.0, 0.9 - index * 0.01)),
                    )
                )
        hits = sorted(
            hits,
            key=lambda hit: (-hit.relevance_score, hit.chunk_id),
        )[:top_k]
        trace = RetrievalTrace(
            case_id=case.case_id,
            query_sha256=_query_sha256(case.query),
            knowledge_build_id=build_id,
            retrieved_at_utc=retrieved_at,
            hits=hits,
        )
        traces.append(validate_retrieval_trace(trace, manifest, case=case))

    evaluation = evaluate_retrieval_cases(
        strict_cases,
        traces,
        build_manifest=manifest,
        top_k=top_k,
    )
    return OfflineRetrievalRun(
        knowledge_build_id=build_id,
        traces=traces,
        evaluation=evaluation,
    )


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_offline_retrieval_evidence(
    run: OfflineRetrievalRun,
    output: Path,
) -> RetrievalEvidencePaths:
    """Persist reproducible summary-only retrieval evidence outside the build."""

    validated = OfflineRetrievalRun.model_validate(run.model_dump(), strict=True)
    traces_payload = {
        "traces": [trace.model_dump(mode="json") for trace in validated.traces]
    }
    run_payload = validated.model_dump(mode="json")
    assert_export_safe(traces_payload)
    assert_export_safe(run_payload)
    output.mkdir(parents=True, exist_ok=True)
    traces_path = output / "retrieval-traces.json"
    run_path = output / "retrieval-run.json"
    traces_path.write_bytes(
        _canonical_json(traces_payload)
    )
    run_path.write_bytes(_canonical_json(run_payload))
    return RetrievalEvidencePaths(traces=traces_path, run=run_path)


__all__ = [
    "CategoryRetrievalEvaluation",
    "EvaluationCase",
    "ExpectedAnchor",
    "OfflineRetrievalRun",
    "RetrievalEvaluation",
    "RetrievalHit",
    "RetrievalEvidencePaths",
    "RetrievalTrace",
    "evaluate_retrieval_cases",
    "load_evaluation_cases",
    "load_retrieval_traces",
    "run_offline_retrieval",
    "validate_retrieval_trace",
    "write_offline_retrieval_evidence",
]
