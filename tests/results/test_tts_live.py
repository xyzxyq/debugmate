from __future__ import annotations

import os
from pathlib import Path

import pytest

from debugmate.hashing import sha256_bytes
from debugmate.results.media import probe_mp3
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import RateProfile, TtsRequestIdentity
from debugmate.results.tts.dify import DifyTtsAdapter
from debugmate.results.tts.edge import EdgeTtsAdapter
from debugmate.results.tts.sapi import SapiTtsAdapter
from debugmate.settings import DebugMateSettings


def _safe_recap() -> SafeRecapText:
    text = (
        "现象：程序启动时反复出现 ModuleNotFoundError，导致人工智能实验无法继续运行。"
        "主要原因与不确定性：当前 Python 环境很可能缺少 numpy，但仍需确认解释器和安装环境是否一致。"
        "首次检查：先确认正在使用的 Python 解释器，再检查 numpy 是否安装在同一个虚拟环境中。"
        "首次修复：在已确认的虚拟环境中补齐项目锁定的依赖，不要改动无关环境。"
        "验证：重新启动解释器并执行最小导入测试，然后再次运行原始实验入口。"
        "剩余限制：若仍然失败，需要继续核对环境变量、依赖版本和项目启动方式。"
    )
    return SafeRecapText.model_construct(
        identity=None,
        text=text,
        sha256=sha256_bytes(text.encode("utf-8")),
        units=("phenomenon", "cause", "check", "fix", "verify", "limitation"),
        word_budget_version="recap-v1",
    )


def _identity(recap: SafeRecapText) -> TtsRequestIdentity:
    return TtsRequestIdentity(
        case_id="case_" + "1" * 32,
        source_run_id="run_" + "2" * 32,
        diagnosis_sha256="3" * 64,
        generation_version="gen_" + "4" * 32,
        recap_sha256=recap.sha256,
    )


@pytest.mark.tts
@pytest.mark.skipif(os.name != "nt", reason="Windows SAPI gate")
def test_real_local_sapi_produces_verified_tag_free_mono_mp3(tmp_path: Path) -> None:
    recap = _safe_recap()
    target = tmp_path / "sapi.mp3"
    candidate = SapiTtsAdapter().synthesize(recap, target, _identity(recap), RateProfile.NORMAL)
    probe = probe_mp3(candidate.path, timeout_seconds=15, max_bytes=8_000_000)
    assert probe.codec == "mp3"
    assert probe.channels == 1
    assert 30_000 <= probe.duration_ms <= 60_000
    assert candidate.voice == "Microsoft Huihui Desktop"
    assert not list(tmp_path.rglob("*.wav"))


@pytest.mark.cloud
@pytest.mark.tts
def test_live_dify_tts_gate(tmp_path: Path) -> None:
    settings = DebugMateSettings.from_env()
    if not settings.cloud_configured:
        pytest.skip("DIFY_API_KEY is absent; external gate remains open")
    recap = _safe_recap()
    candidate = DifyTtsAdapter(settings).synthesize(recap, tmp_path / "dify.mp3", _identity(recap), RateProfile.NORMAL)
    assert probe_mp3(candidate.path, timeout_seconds=15, max_bytes=8_000_000).channels == 1


@pytest.mark.network
@pytest.mark.tts
def test_live_edge_tts_gate(tmp_path: Path) -> None:
    if os.environ.get("DEBUGMATE_ALLOW_NETWORK_TTS") != "1":
        pytest.skip("network TTS not explicitly approved; external gate remains open")
    recap = _safe_recap()
    candidate = EdgeTtsAdapter().synthesize(recap, tmp_path / "edge.mp3", _identity(recap), RateProfile.NORMAL)
    assert probe_mp3(candidate.path, timeout_seconds=15, max_bytes=8_000_000).channels == 1
