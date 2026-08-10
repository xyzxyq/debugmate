from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from debugmate.adapters.base import CandidateRunResult
from debugmate.adapters.dify import DifyAmbiguousTransportError
from debugmate.cloud.contracts import DifyRunEnvelope, ReceiptStatus
from debugmate.cloud.receipts import DifyReceiptStore
from debugmate.cloud.workflow import CloudWorkflowError, DifyLiveWorkflow
from debugmate.contracts import DiagnosisRecord
from debugmate.diagnosis.evidence_binding import bind_retrieval_evidence
from debugmate.diagnosis.extraction import (
    FieldId,
    SourceKind,
    TextLocator,
    build_case_facts,
    extraction_id_for,
    make_candidate,
    ExtractionRecord,
)
from debugmate.diagnosis.workflow import validate_diagnosis_outcome
from debugmate.hashing import sha256_bytes
from debugmate.knowledge.retrieval import RetrievalHit, RetrievalTrace
from debugmate.knowledge.sync import DifyReadbackAttestation, DifySyncConfig
from debugmate.privacy.approval import approve_preview
from debugmate.privacy.models import (
    PreviewBundle,
    RedactedFields,
    RedactionAudit,
    ScreenshotOcrStatus,
    ScreenshotPreviewAudit,
)

KEY = b"k" * 32
CASE_ID = "case_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
BUILD_ID = "3" * 64
NOW = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)


def _approved():
    preview = PreviewBundle(
        case_id=CASE_ID,
        redacted=RedactedFields(
            error_text="ModuleNotFoundError: No module named demo_missing_pkg"
        ),
        candidates=[],
        audit=RedactionAudit(candidate_count=0, counts_by_kind={}),
        screenshot_audit=ScreenshotPreviewAudit(
            provided=False,
            ocr_status=ScreenshotOcrStatus.NOT_APPLICABLE,
            finding_count=0,
            counts_by_kind={},
        ),
        source_hash="1" * 64,
        preview_hash="2" * 64,
        rule_version="test",
        created_at_utc=NOW,
    )
    return approve_preview(preview, KEY, approved_at_utc=NOW)


def _facts():
    values = {
        FieldId.EXCEPTION_TYPE: "ModuleNotFoundError",
        FieldId.TRACEBACK_KEY_LINE: "ModuleNotFoundError: No module named demo_missing_pkg",
        FieldId.PACKAGE: "demo_missing_pkg",
        FieldId.VERSION: "3.13.5",
    }
    candidates = []
    cursor = 0
    for field_id, value in values.items():
        locator = TextLocator(input_field="error_text", start=cursor, end=cursor + len(value))
        candidates.append(
            make_candidate(
                field_id=field_id,
                value=value,
                source_kind=SourceKind.TEXT,
                confidence=1.0,
                locator=locator,
            )
        )
        cursor += len(value) + 1
    candidates.sort(key=lambda item: item.candidate_id)
    hashes = {"provider_facts": sha256_bytes(b"provider-facts")}
    extraction = ExtractionRecord(
        case_id=CASE_ID,
        extraction_id=extraction_id_for(CASE_ID, hashes, candidates),
        source_hashes=hashes,
        candidates=candidates,
    )
    return build_case_facts(extraction)


def _manifest() -> dict[str, object]:
    sources = []
    notes = []
    for index in range(17):
        source_id = "python-exceptions" if index == 0 else f"source-{index:02d}"
        sources.append(
            {
                "source_id": source_id,
                "url": f"https://example.com/{source_id}",
                "retrieved_at": "2026-08-10T00:00:00Z",
            }
        )
        notes.append(
            {
                "source_id": source_id,
                "locators": ["ModuleNotFoundError" if index == 0 else "Reference"],
            }
        )
    return {"build_id": BUILD_ID, "sources": sources, "notes": notes}


def _attestation() -> DifyReadbackAttestation:
    return DifyReadbackAttestation(
        knowledge_build_id=BUILD_ID,
        dataset_fingerprint="4" * 64,
        document_count=17,
        document_fingerprints=[f"{index + 1:064x}" for index in range(17)],
        config=DifySyncConfig(
            indexing_technique="high_quality",
            process_rule_mode="custom",
            chunk_separator="\\n\\n",
            max_tokens=500,
            chunk_overlap=50,
            retrieval_method="semantic_search",
            top_k=4,
            score_threshold_enabled=True,
            score_threshold=0.5,
        ),
        response_hashes=["5" * 64],
    )


def _envelope() -> DifyRunEnvelope:
    facts = _facts()
    observed = [
        {
            "fact_id": fact.fact_id,
            "field_id": fact.field_id.value,
            "value": fact.value,
            "source_kind": "text",
            "confidence": fact.confidence,
            "locator": f"fact:{fact.fact_id}",
        }
        for fact in facts.facts
    ]
    local_trace = RetrievalTrace(
        case_id=CASE_ID,
        query_sha256="6" * 64,
        knowledge_build_id=BUILD_ID,
        retrieved_at_utc=NOW,
        hits=[
            RetrievalHit(
                chunk_id="7" * 64,
                content_summary="The requested module could not be located.",
                source_id="python-exceptions",
                source_url="https://example.com/python-exceptions",
                locator="ModuleNotFoundError",
                relevance_score=0.95,
            )
        ],
    )
    evidence = bind_retrieval_evidence(
        local_trace,
        case_id=CASE_ID,
        expected_build_id=BUILD_ID,
        build_manifest=_manifest(),
    )
    payload = json.loads(Path("fixtures/cases/module_not_found/diagnosis.json").read_text("utf-8"))
    payload.update(
        case_id=CASE_ID,
        observed_facts=observed,
        evidence=[item.model_dump(mode="json") for item in evidence],
        support_links=[],
        root_cause_candidates=[],
    )
    diagnosis = DiagnosisRecord.model_validate(payload)
    return DifyRunEnvelope(
        envelope_version="1.0.0",
        case_id=CASE_ID,
        diagnosis=diagnosis,
        extraction_facts=diagnosis.observed_facts,
        retrieval_trace={
            "knowledge_build_id": BUILD_ID,
            "run_fingerprint": "8" * 64,
            "node_fingerprint": "9" * 64,
            "hits": [
                {
                    "chunk_fingerprint": "7" * 64,
                    "source_id": "python-exceptions",
                    "source_title": "Python Exceptions",
                    "source_url": "https://example.com/python-exceptions",
                    "locator": "ModuleNotFoundError",
                    "content_summary": "The requested module could not be located.",
                    "relevance_score": 0.95,
                }
            ],
        },
        contract={
            "schema_version": "1.1.0",
            "prompt_version": "diagnosis-v1",
            "knowledge_build_id": BUILD_ID,
            "dsl_semantic_sha256": "a" * 64,
        },
    )


@dataclass
class GatewaySpy:
    envelope: DifyRunEnvelope
    receipt_store: DifyReceiptStore
    calls: list[object] = field(default_factory=list)

    def verify(self, approved) -> None:
        self.calls.append("verify")

    def run(self, approved) -> CandidateRunResult:
        receipt_files = list(self.receipt_store._root.glob("*.json"))
        assert len(receipt_files) == 1
        receipt = self.receipt_store.read(receipt_files[0].stem)
        assert receipt.status is ReceiptStatus.STARTED
        self.calls.append("workflow")
        return CandidateRunResult(
            run_id="run_" + "b" * 32,
            backend="dify",
            candidate_payload=self.envelope.diagnosis.model_dump(mode="json"),
            run_envelope=self.envelope,
        )

    def repair(self, inputs: dict[str, object]) -> CandidateRunResult:
        self.calls.append(("repair", inputs))
        return self.run(_approved())


def _workflow(tmp_path: Path, gateway) -> DifyLiveWorkflow:
    return DifyLiveWorkflow(
        gateway=gateway,
        receipt_store=gateway.receipt_store,
        approval_key=KEY,
        build_manifest=_manifest(),
        readback_attestation=_attestation(),
        clock=lambda: NOW,
    )


def test_started_receipt_precedes_dispatch_and_success_is_strict(tmp_path: Path) -> None:
    store = DifyReceiptStore((tmp_path / "receipts").resolve())
    gateway = GatewaySpy(_envelope(), store)

    outcome = _workflow(tmp_path, gateway).run(_approved())

    validate_diagnosis_outcome(outcome)
    assert outcome.execution_backend == "dify"
    assert gateway.calls == ["verify", "workflow"]
    receipt = store.read(next((tmp_path / "receipts").glob("*.json")).stem)
    assert receipt.status is ReceiptStatus.SUCCEEDED
    assert receipt.accepted_result_id == outcome.run_id
    serialized = receipt.model_dump_json()
    assert "raw" not in serialized and "remote" not in serialized


def test_stale_build_fails_terminally_and_same_approval_cannot_dispatch_again(
    tmp_path: Path,
) -> None:
    store = DifyReceiptStore((tmp_path / "receipts").resolve())
    stale = _envelope().model_copy(
        update={
            "contract": _envelope().contract.model_copy(
                update={"knowledge_build_id": "f" * 64}
            )
        }
    )
    gateway = GatewaySpy(stale, store)
    workflow = _workflow(tmp_path, gateway)

    with pytest.raises(CloudWorkflowError, match="knowledge_readback"):
        workflow.run(_approved())
    with pytest.raises(CloudWorkflowError, match="duplicate"):
        workflow.run(_approved())

    assert gateway.calls.count("workflow") == 1
    receipt = store.read(next((tmp_path / "receipts").glob("*.json")).stem)
    assert receipt.status is ReceiptStatus.FAILED


def test_ambiguous_workflow_timeout_is_uncertain_and_never_replayed(tmp_path: Path) -> None:
    store = DifyReceiptStore((tmp_path / "receipts").resolve())

    @dataclass
    class AmbiguousGateway(GatewaySpy):
        def run(self, approved):
            receipt_files = list(self.receipt_store._root.glob("*.json"))
            assert self.receipt_store.read(receipt_files[0].stem).status is ReceiptStatus.STARTED
            self.calls.append("workflow")
            raise DifyAmbiguousTransportError()

    gateway = AmbiguousGateway(_envelope(), store)
    workflow = _workflow(tmp_path, gateway)

    with pytest.raises(CloudWorkflowError, match="ambiguous_timeout"):
        workflow.run(_approved())
    with pytest.raises(CloudWorkflowError, match="duplicate"):
        workflow.run(_approved())

    assert gateway.calls.count("workflow") == 1
    receipt = store.read(next((tmp_path / "receipts").glob("*.json")).stem)
    assert receipt.status is ReceiptStatus.UNCERTAIN
