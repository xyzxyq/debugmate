from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from debugmate.hashing import sha256_bytes
from debugmate.results import audio as audio_module
from debugmate.results.audio import TrustedCandidateRoot, TtsFallbackChain
from debugmate.results.contracts import ArtifactIdentity
from debugmate.results.media import MediaProbe, MediaProbeError
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import AudioCandidate, RateProfile, TtsRequestIdentity
from debugmate.results.tts.dify import DifyTtsAdapter
from debugmate.results.tts import edge as edge_module
from debugmate.results.tts.edge import EdgeTtsAdapter
from debugmate.results.tts.sapi import SapiTtsAdapter
from debugmate.settings import DebugMateSettings


def _recap() -> SafeRecapText:
    units = (
        "phenomenon: ModuleNotFoundError",
        "cause: missing dependency",
        "check: inspect environment",
        "fix: restore locked dependency",
        "verify: rerun minimal import",
        "limitation: confirm in the real environment",
    )
    text = "\n".join(units)
    return SafeRecapText.model_construct(
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
    recap = _recap()
    return TtsRequestIdentity(
        case_id="case_" + "1" * 32,
        source_run_id="run_" + "2" * 32,
        diagnosis_sha256="3" * 64,
        generation_version="gen_" + "4" * 32,
        recap_sha256=recap.sha256,
    )


def _probe(path: Path, **_kwargs) -> MediaProbe:
    return MediaProbe(
        duration_ms=45_000, codec="mp3", channels=1, bytes=path.stat().st_size, sha256="b" * 64
    )


def _canonicalize(source: Path, target: Path, **_kwargs: object) -> MediaProbe:
    target.write_bytes(source.read_bytes())
    return _probe(target)


def _candidate_root(tmp_path: Path) -> TrustedCandidateRoot:
    """Create an explicit test capability; synthesis never receives a raw Path."""

    return TrustedCandidateRoot.for_testing(tmp_path / "debugmate-private-candidates")


def test_chain_requires_a_trusted_candidate_root_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An arbitrary caller directory must not be an output authority."""

    calls: list[tuple[str, str]] = []
    with pytest.raises(TypeError):
        TrustedCandidateRoot(tmp_path)
    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    monkeypatch.setattr("debugmate.results.audio.canonicalize_mp3", _canonicalize)
    chain = TtsFallbackChain(
        (
            FakeAdapter("dify", ["ok"], calls),
            FakeAdapter("edge_tts", ["ok"], calls),
            FakeAdapter("sapi", ["ok"], calls),
        )
    )

    with pytest.raises(TypeError):
        chain.synthesize(_recap(), _identity(), tmp_path / "caller-selected-output")

    result = chain.synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert result.available is True
    assert not (tmp_path / "caller-selected-output" / "recap.mp3").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction replacement attack")
def test_candidate_capability_blocks_junction_swap_during_canonicalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swap in the former canonicalization gap must never write outside."""

    root = tmp_path / "debugmate-private-candidates"
    outside = tmp_path / "outside"
    outside.mkdir()
    capability = _candidate_root(tmp_path)
    calls: list[tuple[str, str]] = []
    outside_was_created = False

    def swap_then_write(source: Path, target: Path, **_kwargs: object) -> MediaProbe:
        nonlocal outside_was_created
        payload = source.read_bytes()
        run = target.parent
        parked = root / f"{run.name}-parked"
        run.replace(parked)
        _make_junction(run, outside)
        target.write_bytes(payload)
        outside_was_created = (outside / "recap.mp3").exists()
        return _probe(target)

    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    monkeypatch.setattr("debugmate.results.audio.canonicalize_mp3", swap_then_write)
    chain = TtsFallbackChain(
        (
            FakeAdapter("dify", ["ok"], calls),
            FakeAdapter("edge_tts", ["transport"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    )

    result = chain.synthesize(_recap(), _identity(), capability)

    assert result.available is False
    assert outside_was_created is False
    assert not (outside / "recap.mp3").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction replacement attack")
def test_leased_temp_child_blocks_junction_swap_during_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact adapter temp directory is non-renamable before target exposure."""

    root = tmp_path / "debugmate-private-candidates"
    outside = tmp_path / "outside"
    outside.mkdir()
    calls: list[tuple[str, str]] = []
    attack_snapshots: list[bool] = []
    swap_attempted = False
    swap_succeeded = False

    class TempSwapAdapter:
        backend = "dify"

        def synthesize(self, text, target, request_identity, rate_profile):
            nonlocal swap_attempted, swap_succeeded
            temp = target.parent
            parked = root / f"{temp.name}-parked"
            swap_attempted = True
            try:
                temp.replace(parked)
                swap_succeeded = True
                _make_junction(temp, outside)
            except OSError:
                pass
            attack_snapshots.append((outside / target.name).exists())
            target.write_bytes(b"\xff\xfb" + b"x" * 64)
            attack_snapshots.append((outside / target.name).exists())
            return AudioCandidate(
                backend=self.backend,
                rate_profile=rate_profile,
                path=target,
                request_identity=request_identity,
            )

    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    monkeypatch.setattr("debugmate.results.audio.canonicalize_mp3", _canonicalize)
    result = TtsFallbackChain(
        (
            TempSwapAdapter(),
            FakeAdapter("edge_tts", ["transport"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert swap_attempted is True
    assert swap_succeeded is False
    assert attack_snapshots == [False, False]
    assert not list(outside.iterdir())
    assert result.available is True


def test_fallback_order_and_success_short_circuit(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    monkeypatch.setattr("debugmate.results.audio.canonicalize_mp3", _canonicalize)
    chain = TtsFallbackChain(
        (
            FakeAdapter("dify", ["transport"], calls),
            FakeAdapter("edge_tts", ["ok"], calls),
            FakeAdapter("sapi", ["ok"], calls),
        )
    )
    result = chain.synthesize(_recap(), _identity(), _candidate_root(tmp_path))
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
    result = chain.synthesize(_recap(), _identity(), _candidate_root(tmp_path))
    assert result.available is False
    assert result.attempts[0].safe_error_code == "tts_candidate_invalid"
    assert not list((tmp_path / "debugmate-private-candidates").rglob("recap.mp3"))


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
    monkeypatch.setattr("debugmate.results.audio.canonicalize_mp3", _canonicalize)
    result = TtsFallbackChain(
        (
            adapter,
            FakeAdapter("edge_tts", ["timeout"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))
    assert calls == [("dify", "normal"), ("dify", "faster")]
    assert result.available is True
    assert len(result.attempts) == 2


def test_chain_canonicalizes_a_verified_candidate_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[Path, Path]] = []
    adapter_calls: list[tuple[str, str]] = []

    def canonicalize(source: Path, target: Path, **kwargs: object) -> MediaProbe:
        assert kwargs == {"timeout_seconds": 15.0, "max_bytes": 8_000_000}
        calls.append((source, target))
        target.write_bytes(b"\xff\xfbcanonical")
        return _probe(target)

    monkeypatch.setattr(audio_module, "probe_mp3", _probe)
    monkeypatch.setattr(audio_module, "canonicalize_mp3", canonicalize, raising=False)
    result = TtsFallbackChain(
        (
            FakeAdapter("dify", ["ok"], adapter_calls),
            FakeAdapter("edge_tts", ["ok"], adapter_calls),
            FakeAdapter("sapi", ["ok"], adapter_calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert result.available is True
    assert len(calls) == 1
    assert calls[0][0].name == "candidate-0-normal.mp3"
    assert calls[0][1].name == "recap.mp3"
    assert calls[0][1].parent.parent.name == "debugmate-private-candidates"


def test_canonicalization_failure_falls_through_to_the_next_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    canonicalization_calls = 0

    def canonicalize(source: Path, target: Path, **_kwargs: object) -> MediaProbe:
        nonlocal canonicalization_calls
        canonicalization_calls += 1
        if canonicalization_calls == 1:
            raise MediaProbeError("canonicalize_failed")
        target.write_bytes(source.read_bytes())
        return _probe(target)

    monkeypatch.setattr(audio_module, "probe_mp3", _probe)
    monkeypatch.setattr(audio_module, "canonicalize_mp3", canonicalize)
    result = TtsFallbackChain(
        (
            FakeAdapter("dify", ["ok"], calls),
            FakeAdapter("edge_tts", ["ok"], calls),
            FakeAdapter("sapi", ["ok"], calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert calls == [("dify", "normal"), ("edge_tts", "normal")]
    assert result.available is True
    assert result.backend == "edge_tts"
    assert result.attempts[0].safe_error_code == "audio_invalid"


def test_directory_candidate_is_a_value_free_invalid_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []

    class DirectoryAdapter(FakeAdapter):
        def synthesize(self, text, target, request_identity, rate_profile):
            self._calls.append((self.backend, rate_profile.value))
            target.mkdir()
            return AudioCandidate(
                backend=self.backend,
                rate_profile=rate_profile,
                path=target,
                request_identity=request_identity,
            )

    monkeypatch.setattr(audio_module, "probe_mp3", _probe)
    result = TtsFallbackChain(
        (
            DirectoryAdapter("dify", [], calls),
            FakeAdapter("edge_tts", ["timeout"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert result.available is False
    assert result.attempts[0].safe_error_code == "tts_candidate_invalid"
    assert str(tmp_path) not in result.model_dump_json()


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
    result = chain.synthesize(_recap(), _identity(), _candidate_root(tmp_path))
    assert calls == [("dify", "normal"), ("edge_tts", "normal"), ("sapi", "normal")]
    assert result.available is False
    assert result.failure.code == "tts_failed"
    assert not list((tmp_path / "debugmate-private-candidates").rglob("*.mp3"))
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


def test_dify_target_write_failure_is_value_free(tmp_path: Path) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, headers={"content-type": "audio/mpeg"}, content=b"\xff\xfbaudio"
            )
        )
    )
    adapter = DifyTtsAdapter(
        DebugMateSettings.from_env({"DIFY_API_KEY": "fictional-test-key"}), client=client
    )
    blocked_target = tmp_path / "private-directory"
    blocked_target.mkdir()

    with pytest.raises(RuntimeError, match="^tts_backend_failed$") as caught:
        adapter.synthesize(_recap(), blocked_target, _identity(), RateProfile.NORMAL)

    assert str(blocked_target) not in str(caught.value)


def test_sapi_target_setup_failure_is_value_free(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "private-file"
    blocked_parent.write_bytes(b"x")

    with pytest.raises(RuntimeError, match="^tts_backend_failed$") as caught:
        SapiTtsAdapter(project_root=Path.cwd()).synthesize(
            _recap(), blocked_parent / "candidate.mp3", _identity(), RateProfile.NORMAL
        )

    assert str(blocked_parent) not in str(caught.value)


def test_edge_cleanup_failure_does_not_leak_a_directory_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingCommunicate:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def save(self, _target: str) -> None:
            raise OSError("private edge failure")

    monkeypatch.setattr("debugmate.results.tts.edge.edge_tts.Communicate", FailingCommunicate)
    blocked_target = tmp_path / "private-directory"
    blocked_target.mkdir()

    with pytest.raises(RuntimeError, match="^tts_backend_failed$") as caught:
        EdgeTtsAdapter().synthesize(_recap(), blocked_target, _identity(), RateProfile.NORMAL)

    assert str(blocked_target) not in str(caught.value)


def test_edge_timeout_is_bounded_cancelled_and_falls_through_to_sapi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A nonresponsive edge request is value-free, bounded, and never blocks SAPI."""

    class NeverCompletes:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def save(self, _target: str) -> None:
            await edge_module.asyncio.Event().wait()

    wait_for_calls: list[float] = []
    real_wait_for = edge_module.asyncio.wait_for

    async def record_wait_for(awaitable, timeout):
        wait_for_calls.append(timeout)
        return await real_wait_for(awaitable, timeout)

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(edge_module.edge_tts, "Communicate", NeverCompletes)
    monkeypatch.setattr(edge_module.asyncio, "wait_for", record_wait_for)
    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    monkeypatch.setattr("debugmate.results.audio.canonicalize_mp3", _canonicalize)
    started = time.monotonic()
    result = TtsFallbackChain(
        (
            FakeAdapter("dify", ["transport"], calls),
            EdgeTtsAdapter(timeout_seconds=0.05),
            FakeAdapter("sapi", ["ok"], calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert wait_for_calls == [0.05]
    assert calls == [("dify", "normal"), ("sapi", "normal")]
    assert result.available is True
    assert result.backend == "sapi"
    assert result.attempts[1].backend == "edge_tts"
    assert result.attempts[1].safe_error_code == "tts_backend_failed"
    assert not list((tmp_path / "debugmate-private-candidates").rglob("candidate-1-normal.mp3"))


def test_sapi_uses_bounded_file_boundary_and_never_places_recap_in_argv(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[list[str]] = []

    def bounded_run(argv: list[str], **kwargs: object) -> tuple[int, bytes]:
        assert kwargs["timeout_seconds"] == 90.0
        assert kwargs["max_output_bytes"] == 64 * 1024
        calls.append(list(argv))
        if "-OutputWaveFile" in argv:
            Path(argv[argv.index("-OutputWaveFile") + 1]).write_bytes(b"RIFF")
        else:
            Path(argv[-1]).write_bytes(b"\xff\xfbfixture")
        return 0, b""

    class LegacySubprocess:
        def run(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("legacy subprocess.run must not be used")

    monkeypatch.setattr(
        "debugmate.results.tts.sapi.subprocess", LegacySubprocess(), raising=False
    )
    monkeypatch.setattr(
        "debugmate.results.tts.sapi._run_bounded_process", bounded_run, raising=False
    )
    target = tmp_path / "candidate.mp3"
    SapiTtsAdapter(project_root=Path.cwd()).synthesize(
        _recap(), target, _identity(), RateProfile.NORMAL
    )
    flattened = [item for argv in calls for item in argv]
    assert "-Command" not in flattened
    assert _recap().text not in flattened
    assert len(calls) == 2
    assert calls[0][3] == "-File"
    assert target.exists()
    assert not list(tmp_path.rglob("*.wav"))


def test_sapi_rejects_untrusted_executable_or_script_roots_without_echoing_values(
    tmp_path: Path,
) -> None:
    for overrides in (
        {"project_root": tmp_path},
        {"powershell": "cmd.exe"},
        {"ffmpeg": "cmd.exe"},
    ):
        with pytest.raises(ValueError, match="^tts_sapi_config_invalid$") as caught:
            SapiTtsAdapter(**overrides)
        assert str(tmp_path) not in str(caught.value)


def test_sapi_rejects_a_non_regular_resolved_ffmpeg_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ForgedTools:
        ffmpeg = Path(r"C:\Windows\System32\cmd.exe")

    monkeypatch.setattr(
        "debugmate.results.tts.sapi.trusted_media_tools", lambda: ForgedTools()
    )

    with pytest.raises(ValueError, match="^tts_sapi_config_invalid$"):
        SapiTtsAdapter(project_root=Path.cwd())


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


def test_chain_rejects_a_constructed_seven_unit_recap_before_any_adapter_call(
    tmp_path: Path,
) -> None:
    recap = _recap()
    forged = SafeRecapText.model_construct(
        identity=recap.identity,
        text=recap.text,
        sha256=recap.sha256,
        units=(*recap.units, "forged seventh unit"),
        word_budget_version=recap.word_budget_version,
    )
    calls: list[tuple[str, str]] = []
    chain = TtsFallbackChain(
        (
            FakeAdapter("dify", ["ok"], calls),
            FakeAdapter("edge_tts", ["ok"], calls),
            FakeAdapter("sapi", ["ok"], calls),
        )
    )

    with pytest.raises(ValueError, match="^tts_input_invalid$"):
        chain.synthesize(forged, _identity(), _candidate_root(tmp_path))

    assert calls == []


def _make_junction(link: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        check=False,
        shell=False,
        timeout=10,
    )
    if completed.returncode != 0:  # pragma: no cover - Windows target gate
        pytest.fail("could not create required junction attack fixture")


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows junction attack")
def test_chain_rejects_nested_junction_root_before_adapter_or_outside_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = tmp_path / "safe"
    outside = tmp_path / "outside"
    safe.mkdir()
    outside.mkdir()
    junction = safe / "nested"
    _make_junction(junction, outside)
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr("debugmate.results.audio.probe_mp3", _probe)
    monkeypatch.setattr("debugmate.results.audio.canonicalize_mp3", _canonicalize)
    chain = TtsFallbackChain(
        (
            FakeAdapter("dify", ["ok"], calls),
            FakeAdapter("edge_tts", ["ok"], calls),
            FakeAdapter("sapi", ["ok"], calls),
        )
    )

    with pytest.raises(ValueError, match="^tts_target_invalid$"):
        chain.synthesize(_recap(), _identity(), TrustedCandidateRoot.for_testing(junction))

    assert calls == []
    assert not list(outside.iterdir())


def test_sapi_ignores_a_forged_systemroot_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    forged_root = tmp_path / "forged-system-root"
    forged_root.mkdir()
    monkeypatch.setenv("SYSTEMROOT", str(forged_root))

    adapter = SapiTtsAdapter(project_root=Path.cwd())

    assert Path(adapter._powershell).is_absolute()
    assert str(forged_root) not in adapter._powershell
