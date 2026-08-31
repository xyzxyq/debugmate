"""Bounded, secret-safe HTTP adapter for the Dify application API."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from typing import Any, Literal

import httpx
from pydantic import ValidationError

from debugmate.adapters.base import (
    AudioSynthesisResult,
    CandidateRunResult,
    CapabilityProbeResult,
    FileUploadResult,
)
from debugmate.cloud.contracts import DifyRunEnvelope, DifyUsage
from debugmate.contracts import CapabilityStatus
from debugmate.settings import DebugMateSettings

MAX_WORKFLOW_RESPONSE_BYTES = 512 * 1024
APPLICATION_TIMEOUT = httpx.Timeout(connect=10.0, write=30.0, read=95.0, pool=5.0)


class DifyError(RuntimeError):
    """Base error with a stable code and provider-independent safe message."""

    code = "configuration"

    def __init__(self, message: str = "Dify request failed safely") -> None:
        super().__init__(message)


class DifyNotConfigured(DifyError):
    code = "configuration"


class DifyAuthError(DifyError):
    code = "authentication"


class DifyQuotaError(DifyError):
    code = "quota"


class DifyTransportError(DifyError):
    code = "pre_dispatch_transport"


class DifyAmbiguousTransportError(DifyTransportError):
    code = "ambiguous_timeout"


class DifyContractError(DifyError):
    code = "workflow_envelope"


class DifyUploadError(DifyContractError):
    code = "upload"


def _fingerprint_remote_id(value: str, prefix: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:32]}"


def _bounded_bytes(response: httpx.Response, limit: int) -> bytes:
    length = response.headers.get("content-length")
    if length is not None:
        try:
            if int(length) > limit:
                raise DifyContractError("Dify response exceeded the safe size limit")
        except ValueError:
            raise DifyContractError("Dify response length was invalid") from None

    body = bytearray()
    for chunk in response.iter_bytes():
        if len(body) + len(chunk) > limit:
            raise DifyContractError("Dify response exceeded the safe size limit")
        body.extend(chunk)
    return bytes(body)


def _safe_usage(payload: object) -> DifyUsage:
    if not isinstance(payload, dict):
        return DifyUsage()
    allowlisted = {
        key: payload[key]
        for key in ("total_tokens", "total_steps", "elapsed_time", "total_price")
        if key in payload
        and isinstance(payload[key], int | float)
        and not isinstance(payload[key], bool)
    }
    try:
        return DifyUsage.model_validate(allowlisted, strict=True)
    except ValidationError:
        return DifyUsage()


class DifyBackend:
    def __init__(
        self,
        settings: DebugMateSettings,
        client: httpx.Client | None = None,
        *,
        test_base_url: str | None = None,
    ) -> None:
        if test_base_url is not None and client is None:
            raise ValueError("a test origin requires an injected HTTP client")
        self._settings = settings
        self._base_url = (test_base_url or settings.dify_base_url).rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=APPLICATION_TIMEOUT,
            follow_redirects=False,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _headers(self) -> dict[str, str]:
        if not self._settings.dify_application_configured:
            raise DifyNotConfigured("Dify application configuration is incomplete")
        assert self._settings.dify_api_key is not None
        return {"Authorization": f"Bearer {self._settings.dify_api_key.get_secret_value()}"}

    def _stream(
        self,
        method: str,
        path: str,
        *,
        endpoint: Literal["upload", "workflow", "audio"],
        **kwargs: Any,
    ) -> Iterator[httpx.Response]:
        url = f"{self._base_url}/{path.lstrip('/')}"
        for attempt in range(2):
            try:
                with self._client.stream(
                    method,
                    url,
                    headers=self._headers(),
                    follow_redirects=False,
                    **kwargs,
                ) as response:
                    yield response
                return
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if attempt == 1:
                    raise DifyTransportError("Dify connection failed before dispatch") from None
            except (
                httpx.ReadTimeout,
                httpx.ReadError,
                httpx.WriteTimeout,
                httpx.WriteError,
                httpx.RemoteProtocolError,
            ):
                if endpoint == "workflow":
                    raise DifyAmbiguousTransportError(
                        "Dify workflow outcome is uncertain after dispatch"
                    ) from None
                if endpoint == "upload":
                    raise DifyUploadError("Dify upload transport failed safely") from None
                raise DifyTransportError("Dify transport failed safely") from None

    @staticmethod
    def _check_status(response: httpx.Response, endpoint: str) -> None:
        status = response.status_code
        if status in {401, 403}:
            raise DifyAuthError("Dify authentication was rejected")
        if status == 429:
            raise DifyQuotaError("Dify quota or rate limit was reached")
        if status in {413, 415}:
            raise DifyUploadError("Dify rejected the upload contract")
        if 300 <= status < 400:
            raise DifyContractError("Dify redirects are not accepted")
        if status >= 500:
            error = DifyTransportError("Dify service returned a safe remote status")
            error.code = "remote_status"
            raise error
        if status >= 300:
            error_type = DifyUploadError if endpoint == "upload" else DifyContractError
            raise error_type("Dify rejected the request contract")

    def _json_request(
        self,
        method: str,
        path: str,
        *,
        endpoint: Literal["upload", "workflow"],
        **kwargs: Any,
    ) -> dict[str, object]:
        response: httpx.Response | None = None
        for response in self._stream(method, path, endpoint=endpoint, **kwargs):
            self._check_status(response, endpoint)
            body = _bounded_bytes(response, MAX_WORKFLOW_RESPONSE_BYTES)
        assert response is not None
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            error_type = DifyUploadError if endpoint == "upload" else DifyContractError
            raise error_type("Dify response was not valid bounded JSON") from None
        if not isinstance(payload, dict):
            error_type = DifyUploadError if endpoint == "upload" else DifyContractError
            raise error_type("Dify response did not match the object contract")
        return payload

    def upload_bytes(
        self,
        content: bytes,
        *,
        filename: str,
        mime_type: Literal["image/png", "image/jpeg"],
        user: str,
    ) -> FileUploadResult:
        payload = self._json_request(
            "POST",
            "/files/upload",
            endpoint="upload",
            data={"user": user},
            files={"file": (filename, content, mime_type)},
        )
        try:
            remote_id = payload["id"]
            remote_name = payload["name"]
            remote_size = payload["size"]
            remote_mime = payload["mime_type"]
            if (
                not isinstance(remote_id, str)
                or not remote_id.strip()
                or remote_name != filename
                or remote_size != len(content)
                or remote_mime != mime_type
            ):
                raise TypeError
        except (KeyError, TypeError):
            raise DifyUploadError("Dify upload response did not match the contract") from None
        return FileUploadResult(
            file_id=remote_id,
            filename=filename,
            backend="dify",
            file_id_fingerprint=hashlib.sha256(remote_id.encode("utf-8")).hexdigest(),
            mime_type=mime_type,
            size=len(content),
        )

    def run_workflow(self, inputs: dict[str, object], user: str) -> CandidateRunResult:
        payload = self._json_request(
            "POST",
            "/workflows/run",
            endpoint="workflow",
            json={"inputs": inputs, "response_mode": "blocking", "user": user},
        )
        try:
            data = payload["data"]
            if not isinstance(data, dict):
                raise TypeError
            outputs = data["outputs"]
            if not isinstance(outputs, dict):
                raise TypeError
            remote_id = (
                payload.get("workflow_run_id")
                or data.get("workflow_run_id")
                or payload.get("task_id")
                or data.get("id")
            )
            if not isinstance(remote_id, str) or not remote_id.strip():
                raise TypeError

            envelope: DifyRunEnvelope | None = None
            if "run_envelope" in outputs:
                raw_envelope = outputs["run_envelope"]
                if isinstance(raw_envelope, str):
                    envelope = DifyRunEnvelope.model_validate_json(raw_envelope, strict=True)
                else:
                    # Dify's object output is already JSON-shaped, but enum
                    # members arrive as strings. Re-parse through JSON so the
                    # strict contract validates the wire representation rather
                    # than requiring Python Enum instances from the provider.
                    envelope = DifyRunEnvelope.model_validate_json(
                        json.dumps(raw_envelope, ensure_ascii=False, separators=(",", ":")),
                        strict=True,
                    )
                candidate_payload: object = envelope.diagnosis.model_dump(mode="json")
            else:
                candidate_payload = outputs["diagnosis"]
            return CandidateRunResult(
                run_id=_fingerprint_remote_id(remote_id, "run"),
                backend="dify",
                candidate_payload=candidate_payload,
                run_envelope=envelope,
                usage=_safe_usage(data.get("usage")),
            )
        except (KeyError, TypeError, ValidationError, ValueError):
            raise DifyContractError(
                "Dify workflow response did not match the bounded envelope"
            ) from None

    def synthesize_audio(self, text: str, user: str) -> AudioSynthesisResult:
        response: httpx.Response | None = None
        for response in self._stream(
            "POST", "/text-to-audio", endpoint="audio", json={"text": text, "user": user}
        ):
            self._check_status(response, "audio")
            audio = _bounded_bytes(response, MAX_WORKFLOW_RESPONSE_BYTES)
        assert response is not None
        is_id3 = audio.startswith(b"ID3")
        is_frame = len(audio) >= 2 and audio[0] == 0xFF and audio[1] & 0xE0 == 0xE0
        if not (is_id3 or is_frame):
            raise DifyContractError("Dify TTS response is not an MP3 stream")
        return AudioSynthesisResult(audio=audio, mime_type="audio/mpeg", backend="dify")

    def capability_probe(self) -> CapabilityProbeResult:
        return CapabilityProbeResult(
            backend="dify",
            capabilities={
                f"C{index:02d}": CapabilityStatus.NOT_TESTED for index in range(1, 8)
            },
        )
