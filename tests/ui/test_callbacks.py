from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import URL

from debugmate.cloud.contracts import ExecutionBackend
from debugmate.results.contracts import (
    ArtifactAvailability,
    ArtifactIdentity,
    AudioAttempt,
    AudioResult,
    ResultMode,
    ResultStatus,
    ResultViewState,
    SafeFailure,
)
from debugmate.results.service import ResultServiceError
from debugmate.results.verifier import VerifiedDownload
from debugmate.ui.app import (
    UiCallbacks,
    _component_updates,
    _loopback_origin,
    correction_draft_from_fields,
    mount_content_endpoint,
)


def test_loopback_origin_accepts_only_string_or_real_starlette_url() -> None:
    expected = "http://127.0.0.1:7868"

    assert _loopback_origin(
        URL("http://127.0.0.1:7868/gradio_api/queue/join"), origin_only=False
    ) == expected
    with pytest.raises(ResultServiceError):
        _loopback_origin(object(), origin_only=False)


def _state() -> ResultViewState:
    identity = ArtifactIdentity(
        case_id="case_" + "1" * 32,
        source_run_id="run_" + "2" * 32,
        diagnosis_sha256="3" * 64,
        schema_version="1.1.0",
        generation_version="gen_" + "4" * 32,
    )


    audio = AudioResult(
        identity=identity,
        available=True,
        backend="dify",
        attempts=(
            AudioAttempt(
                backend="dify",
                rate_profile="normal",
                succeeded=True,
                duration_ms=40_000,
                sha256="5" * 64,
            ),
        ),
        duration_ms=40_000,
        sha256="5" * 64,
    )
    return ResultViewState(
        mode=ResultMode.REPLAY,
        execution_backend=ExecutionBackend.REPLAY,
        fixture_id="module-not-found",
        fixture_name="ModuleNotFoundError：缺少虚构依赖包",
        status=ResultStatus.COMPLETED,
        identity=identity,
        result_id="result_" + "6" * 32,
        availability=ArtifactAvailability(report=True, card=True, recap_text=True, audio=True),
        audio=audio,
    )


def _partial_state(failed_stage: str) -> ResultViewState:
    completed = _state()
    assert completed.identity is not None
    if failed_stage == "audio":
        failure = SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="tts")
        audio = AudioResult(
            identity=completed.identity,
            available=False,
            attempts=(
                AudioAttempt(
                    backend="dify",
                    rate_profile="normal",
                    succeeded=False,
                    safe_error_code="tts_failed",
                ),
            ),
            failure=failure,
        )
        availability = ArtifactAvailability(
            report=True, card=True, recap_text=True, audio=False
        )
    else:
        failure = SafeFailure(
            code="png_layout_failed", failed_stage="card", retry_scope="card"
        )
        audio = completed.audio
        availability = ArtifactAvailability(
            report=True, card=False, recap_text=True, audio=True
        )
    return completed.model_copy(
        update={
            "status": ResultStatus.PARTIAL,
            "result_id": "result_" + "7" * 32,
            "availability": availability,
            "failure": failure,
            "audio": audio,
        }
    )


class _Service:
    def __init__(self) -> None:
        self.state = _state()
        self.reject_member = False
        self.replay_calls: list[str] = []
        self.correction_calls: list[tuple[object, ...]] = []
        self.retry_calls: list[tuple[str, str]] = []

    def load_replay(self, fixture_id: str) -> ResultViewState:
        self.replay_calls.append(fixture_id)
        return self.state

    def resolve_download(self, case_id: str, result_id: str, member_id: str) -> VerifiedDownload:
        assert case_id == self.state.identity.case_id
        assert result_id == self.state.result_id
        if self.reject_member:
            from debugmate.results.service import ResultServiceError

            raise ResultServiceError("download_invalid")
        contents = {
            "diagnosis": (
                (
                    Path(__file__).resolve().parents[2]
                    / "fixtures/cases/module_not_found/diagnosis.json"
                ).read_bytes(),
                "diagnosis.json",
                "application/json",
            ),
            "report": (b"# DebugMate\n\nverified report", "report.md", "text/markdown"),
            "card": (b"verified-card", "card.png", "image/png"),
            "recap_text": (b"verified recap", "recap.txt", "text/plain"),
            "audio": (b"verified-audio", "recap.mp3", "audio/mpeg"),
            "bundle": (b"verified-zip", "debugmate-result.zip", "application/zip"),
        }
        payload, filename, mime_type = contents[member_id]
        return VerifiedDownload._issue(
            payload=payload,
            member_id=member_id,
            filename=filename,
            mime_type=mime_type,
            identity=self.state.identity,
        )

    def correction_fields(self, previous_run_id: str):
        from debugmate.results.service import CorrectionFields

        assert previous_run_id == self.state.identity.source_run_id
        return CorrectionFields(
            source_run_id=previous_run_id,
            values=(
                "ModuleNotFoundError",
                "main.py:1",
                "demo_pkg",
                "1.0",
                "cpu",
                "<WORKSPACE>/main.py",
            ),
        )

    def correct_and_compose(self, previous_run_id, draft, confirmed):
        self.correction_calls.append((previous_run_id, draft, confirmed))
        return self.state

    def retry_stage(self, case_id: str, result_id: str) -> ResultViewState:
        self.retry_calls.append((case_id, result_id))
        completed = _state().model_copy(update={"result_id": "result_" + "8" * 32})
        self.state = completed
        return completed


class _LoopbackRequest:
    def __init__(self, url: str) -> None:
        self.url = url


def test_replay_callback_uses_service_member_ids_and_materializes_only_verified_bytes() -> None:
    service = _Service()
    callbacks = UiCallbacks(service, content_origin="http://127.0.0.1:7868")

    payload = callbacks.load_replay(
        "module-not-found", request=_LoopbackRequest("http://127.0.0.1:7868/queue/join")
    )

    assert service.replay_calls == ["module-not-found"]
    assert payload.state == service.state
    assert payload.report_markdown == "# DebugMate\n\nverified report"
    assert payload.card_url is not None
    assert payload.card_url.url.startswith("http://127.0.0.1:7868/debugmate-content/")
    assert callbacks.resolve_content(payload.card_url).payload == b"verified-card"
    assert payload.audio_url is not None
    assert callbacks.resolve_content(payload.audio_url).payload == b"verified-audio"
    assert payload.download_url is not None
    archive = callbacks.resolve_content(payload.download_url)
    assert archive.payload == b"verified-zip"
    assert archive.attachment is True
    assert "ui-cache" not in repr(payload)
    assert payload.field_values[0] == "ModuleNotFoundError"
    assert "回放" in payload.view.result_metadata

    api = FastAPI()
    mount_content_endpoint(api, callbacks)
    response = TestClient(api).get(payload.card_url.url)
    assert response.status_code == 200
    assert response.content == b"verified-card"
    assert response.headers["content-type"].startswith("image/png")

    hostile = callbacks.load_replay(
        "module-not-found", request=_LoopbackRequest("http://attacker.invalid:7868/queue/join")
    )
    assert hostile.state.status.value == "failed"
    assert hostile.card_url is None


def test_tampered_member_after_render_becomes_safe_failure_without_stale_path(
) -> None:
    service = _Service()
    callbacks = UiCallbacks(service)
    service.reject_member = True

    payload = callbacks.load_replay("module-not-found")

    assert payload.state.status.value == "failed"
    assert payload.state.failure.code == "download_invalid"
    assert payload.report_markdown is None
    assert payload.card_url is None
    assert payload.audio_url is None
    assert payload.download_url is None
    assert "C:" not in repr(payload)


def test_failure_component_update_renders_all_safe_detail_values_not_labels_only() -> None:
    from debugmate.results.contracts import SafeFailure

    service = _Service()
    callbacks = UiCallbacks(service)
    failed = ResultViewState(
        mode=ResultMode.LIVE,
        execution_backend=ExecutionBackend.LOCAL_FALLBACK,
        status=ResultStatus.FAILED,
        availability=ArtifactAvailability(),
        failure=SafeFailure(
            code="source_bundle_invalid", failed_stage="source", retry_scope="source"
        ),
        completed_stages=("source",),
        inherited_stages=("presentation",),
    )

    updates = _component_updates(callbacks._render(failed))

    assert "**失败节点：** 验证来源" in updates[2]
    assert "**已完成阶段：** 验证来源" in updates[2]
    assert "**继承阶段：** 整理诊断" in updates[2]
    assert "**仍可使用的结果：** 无" in updates[2]
    assert "**可重试范围：** 来源证据" in updates[2]
    assert "**建议操作：** 重新验证来源证据后重试。" in updates[2]
    assert "来源证据未通过校验（source_bundle_invalid），未生成结果。" in updates[2]


def test_correction_callback_accepts_only_strict_run_id_and_draft_and_never_a_path(
) -> None:
    from debugmate.diagnosis.extraction import FieldId
    from debugmate.results.service import CorrectionDraft

    service = _Service()
    callbacks = UiCallbacks(service)
    payload = callbacks.correct(
        service.state.identity.source_run_id,
        CorrectionDraft(
            field_id=FieldId.EXCEPTION_TYPE,
            replacement="ImportError",
            reason="确认",
        ),
        confirmed=False,
    )

    assert payload.state == service.state
    assert service.correction_calls[0][2] is False
    bad = callbacks.refresh("C:/private/result", "result_" + "6" * 32)
    assert bad.state.status.value == "failed"
    assert "private" not in repr(bad)


def test_field_edit_creates_only_a_local_old_to_new_draft_until_explicit_confirmation(
) -> None:
    from debugmate.diagnosis.extraction import FieldId

    service = _Service()
    callbacks = UiCallbacks(service)
    original = callbacks.load_replay("module-not-found").field_values
    changed = list(original)
    changed[0] = "ImportError"

    draft, summary = correction_draft_from_fields(
        original, tuple(changed), service.state.identity.source_run_id
    )

    assert draft is not None
    assert draft.field_id is FieldId.EXCEPTION_TYPE
    assert "有 1 项未确认修改" in summary
    assert "ModuleNotFoundError → ImportError" in summary
    assert service.correction_calls == []
    no_op, helper = correction_draft_from_fields(
        original, original, service.state.identity.source_run_id
    )
    assert no_op is None
    assert helper == "请先修改至少一个抽取字段。"

    callbacks.correct(service.state.identity.source_run_id, draft, confirmed=True)
    assert service.correction_calls[-1][2] is True


@pytest.mark.parametrize("failed_stage", ["audio", "card"])
def test_partial_payload_preserves_verified_members_and_retry_uses_only_server_scope(
    failed_stage: str,
) -> None:
    service = _Service()
    service.state = _partial_state(failed_stage)
    callbacks = UiCallbacks(service)

    partial = callbacks._render(service.state)

    assert partial.state.status is ResultStatus.PARTIAL
    assert partial.report_markdown == "# DebugMate\n\nverified report"
    assert partial.recap_text == "verified recap"
    if failed_stage == "audio":
        assert partial.card_url is not None
        assert partial.audio_url is None
    else:
        assert partial.card_url is None
        assert partial.audio_url is not None
    assert partial.view.retry_label is not None
    old_result_id = partial.state.result_id
    assert partial.state.identity is not None and old_result_id is not None

    retried = callbacks.retry(partial.state.identity.case_id, old_result_id)

    assert service.retry_calls == [(partial.state.identity.case_id, old_result_id)]
    assert retried.state.status is ResultStatus.COMPLETED
    assert retried.state.result_id != old_result_id
    assert retried.card_url is not None
    assert retried.audio_url is not None


@pytest.mark.parametrize(
    ("case_id", "result_id"),
    [
        ("case_" + "1" * 31, "result_" + "7" * 32),
        ("case_" + "1" * 32, "result_" + "7" * 31),
        ("C:/private/case", "result_" + "7" * 32),
        ("case_" + "1" * 32, "../result_" + "7" * 32),
    ],
)
def test_retry_rejects_tampered_ids_before_any_service_call(
    case_id: object, result_id: object
) -> None:
    service = _Service()
    service.state = _partial_state("audio")
    callbacks = UiCallbacks(service)

    payload = callbacks.retry(case_id, result_id)

    assert payload.state.status is ResultStatus.FAILED
    assert payload.state.failure is not None
    assert payload.state.failure.code == "result_bundle_invalid"
    assert service.retry_calls == []
    assert "private" not in repr(payload)
