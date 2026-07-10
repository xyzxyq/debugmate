"""Command-line entry points for Phase 1 evidence and probes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from debugmate.contracts import diagnosis_schema
from debugmate.evidence import verify_bundle
from debugmate.hashing import canonical_json_bytes
from debugmate.probe import ProbeOutcome, run_cloud_probe, run_fixture_probe
from debugmate.settings import DebugMateSettings


def _print_outcome(outcome: ProbeOutcome) -> None:
    counts = Counter(item.status.value for item in outcome.report.capabilities)
    print(
        json.dumps(
            {
                "case_id": outcome.case_id,
                "bundle_path": str(outcome.bundle_path.resolve()),
                "backend": outcome.report.backend,
                "status_counts": dict(sorted(counts.items())),
            },
            sort_keys=True,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="debugmate")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("fixture-probe", "cloud-probe"):
        command = commands.add_parser(name)
        command.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify-bundle")
    verify.add_argument("path", type=Path)
    export = commands.add_parser("export-schema")
    export.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "fixture-probe":
        outcome = run_fixture_probe(args.output)
        _print_outcome(outcome)
        return outcome.exit_code
    if args.command == "cloud-probe":
        outcome = run_cloud_probe(DebugMateSettings.from_env(), args.output)
        _print_outcome(outcome)
        return outcome.exit_code
    if args.command == "verify-bundle":
        result = verify_bundle(args.path)
        print(json.dumps({"ok": result.ok, "issues": result.issues}, sort_keys=True))
        return 0 if result.ok else 1
    if args.command == "export-schema":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json_bytes(diagnosis_schema()) + b"\n")
        print(json.dumps({"schema_path": str(args.output.resolve())}, sort_keys=True))
        return 0
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
