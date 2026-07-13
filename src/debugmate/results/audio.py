"""Deterministic privacy-safe TTS orchestration with a leased output boundary."""

from __future__ import annotations

import os
import secrets
import stat
import threading
import weakref
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from debugmate.hashing import sha256_bytes
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.contracts import ArtifactIdentity, AudioAttempt, AudioResult, SafeFailure
from debugmate.results.media import MediaProbe, MediaProbeError, canonicalize_mp3_bytes, probe_mp3
from debugmate.results.recap import SafeRecapText
from debugmate.results.tts.base import AudioPayload, RateProfile, TtsAdapter, TtsRequestIdentity
from debugmate.results.tts.validation import validate_tts_request

# Deliberately narrow indirection points for deterministic tests.  Both have a
# bytes-only contract; no caller path can re-enter the adapter boundary.
canonicalize_mp3 = canonicalize_mp3_bytes


class AudioHandoffError(ValueError):
    """Fixed, value-free refusal from the private audio-to-publisher boundary."""

    def __init__(self) -> None:
        super().__init__("audio_handoff_invalid")


@dataclass(frozen=True, slots=True)
class TtsSynthesisOutcome:
    """The public JSON-safe audio record plus one private successful handoff.

    ``audio`` remains the unmodified :class:`AudioResult` contract.  The
    capability is intentionally not serialisable and is present only for one
    successful synthesis.  Plan 05 can consume it once to copy freshly
    revalidated canonical bytes into its separate transaction.
    """

    audio: AudioResult
    handoff: AudioHandoff | None

    def __post_init__(self) -> None:
        if self.audio.available != (self.handoff is not None):
            raise ValueError("tts_outcome_invalid")


@dataclass(slots=True)
class _RegisteredAudioHandoff:
    """All mutable capability state kept outside the public handoff object."""

    owner_ref: weakref.ReferenceType[AudioHandoff]
    audio: AudioResult
    candidate: _MaterializedAudio
    lease: _CandidateRootLease
    probe_timeout: float
    max_bytes: int


_AUDIO_HANDOFF_LOCK = threading.RLock()
_AUDIO_HANDOFFS: dict[object, _RegisteredAudioHandoff] = {}


def _release_registered_audio_handoff(state: _RegisteredAudioHandoff) -> None:
    """Release private resources without surfacing cleanup data or failures."""

    with suppress(Exception):
        state.candidate.file.close()
    with suppress(Exception):
        _safe_unlink(state.candidate.file.path, state.candidate.root)
    with suppress(Exception):
        state.lease.close()


def _discard_abandoned_audio_handoff(token: object) -> None:
    """Weakref callback target: remove an unconsumed state before it can leak."""

    try:
        with _AUDIO_HANDOFF_LOCK:
            state = _AUDIO_HANDOFFS.pop(token, None)
    except Exception:  # pragma: no cover - interpreter shutdown hygiene
        return
    if state is not None:
        _release_registered_audio_handoff(state)


def _handoff_finalizer(token: object):
    def finalize(_owner: object) -> None:
        _discard_abandoned_audio_handoff(token)

    return finalize


def _registered_handoff_state(
    handoff: AudioHandoff, *, audio: AudioResult | None = None, consume: bool
) -> _RegisteredAudioHandoff | None:
    """Get the private state only for its original object and exact public result."""

    try:
        token = object.__getattribute__(handoff, "_token")
        with _AUDIO_HANDOFF_LOCK:
            state = _AUDIO_HANDOFFS.get(token)
            if state is None or state.owner_ref() is not handoff:
                return None
            if audio is not None and audio is not state.audio:
                return None
            if consume:
                _AUDIO_HANDOFFS.pop(token, None)
            return state
    except (AttributeError, TypeError):
        return None


class AudioHandoff:
    """Opaque, one-shot authority to copy one retained canonical MP3.

    No raw directory or file path is exposed.  A caller must pass the exact
    ``AudioResult`` object returned by the same outcome; equal copied or forged
    models are deliberately rejected.  The private file, run and root leases
    stay held until this one read is complete.
    """

    __slots__ = ("_token", "__weakref__")

    def __init__(self, *_arguments: object, **_keyword_arguments: object) -> None:
        raise TypeError("AudioHandoff requires an approved factory")

    @classmethod
    def _issue(
        cls,
        audio: AudioResult,
        candidate: _MaterializedAudio,
        lease: _CandidateRootLease,
        *,
        probe_timeout: float,
        max_bytes: int,
    ) -> AudioHandoff:
        handoff = object.__new__(cls)
        token = object()
        object.__setattr__(handoff, "_token", token)
        state = _RegisteredAudioHandoff(
            owner_ref=weakref.ref(handoff, _handoff_finalizer(token)),
            audio=audio,
            candidate=candidate,
            lease=lease,
            probe_timeout=probe_timeout,
            max_bytes=max_bytes,
        )
        with _AUDIO_HANDOFF_LOCK:
            _AUDIO_HANDOFFS[token] = state
        return handoff

    def __repr__(self) -> str:
        state = _registered_handoff_state(self, consume=False)
        return "<AudioHandoff active>" if state is not None else "<AudioHandoff released>"

    def __copy__(self) -> AudioHandoff:
        raise TypeError("AudioHandoff is not copyable")

    def __deepcopy__(self, _memo: object) -> AudioHandoff:
        raise TypeError("AudioHandoff is not copyable")

    def __reduce_ex__(self, _protocol: int) -> object:
        raise TypeError("AudioHandoff is not serialisable")

    def __reduce__(self) -> object:
        raise TypeError("AudioHandoff is not serialisable")

    def __getstate__(self) -> object:
        raise TypeError("AudioHandoff is not serialisable")

    def take_verified_bytes(self, audio: AudioResult) -> bytes:
        """Return one freshly re-probed/hash-checked copy and release the lease."""

        state = _registered_handoff_state(self, audio=audio, consume=True)
        if state is None:
            raise AudioHandoffError
        payload: bytes | None = None
        try:
            candidate = state.candidate
            candidate.file.assert_same_path_identity(candidate.root)
            probe = probe_mp3(
                candidate.file.path,
                timeout_seconds=state.probe_timeout,
                max_bytes=state.max_bytes,
            )
            candidate.file.assert_same_path_identity(candidate.root)
            if (
                probe.duration_ms != state.audio.duration_ms
                or probe.sha256 != state.audio.sha256
                or probe.bytes <= 0
            ):
                raise _TargetInvalid
            payload = candidate.file.read_all(state.max_bytes)
            candidate.file.assert_same_path_identity(candidate.root)
            if len(payload) != probe.bytes or sha256_bytes(payload) != probe.sha256:
                raise _TargetInvalid
        except Exception:
            payload = None
        finally:
            _release_registered_audio_handoff(state)
        if payload is None:
            raise AudioHandoffError
        return payload

    def close(self) -> None:
        """Release every private resource without revealing cleanup values."""

        state = _registered_handoff_state(self, consume=True)
        if state is not None:
            _release_registered_audio_handoff(state)


class TtsFallbackChain:
    """Run Dify, edge and SAPI in order without exposing a writable path.

    Adapters return bounded bytes.  Verification and canonicalisation stay on
    stdin/stdout bytes, then this class writes the one canonical MP3 through a
    `CREATE_NEW` handle in an application-owned leased directory.
    """

    def __init__(
        self,
        adapters: tuple[TtsAdapter, ...],
        *,
        probe_timeout: float = 15.0,
        max_bytes: int = 8_000_000,
    ) -> None:
        if tuple(adapter.backend for adapter in adapters) != ("dify", "edge_tts", "sapi"):
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
    ) -> TtsSynthesisOutcome:
        if not isinstance(candidate_root, TrustedCandidateRoot):
            raise TypeError("candidate_root must be a TrustedCandidateRoot")
        try:
            recap, request = validate_tts_request(recap, request)
        except Exception:
            raise ValueError("tts_input_invalid") from None
        if not _request_matches_recap(recap, request):
            raise ValueError("tts_identity_mismatch") from None
        try:
            assert_export_safe(recap.text)
        except Exception:
            raise ValueError("tts_input_invalid") from None
        lease = candidate_root.allocate_leased(request)
        try:
            outcome = self._synthesize_in_leased_root(recap, request, lease)
        except Exception:
            lease.close()
            raise
        if outcome.handoff is None:
            lease.close()
        return outcome

    def _synthesize_in_leased_root(
        self, recap: SafeRecapText, request: TtsRequestIdentity, lease: _CandidateRootLease
    ) -> TtsSynthesisOutcome:
        target_root = lease.path
        final_path = target_root / "recap.mp3"
        attempts: list[AudioAttempt] = []
        try:
            _require_safe_directory(target_root)
            for backend_index, adapter in enumerate(self._adapters):
                for rate in (RateProfile.NORMAL, RateProfile.FASTER):
                    try:
                        assert_export_safe(recap.text)
                        payload = adapter.synthesize(recap, request, rate)
                        _require_valid_payload(
                            payload, adapter.backend, rate, request, self._max_bytes
                        )
                        candidate = _materialize_verified_audio(
                            payload.audio_bytes,
                            candidate_path=target_root
                            / f"candidate-{backend_index}-{rate.value}.mp3",
                            final_path=final_path,
                            root=target_root,
                            timeout_seconds=self._probe_timeout,
                            max_bytes=self._max_bytes,
                        )
                    except _TargetInvalid:
                        raise ValueError("tts_target_invalid") from None
                    except _PayloadInvalid:
                        attempts.append(
                            AudioAttempt(
                                backend=adapter.backend,
                                rate_profile=rate.value,
                                succeeded=False,
                                safe_error_code="tts_candidate_invalid",
                            )
                        )
                        break
                    except MediaProbeError as exc:
                        code = exc.code
                        attempts.append(
                            AudioAttempt(
                                backend=adapter.backend,
                                rate_profile=rate.value,
                                succeeded=False,
                                safe_error_code=(
                                    "audio_duration_invalid"
                                    if code == "duration_out_of_range"
                                    else "audio_invalid"
                                ),
                            )
                        )
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
                        break
                    attempts.append(
                        AudioAttempt(
                            backend=adapter.backend,
                            rate_profile=rate.value,
                            succeeded=True,
                            duration_ms=candidate.probe.duration_ms,
                            sha256=candidate.probe.sha256,
                        )
                    )
                    audio = AudioResult(
                        identity=self._identity(request),
                        available=True,
                        backend=adapter.backend,
                        fallback_used=backend_index > 0,
                        attempts=tuple(attempts),
                        duration_ms=candidate.probe.duration_ms,
                        sha256=candidate.probe.sha256,
                    )
                    return TtsSynthesisOutcome(
                        audio=audio,
                        handoff=AudioHandoff._issue(
                            audio,
                            candidate,
                            lease,
                            probe_timeout=self._probe_timeout,
                            max_bytes=self._max_bytes,
                        ),
                    )
        except _TargetInvalid:
            raise ValueError("tts_target_invalid") from None
        return TtsSynthesisOutcome(
            audio=AudioResult(
                identity=self._identity(request),
                available=False,
                fallback_used=len({attempt.backend for attempt in attempts}) > 1,
                attempts=tuple(attempts),
                failure=SafeFailure(code="tts_failed", failed_stage="audio", retry_scope="tts"),
            ),
            handoff=None,
        )


def _request_matches_recap(recap: SafeRecapText, request: TtsRequestIdentity) -> bool:
    return (
        recap.sha256 == request.recap_sha256
        and recap.identity.case_id == request.case_id
        and recap.identity.source_run_id == request.source_run_id
        and recap.identity.diagnosis_sha256 == request.diagnosis_sha256
        and recap.identity.generation_version == request.generation_version
    )


def _require_valid_payload(
    payload: object,
    backend: str,
    rate: RateProfile,
    request: TtsRequestIdentity,
    max_bytes: int,
) -> None:
    if not isinstance(payload, AudioPayload):
        raise _PayloadInvalid
    if (
        payload.backend != backend
        or payload.rate_profile is not rate
        or payload.request_identity != request
        or not payload.audio_bytes
        or len(payload.audio_bytes) > max_bytes
    ):
        raise _PayloadInvalid


_CANDIDATE_ROOT_CAPABILITY = object()


@dataclass(frozen=True, init=False)
class TrustedCandidateRoot:
    """Factory-issued authority for the private, pre-publication audio area."""

    _root: Path

    def __init__(self, root: Path, *, _capability: object) -> None:
        if _capability is not _CANDIDATE_ROOT_CAPABILITY:
            raise TypeError("TrustedCandidateRoot requires an approved factory")
        object.__setattr__(self, "_root", Path(root))

    @classmethod
    def application_owned(cls) -> TrustedCandidateRoot:
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
        root_lease: _DirectoryLease | None = None
        run_lease: _DirectoryLease | None = None
        try:
            _prepare_private_candidate_root(self._root)
            root_lease = _acquire_directory_lease(self._root)
            _require_safe_directory(self._root)
            run = self._root / f"tts-{request.recap_sha256[:16]}-{secrets.token_hex(8)}"
            run.mkdir()
            _require_safe_directory(self._root)
            _require_safe_directory(run)
            run_lease = _acquire_directory_lease(run)
            _require_safe_directory(self._root)
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
        self.close()

    def close(self) -> None:
        self.run_lease.close()
        self.root_lease.close()


def _acquire_directory_lease(path: Path) -> _DirectoryLease:
    """Hold an existing directory without delete sharing while synthesis runs."""

    _require_safe_directory(path)
    if os.name != "nt":
        return _DirectoryLease(handle=None)
    try:
        import ctypes

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
            0x80000000 | 0x00010000,  # GENERIC_READ | DELETE
            0x00000001 | 0x00000002,  # share read/write, deny delete
            None,
            3,  # OPEN_EXISTING
            0x02000000 | 0x00200000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise OSError
        lease = _DirectoryLease(handle=int(handle))
        try:
            _require_safe_directory(path)
            return lease
        except Exception:
            lease.close()
            raise
    except (AttributeError, OSError, ValueError):
        raise _TargetInvalid from None


@dataclass
class _LeasedCandidateFile:
    path: Path
    descriptor: int

    def write(self, payload: bytes) -> None:
        view = memoryview(payload)
        while view:
            written = os.write(self.descriptor, view)
            if written <= 0:
                raise OSError
            view = view[written:]
        os.fsync(self.descriptor)
        if os.fstat(self.descriptor).st_size != len(payload):
            raise OSError

    def assert_same_path_identity(self, root: Path) -> None:
        """Prove the pathname still denotes this held regular file."""

        _require_safe_file_path(self.path, root)
        held = os.fstat(self.descriptor)
        current = self.path.stat(follow_symlinks=False)
        if (
            held.st_dev != current.st_dev
            or held.st_ino != current.st_ino
            or held.st_size != current.st_size
        ):
            raise _TargetInvalid

    def read_all(self, max_bytes: int) -> bytes:
        """Read the same held file handle; never reopen a candidate pathname."""

        if max_bytes <= 0:
            raise OSError
        os.lseek(self.descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(self.descriptor, min(64 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise OSError
            chunks.append(chunk)
        return b"".join(chunks)

    def close(self) -> None:
        descriptor, self.descriptor = self.descriptor, -1
        if descriptor >= 0:
            with suppress(OSError):
                os.close(descriptor)

    def __enter__(self) -> _LeasedCandidateFile:
        return self

    def __exit__(self, *_arguments: object) -> None:
        self.close()


@dataclass
class _MaterializedAudio:
    """Private final file retained under its open descriptor until publication."""

    file: _LeasedCandidateFile
    root: Path
    probe: MediaProbe


def _allocate_new_leased_file(path: Path, root: Path) -> _LeasedCandidateFile:
    """Allocate a non-reparse regular file with `CREATE_NEW`, never overwrite."""

    _require_safe_new_path(path, root)
    try:
        if os.name != "nt":
            flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            return _LeasedCandidateFile(path=path, descriptor=os.open(path, flags, 0o600))
        import ctypes
        import msvcrt

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
            0x80000000 | 0x40000000,  # READ | WRITE; sharing denies DELETE/WRITE
            0x00000001,  # sharing read allows ffprobe only, never write/delete
            None,
            1,  # CREATE_NEW
            0x00000080 | 0x00200000,  # NORMAL | OPEN_REPARSE_POINT
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle in (None, invalid):
            raise OSError
        descriptor = msvcrt.open_osfhandle(int(handle), os.O_BINARY)
        return _LeasedCandidateFile(path=path, descriptor=descriptor)
    except (AttributeError, OSError, ValueError):
        raise _TargetInvalid from None


def _materialize_verified_audio(
    payload: bytes,
    *,
    candidate_path: Path,
    final_path: Path,
    root: Path,
    timeout_seconds: float,
    max_bytes: int,
):
    """Verify a leased candidate and publish one canonical MP3 safely.

    Both candidate and final files are `CREATE_NEW`, regular and non-reparse.
    Their open handles deny write/delete sharing while ffprobe runs.  FFmpeg
    itself receives the candidate bytes on stdin and returns bytes on stdout.
    """

    final: _LeasedCandidateFile | None = None
    final_created = False
    try:
        with _allocate_new_leased_file(candidate_path, root) as candidate:
            candidate.write(payload)
            candidate.assert_same_path_identity(root)
            probe_mp3(candidate_path, timeout_seconds=timeout_seconds, max_bytes=max_bytes)
            candidate.assert_same_path_identity(root)
            canonical_bytes = canonicalize_mp3(
                candidate.read_all(max_bytes),
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
            )
            final = _allocate_new_leased_file(final_path, root)
            final.write(canonical_bytes)
            final.assert_same_path_identity(root)
            final_probe = probe_mp3(
                final_path, timeout_seconds=timeout_seconds, max_bytes=max_bytes
            )
            final.assert_same_path_identity(root)
            final_created = True
        return _MaterializedAudio(file=final, root=root, probe=final_probe)
    finally:
        _safe_unlink(candidate_path, root)
        if not final_created:
            if final is not None:
                final.close()
            _safe_unlink(final_path, root)


class _PayloadInvalid(Exception):
    pass


class _TargetInvalid(Exception):
    pass


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        info = path.stat(follow_symlinks=False)
        return (
            (not stat.S_ISREG(info.st_mode) and not stat.S_ISDIR(info.st_mode))
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
    """Delete only a freshly checked private regular file after its handle closes."""

    try:
        _require_safe_file_path(path, root)
        path.unlink()
    except (OSError, _TargetInvalid):
        return
