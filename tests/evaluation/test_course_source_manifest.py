from __future__ import annotations

from pathlib import Path

from debugmate.evaluation.collector import (
    build_phase10_source_manifest,
    collect_phase9_cases,
    validate_phase8_live_source,
)
from debugmate.evaluation.contracts import CaseRegistry

CASES_PATH = Path("evaluation/phase9/cases.json")


def load_registry() -> CaseRegistry:
    return CaseRegistry.model_validate_json(CASES_PATH.read_text(encoding="utf-8"))


def test_phase8_live_source_requires_the_current_formal_summary_and_manifest() -> None:
    registry = load_registry()
    live = registry.case_for("P9-C01-live-private")

    assert live.phase8_source is not None
    source = validate_phase8_live_source(live.phase8_source)

    assert source.valid is False
    assert source.reason == "phase8_formal_evidence_missing"
    assert source.summary_path == ".planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md"
    assert source.manifest_path == "evidence/dify-live/phase8/manifest.json"


def test_collector_keeps_locked_cases_truthful_when_current_evidence_is_blocked() -> None:
    rows = collect_phase9_cases(load_registry())
    by_case_id = {row.case_id: row for row in rows}

    live = by_case_id["P9-C01-live-private"]
    assert live.phase10_eligible is False
    assert live.exclusion_reasons == ("phase8_formal_evidence_missing",)
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


def test_phase10_source_manifest_contains_only_eligible_allowlisted_rows() -> None:
    ledger = build_phase10_source_manifest(collect_phase9_cases(load_registry()))

    assert ledger.manifest_version == "phase10-source-1.0"
    assert ledger.cases == ()
