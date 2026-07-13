"""Loopback-only entry point for the native DebugMate Gradio workbench."""

from __future__ import annotations

import argparse
import socket
from collections.abc import Sequence
from pathlib import Path

from debugmate.results.outcome_store import DiagnosisOutcomeStore
from debugmate.results.publisher import TrustedResultRoot
from debugmate.results.service import ResultApplicationService
from debugmate.ui.app import WORKBENCH_CSS, build_app


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


def _local_service() -> ResultApplicationService:
    project_root = Path(__file__).resolve().parents[3]
    runtime_root = project_root / ".debugmate-runtime"
    runtime_root.mkdir(exist_ok=True)
    return ResultApplicationService(
        workflow=None,
        evidence_root=runtime_root / "evidence",
        outcome_store=DiagnosisOutcomeStore(runtime_root / "outcomes"),
        results_root=TrustedResultRoot.for_testing(runtime_root / "results"),
        replay_root=project_root / "fixtures" / "replay",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m debugmate.ui.serve")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=_available_loopback_port)
    args = parser.parse_args(argv)
    if args.host != "127.0.0.1":
        parser.error("host must be literal 127.0.0.1")
    app = build_app(_local_service())
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
