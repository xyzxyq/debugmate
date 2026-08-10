from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from PIL import Image

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.contracts import DiagnosisRecord, EvidenceAnchor
from debugmate.diagnosis.correction import CorrectionOverlay
from debugmate.diagnosis.extraction import (
    ExtractionRecord,
    FieldId,
    SourceKind,
    TextLocator,
    extraction_id_for,
    make_candidate,
)
from debugmate.diagnosis.generation import GenerationFailed, GenerationIssue, IssueCode
from debugmate.diagnosis.providers import ProductionExtractionProvider
from debugmate.diagnosis.workflow import DiagnosisWorkflow
from debugmate.hashing import sha256_bytes, sha256_file
from debugmate.privacy.approval import ApprovalInvalid, approve_preview
from debugmate.privacy.models import (
    PreviewBundle,
    RedactedFields,
    RedactionAudit,
    ScreenshotOcrStatus,
    ScreenshotPreviewAudit,
)
from debugmate.privacy.ocr import OcrToken

KEY = b"k" * 32
ALL_STAGES = [
    "input_approved",
    "extracted",
    "facts_confirmed",
    "provisional_routed",
    "sufficiency_checked",
    "final_routed",
    "retrieved",
    "generated",
    "validated",
    "published",
]


def _approved(
    case_id: str,
    *,
    key: bytes = KEY,
    when: datetime | None = None,
    screenshot: Path | None = None,
    root: Path | None = None,
    environment: dict[str, str] | None = None,
):
    redacted = RedactedFields(error_text="fixture", environment=environment or {})
    if screenshot is not None:
        assert root is not None
        redacted = RedactedFields(
            error_text="fixture",
            redacted_screenshot_path=screenshot.relative_to(root).as_posix(),
            redacted_screenshot_sha256=sha256_file(screenshot),
        )
    preview = PreviewBundle(
        case_id=case_id,
        redacted=redacted,
        candidates=[],
        audit=RedactionAudit(candidate_count=0, counts_by_kind={}),
        screenshot_audit=ScreenshotPreviewAudit(
            provided=screenshot is not None,
            ocr_status=(
                ScreenshotOcrStatus.COMPLETED
                if screenshot is not None
                else ScreenshotOcrStatus.NOT_APPLICABLE
            ),
            finding_count=0,
            counts_by_kind={},
        ),
        source_hash="1" * 64,
        preview_hash="2" * 64,
        rule_version="test",
        created_at_utc=datetime.now(UTC),
    )
    return approve_preview(preview, key, approved_at_utc=when)


def _record(case_id: str, values: dict[str, str]) -> ExtractionRecord:
    candidates = []
    cursor = 0
    for raw_field, value in values.items():
        field_id = FieldId(raw_field)
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
    hashes = {"error_text": sha256_bytes(b"fixture")}
    return ExtractionRecord(
        case_id=case_id,
        extraction_id=extraction_id_for(case_id, hashes, candidates),
        source_hashes=hashes,
        candidates=candidates,
    )


@dataclass
class ExtractionSpy:
    record: ExtractionRecord
    calls: list[object] = field(default_factory=list)

    def extract(self, approved):
        self.calls.append(approved)
        return self.record


@dataclass
class RetrievalSpy:
    calls: list[object] = field(default_factory=list)
    knowledge_build_id: str = "3" * 64

    def retrieve(self, facts, routing):
        self.calls.append((facts, routing))
        return [
            EvidenceAnchor(
                evidence_id="evidence_" + "4" * 32,
                chunk_id="fixture:1",
                content_summary="Official fictional fixture guidance.",
                source_id="python-docs",
                source_url="https://docs.python.org/3/",
                locator="fixture",
                relevance_score=0.9,
                knowledge_build_id=self.knowledge_build_id,
            )
        ]


@dataclass
class GeneratorSpy:
    fail: bool = False
    calls: list[object] = field(default_factory=list)
    backend_name: str = "fixture"

    def generate(self, request):
        self.calls.append(request)
        if self.fail:
            return GenerationFailed(
                issues=[GenerationIssue(code=IssueCode.SCHEMA_INVALID, pointer="/recap_text")],
                generation_attempts=2,
                completed_stages=["candidate_received", "local_validation"],
                run_ids=["fixture:1", "fixture:2"],
            )
        facts = request.observed_facts
        payload = json.loads(
            Path("fixtures/cases/module_not_found/diagnosis.json").read_text(encoding="utf-8")
        )
        payload.update(
            case_id=request.case_id,
            category=request.routing.category.value,
            observed_facts=[f.model_dump(mode="json") for f in facts],
            evidence=[e.model_dump(mode="json") for e in request.evidence],
            support_links=[],
            root_cause_candidates=[],
        )
        return type(
            "Completed",
            (),
            {
                "status": "completed",
                "diagnosis": DiagnosisRecord.model_validate(payload),
                "generation_attempts": 1,
                "run_ids": ["fixture:1"],
            },
        )()


def _workflow(
    row: dict[str, object],
    root: Path,
    *,
    key: bytes | None = KEY,
    execution_backend: ExecutionBackend = ExecutionBackend.LOCAL_FALLBACK,
):
    extraction = ExtractionSpy(_record(str(row["case_id"]), row["facts"]))
    retrieval = RetrievalSpy()
    generator = GeneratorSpy(fail=row.get("expected_status") == "generation_failed")
    workflow = DiagnosisWorkflow(
        extraction_provider=extraction,
        retrieval_provider=retrieval,
        generator=generator,
        execution_backend=execution_backend,
        approval_key=key,
        redacted_root=root,
    )
    return workflow, extraction, retrieval, generator


def _rows() -> list[dict[str, object]]:
    matrix = json.loads(
        Path("tests/fixtures/diagnosis/workflow_cases.json").read_text(encoding="utf-8")
    )
    assert matrix["schema_version"] == "1.0.0"
    primary = json.loads(
        Path("fixtures/cases/module_not_found/candidates.json").read_text(encoding="utf-8")
    )
    return [primary, *matrix["cases"]]


@pytest.mark.parametrize("row", _rows(), ids=lambda row: row["case_key"])
def test_versioned_workflow_matrix(row: dict[str, object], tmp_path: Path) -> None:
    workflow, extraction, retrieval, generator = _workflow(row, tmp_path)
    answers = {FieldId(k): v for k, v in row.get("answers", {}).items()}
    outcome = workflow.run(_approved(str(row["case_id"])), followup_answers=answers or None)
    assert outcome.status == row["expected_status"]
    assert outcome.routing.category.value == row["expected_category"]
    assert outcome.completed_stages == ALL_STAGES[: len(outcome.completed_stages)]
    assert len(extraction.calls) == 1
    if outcome.status == "needs_information":
        assert len(outcome.questions) <= 3
        assert not retrieval.calls and not generator.calls
    if outcome.status == "insufficient_information":
        assert not retrieval.calls and not generator.calls


def test_all_seven_routes_have_exactly_one_primary_matrix_case() -> None:
    completed_route_rows = [
        row
        for row in _rows()
        if row["case_key"]
        in {
            "module_not_found",
            "path_permission",
            "python_runtime",
            "tensor_shape_dtype",
            "cuda_memory",
            "model_loading",
            "unknown",
        }
    ]
    assert [row["expected_category"] for row in completed_route_rows] == [
        "dependency_environment",
        "path_permission",
        "python_runtime",
        "tensor_shape_dtype",
        "cuda_memory",
        "model_loading",
        "unknown",
    ]


@pytest.mark.parametrize("failure", ["forged", "stale", "wrong_key", "missing_key"])
def test_untrusted_approval_calls_no_provider(failure: str, tmp_path: Path) -> None:
    row = _rows()[0]
    workflow, extraction, retrieval, generator = _workflow(
        row, tmp_path, key=None if failure == "missing_key" else KEY
    )
    when = datetime.now(UTC) - timedelta(hours=1) if failure == "stale" else None
    approved = _approved(
        str(row["case_id"]), key=b"w" * 32 if failure == "wrong_key" else KEY, when=when
    )
    if failure == "forged":
        approved = approved.model_copy(update={"approval_signature": "f" * 64})
    with pytest.raises((ApprovalInvalid, ValueError)):
        workflow.run(approved)
    assert not extraction.calls and not retrieval.calls and not generator.calls


@pytest.mark.parametrize("failure", ["missing", "changed"])
def test_screenshot_failure_calls_no_provider(failure: str, tmp_path: Path) -> None:
    screenshot = tmp_path / "redacted.png"
    screenshot.write_bytes(b"original")
    approved = _approved(_rows()[0]["case_id"], screenshot=screenshot, root=tmp_path)
    if failure == "missing":
        screenshot.unlink()
    else:
        screenshot.write_bytes(b"changed")
    workflow, extraction, retrieval, generator = _workflow(_rows()[0], tmp_path)
    with pytest.raises(ApprovalInvalid):
        workflow.run(approved)
    assert not extraction.calls and not retrieval.calls and not generator.calls


def test_unsafe_screenshot_path_calls_no_provider(tmp_path: Path) -> None:
    approved = _approved(_rows()[0]["case_id"])
    unsafe = RedactedFields.model_construct(
        error_text="fixture",
        code=None,
        environment={},
        redacted_screenshot_path="../escape.png",
        redacted_screenshot_sha256="1" * 64,
    )
    preview = PreviewBundle.model_construct(
        case_id=approved.case_id,
        redacted=unsafe,
        candidates=[],
        audit=RedactionAudit(candidate_count=0, counts_by_kind={}),
        source_hash="1" * 64,
        preview_hash="2" * 64,
        rule_version="test",
        created_at_utc=datetime.now(UTC),
    )
    approved = approve_preview(preview, KEY)
    workflow, extraction, retrieval, generator = _workflow(_rows()[0], tmp_path)
    with pytest.raises(ApprovalInvalid):
        workflow.run(approved)
    assert not extraction.calls and not retrieval.calls and not generator.calls


def test_valid_screenshot_is_root_confined_and_rehashed_before_ocr(tmp_path: Path) -> None:
    screenshot = tmp_path / "nested" / "redacted.png"
    screenshot.parent.mkdir()
    Image.new("RGB", (8, 8), "white").save(screenshot)

    @dataclass
    class OcrSpy:
        paths: list[Path] = field(default_factory=list)

        def recognize(self, path: Path) -> list[OcrToken]:
            self.paths.append(path)
            return []

    ocr = OcrSpy()
    extractor = ProductionExtractionProvider(redacted_root=tmp_path, ocr_backend=ocr)
    retrieval = RetrievalSpy()
    generator = GeneratorSpy()
    workflow = DiagnosisWorkflow(
        extraction_provider=extractor,
        retrieval_provider=retrieval,
        generator=generator,
        execution_backend=ExecutionBackend.LOCAL_FALLBACK,
        approval_key=KEY,
        redacted_root=tmp_path,
    )
    approved = _approved(_rows()[0]["case_id"], screenshot=screenshot, root=tmp_path)
    outcome = workflow.run(approved)
    assert outcome.status == "needs_information"
    assert ocr.paths == [screenshot.resolve()]


def test_environment_only_facts_change_workflow_run_identity(tmp_path: Path) -> None:
    @dataclass
    class EmptyOcr:
        def recognize(self, path: Path) -> list[OcrToken]:
            return []

    extractor = ProductionExtractionProvider(redacted_root=tmp_path, ocr_backend=EmptyOcr())
    workflow = DiagnosisWorkflow(
        extraction_provider=extractor,
        retrieval_provider=RetrievalSpy(),
        generator=GeneratorSpy(),
        execution_backend=ExecutionBackend.LOCAL_FALLBACK,
        approval_key=KEY,
        redacted_root=tmp_path,
    )
    case_id = "case_eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    first = workflow.run(
        _approved(case_id, environment={"runtime": "Version: 3.13.5\nDevice: cpu"})
    )
    second = workflow.run(
        _approved(case_id, environment={"runtime": "Version: 3.13.6\nDevice: cpu"})
    )

    assert first.extraction is not None and second.extraction is not None
    assert set(first.extraction.source_hashes) == {"environment", "error_text"}
    assert {fact.field_id for fact in first.facts.facts} >= {
        FieldId.VERSION,
        FieldId.DEVICE,
    }
    assert first.facts_sha256 != second.facts_sha256
    assert first.idempotency_key != second.idempotency_key
    assert first.run_id != second.run_id


def test_correction_rerun_is_immutable_and_revision_bound(tmp_path: Path) -> None:
    row = next(row for row in _rows() if row["case_key"] == "correction_rerun")
    workflow, *_ = _workflow(row, tmp_path)
    original = workflow.run(_approved(row["case_id"]))
    original_bytes = original.model_dump_json().encode()
    target = next(f for f in original.facts.facts if f.field_id is FieldId.EXCEPTION_TYPE)
    overlay = CorrectionOverlay(
        case_id=original.case_id,
        base_revision=original.revision,
        base_facts_sha256=original.facts_sha256,
        field_id=target.field_id,
        fact_id=target.fact_id,
        old_value_sha256=sha256_bytes(target.value.encode()),
        replacement="AttributeError",
        reason="confirmed from redacted traceback",
    )
    with pytest.raises(ValueError, match="revision"):
        workflow.rerun(original.model_copy(update={"revision": 999}), overlay)
    with pytest.raises(ValueError, match="facts hash"):
        workflow.rerun(original.model_copy(update={"facts_sha256": "f" * 64}), overlay)
    rerun = workflow.rerun(original, overlay)
    assert rerun.case_id == original.case_id
    assert rerun.revision == original.revision + 1
    assert rerun.facts_sha256 != original.facts_sha256
    assert rerun.idempotency_key != original.idempotency_key
    assert rerun.run_id != original.run_id
    assert rerun.source_run_id == original.run_id
    assert rerun.inherited_stages == ["input_approved", "extracted", "facts_confirmed"]
    assert rerun.completed_stages[0] == "facts_corrected"
    assert "extracted" not in rerun.completed_stages
    assert original.model_dump_json().encode() == original_bytes


def test_rerun_validates_new_outcome_before_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    row = next(row for row in _rows() if row["case_key"] == "correction_rerun")
    workflow, *_ = _workflow(row, tmp_path)
    original = workflow.run(_approved(row["case_id"]))
    target = next(f for f in original.facts.facts if f.field_id is FieldId.EXCEPTION_TYPE)
    overlay = CorrectionOverlay(
        case_id=original.case_id,
        base_revision=original.revision,
        base_facts_sha256=original.facts_sha256,
        field_id=target.field_id,
        fact_id=target.fact_id,
        old_value_sha256=sha256_bytes(target.value.encode()),
        replacement="AttributeError",
        reason="confirmed from redacted traceback",
    )
    import debugmate.diagnosis.workflow as workflow_module

    real_validator = workflow_module.validate_diagnosis_outcome
    calls = 0

    def fail_on_new_outcome(outcome):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("new outcome contract mismatch")
        return real_validator(outcome)

    monkeypatch.setattr(workflow_module, "validate_diagnosis_outcome", fail_on_new_outcome)

    with pytest.raises(ValueError, match="new outcome contract mismatch"):
        workflow.rerun(original, overlay)
    assert calls == 2
