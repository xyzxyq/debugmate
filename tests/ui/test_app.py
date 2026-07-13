from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from debugmate.results.contracts import (
    ArtifactAvailability,
    ArtifactIdentity,
    AudioAttempt,
    AudioResult,
    ResultMode,
    ResultStatus,
    ResultViewState,
)
from debugmate.ui.app import build_app


def _completed_state() -> ResultViewState:
    identity = ArtifactIdentity(
        case_id="case_" + "1" * 32,
        source_run_id="run_" + "2" * 32,
        diagnosis_sha256="3" * 64,
        schema_version="1.1.0",
        generation_version="gen_" + "4" * 32,
    )
    audio = AudioResult(
        identity=identity,
        available=True,
        backend="dify",
        attempts=(
            AudioAttempt(
                backend="dify",
                rate_profile="normal",
                succeeded=True,
                duration_ms=40_000,
                sha256="5" * 64,
            ),
        ),
        duration_ms=40_000,
        sha256="5" * 64,
    )
    return ResultViewState(
        mode=ResultMode.LIVE,
        status=ResultStatus.COMPLETED,
        identity=identity,
        result_id="result_" + "6" * 32,
        availability=ArtifactAvailability(report=True, card=True, recap_text=True, audio=True),
        audio=audio,
    )


class _Service:
    """Minimal strict façade fake; the app must not need an outcome or path."""

    def load_replay(self, fixture_id: str) -> ResultViewState:
        assert fixture_id == "module-not-found"
        return _completed_state()


def test_build_app_has_native_three_region_workbench_and_no_unsafe_components() -> None:
    app = build_app(_Service())
    config = app.get_config_file()
    rendered = repr(config)

    for text in (
        "DebugMate 诊断工作台",
        "输入与抽取",
        "诊断与证据",
        "三模态结果",
        "文字报告",
        "诊断卡",
        "语音复盘",
        "引用与下载",
        "确认修改并重新诊断",
        "诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。",
        "页面仅展示已验证的脱敏输入与结果。",
    ):
        assert text in rendered
    assert "html" not in {component["type"] for component in config["components"]}
    assert "subprocess" not in Path("src/debugmate/ui/app.py").read_text(encoding="utf-8")
    assert "gr.HTML" not in Path("src/debugmate/ui/app.py").read_text(encoding="utf-8")
    assert "@media (max-width: 1199px)" in app.css
    assert "@media (max-width: 899px)" in app.css
    assert "overflow-x: hidden" not in app.css


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def test_serve_rejects_non_loopback_and_exposes_only_local_config_endpoint(tmp_path: Path) -> None:
    invalid = subprocess.run(
        [
            sys.executable,
            "-m",
            "debugmate.ui.serve",
            "--host",
            "0.0.0.0",
            "--port",
            "7860",
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert invalid.returncode != 0

    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "debugmate.ui.serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        response = None
        while time.monotonic() < deadline:
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/config", timeout=1)
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        assert response is not None and response.status_code == 200
        payload = response.json()
        assert isinstance(payload.get("version"), str)
        assert isinstance(payload.get("components"), list)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        assert probe.connect_ex(("127.0.0.1", port)) != 0
