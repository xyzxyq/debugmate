"""Deterministic, privacy-preserving TTS fallback orchestration."""

from __future__ import annotations

import stat
import tempfile
from contextlib import suppress
from pathlib import Path

from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.contracts import (
    ArtifactIdentity,
    AudioAttempt,
    AudioResult,
    SafeFailure,
)
from debugmate.results.media import MediaProbeError, canonicalize_mp3, probe_mp3
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import RateProfile, TtsAdapter, TtsRequestIdentity


class TtsFallbackChain:
    def __init__(
        self,
        adapters: tuple[TtsAdapter, ...],
        *,
        probe_timeout: float = 15.0,
        max_bytes: int = 8_000_000,
    ) -> None:
        if tuple(adapter.backend for adapter in adapters) != (
            "dify",
            "edge_tts",
            "sapi",
        ):
            raise ValueError("tts_chain_invalid") from None
        self._adapters = adapters
        self._probe_timeout = probe_timeout
        self._max_bytes = max_bytes

    @staticmethod
    def _identity(request: TtsRequestIdentity) -> ArtifactIdentity:
        return ArtifactIdentity(
            case_id=request.case_id,
            source_run_id=request.source_run_id,
            diagnosis_sha256=request.diagnosis_sha256,
            schema_version="1.1.0",
            generation_version=request.generation_version,
        )

    def synthesize(
        self, recap: SafeRecapText, request: TtsRequestIdentity, target_root: Path
    ) -> AudioResult:
        recap_identity = recap.identity
        if (
            recap.sha256 != request.recap_sha256
            or recap_identity.case_id != request.case_id
            or recap_identity.source_run_id != request.source_run_id
            or recap_identity.diagnosis_sha256 != request.diagnosis_sha256
            or recap_identity.generation_version != request.generation_version
        ):
            raise ValueError("tts_identity_mismatch") from None
        assert_export_safe(recap.text)
        target_root.mkdir(parents=True, exist_ok=True)
        if _is_link_or_reparse(target_root):
            raise ValueError("tts_target_invalid") from None
        target_root = target_root.resolve(strict=True)
        final_path = target_root / "recap.mp3"
        if final_path.exists() or final_path.is_symlink():
            raise ValueError("tts_target_invalid") from None
        attempts: list[AudioAttempt] = []
        with tempfile.TemporaryDirectory(prefix="debugmate-tts-", dir=target_root) as temp_name:
            temp = Path(temp_name)
            for backend_index, adapter in enumerate(self._adapters):
                for rate in (RateProfile.NORMAL, RateProfile.FASTER):
                    candidate_path = temp / f"candidate-{backend_index}-{rate.value}.mp3"
                    try:
                        assert_export_safe(recap.text)
                        candidate = adapter.synthesize(recap, candidate_path, request, rate)
                        if not _candidate_matches(
                            candidate,
                            expected_path=candidate_path,
                            backend=adapter.backend,
                            rate=rate,
                            request=request,
                        ):
                            raise _CandidateInvalid
                        probe_mp3(
                            candidate.path,
                            timeout_seconds=self._probe_timeout,
                            max_bytes=self._max_bytes,
                        )
                        published_probe = canonicalize_mp3(
                            candidate.path,
                            final_path,
                            timeout_seconds=self._probe_timeout,
                            max_bytes=self._max_bytes,
                        )
                        final_probe = probe_mp3(
                            final_path,
                            timeout_seconds=self._probe_timeout,
                            max_bytes=self._max_bytes,
                        )
                        if final_probe != published_probe:
                            raise _CandidateInvalid
                    except _CandidateInvalid:
                        attempts.append(
                            AudioAttempt(
                                backend=adapter.backend,
                                rate_profile=rate.value,
                                succeeded=False,
                                safe_error_code="tts_candidate_invalid",
                            )
                        )
                        _safe_unlink(candidate_path)
                        _safe_unlink(final_path)
                        break
                    except MediaProbeError as exc:
                        code = getattr(exc, "code", str(exc))
                        attempts.append(
                            AudioAttempt(
                                backend=adapter.backend,
                                rate_profile=rate.value,
                                succeeded=False,
                                safe_error_code="audio_duration_invalid"
                                if code == "duration_out_of_range"
                                else "audio_invalid",
                            )
                        )
                        _safe_unlink(candidate_path)
                        _safe_unlink(final_path)
                        if code == "duration_out_of_range" and rate is RateProfile.NORMAL:
                            continue
                        break
                    except Exception:
                        attempts.append(
                            AudioAttempt(
                                backend=adapter.backend,
                                rate_profile=rate.value,
                                succeeded=False,
                                safe_error_code="tts_backend_failed",
                            )
                        )
                        _safe_unlink(candidate_path)
                        _safe_unlink(final_path)
                        break
                    attempts.append(
                        AudioAttempt(
                            backend=adapter.backend,
                            rate_profile=rate.value,
                            succeeded=True,
                            duration_ms=final_probe.duration_ms,
                            sha256=final_probe.sha256,
                        )
                    )
                    return AudioResult(
                        identity=self._identity(request),
                        available=True,
                        backend=adapter.backend,
                        fallback_used=backend_index > 0,
                        attempts=tuple(attempts),
                        duration_ms=final_probe.duration_ms,
                        sha256=final_probe.sha256,
                    )
        return AudioResult(
            identity=self._identity(request),
            available=False,
            fallback_used=len({attempt.backend for attempt in attempts}) > 1,
            attempts=tuple(attempts),
            failure=SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="tts"),
        )


class _CandidateInvalid(Exception):
    pass


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        info = path.stat(follow_symlinks=False)
        return (
            not stat.S_ISREG(info.st_mode)
            and not stat.S_ISDIR(info.st_mode)
            or bool(getattr(info, "st_file_attributes", 0) & 0x400)
        )
    except OSError:
        return True


def _safe_unlink(path: Path) -> None:
    with suppress(OSError):
        path.unlink(missing_ok=True)


def _candidate_matches(
    candidate: object,
    *,
    expected_path: Path,
    backend: str,
    rate: RateProfile,
    request: TtsRequestIdentity,
) -> bool:
    if not hasattr(candidate, "path"):
        return False
    value = candidate
    try:
        return (
            value.backend == backend
            and value.rate_profile is rate
            and value.request_identity == request
            and value.path == expected_path
            and expected_path.is_file()
            and not _is_link_or_reparse(expected_path)
            and stat.S_ISREG(expected_path.stat(follow_symlinks=False).st_mode)
        )
    except (AttributeError, OSError):
        return False
