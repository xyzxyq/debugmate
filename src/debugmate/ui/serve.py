"""Loopback-only entry point for the native DebugMate Gradio workbench."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import socket
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from debugmate.adapters.dify import DifyBackend
from debugmate.cloud.contracts import ExecutionBackend
from debugmate.cloud.receipts import DifyReceiptStore
from debugmate.cloud.workflow import DifyLiveWorkflow
from debugmate.contracts import schema_sha256
from debugmate.diagnosis.local_rule import LocalRuleGenerationProvider
from debugmate.diagnosis.providers import ProductionExtractionProvider
from debugmate.diagnosis.workflow import DiagnosisWorkflow
from debugmate.gateway import CloudGateway
from debugmate.knowledge.local_rule import (
    LocalRuleRetrievalProvider,
    load_local_rule_snapshot,
)
from debugmate.knowledge.sync import DifyReadbackAttestation
from debugmate.privacy.models import InputEnvelope, PreviewBundle
from debugmate.privacy.rapidocr_backend import RapidOcrBackend
from debugmate.privacy.text_redactor import build_preview
from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
from debugmate.results.card import CardRenderFailure, render_card
from debugmate.results.consistency import validate_result_candidates
from debugmate.results.font import prepare_generation_context
from debugmate.results.outcome_store import DiagnosisOutcomeStore
from debugmate.results.presentation import build_presentation
from debugmate.results.publisher import TrustedResultRoot, publish_result_bundle
from debugmate.results.recap import compose_recap
from debugmate.results.report import render_citations, render_report
from debugmate.results.service import ResultApplicationService
from debugmate.results.tts.base import TtsAdapterError, TtsRequestIdentity
from debugmate.results.tts.sapi import SapiTtsAdapter
from debugmate.settings import DebugMateSettings
from debugmate.ui.app import WORKBENCH_CSS, build_app, ensure_content_endpoint


@dataclass(frozen=True, slots=True)
class LocalAppDependencies:
    """Ordinary app graph shared by preview and approved extraction."""

    service: ResultApplicationService
    ocr_backend: RapidOcrBackend
    redacted_root: Path
    execution_backend: ExecutionBackend
    approval_key: bytes
    fallback_reason: str | None = None
    contract_hashes: tuple[str, str, str] | None = None

    @property
    def preview_workspace(self) -> Path:
        return self.redacted_root

    def build_preview(self, value: InputEnvelope) -> PreviewBundle:
        return build_preview(value, self.redacted_root, self.ocr_backend)


def _available_loopback_port(value: str) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("port must be an integer") from None
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1024 and 65535")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", port))
    except OSError as error:
        raise argparse.ArgumentTypeError("port is unavailable") from error
    return port


class _UnavailableTtsAdapter:
    """Keep the fixed chain shape when one optional local backend cannot start."""

    def __init__(self, backend: str) -> None:
        self.backend = backend

    def synthesize(self, *_arguments: object, **_kwargs: object):
        raise TtsAdapterError()


def _local_composer(
    *,
    project_root: Path,
    runtime_root: Path,
    results_root: TrustedResultRoot,
    replay_local_only: bool = True,
    qa_result_mode: str | None = None,
):
    """Build the real Phase 4 chain used by fixed replay demonstrations."""

    context = prepare_generation_context(project_root=project_root)
    candidate_root = TrustedCandidateRoot.for_testing(runtime_root / "tts-candidates")
    card_root = runtime_root / "cards"
    compose_calls = 0

    def compose(
        source,
        *,
        mode,
        execution_backend,
        fixture_id,
        fixture_name,
        stage_callback=None,
    ):
        nonlocal compose_calls
        compose_calls += 1
        active_qa_mode = qa_result_mode if compose_calls == 1 else None
        if active_qa_mode == "tts_failed":
            tts = TtsFallbackChain(
                tuple(_UnavailableTtsAdapter(backend) for backend in ("dify", "edge_tts", "sapi"))
            )
        elif active_qa_mode == "fallback":
            tts = TtsFallbackChain(
                (
                    _UnavailableTtsAdapter("dify"),
                    _UnavailableTtsAdapter("edge_tts"),
                    SapiTtsAdapter(project_root=project_root),
                )
            )
        else:
            tts = TtsFallbackChain(
                (SapiTtsAdapter(project_root=project_root),),
                local_only=True,
            )
        presentation = build_presentation(source, context)
        if stage_callback is not None:
            stage_callback("presentation")
        report = render_report(presentation)
        citations = render_citations(presentation)
        if stage_callback is not None:
            stage_callback("report")
        recap = compose_recap(presentation)
        target = card_root / f"{source.source_run_id}-{secrets.token_hex(16)}.png"
        try:
            if active_qa_mode == "png_failed":
                card = CardRenderFailure("png_layout_failed")
            else:
                try:
                    card = render_card(presentation, context, target=target)
                except CardRenderFailure as failure:
                    card = failure
            if stage_callback is not None:
                stage_callback("card")
            audio = tts.synthesize(
                recap,
                TtsRequestIdentity(
                    case_id=recap.identity.case_id,
                    source_run_id=recap.identity.source_run_id,
                    diagnosis_sha256=recap.identity.diagnosis_sha256,
                    generation_version=recap.identity.generation_version,
                    recap_sha256=recap.sha256,
                ),
                candidate_root,
            )
            if stage_callback is not None:
                stage_callback("audio")
            candidates = validate_result_candidates(
                source, presentation, report, citations, card, recap, audio
            )
            if stage_callback is not None:
                stage_callback("consistency")
            published = publish_result_bundle(
                results_root,
                candidates,
                mode=mode,
                execution_backend=execution_backend,
                fixture_id=fixture_id,
                fixture_name=fixture_name,
            )
            if stage_callback is not None:
                stage_callback("publish")
            return published
        finally:
            target.unlink(missing_ok=True)

    compose.supports_stage_events = True
    return compose


def _local_dependencies(
    *,
    runtime_root: Path | None = None,
    approval_key: bytes | None = None,
    replay_local_only: bool = True,
    qa_result_mode: str | None = None,
    qa_ocr_unavailable: bool = False,
) -> LocalAppDependencies:
    project_root = Path(__file__).resolve().parents[3]
    runtime_root = runtime_root or project_root / ".debugmate-runtime"
    runtime_root = Path(runtime_root).absolute()
    runtime_root.mkdir(parents=True, exist_ok=True)
    if qa_result_mode not in {None, "tts_failed", "png_failed", "fallback"}:
        raise ValueError("invalid QA result mode")
    results_root = TrustedResultRoot.for_testing(runtime_root / "results")
    redacted_root = (runtime_root / "redacted").absolute()
    redacted_root.mkdir(parents=True, exist_ok=True)

    def unavailable_ocr_factory():
        raise RuntimeError("controlled OCR unavailable gate")

    ocr_backend = RapidOcrBackend()
    if qa_ocr_unavailable:
        ocr_backend.factory = unavailable_ocr_factory
    approval_key = approval_key or secrets.token_bytes(32)
    snapshot = load_local_rule_snapshot(project_root)
    workflow = DiagnosisWorkflow(
        extraction_provider=ProductionExtractionProvider(
            redacted_root=redacted_root, ocr_backend=ocr_backend
        ),
        retrieval_provider=LocalRuleRetrievalProvider(snapshot),
        generator=LocalRuleGenerationProvider(snapshot),
        execution_backend=ExecutionBackend.LOCAL_FALLBACK,
        approval_key=approval_key,
        redacted_root=redacted_root,
    )
    service = ResultApplicationService(
        workflow=workflow,
        evidence_root=runtime_root / "evidence",
        outcome_store=DiagnosisOutcomeStore(runtime_root / "outcomes"),
        results_root=results_root,
        replay_root=project_root / "fixtures" / "replay",
        composer=_local_composer(
            project_root=project_root,
            runtime_root=runtime_root,
            results_root=results_root,
            replay_local_only=replay_local_only,
            qa_result_mode=qa_result_mode,
        ),
    )
    return LocalAppDependencies(
        service=service,
        ocr_backend=ocr_backend,
        redacted_root=redacted_root,
        execution_backend=ExecutionBackend.LOCAL_FALLBACK,
        approval_key=approval_key,
    )


def _contract_hashes(project_root: Path) -> tuple[str, str, str]:
    """Load current versioned contract identities without probing a provider."""

    dsl_path = project_root / "platform" / "dify" / "app.dsl.yml"
    prompt_path = project_root / "prompts" / "v1-baseline.md"
    dsl_text = dsl_path.read_text(encoding="utf-8")
    match = re.search(r'DSL_SEMANTIC_SHA256\s*=\s*"([0-9a-f]{64})"', dsl_text)
    if match is None:
        raise ValueError("Dify DSL semantic identity is missing")
    prompt_hash = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    return match.group(1), prompt_hash, schema_sha256()


def _fallback_dependencies(
    reason: str,
    *,
    runtime_root: Path | None,
    approval_key: bytes,
    replay_local_only: bool,
    qa_result_mode: str | None,
    qa_ocr_unavailable: bool,
) -> LocalAppDependencies:
    dependencies = _local_dependencies(
        runtime_root=runtime_root,
        approval_key=approval_key,
        replay_local_only=replay_local_only,
        qa_result_mode=qa_result_mode,
        qa_ocr_unavailable=qa_ocr_unavailable,
    )
    return LocalAppDependencies(
        service=dependencies.service,
        ocr_backend=dependencies.ocr_backend,
        redacted_root=dependencies.redacted_root,
        execution_backend=ExecutionBackend.LOCAL_FALLBACK,
        approval_key=approval_key,
        fallback_reason=reason,
    )


def _live_dependencies(
    *,
    settings: DebugMateSettings | None = None,
    runtime_root: Path | None = None,
    build_manifest: Path | None = None,
    readback_attestation: Path | None = None,
    dataset_binding: str | None = None,
    app_ready: bool | None = None,
    replay_local_only: bool = True,
    qa_result_mode: str | None = None,
    qa_ocr_unavailable: bool = False,
) -> LocalAppDependencies:
    """Construct configured Dify or an explicit local fallback with zero I/O.

    The dataset management key is deliberately absent from this gate.  Runtime
    authority comes from the locally verified readback attestation, while the
    management key is reserved for an explicit synchronization acceptance run.
    """

    project_root = Path(__file__).resolve().parents[3]
    if settings is None:
        try:
            settings = DebugMateSettings.from_env()
        except ValidationError:
            approval_key = secrets.token_bytes(32)
            return _fallback_dependencies(
                "app_config_invalid",
                runtime_root=runtime_root,
                approval_key=approval_key,
                replay_local_only=replay_local_only,
                qa_result_mode=qa_result_mode,
                qa_ocr_unavailable=qa_ocr_unavailable,
            )
    runtime_root = Path(runtime_root or project_root / ".debugmate-runtime").absolute()
    approval_key = settings.approval_key_bytes
    ready = (
        os.environ.get("DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED") == "1"
        if app_ready is None
        else app_ready
    )
    if not settings.dify_application_configured:
        return _fallback_dependencies(
            "app_config_incomplete",
            runtime_root=runtime_root,
            approval_key=approval_key,
            replay_local_only=replay_local_only,
            qa_result_mode=qa_result_mode,
            qa_ocr_unavailable=qa_ocr_unavailable,
        )
    if not ready:
        return _fallback_dependencies(
            "app_not_ready",
            runtime_root=runtime_root,
            approval_key=approval_key,
            replay_local_only=replay_local_only,
            qa_result_mode=qa_result_mode,
            qa_ocr_unavailable=qa_ocr_unavailable,
        )

    dataset_binding = dataset_binding or os.environ.get("DIFY_DATASET_ID")
    readback_attestation = readback_attestation or (
        project_root / "evidence" / "dify-live" / "phase8" / "knowledge-readback.json"
    )
    try:
        attestation = DifyReadbackAttestation.model_validate_json(
            Path(readback_attestation).read_bytes(), strict=True
        )
    except (OSError, ValidationError):
        reason = (
            "knowledge_attestation_missing"
            if not Path(readback_attestation).is_file()
            else "knowledge_attestation_invalid"
        )
        return _fallback_dependencies(
            reason,
            runtime_root=runtime_root,
            approval_key=approval_key,
            replay_local_only=replay_local_only,
            qa_result_mode=qa_result_mode,
            qa_ocr_unavailable=qa_ocr_unavailable,
        )
    if not dataset_binding or not secrets.compare_digest(
        hashlib.sha256(dataset_binding.encode("utf-8")).hexdigest(),
        attestation.dataset_fingerprint,
    ):
        return _fallback_dependencies(
            "dataset_binding_mismatch",
            runtime_root=runtime_root,
            approval_key=approval_key,
            replay_local_only=replay_local_only,
            qa_result_mode=qa_result_mode,
            qa_ocr_unavailable=qa_ocr_unavailable,
        )
    build_manifest = build_manifest or (
        project_root
        / ".artifacts"
        / "knowledge-build"
        / attestation.knowledge_build_id
        / "manifest.json"
    )
    try:
        contract_hashes = _contract_hashes(project_root)
        manifest_payload = json.loads(Path(build_manifest).read_text(encoding="utf-8"))
        if manifest_payload.get("build_id") != attestation.knowledge_build_id:
            raise ValueError("knowledge build differs")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        return _fallback_dependencies(
            "local_contract_invalid",
            runtime_root=runtime_root,
            approval_key=approval_key,
            replay_local_only=replay_local_only,
            qa_result_mode=qa_result_mode,
            qa_ocr_unavailable=qa_ocr_unavailable,
        )

    local = _local_dependencies(
        runtime_root=runtime_root,
        approval_key=approval_key,
        replay_local_only=replay_local_only,
        qa_result_mode=qa_result_mode,
        qa_ocr_unavailable=qa_ocr_unavailable,
    )
    backend = DifyBackend(settings)
    gateway = CloudGateway(
        backend,
        approval_key=approval_key,
        user=settings.dify_user,
        redacted_root=local.redacted_root,
    )
    workflow = DifyLiveWorkflow(
        gateway=gateway,
        receipt_store=DifyReceiptStore(runtime_root / "dify-receipts"),
        approval_key=approval_key,
        build_manifest=Path(build_manifest),
        readback_attestation=attestation,
        expected_dsl_semantic_sha256=contract_hashes[0],
    )
    service = ResultApplicationService(
        workflow=workflow,
        evidence_root=runtime_root / "evidence",
        outcome_store=DiagnosisOutcomeStore(runtime_root / "outcomes"),
        results_root=TrustedResultRoot.for_testing(runtime_root / "results"),
        replay_root=project_root / "fixtures" / "replay",
        live_execution_backend=ExecutionBackend.DIFY,
        composer=local.service._composer,
    )
    return LocalAppDependencies(
        service=service,
        ocr_backend=local.ocr_backend,
        redacted_root=local.redacted_root,
        execution_backend=ExecutionBackend.DIFY,
        approval_key=approval_key,
        contract_hashes=contract_hashes,
    )


def _local_service(
    *,
    runtime_root: Path | None = None,
    approval_key: bytes | None = None,
    replay_local_only: bool = True,
    qa_result_mode: str | None = None,
) -> ResultApplicationService:
    """Compatibility façade while Phase 07 UI consumes the explicit graph."""

    return _local_dependencies(
        runtime_root=runtime_root,
        approval_key=approval_key,
        replay_local_only=replay_local_only,
        qa_result_mode=qa_result_mode,
    ).service


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m debugmate.ui.serve")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=_available_loopback_port)
    parser.add_argument("--qa-ocr-unavailable", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.host != "127.0.0.1":
        parser.error("host must be literal 127.0.0.1")
    project_root = Path(__file__).resolve().parents[3]
    cache_root = (project_root / ".debugmate-runtime" / "gradio-cache").absolute()
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ["GRADIO_TEMP_DIR"] = str(cache_root)
    dependencies = _live_dependencies(
        qa_ocr_unavailable=args.qa_ocr_unavailable,
    )
    approval_key = dependencies.approval_key
    app = build_app(
        dependencies.service,
        content_origin=os.environ.get("DEBUGMATE_PUBLIC_ORIGIN")
        or f"http://{args.host}:{args.port}",
        request_origin=f"http://{args.host}:{args.port}",
        approval_key=approval_key,
        preview_builder=dependencies.build_preview,
        upload_root=cache_root,
        redacted_root=dependencies.redacted_root,
    )
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        inbrowser=False,
        quiet=True,
        show_error=False,
        prevent_thread_lock=True,
        max_file_size="10mb",
        css=WORKBENCH_CSS,
    )
    ensure_content_endpoint(app)
    app.block_thread()
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess test
    raise SystemExit(main())
