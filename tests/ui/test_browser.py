"""Real Microsoft Edge visual verification for the Phase 4 workbench.

The browser marker deliberately launches the loopback-only application rather
than loading a fixture HTML page.  Screenshots are evidence of the currently
implemented Gradio application, including failures that block Phase 4 visual
acceptance.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import httpx
import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.browser

_ROOT = Path(__file__).resolve().parents[2]
_EVIDENCE = _ROOT / "evidence" / "ui" / "phase4"
_FAILURE_SCREENSHOT_ENV = "DEBUGMATE_UI_FAILURE_SCREENSHOT"
_FAILURE_SCREENSHOT = _EVIDENCE / "tmp" / "GAP-01-layout-red.png"
_UI_BASE_URL_ENV = "DEBUGMATE_UI_BASE_URL"
_STRICT_LOOPBACK_BASE_URL = re.compile(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})\Z")
_RUNNER = _ROOT / "scripts" / "run-phase4-browser-layout-qa.ps1"
_LOCAL_LIVE_RUNNER = _ROOT / "scripts" / "run-phase4-local-live-qa.ps1"
_LOCAL_LIVE_SCREENSHOT_ENV = "DEBUGMATE_UI_SCREENSHOT_PATH"
_LOCAL_LIVE_LEDGER = _EVIDENCE / "local-live-vq01.json"
_LOCAL_LIVE_RESULTS = _ROOT / ".debugmate-runtime" / "results"
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
    for key in (
        "case_id_sha256",
        "source_run_id_sha256",
        "result_id_sha256",
        "screenshot_sha256",
    ):
        assert re.fullmatch(r"[0-9a-f]{64}", payload[key])


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
            approve = page.get_by_role(
                "button", name="确认预览并开始本地诊断", exact=True
            )
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

            assert "✓ 已完成" in status_text
            assert "后端：local-rule-v1（本地规则，无云端调用）" in body_text
            assert "实时诊断" in result_metadata
            source_run_match = re.search(r"run_[0-9a-f]{32}", result_metadata)
            assert source_run_match is not None
            assert "fixture_id=null" in result_metadata
            assert "fixture_name=null" in result_metadata
            assert "回放" not in result_metadata
            assert "module-not-found" not in result_metadata
            assert "ModuleNotFoundError：缺少虚构依赖包" not in result_metadata
            assert report_visible
            assert "DebugMate" in report_text
            assert citations_visible
            assert download_enabled
            assert metrics["scrollWidth"] == metrics["clientWidth"]

            manifests_after = set(
                _LOCAL_LIVE_RESULTS.glob("case_*/result_*/result-manifest.json")
            )
            fresh_manifests = manifests_after - manifests_before
            assert len(fresh_manifests) == 1
            result_manifest = json.loads(
                fresh_manifests.pop().read_text(encoding="utf-8")
            )
            identity = result_manifest["identity"]
            assert result_manifest["status"] == "completed"
            assert result_manifest["mode"] == "live"
            assert result_manifest["fixture_id"] is None
            assert result_manifest["fixture_name"] is None
            assert re.fullmatch(r"case_[0-9a-f]{32}", identity["case_id"])
            assert identity["source_run_id"] == source_run_match.group(0)
            assert re.fullmatch(r"result_[0-9a-f]{32}", result_manifest["result_id"])

            screenshot_value = os.environ.get(_LOCAL_LIVE_SCREENSHOT_ENV)
            if screenshot_value is not None:
                screenshot_path = Path(screenshot_value).resolve()
                expected_path = (_EVIDENCE / "VQ-01-live-local.png").resolve()
                assert screenshot_path == expected_path
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
                    "backend": "local-rule-v1",
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
                    "body_horizontal_overflow": False,
                    "server_owner": "run-phase4-local-live-qa.ps1",
                    "verified_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                }
                assert set(ledger) == _LOCAL_LIVE_LEDGER_KEYS
                _LOCAL_LIVE_LEDGER.write_text(
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
    assert abs(
        (results_region["x"] + results_region["width"])
        - (evidence_region["x"] + evidence_region["width"])
    ) <= 1
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
