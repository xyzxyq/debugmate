from __future__ import annotations

import inspect
import os
import subprocess
import sys
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
from debugmate.results.tts import edge as edge_module
from debugmate.results.tts.base import AudioPayload, RateProfile, TtsRequestIdentity
from debugmate.results.tts.dify import DifyTtsAdapter
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


def _identity() -> TtsRequestIdentity:
    recap = _recap()
    return TtsRequestIdentity(
        case_id=recap.identity.case_id,
        source_run_id=recap.identity.source_run_id,
        diagnosis_sha256=recap.identity.diagnosis_sha256,
        generation_version=recap.identity.generation_version,
        recap_sha256=recap.sha256,
    )


def _payload(
    backend: str, request: TtsRequestIdentity, rate: RateProfile, *, value: bytes | None = None
) -> AudioPayload:
    return AudioPayload(
        backend=backend,
        rate_profile=rate,
        request_identity=request,
        audio_bytes=value or b"\xff\xfb" + b"x" * 128,
        voice="Microsoft Huihui Desktop" if backend == "sapi" else None,
    )


class FakeAdapter:
    def __init__(self, backend: str, outcomes: list[str], calls: list[tuple[str, str]]) -> None:
        self.backend = backend
        self._outcomes = iter(outcomes)
        self._calls = calls

    def synthesize(
        self, _text: SafeRecapText, request: TtsRequestIdentity, rate: RateProfile
    ) -> AudioPayload:
        self._calls.append((self.backend, rate.value))
        outcome = next(self._outcomes)
        if outcome != "ok":
            raise RuntimeError(outcome)
        return _payload(self.backend, request, rate)


def _probe(path: Path, **_kwargs: object) -> MediaProbe:
    return MediaProbe(
        duration_ms=45_000,
        codec="mp3",
        channels=1,
        bytes=path.stat().st_size,
        sha256="b" * 64,
    )


def _canonicalize(payload: bytes, **_kwargs: object) -> bytes:
    return payload


def _candidate_root(tmp_path: Path) -> TrustedCandidateRoot:
    return TrustedCandidateRoot.for_testing(tmp_path / "debugmate-private-candidates")


def _fake_media(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_module, "probe_mp3", _probe)
    monkeypatch.setattr(audio_module, "canonicalize_mp3", _canonicalize)


def test_chain_requires_a_trusted_candidate_root_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_media(monkeypatch)
    calls: list[tuple[str, str]] = []
    chain = TtsFallbackChain(
        (
            FakeAdapter("dify", ["ok"], calls),
            FakeAdapter("edge_tts", ["ok"], calls),
            FakeAdapter("sapi", ["ok"], calls),
        )
    )
    with pytest.raises(TypeError):
        TrustedCandidateRoot(tmp_path)
    with pytest.raises(TypeError):
        chain.synthesize(_recap(), _identity(), tmp_path / "caller-output")

    result = chain.synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert result.available is True
    assert not (tmp_path / "caller-output" / "recap.mp3").exists()


def test_fallback_order_and_retry_are_fixed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []
    probe_results = iter(
        (
            MediaProbeError("duration_out_of_range"),
            MediaProbe(duration_ms=45_000, codec="mp3", channels=1, bytes=1, sha256="b" * 64),
            MediaProbe(duration_ms=45_000, codec="mp3", channels=1, bytes=1, sha256="b" * 64),
        )
    )

    def varying_probe(_path: Path, **_kwargs: object) -> MediaProbe:
        result = next(probe_results)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(audio_module, "probe_mp3", varying_probe)
    monkeypatch.setattr(audio_module, "canonicalize_mp3", _canonicalize)
    result = TtsFallbackChain(
        (
            FakeAdapter("dify", ["ok", "ok"], calls),
            FakeAdapter("edge_tts", ["transport"], calls),
            FakeAdapter("sapi", ["ok"], calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert calls == [("dify", "normal"), ("dify", "faster")]
    assert result.available is True
    assert result.backend == "dify"
    assert [attempt.safe_error_code for attempt in result.attempts[:-1]] == [
        "audio_duration_invalid"
    ]


def test_non_duration_failure_falls_through_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_media(monkeypatch)
    calls: list[tuple[str, str]] = []
    result = TtsFallbackChain(
        (
            FakeAdapter("dify", ["transport"], calls),
            FakeAdapter("edge_tts", ["bad_content"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert calls == [("dify", "normal"), ("edge_tts", "normal"), ("sapi", "normal")]
    assert result.available is False
    assert result.failure.code == "tts_failed"
    assert str(tmp_path) not in result.model_dump_json()


def test_payload_metadata_forgery_is_rejected_without_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_media(monkeypatch)
    calls: list[tuple[str, str]] = []

    class ForgedPayload(FakeAdapter):
        def synthesize(
            self, _text: SafeRecapText, request: TtsRequestIdentity, rate: RateProfile
        ) -> AudioPayload:
            self._calls.append((self.backend, rate.value))
            return _payload(
                self.backend,
                request.model_copy(update={"recap_sha256": "9" * 64}),
                rate,
            )

    result = TtsFallbackChain(
        (
            ForgedPayload("dify", [], calls),
            FakeAdapter("edge_tts", ["transport"], calls),
            FakeAdapter("sapi", ["process"], calls),
        )
    ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))

    assert result.available is False
    assert result.attempts[0].safe_error_code == "tts_candidate_invalid"
    assert not list((tmp_path / "debugmate-private-candidates").rglob("recap.mp3"))


def test_dify_mock_transport_hardlink_swap_cannot_overwrite_outside(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real Dify adapter only returns bytes; CREATE_NEW rejects a planted link."""

    _fake_media(monkeypatch)
    root = tmp_path / "debugmate-private-candidates"
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"outside-original")

    def handler(_request: httpx.Request) -> httpx.Response:
        run = next(path for path in root.iterdir() if path.name.startswith("tts-"))
        os.link(outside, run / "recap.mp3")
        return httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"\xff\xfbok")

    dify = DifyTtsAdapter(
        DebugMateSettings.from_env({"DIFY_API_KEY": "fictional-test-key"}),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    result_or_error = None
    try:
        result_or_error = TtsFallbackChain(
            (
                dify,
                FakeAdapter("edge_tts", ["transport"], []),
                FakeAdapter("sapi", ["process"], []),
            )
        ).synthesize(_recap(), _identity(), _candidate_root(tmp_path))
    except ValueError as error:
        assert str(error) == "tts_target_invalid"

    assert result_or_error is None
    assert outside.read_bytes() == b"outside-original"


@pytest.mark.skipif(os.name != "nt", reason="Windows junction attack")
def test_nested_junction_root_rejects_before_adapter_or_sapi_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_media(monkeypatch)
    safe = tmp_path / "safe"
    outside = tmp_path / "outside"
    safe.mkdir()
    outside.mkdir()
    junction = safe / "nested"
    _make_junction(junction, outside)
    calls: list[tuple[str, str]] = []
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


def test_dify_adapter_returns_bounded_payload_without_a_caller_output_path() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, headers={"content-type": "audio/mpeg"}, content=b"\xff\xfbbounded-audio"
            )
        )
    )
    adapter = DifyTtsAdapter(
        DebugMateSettings.from_env({"DIFY_API_KEY": "fictional-test-key"}), client=client
    )

    payload = adapter.synthesize(_recap(), _identity(), RateProfile.NORMAL)

    assert payload.backend == "dify"
    assert payload.audio_bytes == b"\xff\xfbbounded-audio"
    assert not hasattr(payload, "path")


def test_all_production_adapters_have_no_caller_writable_path_parameter() -> None:
    for adapter_type in (DifyTtsAdapter, EdgeTtsAdapter, SapiTtsAdapter):
        assert tuple(inspect.signature(adapter_type.synthesize).parameters) == (
            "self",
            "text",
            "request_identity",
            "rate_profile",
        )


def test_dify_rejects_wrong_content_type_and_oversize_without_persisting() -> None:
    for response in (
        httpx.Response(200, headers={"content-type": "text/plain"}, content=b"secret"),
        httpx.Response(200, headers={"content-type": "audio/mpeg"}, content=b"x" * 65),
    ):
        adapter = DifyTtsAdapter(
            DebugMateSettings.from_env({"DIFY_API_KEY": "fictional-test-key"}),
            client=httpx.Client(
                transport=httpx.MockTransport(lambda _request, current=response: current)
            ),
            max_bytes=64,
        )
        with pytest.raises(RuntimeError, match="^tts_backend_failed$"):
            adapter.synthesize(_recap(), _identity(), RateProfile.NORMAL)


def test_edge_cancellation_swallower_is_force_killed_before_sapi_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_media(monkeypatch)
    calls: list[tuple[str, str]] = []

    def never_finishing_worker(_rate: str) -> list[str]:
        return [sys.executable, "-c", "import time; time.sleep(3600)"]

    monkeypatch.setattr(edge_module, "_edge_worker_command", never_finishing_worker)
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
    assert calls == [("dify", "normal"), ("sapi", "normal")]
    assert result.available is True
    assert result.backend == "sapi"
    assert result.attempts[1].safe_error_code == "tts_backend_failed"


def test_sapi_has_no_input_or_output_file_argv_and_ignores_nested_junction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], bytes]] = []
    outside = tmp_path / "outside"
    outside.mkdir()
    nested = tmp_path / "nested"
    _make_junction(nested, outside)

    def bounded_run(argv: list[str], **kwargs: object) -> tuple[int, bytes]:
        input_bytes = kwargs["input_bytes"]
        assert isinstance(input_bytes, bytes)
        calls.append((list(argv), input_bytes))
        if argv[0].casefold().endswith("powershell.exe"):
            return 0, b"RIFF" + b"x" * 64
        return 0, b"\xff\xfb" + b"x" * 64

    monkeypatch.setattr("debugmate.results.tts.sapi._run_bounded_process", bounded_run)
    payload = SapiTtsAdapter(project_root=Path.cwd()).synthesize(
        _recap(), _identity(), RateProfile.NORMAL
    )

    flattened = [value for argv, _ in calls for value in argv]
    assert "-Command" not in flattened
    assert "-InputTextFile" not in flattened
    assert "-OutputWaveFile" not in flattened
    assert _recap().text not in flattened
    assert payload.audio_bytes.startswith(b"\xff\xfb")
    assert not list(outside.iterdir())


def test_all_adapters_reject_constructed_secret_and_mismatched_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "token=debugmate-fictional-secret-0123456789"
    unsafe = _recap().model_copy(
        update={"text": secret, "sha256": sha256_bytes(secret.encode("utf-8"))}
    )
    wrong_identity = _identity().model_copy(update={"recap_sha256": "f" * 64})
    adapters = (
        DifyTtsAdapter(
            DebugMateSettings.from_env({"DIFY_API_KEY": "fictional-test-key"}),
            client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))),
        ),
        EdgeTtsAdapter(),
        SapiTtsAdapter(project_root=Path.cwd()),
    )
    for adapter in adapters:
        with pytest.raises(RuntimeError, match="^tts_backend_failed$") as caught:
            adapter.synthesize(unsafe, _identity(), RateProfile.NORMAL)
        assert secret not in str(caught.value)
        with pytest.raises(RuntimeError, match="^tts_backend_failed$"):
            adapter.synthesize(_recap(), wrong_identity, RateProfile.NORMAL)

    assert monkeypatch is not None


def test_chain_rejects_constructed_seven_unit_recap_before_any_adapter_call(tmp_path: Path) -> None:
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
