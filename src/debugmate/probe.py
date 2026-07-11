"""Truthful seven-capability Phase 1 probe orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from debugmate.adapters.dify import (
    DifyAuthError,
    DifyBackend,
    DifyContractError,
    DifyNotConfigured,
    DifyQuotaError,
    DifyTransportError,
)
from debugmate.adapters.fixture import FixtureBackend
from debugmate.contracts import CapabilityStatus, new_case_id
from debugmate.evidence import (
    MANIFEST_VERSION,
    CapabilityEvidence,
    EvidenceBundle,
    RunManifest,
    RunStatus,
)
from debugmate.hashing import canonical_json_bytes, sha256_bytes, sha256_file
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
        artifacts=[],
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


def run_fixture_probe(output_root: Path) -> ProbeOutcome:
    started = datetime.now(UTC)
    case_id = new_case_id()
    fixture_root = _fixture_root()
    input_payload = json.loads(
        (fixture_root / "module_not_found" / "input.json").read_text(encoding="utf-8")
    )
    diagnosis = FixtureBackend(fixture_root).run_workflow(
        {"case_id": case_id}, user="debugmate-local"
    )
    capabilities = _capabilities(CapabilityStatus.NOT_TESTED)
    report = ProbeReport(
        case_id=case_id,
        backend="fixture",
        generated_at_utc=datetime.now(UTC),
        capabilities=capabilities,
    )

    bundle = EvidenceBundle.begin(output_root, case_id)
    bundle.write_json("input.redacted.json", input_payload)
    bundle.write_json("diagnosis.json", diagnosis.diagnosis.model_dump(mode="json"))
    bundle.write_json("probe-results.json", report.model_dump(mode="json"))
    final = bundle.finalize(
        _manifest(
            case_id=case_id,
            backend="fixture",
            status=RunStatus.PASSED,
            input_sha256=sha256_bytes(canonical_json_bytes(input_payload)),
            run_id=diagnosis.run_id,
            started=started,
            capabilities=capabilities,
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
    try:
        upload = backend.upload_file(input_path, settings.dify_user)
        upload_path = bundle.write_json(
            "dify-upload.json",
            {"file_id": upload.file_id, "filename": upload.filename, "backend": upload.backend},
        )
        workflow = backend.run_workflow(
            {"case_id": case_id, "file_id": upload.file_id}, settings.dify_user
        )
        diagnosis_path = bundle.write_json(
            "diagnosis.json", workflow.diagnosis.model_dump(mode="json")
        )

        def generate_audio(recap_text: str) -> tuple[bytes, str]:
            audio = backend.synthesize_audio(recap_text, settings.dify_user)
            return audio.audio, audio.mime_type

        audio_path = bundle.write_generated_audio(
            "recap.mp3", workflow.diagnosis.recap_text, generate_audio
        )
        evidence = {
            "C01": upload_path,
            "C02": upload_path,
            "C05": diagnosis_path,
            "C07": audio_path,
        }
        capabilities = []
        for capability_id in CAPABILITY_IDS:
            path = evidence.get(capability_id)
            capabilities.append(
                ProbeCapability(
                    capability_id=capability_id,
                    description=CAPABILITY_DESCRIPTIONS[capability_id],
                    status=(CapabilityStatus.PASS if path else CapabilityStatus.NOT_TESTED),
                    evidence_path=(path.relative_to(bundle.temp_path).as_posix() if path else None),
                    sha256=(sha256_file(path) if path else None),
                )
            )
        run_status = RunStatus.PASSED
        exit_code = 0
        run_id = workflow.run_id
    except (DifyNotConfigured, DifyAuthError, DifyQuotaError) as error:
        del error
        capabilities = _capabilities(CapabilityStatus.BLOCKED)
        run_status = RunStatus.BLOCKED
        exit_code = 2
        run_id = "blocked:dify"
    except (DifyTransportError, DifyContractError):
        capabilities = _capabilities(CapabilityStatus.FAIL)
        run_status = RunStatus.FAILED
        exit_code = 1
        run_id = "failed:dify"

    report = ProbeReport(
        case_id=case_id,
        backend="dify",
        generated_at_utc=datetime.now(UTC),
        capabilities=capabilities,
    )
    bundle.write_json("probe-results.json", report.model_dump(mode="json"))
    final = bundle.finalize(
        _manifest(
            case_id=case_id,
            backend="dify",
            status=run_status,
            input_sha256=sha256_bytes(canonical_json_bytes(input_payload)),
            run_id=run_id,
            started=started,
            capabilities=capabilities,
        )
    )
    return ProbeOutcome(case_id, final, report, exit_code)
