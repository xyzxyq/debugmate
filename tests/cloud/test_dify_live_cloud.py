from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import httpx
import pytest

from debugmate.adapters.dify import DifyBackend, DifyContractError
from debugmate.cloud.contracts import DifyRunEnvelope
from debugmate.knowledge.build import validate_knowledge_build
from debugmate.knowledge.sync import (
    DifyReadbackAttestation,
    inspect_dify_knowledge_error,
    synchronize_knowledge,
)
from debugmate.settings import DebugMateSettings

pytestmark = pytest.mark.cloud

ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = ROOT / "tests" / "fixtures" / "cloud" / "phase8-live-case.json"
READBACK_PATH = ROOT / "evidence" / "dify-live" / "phase8" / "knowledge-readback.json"
SMOKE_PATH = ROOT / ".debugmate-runtime" / "phase8-cloud-smoke" / "live-smoke.json"
ENVELOPE_PATH = SMOKE_PATH.parent / "run-envelope.json"
KNOWLEDGE_REQUEST_INTERVAL_SECONDS = 7.0
KNOWLEDGE_ROLLING_WINDOW_SECONDS = 61.0
SYNC_FAILURE_PATH = SMOKE_PATH.parent / "knowledge-sync-failure.json"
WORKFLOW_CONTRACT_RETRIES = 3


def _safe_operation(method: str, target: object) -> str:
    path = str(target)
    if method == "POST" and path.endswith("/document/create-by-text"):
        return "document_create_text"
    if method == "POST" and path.endswith("/documents/metadata"):
        return "document_metadata_batch"
    if method == "POST" and path.endswith("/metadata"):
        return "metadata_field_create"
    if method == "GET" and path.endswith("/indexing-status"):
        return "document_indexing_status"
    if method == "GET" and path.endswith("/metadata"):
        return "metadata_field_list"
    if method == "GET" and path.endswith("/documents"):
        return "document_list"
    if method == "GET" and "/documents/" in path:
        return "document_detail"
    if method == "GET" and "datasets/" in path:
        return "dataset_config"
    if method == "DELETE" and "/documents/" in path:
        return "document_delete"
    return "unknown_knowledge_operation"


class _RateLimitedClient:
    """Keep the live knowledge transaction below Dify's 10 req/min sandbox gate."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._last_request_at: float | None = None
        self._created_document_ids: list[str] = []
        self.last_operation = "none"

    def _wait(self) -> None:
        if self._last_request_at is not None:
            remaining = KNOWLEDGE_REQUEST_INTERVAL_SECONDS - (
                time.monotonic() - self._last_request_at
            )
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_at = time.monotonic()

    def get(self, *args: object, **kwargs: object) -> httpx.Response:
        self._wait()
        self.last_operation = _safe_operation("GET", args[0])
        response = self._client.get(*args, **kwargs)
        self._record_response_failure(response, "GET")
        return response

    def post(self, *args: object, **kwargs: object) -> httpx.Response:
        self._wait()
        self.last_operation = _safe_operation("POST", args[0])
        response = self._client.post(*args, **kwargs)
        if response.status_code == 200 and str(args[0]).endswith("/document/create-by-text"):
            try:
                payload = response.json()
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload = None
            document = payload.get("document") if isinstance(payload, dict) else None
            document_id = document.get("id") if isinstance(document, dict) else None
            if isinstance(document_id, str):
                self._created_document_ids.append(document_id)
        self._record_response_failure(response, "POST")
        return response

    def delete(self, *args: object, **kwargs: object) -> httpx.Response:
        self._wait()
        self.last_operation = _safe_operation("DELETE", args[0])
        response = self._client.delete(*args, **kwargs)
        self._record_response_failure(response, "DELETE")
        return response

    def _record_response_failure(self, response: httpx.Response, method: str) -> None:
        if response.status_code < 300:
            return
        SMOKE_PATH.parent.mkdir(parents=True, exist_ok=True)
        inspection = inspect_dify_knowledge_error(response)
        (SMOKE_PATH.parent / "knowledge-http-failure.json").write_text(
            json.dumps(
                {
                    **inspection,
                    "created_count": len(self._created_document_ids),
                    "method": method,
                    "operation": self.last_operation,
                    "status_code": response.status_code,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def record_exception(self, error: Exception) -> None:
        safe_reasons = {
            "dataset configuration readback is invalid",
            "dataset segmentation readback is invalid",
            "dataset configuration does not match fixed contract",
            "dataset configuration readback did not stabilize",
            "metadata batch update failed",
            "readback document page is incomplete",
            "readback contains an unexpected document",
            "remote metadata does not exactly match sealed build",
            "remote document pagination is invalid",
            "remote document identity metadata is invalid",
        }
        message = str(error)
        SYNC_FAILURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SYNC_FAILURE_PATH.write_text(
            json.dumps(
                {
                    "created_count": len(self._created_document_ids),
                    "exception_type": type(error).__name__,
                    "last_operation": self.last_operation,
                    "safe_reason": message if message in safe_reasons else "unclassified",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def rollback_created(self, *, dataset_id: str, headers: dict[str, str]) -> None:
        """Delete only documents created by this failed transaction."""

        if not self._created_document_ids:
            return
        time.sleep(KNOWLEDGE_ROLLING_WINDOW_SECONDS)
        self._last_request_at = None
        for document_id in reversed(self._created_document_ids):
            response = self.delete(
                f"datasets/{dataset_id}/documents/{document_id}", headers=headers
            )
            if response.status_code not in {200, 204}:
                raise AssertionError("phase8_knowledge_rollback_failed")
        self._created_document_ids.clear()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _required_environment() -> dict[str, str]:
    names = (
        "DIFY_API_KEY",
        "DIFY_BASE_URL",
        "DIFY_USER",
        "DIFY_DATASET_API_KEY",
        "DIFY_DATASET_ID",
        "DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED",
    )
    values = {name: os.environ.get(name, "") for name in names}
    missing = [name for name, value in values.items() if not value.strip()]
    assert not missing, "phase8_cloud_readiness_missing"
    assert values["DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED"] == "1"
    return values


def _load_case() -> tuple[dict[str, object], Path, bytes]:
    case = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    assert isinstance(case, dict)
    relative = case["screenshot_path"]
    assert isinstance(relative, str) and relative == relative.replace("\\", "/")
    image_path = (ROOT / relative).resolve()
    image_path.relative_to(ROOT.resolve())
    image = image_path.read_bytes()
    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    assert case["screenshot_sha256"] == _sha256(image)
    return case, image_path, image


def _assert_parameters(settings: DebugMateSettings) -> str:
    assert settings.dify_api_key is not None
    with httpx.Client(
        base_url=f"{settings.dify_base_url.rstrip('/')}/",
        timeout=30.0,
        follow_redirects=False,
    ) as client:
        response = client.get(
            "parameters",
            headers={"Authorization": f"Bearer {settings.dify_api_key.get_secret_value()}"},
        )
        assert response.status_code == 200, "phase8_app_parameters_failed"
        assert len(response.content) <= 256 * 1024
        payload = response.json()
    forms = payload.get("user_input_form")
    assert isinstance(forms, list)
    image_fields = []
    for form in forms:
        assert isinstance(form, dict) and len(form) == 1
        kind, definition = next(iter(form.items()))
        assert isinstance(definition, dict)
        if definition.get("variable") == "image_input":
            image_fields.append((kind, definition))
    assert len(image_fields) == 1
    kind, definition = image_fields[0]
    assert kind in {"file", "file-list"}
    assert definition.get("variable") == "image_input"
    return _sha256(json.dumps(payload, sort_keys=True).encode("utf-8"))


def test_phase8_current_knowledge_and_published_image_workflow() -> None:
    values = _required_environment()
    settings = DebugMateSettings.from_env()
    case, image_path, image = _load_case()
    build_id = case["knowledge_build_id"]
    assert isinstance(build_id, str)
    build_path = ROOT / ".artifacts" / "knowledge-build" / build_id
    build = validate_knowledge_build(build_path)
    assert build.manifest["content_hash"] == case["knowledge_content_sha256"]
    assert build.manifest["document_count"] == 17
    assert build.manifest["status"] == "ready" and build.manifest["syncable"] is True

    with httpx.Client(
        base_url=f"{settings.dify_base_url.rstrip('/')}/",
        timeout=httpx.Timeout(connect=10.0, write=30.0, read=95.0, pool=5.0),
        follow_redirects=False,
    ) as client:
        knowledge_client = _RateLimitedClient(client)
        try:
            attestation = synchronize_knowledge(
                build_path,
                client=knowledge_client,  # type: ignore[arg-type]
                dataset_key=values["DIFY_DATASET_API_KEY"],
                dataset_id=values["DIFY_DATASET_ID"],
                confirm_delete=False,
                deadline_seconds=900.0,
            )
        except Exception as error:
            knowledge_client.record_exception(error)
            knowledge_client.rollback_created(
                dataset_id=values["DIFY_DATASET_ID"],
                headers={"Authorization": f"Bearer {values['DIFY_DATASET_API_KEY']}"},
            )
            raise
    assert attestation.document_count == 17
    assert len(set(attestation.document_fingerprints)) == 17
    READBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    READBACK_PATH.write_text(attestation.model_dump_json() + "\n", encoding="utf-8")
    DifyReadbackAttestation.model_validate_json(READBACK_PATH.read_bytes(), strict=True)

    parameters_sha256 = _assert_parameters(settings)
    result = None
    upload = None
    for attempt in range(WORKFLOW_CONTRACT_RETRIES):
        backend = DifyBackend(settings)
        try:
            upload = backend.upload_bytes(
                image,
                filename=image_path.name,
                mime_type="image/png",
                user=settings.dify_user,
            )
            result = backend.run_workflow(
                {
                    "case_id": case["case_id"],
                    "error_text": case["error_text"],
                    "code": case["code"],
                    "environment": case["environment"],
                    "image_input": {
                        "type": "image",
                        "transfer_method": "local_file",
                        "upload_file_id": upload.file_id,
                    },
                },
                settings.dify_user,
            )
            break
        except DifyContractError as error:
            if type(error) is not DifyContractError:
                raise
            if attempt + 1 == WORKFLOW_CONTRACT_RETRIES:
                raise
        finally:
            backend.close()
    if result is None or upload is None:
        raise AssertionError("live workflow did not produce a result")

    envelope = result.run_envelope
    assert isinstance(envelope, DifyRunEnvelope)
    assert envelope.case_id == case["case_id"]
    assert envelope.contract.knowledge_build_id == build_id
    assert envelope.retrieval_trace.knowledge_build_id == build_id
    assert envelope.retrieval_trace.hits
    assert envelope.diagnosis.case_id == case["case_id"]
    assert envelope.diagnosis.observed_facts
    assert result.backend == "dify"
    ENVELOPE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENVELOPE_PATH.write_text(envelope.model_dump_json() + "\n", encoding="utf-8")

    usage = result.usage.model_dump(mode="json") if result.usage is not None else None
    safe_usage: object = "not_reported"
    if isinstance(usage, dict) and any(value is not None for value in usage.values()):
        safe_usage = usage
    safe = {
        "schema_version": "1.0.0",
        "backend": "dify",
        "case_id_sha256": _sha256(str(case["case_id"]).encode("utf-8")),
        "image_sha256": case["screenshot_sha256"],
        "upload_fingerprint": upload.file_id_fingerprint,
        "run_fingerprint": result.run_id,
        "parameters_sha256": parameters_sha256,
        "knowledge_build_id": build_id,
        "dataset_fingerprint": attestation.dataset_fingerprint,
        "dsl_semantic_sha256": envelope.contract.dsl_semantic_sha256,
        "prompt_version": envelope.contract.prompt_version,
        "retrieval_run_fingerprint": envelope.retrieval_trace.run_fingerprint,
        "retrieval_node_fingerprint": envelope.retrieval_trace.node_fingerprint,
        "diagnosis_sha256": _sha256(envelope.diagnosis.model_dump_json().encode("utf-8")),
        "usage": safe_usage,
    }
    SMOKE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_PATH.write_text(
        json.dumps(safe, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
