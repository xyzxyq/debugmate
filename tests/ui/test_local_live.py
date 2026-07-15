from __future__ import annotations

import json
import socket
from pathlib import Path

import httpx
import pytest

from debugmate.contracts import new_case_id
from debugmate.knowledge.local_rule import load_local_rule_snapshot
from debugmate.privacy.approval import approve_preview
from debugmate.privacy.models import InputEnvelope
from debugmate.privacy.text_redactor import redact_input
from debugmate.results.contracts import ResultMode, ResultStatus
from debugmate.ui import serve as serve_module

_KEY = b"local-live-approval-key-is-32bytes"


def _approved_local_input():
    return approve_preview(
        redact_input(
            InputEnvelope(
                case_id=new_case_id(),
                error_text="ModuleNotFoundError: No module named 'fictional_pkg'",
                environment={"python": "3.13.5"},
            )
        ),
        _KEY,
    )


def _source_run_manifest(
    runtime_root: Path, case_id: str, source_run_id: str
) -> dict[str, object]:
    manifest = json.loads(
        (
            runtime_root
            / "evidence"
            / case_id
            / source_run_id
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(manifest, dict)
    return manifest


def test_local_rule_live_service_creates_verified_fresh_live_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as approval_patch:
        approval_patch.setattr(serve_module.secrets, "token_bytes", lambda _size: _KEY)
        service = serve_module._local_service(runtime_root=tmp_path / "runtime")

    first = service.diagnose_and_compose(_approved_local_input())
    second = service.diagnose_and_compose(_approved_local_input())

    assert first.mode is ResultMode.LIVE and first.fixture_id is None
    assert first.status is ResultStatus.COMPLETED
    assert first.identity is not None and second.identity is not None
    assert first.identity.case_id != second.identity.case_id
    assert first.identity.source_run_id != second.identity.source_run_id
    assert first.result_id != second.result_id
    source_manifest = _source_run_manifest(
        tmp_path / "runtime", first.identity.case_id, first.identity.source_run_id
    )
    assert source_manifest["backend"] == "local-rule-v1"
    assert source_manifest["knowledge_version"] == "local-rule-v1"
    assert source_manifest["knowledge_build_id"] == load_local_rule_snapshot(
        Path.cwd()
    ).knowledge_build_id


def test_nonmatching_local_request_publishes_no_outcome_or_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = tmp_path / "runtime"
    with monkeypatch.context() as approval_patch:
        approval_patch.setattr(serve_module.secrets, "token_bytes", lambda _size: _KEY)
        service = serve_module._local_service(runtime_root=runtime)
    approved = approve_preview(
        redact_input(
            InputEnvelope(
                case_id=new_case_id(),
                error_text="ValueError: invalid fictional value",
                environment={"python": "3.13.5"},
            )
        ),
        _KEY,
    )

    result = service.diagnose_and_compose(approved)

    assert result.status is ResultStatus.FAILED
    assert not list((runtime / "outcomes").glob("*.json"))
    assert not list((runtime / "evidence").glob("run_*"))
    assert not list((runtime / "results").glob("case_*"))


def test_local_live_path_never_constructs_cloud_tts_or_touches_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def poisoned(*_args: object, **_kwargs: object):
        raise AssertionError("network or cloud adapter boundary touched")

    monkeypatch.setattr(serve_module, "DifyTtsAdapter", poisoned)
    monkeypatch.setattr(serve_module, "EdgeTtsAdapter", poisoned)
    monkeypatch.setattr(httpx, "Client", poisoned)
    monkeypatch.setattr(socket, "create_connection", poisoned)
    reads: list[Path] = []
    original_read_text = Path.read_text

    def recording_read_text(path: Path, *args: object, **kwargs: object) -> str:
        reads.append(path.resolve())
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", recording_read_text)
    with monkeypatch.context() as approval_patch:
        approval_patch.setattr(serve_module.secrets, "token_bytes", lambda _size: _KEY)
        service = serve_module._local_service(runtime_root=tmp_path / "runtime")

    result = service.diagnose_and_compose(_approved_local_input())

    assert result.status is ResultStatus.COMPLETED
    snapshot_reads = [path for path in reads if "knowledge" in path.parts]
    assert snapshot_reads
    assert all("knowledge\\snapshots\\local-rule" in str(path) for path in snapshot_reads)
    assert all("fixtures" not in path.parts and "tests" not in path.parts for path in reads)
