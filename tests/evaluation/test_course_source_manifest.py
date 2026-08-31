from __future__ import annotations

import hashlib
import json
from pathlib import Path

from debugmate.evaluation.collector import (
    build_phase10_source_manifest,
    collect_phase9_cases,
    validate_phase8_live_source,
)
from debugmate.evaluation.contracts import CaseRegistry, Phase8SourceEvidence
from debugmate.knowledge.sync import DifyReadbackAttestation, DifySyncConfig

CASES_PATH = Path("evaluation/phase9/cases.json")


def load_registry() -> CaseRegistry:
    return CaseRegistry.model_validate_json(CASES_PATH.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _formal_phase8_source(tmp_path: Path, *, skipped: int = 0) -> Phase8SourceEvidence:
    plan = tmp_path / ".planning/phases/08-dify-unified-live-chain/08-07-PLAN.md"
    summary = tmp_path / ".planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md"
    formal = tmp_path / "evidence/dify-live/phase8"
    plan.parent.mkdir(parents=True)
    formal.mkdir(parents=True)
    plan.write_text("formal plan", encoding="utf-8")
    summary.write_text("formal summary", encoding="utf-8")

    build_id = "4" * 64
    readback = DifyReadbackAttestation(
        knowledge_build_id=build_id,
        dataset_fingerprint="9" * 64,
        document_count=17,
        document_fingerprints=[f"{index:064x}" for index in range(1, 18)],
        config=DifySyncConfig(),
        response_hashes=["a" * 64],
    )
    _write_json(formal / "knowledge-readback.json", readback.model_dump(mode="json"))
    output_values = {
        "report.md": b"safe report",
        "card.png": b"safe png projection",
        "recap.mp3": b"safe mp3 projection",
        "result.zip": b"safe verified archive projection",
    }
    for name, value in output_values.items():
        (formal / name).write_bytes(value)
    live_run = {
        "schema_version": "phase8-live-run-1.0",
        "qa_run_id": "p8qa_" + "1" * 32,
        "backend": "dify",
        "case_id": "case_" + "2" * 32,
        "status": "completed",
        "prompt_sha256": "3" * 64,
        "schema_sha256": "5" * 64,
        "knowledge_build_id": build_id,
        "facts_sha256": "6" * 64,
        "retrieval_trace_sha256": "7" * 64,
        "diagnosis_sha256": "8" * 64,
        "result_id": "result_" + "b" * 32,
        "artifact_sha256": {name: _sha(formal / name) for name in output_values},
    }
    _write_json(formal / "live-run.json", live_run)
    artifact_names = ["knowledge-readback.json", "live-run.json", *output_values]
    manifest = {
        "schema_version": "phase8-formal-acceptance-1.0",
        "qa_run_id": live_run["qa_run_id"],
        "evidence_time_utc": "2026-08-11T00:00:00Z",
        "source_commit": "c" * 40,
        "worktree_scope_sha256": "d" * 64,
        "backend": "dify",
        "cloud_junit": {"tests": 1, "failures": 0, "errors": 0, "skipped": skipped},
        "edge_junit": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0},
        "artifacts": [
            {"path": name, "sha256": _sha(formal / name)} for name in artifact_names
        ],
    }
    _write_json(formal / "manifest.json", manifest)
    checksummed = ["manifest.json", *artifact_names]
    (formal / "checksums.sha256").write_text(
        "".join(f"{_sha(formal / name)}  {name}\n" for name in sorted(checksummed)),
        encoding="ascii",
    )
    return Phase8SourceEvidence.model_validate(
        {
            "acceptance_plan": {
                "path": {"path": ".planning/phases/08-dify-unified-live-chain/08-07-PLAN.md"},
                "sha256": _sha(plan),
            },
            "summary_path": {
                "path": ".planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md"
            },
            "summary_sha256": _sha(summary),
            "manifest_path": {"path": "evidence/dify-live/phase8/manifest.json"},
            "manifest_sha256": _sha(formal / "manifest.json"),
        }
    )


def test_phase8_live_source_accepts_current_formal_summary_and_manifest() -> None:
    registry = load_registry()
    live = registry.case_for("P9-C01-live-private")

    assert live.phase8_source is not None
    source = validate_phase8_live_source(live.phase8_source)

    assert source.valid is True
    assert source.reason == "current_phase8_source_verified"
    assert source.summary_path == ".planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md"
    assert source.manifest_path == "evidence/dify-live/phase8/manifest.json"


def test_collector_keeps_locked_cases_truthful_when_current_evidence_is_blocked() -> None:
    rows = collect_phase9_cases(load_registry())
    by_case_id = {row.case_id: row for row in rows}

    live = by_case_id["P9-C01-live-private"]
    assert live.phase10_eligible is False
    assert live.exclusion_reasons == ("result_bundle_missing",)
    assert live.execution_backend == "dify"

    insufficient = by_case_id["P9-C02-insufficient"]
    assert insufficient.phase10_eligible is False
    assert insufficient.exclusion_reasons == ("insufficient_data",)
    assert insufficient.availability.bundle is False

    fallback = by_case_id["P9-C04-fallback-failure"]
    assert fallback.phase10_eligible is False
    assert fallback.execution_backend == "local_fallback"
    assert fallback.actual_status == "partial"
    assert fallback.availability.audio is False
    assert fallback.exclusion_reasons == ("result_bundle_missing",)


def test_phase8_formal_source_uses_its_strict_zero_skip_manifest_and_checksums(
    tmp_path: Path,
) -> None:
    source = _formal_phase8_source(tmp_path)
    assert validate_phase8_live_source(source, repository_root=tmp_path).valid is True

    live_run = tmp_path / "evidence/dify-live/phase8/live-run.json"
    live_run.write_text("{}", encoding="utf-8")
    invalid = validate_phase8_live_source(source, repository_root=tmp_path)
    assert invalid.valid is False
    assert invalid.reason == "phase8_manifest_invalid"


def test_phase8_formal_source_rejects_any_skipped_acceptance_test(tmp_path: Path) -> None:
    source = _formal_phase8_source(tmp_path, skipped=1)
    invalid = validate_phase8_live_source(source, repository_root=tmp_path)
    assert invalid.valid is False
    assert invalid.reason == "phase8_manifest_invalid"


def test_phase10_source_manifest_contains_only_eligible_allowlisted_rows() -> None:
    ledger = build_phase10_source_manifest(collect_phase9_cases(load_registry()))

    assert ledger.manifest_version == "phase10-source-1.0"
    assert ledger.cases == ()
