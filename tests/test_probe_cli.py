from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from debugmate.adapters.base import CandidateRunResult
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


def test_extraction_cli_view_has_six_explicit_slots_and_correction_ids() -> None:
    from debugmate.cli import extraction_cli_view
    from debugmate.diagnosis.extraction import (
        ExtractionRecord,
        FieldId,
        SourceKind,
        TextLocator,
        extraction_id_for,
        make_candidate,
    )

    candidate = make_candidate(
        field_id=FieldId.EXCEPTION_TYPE,
        value="ModuleNotFoundError",
        source_kind=SourceKind.TEXT,
        confidence=1.0,
        locator=TextLocator(input_field="error_text", start=0, end=19),
    )
    record = ExtractionRecord(
        case_id="case_00000000000000000000000000000000",
        extraction_id=extraction_id_for(
            "case_00000000000000000000000000000000", {"error_text": "1" * 64}, [candidate]
        ),
        source_hashes={"error_text": "1" * 64},
        candidates=[candidate],
    )
    view = extraction_cli_view(record)
    assert list(view["slots"]) == [
        "exception_type",
        "traceback_key_line",
        "package",
        "version",
        "device",
        "path",
    ]
    assert view["slots"]["exception_type"]["candidate_id"] == candidate.candidate_id
    assert view["slots"]["exception_type"]["correction_field_id"] == "exception_type"
    assert view["slots"]["path"] == {"state": "missing", "field_id": "path"}


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
    assert result.candidate_payload["case_id"] == diagnosis["case_id"]


def test_dify_workflow_returns_invalid_contract_as_untrusted_candidate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"workflow_run_id": "run-bad", "data": {"outputs": {"diagnosis": {}}}},
            request=request,
        )

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))

    result = backend.run_workflow({"case_id": new_case_id()}, user="debugmate-test")

    assert result.candidate_payload == {}


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


def test_cloud_probe_keeps_scanned_recap_text_but_defers_audio_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audio_calls: list[str] = []
    workflow_inputs: list[dict[str, object]] = []

    class SuccessfulBackend:
        def __init__(self, configured: DebugMateSettings) -> None:
            del configured

        def upload_file(self, path: Path, user: str) -> SimpleNamespace:
            del path, user
            return SimpleNamespace(file_id="file-fixture", filename="input.json", backend="dify")

        def run_workflow(self, inputs: dict[str, object], user: str) -> CandidateRunResult:
            del user
            workflow_inputs.append(inputs)
            payload = json.loads(FIXTURE_DIAGNOSIS.read_text(encoding="utf-8"))
            payload["case_id"] = inputs["case_id"]
            return CandidateRunResult(
                run_id="run-fixture",
                backend="dify",
                candidate_payload=payload,
            )

        def synthesize_audio(self, text: str, user: str) -> None:
            del user
            audio_calls.append(text)
            raise AssertionError("Phase 2 probe must not invoke TTS")

    monkeypatch.setattr("debugmate.probe.DifyBackend", SuccessfulBackend)
    configured = DebugMateSettings.from_env({"DIFY_API_KEY": SENTINEL})

    outcome = run_cloud_probe(configured, tmp_path / "evidence")
    report = json.loads((outcome.bundle_path / "probe-results.json").read_text(encoding="utf-8"))

    assert outcome.exit_code == 0
    assert audio_calls == []
    assert len(workflow_inputs) == 1
    generation_request = workflow_inputs[0]["generation_request"]
    assert isinstance(generation_request, dict)
    assert generation_request["case_id"] == outcome.case_id
    assert generation_request["observed_facts"]
    assert generation_request["evidence"]
    assert generation_request["routing"]["category"] == "dependency_environment"
    assert {item["capability_id"]: item["status"] for item in report["capabilities"]} == {
        "C01": "pass",
        "C02": "pass",
        "C03": "not-tested",
        "C04": "not-tested",
        "C05": "pass",
        "C06": "not-tested",
        "C07": "not-tested",
    }
    assert not (outcome.bundle_path / "recap.mp3").exists()
    assert json.loads((outcome.bundle_path / "recap.json").read_text(encoding="utf-8")) == {
        "recap_text": (
            "Confirm the active interpreter, check whether the package is installed there, "
            "then install and verify only after reviewing the command."
        ),
    }
    c07 = next(item for item in report["capabilities"] if item["capability_id"] == "C07")
    assert c07["status"] == "not-tested"
    assert c07["evidence_path"] is None


def test_cloud_probe_preserves_upload_evidence_when_c05_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class SemanticallyInvalidBackend:
        def __init__(self, configured: DebugMateSettings) -> None:
            del configured

        def upload_file(self, path: Path, user: str) -> SimpleNamespace:
            del path, user
            return SimpleNamespace(file_id="file-fixture", filename="input.json", backend="dify")

        def run_workflow(self, inputs: dict[str, object], user: str) -> CandidateRunResult:
            del inputs, user
            payload = json.loads(FIXTURE_DIAGNOSIS.read_text(encoding="utf-8"))
            payload["category"] = "unknown"
            payload["observed_facts"] = []
            payload["evidence"] = []
            payload["support_links"] = []
            payload["root_cause_candidates"] = []
            return CandidateRunResult(
                run_id="run-semantic-mismatch",
                backend="dify",
                candidate_payload=payload,
            )

    monkeypatch.setattr("debugmate.probe.DifyBackend", SemanticallyInvalidBackend)
    configured = DebugMateSettings.from_env({"DIFY_API_KEY": SENTINEL})

    outcome = run_cloud_probe(configured, tmp_path / "evidence")
    statuses = {item.capability_id: item.status.value for item in outcome.report.capabilities}

    assert outcome.exit_code == 1
    assert statuses == {
        "C01": "pass",
        "C02": "pass",
        "C03": "not-tested",
        "C04": "not-tested",
        "C05": "fail",
        "C06": "not-tested",
        "C07": "not-tested",
    }


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
    repository = Path.cwd().resolve()
    matrix = json.loads(Path("platform/dify/capability-matrix.json").read_text(encoding="utf-8"))
    expected_evidence = {
        "C01": "evidence/dify-live/2026-08-08/cloud-probe/"
        "case_d2c4d21672c14d9bad7f7fe95ee86653/dify-upload.json",
        "C02": "evidence/dify-live/2026-08-08/cloud-probe/"
        "case_d2c4d21672c14d9bad7f7fe95ee86653/dify-upload.json",
        "C03": "evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json",
        "C04": "evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json",
        "C05": "evidence/dify-live/2026-08-08/cloud-probe/"
        "case_d2c4d21672c14d9bad7f7fe95ee86653/diagnosis.json",
        "C06": "evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json",
        "C07": "evidence/dify-live/2026-08-09/tts/dify-recap.mp3",
    }
    expected_statuses = {
        "C01": "pass",
        "C02": "pass",
        "C03": "pass",
        "C04": "pass",
        "C05": "pass",
        "C06": "blocked",
        "C07": "pass",
    }

    assert tuple(item["capability_id"] for item in matrix["capabilities"]) == CAPABILITY_IDS
    for item in matrix["capabilities"]:
        capability_id = item["capability_id"]
        assert item["status"] in {"pass", "not-tested", "blocked"}
        assert item["status"] == expected_statuses[capability_id]
        if item["status"] in {"pass", "blocked"}:
            evidence_path = item["evidence_path"]
            assert evidence_path == expected_evidence[capability_id]
            relative_path = Path(evidence_path)
            assert not relative_path.is_absolute()
            assert ".." not in relative_path.parts
            resolved_path = (repository / relative_path).resolve(strict=True)
            resolved_path.relative_to(repository)
            assert resolved_path.is_file()
            assert (
                subprocess.run(
                    ["git", "check-ignore", "--", evidence_path],
                    check=False,
                    capture_output=True,
                ).returncode
                == 1
            )
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", "--", evidence_path],
                check=True,
                capture_output=True,
            )
            assert item["sha256"] == hashlib.sha256(resolved_path.read_bytes()).hexdigest()
            if item["status"] == "blocked":
                blocker_text = resolved_path.read_text(encoding="utf-8")
                blocker = json.loads(blocker_text)
                assert blocker["capability_id"] == capability_id
                assert blocker["status"] == "blocked"
                assert blocker["reason_code"]
                assert not re.search(
                    r"(?i)(bearer\s+|authorization\s*[:=]|api[_ -]?key\s*[:=]|"
                    r"csrf|session[_ -]?token|cookie\s*[:=]|[A-Z]:\\Users\\)",
                    blocker_text,
                )
        elif item["status"] == "not-tested":
            assert item["evidence_path"] is None
            assert item["sha256"] is None
        else:
            raise AssertionError(f"unsupported capability status: {item['status']}")

    status_by_id = {item["capability_id"]: item["status"] for item in matrix["capabilities"]}
    passing_ids = {
        capability_id for capability_id, status in status_by_id.items() if status == "pass"
    }
    assert passing_ids == {"C01", "C02", "C03", "C04", "C05", "C07"}


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
