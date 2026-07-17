"""Real Microsoft Edge visual verification for the Phase 4 workbench.

The browser marker deliberately launches the loopback-only application rather
than loading a fixture HTML page.  Screenshots are evidence of the currently
implemented Gradio application, including failures that block Phase 4 visual
acceptance.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

from debugmate.evidence import RunManifest, RunStatus

pytestmark = pytest.mark.browser

_ROOT = Path(__file__).resolve().parents[2]
_EVIDENCE = _ROOT / "evidence" / "ui" / "phase4"
_FAILURE_SCREENSHOT_ENV = "DEBUGMATE_UI_FAILURE_SCREENSHOT"
_FAILURE_SCREENSHOT = _EVIDENCE / "tmp" / "GAP-01-layout-red.png"
_UI_BASE_URL_ENV = "DEBUGMATE_UI_BASE_URL"
_QA_CAPABILITY_ENV = "DEBUGMATE_QA_CAPABILITY"
_QA_HEADER = "x-debugmate-qa-capability"
_QA_ROUTE = "/_debugmate/qa"
_QA_STAGING_ENV = "DEBUGMATE_QA_STAGING_DIR"
_QA_STAGING_ROW_KEYS = {
    "schema_version",
    "scenario",
    "viewport",
    "status_sha256",
    "metadata_sha256",
    "screenshot_sha256",
}
_STRICT_LOOPBACK_BASE_URL = re.compile(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})\Z")
_RUNNER = _ROOT / "scripts" / "run-phase4-browser-layout-qa.ps1"
_LOCAL_LIVE_RUNNER = _ROOT / "scripts" / "run-phase4-local-live-qa.ps1"
_LOCAL_LIVE_SCREENSHOT_ENV = "DEBUGMATE_UI_SCREENSHOT_PATH"
_LOCAL_LIVE_LEDGER_ENV = "DEBUGMATE_UI_LEDGER_PATH"
_LOCAL_LIVE_LEDGER = _EVIDENCE / "local-live-vq01.json"
_LOCAL_LIVE_RESULTS = _ROOT / ".debugmate-runtime" / "results"
_LOCAL_LIVE_EVIDENCE = _ROOT / ".debugmate-runtime" / "evidence"
_LOCAL_LIVE_LEDGER_KEYS = {
    "evidence_version",
    "viewport",
    "status",
    "mode",
    "fixture_id",
    "fixture_name",
    "backend",
    "case_id_sha256",
    "source_run_id_sha256",
    "result_id_sha256",
    "screenshot_sha256",
    "body_horizontal_overflow",
    "server_owner",
    "verified_at_utc",
}


def test_local_live_runner_has_single_owner_and_evidence_contract() -> None:
    source = _LOCAL_LIVE_RUNNER.read_text(encoding="utf-8")

    assert "[System.Net.IPAddress]::Loopback" in source
    assert "Start-Process" in source and "-PassThru" in source
    assert "-WindowStyle Hidden" in source
    assert "debugmate.ui.serve" in source
    assert "--host', '127.0.0.1'" in source
    assert "DEBUGMATE_UI_BASE_URL" in source
    assert _LOCAL_LIVE_SCREENSHOT_ENV in source
    assert _LOCAL_LIVE_LEDGER_ENV in source
    assert "New-EvidencePairTransaction" in source
    assert "Complete-EvidencePairTransaction" in source
    assert "Restore-EvidencePairTransaction" in source
    assert "test_vq_01_real_loopback_local_approval_produces_completed_live_result" in source
    assert "Wait-ForLoopbackPortClosed -Port $port" in source
    assert "Stop-Process -InputObject $Process" in source
    assert "fixtures/" not in source and "fixtures\\" not in source
    assert "RedirectStandard" not in source


def test_local_live_ledger_has_exact_redacted_allowlist() -> None:
    payload = json.loads(_LOCAL_LIVE_LEDGER.read_text(encoding="utf-8"))

    assert set(payload) == _LOCAL_LIVE_LEDGER_KEYS
    assert payload["evidence_version"] == 1
    assert payload["viewport"] == {"width": 1366, "height": 768}
    assert payload["status"] == "completed"
    assert payload["mode"] == "live"
    assert payload["fixture_id"] is None
    assert payload["fixture_name"] is None
    assert payload["backend"] == "local-rule-v1"
    assert payload["body_horizontal_overflow"] is False
    assert payload["server_owner"] == "run-phase4-local-live-qa.ps1"
    assert (
        payload["screenshot_sha256"]
        == hashlib.sha256((_EVIDENCE / "VQ-01-live-local.png").read_bytes()).hexdigest()
    )
    verified_at = datetime.fromisoformat(payload["verified_at_utc"].replace("Z", "+00:00"))
    assert payload["verified_at_utc"].endswith("Z")
    assert verified_at.tzinfo is UTC
    for key in (
        "case_id_sha256",
        "source_run_id_sha256",
        "result_id_sha256",
        "screenshot_sha256",
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", payload[key])


def test_local_live_runner_failure_restores_old_pair_and_clears_staging(tmp_path: Path) -> None:
    source = _LOCAL_LIVE_RUNNER.read_text(encoding="utf-8")
    assert "if ($MyInvocation.InvocationName -eq '.')" in source

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    screenshot = evidence_dir / "formal.png"
    ledger = evidence_dir / "formal.json"
    screenshot.write_bytes(b"old-png-bytes")
    ledger.write_bytes(b"old-ledger-bytes")
    runner = str(_LOCAL_LIVE_RUNNER).replace("'", "''")
    screenshot_arg = str(screenshot).replace("'", "''")
    ledger_arg = str(ledger).replace("'", "''")
    command = rf"""
$ErrorActionPreference = 'Stop'
. '{runner}'
$transaction = New-EvidencePairTransaction `
    -ScreenshotPath '{screenshot_arg}' `
    -LedgerPath '{ledger_arg}'
try {{
    [System.IO.File]::WriteAllBytes($transaction.StagingScreenshot, [byte[]](1, 2, 3))
    [System.IO.File]::WriteAllBytes($transaction.StagingLedger, [byte[]](4, 5, 6))
    throw 'controlled validation failure'
}}
catch {{
    Restore-EvidencePairTransaction -Transaction $transaction
}}
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert screenshot.read_bytes() == b"old-png-bytes"
    assert ledger.read_bytes() == b"old-ledger-bytes"
    assert sorted(path.name for path in evidence_dir.iterdir()) == ["formal.json", "formal.png"]


def _run_transaction_fault(tmp_path: Path, fault: str) -> dict[str, object]:
    evidence_dir = tmp_path / fault
    evidence_dir.mkdir()
    screenshot = evidence_dir / "formal.png"
    ledger = evidence_dir / "formal.json"
    screenshot.write_bytes(b"old-png-bytes")
    ledger.write_bytes(b"old-ledger-bytes")
    staged_png = evidence_dir / "new.png"
    staged_png.write_bytes((_EVIDENCE / "VQ-01-live-local.png").read_bytes())
    staged_ledger = evidence_dir / "new.json"
    staged_ledger.write_text(
        json.dumps(
            {
                "evidence_version": 1,
                "viewport": {"width": 1366, "height": 768},
                "status": "completed",
                "mode": "live",
                "fixture_id": None,
                "fixture_name": None,
                "backend": "local-rule-v1",
                "case_id_sha256": "1" * 64,
                "source_run_id_sha256": "2" * 64,
                "result_id_sha256": "3" * 64,
                "screenshot_sha256": hashlib.sha256(staged_png.read_bytes()).hexdigest(),
                "body_horizontal_overflow": False,
                "server_owner": "run-phase4-local-live-qa.ps1",
                "verified_at_utc": "2026-07-16T08:00:00.000000Z",
            }
        ),
        encoding="utf-8",
    )

    def quote(value: object) -> str:
        return str(value).replace("'", "''")

    command = rf"""
$ErrorActionPreference = 'Stop'
. '{quote(_LOCAL_LIVE_RUNNER)}'
$fault = '{fault}'
$move = {{
    param($Source, $Destination)
    $sourceName = [IO.Path]::GetFileName([string]$Source)
    $destinationName = [IO.Path]::GetFileName([string]$Destination)
    $backupScreenshot = $fault -eq 'backup_screenshot' -and `
        $sourceName -eq 'formal.png' -and $destinationName -match 'backup'
    $backupLedger = $fault -eq 'backup_ledger' -and `
        $sourceName -eq 'formal.json' -and $destinationName -match 'backup'
    $promoteScreenshot = $fault -eq 'promote_screenshot' -and `
        $sourceName -match 'staging.*png' -and $destinationName -eq 'formal.png'
    $promoteLedger = $fault -eq 'promote_ledger' -and `
        $sourceName -match 'staging.*json' -and $destinationName -eq 'formal.json'
    if ($backupScreenshot -or $backupLedger -or $promoteScreenshot -or $promoteLedger) {{
        throw "injected move failure: $fault"
    }}
    Microsoft.PowerShell.Management\Move-Item -LiteralPath $Source -Destination $Destination
}}
$remove = {{
    param($Path)
    $name = [IO.Path]::GetFileName([string]$Path)
    if (($fault -eq 'cleanup_screenshot' -and $name -match '^\.VQ-01.*backup') -or
        ($fault -eq 'cleanup_ledger' -and $name -match '^\.local-live.*backup')) {{
        throw "injected cleanup failure: $fault"
    }}
    Microsoft.PowerShell.Management\Remove-Item -LiteralPath $Path -Force
}}
$transaction = $null
$errorText = $null
try {{
    $transaction = New-EvidencePairTransaction `
        -ScreenshotPath '{quote(screenshot)}' `
        -LedgerPath '{quote(ledger)}' `
        -MoveFile $move `
        -RemoveFile $remove
    [IO.File]::Copy('{quote(staged_png)}', $transaction.StagingScreenshot, $true)
    [IO.File]::Copy('{quote(staged_ledger)}', $transaction.StagingLedger, $true)
    Complete-EvidencePairTransaction -Transaction $transaction
    Commit-EvidencePairTransaction -Transaction $transaction
}}
catch {{ $errorText = $_.Exception.Message }}
$filesBeforeReconcile = @((Get-ChildItem -LiteralPath '{quote(evidence_dir)}').Name | Sort-Object)
if ($fault -match '^cleanup_') {{
    Reconcile-EvidencePairResidue `
        -ScreenshotPath '{quote(screenshot)}' `
        -LedgerPath '{quote(ledger)}'
}}
$summary = [ordered]@{{
    error = $errorText
    screenshot = if (Test-Path -LiteralPath '{quote(screenshot)}') {{
        [Convert]::ToBase64String([IO.File]::ReadAllBytes('{quote(screenshot)}'))
    }} else {{ $null }}
    ledger = if (Test-Path -LiteralPath '{quote(ledger)}') {{
        [Convert]::ToBase64String([IO.File]::ReadAllBytes('{quote(ledger)}'))
    }} else {{ $null }}
    files = @((Get-ChildItem -LiteralPath '{quote(evidence_dir)}').Name | Sort-Object)
    files_before_reconcile = $filesBeforeReconcile
    screenshot_backed_up = if ($null -ne $transaction) {{
        $transaction.Screenshot.BackedUp
    }} else {{ $null }}
    ledger_backed_up = if ($null -ne $transaction) {{
        $transaction.Ledger.BackedUp
    }} else {{ $null }}
    screenshot_promoted = if ($null -ne $transaction) {{
        $transaction.Screenshot.Promoted
    }} else {{ $null }}
    ledger_promoted = if ($null -ne $transaction) {{
        $transaction.Ledger.Promoted
    }} else {{ $null }}
    formal_committed = if ($null -ne $transaction) {{
        $transaction.FormalCommitted
    }} else {{ $null }}
    cleanup_complete = if ($null -ne $transaction) {{
        $transaction.CleanupComplete
    }} else {{ $null }}
}}
$summary | ConvertTo-Json -Compress
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    json_line = next(
        line for line in reversed(completed.stdout.splitlines()) if line.startswith("{")
    )
    return json.loads(json_line)


@pytest.mark.parametrize(
    "fault", ["backup_screenshot", "backup_ledger", "promote_screenshot", "promote_ledger"]
)
def test_evidence_transaction_move_failures_restore_old_pair(tmp_path: Path, fault: str) -> None:
    result = _run_transaction_fault(tmp_path, fault)

    assert "injected move failure" in str(result["error"])
    assert base64.b64decode(result["screenshot"]) == b"old-png-bytes"
    assert base64.b64decode(result["ledger"]) == b"old-ledger-bytes"
    assert not any("staging" in name or "backup" in name for name in result["files"])


@pytest.mark.parametrize("fault", ["cleanup_screenshot", "cleanup_ledger"])
def test_evidence_transaction_cleanup_failure_keeps_new_pair_and_explicit_residue(
    tmp_path: Path, fault: str
) -> None:
    result = _run_transaction_fault(tmp_path, fault)

    assert "injected cleanup failure" in str(result["error"])
    assert base64.b64decode(result["screenshot"]) != b"old-png-bytes"
    assert base64.b64decode(result["ledger"]) != b"old-ledger-bytes"
    assert result["formal_committed"] is True
    assert result["cleanup_complete"] is False
    assert result["screenshot_promoted"] is True
    assert result["ledger_promoted"] is True
    assert any("backup" in name for name in result["files_before_reconcile"])
    assert not any("staging" in name or "backup" in name for name in result["files"])


def test_source_manifest_backend_is_strictly_observed_and_identity_bound(tmp_path: Path) -> None:
    case_id = "case_" + "1" * 32
    source_run_id = "run_" + "2" * 32
    result_id = "result_" + "3" * 32
    manifest_path = tmp_path / case_id / source_run_id / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    now = datetime.now(UTC)
    manifest = RunManifest(
        manifest_version="1.0.0",
        case_id=case_id,
        status=RunStatus.PASSED,
        created_at_utc=now,
        completed_at_utc=now,
        backend="local-rule-v1",
        workflow_version="test-v1",
        prompt_version="test-v1",
        schema_version="1.1.0",
        knowledge_version="local-rule-v1",
        input_sha256="4" * 64,
        run_id=source_run_id,
        node_states={},
        latency_ms=0,
        token_usage={},
        estimated_cost=0.0,
        artifacts=[],
        probe_capabilities=[],
        source_run_id=None,
    )
    manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")
    result_manifest = {
        "identity": {"case_id": case_id, "source_run_id": source_run_id},
        "result_id": result_id,
    }

    assert (
        _validated_source_backend(
            evidence_root=tmp_path,
            result_manifest=result_manifest,
            dom_source_run_id=source_run_id,
        )
        == "local-rule-v1"
    )
    tampered_case_id = "case_" + "9" * 32
    tampered_path = tmp_path / tampered_case_id / source_run_id / "manifest.json"
    tampered_path.parent.mkdir(parents=True)
    tampered_path.write_bytes(manifest_path.read_bytes())
    result_manifest["identity"]["case_id"] = tampered_case_id
    with pytest.raises(AssertionError):
        _validated_source_backend(
            evidence_root=tmp_path,
            result_manifest=result_manifest,
            dom_source_run_id=source_run_id,
        )


def _validated_source_backend(
    *, evidence_root: Path, result_manifest: dict[str, object], dom_source_run_id: str
) -> str:
    identity = result_manifest["identity"]
    assert isinstance(identity, dict)
    case_id = identity["case_id"]
    source_run_id = identity["source_run_id"]
    assert isinstance(case_id, str) and re.fullmatch(r"case_[0-9a-f]{32}", case_id)
    assert isinstance(source_run_id, str) and re.fullmatch(r"run_[0-9a-f]{32}", source_run_id)
    assert source_run_id == dom_source_run_id
    manifest_path = evidence_root / case_id / source_run_id / "manifest.json"
    source_manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert source_manifest.case_id == case_id
    assert source_manifest.run_id == source_run_id
    observed_backend = source_manifest.backend
    assert observed_backend == "local-rule-v1"
    return observed_backend


def _reserve_loopback_port() -> int:
    """Reserve a loopback port only long enough to obtain its number."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _start_loopback_server(port: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "debugmate.ui.serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _parse_supplied_browser_base_url(value: str) -> str:
    """Accept only a literal IPv4 loopback URL with a valid nonzero port."""

    match = _STRICT_LOOPBACK_BASE_URL.fullmatch(value)
    if match is None or int(match.group(1)) > 65535:
        raise ValueError(
            f"{_UI_BASE_URL_ENV} must be literal http://127.0.0.1:N with N between 1 and 65535"
        )
    return value


def _wait_for_config(
    base_url: str,
    process: subprocess.Popen[bytes] | None = None,
    *,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.25,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    owner = "loopback Gradio process" if process is not None else "supplied loopback Gradio"
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            pytest.fail("loopback Gradio process exited before /config became ready")
        try:
            response = httpx.get(f"{base_url}/config", timeout=1.0)
            payload = response.json()
            if (
                response.status_code == 200
                and isinstance(payload, dict)
                and isinstance(payload.get("components"), list)
            ):
                return base_url
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(poll_interval_seconds)
    pytest.fail(f"{owner} /config did not become ready in {timeout_seconds:g} seconds")


def _stop_loopback_server(process: subprocess.Popen[bytes], port: int) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return
        time.sleep(0.1)
    pytest.fail("captured loopback server port remained open after cleanup")


@pytest.fixture
def browser_base_url() -> Iterator[str]:
    """Supply one ready loopback UI server without ever taking over an external owner."""

    supplied_base_url = os.environ.get(_UI_BASE_URL_ENV)
    if supplied_base_url is not None:
        try:
            base_url = _parse_supplied_browser_base_url(supplied_base_url)
        except ValueError as error:
            pytest.fail(str(error))
        yield _wait_for_config(base_url)
        return

    port = _reserve_loopback_port()
    process = _start_loopback_server(port)
    try:
        yield _wait_for_config(f"http://127.0.0.1:{port}", process)
    finally:
        _stop_loopback_server(process, port)


def _capture_failure_screenshot(page) -> Path | None:
    """Capture only an explicitly requested, ignored temporary diagnostic image."""

    if os.environ.get(_FAILURE_SCREENSHOT_ENV) != "1":
        return None
    _FAILURE_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(_FAILURE_SCREENSHOT), full_page=True)
    return _FAILURE_SCREENSHOT


def _qa_context(browser, browser_base_url: str):
    capability = os.environ.get(_QA_CAPABILITY_ENV)
    if capability is None:
        pytest.skip("runner-owned truth-state QA server is not active")
    assert re.fullmatch(r"qa_[0-9a-f]{64}", capability)
    context = browser.new_context(
        viewport={"width": 1366, "height": 768},
        extra_http_headers={_QA_HEADER: capability},
    )
    return context, capability


def _activate_qa(context, browser_base_url: str, scenario: str) -> None:
    response = context.request.post(f"{browser_base_url}{_QA_ROUTE}", data={"scenario": scenario})
    assert response.status == 200
    assert response.json() == {"accepted": scenario}


def _qa_stage_command(
    browser_base_url: str, capability: str, action: str, stage: str
) -> dict[str, object]:
    """Use a separately owned APIRequestContext so a held UI stream cannot deadlock it."""

    with sync_playwright() as worker_playwright:
        request = worker_playwright.request.new_context(extra_http_headers={_QA_HEADER: capability})
        try:
            response = request.post(
                f"{browser_base_url}{_QA_ROUTE}",
                data={"action": action, "stage": stage},
                timeout=40_000,
            )
            assert response.status == 200
            payload = response.json()
            assert isinstance(payload, dict)
            return payload
        finally:
            request.dispose()


def _release_qa_stage(context, browser_base_url: str, stage: str) -> dict[str, object]:
    response = context.request.post(
        f"{browser_base_url}{_QA_ROUTE}",
        data={"action": "release", "stage": stage},
        timeout=10_000,
    )
    assert response.status == 200
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def _write_qa_staging(page, scenario: str) -> None:
    """Write runner-owned staging only; all captured identity-bearing text is hashed."""

    configured = os.environ.get(_QA_STAGING_ENV)
    assert configured is not None
    root = Path(configured).resolve()
    allowed_root = (_EVIDENCE / "staging").resolve()
    assert root.is_relative_to(allowed_root)
    root.mkdir(parents=True, exist_ok=True)
    screenshot = root / f"{scenario}.png"
    row_path = root / f"{scenario}.row.json"
    page.screenshot(path=str(screenshot), full_page=True)
    status = page.locator("#diagnostic-status").inner_text()
    metadata = page.locator("#result-metadata").inner_text()
    row = {
        "schema_version": "phase4-qa-staging-v1",
        "scenario": scenario,
        "viewport": "1366x768",
        "status_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
        "metadata_sha256": hashlib.sha256(metadata.encode("utf-8")).hexdigest(),
        "screenshot_sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
    }
    assert set(row) == _QA_STAGING_ROW_KEYS
    row_path.write_text(json.dumps(row, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    capability = os.environ[_QA_CAPABILITY_ENV]
    resource_urls = page.evaluate(
        "() => performance.getEntries().map(entry => entry.name).join('\\n')"
    )
    surfaces = (
        page.locator("html").inner_text(),
        page.url,
        resource_urls,
        json.dumps(row, sort_keys=True),
        row_path.read_text(encoding="utf-8"),
    )
    assert all(capability not in surface for surface in surfaces)
    assert capability.encode("utf-8") not in screenshot.read_bytes()


def test_vq_02_completed_replay_truth_is_visible_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = None
        try:
            context, _capability = _qa_context(browser, browser_base_url)
            _activate_qa(context, browser_base_url, "vq-02-replay")
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            page.get_by_role("button", name="加载回放案例", exact=True).click()
            status = page.locator("#diagnostic-status").first
            status.get_by_text("✓ 已完成", exact=False).wait_for(timeout=90_000)
            assert "离线回放" in status.inner_text()
            metadata = page.locator("#result-metadata").first.inner_text()
            page.get_by_role("tab", name="引用与下载", exact=True).click()
            download_metadata = page.locator("#download-metadata").first.inner_text()
            body = page.locator("body").inner_text()
            assert "离线回放" in metadata
            assert "ModuleNotFoundError：缺少虚构依赖包" in metadata
            assert "来源运行" in metadata
            assert "实时诊断" not in metadata
            assert "离线回放" in download_metadata
            assert "云端运行成功" not in body
            assert page.get_by_text("下载完整证据包", exact=True).is_visible()
            _write_qa_staging(page, "vq-02")
        finally:
            if context is not None:
                context.close()
            browser.close()


def test_vq_03_running_queue_stages_are_truthful_and_conflict_safe_in_real_edge(
    browser_base_url: str,
) -> None:
    stage_labels = {
        "source": "验证来源",
        "presentation": "整理诊断",
        "report": "生成报告",
        "card": "绘制诊断卡",
        "audio": "生成语音",
        "consistency": "一致性校验",
        "publish": "发布结果包",
    }
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = None
        held_stage: str | None = None
        try:
            context, capability = _qa_context(browser, browser_base_url)
            _activate_qa(context, browser_base_url, "vq-03-running")
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            page.locator("#replay-action").click()
            with ThreadPoolExecutor(max_workers=1) as executor:
                for index, (stage, label) in enumerate(stage_labels.items()):
                    future = executor.submit(
                        _qa_stage_command,
                        browser_base_url,
                        capability,
                        "hold",
                        stage,
                    )
                    snapshot = future.result(timeout=45)
                    held_stage = stage
                    assert snapshot == {
                        "stage": stage,
                        "completed_stages": list(stage_labels)[:index],
                    }
                    status = page.locator("#diagnostic-status").first
                    expect(status).to_contain_text(label, timeout=30_000)
                    assert page.locator("#replay-action").is_disabled()
                    assert page.locator("#local-preview").is_disabled()
                    assert page.locator("#local-approve").is_disabled()
                    assert page.locator("#partial-retry").is_disabled()
                    assert not re.search(r"\b\d+(?:\.\d+)?\s*%", status.inner_text())
                    if stage == "publish":
                        _write_qa_staging(page, "vq-03")
                    assert _release_qa_stage(context, browser_base_url, stage) == {
                        "released": stage
                    }
                    held_stage = None
            page.locator("#diagnostic-status").get_by_text("✓ 已完成", exact=False).wait_for(
                timeout=90_000
            )
        finally:
            if held_stage is not None and context is not None:
                with suppress(Exception):
                    _release_qa_stage(context, browser_base_url, held_stage)
            if context is not None:
                context.close()
            browser.close()


def _wait_for_terminal_status(page, copy: str) -> None:
    page.locator("#diagnostic-status").get_by_text(copy, exact=False).wait_for(timeout=90_000)


def test_vq_06_vq_07_partial_recovery_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            for scenario, failed_stage in (
                ("vq-06-tts-failed", "生成语音"),
                ("vq-07-png-failed", "绘制诊断卡"),
            ):
                context, _capability = _qa_context(browser, browser_base_url)
                try:
                    _activate_qa(context, browser_base_url, scenario)
                    page = context.new_page()
                    page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
                    page.locator(".gradio-container").wait_for(timeout=30_000)
                    page.locator("#replay-action").click()
                    _wait_for_terminal_status(page, "⚠ 部分完成")
                    details = page.locator("#failure-details").inner_text()
                    for label in (
                        "失败节点",
                        "安全错误码",
                        "已完成阶段",
                        "继承阶段",
                        "仍可使用的结果",
                        "可重试范围",
                        "建议操作",
                    ):
                        assert label in details
                    assert failed_stage in details
                    assert page.locator("#partial-retry").is_enabled()
                    page.get_by_role("tab", name="引用与下载", exact=True).click()
                    expect(page.locator("#download-result")).to_contain_text("下载部分结果包")
                    if scenario == "vq-06-tts-failed":
                        page.get_by_role("tab", name="诊断卡", exact=True).click()
                        page.locator("#diagnostic-card img").wait_for(timeout=30_000)
                        page.get_by_role("tab", name="语音复盘", exact=True).click()
                        expect(page.locator("#diagnostic-audio")).to_be_hidden()
                        assert "tts_failed" in page.locator("#audio-metadata").inner_text()
                    else:
                        page.get_by_role("tab", name="诊断卡", exact=True).click()
                        assert page.locator("#diagnostic-card img[src]").count() == 0
                        page.get_by_role("tab", name="语音复盘", exact=True).click()
                        expect(page.locator("#audio-metadata")).to_contain_text(
                            "语音后端", timeout=30_000
                        )
                        expect(page.locator("#diagnostic-audio")).to_be_visible()
                    _write_qa_staging(page, "-".join(scenario.split("-")[:2]))
                    page.locator("#partial-retry").click()
                    _wait_for_terminal_status(page, "✓ 已完成")
                    assert page.locator("#partial-retry").is_disabled()
                finally:
                    context.close()

        finally:
            browser.close()


def test_vq_08_safe_failure_and_vq_09_fallback_truth_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            context, _capability = _qa_context(browser, browser_base_url)
            try:
                _activate_qa(context, browser_base_url, "vq-08-source-invalid")
                page = context.new_page()
                page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
                page.locator(".gradio-container").wait_for(timeout=30_000)
                page.locator("#replay-action").click()
                expect(page.locator("#diagnostic-status")).to_contain_text(
                    "诊断失败", timeout=90_000
                )
                details = page.locator("#failure-details").inner_text()
                for label in (
                    "失败节点",
                    "安全错误码",
                    "已完成阶段",
                    "继承阶段",
                    "仍可使用的结果",
                    "可重试范围",
                    "建议操作",
                ):
                    assert label in details
                assert "source_bundle_invalid" in details
                assert not re.search(r"(?:[A-Za-z]:\\|/Users/|/home/|Traceback)", details)
                assert page.locator("#diagnostic-card img[src]").count() == 0
                expect(page.locator("#diagnostic-audio")).to_be_hidden()
                page.get_by_role("tab", name="引用与下载", exact=True).click()
                expect(page.locator("#download-result")).to_be_hidden()
                _write_qa_staging(page, "vq-08")
            finally:
                context.close()

            context, _capability = _qa_context(browser, browser_base_url)
            try:
                _activate_qa(context, browser_base_url, "vq-09-fallback")
                page = context.new_page()
                page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
                page.locator(".gradio-container").wait_for(timeout=30_000)
                page.locator("#replay-action").click()
                _wait_for_terminal_status(page, "✓ 已完成")
                status = page.locator("#diagnostic-status").inner_text()
                assert "语音已降级" in status
                assert "sapi" in status
                page.get_by_role("tab", name="语音复盘", exact=True).click()
                audio_metadata = page.locator("#audio-metadata").inner_text()
                assert "语音后端：sapi" in audio_metadata
                assert "是否降级：是" in audio_metadata
                assert "降级原因：无" not in audio_metadata
                expect(page.locator("#diagnostic-audio")).to_be_visible()
                page.get_by_role("tab", name="引用与下载", exact=True).click()
                expect(page.locator("#download-result")).to_contain_text("下载完整证据包")
                _write_qa_staging(page, "vq-09")
            finally:
                context.close()
        finally:
            browser.close()


def test_vq_10_single_field_correction_creates_new_identity_and_preserves_old_run(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = None
        try:
            context, _capability = _qa_context(browser, browser_base_url)
            _activate_qa(context, browser_base_url, "vq-02-replay")
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            page.locator("#replay-action").click()
            _wait_for_terminal_status(page, "✓ 已完成")
            metadata = page.locator("#result-metadata")
            old_identity = metadata.inner_text()

            field = page.get_by_label("包/模块", exact=True)
            old_value = field.input_value()
            new_value = f"{old_value}x"
            field.click()
            field.press("End")
            field.type("x")
            pending = page.get_by_label("修改草稿", exact=True)
            expect(pending).to_have_value(re.compile(re.escape(new_value)), timeout=30_000)
            pending_copy = pending.input_value()
            assert "有 1 项未确认修改" in pending_copy
            assert old_value in pending_copy and new_value in pending_copy and "→" in pending_copy
            assert metadata.inner_text() == old_identity

            confirm = page.get_by_role("button", name="确认修改并重新诊断", exact=True)
            assert confirm.is_enabled()
            confirm.click()
            create = page.get_by_role("button", name="创建新运行", exact=True)
            create.wait_for(timeout=30_000)
            assert create.is_enabled()
            assert metadata.inner_text() == old_identity
            create.click()
            page.wait_for_function(
                "([selector, oldValue]) => "
                "document.querySelector(selector)?.innerText !== oldValue",
                arg=["#result-metadata", old_identity],
                timeout=90_000,
            )
            new_identity = metadata.inner_text()
            assert new_identity != old_identity
            assert "来源运行" in new_identity
            _write_qa_staging(page, "vq-10")

            _activate_qa(context, browser_base_url, "vq-02-replay")
            recovery = context.new_page()
            recovery.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            recovery.locator(".gradio-container").wait_for(timeout=30_000)
            recovery.locator("#replay-action").click()
            _wait_for_terminal_status(recovery, "✓ 已完成")
            assert recovery.locator("#result-metadata").inner_text() == old_identity
        finally:
            if context is not None:
                context.close()
            browser.close()


@pytest.fixture
def _external_config_server() -> Iterator[str]:
    """Provide an independently owned ready server for lifecycle coverage."""

    class ConfigHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            if self.path == "/config":
                body = b'{"components": []}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ConfigHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        assert thread.is_alive(), "browser fixture terminated an externally owned server"
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.mark.parametrize(
    "value",
    [
        "https://127.0.0.1:8000",
        "http://localhost:8000",
        "http://[::1]:8000",
        "http://127.0.0.1:8000/config",
        "http://127.0.0.1:8000?debug=1",
        "http://user:password@127.0.0.1:8000",
        "http://127.0.0.1:0",
        "http://127.0.0.1:65536",
    ],
)
def test_supplied_browser_base_url_rejects_everything_except_literal_ipv4_loopback(
    value: str,
) -> None:
    with pytest.raises(ValueError, match="literal http://127\\.0\\.0\\.1:N"):
        _parse_supplied_browser_base_url(value)


def test_supplied_browser_base_url_requires_ready_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(200, json={"components": "not-a-list"}),
    )

    with pytest.raises(pytest.fail.Exception, match="supplied loopback Gradio /config"):
        _wait_for_config(
            "http://127.0.0.1:8000",
            process=None,
            timeout_seconds=0.01,
            poll_interval_seconds=0,
        )


@pytest.mark.parametrize("payload", [[], "not-an-object"])
def test_supplied_browser_base_url_ignores_non_object_config_payloads(
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(200, json=payload),
    )

    with pytest.raises(pytest.fail.Exception, match="supplied loopback Gradio /config"):
        _wait_for_config(
            "http://127.0.0.1:8000",
            process=None,
            timeout_seconds=0.01,
            poll_interval_seconds=0,
        )


def _controlled_runner_failure() -> tuple[dict[str, object], subprocess.CompletedProcess[str]]:
    runner_path = str(_RUNNER).replace("'", "''")
    sentinel = "http://127.0.0.1:61234"
    command = f"""
$ErrorActionPreference = 'Stop'
$summary = [ordered]@{{ error = $null; base_url = $null; debugmate_server_count = $null }}
try {{
    & '{runner_path}' -FailOwnershipAuditForSmoke
}}
catch {{
    $summary.error = $_.Exception.Message
}}
$summary.base_url = $env:DEBUGMATE_UI_BASE_URL
$summary.debugmate_server_count = @(
    Get-CimInstance Win32_Process |
        Where-Object {{ $_.CommandLine -match 'debugmate\\.ui\\.serve' }}
).Count
$summary | ConvertTo-Json -Compress
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=_ROOT,
        env={**os.environ, _UI_BASE_URL_ENV: sentinel},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    json_line = next(
        (line for line in reversed(completed.stdout.splitlines()) if line.lstrip().startswith("{")),
        "",
    )
    return json.loads(json_line), completed


def test_runner_cleanup_contract_restores_context_after_cleanup_errors() -> None:
    source = _RUNNER.read_text(encoding="utf-8")
    cleanup_start = source.index("finally {\n    $cleanupErrors")
    port_probe = source.index("Wait-ForLoopbackPortClosed -Port $port", cleanup_start)
    restore_environment = source.index("if ($hadBaseUrl)", cleanup_start)
    pop_location = source.index("Pop-Location", cleanup_start)
    raise_cleanup_error = source.index("if ($cleanupErrors.Count -gt 0)", cleanup_start)

    assert "function Stop-CapturedServer" in source
    assert "Stop-Process -InputObject $Process" in source
    assert "$serverProcessStartUtc" in source
    assert "$serverProcessVerified" not in source
    assert port_probe < restore_environment < pop_location < raise_cleanup_error


def test_runner_controlled_failure_cleans_server_and_restores_base_url() -> None:
    summary, completed = _controlled_runner_failure()

    assert completed.returncode == 0, completed.stderr
    assert "command line does not match" in str(summary["error"])
    assert summary["base_url"] == "http://127.0.0.1:61234"
    assert summary["debugmate_server_count"] == 0
    assert "Captured loopback server stopped; port" in completed.stdout


def _runner_config_readiness_results() -> dict[str, bool]:
    runner_path = str(_RUNNER).replace("'", "''")
    command = f"""
$ErrorActionPreference = 'Stop'
function Invoke-WebRequest {{
    return [pscustomobject]@{{
        StatusCode = $global:configPayload.status_code
        Content = $global:configPayload.content
    }}
}}
. '{runner_path}'
$cases = [ordered]@{{
    string = [pscustomobject]@{{ status_code = 200; content = '"ordinary string"' }}
    wrapped_object = [pscustomobject]@{{
        status_code = 200
        content = (ConvertTo-Json -InputObject '{{"components":[]}}' -Compress)
    }}
    array = [pscustomobject]@{{ status_code = 200; content = '[]' }}
    number = [pscustomobject]@{{ status_code = 200; content = '7' }}
    object = [pscustomobject]@{{ status_code = 200; content = '{{"components":[]}}' }}
    object_with_empty_key = [pscustomobject]@{{
        status_code = 200
        content = '{{"components":[],"":null}}'
    }}
    not_found = [pscustomobject]@{{ status_code = 404; content = '{{"components":[]}}' }}
}}
$results = [ordered]@{{}}
foreach ($case in $cases.GetEnumerator()) {{
    $global:configPayload = $case.Value
    $results[$case.Key] = [bool](Test-ConfigReady -BaseUrl 'http://127.0.0.1:8000')
}}
$results | ConvertTo-Json -Compress
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_runner_config_validation_requires_a_root_object_with_components_list() -> None:
    source = _RUNNER.read_text(encoding="utf-8")
    assert "if ($MyInvocation.InvocationName -eq '.')" in source
    assert "return $config -match" not in source

    assert _runner_config_readiness_results() == {
        "string": False,
        "wrapped_object": False,
        "array": False,
        "number": False,
        "object": True,
        "object_with_empty_key": True,
        "not_found": False,
    }
    assert "$config -is [string]" not in source
    assert "DeserializeObject($config)" not in source


def test_browser_fixture_reuses_external_url_without_terminating_its_server(
    _external_config_server: str,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    monkeypatch.setenv(_UI_BASE_URL_ENV, _external_config_server)

    assert request.getfixturevalue("browser_base_url") == _external_config_server


def test_failure_screenshot_capture_is_opt_in_and_uses_only_ignored_temp_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ScreenshotPage:
        def __init__(self) -> None:
            self.paths: list[str] = []

        def screenshot(self, *, path: str, full_page: bool) -> None:
            assert full_page is True
            self.paths.append(path)

    page = ScreenshotPage()
    monkeypatch.delenv(_FAILURE_SCREENSHOT_ENV, raising=False)
    assert _capture_failure_screenshot(page) is None
    assert page.paths == []

    monkeypatch.setenv(_FAILURE_SCREENSHOT_ENV, "1")
    assert _capture_failure_screenshot(page) == _FAILURE_SCREENSHOT
    assert page.paths == [str(_FAILURE_SCREENSHOT)]
    assert _FAILURE_SCREENSHOT.is_relative_to(_EVIDENCE / "tmp")
    assert _FAILURE_SCREENSHOT.name != "VQ-01.png"
    assert _FAILURE_SCREENSHOT.name != "GAP-01-VQ-01-failing.png"


def test_gap_01_real_loopback_workbench_has_three_usable_regions(
    browser_base_url: str,
) -> None:
    """RED: the first screen must keep its three regions usable at 1366px."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            for heading in ("输入与抽取", "诊断与证据", "三模态结果"):
                page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=30_000)
            page.get_by_text("固定回放案例", exact=True).wait_for(timeout=30_000)
            page.get_by_role("button", name="加载回放案例", exact=True).wait_for(timeout=30_000)
            visible_before_viewport = []
            for text, locator in (
                ("输入与抽取", page.get_by_role("heading", name="输入与抽取", exact=True)),
                ("诊断与证据", page.get_by_role("heading", name="诊断与证据", exact=True)),
                ("三模态结果", page.get_by_role("heading", name="三模态结果", exact=True)),
                ("固定回放案例", page.get_by_text("固定回放案例", exact=True)),
                ("加载回放案例", page.get_by_role("button", name="加载回放案例", exact=True)),
            ):
                box = locator.bounding_box()
                visible_before_viewport.append(
                    {
                        "text": text,
                        "visible": box is not None
                        and box["width"] > 0
                        and box["height"] > 0
                        and box["y"] >= 0
                        and box["y"] + box["height"] <= 768,
                    }
                )
            screenshot = _capture_failure_screenshot(page)
            metrics = page.evaluate(
                """() => ({
                    regions: [...document.querySelectorAll('.region')].map((element) => {
                        const box = element.getBoundingClientRect();
                        return { width: box.width, y: box.y };
                    }),
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                })"""
            )
        finally:
            browser.close()
    if screenshot is not None:
        assert screenshot.is_file()
    assert len(metrics["regions"]) == 3
    assert all(
        item["width"] >= minimum
        for item, minimum in zip(metrics["regions"], (280, 360, 440), strict=True)
    )
    assert all(item["y"] < 768 for item in metrics["regions"])
    assert visible_before_viewport == [
        {"text": "输入与抽取", "visible": True},
        {"text": "诊断与证据", "visible": True},
        {"text": "三模态结果", "visible": True},
        {"text": "固定回放案例", "visible": True},
        {"text": "加载回放案例", "visible": True},
    ]
    assert metrics["scrollWidth"] == metrics["clientWidth"]


def test_vq_01_real_loopback_local_approval_produces_completed_live_result(
    browser_base_url: str,
) -> None:
    manifests_before = set(_LOCAL_LIVE_RESULTS.glob("case_*/result_*/result-manifest.json"))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            preview = page.get_by_role("button", name="生成本地脱敏预览", exact=True)
            approve = page.get_by_role("button", name="确认预览并开始本地诊断", exact=True)
            preview.wait_for(timeout=30_000)
            assert approve.is_disabled()
            preview.click()
            deadline = time.monotonic() + 30
            while approve.is_disabled() and time.monotonic() < deadline:
                page.wait_for_timeout(100)
            assert approve.is_enabled()
            approve.click()
            status = page.locator("#diagnostic-status").first
            deadline = time.monotonic() + 90
            status_text = ""
            while time.monotonic() < deadline:
                status_text = status.inner_text()
                if "✓ 已完成" in status_text:
                    break
                page.wait_for_timeout(250)
            page.get_by_role("tab", name="文字报告", exact=True).click()
            report_panel = page.locator(".report-panel").first
            report_text = report_panel.inner_text()
            report_visible = report_panel.is_visible()
            page.get_by_role("tab", name="诊断卡", exact=True).click()
            card_image = page.locator("#diagnostic-card img").first
            card_image.wait_for(state="visible", timeout=10_000)
            page.get_by_role("tab", name="引用与下载", exact=True).click()
            download_button = page.locator("text=下载完整证据包").first
            body_text = page.locator("body").inner_text()
            result_metadata = page.locator("#result-metadata").first.inner_text()
            citation_table = page.get_by_text("引用", exact=True).last
            citations_visible = citation_table.is_visible()
            assert download_button.count() == 1, body_text
            download_enabled = download_button.is_enabled(timeout=1_000)
            metrics = page.evaluate(
                """() => ({
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                })"""
            )
            body_horizontal_overflow = metrics["scrollWidth"] > metrics["clientWidth"]

            assert "✓ 已完成" in status_text
            assert "后端：local-rule-v1（本地规则，无云端调用）" in body_text
            assert "实时诊断" in result_metadata
            source_run_match = re.search(r"run_[0-9a-f]{32}", result_metadata)
            assert source_run_match is not None
            assert "fixture_id=null" in result_metadata
            assert "fixture_name=null" in result_metadata
            assert "回放" not in result_metadata
            assert body_text.count(result_metadata.strip()) == 1
            assert "module-not-found" not in result_metadata
            assert "ModuleNotFoundError：缺少虚构依赖包" not in result_metadata
            assert report_visible
            assert "DebugMate" in report_text
            assert citations_visible
            assert page.get_by_text("ModuleNotFoundError", exact=True).first.is_visible()
            assert re.search(r"evidence_[0-9a-f]{32}", body_text) is not None
            assert "https://docs.python.org/3/library/exceptions.html" in body_text
            assert page.get_by_role(
                "button",
                name="https://docs.python.org/3/library/exceptions.html",
                exact=True,
            ).is_visible()
            assert download_enabled
            assert body_horizontal_overflow is False

            manifests_after = set(_LOCAL_LIVE_RESULTS.glob("case_*/result_*/result-manifest.json"))
            fresh_manifests = manifests_after - manifests_before
            assert len(fresh_manifests) == 1
            result_manifest = json.loads(fresh_manifests.pop().read_text(encoding="utf-8"))
            identity = result_manifest["identity"]
            assert result_manifest["status"] == "completed"
            assert result_manifest["mode"] == "live"
            assert result_manifest["fixture_id"] is None
            assert result_manifest["fixture_name"] is None
            assert re.fullmatch(r"case_[0-9a-f]{32}", identity["case_id"])
            assert identity["source_run_id"] == source_run_match.group(0)
            assert re.fullmatch(r"result_[0-9a-f]{32}", result_manifest["result_id"])
            observed_backend = _validated_source_backend(
                evidence_root=_LOCAL_LIVE_EVIDENCE,
                result_manifest=result_manifest,
                dom_source_run_id=source_run_match.group(0),
            )

            screenshot_value = os.environ.get(_LOCAL_LIVE_SCREENSHOT_ENV)
            ledger_value = os.environ.get(_LOCAL_LIVE_LEDGER_ENV)
            assert (screenshot_value is None) is (ledger_value is None)
            if screenshot_value is not None and ledger_value is not None:
                screenshot_path = Path(screenshot_value).resolve()
                ledger_path = Path(ledger_value).resolve()
                assert screenshot_path.parent == _EVIDENCE.resolve()
                assert ledger_path.parent == _EVIDENCE.resolve()
                assert ".staging." in screenshot_path.name
                assert ".staging." in ledger_path.name
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot_path))
                screenshot_sha256 = hashlib.sha256(screenshot_path.read_bytes()).hexdigest()
                ledger = {
                    "evidence_version": 1,
                    "viewport": {"width": 1366, "height": 768},
                    "status": "completed",
                    "mode": "live",
                    "fixture_id": None,
                    "fixture_name": None,
                    "backend": observed_backend,
                    "case_id_sha256": hashlib.sha256(
                        identity["case_id"].encode("utf-8")
                    ).hexdigest(),
                    "source_run_id_sha256": hashlib.sha256(
                        source_run_match.group(0).encode("utf-8")
                    ).hexdigest(),
                    "result_id_sha256": hashlib.sha256(
                        result_manifest["result_id"].encode("utf-8")
                    ).hexdigest(),
                    "screenshot_sha256": screenshot_sha256,
                    "body_horizontal_overflow": body_horizontal_overflow,
                    "server_owner": "run-phase4-local-live-qa.ps1",
                    "verified_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                }
                assert set(ledger) == _LOCAL_LIVE_LEDGER_KEYS
                assert (
                    ledger["screenshot_sha256"]
                    == hashlib.sha256(screenshot_path.read_bytes()).hexdigest()
                )
                assert ledger["backend"] == "local-rule-v1"
                ledger_path.write_text(
                    json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        finally:
            browser.close()


def test_gap_01_real_loopback_workbench_keeps_two_columns_and_spans_results_at_1024px(
    browser_base_url: str,
) -> None:
    """The tablet breakpoint keeps inputs/evidence together and spans results below."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1024, "height": 768})
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            for heading in ("输入与抽取", "诊断与证据", "三模态结果"):
                page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=30_000)
            page.get_by_text("固定回放案例", exact=True).wait_for(timeout=30_000)
            page.get_by_role("button", name="加载回放案例", exact=True).wait_for(timeout=30_000)
            metrics = page.evaluate(
                """() => ({
                    regions: [...document.querySelectorAll('.region')].map((element) => {
                        const box = element.getBoundingClientRect();
                        return { x: box.x, y: box.y, width: box.width, height: box.height };
                    }),
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                })"""
            )
        finally:
            browser.close()
    assert len(metrics["regions"]) == 3
    input_region, evidence_region, results_region = metrics["regions"]
    assert abs(input_region["y"] - evidence_region["y"]) <= 1
    assert input_region["x"] < evidence_region["x"]
    assert results_region["y"] > input_region["y"]
    assert results_region["y"] > evidence_region["y"]
    assert abs(results_region["x"] - input_region["x"]) <= 1
    assert (
        abs(
            (results_region["x"] + results_region["width"])
            - (evidence_region["x"] + evidence_region["width"])
        )
        <= 1
    )
    assert metrics["scrollWidth"] == metrics["clientWidth"]


def test_gap_01_real_loopback_workbench_stacks_regions_and_keeps_replay_visible_at_768px(
    browser_base_url: str,
) -> None:
    """The mobile breakpoint stacks the ordered regions without hiding replay controls."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 768, "height": 1024})
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            for heading in ("输入与抽取", "诊断与证据", "三模态结果"):
                page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=30_000)
            replay_label = page.get_by_text("固定回放案例", exact=True)
            replay_label.wait_for(timeout=30_000)
            replay_button = page.get_by_role("button", name="加载回放案例", exact=True)
            replay_button.wait_for(timeout=30_000)
            replay_boxes = [replay_label.bounding_box(), replay_button.bounding_box()]
            metrics = page.evaluate(
                """() => ({
                    regions: [...document.querySelectorAll('.region')].map((element) => {
                        const box = element.getBoundingClientRect();
                        return { x: box.x, y: box.y, width: box.width, height: box.height };
                    }),
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                })"""
            )
        finally:
            browser.close()
    assert len(metrics["regions"]) == 3
    input_region, evidence_region, results_region = metrics["regions"]
    assert abs(input_region["x"] - evidence_region["x"]) <= 1
    assert abs(evidence_region["x"] - results_region["x"]) <= 1
    assert input_region["y"] < evidence_region["y"] < results_region["y"]
    assert all(
        box is not None
        and box["width"] > 0
        and box["height"] > 0
        and box["y"] >= 0
        and box["y"] + box["height"] <= 1024
        for box in replay_boxes
    )
    assert metrics["scrollWidth"] == metrics["clientWidth"]
