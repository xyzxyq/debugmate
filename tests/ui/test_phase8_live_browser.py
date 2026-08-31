"""Phase 08 real Edge acceptance for the Dify-backed workbench.

The browser test intentionally has no fallback path.  The Phase 08 runner sets
the readiness variables and owns the loopback server; if either prerequisite is
missing this test fails instead of silently becoming a passing skip.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "tests" / "fixtures" / "cloud" / "phase8-live-case.json"
IMAGE_PATH = ROOT / "tests" / "fixtures" / "phase8" / "terminal-module-not-found-redacted.png"
BASE_URL_ENV = "DEBUGMATE_UI_BASE_URL"
QA_RUN_ENV = "DEBUGMATE_PHASE8_QA_RUN_ID"
STAGING_ENV = "DEBUGMATE_PHASE8_STAGING_DIR"
EXPECTED_BACKEND_ENV = "DEBUGMATE_PHASE8_EXPECTED_BACKEND"


def _require_runner_environment() -> tuple[str, str, Path, str]:
    base_url = os.environ.get(BASE_URL_ENV, "").strip()
    qa_run_id = os.environ.get(QA_RUN_ENV, "").strip()
    staging = os.environ.get(STAGING_ENV, "").strip()
    expected_backend = os.environ.get(EXPECTED_BACKEND_ENV, "dify").strip()
    if not base_url or not qa_run_id or not staging:
        pytest.fail("phase8_runner_environment_missing")
    if not base_url.startswith("http://127.0.0.1:"):
        pytest.fail("phase8_browser_must_use_owned_loopback")
    if expected_backend not in {"dify", "local_fallback"}:
        pytest.fail("phase8_expected_backend_invalid")
    image_hash = hashlib.sha256(IMAGE_PATH.read_bytes()).hexdigest() if IMAGE_PATH.is_file() else ""
    if not IMAGE_PATH.is_file() or image_hash != _case_hash():
        pytest.fail("phase8_committed_png_hash_mismatch")
    return base_url, qa_run_id, Path(staging), expected_backend


def _case_hash() -> str:
    import json

    payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    value = payload.get("screenshot_sha256")
    if not isinstance(value, str):
        pytest.fail("phase8_case_image_hash_missing")
    return value


def _page(browser_page: Page) -> Page:
    browser_page.set_default_timeout(15_000)
    browser_page.set_default_navigation_timeout(30_000)
    return browser_page


def test_phase8_runner_contract_is_explicit_and_zero_skip() -> None:
    runner = (ROOT / "scripts" / "run-phase8-live-qa.ps1").read_text(encoding="utf-8")
    security = (ROOT / "scripts" / "verify-phase8-security-scope.ps1").read_text(encoding="utf-8")
    for required in (
        "Assert-JUnitZeroIssues",
        "Start-Process",
        "-WindowStyle Hidden",
        "127.0.0.1",
        "Wait-ForLoopbackPortClosed",
        "Complete-Phase8EvidenceTransaction",
        "Restore-Phase8EvidenceTransaction",
        "tests/cloud/test_dify_live_cloud.py",
        "tests/ui/test_phase8_live_browser.py",
        "-m cloud",
        "-m browser",
    ):
        assert required in runner
    for required in (
        "Authorization",
        "provider",
        "raw_remote",
        "Test-FrozenTargets",
        "checksums.sha256",
    ):
        assert required.casefold() in security.casefold()


@pytest.mark.browser
def test_phase8_edge_real_four_field_approval_and_downloads() -> None:
    base_url, qa_run_id, staging, expected_backend = _require_runner_environment()
    if not staging.is_dir():
        pytest.fail("phase8_staging_directory_missing")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = _page(browser.new_page(viewport={"width": 1366, "height": 768}))
        try:
            page.goto(base_url, wait_until="domcontentloaded")
            expect(page.locator("#error-input")).to_be_visible()
            page.locator("#error-input textarea").fill(
                "ModuleNotFoundError: No module named 'debugmate_demo_dependency'"
            )
            page.get_by_text("补充诊断信息（可选）：代码、环境", exact=True).click()
            page.locator("#code-input textarea").fill(
                "from debugmate_demo_dependency import diagnose\nprint(diagnose())"
            )
            page.locator("#environment-input textarea").fill(
                "Python: 3.13\nOS: Windows 11\nCUDA: unavailable"
            )
            page.locator("#screenshot-input input[type=file]").set_input_files(IMAGE_PATH)
            # Gradio's file component does not expose a stable, version-independent
            # "Clear" aria label after Playwright uploads a file.  set_input_files
            # completes the upload synchronously from the browser test's perspective;
            # the preview assertion below provides the real readiness gate.
            page.locator("#local-preview").click()
            expect(page.locator("#preview-validity")).to_contain_text(
                "脱敏预览已就绪，请逐项检查后再确认。", timeout=60_000
            )
            expect(page.locator("#preview-screenshot")).to_be_visible()
            page.locator("#local-approve").click()

            expected_status = "dify" if expected_backend == "dify" else "本地降级"
            expect(page.locator("#diagnostic-status")).to_contain_text(
                expected_status, timeout=180_000
            )
            expect(page.locator("#result-tabs")).to_be_visible(timeout=180_000)
            expect(page.locator("#diagnostic-report")).to_be_visible()
            page.get_by_role("tab", name="诊断卡", exact=True).click()
            expect(page.locator("#diagnostic-card")).to_be_visible()
            page.get_by_role("tab", name="语音复盘", exact=True).click()
            expect(page.locator("#diagnostic-audio")).to_be_visible()
            page.get_by_role("tab", name="引用与下载", exact=True).click()

            with page.expect_download(timeout=30_000) as download_info:
                page.locator("#download-result").click()
            download = download_info.value
            target = staging / f"{qa_run_id}-result.zip"
            download.save_as(target)
            assert target.is_file() and target.stat().st_size > 0
        finally:
            browser.close()
