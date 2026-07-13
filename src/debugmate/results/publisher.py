"""Atomic, deterministic publication of separately verified result bundles."""

from __future__ import annotations

import os
import re
import shutil
import stat
import zipfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.results.consistency import (
    ResultConsistencyError,
    ValidatedResultCandidates,
    discard_audio_handoff,
    is_issued_result_candidate,
    take_verified_audio_for_publication,
)
from debugmate.results.contracts import (
    ArtifactIdentity,
    ArtifactRecord,
    ResultManifest,
    ResultMode,
    ResultStatus,
)

RESULT_MANIFEST_NAME = "result-manifest.json"
CHECKSUMS_NAME = "checksums.sha256"
PUBLICATION_NAME = "publication.json"
FULL_ARCHIVE_NAME = "debugmate-result.zip"
PARTIAL_ARCHIVE_NAME = "debugmate-result-partial.zip"
MANIFEST_VERSION = "1.0.0"
PUBLICATION_VERSION = "1.0.0"
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
_CASE_ID = re.compile(r"^case_[0-9a-f]{32}$")
_RESULT_ID = re.compile(r"^result_[0-9a-f]{32}$")

_BUSINESS_SPECS = {
    "diagnosis": ("diagnosis.json", "application/json"),
    "report": ("report.md", "text/markdown"),
    "card": ("card.png", "image/png"),
    "recap_text": ("recap.txt", "text/plain"),
    "audio": ("recap.mp3", "audio/mpeg"),
    "citations": ("citations.json", "application/json"),
    "source_manifest": ("source-manifest.json", "application/json"),
}


class ResultPublishError(ValueError):
    """Fixed, non-path-bearing publication rejection."""

    def __init__(self, code: str = "result_publication_failed") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PublishedResultBundle:
    path: Path
    manifest: ResultManifest
    archive_name: str


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400)
    except OSError:
        return True


def _safe_directory(path: Path) -> bool:
    current = path
    while True:
        try:
            info = current.stat(follow_symlinks=False)
        except OSError:
            return False
        if not stat.S_ISDIR(info.st_mode) or _is_link_or_reparse(current):
            return False
        if current == current.parent:
            return True
        current = current.parent


def _safe_file(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        info = path.stat(follow_symlinks=False)
    except (OSError, ValueError):
        return False
    return (
        stat.S_ISREG(info.st_mode)
        and not _is_link_or_reparse(path)
        and _safe_directory(path.parent)
    )


def _prepare_results_root(root: Path) -> Path:
    root = Path(root)
    if not root.is_absolute():
        raise ResultPublishError("results_root_invalid")
    parent = root.parent
    if not _safe_directory(parent):
        raise ResultPublishError("results_root_invalid")
    if root.exists() and (not root.is_dir() or _is_link_or_reparse(root)):
        raise ResultPublishError("results_root_invalid")
    root.mkdir(exist_ok=True)
    if not _safe_directory(root):
        raise ResultPublishError("results_root_invalid")
    return root


def _write_new(path: Path, payload: bytes) -> None:
    if not payload or len(payload) > MAX_MEMBER_BYTES or not _safe_directory(path.parent):
        raise ResultPublishError("result_member_invalid")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o444)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        raise ResultPublishError("result_member_invalid") from None
    if not _safe_file(path, path.parent) or path.stat().st_size != len(payload):
        raise ResultPublishError("result_member_invalid")


def _remove_temporary_tree(path: Path) -> None:
    """Remove only our exclusive, non-reparse transaction directory on Windows too."""

    if not path.exists() or path.is_symlink() or not _safe_directory(path):
        return

    def make_writable(action, target, _exception) -> None:
        try:
            os.chmod(target, stat.S_IWRITE)
            action(target)
        except OSError:
            return

    with suppress(OSError):
        shutil.rmtree(path, onerror=make_writable)


def _candidate_payloads(
    candidate: ValidatedResultCandidates, audio: bytes | None
) -> dict[str, bytes]:
    payloads = {
        "diagnosis": candidate.diagnosis_bytes,
        "report": candidate.report_bytes,
        "recap_text": candidate.recap_bytes,
        "citations": candidate.citations_bytes,
        "source_manifest": candidate.source_manifest_bytes,
    }
    if candidate.availability.card:
        if candidate.card_bytes is None:
            raise ResultPublishError("candidate_card_invalid")
        payloads["card"] = candidate.card_bytes
    if candidate.availability.audio:
        if audio is None:
            raise ResultPublishError("candidate_audio_invalid")
        payloads["audio"] = audio
    elif audio is not None:
        raise ResultPublishError("candidate_audio_invalid")
    if sum(map(len, payloads.values())) > MAX_TOTAL_BYTES:
        raise ResultPublishError("result_too_large")
    return payloads


def _result_id(
    candidate: ValidatedResultCandidates,
    *,
    mode: ResultMode,
    fixture_id: str | None,
    fixture_name: str | None,
) -> str:
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "identity": candidate.identity.model_dump(mode="json"),
        "mode": mode.value,
        "fixture_id": fixture_id,
        "fixture_name": fixture_name,
        "status": candidate.status.value,
        "availability": candidate.availability.model_dump(mode="json"),
        "failure": candidate.failure.model_dump(mode="json") if candidate.failure else None,
        "audio": candidate.audio.model_dump(mode="json"),
        "business": {
            "diagnosis": sha256_bytes(candidate.diagnosis_bytes),
            "report": sha256_bytes(candidate.report_bytes),
            "recap_text": sha256_bytes(candidate.recap_bytes),
            "citations": sha256_bytes(candidate.citations_bytes),
            "source_manifest": sha256_bytes(candidate.source_manifest_bytes),
            "card": sha256_bytes(candidate.card_bytes) if candidate.card_bytes else None,
            "audio": candidate.audio.sha256,
        },
    }
    return f"result_{sha256_bytes(canonical_json_bytes(payload))[:32]}"


def _record(kind: str, payload: bytes, identity: ArtifactIdentity) -> ArtifactRecord:
    path, mime_type = _BUSINESS_SPECS[kind]
    return ArtifactRecord(
        kind=kind,
        path=path,
        mime_type=mime_type,
        bytes=len(payload),
        sha256=sha256_bytes(payload),
        identity=identity,
    )


def _manifest(
    candidate: ValidatedResultCandidates,
    payloads: dict[str, bytes],
    *,
    result_id: str,
    mode: ResultMode,
    fixture_id: str | None,
    fixture_name: str | None,
) -> ResultManifest:
    order = (
        "diagnosis",
        "report",
        "card",
        "recap_text",
        "audio",
        "citations",
        "source_manifest",
    )
    return ResultManifest(
        manifest_version=MANIFEST_VERSION,
        result_id=result_id,
        identity=candidate.identity,
        mode=mode,
        status=candidate.status,
        fixture_id=fixture_id,
        fixture_name=fixture_name,
        availability=candidate.availability,
        artifacts=tuple(
            _record(kind, payloads[kind], candidate.identity) for kind in order if kind in payloads
        ),
        failure=candidate.failure,
        completed_stages=("results_published",),
        audio=candidate.audio,
    )


def _checksums(members: dict[str, bytes]) -> bytes:
    return "".join(f"{sha256_bytes(members[name])}  {name}\n" for name in sorted(members)).encode(
        "ascii"
    )


def _write_archive(path: Path, members: dict[str, bytes]) -> None:
    if set(members) != set(sorted(members)) and len(members) != len(set(members)):
        raise ResultPublishError("archive_member_invalid")
    try:
        with zipfile.ZipFile(
            path,
            mode="x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as archive:
            archive.comment = b""
            for name in sorted(members):
                info = zipfile.ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100444 << 16
                info.extra = b""
                info.comment = b""
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(
                    info,
                    members[name],
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
    except (OSError, ValueError, zipfile.BadZipFile):
        raise ResultPublishError("archive_write_failed") from None


def _publication_bytes(manifest: ResultManifest, archive_name: str, archive_bytes: bytes) -> bytes:
    return canonical_json_bytes(
        {
            "publication_version": PUBLICATION_VERSION,
            "result_id": manifest.result_id,
            "identity": manifest.identity.model_dump(mode="json"),
            "status": manifest.status.value,
            "archive_name": archive_name,
            "archive_sha256": sha256_bytes(archive_bytes),
        }
    )


class ResultBundlePublisher:
    """Create exactly one identity-derived final directory without overwriting it."""

    def __init__(self, results_root: Path, case_id: str, result_identity: ArtifactIdentity) -> None:
        if _CASE_ID.fullmatch(case_id) is None or result_identity.case_id != case_id:
            raise ResultPublishError("result_identity_invalid")
        self.results_root = _prepare_results_root(results_root)
        self.case_id = case_id
        self.result_identity = result_identity

    @classmethod
    def begin(
        cls, results_root: Path, case_id: str, result_identity: ArtifactIdentity
    ) -> ResultBundlePublisher:
        return cls(results_root, case_id, result_identity)

    def publish(
        self,
        candidate: ValidatedResultCandidates,
        *,
        mode: ResultMode,
        fixture_id: str | None,
        fixture_name: str | None,
    ) -> PublishedResultBundle:
        if not is_issued_result_candidate(candidate) or candidate.identity != self.result_identity:
            raise ResultPublishError("candidate_invalid")
        result_id = _result_id(
            candidate, mode=mode, fixture_id=fixture_id, fixture_name=fixture_name
        )
        case_root = self.results_root / self.case_id
        if case_root.exists() and (not case_root.is_dir() or _is_link_or_reparse(case_root)):
            raise ResultPublishError("result_path_invalid")
        case_root.mkdir(exist_ok=True)
        if not _safe_directory(case_root):
            raise ResultPublishError("result_path_invalid")
        final = case_root / result_id
        temporary = case_root / f".tmp-{result_id}"
        if final.exists():
            return _reuse_existing(final, candidate, result_id, mode, fixture_id, fixture_name)
        try:
            temporary.mkdir()
        except FileExistsError:
            raise ResultPublishError("publication_in_progress") from None
        except OSError:
            raise ResultPublishError("result_path_invalid") from None
        try:
            audio = take_verified_audio_for_publication(candidate)
            payloads = _candidate_payloads(candidate, audio)
            manifest = _manifest(
                candidate,
                payloads,
                result_id=result_id,
                mode=mode,
                fixture_id=fixture_id,
                fixture_name=fixture_name,
            )
            by_name = {_BUSINESS_SPECS[kind][0]: payload for kind, payload in payloads.items()}
            for name, payload in sorted(by_name.items()):
                _write_new(temporary / name, payload)
            manifest_bytes = canonical_json_bytes(manifest.model_dump(mode="json"))
            _write_new(temporary / RESULT_MANIFEST_NAME, manifest_bytes)
            archive_members = {**by_name, RESULT_MANIFEST_NAME: manifest_bytes}
            checksums = _checksums(archive_members)
            _write_new(temporary / CHECKSUMS_NAME, checksums)
            archive_name = (
                FULL_ARCHIVE_NAME
                if manifest.status is ResultStatus.COMPLETED
                else PARTIAL_ARCHIVE_NAME
            )
            _write_archive(
                temporary / archive_name,
                {**archive_members, CHECKSUMS_NAME: checksums},
            )
            publication = _publication_bytes(
                manifest, archive_name, (temporary / archive_name).read_bytes()
            )
            _write_new(temporary / PUBLICATION_NAME, publication)
            from debugmate.results.verifier import verify_result_bundle

            verify_result_bundle(temporary, allow_temporary=True)
            try:
                os.replace(temporary, final)
            except FileExistsError:
                return _reuse_existing(final, candidate, result_id, mode, fixture_id, fixture_name)
            return PublishedResultBundle(path=final, manifest=manifest, archive_name=archive_name)
        except ResultPublishError:
            raise
        except ResultConsistencyError:
            raise ResultPublishError("candidate_audio_invalid") from None
        except Exception:
            raise ResultPublishError() from None
        finally:
            _remove_temporary_tree(temporary)
            discard_audio_handoff(candidate)


def _reuse_existing(
    final: Path,
    candidate: ValidatedResultCandidates,
    result_id: str,
    mode: ResultMode,
    fixture_id: str | None,
    fixture_name: str | None,
) -> PublishedResultBundle:
    try:
        from debugmate.results.verifier import verify_result_bundle

        verified = verify_result_bundle(final)
        manifest = verified.manifest
        if (
            manifest.result_id != result_id
            or manifest.identity != candidate.identity
            or manifest.mode is not mode
            or manifest.fixture_id != fixture_id
            or manifest.fixture_name != fixture_name
            or manifest.status is not candidate.status
            or manifest.availability != candidate.availability
            or manifest.failure != candidate.failure
            or manifest.audio != candidate.audio
        ):
            raise ValueError("immutable content differs")
        expected = {
            "diagnosis": sha256_bytes(candidate.diagnosis_bytes),
            "report": sha256_bytes(candidate.report_bytes),
            "recap_text": sha256_bytes(candidate.recap_bytes),
            "citations": sha256_bytes(candidate.citations_bytes),
            "source_manifest": sha256_bytes(candidate.source_manifest_bytes),
            "card": sha256_bytes(candidate.card_bytes) if candidate.card_bytes else None,
            "audio": candidate.audio.sha256,
        }
        if any(
            expected[record.kind] != record.sha256
            for record in manifest.artifacts
            if record.kind in expected
        ):
            raise ValueError("immutable payload differs")
        archive_name = (
            FULL_ARCHIVE_NAME if manifest.status is ResultStatus.COMPLETED else PARTIAL_ARCHIVE_NAME
        )
        discard_audio_handoff(candidate)
        return PublishedResultBundle(path=final, manifest=manifest, archive_name=archive_name)
    except Exception:
        discard_audio_handoff(candidate)
        raise ResultPublishError("result_already_exists") from None


def publish_result_bundle(
    results_root: Path,
    candidate: ValidatedResultCandidates,
    *,
    mode: ResultMode = ResultMode.LIVE,
    fixture_id: str | None = None,
    fixture_name: str | None = None,
) -> PublishedResultBundle:
    """Publish only a consistency-gated candidate into ``results/case/result``."""

    if not is_issued_result_candidate(candidate):
        raise ResultPublishError("candidate_invalid")
    publisher = ResultBundlePublisher.begin(
        results_root, candidate.identity.case_id, candidate.identity
    )
    return publisher.publish(candidate, mode=mode, fixture_id=fixture_id, fixture_name=fixture_name)
