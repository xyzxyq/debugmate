"""Deterministic, privacy-preserving TTS fallback orchestration."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.contracts import (
    ArtifactIdentity,
    AudioAttempt,
    AudioResult,
    SafeFailure,
)
from debugmate.results.media import MediaProbeError, probe_mp3
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
        attempts: list[AudioAttempt] = []
        with tempfile.TemporaryDirectory(prefix="debugmate-tts-", dir=target_root) as temp_name:
            temp = Path(temp_name)
            for backend_index, adapter in enumerate(self._adapters):
                for rate in (RateProfile.NORMAL, RateProfile.FASTER):
                    candidate_path = temp / f"candidate-{backend_index}-{rate.value}.mp3"
                    try:
                        assert_export_safe(recap.text)
                        candidate = adapter.synthesize(recap, candidate_path, request, rate)
                        probe = probe_mp3(
                            candidate.path,
                            timeout_seconds=self._probe_timeout,
                            max_bytes=self._max_bytes,
                        )
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
                        candidate_path.unlink(missing_ok=True)
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
                        candidate_path.unlink(missing_ok=True)
                        break
                    final_path = target_root / "recap.mp3"
                    shutil.copyfile(candidate.path, final_path)
                    attempts.append(
                        AudioAttempt(
                            backend=adapter.backend,
                            rate_profile=rate.value,
                            succeeded=True,
                            duration_ms=probe.duration_ms,
                            sha256=probe.sha256,
                        )
                    )
                    return AudioResult(
                        identity=self._identity(request),
                        available=True,
                        backend=adapter.backend,
                        fallback_used=backend_index > 0,
                        attempts=tuple(attempts),
                        duration_ms=probe.duration_ms,
                        sha256=probe.sha256,
                    )
        return AudioResult(
            identity=self._identity(request),
            available=False,
            fallback_used=len({attempt.backend for attempt in attempts}) > 1,
            attempts=tuple(attempts),
            failure=SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="tts"),
        )
