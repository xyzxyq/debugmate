"""Real Microsoft Edge visual verification for the Phase 4 workbench.

The browser marker deliberately launches the loopback-only application rather
than loading a fixture HTML page.  Screenshots are evidence of the currently
implemented Gradio application, including failures that block Phase 4 visual
acceptance.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.browser

_ROOT = Path(__file__).resolve().parents[2]
_EVIDENCE = _ROOT / "evidence" / "ui" / "phase4"
_FAILURE_SCREENSHOT_ENV = "DEBUGMATE_UI_FAILURE_SCREENSHOT"
_FAILURE_SCREENSHOT = _EVIDENCE / "tmp" / "GAP-01-layout-red.png"


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


def _wait_for_config(port: int, process: subprocess.Popen[bytes]) -> str:
    deadline = time.monotonic() + 30.0
    url = f"http://127.0.0.1:{port}"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail("loopback Gradio process exited before /config became ready")
        try:
            response = httpx.get(f"{url}/config", timeout=1.0)
            payload = response.json()
            if response.status_code == 200 and isinstance(payload.get("components"), list):
                return url
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(0.25)
    pytest.fail("loopback Gradio /config did not become ready in 30 seconds")


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


def _capture_failure_screenshot(page) -> Path | None:
    """Capture only an explicitly requested, ignored temporary diagnostic image."""

    if os.environ.get(_FAILURE_SCREENSHOT_ENV) != "1":
        return None
    _FAILURE_SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(_FAILURE_SCREENSHOT), full_page=True)
    return _FAILURE_SCREENSHOT


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


def test_gap_01_real_loopback_workbench_has_three_usable_regions() -> None:
    """RED: the first screen must keep its three regions usable at 1366px."""

    port = _reserve_loopback_port()
    process = _start_loopback_server(port)
    try:
        base_url = _wait_for_config(port, process)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                page = browser.new_page(viewport={"width": 1366, "height": 768})
                page.goto(base_url, wait_until="domcontentloaded", timeout=30_000)
                page.locator(".gradio-container").wait_for(timeout=30_000)
                for heading in ("输入与抽取", "诊断与证据", "三模态结果"):
                    page.get_by_role("heading", name=heading, exact=True).wait_for(timeout=30_000)
                page.get_by_text("固定回放案例", exact=True).wait_for(timeout=30_000)
                page.get_by_role("button", name="加载回放案例", exact=True).wait_for(
                    timeout=30_000
                )
                visible_before_viewport = []
                for text, locator in (
                    (
                        "输入与抽取",
                        page.get_by_role("heading", name="输入与抽取", exact=True),
                    ),
                    (
                        "诊断与证据",
                        page.get_by_role("heading", name="诊断与证据", exact=True),
                    ),
                    (
                        "三模态结果",
                        page.get_by_role("heading", name="三模态结果", exact=True),
                    ),
                    ("固定回放案例", page.get_by_text("固定回放案例", exact=True)),
                    (
                        "加载回放案例",
                        page.get_by_role("button", name="加载回放案例", exact=True),
                    ),
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
    finally:
        _stop_loopback_server(process, port)
