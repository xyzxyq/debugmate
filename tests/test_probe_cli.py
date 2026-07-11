from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from debugmate.adapters.dify import (
    DifyAuthError,
    DifyBackend,
    DifyContractError,
    DifyQuotaError,
)
from debugmate.cli import main
from debugmate.contracts import new_case_id
from debugmate.evidence import RunStatus, verify_bundle
from debugmate.probe import CAPABILITY_IDS, run_cloud_probe, run_fixture_probe
from debugmate.settings import DebugMateSettings

SENTINEL = "SECRET_SENTINEL_DO_NOT_LOG"
FIXTURE_DIAGNOSIS = Path("fixtures/cases/module_not_found/diagnosis.json")


def settings() -> DebugMateSettings:
    return DebugMateSettings.from_env(
        {"DIFY_API_KEY": SENTINEL, "DIFY_BASE_URL": "https://api.dify.test/v1"}
    )


@pytest.mark.parametrize(
    ("status", "error_type"),
    [(401, DifyAuthError), (403, DifyAuthError), (429, DifyQuotaError)],
)
def test_dify_auth_and_quota_errors_are_not_retried_or_leaked(
    status: int,
    error_type: type[Exception],
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, json={"message": SENTINEL}, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = DifyBackend(settings(), client=client)

    with pytest.raises(error_type) as caught:
        backend.run_workflow({"case_id": new_case_id()}, user="debugmate-test")

    rendered = str(caught.value) + capsys.readouterr().out + caplog.text
    assert calls == 1
    assert SENTINEL not in rendered


def test_dify_connect_error_retries_once() -> None:
    calls = 0
    diagnosis = json.loads(FIXTURE_DIAGNOSIS.read_text(encoding="utf-8"))
    diagnosis["case_id"] = new_case_id()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("temporary", request=request)
        return httpx.Response(
            200,
            json={"workflow_run_id": "run-test", "data": {"outputs": {"diagnosis": diagnosis}}},
            request=request,
        )

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = backend.run_workflow({"case_id": diagnosis["case_id"]}, user="debugmate-test")

    assert calls == 2
    assert result.run_id == "run-test"
    assert result.diagnosis.case_id == diagnosis["case_id"]


def test_dify_workflow_rejects_invalid_contract_without_leaking_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"workflow_run_id": "run-bad", "data": {"outputs": {"diagnosis": {}}}},
            request=request,
        )

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(DifyContractError) as caught:
        backend.run_workflow({"case_id": new_case_id()}, user="debugmate-test")

    assert SENTINEL not in str(caught.value)


@pytest.mark.parametrize("audio", [b"ID3\x04\x00\x00fixture", b"\xff\xfb\x90\x64fixture"])
def test_dify_tts_accepts_mp3_headers(audio: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=audio, request=request)

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = backend.synthesize_audio("fictional recap", user="debugmate-test")

    assert result.audio == audio
    assert result.mime_type == "audio/mpeg"


def test_dify_tts_rejects_non_mp3_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-mp3", request=request)

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(DifyContractError):
        backend.synthesize_audio("fictional recap", user="debugmate-test")


def test_fixture_probe_writes_truthful_seven_capability_bundle(tmp_path: Path) -> None:
    outcome = run_fixture_probe(tmp_path / "evidence")
    verification = verify_bundle(outcome.bundle_path)
    report = json.loads((outcome.bundle_path / "probe-results.json").read_text(encoding="utf-8"))

    assert verification.ok is True
    assert verification.manifest is not None
    assert verification.manifest.backend == "fixture"
    assert verification.manifest.status is RunStatus.PASSED
    assert tuple(item["capability_id"] for item in report["capabilities"]) == CAPABILITY_IDS
    assert {item["status"] for item in report["capabilities"]} == {"not-tested"}
    assert (outcome.bundle_path / "diagnosis.json").is_file()
    assert (outcome.bundle_path / "input.redacted.json").is_file()


def test_cloud_probe_without_credentials_is_blocked_not_failed(tmp_path: Path) -> None:
    outcome = run_cloud_probe(DebugMateSettings.from_env({}), tmp_path / "evidence")
    report = json.loads((outcome.bundle_path / "probe-results.json").read_text(encoding="utf-8"))
    verification = verify_bundle(outcome.bundle_path)

    assert outcome.exit_code == 2
    assert {item["status"] for item in report["capabilities"]} == {"blocked"}
    assert verification.ok is True
    assert verification.manifest is not None
    assert verification.manifest.status is RunStatus.BLOCKED


def test_cloud_contract_failure_publishes_failed_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingBackend:
        def __init__(self, configured: DebugMateSettings) -> None:
            del configured

        def upload_file(self, path: Path, user: str) -> None:
            del path, user
            raise DifyContractError("safe contract failure")

    monkeypatch.setattr("debugmate.probe.DifyBackend", FailingBackend)
    configured = DebugMateSettings.from_env({"DIFY_API_KEY": SENTINEL})

    outcome = run_cloud_probe(configured, tmp_path / "evidence")
    verification = verify_bundle(outcome.bundle_path)

    assert outcome.exit_code == 1
    assert verification.ok is True
    assert verification.manifest is not None
    assert verification.manifest.status is RunStatus.FAILED
    assert verification.manifest.error_code == "E_DIFY_PROBE"


def test_cli_fixture_probe_and_bundle_verification(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "cli-evidence"

    assert main(["fixture-probe", "--output", str(root)]) == 0
    output = json.loads(capsys.readouterr().out)
    bundle_path = Path(output["bundle_path"])
    assert output["backend"] == "fixture"
    assert output["status_counts"] == {"not-tested": 7}

    assert main(["verify-bundle", str(bundle_path)]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["ok"] is True


def test_cli_machine_json_is_ascii_safe_for_chinese_windows_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "中文证据"

    assert main(["fixture-probe", "--output", str(root)]) == 0
    raw = capsys.readouterr().out
    parsed = json.loads(raw)

    assert raw.isascii()
    assert "中文证据" in parsed["bundle_path"]


def test_schema_export_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    assert main(["export-schema", "--output", str(first)]) == 0
    assert main(["export-schema", "--output", str(second)]) == 0

    assert first.read_bytes() == second.read_bytes()
    schema = json.loads(first.read_text(encoding="utf-8"))
    assert schema["title"] == "DiagnosisRecord"


def test_capability_matrix_has_exact_ids_and_no_unproven_pass() -> None:
    matrix = json.loads(Path("platform/dify/capability-matrix.json").read_text(encoding="utf-8"))

    assert tuple(item["capability_id"] for item in matrix["capabilities"]) == CAPABILITY_IDS
    for item in matrix["capabilities"]:
        if item["status"] == "pass":
            assert item["evidence_path"]
            assert item["sha256"]


def test_reconstruction_docs_and_examples_are_truthful_and_secret_free() -> None:
    dify_readme = Path("platform/dify/README.md").read_text(encoding="utf-8")
    root_readme = Path("README.md").read_text(encoding="utf-8")
    dsl = Path("platform/dify/app.dsl.yml.example").read_text(encoding="utf-8")
    prompts = Path("prompts/README.md").read_text(encoding="utf-8")
    combined_examples = "\n".join([dsl, prompts])

    for capability_id in CAPABILITY_IDS:
        assert capability_id in dify_readme
    assert "4 小时" in dify_readme
    assert "重导入" in dify_readme
    assert "不得充值" in dify_readme
    assert "fixture-probe" in root_readme
    assert "cloud-probe" in root_readme
    for status in ("pass", "fail", "blocked", "not-tested"):
        assert status in root_readme
    assert all(version in prompts for version in ("V1", "V2", "V3", "V4"))
    assert "不可运行" in dsl
    for pattern in (r"api_key", r"authorization", r"token:", r"Bearer ", r"20795"):
        assert re.search(pattern, combined_examples, re.I) is None


def test_contract_and_knowledge_schemas_are_separate_and_strict() -> None:
    diagnosis = json.loads(
        Path("contracts/diagnosis-record-v1.schema.json").read_text(encoding="utf-8")
    )
    knowledge = json.loads(Path("knowledge/manifest.schema.json").read_text(encoding="utf-8"))

    assert diagnosis["title"] == "DiagnosisRecord"
    assert diagnosis["additionalProperties"] is False
    required = {
        "source_id",
        "title",
        "url",
        "final_url",
        "product",
        "version_scope",
        "platform",
        "allowed_domain",
        "heading_patterns",
        "error_categories",
        "retrieved_at",
        "status_code",
        "etag",
        "last_modified",
        "sha256",
        "license_or_terms_note",
        "selection_reason",
    }
    assert set(knowledge["items"]["required"]) == required
    assert knowledge["items"]["additionalProperties"] is False
