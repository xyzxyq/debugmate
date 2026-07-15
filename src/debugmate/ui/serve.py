"""Loopback-only entry point for the native DebugMate Gradio workbench."""

from __future__ import annotations

import argparse
import secrets
import socket
from collections.abc import Sequence
from pathlib import Path

from debugmate.diagnosis.local_rule import LocalRuleGenerationProvider
from debugmate.diagnosis.providers import ProductionExtractionProvider
from debugmate.diagnosis.workflow import DiagnosisWorkflow
from debugmate.knowledge.local_rule import (
    LocalRuleRetrievalProvider,
    load_local_rule_snapshot,
)
from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
from debugmate.results.card import CardRenderFailure, render_card
from debugmate.results.consistency import validate_result_candidates
from debugmate.results.contracts import ResultMode
from debugmate.results.font import prepare_generation_context
from debugmate.results.outcome_store import DiagnosisOutcomeStore
from debugmate.results.presentation import build_presentation
from debugmate.results.publisher import TrustedResultRoot, publish_result_bundle
from debugmate.results.recap import compose_recap
from debugmate.results.report import render_citations, render_report
from debugmate.results.service import ResultApplicationService
from debugmate.results.tts.base import TtsAdapterError, TtsRequestIdentity
from debugmate.results.tts.dify import DifyTtsAdapter
from debugmate.results.tts.edge import EdgeTtsAdapter
from debugmate.results.tts.sapi import SapiTtsAdapter
from debugmate.settings import DebugMateSettings
from debugmate.ui.app import WORKBENCH_CSS, build_app


class _NoopOcr:
    """Text-only local workflow OCR port with no external side effects."""

    def recognize(self, _path: Path) -> list[object]:
        return []


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


def _optional_tts_adapter(backend: str, factory):
    try:
        return factory()
    except (OSError, TypeError, ValueError):
        return _UnavailableTtsAdapter(backend)


def _local_composer(
    *, project_root: Path, runtime_root: Path, results_root: TrustedResultRoot
):
    """Build the real Phase 4 chain used by fixed replay demonstrations."""

    context = prepare_generation_context(project_root=project_root)
    candidate_root = TrustedCandidateRoot.for_testing(runtime_root / "tts-candidates")
    card_root = runtime_root / "cards"

    def compose(source, *, mode, fixture_id, fixture_name, stage_callback=None):
        if mode is ResultMode.LIVE:
            tts = TtsFallbackChain(
                (SapiTtsAdapter(project_root=project_root),), local_only=True
            )
        else:
            settings = DebugMateSettings.from_env()
            tts = TtsFallbackChain(
                (
                    _optional_tts_adapter("dify", lambda: DifyTtsAdapter(settings)),
                    _optional_tts_adapter(
                        "edge_tts", lambda: EdgeTtsAdapter(timeout_seconds=5.0)
                    ),
                    _optional_tts_adapter(
                        "sapi", lambda: SapiTtsAdapter(project_root=project_root)
                    ),
                )
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


def _local_service(
    *, runtime_root: Path | None = None, approval_key: bytes | None = None
) -> ResultApplicationService:
    project_root = Path(__file__).resolve().parents[3]
    runtime_root = runtime_root or project_root / ".debugmate-runtime"
    runtime_root = Path(runtime_root).absolute()
    runtime_root.mkdir(exist_ok=True)
    results_root = TrustedResultRoot.for_testing(runtime_root / "results")
    approval_key = approval_key or secrets.token_bytes(32)
    snapshot = load_local_rule_snapshot(project_root)
    workflow = DiagnosisWorkflow(
        extraction_provider=ProductionExtractionProvider(
            redacted_root=runtime_root / "redacted", ocr_backend=_NoopOcr()
        ),
        retrieval_provider=LocalRuleRetrievalProvider(snapshot),
        generator=LocalRuleGenerationProvider(snapshot),
        approval_key=approval_key,
        redacted_root=runtime_root / "redacted",
    )
    return ResultApplicationService(
        workflow=workflow,
        evidence_root=runtime_root / "evidence",
        outcome_store=DiagnosisOutcomeStore(runtime_root / "outcomes"),
        results_root=results_root,
        replay_root=project_root / "fixtures" / "replay",
        composer=_local_composer(
            project_root=project_root,
            runtime_root=runtime_root,
            results_root=results_root,
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m debugmate.ui.serve")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=_available_loopback_port)
    args = parser.parse_args(argv)
    if args.host != "127.0.0.1":
        parser.error("host must be literal 127.0.0.1")
    approval_key = secrets.token_bytes(32)
    app = build_app(
        _local_service(approval_key=approval_key),
        content_origin=f"http://{args.host}:{args.port}",
        approval_key=approval_key,
    )
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        inbrowser=False,
        quiet=True,
        show_error=False,
        css=WORKBENCH_CSS,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess test
    raise SystemExit(main())
