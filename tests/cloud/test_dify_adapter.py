from __future__ import annotations

import hashlib
import json

import httpx
import pytest
from pydantic import SecretStr
from tests.cloud.test_run_envelope import _envelope_payload

import debugmate.adapters.dify as dify
from debugmate.adapters.dify import (
    DifyAuthError,
    DifyBackend,
    DifyContractError,
    DifyNotConfigured,
    DifyQuotaError,
    DifyTransportError,
)
from debugmate.settings import DebugMateSettings

MAX_WORKFLOW_RESPONSE_BYTES = 512 * 1024


def _settings() -> DebugMateSettings:
    return DebugMateSettings(dify_api_key=SecretStr("fixture-app-key"))


def _workflow_response() -> dict[str, object]:
    return {
        "workflow_run_id": "remote-run-id",
        "data": {"outputs": {"diagnosis": {"case_id": "case_candidate"}}},
    }


def test_object_run_envelope_uses_strict_json_wire_validation() -> None:
    payload = _envelope_payload()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "workflow_run_id": "remote-run-id",
                "data": {"outputs": {"run_envelope": payload}},
            },
            request=request,
        )

    backend = DifyBackend(
        _settings(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        test_base_url="https://dify.test/v1",
    )
    result = backend.run_workflow({}, user="debugmate-stable")
    assert result.run_envelope is not None
    assert result.run_envelope.diagnosis.schema_version == "1.1.0"


def test_constructor_does_not_dispatch_and_incomplete_config_fails_locally() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise AssertionError("constructor must not make a request")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    DifyBackend(_settings(), client=client, test_base_url="https://dify.test/v1")
    assert calls == 0

    backend = DifyBackend(
        DebugMateSettings(), client=client, test_base_url="https://dify.test/v1"
    )
    with pytest.raises(DifyNotConfigured) as caught:
        backend.run_workflow({}, user="debugmate-stable")
    assert caught.value.code == "configuration"
    assert calls == 0


def test_adapter_exposes_typed_upload_and_ambiguous_transport_errors() -> None:
    assert issubclass(dify.DifyUploadError, dify.DifyError)
    assert issubclass(dify.DifyAmbiguousTransportError, dify.DifyTransportError)


def test_default_client_has_exact_timeouts_and_never_follows_redirects() -> None:
    backend = DifyBackend(_settings())
    try:
        assert backend._client.follow_redirects is False
        assert backend._client.timeout.connect == 10.0
        assert backend._client.timeout.write == 30.0
        assert backend._client.timeout.read == 95.0
        assert backend._client.timeout.pool == 5.0
    finally:
        backend.close()


def test_explicit_test_origin_is_injectable_but_redirect_is_rejected() -> None:
    observed: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://example.invalid"}, request=request)

    backend = DifyBackend(
        _settings(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        test_base_url="http://127.0.0.1:9999/test-v1",
    )
    with pytest.raises(DifyContractError) as caught:
        backend.run_workflow({}, user="debugmate-stable")
    assert observed == ["http://127.0.0.1:9999/test-v1/workflows/run"]
    assert caught.value.code == "workflow_envelope"


@pytest.mark.parametrize("use_content_length", [True, False])
def test_workflow_response_is_bounded_before_json_decode(use_content_length: bool) -> None:
    oversized = b"{" + b"x" * MAX_WORKFLOW_RESPONSE_BYTES + b"}"

    def handler(request: httpx.Request) -> httpx.Response:
        headers = {"content-length": str(len(oversized))} if use_content_length else {}
        return httpx.Response(200, headers=headers, content=oversized, request=request)

    backend = DifyBackend(
        _settings(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        test_base_url="https://dify.test/v1",
    )
    with pytest.raises(DifyContractError) as caught:
        backend.run_workflow({}, user="debugmate-stable")
    assert caught.value.code == "workflow_envelope"


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ConnectTimeout])
def test_pre_dispatch_connect_failure_retries_exactly_once(
    error_type: type[httpx.RequestError],
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise error_type("sentinel-provider-detail", request=request)
        return httpx.Response(200, json=_workflow_response(), request=request)

    backend = DifyBackend(
        _settings(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        test_base_url="https://dify.test/v1",
    )
    result = backend.run_workflow({}, user="debugmate-stable")
    assert calls == 2
    assert result.run_id != "remote-run-id"


@pytest.mark.parametrize(
    "error_type",
    [
        httpx.ReadTimeout,
        httpx.ReadError,
        httpx.WriteTimeout,
        httpx.WriteError,
        httpx.RemoteProtocolError,
    ],
)
def test_ambiguous_workflow_failure_is_never_replayed(
    error_type: type[httpx.RequestError],
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise error_type("sentinel-provider-detail", request=request)

    backend = DifyBackend(
        _settings(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        test_base_url="https://dify.test/v1",
    )
    with pytest.raises(getattr(dify, "DifyAmbiguousTransportError", DifyTransportError)) as caught:
        backend.run_workflow({}, user="debugmate-stable")
    assert calls == 1
    assert caught.value.code == "ambiguous_timeout"
    assert "sentinel" not in str(caught.value)


@pytest.mark.parametrize(
    ("status", "error_type", "code"),
    [
        (400, DifyContractError, "workflow_envelope"),
        (401, DifyAuthError, "authentication"),
        (403, DifyAuthError, "authentication"),
        (413, DifyContractError, "upload"),
        (415, DifyContractError, "upload"),
        (429, DifyQuotaError, "quota"),
        (500, DifyTransportError, "remote_status"),
    ],
)
def test_status_errors_are_typed_and_contain_no_provider_material(
    status: int, error_type: type[Exception], code: str
) -> None:
    secret = "fixture-app-key"
    provider_body = "remote-id-and-provider-body"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            headers={"x-provider-secret": provider_body},
            content=json.dumps({"message": provider_body}).encode(),
            request=request,
        )

    backend = DifyBackend(
        _settings(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        test_base_url="https://dify.test/v1",
    )
    expected_type = dify.DifyUploadError if status in {413, 415} else error_type
    with pytest.raises(expected_type) as caught:
        backend.run_workflow({}, user="debugmate-stable")
    rendered = str(caught.value)
    assert caught.value.code == code
    assert secret not in rendered
    assert provider_body not in rendered
    assert "dify.test" not in rendered


@pytest.mark.parametrize(
    ("filename", "mime_type", "content"),
    [
        ("redacted.png", "image/png", b"approved-png-snapshot"),
        ("redacted.jpg", "image/jpeg", b"approved-jpeg-snapshot"),
    ],
)
def test_upload_sends_exact_snapshot_and_validates_returned_contract(
    filename: str, mime_type: str, content: bytes
) -> None:
    observed: list[tuple[bytes, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        observed.append((body, request.headers["content-type"]))
        assert content in body
        assert filename.encode() in body
        assert mime_type.encode() in body
        assert b'stable-dify-user' in body
        return httpx.Response(
            201,
            json={
                "id": "transient-upload-id",
                "name": filename,
                "size": len(content),
                "mime_type": mime_type,
            },
            request=request,
        )

    backend = DifyBackend(
        _settings(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        test_base_url="https://dify.test/v1",
    )
    result = backend.upload_bytes(
        content,
        filename=filename,
        mime_type=mime_type,  # type: ignore[arg-type]
        user="stable-dify-user",
    )

    assert len(observed) == 1
    assert result.file_id == "transient-upload-id"
    assert result.file_id_fingerprint == hashlib.sha256(
        b"transient-upload-id"
    ).hexdigest()
    assert result.filename == filename
    assert result.mime_type == mime_type
    assert result.size == len(content)


@pytest.mark.parametrize("changed_field", ["name", "size", "mime_type"])
def test_upload_rejects_mismatched_provider_metadata(changed_field: str) -> None:
    response = {
        "id": "transient-upload-id",
        "name": "redacted.png",
        "size": 8,
        "mime_type": "image/png",
    }
    response[changed_field] = {
        "name": "different.png",
        "size": 9,
        "mime_type": "image/jpeg",
    }[changed_field]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=response, request=request)

    backend = DifyBackend(
        _settings(),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        test_base_url="https://dify.test/v1",
    )
    with pytest.raises(dify.DifyUploadError):
        backend.upload_bytes(
            b"snapshot",
            filename="redacted.png",
            mime_type="image/png",
            user="stable-dify-user",
        )
