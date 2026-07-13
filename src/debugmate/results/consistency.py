"""One fail-closed cross-modal boundary before result publication.

The renderers deliberately expose different candidate shapes.  This module is
the only place where those shapes become a publication candidate.  It retains
no renderer-owned file path and keeps a successful TTS candidate behind its
existing one-shot handoff until the publisher has an exclusive transaction.
"""

from __future__ import annotations

import os
import stat
import threading
import weakref
from dataclasses import dataclass
from pathlib import Path

from debugmate.diagnosis.workflow import WorkflowStatus
from debugmate.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.audio import TtsSynthesisOutcome
from debugmate.results.card import CardCandidate, CardRenderFailure, verify_card_png
from debugmate.results.contracts import (
    ArtifactAvailability,
    ArtifactIdentity,
    AudioResult,
    ResultStatus,
    SafeFailure,
)
from debugmate.results.loader import LoadedDiagnosisSource
from debugmate.results.presentation import PresentationModel, _validated_presentation
from debugmate.results.recap import SafeRecapText, compose_recap
from debugmate.results.report import (
    RenderedCitations,
    RenderedReport,
    _scan_rendered_report,
    render_citations,
    render_report,
)


class ResultConsistencyError(ValueError):
    """A stable, path-free rejection from the renderer/publication boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ValidatedResultCandidates:
    """Bytes and metadata proven safe for one immutable result transaction.

    The dataclass intentionally has no source/card/audio filesystem path.  A
    successful MP3 is represented by the corresponding public ``AudioResult``
    only; the private handoff is held in the module registry and can be used
    exactly once by :func:`take_verified_audio_for_publication`.
    """

    identity: ArtifactIdentity
    status: ResultStatus
    availability: ArtifactAvailability
    failure: SafeFailure | None
    diagnosis_bytes: bytes
    report_bytes: bytes
    citations_bytes: bytes
    source_manifest_bytes: bytes
    recap_bytes: bytes
    card_bytes: bytes | None
    audio: AudioResult
    _token: object | None


@dataclass(slots=True)
class _AudioState:
    owner: weakref.ReferenceType[ValidatedResultCandidates]
    outcome: TtsSynthesisOutcome


_AUDIO_LOCK = threading.RLock()
_AUDIO_STATES: dict[object, _AudioState] = {}


def _discard_state(token: object) -> None:
    with _AUDIO_LOCK:
        state = _AUDIO_STATES.pop(token, None)
    if state is not None and state.outcome.handoff is not None:
        state.outcome.handoff.close()


def _forget_candidate(token: object):
    def finalize(_owner: object) -> None:
        _discard_state(token)

    return finalize


def take_verified_audio_for_publication(candidate: ValidatedResultCandidates) -> bytes | None:
    """Consume the exact TTS handoff once inside the publisher transaction."""

    if not isinstance(candidate, ValidatedResultCandidates):
        raise ResultConsistencyError("candidate_invalid")
    token = candidate._token
    if token is None:
        return None
    with _AUDIO_LOCK:
        state = _AUDIO_STATES.pop(token, None)
    if state is None or state.owner() is not candidate or state.outcome.handoff is None:
        raise ResultConsistencyError("audio_handoff_invalid")
    try:
        payload = state.outcome.handoff.take_verified_bytes(state.outcome.audio)
    except Exception:
        raise ResultConsistencyError("audio_handoff_invalid") from None
    if (
        not payload
        or sha256_bytes(payload) != candidate.audio.sha256
        or len(payload) > 8_000_000
    ):
        raise ResultConsistencyError("audio_handoff_invalid")
    return payload


def discard_audio_handoff(candidate: ValidatedResultCandidates) -> None:
    """Release an unneeded successful handoff without exposing its location."""

    if isinstance(candidate, ValidatedResultCandidates) and candidate._token is not None:
        _discard_state(candidate._token)


def _strict_source(value: object) -> LoadedDiagnosisSource:
    if not isinstance(value, LoadedDiagnosisSource):
        raise ValueError("source type")
    source = LoadedDiagnosisSource.model_validate_json(
        canonical_json_bytes(value.model_dump(mode="json")), strict=True
    )
    diagnosis = source.diagnosis
    if (
        source.outcome.status is not WorkflowStatus.COMPLETED
        or source.outcome.diagnosis != diagnosis
        or source.case_id != diagnosis.case_id
        or source.source_run_id != source.outcome.run_id
        or source.source_manifest.case_id != source.case_id
        or source.source_manifest.run_id != source.source_run_id
        or source.source_manifest.schema_version != diagnosis.schema_version
        or source.diagnosis_sha256
        != sha256_bytes(canonical_json_bytes(diagnosis.model_dump(mode="json")))
    ):
        raise ValueError("source identity")
    return source


def _safe_regular_file(path: Path) -> bool:
    try:
        info = path.stat(follow_symlinks=False)
    except OSError:
        return False
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        return False
    if bool(getattr(info, "st_file_attributes", 0) & 0x400):
        return False
    current = path.parent
    while current != current.parent:
        try:
            ancestor = current.stat(follow_symlinks=False)
        except OSError:
            return False
        if current.is_symlink() or not stat.S_ISDIR(ancestor.st_mode):
            return False
        if bool(getattr(ancestor, "st_file_attributes", 0) & 0x400):
            return False
        current = current.parent
    return True


def _source_manifest_bytes(source: LoadedDiagnosisSource) -> bytes:
    summary = {
        "source_contract_version": "1.0.0",
        "case_id": source.case_id,
        "source_run_id": source.source_run_id,
        "diagnosis_sha256": source.diagnosis_sha256,
        "schema_version": source.source_manifest.schema_version,
        "facts_revision": source.source_manifest.facts_revision,
        "facts_sha256": source.source_manifest.facts_sha256,
        "routing_rule_version": source.source_manifest.routing_rule_version,
        "knowledge_build_id": source.source_manifest.knowledge_build_id,
        "prompt_version": source.source_manifest.prompt_version,
        "workflow_version": source.source_manifest.workflow_version,
        "node_states": [item.model_dump(mode="json") for item in source.source_manifest.node_states],
    }
    assert_export_safe(summary)
    return canonical_json_bytes(summary)


def _card_bytes(card: CardCandidate, presentation: PresentationModel) -> bytes:
    if (
        card.identity != presentation.identity
        or card.font_name != presentation.font_name
        or card.font_sha256 != presentation.font_sha256
        or not card.path.is_absolute()
        or not _safe_regular_file(card.path)
    ):
        raise ResultConsistencyError("artifact_identity_mismatch")
    try:
        verify_card_png(card.path, expected_size=(card.width, card.height))
        payload = card.path.read_bytes()
    except Exception:
        raise ResultConsistencyError("card_verify_failed") from None
    if card.bytes != len(payload) or card.sha256 != sha256_bytes(payload):
        raise ResultConsistencyError("card_verify_failed")
    return payload


def _strict_identity(*values: ArtifactIdentity) -> ArtifactIdentity:
    identity = values[0]
    if any(item != identity for item in values[1:]):
        raise ResultConsistencyError("artifact_identity_mismatch")
    return identity


def _validated_audio(
    value: object, identity: ArtifactIdentity
) -> tuple[AudioResult, TtsSynthesisOutcome | None]:
    if not isinstance(value, TtsSynthesisOutcome):
        raise ResultConsistencyError("audio_handoff_invalid")
    audio = value.audio
    if audio.identity != identity:
        raise ResultConsistencyError("artifact_identity_mismatch")
    if audio.available:
        if value.handoff is None:
            raise ResultConsistencyError("audio_handoff_invalid")
        return audio, value
    if value.handoff is not None or audio.failure is None:
        raise ResultConsistencyError("audio_handoff_invalid")
    if audio.failure.failed_stage != "audio":
        raise ResultConsistencyError("audio_failure_invalid")
    return audio, None


def validate_result_candidates(
    source: LoadedDiagnosisSource,
    presentation: PresentationModel,
    report: RenderedReport,
    citations: RenderedCitations,
    card_result: CardCandidate | CardRenderFailure,
    recap: SafeRecapText,
    audio_result: TtsSynthesisOutcome,
) -> ValidatedResultCandidates:
    """Revalidate one same-identity modality set before any public file exists."""

    try:
        verified_source = _strict_source(source)
        verified_presentation = _validated_presentation(presentation)
        expected_identity = ArtifactIdentity(
            case_id=verified_source.case_id,
            source_run_id=verified_source.source_run_id,
            diagnosis_sha256=verified_source.diagnosis_sha256,
            schema_version=verified_source.diagnosis.schema_version,
            generation_version=verified_presentation.identity.generation_version,
        )
        if verified_presentation.identity != expected_identity:
            raise ResultConsistencyError("artifact_identity_mismatch")
        expected_report = render_report(verified_presentation)
        expected_citations = render_citations(verified_presentation)
        expected_recap = compose_recap(verified_presentation)
        if not isinstance(report, RenderedReport) or report != expected_report:
            raise ResultConsistencyError("report_verify_failed")
        if not isinstance(citations, RenderedCitations) or citations != expected_citations:
            raise ResultConsistencyError("citation_verify_failed")
        if not isinstance(recap, SafeRecapText) or recap != expected_recap:
            raise ResultConsistencyError("recap_verify_failed")
        identity = _strict_identity(
            expected_identity, report.identity, citations.identity, recap.identity
        )
        _scan_rendered_report(verified_presentation, report.markdown)
        assert_export_safe(recap.text)
        diagnosis_payload = verified_source.diagnosis.model_dump(mode="json")
        assert_export_safe(diagnosis_payload)
        diagnosis_bytes = canonical_json_bytes(diagnosis_payload)
        source_bytes = _source_manifest_bytes(verified_source)
        audio, handoff_outcome = _validated_audio(audio_result, identity)

        card_bytes: bytes | None
        failure: SafeFailure | None
        if isinstance(card_result, CardCandidate):
            card_bytes = _card_bytes(card_result, verified_presentation)
            if audio.available:
                availability = ArtifactAvailability(
                    report=True, card=True, recap_text=True, audio=True
                )
                status = ResultStatus.COMPLETED
                failure = None
            else:
                availability = ArtifactAvailability(
                    report=True, card=True, recap_text=True, audio=False
                )
                status = ResultStatus.PARTIAL
                failure = audio.failure
        elif isinstance(card_result, CardRenderFailure):
            if audio.available:
                card_bytes = None
                availability = ArtifactAvailability(
                    report=True, card=False, recap_text=True, audio=True
                )
                status = ResultStatus.PARTIAL
                failure = SafeFailure(
                    code=card_result.code, failed_stage="card", retry_scope="card"
                )
            else:
                raise ResultConsistencyError("partial_availability_invalid")
        else:
            raise ResultConsistencyError("card_verify_failed")
        if status is ResultStatus.PARTIAL and failure is None:
            raise ResultConsistencyError("partial_availability_invalid")
        token: object | None = None
        if handoff_outcome is not None:
            token = object()
        candidate = ValidatedResultCandidates(
            identity=identity,
            status=status,
            availability=availability,
            failure=failure,
            diagnosis_bytes=diagnosis_bytes,
            report_bytes=report.markdown.encode("utf-8"),
            citations_bytes=citations.json_bytes,
            source_manifest_bytes=source_bytes,
            recap_bytes=recap.text.encode("utf-8"),
            card_bytes=card_bytes,
            audio=audio,
            _token=token,
        )
        if token is not None:
            owner = weakref.ref(candidate, _forget_candidate(token))
            with _AUDIO_LOCK:
                _AUDIO_STATES[token] = _AudioState(owner=owner, outcome=handoff_outcome)
        return candidate
    except ResultConsistencyError:
        raise
    except Exception:
        raise ResultConsistencyError("candidate_validation_failed") from None
