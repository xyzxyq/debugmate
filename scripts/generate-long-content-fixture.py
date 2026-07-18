"""Generate the strict deterministic Phase 4 long-content replay fixture."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from debugmate.diagnosis.extraction import (  # noqa: E402
    CaseFact,
    CaseFacts,
    CorrectionProvenance,
    FactCandidate,
    extraction_id_for,
    facts_hash,
)
from debugmate.diagnosis.routing import RoutingDecision  # noqa: E402
from debugmate.diagnosis.workflow import (  # noqa: E402
    DiagnosisRunOutcome,
    derive_run_identities,
)
from debugmate.evidence import RunManifest, verify_bundle  # noqa: E402
from debugmate.hashing import canonical_json_bytes, sha256_bytes  # noqa: E402

FIXTURE_ID = "long-content"
DISPLAY_LABEL = "\u957f\u62a5\u544a\u4e0e\u957f\u547d\u4ee4\uff1a\u5e03\u5c40\u97e7\u6027"
CASE_ID = "case_" + hashlib.sha256(b"debugmate-phase4-long-content-case").hexdigest()[:32]


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected object in {path}")
    return value


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _long_diagnosis(base: dict[str, object]) -> dict[str, object]:
    diagnosis = dict(base)
    diagnosis["case_id"] = CASE_ID
    marker = "verified_segment_" * 28 + "EXPECTED-LONG-COMMAND-END"
    diagnosis["checks"] = [
        {
            "command": f"python -c \"print('{marker}')\"",
            "expected_result": (
                "The complete deterministic marker is printed and ends with "
                "EXPECTED-LONG-COMMAND-END."
            ),
            "impact": (
                "read-only inspection of the active interpreter; "
                "no files or environments are changed"
            ),
            "platform": "windows_powershell",
            "rollback": (
                "No rollback is needed because the command is read-only; ROLLBACK-LONG-COMMAND-END"
            ),
        },
        {
            "command": "python -m pip show demo_missing_pkg",
            "expected_result": "Package metadata or a not-found message is displayed.",
            "impact": "read-only",
            "platform": "windows_powershell",
            "rollback": "No rollback is needed for a read-only command.",
        },
    ]
    diagnosis["limitations"] = [
        (
            f"Long-content limitation {index:02d}: this deterministic fixture does not inspect "
            "a real machine, execute commands, install packages, or infer facts outside its "
            "verified evidence."
        )
        for index in range(1, 25)
    ]
    diagnosis["missing_information"] = [
        (
            f"Long-content verification note {index:02d}: confirm the fictional interpreter, "
            "environment, package source, and reproducible context before changing anything."
        )
        for index in range(1, 25)
    ]
    diagnosis["recap_text"] = (
        "Review the verified long command without executing it, inspect the bounded report, "
        "and preserve the safety boundary."
    )
    return diagnosis


def generate(root: Path) -> Path:
    index_path = root / "index.json"
    index = _read_json(index_path)
    fixtures = index.get("fixtures")
    if not isinstance(fixtures, list):
        raise TypeError("replay index fixtures must be a list")
    baseline = next(
        item
        for item in fixtures
        if isinstance(item, dict) and item.get("fixture_id") == "module-not-found"
    )
    outcome_payload = _read_json(root / str(baseline["outcome_path"]))
    outcome_payload["case_id"] = CASE_ID
    outcome_payload["diagnosis"] = _long_diagnosis(
        dict(outcome_payload["diagnosis"])  # type: ignore[arg-type]
    )
    extraction = dict(outcome_payload["extraction"])  # type: ignore[arg-type]
    extraction["case_id"] = CASE_ID
    candidates = [
        FactCandidate.model_validate_json(json.dumps(item), strict=True)
        for item in extraction["candidates"]  # type: ignore[union-attr]
    ]
    source_hashes = dict(extraction["source_hashes"])  # type: ignore[arg-type]
    extraction["extraction_id"] = extraction_id_for(CASE_ID, source_hashes, candidates)
    outcome_payload["extraction"] = extraction
    facts = dict(outcome_payload["facts"])  # type: ignore[arg-type]
    facts["case_id"] = CASE_ID
    fact_items = [
        CaseFact.model_validate_json(json.dumps(item), strict=True)
        for item in facts["facts"]  # type: ignore[union-attr]
    ]
    corrections = [
        CorrectionProvenance.model_validate_json(json.dumps(item), strict=True)
        for item in facts["applied_corrections"]  # type: ignore[union-attr]
    ]
    facts["facts_sha256"] = facts_hash(CASE_ID, int(facts["revision"]), fact_items, corrections)
    outcome_payload["facts"] = facts
    outcome_payload["facts_sha256"] = facts["facts_sha256"]
    facts_model = CaseFacts.model_validate_json(json.dumps(facts), strict=True)
    routing_model = RoutingDecision.model_validate_json(
        json.dumps(outcome_payload["routing"]), strict=True
    )
    idempotency_key, run_id = derive_run_identities(
        facts_model, routing_model, str(outcome_payload["knowledge_build_id"])
    )
    outcome_payload["idempotency_key"] = idempotency_key
    outcome_payload["run_id"] = run_id
    outcome = DiagnosisRunOutcome.model_validate_json(
        json.dumps(outcome_payload, ensure_ascii=False), strict=True
    )

    target = root / FIXTURE_ID
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    _write_json(target / "outcome.json", outcome.model_dump(mode="json"))

    source = target / "source" / CASE_ID / run_id
    shutil.copytree(root / str(baseline["source_path"]), source)
    case_facts = _read_json(source / "case-facts.json")
    case_facts["case_id"] = CASE_ID
    case_facts["facts_sha256"] = outcome.facts_sha256
    _write_json(source / "case-facts.json", case_facts)
    _write_json(source / "diagnosis.json", outcome.diagnosis.model_dump(mode="json"))
    source_extraction = _read_json(source / "extraction.json")
    source_extraction["case_id"] = CASE_ID
    source_extraction["extraction_id"] = outcome.extraction.extraction_id
    _write_json(source / "extraction.json", source_extraction)
    retrieval = _read_json(source / "retrieval.json")
    retrieval["case_id"] = CASE_ID
    _write_json(source / "retrieval.json", retrieval)

    manifest_payload = _read_json(source / "manifest.json")
    manifest_payload["case_id"] = CASE_ID
    manifest_payload["run_id"] = run_id
    manifest_payload["input_sha256"] = outcome.facts_sha256
    manifest_payload["facts_sha256"] = outcome.facts_sha256
    artifacts: list[dict[str, object]] = []
    for path in sorted(item for item in source.iterdir() if item.name != "manifest.json"):
        payload = path.read_bytes()
        artifacts.append(
            {
                "path": path.name,
                "mime_type": "application/json",
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )
    manifest_payload["artifacts"] = artifacts
    manifest = RunManifest.model_validate_json(
        json.dumps(manifest_payload, ensure_ascii=False), strict=True
    )
    _write_json(source / "manifest.json", manifest.model_dump(mode="json"))
    verification = verify_bundle(source)
    if not verification.ok:
        raise RuntimeError(f"long-content source bundle did not verify: {verification.issues}")

    long_entry = {
        "fixture_id": FIXTURE_ID,
        "display_label": DISPLAY_LABEL,
        "case_id": CASE_ID,
        "run_id": run_id,
        "outcome_path": f"{FIXTURE_ID}/outcome.json",
        "source_path": f"{FIXTURE_ID}/source/{CASE_ID}/{run_id}",
    }
    retained = [
        item for item in fixtures if isinstance(item, dict) and item.get("fixture_id") != FIXTURE_ID
    ]
    for item in retained:
        if item.get("fixture_id") == "module-not-found":
            item["display_label"] = (
                "ModuleNotFoundError\uff1a\u7f3a\u5c11\u865a\u6784\u4f9d\u8d56\u5305"
            )
    index["fixtures"] = [*retained, long_entry]
    _write_json(index_path, index)
    return target


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("fixtures/replay")
    generate(destination)
