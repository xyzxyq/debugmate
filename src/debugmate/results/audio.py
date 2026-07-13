"""Deterministic, privacy-preserving TTS fallback orchestration."""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
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
        self,
        recap: SafeRecapText,
        request: TtsRequestIdentity,
        candidate_root: TrustedCandidateRoot,
    ) -> AudioResult:
        if not isinstance(candidate_root, TrustedCandidateRoot):
            raise TypeError("candidate_root must be a TrustedCandidateRoot")
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
        with candidate_root.allocate_leased(request) as target_root:
            return self._synthesize_in_private_root(recap, request, target_root)

    def _synthesize_in_private_root(
        self, recap: SafeRecapText, request: TtsRequestIdentity, target_root: Path
    ) -> AudioResult:
        final_path = target_root / "recap.mp3"
        if final_path.exists() or final_path.is_symlink():
            raise ValueError("tts_target_invalid") from None
        attempts: list[AudioAttempt] = []
        try:
            _require_safe_directory(target_root)
            with _allocate_leased_temp_directory(target_root) as temp:
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
                            _safe_unlink(candidate_path, target_root)
                            _safe_unlink(final_path, target_root)
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
                            _safe_unlink(candidate_path, target_root)
                            _safe_unlink(final_path, target_root)
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
                            _safe_unlink(candidate_path, target_root)
                            _safe_unlink(final_path, target_root)
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
                            _safe_unlink(candidate_path, target_root)
                            _safe_unlink(final_path, target_root)
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


_CANDIDATE_ROOT_CAPABILITY = object()


@dataclass(frozen=True, init=False)
class TrustedCandidateRoot:
    """An explicit capability for private, pre-publication TTS candidates.

    ``TtsFallbackChain`` deliberately accepts this object rather than a caller
    path.  The Phase 5 publisher will copy a freshly verified candidate into its
    separate immutable result transaction; speech synthesis itself never writes
    directly to a publish root selected by a UI or API caller.

    ``for_testing`` is the only injectable constructor.  It is intentionally
    explicit so tests can use isolated temporary storage without restoring the
    unsafe raw-``Path`` synthesis API.
    """

    _root: Path

    def __init__(self, root: Path, *, _capability: object) -> None:
        if _capability is not _CANDIDATE_ROOT_CAPABILITY:
            raise TypeError("TrustedCandidateRoot requires an approved factory")
        object.__setattr__(self, "_root", Path(root))

    @classmethod
    def application_owned(cls) -> TrustedCandidateRoot:
        """Return the fixed repository-owned private candidate space."""

        project_root = Path(__file__).resolve().parents[3]
        return cls(
            project_root / ".debugmate-private" / "tts-candidates",
            _capability=_CANDIDATE_ROOT_CAPABILITY,
        )

    @classmethod
    def for_testing(cls, private_root: Path) -> TrustedCandidateRoot:
        root = Path(private_root)
        if not root.is_absolute():
            raise ValueError("tts_target_invalid") from None
        return cls(root, _capability=_CANDIDATE_ROOT_CAPABILITY)

    def allocate_leased(self, request: TtsRequestIdentity) -> _CandidateRootLease:
        """Allocate and lock one identity-derived private candidate directory."""

        root = self._root
        root_lease: _DirectoryLease | None = None
        run_lease: _DirectoryLease | None = None
        try:
            _prepare_private_candidate_root(root)
            root_lease = _acquire_directory_lease(root)
            _require_safe_directory(root)
            # The recap hash is part of the request identity and gives a stable
            # hand-off name without accepting a caller-provided directory name.
            run = root / f"tts-{request.recap_sha256[:32]}"
            if run.exists() or run.is_symlink():
                raise _TargetInvalid
            run.mkdir()
            _require_safe_directory(root)
            _require_safe_directory(run)
            run_lease = _acquire_directory_lease(run)
            _require_safe_directory(root)
            _require_safe_directory(run)
            return _CandidateRootLease(path=run, root_lease=root_lease, run_lease=run_lease)
        except (OSError, _TargetInvalid):
            if run_lease is not None:
                run_lease.close()
            if root_lease is not None:
                root_lease.close()
            raise ValueError("tts_target_invalid") from None


@dataclass
class _DirectoryLease:
    """A Windows directory handle that denies delete/rename while active."""

    handle: int | None

    def close(self) -> None:
        if self.handle is None:
            return
        handle, self.handle = self.handle, None
        if os.name == "nt":
            try:
                import ctypes

                ctypes.windll.kernel32.CloseHandle(handle)
            except (AttributeError, OSError):
                pass


@dataclass
class _CandidateRootLease:
    path: Path
    root_lease: _DirectoryLease
    run_lease: _DirectoryLease

    def __enter__(self) -> Path:
        return self.path

    def __exit__(self, *_arguments: object) -> None:
        self.run_lease.close()
        self.root_lease.close()


def _acquire_directory_lease(path: Path) -> _DirectoryLease:
    """Hold a directory open without DELETE sharing for the candidate operation."""

    _require_safe_directory(path)
    if os.name != "nt":
        return _DirectoryLease(handle=None)
    try:
        import ctypes

        generic_read = 0x80000000
        delete = 0x00010000
        file_share_read_write = 0x00000001 | 0x00000002
        open_existing = 3
        file_flag_backup_semantics = 0x02000000
        file_flag_open_reparse_point = 0x00200000
        create_file = ctypes.windll.kernel32.CreateFileW
        create_file.argtypes = (
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        )
        create_file.restype = ctypes.c_void_p
        handle = create_file(
            str(path),
            generic_read | delete,
            file_share_read_write,
            None,
            open_existing,
            file_flag_backup_semantics | file_flag_open_reparse_point,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle in (None, invalid_handle):
            raise OSError
        lease = _DirectoryLease(handle=int(handle))
        try:
            # Recheck after acquiring the non-delete handle.  A successful
            # reparse-free check now remains stable for the lifetime of lease.
            _require_safe_directory(path)
            return lease
        except Exception:
            lease.close()
            raise
    except (AttributeError, OSError, ValueError):
        raise _TargetInvalid from None


@dataclass
class _LeasedTempDirectory:
    """A private temporary child whose exact directory stays non-renamable."""

    path: Path
    lease: _DirectoryLease

    def __enter__(self) -> Path:
        return self.path

    def __exit__(self, *_arguments: object) -> None:
        # Never delegate to ``TemporaryDirectory.cleanup()``: after a directory
        # substitution it may invoke recursive removal on an attacker-selected
        # reparse point. The active no-delete lease makes this exact child stable
        # while we remove only direct, regular files we can still prove are safe.
        _cleanup_leased_temp_directory(self.path, self.lease)
        self.lease.close()


def _allocate_leased_temp_directory(root: Path) -> _LeasedTempDirectory:
    """Create and lease a temp child before exposing any adapter target path."""

    temp: Path | None = None
    lease: _DirectoryLease | None = None
    try:
        _require_safe_directory(root)
        temp = Path(tempfile.mkdtemp(prefix="debugmate-tts-", dir=root))
        _require_safe_directory(root)
        _require_safe_directory(temp)
        lease = _acquire_directory_lease(temp)
        _require_safe_directory(root)
        _require_safe_directory(temp)
        return _LeasedTempDirectory(path=temp, lease=lease)
    except (OSError, _TargetInvalid):
        if lease is not None:
            lease.close()
        # If the initial create/lease handoff was attacked, intentionally leave
        # the uncertain directory in the private root rather than recursively
        # traversing an untrusted reparse point during cleanup.
        raise _TargetInvalid from None


def _cleanup_leased_temp_directory(path: Path, lease: _DirectoryLease) -> None:
    """Best-effort, non-recursive cleanup while the original child is leased."""

    try:
        _require_safe_directory(path)
        entries = tuple(path.iterdir())
        for entry in entries:
            _require_safe_directory(path)
            _require_safe_file_path(entry, path)
            entry.unlink()
        _require_safe_directory(path)
        _mark_leased_empty_directory_for_deletion(path, lease)
    except (OSError, _TargetInvalid):
        # Cleanup failure is deliberately value-free and cannot change a
        # synthesis result. Leaving a private orphan is safer than following a
        # substituted directory or exposing an OS error/path to the caller.
        return


def _mark_leased_empty_directory_for_deletion(path: Path, lease: _DirectoryLease) -> None:
    """Delete only the leased empty directory; never reopen an untrusted path."""

    if os.name != "nt":
        try:
            path.rmdir()
        except OSError:
            return
        return
    if lease.handle is None:
        return
    try:
        import ctypes

        # FileDispositionInfo marks the already-open, DELETE-capable directory
        # for removal once its non-delete lease closes. No second path lookup or
        # recursive deletion is performed after the lease is released.
        file_disposition_info = 4
        delete_file = ctypes.c_byte(1)
        set_information = ctypes.windll.kernel32.SetFileInformationByHandle
        set_information.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint32,
        )
        set_information.restype = ctypes.c_int
        if not set_information(
            ctypes.c_void_p(lease.handle),
            file_disposition_info,
            ctypes.byref(delete_file),
            ctypes.sizeof(delete_file),
        ):
            return
    except (AttributeError, OSError, ValueError):
        return


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


def _prepare_private_candidate_root(candidate: Path) -> None:
    """Prepare the capability-owned root; never create a caller publish path."""

    if not candidate.is_absolute():
        raise _TargetInvalid
    probe = candidate
    while not probe.exists() and not probe.is_symlink():
        parent = probe.parent
        if parent == probe:
            raise _TargetInvalid
        probe = parent
    _require_safe_directory(probe)
    candidate.mkdir(parents=True, exist_ok=True)
    # Recheck the whole resulting path immediately after mkdir to surface a
    # junction/reparse swap before any adapter receives a writable filename.
    _require_safe_directory(candidate)


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


def _safe_unlink(path: Path, root: Path) -> None:
    """Remove only a proven regular candidate; never follow a reparse point."""

    try:
        _require_safe_file_path(path, root)
        path.unlink()
    except (OSError, _TargetInvalid):
        return


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
