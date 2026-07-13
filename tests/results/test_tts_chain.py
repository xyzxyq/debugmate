from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from debugmate.hashing import sha256_bytes
from debugmate.results.audio import TtsFallbackChain
from debugmate.results.contracts import ArtifactIdentity
from debugmate.results.media import MediaProbe, MediaProbeError
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import AudioCandidate, RateProfile, TtsRequestIdentity
from debugmate.results.tts.dify import DifyTtsAdapter
from debugmate.results.tts.edge import EdgeTtsAdapter
from debugmate.results.tts.sapi import SapiTtsAdapter
from debugmate.settings import DebugMateSettings


def _recap() -> SafeRecapText:
    return SafeRecapText.model_construct(
        identity=ArtifactIdentity(
            case_id="case_" + "1" * 32,
            source_run_id="run_" + "2" * 32,
            diagnosis_sha256="3" * 64,
            schema_version="1.1.0",
            generation_version="gen_" + "4" * 32,
        ),
        text=(
            "现象：ModuleNotFoundError。主要原因：缺少 numpy。首次检查：检查环境。"
            "首次修复：安装依赖。验证：重新导入。限制：仍需确认环境。"
        ),
        sha256="a" * 64,
        units=("a", "b", "c", "d", "e", "f"),
        word_budget_version="recap_budget_v1",
    )


class FakeAdapter:
    def __init__(self, backend: str, outcomes: list[str], calls: list[tuple[str, str]]):
        self.backend = backend
        self._outcomes = iter(outcomes)
        self._calls = calls

    def synthesize(self, text, target, request_identity, rate_profile):
        self._calls.append((self.backend, rate_profile.value))
        outcome = next(self._outcomes)
        if outcome != "ok":
            raise RuntimeError(outcome)
        target.write_bytes(b"\xff\xfb" + b"x" * 64)
        return AudioCandidate(
            backend=self.backend,
            rate_profile=rate_profile,
            path=target,
            request_identity=request_identity,
        )


def _identity() -> TtsRequestIdentity:
    return TtsRequestIdentity(
        case_id="case_" + "1" * 32,
        source_run_id="run_" + "2" * 32,
        diagnosis_sha256="3" * 64,
        generation_version="gen_" + "4" * 32,
        recap_sha256="a" * 64,
    )


def _probe(path: Path, **_kwargs) -> MediaProbe:
    return MediaProbe(
        duration_ms=45_000, codec="mp3", channels=1, bytes=path.stat().st_size, sha256="b" * 64
    )


def test_fallback_order_and_success_short_circuit(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    chain = TtsFallbackChain(
        (
            FakeAdapter("dify", ["transport"], calls),
            FakeAdapter("edge_tts", ["ok"], calls),
            FakeAdapter("sapi", ["ok"], calls),
        )
    )
    result = chain.synthesize(_recap(), _identity(), tmp_path)
    assert calls == [("dify", "normal"), ("edge_tts", "normal")]
    assert result.available is True
    assert result.backend == "edge_tts"
    assert result.fallback_used is True
    assert result.attempts[0].safe_error_code == "tts_backend_failed"
    assert result.attempts[-1].sha256 == "b" * 64


def test_chain_rejects_missing_duplicate_custom_or_reordered_backends() -> None:
    calls: list[tuple[str, str]] = []
    dify = FakeAdapter("dify", ["ok"], calls)
    edge = FakeAdapter("edge_tts", ["ok"], calls)
    sapi = FakeAdapter("sapi", ["ok"], calls)
    for adapters in (
        (dify, edge),
        (dify, edge, edge),
        (edge, dify, sapi),
        (dify, FakeAdapter("custom", ["ok"], calls), sapi),
    ):
        with pytest.raises(ValueError, match="tts_chain_invalid"):
            TtsFallbackChain(adapters)


def test_chain_rejects_external_or_identity_mismatched_candidate(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    outside = tmp_path.parent / "outside-valid.mp3"
    outside.write_bytes(b"\xff\xfb" + b"x" * 64)

    class MaliciousAdapter(FakeAdapter):
        def synthesize(self, text, target, request_identity, rate_profile):
            self._calls.append((self.backend, rate_profile.value))
            return AudioCandidate(
                backend=self.backend,
                rate_profile=rate_profile,
                path=outside,
                request_identity=request_identity.model_copy(update={"recap_sha256": "9" * 64}),
            )

    calls: list[tuple[str, str]] = []
    chain = TtsFallbackChain(
        (
            MaliciousAdapter("dify", [], calls),
            FakeAdapter("edge_tts", ["timeout"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    )
    result = chain.synthesize(_recap(), _identity(), tmp_path / "result")
    assert result.available is False
    assert result.attempts[0].safe_error_code == "tts_candidate_invalid"
    assert not (tmp_path / "result" / "recap.mp3").exists()


def test_duration_failure_retries_once_then_falls_through(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    adapter = FakeAdapter("dify", ["ok", "ok"], calls)
    probes = iter((MediaProbeError("duration_out_of_range"), _probe, _probe))

    def varying_probe(path, **kwargs):
        value = next(probes)
        if isinstance(value, Exception):
            raise value
        return value(path, **kwargs)

    monkeypatch.setattr("debugmate.results.audio.probe_mp3", varying_probe)
    result = TtsFallbackChain(
        (
            adapter,
            FakeAdapter("edge_tts", ["timeout"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    ).synthesize(_recap(), _identity(), tmp_path)
    assert calls == [("dify", "normal"), ("dify", "faster")]
    assert result.available is True
    assert len(result.attempts) == 2


def test_non_duration_failure_never_retries_and_all_failed_is_partial(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    chain = TtsFallbackChain(
        (
            FakeAdapter("dify", ["timeout"], calls),
            FakeAdapter("edge_tts", ["bad_content"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    )
    result = chain.synthesize(_recap(), _identity(), tmp_path)
    assert calls == [("dify", "normal"), ("edge_tts", "normal"), ("sapi", "normal")]
    assert result.available is False
    assert result.failure.code == "tts_failed"
    assert not list(tmp_path.glob("*.mp3"))
    dumped = result.model_dump_json()
    assert _recap().text not in dumped
    assert str(tmp_path) not in dumped


def test_dify_rejects_wrong_content_type_and_oversize_without_persisting(tmp_path: Path) -> None:
    for response in (
        httpx.Response(200, headers={"content-type": "text/plain"}, content=b"secret"),
        httpx.Response(
            200,
            headers={"content-type": "audio/mpeg"},
            content=b"x" * 65,
        ),
    ):
        client = httpx.Client(
            transport=httpx.MockTransport(lambda _request, current=response: current)
        )
        settings = DebugMateSettings.from_env({"DIFY_API_KEY": "fictional-test-key"})
        adapter = DifyTtsAdapter(settings, client=client, max_bytes=64)
        target = tmp_path / "candidate.mp3"
        try:
            adapter.synthesize(_recap(), target, _identity(), RateProfile.NORMAL)
        except RuntimeError as exc:
            assert str(exc) == "tts_backend_failed"
        else:  # pragma: no cover - guards a security contract
            raise AssertionError("unsafe Dify response was accepted")
        assert not target.exists()


def test_sapi_uses_file_boundary_and_never_places_recap_in_argv(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[list[str], bool]] = []

    def fake_run(argv, **kwargs):
        calls.append((list(argv), kwargs["shell"]))
        if "-OutputWaveFile" in argv:
            Path(argv[argv.index("-OutputWaveFile") + 1]).write_bytes(b"RIFF")
        else:
            Path(argv[-1]).write_bytes(b"\xff\xfbfixture")

    monkeypatch.setattr("debugmate.results.tts.sapi.subprocess.run", fake_run)
    target = tmp_path / "candidate.mp3"
    SapiTtsAdapter(project_root=Path.cwd()).synthesize(
        _recap(), target, _identity(), RateProfile.NORMAL
    )
    flattened = [item for argv, _ in calls for item in argv]
    assert "-Command" not in flattened
    assert _recap().text not in flattened
    assert all(shell is False for _, shell in calls)
    assert calls[0][0][3] == "-File"
    assert target.exists()
    assert not list(tmp_path.rglob("*.wav"))


def test_all_adapters_reject_constructed_secret_and_mismatched_identity(
    tmp_path: Path, monkeypatch
) -> None:
    secret = "token=debugmate-fictional-secret-0123456789"
    unsafe = _recap().model_copy(
        update={"text": secret, "sha256": sha256_bytes(secret.encode("utf-8"))}
    )
    wrong_identity = _identity().model_copy(update={"recap_sha256": "f" * 64})
    settings = DebugMateSettings.from_env({"DIFY_API_KEY": "fictional-test-key"})
    adapters = (
        DifyTtsAdapter(
            settings,
            client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))),
        ),
        EdgeTtsAdapter(),
        SapiTtsAdapter(project_root=Path.cwd()),
    )
    monkeypatch.setattr("debugmate.results.tts.edge.asyncio.run", lambda _: None)
    monkeypatch.setattr("debugmate.results.tts.sapi.subprocess.run", lambda *_a, **_kw: None)

    for index, adapter in enumerate(adapters):
        with pytest.raises(RuntimeError, match="^tts_backend_failed$") as caught:
            adapter.synthesize(
                unsafe, tmp_path / f"unsafe-{index}.mp3", _identity(), RateProfile.NORMAL
            )
        assert secret not in str(caught.value)
        with pytest.raises(RuntimeError, match="^tts_backend_failed$"):
            adapter.synthesize(
                _recap(), tmp_path / f"identity-{index}.mp3", wrong_identity, RateProfile.NORMAL
            )
