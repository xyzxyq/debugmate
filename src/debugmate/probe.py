"""Truthful seven-capability Phase 1 probe orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from debugmate.adapters.base import CandidateBackend, CandidateRunResult
from debugmate.adapters.dify import (
    DifyAuthError,
    DifyBackend,
    DifyContractError,
    DifyNotConfigured,
    DifyQuotaError,
    DifyTransportError,
)
from debugmate.adapters.fixture import FixtureBackend
from debugmate.contracts import CapabilityStatus, DiagnosisRecord, new_case_id
from debugmate.diagnosis.generation import DiagnosisGenerator, GenerationRequest
from debugmate.diagnosis.routing import DecisionStage, RoutingDecision
from debugmate.evidence import (
    MANIFEST_VERSION,
    ArtifactEntry,
    CapabilityEvidence,
    EvidenceBundle,
    RunManifest,
    RunStatus,
)
from debugmate.hashing import artifact_metadata, canonical_json_bytes, sha256_bytes, sha256_file
from debugmate.settings import DebugMateSettings

CAPABILITY_IDS = ("C01", "C02", "C03", "C04", "C05", "C06", "C07")
CAPABILITY_DESCRIPTIONS = {
    "C01": "Authentication/API",
    "C02": "File upload",
    "C03": "Vision extraction",
    "C04": "Knowledge retrieval",
    "C05": "Structured DiagnosisRecord JSON",
    "C06": "DSL export/import",
    "C07": "TTS MP3",
}


class ProbeCapability(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    capability_id: str
    description: str
    status: CapabilityStatus
    evidence_path: str | None = None
    sha256: str | None = None


class ProbeReport(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    report_version: str = "1.0.0"
    case_id: str
    backend: str
    generated_at_utc: datetime
    capabilities: list[ProbeCapability]


@dataclass(frozen=True, slots=True)
class ProbeOutcome:
    case_id: str
    bundle_path: Path
    report: ProbeReport
    exit_code: int


def _capabilities(status: CapabilityStatus) -> list[ProbeCapability]:
    return [
        ProbeCapability(
            capability_id=capability_id,
            description=CAPABILITY_DESCRIPTIONS[capability_id],
            status=status,
        )
        for capability_id in CAPABILITY_IDS
    ]


def _manifest(
    *,
    case_id: str,
    backend: str,
    status: RunStatus,
    input_sha256: str,
    run_id: str,
    started: datetime,
    capabilities: list[ProbeCapability],
    artifacts: list[ArtifactEntry] | None = None,
) -> RunManifest:
    now = datetime.now(UTC)
    return RunManifest(
        manifest_version=MANIFEST_VERSION,
        case_id=case_id,
        status=status,
        created_at_utc=started,
        completed_at_utc=now,
        backend=backend,
        workflow_version="phase1-probe-v1",
        prompt_version="fixture-v1" if backend == "fixture" else "dify-configured",
        schema_version="1.0.0",
        knowledge_version="phase1-probe",
        input_sha256=input_sha256,
        run_id=run_id,
        node_states={item.capability_id: item.status.value for item in capabilities},
        latency_ms=max(0, int((now - started).total_seconds() * 1000)),
        token_usage={},
        estimated_cost=0.0,
        artifacts=artifacts or [],
        probe_capabilities=[
            CapabilityEvidence(
                capability_id=item.capability_id,
                status=item.status,
                evidence_path=item.evidence_path,
                sha256=item.sha256,
            )
            for item in capabilities
        ],
        error_code="E_DIFY_PROBE" if status is RunStatus.FAILED else None,
        safe_message=(
            "Dify capability probe failed contract or transport validation"
            if status is RunStatus.FAILED
            else None
        ),
    )


def _fixture_root() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "cases"


def _probe_generation_request(case_id: str) -> GenerationRequest:
    payload = json.loads(
        (_fixture_root() / "module_not_found" / "diagnosis.json").read_text(encoding="utf-8")
    )
    payload["case_id"] = case_id
    expected = DiagnosisRecord.model_validate_json(json.dumps(payload), strict=True)
    return GenerationRequest(
        case_id=expected.case_id,
        observed_facts=expected.observed_facts,
        evidence=expected.evidence,
        routing=RoutingDecision(
            decision_stage=DecisionStage.FINAL,
            rule_version="phase1-probe-expected-v1",
            category=expected.category,
            candidates=[],
            reason="committed synthetic probe fixture",
        ),
        knowledge_build_id=expected.evidence[0].knowledge_build_id,
        schema_version="1.1.0",
        prompt_version="fixture-v1",
    )


def _validated_probe_diagnosis(
    backend: CandidateBackend,
    candidate: CandidateRunResult,
    request: GenerationRequest,
) -> DiagnosisRecord:
    outcome = DiagnosisGenerator(backend).generate(
        request,
        initial_candidate=candidate,
    )
    if outcome.status != "completed":
        raise DifyContractError("candidate failed local diagnosis validation")
    return outcome.diagnosis


def run_fixture_probe(output_root: Path) -> ProbeOutcome:
    started = datetime.now(UTC)
    case_id = new_case_id()
    fixture_root = _fixture_root()
    input_payload = json.loads(
        (fixture_root / "module_not_found" / "input.json").read_text(encoding="utf-8")
    )
    backend = FixtureBackend(fixture_root)
    request = _probe_generation_request(case_id)
    candidate = backend.run_workflow({"case_id": case_id}, user="debugmate-local")
    diagnosis = _validated_probe_diagnosis(backend, candidate, request)
    capabilities = _capabilities(CapabilityStatus.NOT_TESTED)
    report = ProbeReport(
        case_id=case_id,
        backend="fixture",
        generated_at_utc=datetime.now(UTC),
        capabilities=capabilities,
    )

    bundle = EvidenceBundle.begin(output_root, case_id)
    bundle.write_json("input.redacted.json", input_payload)
    bundle.write_json("diagnosis.json", diagnosis.model_dump(mode="json"))
    bundle.write_json("probe-results.json", report.model_dump(mode="json"))
    initial_artifacts = [
        ArtifactEntry.model_validate(
            artifact_metadata(bundle.temp_path, Path(path), "application/json")
        )
        for path in (
            "input.redacted.json",
            "dify-upload.json",
            "diagnosis.json",
            "recap.json",
            "probe-results.json",
        )
        if (bundle.temp_path / path).is_file()
    ]
    final = bundle.finalize(
        _manifest(
            case_id=case_id,
            backend="fixture",
            status=RunStatus.PASSED,
            input_sha256=sha256_bytes(canonical_json_bytes(input_payload)),
            run_id=candidate.run_id,
            started=started,
            capabilities=capabilities,
            artifacts=initial_artifacts,
        )
    )
    return ProbeOutcome(case_id=case_id, bundle_path=final, report=report, exit_code=0)


def run_cloud_probe(settings: DebugMateSettings, output_root: Path) -> ProbeOutcome:
    started = datetime.now(UTC)
    case_id = new_case_id()
    input_path = _fixture_root() / "module_not_found" / "input.json"
    input_payload = json.loads(input_path.read_text(encoding="utf-8"))

    if not settings.cloud_configured:
        capabilities = _capabilities(CapabilityStatus.BLOCKED)
        report = ProbeReport(
            case_id=case_id,
            backend="dify",
            generated_at_utc=datetime.now(UTC),
            capabilities=capabilities,
        )
        bundle = EvidenceBundle.begin(output_root, case_id)
        bundle.write_json("input.redacted.json", input_payload)
        bundle.write_json("probe-results.json", report.model_dump(mode="json"))
        final = bundle.finalize(
            _manifest(
                case_id=case_id,
                backend="dify",
                status=RunStatus.BLOCKED,
                input_sha256=sha256_bytes(canonical_json_bytes(input_payload)),
                run_id="blocked:not-configured",
                started=started,
                capabilities=capabilities,
            )
        )
        return ProbeOutcome(case_id, final, report, 2)

    backend = DifyBackend(settings)
    bundle = EvidenceBundle.begin(output_root, case_id)
    bundle.write_json("input.redacted.json", input_payload)
    capability_statuses = {
        capability_id: CapabilityStatus.NOT_TESTED for capability_id in CAPABILITY_IDS
    }
    evidence: dict[str, Path] = {}
    try:
        upload = backend.upload_file(input_path, settings.dify_user)
        upload_path = bundle.write_json(
            "dify-upload.json",
            {"file_id": upload.file_id, "filename": upload.filename, "backend": upload.backend},
        )
        evidence.update({"C01": upload_path, "C02": upload_path})
        capability_statuses.update({"C01": CapabilityStatus.PASS, "C02": CapabilityStatus.PASS})
        request = _probe_generation_request(case_id)
        workflow = backend.run_workflow(
            {
                "case_id": case_id,
                "file_id": upload.file_id,
                "generation_request": request.model_dump(mode="json"),
            },
            settings.dify_user,
        )
        diagnosis = _validated_probe_diagnosis(backend, workflow, request)
        diagnosis_path = bundle.write_json("diagnosis.json", diagnosis.model_dump(mode="json"))

        # Phase 2 stores only the scanned source text. Audio generation remains
        # deferred until Phase 4 can prove semantic derivation and media safety.
        bundle.write_json("recap.json", {"recap_text": diagnosis.recap_text})
        evidence["C05"] = diagnosis_path
        capability_statuses["C05"] = CapabilityStatus.PASS
        run_status = RunStatus.PASSED
        exit_code = 0
        run_id = workflow.run_id
    except (DifyNotConfigured, DifyAuthError, DifyQuotaError) as error:
        del error
        if evidence:
            capability_statuses["C05"] = CapabilityStatus.BLOCKED
        else:
            capability_statuses = {
                capability_id: CapabilityStatus.BLOCKED for capability_id in CAPABILITY_IDS
            }
        run_status = RunStatus.BLOCKED
        exit_code = 2
        run_id = "blocked:dify"
    except (DifyTransportError, DifyContractError):
        if evidence:
            capability_statuses["C05"] = CapabilityStatus.FAIL
        else:
            capability_statuses.update({"C01": CapabilityStatus.FAIL, "C02": CapabilityStatus.FAIL})
        run_status = RunStatus.FAILED
        exit_code = 1
        run_id = "failed:dify"

    capabilities = []
    for capability_id in CAPABILITY_IDS:
        path = evidence.get(capability_id)
        capabilities.append(
            ProbeCapability(
                capability_id=capability_id,
                description=CAPABILITY_DESCRIPTIONS[capability_id],
                status=capability_statuses[capability_id],
                evidence_path=(path.relative_to(bundle.temp_path).as_posix() if path else None),
                sha256=(sha256_file(path) if path else None),
            )
        )

    report = ProbeReport(
        case_id=case_id,
        backend="dify",
        generated_at_utc=datetime.now(UTC),
        capabilities=capabilities,
    )
    bundle.write_json("probe-results.json", report.model_dump(mode="json"))
    initial_artifacts = [
        ArtifactEntry.model_validate(
            artifact_metadata(bundle.temp_path, Path(path), "application/json")
        )
        for path in (
            "input.redacted.json",
            "dify-upload.json",
            "diagnosis.json",
            "recap.json",
            "probe-results.json",
        )
        if (bundle.temp_path / path).is_file()
    ]
    final = bundle.finalize(
        _manifest(
            case_id=case_id,
            backend="dify",
            status=run_status,
            input_sha256=sha256_bytes(canonical_json_bytes(input_payload)),
            run_id=run_id,
            started=started,
            capabilities=capabilities,
            artifacts=initial_artifacts,
        )
    )
    return ProbeOutcome(case_id, final, report, exit_code)
