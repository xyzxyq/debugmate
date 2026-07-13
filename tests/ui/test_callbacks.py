from __future__ import annotations

from pathlib import Path

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
from debugmate.ui.app import UiCallbacks


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

    def correct_and_compose(self, previous_run_id, draft, confirmed):
        self.correction_calls.append((previous_run_id, draft, confirmed))
        return self.state


def test_replay_callback_uses_service_member_ids_and_materializes_only_verified_bytes(
    tmp_path: Path,
) -> None:
    service = _Service()
    callbacks = UiCallbacks(service, cache_root=tmp_path / "ui-cache")

    payload = callbacks.load_replay("module-not-found")

    assert service.replay_calls == ["module-not-found"]
    assert payload.state == service.state
    assert payload.report_markdown == "# DebugMate\n\nverified report"
    assert payload.card_path is not None and Path(payload.card_path).read_bytes() == b"verified-card"
    assert payload.audio_path is not None and Path(payload.audio_path).read_bytes() == b"verified-audio"
    assert payload.download_path is not None and Path(payload.download_path).read_bytes() == b"verified-zip"
    assert "回放" in payload.view.result_metadata


def test_tampered_member_after_render_becomes_safe_failure_without_stale_path(tmp_path: Path) -> None:
    service = _Service()
    callbacks = UiCallbacks(service, cache_root=tmp_path / "ui-cache")
    service.reject_member = True

    payload = callbacks.load_replay("module-not-found")

    assert payload.state.status.value == "failed"
    assert payload.state.failure.code == "download_invalid"
    assert payload.report_markdown is None
    assert payload.card_path is None and payload.audio_path is None and payload.download_path is None
    assert "C:" not in repr(payload)


def test_correction_callback_accepts_only_strict_run_id_and_draft_and_never_a_path(tmp_path: Path) -> None:
    from debugmate.results.service import CorrectionDraft

    service = _Service()
    callbacks = UiCallbacks(service, cache_root=tmp_path / "ui-cache")
    payload = callbacks.correct(
        service.state.identity.source_run_id,
        CorrectionDraft(field_id="exception_type", replacement="ImportError", reason="确认"),
        confirmed=False,
    )

    assert payload.state == service.state
    assert service.correction_calls[0][2] is False
    bad = callbacks.refresh("C:/private/result", "result_" + "6" * 32)
    assert bad.state.status.value == "failed"
    assert "private" not in repr(bad)
