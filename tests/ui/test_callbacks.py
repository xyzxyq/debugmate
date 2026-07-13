from __future__ import annotations

import asyncio

import gradio as gr
from fastapi import FastAPI
from fastapi.testclient import TestClient

from debugmate.results.contracts import (
    ArtifactAvailability,
    ArtifactIdentity,
    AudioAttempt,
    AudioResult,
    ResultMode,
    ResultStatus,
    ResultViewState,
)
from debugmate.results.verifier import VerifiedDownload
from debugmate.ui.app import (
    UiCallbacks,
    UiContentUrl,
    _VerifiedAudio,
    _VerifiedDownloadButton,
    _VerifiedImage,
    correction_draft_from_fields,
    mount_content_endpoint,
)


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
        fixture_id="module-not-found",
        fixture_name="ModuleNotFoundError：缺少虚构依赖包",
        status=ResultStatus.COMPLETED,
        identity=identity,
        result_id="result_" + "6" * 32,
        availability=ArtifactAvailability(report=True, card=True, recap_text=True, audio=True),
        audio=audio,
    )


class _Service:
    def __init__(self) -> None:
        self.state = _state()
        self.reject_member = False
        self.replay_calls: list[str] = []
        self.correction_calls: list[tuple[object, ...]] = []

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
            "report": (b"# DebugMate\n\nverified report", "report.md", "text/markdown"),
            "card": (b"verified-card", "card.png", "image/png"),
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


def test_process_api_serializes_verified_urls_without_a_server_path() -> None:
    """Native components must preserve the capability URL instead of staging a file."""

    card_url = UiContentUrl(
        url="http://127.0.0.1:7860/debugmate-content/" + "a" * 32,
        filename="diagnosis-card.png",
        mime_type="image/png",
    )
    audio_url = UiContentUrl(
        url="http://127.0.0.1:7860/debugmate-content/" + "b" * 32,
        filename="recap.mp3",
        mime_type="audio/mpeg",
    )
    bundle_url = UiContentUrl(
        url="http://127.0.0.1:7860/debugmate-content/" + "c" * 32,
        filename="debugmate-result.zip",
        mime_type="application/zip",
    )
    with gr.Blocks() as app:
        trigger = gr.Button("deliver")
        card = _VerifiedImage(type="filepath", sources=None, buttons=[])
        audio = _VerifiedAudio(type="filepath", sources=None, recording=False, buttons=[])
        bundle = _VerifiedDownloadButton("download")
        trigger.click(
            lambda: (card_url, audio_url, bundle_url),
            outputs=[card, audio, bundle],
            api_name=False,
        )

    response = asyncio.run(app.process_api(block_fn=0, inputs=[], state=None))

    assert [item["url"] for item in response["data"]] == [
        card_url.url,
        audio_url.url,
        bundle_url.url,
    ]
    assert [item["path"] for item in response["data"]] == [
        card_url.url,
        audio_url.url,
        bundle_url.url,
    ]
    assert [item["orig_name"] for item in response["data"]] == [
        card_url.filename,
        audio_url.filename,
        bundle_url.filename,
    ]
    assert [item.get("mime_type") for item in response["data"]] == [
        card_url.mime_type,
        audio_url.mime_type,
        bundle_url.mime_type,
    ]
    rendered = repr(response["data"])
    assert "X:\\" not in rendered
    assert "phase-1-foundation-platform-gate" not in rendered
    assert "/gradio_api/file=" not in rendered


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
