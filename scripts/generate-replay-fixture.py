"""Generate the deterministic, fictional Phase 3 replay fixture."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.diagnosis.test_workflow_e2e import _approved, _rows, _workflow  # noqa: E402

from debugmate.cloud.contracts import ExecutionBackend  # noqa: E402
from debugmate.diagnosis.extraction import FieldId  # noqa: E402
from debugmate.diagnosis.workflow import validate_diagnosis_outcome  # noqa: E402
from debugmate.evidence import (  # noqa: E402
    RunManifest,
    publish_diagnosis_evidence,
    verify_bundle,
)
from debugmate.hashing import canonical_json_bytes  # noqa: E402

FIXTURE_ID = "module-not-found"
FIXED_TIME = "2026-01-01T00:00:00Z"


def generate(root: Path) -> Path:
    row = next(item for item in _rows() if item["case_key"] == "module_not_found")
    with tempfile.TemporaryDirectory(prefix="debugmate-replay-") as temporary:
        work = Path(temporary)
        workflow, *_ = _workflow(
            row, work, execution_backend=ExecutionBackend.REPLAY
        )
        answers = {FieldId(key): value for key, value in row.get("answers", {}).items()}
        outcome = workflow.run(
            _approved(str(row["case_id"])), followup_answers=answers or None
        )
        validate_diagnosis_outcome(outcome)
        published = publish_diagnosis_evidence(outcome, work / "evidence")

        manifest_path = published / "manifest.json"
        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_payload["created_at_utc"] = FIXED_TIME
        manifest_payload["completed_at_utc"] = FIXED_TIME
        manifest_payload["latency_ms"] = 0
        manifest = RunManifest.model_validate_json(
            json.dumps(manifest_payload, ensure_ascii=False), strict=True
        )
        manifest_path.write_bytes(canonical_json_bytes(manifest.model_dump(mode="json")))
        if not verify_bundle(published).ok:
            raise RuntimeError("generated Phase 3 source bundle did not verify")

        target = root / FIXTURE_ID
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        (target / "outcome.json").write_bytes(
            canonical_json_bytes(outcome.model_dump(mode="json"))
        )
        source = target / "source" / outcome.case_id / outcome.run_id
        source.parent.mkdir(parents=True)
        shutil.copytree(published, source)

    module_entry = {
        "fixture_id": FIXTURE_ID,
        "display_label": "ModuleNotFoundError：缺少虚构依赖包",
        "case_id": outcome.case_id,
        "run_id": outcome.run_id,
        "outcome_path": f"{FIXTURE_ID}/outcome.json",
        "source_path": f"{FIXTURE_ID}/source/{outcome.case_id}/{outcome.run_id}",
    }
    index_path = root / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(index, dict) or index.get("index_version") != "1.0.0":
            raise TypeError("replay index must be a version 1.0.0 object")
        fixtures = index.get("fixtures")
        if not isinstance(fixtures, list) or not all(
            isinstance(item, dict) and isinstance(item.get("fixture_id"), str)
            for item in fixtures
        ):
            raise TypeError("replay index fixtures must be fixture objects")
    else:
        index = {"index_version": "1.0.0", "fixtures": []}
        fixtures = []
    retained = [item for item in fixtures if item["fixture_id"] != FIXTURE_ID]
    index["fixtures"] = [module_entry, *retained]
    index_path.write_bytes(canonical_json_bytes(index))
    return target


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("fixtures/replay")
    generate(destination)
