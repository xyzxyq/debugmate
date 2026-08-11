from __future__ import annotations

import json
from pathlib import Path

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


def test_collector_discovers_one_native_product_result_and_marks_it_eligible(
    candidates, tmp_path: Path
) -> None:
    case = _eligible_replay_case(tmp_path)
    locked = CaseRegistry.model_validate_json(
        Path("evaluation/phase9/cases.json").read_text(encoding="utf-8")
    )
    registry = locked.model_copy(
        update={
            "cases": tuple(case if item.case_id == case.case_id else item for item in locked.cases)
        }
    )
    staging_root = tmp_path / "evidence/evaluation/phase9" / case.case_id
    staging_root.parent.mkdir(parents=True)
    bundle = publish_result_bundle(
        TrustedResultRoot.for_testing(staging_root),
        validate_result_candidates(*candidates),
        mode=ResultMode.REPLAY,
        execution_backend=ExecutionBackend.REPLAY,
        fixture_id="phase9-supported-replay",
        fixture_name="Phase 9 supported replay",
    )

    rows = collect_phase9_cases(
        registry,
        repository_root=tmp_path,
    )

    row = next(item for item in rows if item.case_id == case.case_id)
    assert row.phase10_eligible is True
    assert row.exclusion_reasons == ()
    assert row.result_bundle_path == bundle.path.relative_to(tmp_path).as_posix()
