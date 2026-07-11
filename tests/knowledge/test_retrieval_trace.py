from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from debugmate.cli import main
from debugmate.contracts import ErrorCategory, new_case_id
from debugmate.evidence import EvidenceBundle
from debugmate.knowledge.models import load_registry
from debugmate.knowledge.retrieval import (
    EvaluationCase,
    ExpectedAnchor,
    RetrievalHit,
    RetrievalTrace,
    evaluate_retrieval_cases,
    load_evaluation_cases,
    load_retrieval_traces,
    run_offline_retrieval,
    validate_retrieval_trace,
    write_offline_retrieval_evidence,
)


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


def _manifest(tmp_path: Path) -> Path:
    build_id = "b" * 64
    manifest = {
        "build_id": build_id,
        "content_hash": "c" * 64,
        "sources": [
            {
                "source_id": "python-errors",
                "url": "https://docs.python.org/3/tutorial/errors.html",
                "retrieved_at": "2026-07-10T08:00:00Z",
            },
            {
                "source_id": "pytorch-cuda",
                "url": "https://docs.pytorch.org/docs/2.13/notes/cuda.html",
                "retrieved_at": "2026-07-11T08:00:00Z",
            },
        ],
        "notes": [
            {
                "source_id": "python-errors",
                "locators": ["#exceptions", "#handling-exceptions"],
            },
            {
                "source_id": "pytorch-cuda",
                "locators": ["#memory-management"],
            },
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def _case(
    category: ErrorCategory = ErrorCategory.DEPENDENCY_ENVIRONMENT,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=new_case_id(),
        category=category,
        query="虚构学生环境中导入包失败，但不包含任何真实路径",
        expected_anchors=[ExpectedAnchor(source_id="python-errors", locator="#exceptions")],
    )


def _trace(case: EvaluationCase, *, hits: list[RetrievalHit]) -> RetrievalTrace:
    return RetrievalTrace(
        case_id=case.case_id,
        query_sha256=_query_hash(case.query),
        knowledge_build_id="b" * 64,
        retrieved_at_utc=datetime(2026, 7, 11, 9, 0, tzinfo=UTC),
        hits=hits,
    )


def _hit(
    *,
    chunk_id: str = "python-errors#exceptions-0",
    content_summary: str = "Traceback anatomy",
    source_id: str = "python-errors",
    source_url: str = "https://docs.python.org/3/tutorial/errors.html",
    locator: str = "#exceptions",
    relevance_score: float = 0.91,
) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk_id,
        content_summary=content_summary,
        source_id=source_id,
        source_url=source_url,
        locator=locator,
        relevance_score=relevance_score,
    )


def test_retrieval_hit_keeps_only_auditable_bounded_source_fields() -> None:
    hit = _hit()

    assert hit.relevance_score == 0.91
    assert "content" not in hit.model_dump()
    with pytest.raises(ValidationError):
        _hit(content_summary="x" * 501)
    with pytest.raises(ValidationError):
        _hit(source_url="http://docs.python.org/3/tutorial/errors.html")
    with pytest.raises(ValidationError):
        _hit(relevance_score=1)  # type: ignore[arg-type]


def test_trace_rejects_duplicate_chunks_and_unsorted_scores() -> None:
    case = _case()

    with pytest.raises(ValidationError, match="duplicate"):
        _trace(case, hits=[_hit(), _hit()])
    with pytest.raises(ValidationError, match="descending"):
        _trace(
            case,
            hits=[
                _hit(relevance_score=0.2),
                _hit(chunk_id="python-errors#exceptions-1", relevance_score=0.9),
            ],
        )


def test_trace_validation_binds_registry_build_url_and_query(tmp_path: Path) -> None:
    case = _case()
    manifest = _manifest(tmp_path)
    registry = load_registry(Path("knowledge/sources.json"))
    trace = _trace(case, hits=[_hit()])

    assert validate_retrieval_trace(trace, manifest, registry, case) == trace

    wrong_url = _trace(
        case,
        hits=[_hit(source_url="https://docs.python.org/3/library/venv.html")],
    )
    with pytest.raises(ValueError, match="URL"):
        validate_retrieval_trace(wrong_url, manifest, registry, case)

    unknown = _trace(
        case,
        hits=[
            _hit(
                source_id="missing-source",
                source_url="https://docs.python.org/3/missing.html",
            )
        ],
    )
    with pytest.raises(ValueError, match="absent"):
        validate_retrieval_trace(unknown, manifest, registry, case)

    changed_query = case.model_copy(update={"query": case.query + " changed"})
    with pytest.raises(ValueError, match="query"):
        validate_retrieval_trace(trace, manifest, registry, changed_query)


def test_validation_and_evidence_reject_model_copy_bypass(tmp_path: Path) -> None:
    case = _case()
    invalid_hit = _hit().model_copy(update={"content_summary": "raw" * 200})
    invalid_trace = _trace(case, hits=[_hit()]).model_copy(update={"hits": [invalid_hit]})

    with pytest.raises(ValidationError):
        validate_retrieval_trace(invalid_trace, _manifest(tmp_path), case=case)

    bundle = EvidenceBundle.begin(tmp_path / "evidence", case.case_id)
    with pytest.raises(ValidationError):
        bundle.write_retrieval_trace(invalid_trace)


def test_trace_rejects_locator_borrowed_from_another_source(tmp_path: Path) -> None:
    case = _case()
    cross_paired = _trace(
        case,
        hits=[_hit(locator="#memory-management")],
    )

    with pytest.raises(ValueError, match="locator"):
        validate_retrieval_trace(cross_paired, _manifest(tmp_path), case=case)

    result = evaluate_retrieval_cases([case], [cross_paired])
    assert result.by_category[ErrorCategory.DEPENDENCY_ENVIRONMENT].hit_rate == 0.0


def test_evaluation_strictly_revalidates_model_copies_and_direct_dicts(
    tmp_path: Path,
) -> None:
    case = _case()
    trace = _trace(case, hits=[_hit()])

    valid = evaluate_retrieval_cases(
        [case.model_dump()],
        [trace.model_dump()],
        build_manifest=_manifest(tmp_path),
    )
    assert valid.by_category[case.category].hit_rate == 1.0

    invalid_case = case.model_copy(update={"query": ""})
    with pytest.raises(ValidationError):
        evaluate_retrieval_cases([invalid_case], [trace])
    with pytest.raises(ValidationError):
        evaluate_retrieval_cases([{"case_id": case.case_id}], [trace])


def test_category_hit_rate_and_blind_spot_are_reported(tmp_path: Path) -> None:
    dependency = _case(ErrorCategory.DEPENDENCY_ENVIRONMENT)
    cuda = _case(ErrorCategory.CUDA_MEMORY).model_copy(
        update={
            "expected_anchors": [
                ExpectedAnchor(source_id="pytorch-cuda", locator="#memory-management")
            ],
        }
    )
    traces = [_trace(dependency, hits=[_hit()]), _trace(cuda, hits=[])]

    result = evaluate_retrieval_cases(
        [cuda, dependency], traces, build_manifest=_manifest(tmp_path), top_k=3
    )

    assert result.by_category[ErrorCategory.DEPENDENCY_ENVIRONMENT].hit_rate == 1.0
    assert result.by_category[ErrorCategory.CUDA_MEMORY].hit_rate == 0.0
    assert ErrorCategory.CUDA_MEMORY.value in result.blind_spots
    assert result.blind_spots == sorted(result.blind_spots)
    assert result.by_category[ErrorCategory.CUDA_MEMORY].uncovered_expected_sources == [
        "pytorch-cuda"
    ]
    assert (
        result.by_category[ErrorCategory.CUDA_MEMORY].last_source_update_utc
        == "2026-07-11T08:00:00Z"
    )


def test_evaluation_rejects_missing_duplicate_or_wrong_build_traces(
    tmp_path: Path,
) -> None:
    case = _case()
    trace = _trace(case, hits=[_hit()])

    with pytest.raises(ValueError, match="exactly one"):
        evaluate_retrieval_cases([case], [], build_manifest=_manifest(tmp_path))
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_retrieval_cases([case], [trace, trace], build_manifest=_manifest(tmp_path))
    with pytest.raises(ValueError, match="build"):
        evaluate_retrieval_cases(
            [case],
            [trace.model_copy(update={"knowledge_build_id": "d" * 64})],
            build_manifest=_manifest(tmp_path),
        )


def test_fixed_query_set_covers_every_category_and_known_registry_sources() -> None:
    cases = load_evaluation_cases(Path("knowledge/eval_queries.json"))
    registry = load_registry(Path("knowledge/sources.json"))
    known_ids = {source.source_id for source in registry.sources}

    assert {case.category for case in cases} == set(ErrorCategory)
    assert len({case.case_id for case in cases}) == len(cases)
    assert all(
        {anchor.source_id for anchor in case.expected_anchors} <= known_ids for case in cases
    )
    assert all(case.expected_anchors for case in cases)


def test_retrieval_evidence_contains_summary_but_never_raw_chunk(tmp_path: Path) -> None:
    case = _case()
    trace = _trace(case, hits=[_hit()])
    bundle = EvidenceBundle.begin(tmp_path / "evidence", case.case_id)

    output = bundle.write_retrieval_trace(trace)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert output.name == "retrieval.json"
    assert payload["hits"][0]["content_summary"] == "Traceback anatomy"
    assert "content" not in payload["hits"][0]


def test_coverage_cli_includes_retrieval_evaluation_when_fixtures_are_given(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case = _case()
    trace = _trace(case, hits=[_hit()])
    _manifest(tmp_path)
    queries = tmp_path / "queries.json"
    queries.write_text(
        json.dumps({"version": "1.0.0", "cases": [case.model_dump(mode="json")]}),
        encoding="utf-8",
    )
    traces = tmp_path / "traces.json"
    traces.write_text(
        json.dumps({"traces": [trace.model_dump(mode="json")]}),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "knowledge-coverage",
                str(tmp_path),
                "--eval-queries",
                str(queries),
                "--retrieval-traces",
                str(traces),
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    evaluation = payload["retrieval_evaluation"]
    assert evaluation["knowledge_build_id"] == "b" * 64
    assert evaluation["by_category"]["dependency_environment"]["hit_rate"] == 1.0


def _fixture_build(tmp_path: Path) -> Path:
    build = tmp_path / "fixture-build"
    notes = build / "notes"
    notes.mkdir(parents=True)
    (notes / "python-errors.md").write_text(
        "# Python Errors\n\n## 短摘录\n\n"
        "- #exceptions：Tracebacks identify the exception type and triggering line.\n"
        "- #handling-exceptions：Handlers can catch selected exception classes.\n\n"
        "SECRET_RAW_NOTE_BODY_THAT_MUST_NOT_BE_EXPORTED\n",
        encoding="utf-8",
    )
    manifest = {
        "build_id": "b" * 64,
        "content_hash": "c" * 64,
        "sources": [
            {
                "source_id": "python-errors",
                "url": "https://docs.python.org/3/tutorial/errors.html",
                "retrieved_at": "2026-07-10T08:00:00Z",
            }
        ],
        "notes": [
            {
                "source_id": "python-errors",
                "path": "notes/python-errors.md",
                "categories": ["python_runtime"],
                "locators": ["#exceptions", "#handling-exceptions"],
            }
        ],
    }
    (build / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return build


def test_offline_runner_reads_published_notes_and_keeps_honest_misses(
    tmp_path: Path,
) -> None:
    build_path = _fixture_build(tmp_path)
    cases = load_evaluation_cases(Path("knowledge/eval_queries.json"))

    run = run_offline_retrieval(cases, build_path, top_k=3)

    assert run.backend == "offline_fixture"
    assert {trace.case_id for trace in run.traces} == {case.case_id for case in cases}
    assert len(run.traces) == len(ErrorCategory)
    python_case = next(case for case in cases if case.category is ErrorCategory.PYTHON_RUNTIME)
    python_trace = next(trace for trace in run.traces if trace.case_id == python_case.case_id)
    assert python_trace.hits
    assert python_trace.hits[0].source_id == "python-errors"
    assert python_trace.hits[0].locator.startswith("#")
    assert len(python_trace.hits[0].content_summary) <= 500
    dependency_case = next(
        case for case in cases if case.category is ErrorCategory.DEPENDENCY_ENVIRONMENT
    )
    dependency_trace = next(
        trace for trace in run.traces if trace.case_id == dependency_case.case_id
    )
    assert dependency_trace.hits == []
    assert ErrorCategory.DEPENDENCY_ENVIRONMENT.value in run.evaluation.blind_spots
    assert (
        run.evaluation.by_category[ErrorCategory.DEPENDENCY_ENVIRONMENT].last_source_update_utc
        is None
    )


def test_offline_retrieval_evidence_is_reproducible_and_contains_no_raw_notes(
    tmp_path: Path,
) -> None:
    build_path = _fixture_build(tmp_path)
    cases = load_evaluation_cases(Path("knowledge/eval_queries.json"))
    first = run_offline_retrieval(cases, build_path)
    second = run_offline_retrieval(cases, build_path)

    first_paths = write_offline_retrieval_evidence(first, tmp_path / "one")
    second_paths = write_offline_retrieval_evidence(second, tmp_path / "two")

    assert first_paths.run.read_bytes() == second_paths.run.read_bytes()
    assert first_paths.traces.read_bytes() == second_paths.traces.read_bytes()
    assert load_retrieval_traces(first_paths.traces) == first.traces
    payload = json.loads(first_paths.run.read_text(encoding="utf-8"))
    assert payload["backend"] == "offline_fixture"
    assert "raw_chunk" not in first_paths.run.read_text(encoding="utf-8")
    assert "SECRET_RAW_NOTE_BODY" not in first_paths.run.read_text(encoding="utf-8")


def test_retrieval_eval_cli_generates_actual_offline_evidence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_path = _fixture_build(tmp_path)
    output = tmp_path / "retrieval-evidence"

    assert (
        main(
            [
                "knowledge-retrieval-eval",
                str(build_path),
                "--eval-queries",
                "knowledge/eval_queries.json",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    summary = json.loads(capsys.readouterr().out)
    assert summary["backend"] == "offline_fixture"
    assert summary["trace_count"] == len(ErrorCategory)
    assert Path(summary["run_path"]).is_file()
    assert Path(summary["traces_path"]).is_file()


def test_default_knowledge_wrapper_runs_retrieval_before_coverage() -> None:
    script = Path("scripts/build_knowledge.ps1").read_text(encoding="utf-8")

    retrieval = script.index("knowledge-retrieval-eval")
    coverage = script.index("knowledge-coverage")
    assert retrieval < coverage
    assert "knowledge\\eval_queries.json" in script
    assert "--retrieval-traces" in script
    assert "offline_fixture" in script
