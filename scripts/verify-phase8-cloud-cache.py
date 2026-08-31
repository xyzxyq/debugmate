"""Validate the previously accepted, privacy-safe Phase 8 Dify evidence cache."""

from __future__ import annotations

import json
from pathlib import Path

from debugmate.cloud.contracts import DifyRunEnvelope
from debugmate.knowledge.sync import DifyReadbackAttestation


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    smoke_path = root / ".debugmate-runtime" / "phase8-cloud-smoke" / "live-smoke.json"
    envelope_path = root / ".debugmate-runtime" / "phase8-cloud-smoke" / "run-envelope.json"
    readback_path = root / "evidence" / "dify-live" / "phase8" / "knowledge-readback.json"
    envelope = DifyRunEnvelope.model_validate_json(envelope_path.read_bytes(), strict=True)
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    readback = DifyReadbackAttestation.model_validate_json(readback_path.read_bytes(), strict=True)
    if not envelope.retrieval_trace.hits:
        raise ValueError("cloud evidence has no retrieval hits")
    if not (
        envelope.contract.knowledge_build_id
        == readback.knowledge_build_id
        == smoke.get("knowledge_build_id")
    ):
        raise ValueError("cloud evidence knowledge build mismatch")
    print("verified_cloud_cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
