"""Command-line entry points for Phase 1 evidence and probes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import httpx

from debugmate.contracts import diagnosis_schema
from debugmate.evidence import verify_bundle
from debugmate.hashing import canonical_json_bytes
from debugmate.knowledge.build import build_knowledge
from debugmate.knowledge.coverage import coverage_report
from debugmate.knowledge.models import SourceRegistry, load_registry
from debugmate.knowledge.sync import create_sync_plan, execute_sync
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
    knowledge_build = commands.add_parser("knowledge-build")
    knowledge_build.add_argument("--registry", type=Path, required=True)
    knowledge_build.add_argument("--output", type=Path, required=True)
    knowledge_build.add_argument("--source-id")
    knowledge_build.add_argument("--fixture", type=Path)
    knowledge_build.add_argument("--online", action="store_true")
    knowledge_coverage = commands.add_parser("knowledge-coverage")
    knowledge_coverage.add_argument("path", type=Path)
    knowledge_sync = commands.add_parser("knowledge-sync")
    knowledge_sync.add_argument("path", type=Path)
    knowledge_sync.add_argument("--remote-manifest", type=Path)
    mode = knowledge_sync.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--execute", action="store_false", dest="dry_run")
    knowledge_sync.add_argument("--dataset-id")
    knowledge_sync.add_argument("--confirm-delete", action="store_true")
    return parser


def _ascii_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _selected_registry(registry: SourceRegistry, source_id: str | None) -> SourceRegistry:
    if source_id is None:
        return registry
    selected = [source for source in registry.sources if source.source_id == source_id]
    if not selected:
        raise ValueError(f"unknown source_id: {source_id}")
    return SourceRegistry(registry_version=registry.registry_version, sources=selected)


def _run_knowledge_build(args: argparse.Namespace) -> int:
    registry = _selected_registry(load_registry(args.registry), args.source_id)
    if args.online:
        if args.fixture is not None:
            raise ValueError("--fixture cannot be combined with --online")
        with httpx.Client(follow_redirects=False) as client:
            build = build_knowledge(registry, args.output, client)
    else:
        if args.fixture is None:
            raise ValueError("offline knowledge builds require --fixture")
        fixture_bytes = args.fixture.read_bytes()

        def fixture_response(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"Content-Type": "text/html; charset=utf-8"},
                content=fixture_bytes,
            )

        with httpx.Client(transport=httpx.MockTransport(fixture_response)) as client:
            build = build_knowledge(registry, args.output, client)
    print(
        _ascii_json(
            {
                "build_id": build.build_id,
                "build_path": str(build.path.resolve()),
                "status": build.status,
                "syncable": build.syncable,
            }
        )
    )
    return 0 if build.syncable else 1


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
    if args.command == "knowledge-build":
        return _run_knowledge_build(args)
    if args.command == "knowledge-coverage":
        report = coverage_report(args.path)
        print(_ascii_json(report.model_dump(mode="json")))
        return 0
    if args.command == "knowledge-sync":
        remote_manifest = (
            json.loads(args.remote_manifest.read_text(encoding="utf-8"))
            if args.remote_manifest is not None
            else {"documents": []}
        )
        plan = create_sync_plan(args.path, remote_manifest)
        settings = DebugMateSettings.from_env()
        dataset_key = (
            settings.dify_dataset_api_key.get_secret_value()
            if settings.dify_dataset_api_key is not None
            else None
        )
        with httpx.Client(base_url=f"{settings.dify_base_url.rstrip('/')}/") as client:
            result = execute_sync(
                plan,
                client=client,
                dataset_key=dataset_key,
                dataset_id=args.dataset_id,
                confirm_delete=args.confirm_delete,
                dry_run=args.dry_run,
            )
        print(
            _ascii_json(
                {
                    "plan": plan.model_dump(mode="json"),
                    "result": result.model_dump(mode="json"),
                }
            )
        )
        return 0
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
