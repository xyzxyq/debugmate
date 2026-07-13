from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from debugmate.hashing import sha256_bytes
from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
from debugmate.results.contracts import ArtifactIdentity
from debugmate.results.media import probe_mp3
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import RateProfile, TtsRequestIdentity
from debugmate.results.tts.dify import DifyTtsAdapter
from debugmate.results.tts.edge import EdgeTtsAdapter
from debugmate.results.tts.sapi import SapiTtsAdapter
from debugmate.settings import DebugMateSettings


def _safe_recap() -> SafeRecapText:
    units = (
        "现象：程序启动时反复出现 ModuleNotFoundError，导致人工智能实验无法继续运行。",
        "主要原因与不确定性：当前 Python 环境很可能缺少 numpy，"
        "但仍需确认解释器和安装环境是否一致。",
        "首次检查：先确认正在使用的 Python 解释器，再检查 numpy 是否安装在同一个虚拟环境中。",
        "首次修复：在已确认的虚拟环境中补齐项目锁定的依赖，不要改动无关环境。",
        "验证：重新启动解释器并执行最小导入测试，然后再次运行原始实验入口。",
        "剩余限制：若仍然失败，需要继续核对环境变量、依赖版本和项目启动方式。",
    )
    text = "\n".join(units)
    return SafeRecapText(
        identity=ArtifactIdentity(
            case_id="case_" + "1" * 32,
            source_run_id="run_" + "2" * 32,
            diagnosis_sha256="3" * 64,
            schema_version="1.1.0",
            generation_version="gen_" + "4" * 32,
        ),
        text=text,
        sha256=sha256_bytes(text.encode("utf-8")),
        units=units,
        word_budget_version="recap_budget_v1",
    )


def _identity(recap: SafeRecapText) -> TtsRequestIdentity:
    return TtsRequestIdentity(
        case_id="case_" + "1" * 32,
        source_run_id="run_" + "2" * 32,
        diagnosis_sha256="3" * 64,
        generation_version="gen_" + "4" * 32,
        recap_sha256=recap.sha256,
    )


def _assert_live_candidate(
    candidate, *, backend: str, request: TtsRequestIdentity, tmp_path: Path
) -> None:
    media = tmp_path / f"{backend}.mp3"
    media.write_bytes(candidate.audio_bytes)
    probe = probe_mp3(media, timeout_seconds=15, max_bytes=8_000_000)
    assert candidate.backend == backend
    assert candidate.rate_profile is RateProfile.NORMAL
    assert candidate.request_identity == request
    assert len(candidate.audio_bytes) == probe.bytes
    assert probe.codec == "mp3"
    assert probe.channels == 1
    assert probe.sha256 != "0" * 64
    evidence = candidate.model_dump_json()
    assert _safe_recap().text not in evidence
    assert "DIFY_API_KEY" not in evidence


def _assert_value_free_rejection(adapter, recap: SafeRecapText) -> None:
    secret = "token=debugmate-fictional-secret-0123456789"
    unsafe = recap.model_copy(
        update={"text": secret, "sha256": sha256_bytes(secret.encode("utf-8"))}
    )
    with pytest.raises(RuntimeError, match="^tts_backend_failed$") as caught:
        adapter.synthesize(unsafe, _identity(recap), RateProfile.NORMAL)
    assert secret not in str(caught.value)


@pytest.mark.tts
@pytest.mark.skipif(os.name != "nt", reason="Windows SAPI gate")
def test_real_local_sapi_produces_verified_tag_free_mono_mp3(tmp_path: Path) -> None:
    recap = _safe_recap()
    candidate = SapiTtsAdapter().synthesize(recap, _identity(recap), RateProfile.NORMAL)
    target = tmp_path / "sapi.mp3"
    target.write_bytes(candidate.audio_bytes)
    probe = probe_mp3(target, timeout_seconds=15, max_bytes=8_000_000)
    assert probe.codec == "mp3"
    assert probe.channels == 1
    assert 30_000 <= probe.duration_ms <= 60_000
    assert candidate.voice == "Microsoft Huihui Desktop"


@pytest.mark.tts
@pytest.mark.skipif(os.name != "nt", reason="Windows SAPI junction gate")
def test_real_sapi_cannot_write_recap_into_a_nested_temp_junction(tmp_path: Path) -> None:
    """The real adapter has no temp-file output argument to redirect through a Junction."""

    safe = tmp_path / "safe"
    outside = tmp_path / "outside"
    safe.mkdir()
    outside.mkdir()
    junction = safe / "nested"
    created = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        check=False,
        shell=False,
        timeout=10,
    )
    if created.returncode != 0:  # pragma: no cover - host capability gate
        pytest.fail("could not create required SAPI junction attack fixture")

    SapiTtsAdapter().synthesize(_safe_recap(), _identity(_safe_recap()), RateProfile.NORMAL)

    assert not list(outside.iterdir())


@pytest.mark.tts
@pytest.mark.skipif(os.name != "nt", reason="Windows controlled-chain gate")
def test_real_sapi_payload_survives_the_leased_candidate_and_canonicalisation_chain(
    tmp_path: Path,
) -> None:
    """Exercise the real SAPI result through the lease, ffprobe and bytes-only FFmpeg path."""

    class FailingAdapter:
        def __init__(self, backend: str) -> None:
            self.backend = backend

        def synthesize(self, *_args: object) -> object:
            raise RuntimeError("deliberate test fallback")

    recap = _safe_recap()
    result = TtsFallbackChain(
        (FailingAdapter("dify"), FailingAdapter("edge_tts"), SapiTtsAdapter())
    ).synthesize(
        recap,
        _identity(recap),
        TrustedCandidateRoot.for_testing(tmp_path / "private-candidates"),
    )

    assert result.audio.available is True
    assert result.audio.backend == "sapi"
    assert 30_000 <= result.audio.duration_ms <= 60_000


@pytest.mark.cloud
@pytest.mark.tts
def test_live_dify_tts_gate(tmp_path: Path) -> None:
    settings = DebugMateSettings.from_env()
    if not settings.cloud_configured:
        pytest.skip("DIFY_API_KEY is absent; external gate remains open")
    recap = _safe_recap()
    request = _identity(recap)
    adapter = DifyTtsAdapter(settings)
    candidate = adapter.synthesize(recap, request, RateProfile.NORMAL)
    _assert_live_candidate(candidate, backend="dify", request=request, tmp_path=tmp_path)
    _assert_value_free_rejection(adapter, recap)


@pytest.mark.network
@pytest.mark.tts
def test_live_edge_tts_gate(tmp_path: Path) -> None:
    if os.environ.get("DEBUGMATE_ALLOW_NETWORK_TTS") != "1":
        pytest.skip("network TTS not explicitly approved; external gate remains open")
    recap = _safe_recap()
    request = _identity(recap)
    adapter = EdgeTtsAdapter()
    candidate = adapter.synthesize(recap, request, RateProfile.NORMAL)
    _assert_live_candidate(candidate, backend="edge_tts", request=request, tmp_path=tmp_path)
    assert candidate.voice == "zh-CN-XiaoxiaoNeural"
    _assert_value_free_rejection(adapter, recap)
