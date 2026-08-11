from __future__ import annotations

import json
from pathlib import Path

import pytest

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.evaluation.collector import collect_phase9_cases
from debugmate.evaluation.contracts import CaseEvaluation, CaseRegistry
from debugmate.hashing import sha256_file
from debugmate.results.consistency import validate_result_candidates
from debugmate.results.contracts import ResultMode
from debugmate.results.publisher import (
    TrustedResultRoot,
    publish_result_bundle,
)


def _eligible_replay_case(repository_root: Path) -> CaseEvaluation:
    source = repository_root / "fixtures/replay/index.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(Path("fixtures/replay/index.json").read_bytes())
    registry = CaseRegistry.model_validate_json(
        Path("evaluation/phase9/cases.json").read_text(encoding="utf-8")
    )
    payload = registry.case_for("P9-C03-long-replay").model_dump(mode="json")
    payload.update(
        {
            "source_sha256": sha256_file(source),
            "expected_status": "completed",
            "actual_status": "completed",
            "availability": {
                "report": True,
                "card": True,
                "recap_text": True,
                "audio": True,
                "bundle": True,
            },
            "privacy": {
                "status": "pass",
                "safe_scan_sha256": sha256_file(source),
                "finding_count": 0,
            },
            "citations": {"status": "verified", "count": 1},
            "limitation": "A current verified replay result is staged for evaluation.",
        }
    )
    return CaseEvaluation.model_validate_json(json.dumps(payload), strict=True)


def _stage_bound_diagnosis_evidence(staging_root: Path, names: set[str]) -> None:
    outcome = json.loads(Path("fixtures/replay/module-not-found/outcome.json").read_text())
    if "outcome.json" in names:
        (staging_root / "outcome.json").write_text(json.dumps(outcome), encoding="utf-8")
    if "retrieval.json" in names:
        retrieval = {
            "case_id": outcome["case_id"],
            "query_sha256": "1" * 64,
            "knowledge_build_id": outcome["knowledge_build_id"],
            "retrieved_at_utc": "2026-08-11T00:00:00Z",
            "hits": [
                {
                    "chunk_id": "fixture:1",
                    "content_summary": "Official fictional fixture guidance.",
                    "source_id": "python-docs",
                    "source_url": "https://docs.python.org/3/",
                    "locator": "fixture",
                    "relevance_score": 0.9,
                }
            ],
        }
        (staging_root / "retrieval.json").write_text(
            json.dumps(retrieval), encoding="utf-8"
        )
    if "knowledge-build.json" in names:
        build = {
            "schema_version": "phase9-knowledge-build-binding-1.0",
            "build_id": outcome["knowledge_build_id"],
            "sources": [
                {
                    "source_id": "python-docs",
                    "url": "https://docs.python.org/3/",
                    "retrieved_at": "2026-08-11T00:00:00Z",
                }
            ],
            "notes": [{"source_id": "python-docs", "locators": ["fixture"]}],
        }
        (staging_root / "knowledge-build.json").write_text(
            json.dumps(build), encoding="utf-8"
        )


def _published_case(candidates, repository_root: Path):
    case = _eligible_replay_case(repository_root)
    locked = CaseRegistry.model_validate_json(
        Path("evaluation/phase9/cases.json").read_text(encoding="utf-8")
    )
    registry = locked.model_copy(
        update={
            "cases": tuple(case if item.case_id == case.case_id else item for item in locked.cases)
        }
    )
    staging_root = repository_root / "evidence/evaluation/phase9" / case.case_id
    staging_root.parent.mkdir(parents=True)
    bundle = publish_result_bundle(
        TrustedResultRoot.for_testing(staging_root),
        validate_result_candidates(*candidates),
        mode=ResultMode.REPLAY,
        execution_backend=ExecutionBackend.REPLAY,
        fixture_id="phase9-supported-replay",
        fixture_name="Phase 9 supported replay",
    )
    return case, registry, staging_root, bundle


def test_collector_discovers_one_native_product_result_and_marks_it_eligible(
    candidates, tmp_path: Path
) -> None:
    case, registry, staging_root, bundle = _published_case(candidates, tmp_path)
    _stage_bound_diagnosis_evidence(
        staging_root, {"outcome.json", "retrieval.json", "knowledge-build.json"}
    )

    rows = collect_phase9_cases(
        registry,
        repository_root=tmp_path,
    )

    row = next(item for item in rows if item.case_id == case.case_id)
    assert row.phase10_eligible is True
    assert row.exclusion_reasons == ()
    assert row.result_bundle_path == bundle.path.relative_to(tmp_path).as_posix()


@pytest.mark.parametrize(
    ("present", "reason"),
    [
        (set(), "diagnosis_outcome_missing"),
        ({"retrieval.json"}, "diagnosis_outcome_missing"),
        ({"knowledge-build.json"}, "diagnosis_outcome_missing"),
        ({"retrieval.json", "knowledge-build.json"}, "diagnosis_outcome_missing"),
        ({"outcome.json"}, "retrieval_evidence_missing"),
        ({"outcome.json", "knowledge-build.json"}, "retrieval_evidence_missing"),
        ({"outcome.json", "retrieval.json"}, "knowledge_build_evidence_missing"),
    ],
)
def test_collector_requires_the_complete_staged_diagnosis_evidence_set(
    candidates, tmp_path: Path, present: set[str], reason: str
) -> None:
    case, registry, staging_root, _bundle = _published_case(candidates, tmp_path)
    _stage_bound_diagnosis_evidence(staging_root, present)

    rows = collect_phase9_cases(registry, repository_root=tmp_path)
    row = next(item for item in rows if item.case_id == case.case_id)
    assert row.phase10_eligible is False
    assert row.exclusion_reasons == (reason,)
