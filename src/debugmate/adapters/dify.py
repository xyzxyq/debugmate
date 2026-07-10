"""Narrow, secret-safe HTTP adapter for the Dify application API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from debugmate.adapters.base import (
    AudioSynthesisResult,
    CapabilityProbeResult,
    FileUploadResult,
    WorkflowRunResult,
)
from debugmate.contracts import CapabilityStatus, DiagnosisRecord
from debugmate.settings import DebugMateSettings


class DifyError(RuntimeError):
    """Base class whose messages never include response bodies or headers."""


class DifyNotConfigured(DifyError):
    pass


class DifyAuthError(DifyError):
    pass


class DifyQuotaError(DifyError):
    pass


class DifyTransportError(DifyError):
    pass


class DifyContractError(DifyError):
    pass


class DifyBackend:
    def __init__(self, settings: DebugMateSettings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=httpx.Timeout(30.0))

    def _headers(self) -> dict[str, str]:
        if self._settings.dify_api_key is None:
            raise DifyNotConfigured("Dify API key is not configured")
        return {
            "Authorization": f"Bearer {self._settings.dify_api_key.get_secret_value()}",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self._settings.dify_base_url.rstrip('/')}/{path.lstrip('/')}"
        for attempt in range(2):
            try:
                response = self._client.request(
                    method,
                    url,
                    headers=self._headers(),
                    **kwargs,
                )
                break
            except (httpx.ConnectError, httpx.TimeoutException):
                if attempt == 1:
                    raise DifyTransportError("Dify transport failed after one retry") from None
        else:  # pragma: no cover - loop always breaks or raises
            raise DifyTransportError("Dify transport failed")

        if response.status_code in {401, 403}:
            raise DifyAuthError("Dify authentication was rejected")
        if response.status_code == 429:
            raise DifyQuotaError("Dify quota or rate limit was reached")
        if response.status_code in {400, 404}:
            raise DifyContractError(f"Dify rejected the request with status {response.status_code}")
        if response.status_code >= 500:
            raise DifyTransportError(f"Dify service returned status {response.status_code}")
        if response.status_code >= 300:
            raise DifyContractError(f"Unexpected Dify status {response.status_code}")
        return response

    def upload_file(self, path: Path, user: str) -> FileUploadResult:
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open("rb") as handle:
            response = self._request(
                "POST",
                "/files/upload",
                data={"user": user},
                files={"file": (path.name, handle, "application/octet-stream")},
            )
        try:
            payload = response.json()
            file_id = str(payload["id"])
            filename = str(payload.get("name") or path.name)
        except (ValueError, KeyError, TypeError):
            raise DifyContractError("Dify upload response did not match the contract") from None
        return FileUploadResult(file_id=file_id, filename=filename, backend="dify")

    def run_workflow(self, inputs: dict[str, object], user: str) -> WorkflowRunResult:
        response = self._request(
            "POST",
            "/workflows/run",
            json={"inputs": inputs, "response_mode": "blocking", "user": user},
        )
        try:
            payload = response.json()
            data = payload.get("data", {})
            outputs = data.get("outputs", {})
            raw_diagnosis = outputs["diagnosis"]
            if isinstance(raw_diagnosis, str):
                diagnosis = DiagnosisRecord.model_validate_json(raw_diagnosis)
            else:
                diagnosis = DiagnosisRecord.model_validate_json(
                    json.dumps(raw_diagnosis, ensure_ascii=False)
                )
            run_id = str(
                payload.get("workflow_run_id")
                or data.get("workflow_run_id")
                or payload.get("task_id")
                or data["id"]
            )
        except Exception:
            raise DifyContractError(
                "Dify workflow response did not match DiagnosisRecord"
            ) from None
        return WorkflowRunResult(run_id=run_id, diagnosis=diagnosis, backend="dify")

    def synthesize_audio(self, text: str, user: str) -> AudioSynthesisResult:
        response = self._request(
            "POST",
            "/text-to-audio",
            json={"text": text, "user": user},
        )
        audio = response.content
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
