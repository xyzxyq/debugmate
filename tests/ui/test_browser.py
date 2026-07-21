"""Real Microsoft Edge visual verification for the Phase 4 workbench.

The browser marker deliberately launches the loopback-only application rather
than loading a fixture HTML page.  Screenshots are evidence of the currently
implemented Gradio application, including failures that block Phase 4 visual
acceptance.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import zipfile
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import httpx
import pytest
from PIL import Image
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
_STUDENT_SCREENSHOT_DIR = _ROOT / "output" / "playwright"
_CAPTURE_STUDENT_REVIEW_ENV = "DEBUGMATE_CAPTURE_UI_REVIEW"
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


def _open_example(page) -> None:
    disclosure = page.get_by_text("查看示例", exact=True)
    if page.locator("#replay-action").is_hidden():
        disclosure.click()
    page.locator("#replay-action").wait_for(state="visible", timeout=10_000)


def _click_replay(page) -> None:
    _open_example(page)
    page.locator("#replay-action").click()


def _capture_student_review(page, filename: str, *, full_page: bool = False) -> None:
    if os.environ.get(_CAPTURE_STUDENT_REVIEW_ENV) != "1":
        return
    _STUDENT_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(_STUDENT_SCREENSHOT_DIR / filename), full_page=full_page)


def test_student_result_tabs_and_learning_flow_capture_real_edge(
    browser_base_url: str,
) -> None:
    """Capture the audited student flow from the current loopback app in Edge."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)

            preview = page.get_by_role("button", name="1. 生成脱敏预览", exact=True)
            approve = page.get_by_role("button", name="2. 确认并开始诊断", exact=True)
            report_tab = page.get_by_role("tab", name="文字报告", exact=True)
            card_tab = page.get_by_role("tab", name="诊断卡", exact=True)
            assert preview.is_enabled()
            assert approve.is_disabled()
            assert report_tab.is_hidden()
            assert card_tab.is_hidden()
            expect(page.locator("#student-overview")).to_contain_text("发生了什么")
            expect(page.get_by_text("查看示例", exact=True)).to_be_visible()
            assert page.locator("#replay-action").is_hidden()
            assert page.locator("#technical-details").is_hidden()
            idle_geometry = page.evaluate(
                "() => ({scroll: document.documentElement.scrollWidth, "
                "client: document.documentElement.clientWidth})"
            )
            assert idle_geometry["scroll"] == idle_geometry["client"]
            _capture_student_review(page, "after-student-idle-desktop.png")

            preview.click()
            expect(approve).to_be_enabled(timeout=30_000)
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")
            expect(page.locator('[role="status"][aria-live="polite"]')).to_have_text(
                "状态：已完成", timeout=30_000
            )
            for tab_name in ("文字报告", "诊断卡", "语音复盘", "引用与下载"):
                assert page.get_by_role("tab", name=tab_name, exact=True).is_enabled()
            card_tab.click()
            expect(card_tab).to_have_attribute("aria-selected", "true")
            report_tab.focus()
            report_tab.press("Enter")
            expect(report_tab).to_have_attribute("aria-selected", "true")
            expect(page.locator("#student-overview")).to_contain_text("最可能原因")
            expect(page.locator("#student-overview")).to_have_class(re.compile(r"tone-green"))
            expect(page.get_by_text("技术详情与恢复信息", exact=True)).to_be_visible()
            desktop_geometry = page.evaluate(
                "() => ({scroll: document.documentElement.scrollWidth, "
                "client: document.documentElement.clientWidth})"
            )
            assert desktop_geometry["scroll"] == desktop_geometry["client"]
            _capture_student_review(page, "after-student-completed-desktop.png")

            page.set_viewport_size({"width": 375, "height": 812})
            page.evaluate("document.body.style.zoom = '1'")
            page.wait_for_timeout(250)
            mobile_geometry = page.evaluate(
                "() => ({scroll: document.documentElement.scrollWidth, "
                "client: document.documentElement.clientWidth})"
            )
            assert mobile_geometry["scroll"] == mobile_geometry["client"]
            title_box = page.get_by_role(
                "heading", name="DebugMate 学习诊断助手", exact=True
            ).bounding_box()
            assert title_box is not None and title_box["width"] <= 359
            page.locator("#student-overview").scroll_into_view_if_needed()
            page.evaluate("window.scrollBy(0, 180)")
            _capture_student_review(
                page,
                "after-student-completed-mobile.png",
            )
        finally:
            context.close()
            browser.close()


def _qa_context(browser, browser_base_url: str):
    capability = os.environ.get(_QA_CAPABILITY_ENV)
    if capability is None:
        pytest.skip("runner-owned truth-state QA server is not active")
    assert re.fullmatch(r"qa_[0-9a-f]{64}", capability)
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    return context, capability


def _activate_qa(context, browser_base_url: str, scenario: str) -> None:
    response = context.request.post(
        f"{browser_base_url}{_QA_ROUTE}",
        data={"scenario": scenario},
        headers={_QA_HEADER: os.environ[_QA_CAPABILITY_ENV]},
    )
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
        headers={_QA_HEADER: os.environ[_QA_CAPABILITY_ENV]},
        timeout=10_000,
    )
    assert response.status == 200
    payload = response.json()
    assert isinstance(payload, dict)
    return payload


def _qa_audit_counts(context, browser_base_url: str) -> dict[str, int]:
    response = context.request.post(
        f"{browser_base_url}{_QA_ROUTE}",
        data={"action": "audit"},
        headers={_QA_HEADER: os.environ[_QA_CAPABILITY_ENV]},
        timeout=10_000,
    )
    assert response.status == 200
    payload = response.json()
    assert isinstance(payload, dict) and {"run_count", "result_count"} <= set(payload)
    counts = {name: payload[name] for name in ("run_count", "result_count")}
    assert all(isinstance(value, int) and value >= 0 for value in counts.values())
    return counts


def _qa_session_states(context, browser_base_url: str) -> list[dict[str, object]]:
    response = context.request.post(
        f"{browser_base_url}{_QA_ROUTE}",
        data={"action": "audit"},
        headers={_QA_HEADER: os.environ[_QA_CAPABILITY_ENV]},
        timeout=10_000,
    )
    assert response.status == 200
    payload = response.json()
    assert isinstance(payload, dict)
    states = payload.get("session_states")
    assert isinstance(states, list)
    assert all(
        isinstance(item, dict) and set(item) == {"session_sha256_prefix", "status", "source_run_id"}
        for item in states
    )
    return states


def _qa_session_events(context, browser_base_url: str) -> list[dict[str, object]]:
    response = context.request.post(
        f"{browser_base_url}{_QA_ROUTE}",
        data={"action": "audit"},
        headers={_QA_HEADER: os.environ[_QA_CAPABILITY_ENV]},
        timeout=10_000,
    )
    assert response.status == 200
    payload = response.json()
    assert isinstance(payload, dict)
    events = payload.get("session_events")
    assert isinstance(events, list)
    return events


def _latest_issued_session_prefix(context, browser_base_url: str) -> str:
    for event in reversed(_qa_session_events(context, browser_base_url)):
        prefix = event.get("session_sha256_prefix")
        if event.get("operation") == "issue_lease" and isinstance(prefix, str):
            return prefix
    raise AssertionError("no issued UI session lease was audited")


def _session_state_for_prefix(
    context, browser_base_url: str, session_prefix: str
) -> dict[str, object]:
    matches = [
        state
        for state in _qa_session_states(context, browser_base_url)
        if state.get("session_sha256_prefix") == session_prefix
    ]
    assert len(matches) == 1, (session_prefix, matches)
    return matches[0]


def _wait_for_created_result_counts(
    context, browser_base_url: str, initial: dict[str, int]
) -> dict[str, int]:
    deadline = time.monotonic() + 30
    latest = initial
    while time.monotonic() < deadline:
        latest = _qa_audit_counts(context, browser_base_url)
        if (
            latest["run_count"] > initial["run_count"]
            and latest["result_count"] == initial["result_count"] + 1
        ):
            return latest
        time.sleep(0.1)
    raise AssertionError(("created result was not persisted", initial, latest))


def _wait_for_new_session_source_run(
    context, browser_base_url: str, session_prefix: str, old_run_id: str
) -> str:
    deadline = time.monotonic() + 30
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = _session_state_for_prefix(context, browser_base_url, session_prefix)
        candidate = latest.get("source_run_id")
        if (
            latest.get("status") == "completed"
            and isinstance(candidate, str)
            and re.fullmatch(r"run_[0-9a-f]{32}", candidate)
            and candidate != old_run_id
        ):
            return candidate
        time.sleep(0.1)
    raise AssertionError(("new session source run was not published", old_run_id, latest))


def _download_verified_bundle(page, context, *, partial: bool) -> dict[str, object]:
    """Download the served archive and validate its self-contained allowlist."""

    button = page.locator("#download-result")
    expected_name = "debugmate-result-partial.zip" if partial else "debugmate-result.zip"
    with page.expect_download(timeout=30_000) as pending:
        button.click()
    download = pending.value
    assert download.suggested_filename == expected_name
    response = context.request.get(download.url, timeout=30_000)
    assert download.failure() is None, (
        download.url,
        download.failure(),
        response.status,
        response.headers,
        response.text()[:200],
    )
    downloaded_path = download.path()
    assert downloaded_path is not None
    payload = Path(downloaded_path).read_bytes()
    assert 0 < len(payload) <= 32 * 1024 * 1024
    archive_sha256 = hashlib.sha256(payload).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", archive_sha256)

    assert response.status == 200
    assert response.headers["content-type"].split(";", 1)[0] == "application/zip"
    assert expected_name in response.headers.get("content-disposition", "")
    assert hashlib.sha256(response.body()).hexdigest() == archive_sha256

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        assert names == sorted(names) and len(names) == len(set(names))
        manifest_bytes = archive.read("result-manifest.json")
        manifest = json.loads(manifest_bytes)
        assert isinstance(manifest, dict)
        artifacts = manifest.get("artifacts")
        assert isinstance(artifacts, list)
        allowed = {"result-manifest.json", "checksums.sha256"}
        for record in artifacts:
            assert isinstance(record, dict)
            name = record.get("path")
            digest = record.get("sha256")
            assert isinstance(name, str) and isinstance(digest, str)
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
            allowed.add(name)
        assert set(names) == allowed
        checksums = {}
        for line in archive.read("checksums.sha256").decode("ascii").splitlines():
            digest, name = line.split("  ", 1)
            checksums[name] = digest
        assert set(checksums) == allowed - {"checksums.sha256"}
        assert all(
            hashlib.sha256(archive.read(name)).hexdigest() == digest
            for name, digest in checksums.items()
        )
    assert manifest.get("status") == ("partial" if partial else "completed")
    return manifest


def _write_qa_staging(page, context, browser_base_url: str, scenario: str) -> None:
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
    browser_surfaces = page.evaluate(
        r"""() => ({
            outer_html: document.documentElement.outerHTML,
            hidden_inputs: [...document.querySelectorAll('input[type=hidden]')]
                .map(element => element.value).join('\n'),
            local_storage: JSON.stringify({...localStorage}),
            session_storage: JSON.stringify({...sessionStorage}),
            resource_urls: performance.getEntries().map(entry => entry.name).join('\n'),
        })"""
    )
    config_response = context.request.get(f"{browser_base_url}/config", timeout=10_000)
    assert config_response.status == 200
    with Image.open(screenshot) as captured:
        assert captured.format == "PNG"
        image_metadata = json.dumps(captured.info, ensure_ascii=True, sort_keys=True, default=str)
    surfaces = (
        page.content(),
        page.locator("html").inner_text(),
        page.locator("body").inner_text(),
        page.url,
        config_response.text(),
        image_metadata,
        json.dumps(row, sort_keys=True),
        row_path.read_text(encoding="utf-8"),
        *(str(value) for value in browser_surfaces.values()),
    )
    assert all(capability not in surface for surface in surfaces)


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
            _click_replay(page)
            status = page.locator("#diagnostic-status").first
            status.get_by_text("✓ 已完成", exact=False).wait_for(timeout=90_000)
            assert "离线回放" in status.inner_text()
            metadata = page.locator("#result-metadata").first.inner_text()
            download_tab = page.get_by_role("tab", name="引用与下载", exact=True)
            download_tab.focus()
            download_tab.press("Enter")
            expect(download_tab).to_have_attribute("aria-selected", "true")
            download_surface = page.locator("#download-metadata").first
            expect(download_surface).to_contain_text("离线回放", timeout=30_000)
            download_metadata = download_surface.inner_text()
            body = page.locator("body").inner_text()
            assert "离线回放" in metadata
            assert "ModuleNotFoundError：缺少虚构依赖包" in metadata
            assert "来源运行" in metadata
            assert "实时诊断" not in metadata
            assert "离线回放" in download_metadata
            assert "云端运行成功" not in body
            assert page.get_by_text("下载完整证据包", exact=True).is_visible()
            manifest = _download_verified_bundle(page, context, partial=False)
            assert manifest["mode"] == "replay"
            assert manifest["fixture_name"] == "ModuleNotFoundError：缺少虚构依赖包"
            _write_qa_staging(page, context, browser_base_url, "vq-02")
        finally:
            if context is not None:
                context.close()
            browser.close()


def test_completed_learning_workbench_has_consistent_light_surfaces_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")
            page.get_by_text("技术详情与恢复信息", exact=True).click()
            expect(page.locator("#result-metadata")).to_be_visible()

            metrics = page.evaluate(
                r"""() => {
                    const parse = value => {
                        const parts = value.match(/[\d.]+/g);
                        if (!parts || parts.length < 3) return null;
                        return {
                            rgb: parts.slice(0, 3).map(Number),
                            alpha: parts.length > 3 ? Number(parts[3]) : 1,
                        };
                    };
                    const luminance = rgb => {
                        const linear = rgb.map(channel => {
                            const value = channel / 255;
                            return value <= 0.04045
                                ? value / 12.92
                                : ((value + 0.055) / 1.055) ** 2.4;
                        });
                        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
                    };
                    const composite = (foreground, backdrop, alpha) => foreground.map(
                        (channel, index) => channel * alpha + backdrop[index] * (1 - alpha)
                    );
                    const ancestry = element => {
                        const chain = [];
                        for (let current = element; current; current = current.parentElement) {
                            chain.push(current);
                        }
                        return chain.reverse();
                    };
                    const effectiveBackground = element => {
                        let background = [255, 255, 255];
                        for (const current of ancestry(element)) {
                            const style = getComputedStyle(current);
                            const parsed = parse(style.backgroundColor);
                            const opacity = Number(style.opacity);
                            if (parsed && parsed.alpha > 0) {
                                background = composite(
                                    parsed.rgb, background, parsed.alpha * opacity
                                );
                            }
                        }
                        return background;
                    };
                    const effectiveForeground = element => {
                        const parsed = parse(getComputedStyle(element).color);
                        if (!parsed) return null;
                        const backdrop = effectiveBackground(element.parentElement);
                        const opacity = ancestry(element).reduce(
                            (value, current) => value * Number(getComputedStyle(current).opacity), 1
                        );
                        return composite(parsed.rgb, backdrop, parsed.alpha * opacity);
                    };
                    const contrast = (foreground, background) => {
                        const first = luminance(foreground);
                        const second = luminance(background);
                        return (Math.max(first, second) + 0.05) /
                            (Math.min(first, second) + 0.05);
                    };
                    const leaked = [...document.querySelectorAll('.gradio-container *, footer')]
                        .filter(element => {
                            const box = element.getBoundingClientRect();
                            const outsideViewport = box.bottom <= 0 || box.top >= innerHeight;
                            if (box.width * box.height < 2000 || outsideViewport) {
                                return false;
                            }
                            return !element.closest('img, canvas, video, svg') &&
                                luminance(effectiveBackground(element)) < 0.72;
                        })
                        .map(element => ({
                            selector: `${element.tagName.toLowerCase()}#${element.id}.` +
                                element.className,
                            background: getComputedStyle(element).backgroundColor,
                            area: Math.round(
                                element.getBoundingClientRect().width *
                                element.getBoundingClientRect().height
                            ),
                        }));
                    const contrastTargets = [
                        '.diagnosis-summary',
                        '#fact-table',
                        '#diagnostic-report',
                        '#result-metadata',
                        'footer',
                    ].map(selector => {
                        const element = document.querySelector(selector);
                        if (!element) return {selector, missing: true};
                        const foreground = effectiveForeground(element);
                        const background = effectiveBackground(element);
                        return {
                            selector,
                            color: getComputedStyle(element).color,
                            background: `rgb(${background.join(', ')})`,
                            contrast: foreground ? contrast(foreground, background) : 0,
                        };
                    });
                    const disabledControls = [...document.querySelectorAll('button:disabled')]
                        .filter(element => {
                            const box = element.getBoundingClientRect();
                            return box.width > 0 && box.height > 0 && box.bottom > 0 &&
                                box.top < innerHeight;
                        })
                        .map(element => {
                            const foreground = effectiveForeground(element);
                            const background = effectiveBackground(element);
                            return {
                                text: element.innerText,
                                opacity: Number(getComputedStyle(element).opacity),
                                contrast: foreground ? contrast(foreground, background) : 0,
                            };
                        });
                    const mediaMasks = [...document.querySelectorAll(
                        '#diagnostic-card img, img, canvas, video, svg'
                    )].map(element => {
                        const box = element.getBoundingClientRect();
                        return {left: box.left, top: box.top, right: box.right, bottom: box.bottom};
                    }).filter(mask => mask.right > 0 && mask.bottom > 0 &&
                        mask.left < innerWidth && mask.top < innerHeight);
                    return {leaked, contrastTargets, disabledControls, mediaMasks};
                }"""
            )
            assert metrics["leaked"] == []
            assert all(
                not target.get("missing") and target["contrast"] >= 4.5
                for target in metrics["contrastTargets"]
            ), metrics["contrastTargets"]
            assert all(
                control["opacity"] >= 0.8 and control["contrast"] >= 4.5
                for control in metrics["disabledControls"]
            ), metrics["disabledControls"]

            screenshot = page.screenshot(full_page=False)
            with Image.open(io.BytesIO(screenshot)) as captured:
                pixels = tuple(captured.convert("RGB").get_flattened_data())
            unmasked_pixels = 0
            light_pixels = 0
            for index, (red, green, blue) in enumerate(pixels):
                x = index % captured.width
                y = index // captured.width
                if any(
                    mask["left"] <= x < mask["right"] and mask["top"] <= y < mask["bottom"]
                    for mask in metrics["mediaMasks"]
                ):
                    continue
                unmasked_pixels += 1
                if min(red, green, blue) >= 190:
                    light_pixels += 1
            assert unmasked_pixels > 0
            assert light_pixels / unmasked_pixels > 0.60
        finally:
            context.close()
            browser.close()


def test_completed_command_bar_keeps_title_and_truthful_status_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")

            geometry = page.evaluate(
                r"""() => {
                    const carrier = [...document.querySelectorAll('.command-bar > .styler')]
                        .find(element => element.children.length >= 3);
                    if (!carrier) return {missing: true};
                    const rect = selector => {
                        const element = carrier.querySelector(selector);
                        if (!element) return null;
                        const box = element.getBoundingClientRect();
                        return {x: box.x, right: box.right, y: box.y, width: box.width};
                    };
                    return {
                        display: getComputedStyle(carrier).display,
                        columns: getComputedStyle(carrier).gridTemplateColumns
                            .trim().split(/\s+/).filter(Boolean).length,
                        title: rect('.product-title'),
                        status: rect('#diagnostic-status'),
                        accessibleStatus: rect('#accessible-status'),
                        statusClass: carrier.querySelector('#diagnostic-status')?.className || '',
                    };
                }"""
            )
            assert not geometry.get("missing"), geometry
            assert geometry["display"] == "grid", geometry
            assert geometry["columns"] == 2, geometry
            assert all(
                geometry[name] and geometry[name]["width"] > 0
                for name in ("title", "status", "accessibleStatus")
            ), geometry
            assert geometry["title"]["right"] <= geometry["status"]["x"]
            assert "tone-green" in geometry["statusClass"]

            mobile_context = browser.new_context(viewport={"width": 768, "height": 1024})
            try:
                mobile_page = mobile_context.new_page()
                mobile_page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
                mobile_page.locator(".gradio-container").wait_for(timeout=30_000)
                _click_replay(mobile_page)
                _wait_for_terminal_status(mobile_page, "✓ 已完成")
                mobile_page.evaluate("window.scrollTo(0, 0)")
                mobile_geometry = mobile_page.evaluate(
                    r"""() => {
                        const carrier = [...document.querySelectorAll('.command-bar > .styler')]
                            .find(element => element.children.length >= 3);
                        if (!carrier) return {missing: true};
                        const rect = selector => {
                            const element = carrier.querySelector(selector);
                            if (!element) return null;
                            const box = element.getBoundingClientRect();
                            return {x: box.x, right: box.right, y: box.y, bottom: box.bottom};
                        };
                        return {
                            display: getComputedStyle(carrier).display,
                            columns: getComputedStyle(carrier).gridTemplateColumns
                                .trim().split(/\s+/).filter(Boolean).length,
                            viewport: innerWidth,
                            items: [
                                rect('.product-title'),
                                rect('#diagnostic-status'),
                            ],
                        };
                    }"""
                )
                assert not mobile_geometry.get("missing"), mobile_geometry
                assert mobile_geometry["display"] == "grid", mobile_geometry
                assert mobile_geometry["columns"] == 1, mobile_geometry
                assert all(item and 0 <= item["x"] <= item["right"] <= mobile_geometry["viewport"]
                           for item in mobile_geometry["items"]), mobile_geometry
                stacked = sorted(mobile_geometry["items"], key=lambda item: item["y"])
                assert all(
                    following["y"] >= previous["bottom"] - 1
                    for previous, following in zip(stacked, stacked[1:], strict=False)
                ), mobile_geometry
            finally:
                mobile_context.close()
        finally:
            context.close()
            browser.close()


def test_completed_result_tabs_keep_visible_surfaces_light_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")

            tabs = page.get_by_role("tab")
            expected_surfaces = (
                ("#diagnostic-report", ("#diagnostic-report",)),
                ("#diagnostic-card", ()),
                ("#diagnostic-audio", ("#audio-metadata", "#recap-text textarea")),
                ("#citation-table", ("#citation-table",)),
            )
            assert tabs.count() == len(expected_surfaces)

            for index, (surface_selector, text_selectors) in enumerate(expected_surfaces):
                tab = tabs.nth(index)
                tab.click()
                expect(tab).to_have_attribute("aria-selected", "true")
                page.locator(surface_selector).wait_for(state="visible", timeout=30_000)
                metrics = page.evaluate(
                    r"""selectors => {
                        const parse = value => {
                            const parts = value.match(/[\d.]+/g);
                            if (!parts || parts.length < 3) return null;
                            return {
                                rgb: parts.slice(0, 3).map(Number),
                                alpha: parts.length > 3 ? Number(parts[3]) : 1,
                            };
                        };
                        const luminance = rgb => {
                            const linear = rgb.map(channel => {
                                const value = channel / 255;
                                return value <= 0.04045
                                    ? value / 12.92
                                    : ((value + 0.055) / 1.055) ** 2.4;
                            });
                            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
                        };
                        const composite = (foreground, backdrop, alpha) => foreground.map(
                            (channel, index) => channel * alpha + backdrop[index] * (1 - alpha)
                        );
                        const ancestry = element => {
                            const chain = [];
                            for (let current = element; current; current = current.parentElement) {
                                chain.push(current);
                            }
                            return chain.reverse();
                        };
                        const background = element => {
                            let rendered = [255, 255, 255];
                            for (const current of ancestry(element)) {
                                const style = getComputedStyle(current);
                                const fill = parse(style.backgroundColor);
                                if (fill && fill.alpha > 0) {
                                    rendered = composite(
                                        fill.rgb, rendered, fill.alpha * Number(style.opacity)
                                    );
                                }
                            }
                            return rendered;
                        };
                        const contrast = element => {
                            const color = parse(getComputedStyle(element).color);
                            if (!color) return 0;
                            const backdrop = background(element.parentElement);
                        const opacity = ancestry(element).reduce(
                            (value, current) => value * Number(
                                getComputedStyle(current).opacity
                            ),
                            1
                        );
                        const foreground = composite(
                            color.rgb, backdrop, color.alpha * opacity
                        );
                            const fill = background(element);
                            const first = luminance(foreground);
                            const second = luminance(fill);
                            return (Math.max(first, second) + 0.05) /
                                (Math.min(first, second) + 0.05);
                        };
                        const visible = element => {
                            const box = element.getBoundingClientRect();
                            return box.width > 0 && box.height > 0 && box.bottom > 0 &&
                                box.top < innerHeight;
                        };
                        const findLeaks = () => [
                            ...document.querySelectorAll('.result-workspace *')
                        ]
                            .filter(element => {
                                const box = element.getBoundingClientRect();
                                return visible(element) && box.width * box.height >= 2000 &&
                                    !element.closest('img, canvas, video, svg') &&
                                    luminance(background(element)) < 0.72;
                            })
                            .map(element => (
                                `${element.tagName.toLowerCase()}#${element.id}.${element.className}`
                            ));
                        const card = selectors.probeCard
                            ? document.querySelector('#diagnostic-card')
                            : null;
                        const originalBackground = card?.style.backgroundColor;
                        if (card) card.style.setProperty(
                            'background-color', 'rgb(15, 23, 42)', 'important'
                        );
                        const probeLeaks = findLeaks();
                        if (card) {
                            card.style.backgroundColor = originalBackground;
                            card.style.removeProperty('background-color');
                        }
                        const leaked = findLeaks();
                        const text = selectors.text.map(selector => {
                            const element = document.querySelector(selector);
                            return {
                                selector,
                                visible: Boolean(element && visible(element)),
                                contrast: element ? contrast(element) : 0,
                            };
                        });
                        const audio = selectors.audio.map(selector => {
                            const element = document.querySelector(selector);
                            return {
                                selector,
                                visible: Boolean(element && visible(element)),
                                luminance: element ? luminance(background(element)) : 1,
                            };
                        });
                        return {leaked, probeLeaks, text, audio};
                    }""",
                    {
                        "text": list(text_selectors),
                        "probeCard": surface_selector == "#diagnostic-card",
                        "audio": (
                            (
                                "#diagnostic-audio",
                                "#diagnostic-audio label",
                                "#diagnostic-audio .controls",
                            )
                            if surface_selector == "#diagnostic-audio"
                            else ()
                        ),
                    },
                )
                if surface_selector == "#diagnostic-card":
                    assert any(
                        "#diagnostic-card" in value for value in metrics["probeLeaks"]
                    ), metrics
                assert metrics["leaked"] == [], metrics["leaked"]
                assert all(
                    target["visible"] and target["contrast"] >= 4.5
                    for target in metrics["text"]
                ), metrics["text"]
                assert all(
                    target["visible"] and target["luminance"] >= 0.72
                    for target in metrics["audio"]
                ), metrics["audio"]
        finally:
            context.close()
            browser.close()


def test_v01_download_matches_visible_source_run_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")

            metadata = page.locator("#result-metadata").first.inner_text()
            visible_match = re.search(r"来源运行：(run_[0-9a-f]{32})", metadata)
            assert visible_match is not None
            visible_source_run_id = visible_match.group(1)

            download_tab = page.get_by_role("tab", name="引用与下载", exact=True)
            download_tab.click()
            manifest = _download_verified_bundle(page, context, partial=False)
            identity = manifest.get("identity")
            assert isinstance(identity, dict)
            assert identity.get("source_run_id") == visible_source_run_id
        finally:
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
            _click_replay(page)
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
                    for field_label in (
                        "异常类型",
                        "关键回溯行",
                        "包/模块",
                        "版本",
                        "设备",
                        "路径",
                    ):
                        assert page.get_by_label(field_label, exact=True).is_disabled()
                    assert not re.search(r"\b\d+(?:\.\d+)?\s*%", status.inner_text())
                    if stage == "publish":
                        _write_qa_staging(page, context, browser_base_url, "vq-03")
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


def _select_replay(page, label: str) -> None:
    _open_example(page)
    control = page.get_by_label("示例案例", exact=True)
    control.click()
    page.get_by_role("option", name=label, exact=True).click()
    expect(control).to_have_value(label)


def _body_overflow(page) -> bool:
    return bool(
        page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
    )


def _focused_control(page) -> tuple[object, dict[str, object]]:
    locator = page.locator(
        ":focus:is(button, a, input, textarea, select, audio, [role='tab'], [role='button'])"
    ).last
    locator.wait_for(state="attached")
    page.wait_for_function(
        "element => parseFloat(getComputedStyle(element).outlineOffset) >= 2",
        arg=locator.element_handle(),
    )
    metrics = locator.evaluate(
        """element => {
            const style = getComputedStyle(element);
            return {
                id: element.id,
                name: element.getAttribute('aria-label') ||
                    element.labels?.[0]?.innerText?.trim() ||
                    element.innerText?.trim() || '',
                outlineStyle: style.outlineStyle,
                outlineWidth: parseFloat(style.outlineWidth),
                outlineOffset: parseFloat(style.outlineOffset),
            };
        }"""
    )
    return locator, metrics


def _assert_visible_focus(page) -> tuple[object, dict[str, object]]:
    locator, metrics = _focused_control(page)
    assert metrics["outlineStyle"] not in {"none", "hidden"}
    assert metrics["outlineWidth"] >= 2
    assert metrics["outlineOffset"] >= 2
    return locator, metrics


def _tab_to(page, *, expected_id: str | None = None, expected_name: str, limit: int = 12):
    for _step in range(limit):
        page.keyboard.press("Tab")
        if (
            page.locator(
                ":focus:is(button, a, input, textarea, select, audio, "
                "[role='tab'], [role='button'])"
            ).count()
            == 0
        ):
            continue
        locator, metrics = _assert_visible_focus(page)
        if (expected_id is None or metrics["id"] == expected_id) and expected_name in str(
            metrics["name"]
        ):
            return locator
    raise AssertionError(f"Tab order did not reach {expected_name!r} within {limit} steps")


def _shift_tab_to(page, *, expected_name: str, limit: int = 12):
    for _step in range(limit):
        page.keyboard.press("Shift+Tab")
        if (
            page.locator(
                ":focus:is(button, a, input, textarea, select, audio, "
                "[role='tab'], [role='button'])"
            ).count()
            == 0
        ):
            continue
        locator, metrics = _assert_visible_focus(page)
        if expected_name in str(metrics["name"]):
            return locator
    raise AssertionError(f"Reverse tab order did not reach {expected_name!r} within {limit} steps")


def test_vq_13_keyboard_native_controls_and_announced_status_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)

            positive_tabindex = page.locator("[tabindex]").evaluate_all(
                "elements => elements.map(element => Number(element.tabIndex))"
                ".filter(value => value > 0)"
            )
            assert positive_tabindex == []
            _tab_to(
                page,
                expected_id="local-preview",
                expected_name="1. 生成脱敏预览",
                limit=20,
            )
            example_accordion = _tab_to(page, expected_name="查看示例", limit=3)
            example_accordion.press("Space")
            expect(example_accordion).to_have_class(re.compile(r"\bopen\b"))
            _tab_to(page, expected_name="示例案例", limit=3)
            replay_button = _tab_to(
                page,
                expected_id="replay-action",
                expected_name="加载回放案例",
                limit=2,
            )
            replay_button.press("Enter")
            _wait_for_terminal_status(page, "✓ 已完成")

            announced = page.locator('[role="status"][aria-live="polite"]')
            expect(announced).to_have_text("状态：已完成", timeout=30_000)

            correction_accordion = _tab_to(page, expected_name="抽取字段与纠错", limit=3)
            correction_accordion.press("Space")
            expect(correction_accordion).to_have_class(re.compile(r"\bopen\b"))
            _tab_to(page, expected_name="异常类型", limit=20)
            for field_label in ("关键回溯行", "包/模块", "版本", "设备", "路径"):
                _tab_to(page, expected_name=field_label, limit=2)
            _tab_to(page, expected_name="确认创建新运行", limit=2)

            command_accordion = _tab_to(
                page, expected_name="技术详情与恢复信息", limit=6
            )
            command_accordion.press("Space")
            expect(command_accordion).to_have_class(re.compile(r"\bopen\b"))
            expect(page.locator("#diagnostic-commands")).to_be_visible()

            _tab_to(page, expected_name="文字报告", limit=3)
            diagnosis_tab = _tab_to(page, expected_name="诊断卡", limit=2)
            diagnosis_tab.press("Enter")
            expect(page.get_by_role("tab", name="诊断卡", exact=True)).to_have_attribute(
                "aria-selected", "true"
            )
            audio_tab = _tab_to(page, expected_name="语音复盘", limit=2)
            audio_tab.press("Enter")
            expect(page.get_by_role("tab", name="语音复盘", exact=True)).to_have_attribute(
                "aria-selected", "true"
            )

            _tab_to(page, expected_name="引用与下载", limit=2)
            audio_control = _tab_to(page, expected_name="Play", limit=8)
            audio_control.press("Space")
            pause_control = page.get_by_role("button", name="Pause", exact=True)
            expect(pause_control).to_be_visible()

            download_tab = _shift_tab_to(page, expected_name="引用与下载", limit=8)
            download_tab.press("Enter")
            expect(page.get_by_role("tab", name="引用与下载", exact=True)).to_have_attribute(
                "aria-selected", "true"
            )
            download_control = _tab_to(page, expected_name="下载完整证据包", limit=60)
            with page.expect_download(timeout=30_000):
                download_control.press("Enter")
        finally:
            context.close()
            browser.close()


def test_vq_14_statuses_keep_icon_and_text_under_test_side_grayscale(
    browser_base_url: str,
) -> None:
    scenarios = (
        ("vq-02-replay", "✓", "已完成", "↺", "离线回放"),
        ("vq-06-tts-failed", "⚠", "部分完成", None, None),
        ("vq-08-source-invalid", "✕", "诊断失败", None, None),
    )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            for scenario, icon, label, mode_icon, mode_label in scenarios:
                context, _capability = _qa_context(browser, browser_base_url)
                try:
                    _activate_qa(context, browser_base_url, scenario)
                    page = context.new_page()
                    page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
                    page.locator(".gradio-container").wait_for(timeout=30_000)
                    page.add_style_tag(content="html { filter: grayscale(1) !important; }")
                    _click_replay(page)
                    _wait_for_terminal_status(page, f"{icon} {label}")
                    status_text = page.locator("#diagnostic-status").inner_text()
                    assert icon in status_text and label in status_text
                    if mode_icon is not None and mode_label is not None:
                        assert mode_icon in status_text and mode_label in status_text
                    assert (
                        page.evaluate("() => getComputedStyle(document.documentElement).filter")
                        == "grayscale(1)"
                    )
                finally:
                    context.close()
        finally:
            browser.close()


def test_vq_15_completed_state_remains_reachable_at_two_x_browser_zoom_geometry(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")
            assert page.evaluate("() => innerWidth") == 1366
            cdp = context.new_cdp_session(page)
            cdp.send(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": 683,
                    "height": 384,
                    "screenWidth": 1366,
                    "screenHeight": 768,
                    "deviceScaleFactor": 2,
                    "mobile": False,
                },
            )
            page.wait_for_function("() => innerWidth === 683 && devicePixelRatio === 2")

            page.locator("#diagnostic-status").scroll_into_view_if_needed()
            assert page.locator("#diagnostic-status").is_visible()
            correction_accordion = _tab_to(page, expected_name="抽取字段与纠错", limit=6)
            correction_accordion.press("Space")
            expect(correction_accordion).to_have_class(re.compile(r"\bopen\b"))
            primary_action = page.get_by_role("button", name="确认修改并重新诊断", exact=True)
            primary_action.scroll_into_view_if_needed()
            assert primary_action.is_visible()
            download_tab = page.get_by_role("tab", name="引用与下载", exact=True)
            download_tab.focus()
            download_tab.press("Enter")
            expect(download_tab).to_have_attribute("aria-selected", "true")
            download = page.locator("#download-result")
            download.scroll_into_view_if_needed()
            assert download.is_visible()
            metrics = page.evaluate(
                """() => ({
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                    clipped: [...document.querySelectorAll(
                        '#diagnostic-status, [role=tab], #download-result'
                    )].some(element =>
                        element.scrollWidth > element.clientWidth + 1 ||
                        element.scrollHeight > element.clientHeight + 1
                    ),
                    tabOverlap: [...document.querySelectorAll('[role=tab]')]
                        .some((element, index, elements) => {
                            const first = element.getBoundingClientRect();
                            return elements.slice(index + 1).some(other => {
                                const second = other.getBoundingClientRect();
                                return first.left < second.right - 1 &&
                                    first.right > second.left + 1 &&
                                    first.top < second.bottom - 1 &&
                                    first.bottom > second.top + 1;
                            });
                        }),
                })"""
            )
            assert metrics["scrollWidth"] == metrics["clientWidth"]
            assert metrics["clipped"] is False
            assert metrics["tabOverlap"] is False
            action_metrics = primary_action.evaluate(
                "element => ({clientWidth: element.clientWidth, "
                "scrollWidth: element.scrollWidth, clientHeight: element.clientHeight, "
                "scrollHeight: element.scrollHeight})"
            )
            assert action_metrics["scrollWidth"] <= action_metrics["clientWidth"] + 1
            assert action_metrics["scrollHeight"] <= action_metrics["clientHeight"] + 1
        finally:
            context.close()
            browser.close()


def test_vq_04_long_content_commands_and_vq_05_tall_card_in_real_edge(
    browser_base_url: str,
) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            _select_replay(page, "长报告与长命令：布局韧性")
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")

            report = page.locator("#diagnostic-report")
            report_metrics = report.locator("*").evaluate_all(
                "elements => elements.map(element => ({clientHeight: element.clientHeight, "
                "scrollHeight: element.scrollHeight, overflowY: "
                "getComputedStyle(element).overflowY}))"
            )
            assert any(
                metric["scrollHeight"] > metric["clientHeight"] > 0
                and metric["overflowY"] in {"auto", "scroll"}
                for metric in report_metrics
            )
            technical = page.get_by_text("技术详情与恢复信息", exact=True)
            expect(technical).to_be_visible()
            technical.click()
            commands = page.locator("#diagnostic-commands")
            expect(commands).to_contain_text("windows_powershell")
            expect(commands).to_contain_text("EXPECTED-LONG-COMMAND-END")
            expect(commands).to_contain_text("ROLLBACK-LONG-COMMAND-END")
            command_box = commands.bounding_box()
            assert command_box is not None
            assert command_box["x"] >= 0
            assert command_box["x"] + command_box["width"] <= page.evaluate("innerWidth") + 1
            assert not _body_overflow(page)
            expect(
                page.get_by_text(
                    "诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。", exact=True
                ).first
            ).to_be_visible()

            page.get_by_role("tab", name="诊断卡", exact=True).click()
            image = page.locator("#diagnostic-card img").first
            image.wait_for(timeout=30_000)
            card = image.evaluate(
                "element => ({naturalWidth: element.naturalWidth, "
                "naturalHeight: element.naturalHeight, "
                "width: element.getBoundingClientRect().width, "
                "height: element.getBoundingClientRect().height, "
                "parentWidth: element.parentElement.getBoundingClientRect().width})"
            )
            assert card["naturalHeight"] > card["naturalWidth"]
            assert (
                abs(card["width"] / card["height"] - card["naturalWidth"] / card["naturalHeight"])
                < 0.01
            )
            assert card["width"] <= card["parentWidth"] + 1
            assert _body_overflow(page) is False
        finally:
            context.close()
            browser.close()


@pytest.mark.parametrize("viewport", [(1024, 768), (768, 1024)])
def test_vq_11_vq_12_completed_responsive_geometry_in_real_edge(
    browser_base_url: str, viewport: tuple[int, int]
) -> None:
    width, height = viewport
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": width, "height": height})
        try:
            page = context.new_page()
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")
            tabs = page.get_by_role("tab").all_inner_texts()
            assert tabs == ["文字报告", "诊断卡", "语音复盘", "引用与下载"]
            regions = [
                page.locator("#workbench-grid .control-rail"),
                page.locator("#workbench-grid .diagnosis-canvas"),
                page.locator("#workbench-grid .result-workspace"),
            ]
            boxes = [region.bounding_box() for region in regions]
            assert all(box is not None for box in boxes)
            first, second, third = boxes
            assert first is not None and second is not None and third is not None
            assert abs(first["x"] - second["x"]) <= 1
            assert abs(second["x"] - third["x"]) <= 1
            assert first["y"] < second["y"] < third["y"]
            assert page.locator("#replay-action").is_visible()
            assert page.locator("#diagnostic-status").is_visible()
            assert _body_overflow(page) is False
        finally:
            context.close()
            browser.close()


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
                    _click_replay(page)
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
                    expect(page.locator("#diagnostic-report")).to_contain_text(
                        "DebugMate", timeout=30_000
                    )
                    page.get_by_role("tab", name="引用与下载", exact=True).click()
                    expect(page.locator("#download-result")).to_contain_text("下载部分结果包")
                    partial_manifest = _download_verified_bundle(page, context, partial=True)
                    if scenario == "vq-06-tts-failed":
                        page.get_by_role("tab", name="诊断卡", exact=True).click()
                        page.locator("#diagnostic-card img").wait_for(timeout=30_000)
                        page.get_by_role("tab", name="语音复盘", exact=True).click()
                        expect(page.locator("#diagnostic-audio")).to_be_hidden()
                        assert "tts_failed" in page.locator("#audio-metadata").inner_text()
                        assert (
                            "ModuleNotFoundError"
                            in page.locator("#recap-text textarea").input_value()
                        )
                    else:
                        page.get_by_role("tab", name="诊断卡", exact=True).click()
                        assert page.locator("#diagnostic-card img[src]").count() == 0
                        page.get_by_role("tab", name="语音复盘", exact=True).click()
                        expect(page.locator("#audio-metadata")).to_contain_text(
                            "语音后端", timeout=30_000
                        )
                        expect(page.locator("#diagnostic-audio")).to_be_visible()
                    _write_qa_staging(
                        page,
                        context,
                        browser_base_url,
                        "-".join(scenario.split("-")[:2]),
                    )
                    page.locator("#partial-retry").click()
                    _wait_for_terminal_status(page, "✓ 已完成")
                    assert page.locator("#partial-retry").is_disabled()
                    if scenario == "vq-06-tts-failed":
                        page.get_by_role("tab", name="语音复盘", exact=True).click()
                        expect(page.locator("#diagnostic-audio")).to_be_visible()
                    else:
                        page.get_by_role("tab", name="诊断卡", exact=True).click()
                        page.locator("#diagnostic-card img").wait_for(timeout=30_000)
                    page.get_by_role("tab", name="引用与下载", exact=True).click()
                    complete_manifest = _download_verified_bundle(page, context, partial=False)
                    assert complete_manifest["result_id"] != partial_manifest["result_id"]
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
                _click_replay(page)
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
                expect(page.locator("#diagnostic-report")).to_have_text("尚未生成诊断结果")
                assert page.locator("#diagnostic-card img[src]").count() == 0
                expect(page.locator("#diagnostic-audio")).to_be_hidden()
                expect(page.locator("#recap-text")).to_be_hidden()
                assert page.locator("#recap-text textarea").count() == 0
                page.get_by_role("tab", name="引用与下载", exact=True).click()
                expect(page.locator("#download-result")).to_be_hidden()
                expect(page.locator("#individual-artifacts")).to_be_hidden()
                citation_surface = page.locator("#citation-table").inner_text()
                assert "evidence_" not in citation_surface
                assert "http://" not in citation_surface and "https://" not in citation_surface
                page_surface = page.content()
                assert "/debugmate-content/" not in page_surface
                assert not re.search(
                    r"(?:[A-Za-z]:\\|/Users/|/home/|Traceback)",
                    page.locator("body").inner_text(),
                )
                _write_qa_staging(page, context, browser_base_url, "vq-08")
            finally:
                context.close()

            context, _capability = _qa_context(browser, browser_base_url)
            try:
                _activate_qa(context, browser_base_url, "vq-09-fallback")
                page = context.new_page()
                page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
                page.locator(".gradio-container").wait_for(timeout=30_000)
                _click_replay(page)
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
                manifest = _download_verified_bundle(page, context, partial=False)
                assert manifest["audio"]["backend"] == "sapi"
                _write_qa_staging(page, context, browser_base_url, "vq-09")
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
            _click_replay(page)
            _wait_for_terminal_status(page, "✓ 已完成")
            metadata = page.locator("#result-metadata")
            old_identity = metadata.inner_text()
            old_run_match = re.search(r"run_[0-9a-f]{32}", old_identity)
            assert old_run_match is not None
            old_run_id = old_run_match.group(0)
            session_prefix = _latest_issued_session_prefix(context, browser_base_url)
            initial_session_state = _session_state_for_prefix(
                context, browser_base_url, session_prefix
            )
            assert initial_session_state["status"] == "completed"
            assert initial_session_state["source_run_id"] == old_run_id
            download_tab = page.get_by_role("tab", name="引用与下载", exact=True)
            download_tab.focus()
            download_tab.press("Enter")
            expect(download_tab).to_have_attribute("aria-selected", "true")
            old_manifest = _download_verified_bundle(page, context, partial=False)
            old_download_metadata = page.locator("#download-metadata").inner_text()
            assert old_run_id in old_download_metadata
            initial_counts = _qa_audit_counts(context, browser_base_url)

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
            page.wait_for_timeout(1_000)
            assert _qa_audit_counts(context, browser_base_url) == initial_counts

            confirm = page.get_by_role("button", name="确认修改并重新诊断", exact=True)
            assert confirm.is_enabled()
            confirm.click()
            create = page.get_by_role("button", name="创建新运行", exact=True)
            create.wait_for(timeout=30_000)
            assert create.is_enabled()
            assert metadata.inner_text() == old_identity
            page.wait_for_timeout(1_000)
            assert _qa_audit_counts(context, browser_base_url) == initial_counts
            create.click()
            created_counts = _wait_for_created_result_counts(
                context, browser_base_url, initial_counts
            )
            assert created_counts["run_count"] >= initial_counts["run_count"] + 1
            _wait_for_terminal_status(page, "✓ 已完成")
            new_run_id = _wait_for_new_session_source_run(
                context, browser_base_url, session_prefix, old_run_id
            )
            expect(metadata).to_contain_text(new_run_id, timeout=30_000)
            new_identity = metadata.inner_text()
            assert new_identity != old_identity
            assert "来源运行" in new_identity
            page.get_by_role("tab", name="引用与下载", exact=True).click()
            download_metadata = page.locator("#download-metadata")
            try:
                expect(download_metadata).to_contain_text(new_run_id, timeout=30_000)
            except AssertionError as error:
                raise AssertionError(
                    (
                        new_run_id,
                        download_metadata.inner_text(),
                        _qa_session_states(context, browser_base_url),
                        _qa_session_events(context, browser_base_url),
                    )
                ) from error
            new_manifest = _download_verified_bundle(page, context, partial=False)
            assert new_manifest["result_id"] != old_manifest["result_id"]
            identity = new_manifest.get("identity")
            assert isinstance(identity, dict)
            assert identity.get("source_run_id") == new_run_id
            _write_qa_staging(page, context, browser_base_url, "vq-10")

            _activate_qa(context, browser_base_url, "vq-02-replay")
            recovery = context.new_page()
            recovery.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            recovery.locator(".gradio-container").wait_for(timeout=30_000)
            _click_replay(recovery)
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


def test_gap_01_real_loopback_workbench_has_two_student_zones(
    browser_base_url: str,
) -> None:
    """The first screen is a narrow input rail beside one wide result zone."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            for heading in ("开始诊断", "诊断结果"):
                page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=30_000)
            page.get_by_text("查看示例", exact=True).wait_for(timeout=30_000)
            visible_before_viewport = []
            for text, locator in (
                ("开始诊断", page.get_by_role("heading", name="开始诊断", exact=True)),
                ("诊断结果", page.get_by_role("heading", name="诊断结果", exact=True)),
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
            assert page.get_by_text("查看示例", exact=True).is_visible()
            assert page.locator("#replay-action").is_hidden()
            screenshot = _capture_failure_screenshot(page)
            metrics = page.evaluate(
                """() => ({
                    regions: ['.control-rail', '.diagnosis-canvas'].map((selector) => {
                        const element = document.querySelector(`#workbench-grid ${selector}`);
                        const box = element.getBoundingClientRect();
                        return { selector, width: box.width, y: box.y };
                    }),
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                })"""
            )
        finally:
            browser.close()
    if screenshot is not None:
        assert screenshot.is_file()
    assert len(metrics["regions"]) == 2
    control_rail, result_zone = metrics["regions"]
    assert 320 <= control_rail["width"] <= 360
    assert result_zone["width"] > control_rail["width"]
    assert all(item["y"] < 768 for item in metrics["regions"])
    assert visible_before_viewport == [
        {"text": "开始诊断", "visible": True},
        {"text": "诊断结果", "visible": True},
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
            preview = page.get_by_role("button", name="1. 生成脱敏预览", exact=True)
            approve = page.get_by_role("button", name="2. 确认并开始诊断", exact=True)
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


def test_gap_01_real_loopback_workbench_stacks_student_zones_at_1024px(
    browser_base_url: str,
) -> None:
    """The compact breakpoint keeps a single, result-oriented reading column."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1024, "height": 768})
            page.goto(browser_base_url, wait_until="domcontentloaded", timeout=30_000)
            page.locator(".gradio-container").wait_for(timeout=30_000)
            for heading in ("开始诊断", "诊断结果"):
                page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=30_000)
            page.get_by_text("查看示例", exact=True).wait_for(timeout=30_000)
            metrics = page.evaluate(
                """() => ({
                    regions: ['.control-rail', '.diagnosis-canvas'].map((selector) => {
                        const element = document.querySelector(`#workbench-grid ${selector}`);
                        const box = element.getBoundingClientRect();
                        return {
                            selector, x: box.x, y: box.y,
                            width: box.width, height: box.height
                        };
                    }),
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                })"""
            )
        finally:
            browser.close()
    assert len(metrics["regions"]) == 2
    control_rail, diagnosis_canvas = metrics["regions"]
    assert abs(control_rail["x"] - diagnosis_canvas["x"]) <= 1
    assert diagnosis_canvas["y"] > control_rail["y"]
    assert abs(control_rail["width"] - diagnosis_canvas["width"]) <= 1
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
            for heading in ("开始诊断", "诊断结果", "多模态与完整报告"):
                page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=30_000)
            example_disclosure = _tab_to(page, expected_name="查看示例", limit=20)
            example_disclosure.press("Space")
            replay_label = page.get_by_text("示例案例", exact=True)
            replay_label.wait_for(timeout=30_000)
            replay_button = page.get_by_role("button", name="加载回放案例", exact=True)
            replay_button.wait_for(timeout=30_000)
            assert replay_button.is_enabled()
            replay_boxes = [replay_label.bounding_box(), replay_button.bounding_box()]
            keyboard_replay = _tab_to(
                page,
                expected_id="replay-action",
                expected_name="加载回放案例",
                limit=20,
            )
            keyboard_replay.press("Enter")
            _wait_for_terminal_status(page, "✓ 已完成")
            metrics = page.evaluate(
                """() => ({
                    regions: [
                        '.control-rail', '.diagnosis-canvas', '.result-workspace'
                    ].map((selector) => {
                        const element = document.querySelector(`#workbench-grid ${selector}`);
                        const box = element.getBoundingClientRect();
                        return {
                            selector, x: box.x, y: box.y,
                            width: box.width, height: box.height
                        };
                    }),
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                })"""
            )
        finally:
            browser.close()
    assert len(metrics["regions"]) == 3
    control_rail, diagnosis_canvas, result_workspace = metrics["regions"]
    assert abs(control_rail["x"] - diagnosis_canvas["x"]) <= 1
    assert abs(diagnosis_canvas["x"] - result_workspace["x"]) <= 1
    assert control_rail["y"] < diagnosis_canvas["y"] < result_workspace["y"]
    assert all(
        box is not None
        and box["width"] > 0
        and box["height"] > 0
        and box["y"] >= 0
        and box["y"] + box["height"] <= 1024
        for box in replay_boxes
    )
    assert metrics["scrollWidth"] == metrics["clientWidth"]
