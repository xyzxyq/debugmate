"""Real Microsoft Edge visual verification for the Phase 4 workbench.

The browser marker deliberately launches the loopback-only application rather
than loading a fixture HTML page.  Screenshots are evidence of the currently
implemented Gradio application, including failures that block Phase 4 visual
acceptance.
"""

from __future__ import annotations

import hashlib
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


def test_vq_01_real_loopback_workbench_has_three_visible_regions() -> None:
    """VQ-01: the first screen must keep all three regions usable at 1366px."""

    port = _reserve_loopback_port()
    process = _start_loopback_server(port)
    _EVIDENCE.mkdir(parents=True, exist_ok=True)
    screenshot = _EVIDENCE / "VQ-01.png"
    try:
        base_url = _wait_for_config(port, process)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                page = browser.new_page(viewport={"width": 1366, "height": 768})
                page.goto(base_url, wait_until="domcontentloaded", timeout=30_000)
                page.locator(".gradio-container").wait_for(timeout=30_000)
                page.wait_for_timeout(1_000)
                page.screenshot(path=str(screenshot), full_page=True)
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
        assert screenshot.is_file()
        assert hashlib.sha256(screenshot.read_bytes()).hexdigest()
        assert len(metrics["regions"]) == 3
        assert all(
            item["width"] >= minimum
            for item, minimum in zip(metrics["regions"], (280, 360, 440), strict=True)
        )
        assert all(item["y"] < 768 for item in metrics["regions"])
        assert metrics["scrollWidth"] == metrics["clientWidth"]
    finally:
        _stop_loopback_server(process, port)
