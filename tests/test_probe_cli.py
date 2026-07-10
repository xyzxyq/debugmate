from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from debugmate.adapters.dify import (
    DifyAuthError,
    DifyBackend,
    DifyContractError,
    DifyQuotaError,
)
from debugmate.contracts import new_case_id
from debugmate.settings import DebugMateSettings

SENTINEL = "SECRET_SENTINEL_DO_NOT_LOG"
FIXTURE_DIAGNOSIS = Path("fixtures/cases/module_not_found/diagnosis.json")


def settings() -> DebugMateSettings:
    return DebugMateSettings.from_env(
        {"DIFY_API_KEY": SENTINEL, "DIFY_BASE_URL": "https://api.dify.test/v1"}
    )


@pytest.mark.parametrize(
    ("status", "error_type"),
    [(401, DifyAuthError), (403, DifyAuthError), (429, DifyQuotaError)],
)
def test_dify_auth_and_quota_errors_are_not_retried_or_leaked(
    status: int,
    error_type: type[Exception],
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, json={"message": SENTINEL}, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = DifyBackend(settings(), client=client)

    with pytest.raises(error_type) as caught:
        backend.run_workflow({"case_id": new_case_id()}, user="debugmate-test")

    rendered = str(caught.value) + capsys.readouterr().out + caplog.text
    assert calls == 1
    assert SENTINEL not in rendered


def test_dify_connect_error_retries_once() -> None:
    calls = 0
    diagnosis = json.loads(FIXTURE_DIAGNOSIS.read_text(encoding="utf-8"))
    diagnosis["case_id"] = new_case_id()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("temporary", request=request)
        return httpx.Response(
            200,
            json={"workflow_run_id": "run-test", "data": {"outputs": {"diagnosis": diagnosis}}},
            request=request,
        )

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = backend.run_workflow({"case_id": diagnosis["case_id"]}, user="debugmate-test")

    assert calls == 2
    assert result.run_id == "run-test"
    assert result.diagnosis.case_id == diagnosis["case_id"]


def test_dify_workflow_rejects_invalid_contract_without_leaking_secret() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"workflow_run_id": "run-bad", "data": {"outputs": {"diagnosis": {}}}},
            request=request,
        )

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(DifyContractError) as caught:
        backend.run_workflow({"case_id": new_case_id()}, user="debugmate-test")

    assert SENTINEL not in str(caught.value)


@pytest.mark.parametrize("audio", [b"ID3\x04\x00\x00fixture", b"\xff\xfb\x90\x64fixture"])
def test_dify_tts_accepts_mp3_headers(audio: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=audio, request=request)

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = backend.synthesize_audio("fictional recap", user="debugmate-test")

    assert result.audio == audio
    assert result.mime_type == "audio/mpeg"


def test_dify_tts_rejects_non_mp3_bytes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-mp3", request=request)

    backend = DifyBackend(settings(), client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(DifyContractError):
        backend.synthesize_audio("fictional recap", user="debugmate-test")
