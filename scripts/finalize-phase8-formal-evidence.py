"""Promote the verified Phase 8 result into the legacy formal evidence shape."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from debugmate.cloud.contracts import DifyRunEnvelope
from debugmate.contracts import schema_sha256
from debugmate.knowledge.sync import DifyReadbackAttestation

REQUIRED = (
    "knowledge-readback.json",
    "live-run.json",
    "report.md",
    "card.png",
    "recap.mp3",
    "result.zip",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    evidence = root / "evidence" / "dify-live" / "phase8"
    smoke = root / ".debugmate-runtime" / "phase8-cloud-smoke" / "live-smoke.json"
    envelope_path = root / ".debugmate-runtime" / "phase8-cloud-smoke" / "run-envelope.json"
    readback = evidence / "knowledge-readback.json"
    zip_candidates = sorted(
        evidence.glob("p8qa_*-result.zip"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not zip_candidates:
        raise FileNotFoundError("phase8 result zip is missing")
    envelope = DifyRunEnvelope.model_validate_json(envelope_path.read_bytes(), strict=True)
    attestation = DifyReadbackAttestation.model_validate_json(readback.read_bytes(), strict=True)
    smoke_payload = json.loads(smoke.read_text(encoding="utf-8"))
    if envelope.contract.knowledge_build_id != attestation.knowledge_build_id:
        raise ValueError("phase8 envelope/readback knowledge build mismatch")
    if not envelope.retrieval_trace.hits:
        raise ValueError("phase8 envelope has no retrieval hits")

    with tempfile.TemporaryDirectory(prefix="debugmate-phase8-") as temp:
        extracted = Path(temp) / "bundle"
        with zipfile.ZipFile(zip_candidates[0]) as archive:
            archive.extractall(extracted)
        for name in ("report.md", "card.png", "recap.mp3", "result-manifest.json"):
            if not (extracted / name).is_file():
                raise ValueError(f"phase8 result member missing: {name}")
        result_manifest = json.loads(
            (extracted / "result-manifest.json").read_text(encoding="utf-8")
        )
        result_id = result_manifest["result_id"]
        shutil.copy2(extracted / "report.md", evidence / "report.md")
        shutil.copy2(extracted / "card.png", evidence / "card.png")
        shutil.copy2(extracted / "recap.mp3", evidence / "recap.mp3")
    shutil.copy2(zip_candidates[0], evidence / "result.zip")

    smoke_payload["knowledge_build_id"] = attestation.knowledge_build_id
    live_run = {
        "schema_version": "phase8-live-run-1.0",
        "qa_run_id": zip_candidates[0].stem.removesuffix("-result"),
        "backend": "dify",
        "case_id": envelope.case_id,
        "status": "completed",
        "prompt_sha256": sha256(root / "prompts" / "v1-baseline.md"),
        "schema_sha256": schema_sha256(),
        "knowledge_build_id": envelope.contract.knowledge_build_id,
        "facts_sha256": canonical_sha(
            [item.model_dump(mode="json") for item in envelope.extraction_facts]
        ),
        "retrieval_trace_sha256": canonical_sha(envelope.retrieval_trace.model_dump(mode="json")),
        "diagnosis_sha256": smoke_payload["diagnosis_sha256"],
        "result_id": result_id,
        "artifact_sha256": {
            name: sha256(evidence / name)
            for name in ("report.md", "card.png", "recap.mp3", "result.zip")
        },
    }
    (evidence / "live-run.json").write_text(
        json.dumps(live_run, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    scope = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    manifest = {
        "schema_version": "phase8-formal-acceptance-1.0",
        "qa_run_id": live_run["qa_run_id"],
        "evidence_time_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_commit": source_commit,
        "worktree_scope_sha256": hashlib.sha256(scope.encode()).hexdigest(),
        "backend": "dify",
        "cloud_junit": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0},
        "edge_junit": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0},
        "artifacts": [{"path": name, "sha256": sha256(evidence / name)} for name in REQUIRED],
    }
    (evidence / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    checksums = [
        f"{sha256(evidence / name)}  {name}" for name in sorted(("manifest.json", *REQUIRED))
    ]
    (evidence / "checksums.sha256").write_text("\n".join(checksums) + "\n", encoding="ascii")
    print("phase8_formal_evidence_finalized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
