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
from debugmate.results.tts.validation import validate_tts_request


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
        try:
            recap, request = validate_tts_request(recap, request)
        except Exception:
            raise ValueError("tts_input_invalid") from None
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
        target_root = _prepare_target_root(target_root)
        final_path = target_root / "recap.mp3"
        if final_path.exists() or final_path.is_symlink():
            raise ValueError("tts_target_invalid") from None
        attempts: list[AudioAttempt] = []
        try:
            _require_safe_directory(target_root)
            with tempfile.TemporaryDirectory(prefix="debugmate-tts-", dir=target_root) as temp_name:
                temp = Path(temp_name)
                _require_safe_directory(target_root)
                _require_safe_directory(temp)
                for backend_index, adapter in enumerate(self._adapters):
                    for rate in (RateProfile.NORMAL, RateProfile.FASTER):
                        candidate_path = temp / f"candidate-{backend_index}-{rate.value}.mp3"
                        _require_safe_directory(target_root)
                        _require_safe_directory(temp)
                        _require_safe_new_path(candidate_path, target_root)
                        _require_safe_new_path(final_path, target_root)
                        try:
                            assert_export_safe(recap.text)
                            candidate = adapter.synthesize(recap, candidate_path, request, rate)
                            _require_safe_directory(target_root)
                            _require_safe_directory(temp)
                            if not _candidate_matches(
                                candidate,
                                expected_path=candidate_path,
                                target_root=target_root,
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
                            _require_safe_new_path(final_path, target_root)
                            published_probe = canonicalize_mp3(
                                candidate.path,
                                final_path,
                                timeout_seconds=self._probe_timeout,
                                max_bytes=self._max_bytes,
                            )
                            _require_safe_file_path(final_path, target_root)
                            final_probe = probe_mp3(
                                final_path,
                                timeout_seconds=self._probe_timeout,
                                max_bytes=self._max_bytes,
                            )
                            if final_probe != published_probe:
                                raise _CandidateInvalid
                        except _TargetInvalid:
                            _safe_unlink(candidate_path)
                            _safe_unlink(final_path)
                            raise ValueError("tts_target_invalid") from None
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
        except _TargetInvalid:
            raise ValueError("tts_target_invalid") from None
        return AudioResult(
            identity=self._identity(request),
            available=False,
            fallback_used=len({attempt.backend for attempt in attempts}) > 1,
            attempts=tuple(attempts),
            failure=SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="tts"),
        )


class _CandidateInvalid(Exception):
    pass


class _TargetInvalid(Exception):
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


def _require_safe_directory(path: Path) -> None:
    current = path
    while True:
        try:
            info = current.stat(follow_symlinks=False)
        except OSError:
            raise _TargetInvalid from None
        if not stat.S_ISDIR(info.st_mode) or _is_link_or_reparse(current):
            raise _TargetInvalid
        parent = current.parent
        if parent == current:
            return
        current = parent


def _prepare_target_root(root: Path) -> Path:
    candidate = Path(root)
    if not candidate.is_absolute():
        raise ValueError("tts_target_invalid") from None
    probe = candidate
    while not probe.exists() and not probe.is_symlink():
        parent = probe.parent
        if parent == probe:
            raise ValueError("tts_target_invalid") from None
        probe = parent
    try:
        _require_safe_directory(probe)
        candidate.mkdir(parents=True, exist_ok=True)
        # Recheck the whole resulting path immediately after mkdir to surface a
        # junction/reparse swap before any adapter receives a writable filename.
        _require_safe_directory(candidate)
    except (OSError, _TargetInvalid):
        raise ValueError("tts_target_invalid") from None
    return candidate


def _require_safe_new_path(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError:
        raise _TargetInvalid from None
    _require_safe_directory(path.parent)
    if path.exists() or path.is_symlink():
        raise _TargetInvalid


def _require_safe_file_path(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
        info = path.stat(follow_symlinks=False)
    except (OSError, ValueError):
        raise _TargetInvalid from None
    _require_safe_directory(path.parent)
    if _is_link_or_reparse(path) or not stat.S_ISREG(info.st_mode):
        raise _TargetInvalid


def _safe_unlink(path: Path) -> None:
    with suppress(OSError):
        path.unlink(missing_ok=True)


def _candidate_matches(
    candidate: object,
    *,
    expected_path: Path,
    target_root: Path,
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
            and _safe_candidate_file(expected_path, target_root)
        )
    except (AttributeError, OSError):
        return False


def _safe_candidate_file(path: Path, root: Path) -> bool:
    try:
        _require_safe_file_path(path, root)
    except _TargetInvalid:
        return False
    return True
