"""Offline contracts for Phase 08 ordinary Dify/live UI assembly."""

from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.cloud.workflow import DifyLiveWorkflow
from debugmate.knowledge.sync import DifyReadbackAttestation, DifySyncConfig
from debugmate.results.contracts import (
    ArtifactAvailability,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.settings import DebugMateSettings
from debugmate.ui import serve as serve_module
from debugmate.ui.app import build_app
from debugmate.ui.presentation import render_view_state

BUILD_ID = "b" * 64


def _write_live_authority(root: Path) -> tuple[Path, Path, str]:
    build_root = root / BUILD_ID
    build_root.mkdir(parents=True)
    manifest = {
        "build_id": BUILD_ID,
        "sources": [
            {
                "source_id": f"source-{index:02d}",
                "url": f"https://example.invalid/source-{index:02d}",
            }
            for index in range(17)
        ],
    }
    manifest_path = build_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    dataset_id = "configured-dataset-binding"
    attestation = DifyReadbackAttestation(
        knowledge_build_id=BUILD_ID,
        dataset_fingerprint=hashlib.sha256(dataset_id.encode()).hexdigest(),
        document_count=17,
        document_fingerprints=[f"{index + 1:064x}" for index in range(17)],
        config=DifySyncConfig(),
        response_hashes=["c" * 64],
    )
    attestation_path = root / "knowledge-readback.json"
    attestation_path.write_text(attestation.model_dump_json(), encoding="utf-8")
    return manifest_path, attestation_path, dataset_id


def _settings(*, dataset_key: bool = True) -> DebugMateSettings:
    return DebugMateSettings(
        dify_api_key=SecretStr("app-secret"),
        dify_dataset_api_key=SecretStr("dataset-secret") if dataset_key else None,
        dify_user="debugmate-phase8",
        approval_key=SecretStr("a" * 32),
    )


def _poison_outbound(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("construction attempted outbound I/O")

    monkeypatch.setattr(httpx.Client, "send", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)


def test_complete_local_authority_constructs_dify_without_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest_path, attestation_path, dataset_id = _write_live_authority(tmp_path)
    _poison_outbound(monkeypatch)

    dependencies = serve_module._live_dependencies(
        settings=_settings(),
        runtime_root=tmp_path / "runtime",
        build_manifest=manifest_path,
        readback_attestation=attestation_path,
        dataset_binding=dataset_id,
        app_ready=True,
    )

    assert dependencies.execution_backend is ExecutionBackend.DIFY
    assert dependencies.fallback_reason is None
    assert isinstance(dependencies.service._workflow, DifyLiveWorkflow)
    assert dependencies.service._live_execution_backend is ExecutionBackend.DIFY


def test_incomplete_configuration_constructs_value_free_local_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _poison_outbound(monkeypatch)
    settings = DebugMateSettings(approval_key=SecretStr("a" * 32))

    dependencies = serve_module._live_dependencies(
        settings=settings,
        runtime_root=tmp_path / "runtime",
        app_ready=False,
    )

    assert dependencies.execution_backend is ExecutionBackend.LOCAL_FALLBACK
    assert dependencies.fallback_reason == "app_config_incomplete"
    assert dependencies.service._live_execution_backend is ExecutionBackend.LOCAL_FALLBACK
    assert "secret" not in dependencies.fallback_reason


def test_dataset_key_is_not_required_after_verified_readback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest_path, attestation_path, dataset_id = _write_live_authority(tmp_path)
    _poison_outbound(monkeypatch)

    dependencies = serve_module._live_dependencies(
        settings=_settings(dataset_key=False),
        runtime_root=tmp_path / "runtime",
        build_manifest=manifest_path,
        readback_attestation=attestation_path,
        dataset_binding=dataset_id,
        app_ready=True,
    )

    assert dependencies.execution_backend is ExecutionBackend.DIFY
    assert isinstance(dependencies.service._workflow, DifyLiveWorkflow)


class _UiOnlyService:
    _live_execution_backend = ExecutionBackend.DIFY


def _view(
    backend: ExecutionBackend,
    *,
    status: ResultStatus = ResultStatus.IDLE,
    stage: str | None = None,
) -> ResultViewState:
    return ResultViewState(
        mode=ResultMode.REPLAY if backend is ExecutionBackend.REPLAY else ResultMode.LIVE,
        execution_backend=backend,
        status=status,
        fixture_id="module-not-found" if backend is ExecutionBackend.REPLAY else None,
        fixture_name=(
            "ModuleNotFoundError：缺少虚构依赖包"
            if backend is ExecutionBackend.REPLAY
            else None
        ),
        availability=ArtifactAvailability(),
        current_stage=stage,
    )


def test_backend_labels_and_dify_confirmation_copy_are_explicit() -> None:
    assert "Dify 实时诊断" in render_view_state(_view(ExecutionBackend.DIFY)).mode_badge
    assert "本地降级" in render_view_state(
        _view(ExecutionBackend.LOCAL_FALLBACK)
    ).mode_badge
    assert "固定回放" in render_view_state(_view(ExecutionBackend.REPLAY)).mode_badge

    app = build_app(_UiOnlyService(), execution_backend=ExecutionBackend.DIFY)
    disclosure = next(
        component
        for component in app.get_config_file()["components"]
        if component.get("props", {}).get("elem_id") == "approval-disclosure"
    )
    copy = disclosure["props"]["value"]
    assert "脱敏" in copy and "Dify" in copy and "额度" in copy
    assert "API key" not in copy and "run_id" not in copy


def test_dify_running_and_validation_are_coarse_truthful_stages() -> None:
    expected = {
        "upload": "上传脱敏截图",
        "dify_workflow": "Dify 工作流运行中",
        "validation": "本地严格校验",
    }
    for stage, label in expected.items():
        view = render_view_state(
            _view(ExecutionBackend.DIFY, status=ResultStatus.RUNNING, stage=stage)
        )
        assert view.stage_label == label
        assert "%" not in (view.running_copy or "")
        assert "节点" not in (view.running_copy or "")


def test_invalid_dify_diagnosis_has_backend_failure_and_no_artifacts() -> None:
    state = ResultViewState(
        mode=ResultMode.LIVE,
        execution_backend=ExecutionBackend.DIFY,
        status=ResultStatus.FAILED,
        availability=ArtifactAvailability(),
        failure=SafeFailure(
            code="diagnosis_validation",
            failed_stage="workflow",
            retry_scope="input",
        ),
    )
    view = render_view_state(state)

    assert "Dify 实时诊断" in view.mode_badge
    assert view.available_artifacts == ()
    assert view.download_label is None
    assert view.failure_code == "diagnosis_validation"
    assert view.stage_label == "诊断工作流"
    assert "重新" in (view.safe_failure_copy or "") or "重试" in (
        view.safe_failure_copy or ""
    )
