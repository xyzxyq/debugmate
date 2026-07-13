"""Fresh, public on-disk verification for immutable DebugMate result bundles."""

from __future__ import annotations

import io
import json
import os
import re
import stat
import threading
import weakref
import zipfile
import zlib
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from pydantic import ValidationError

from debugmate.contracts import DiagnosisRecord
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.card import verify_card_png
from debugmate.results.contracts import ResultManifest, ResultStatus
from debugmate.results.loader import NodeStateEntry, SourceManifestSummary
from debugmate.results.media import probe_mp3
from debugmate.results.publisher import (
    _BUSINESS_SPECS,
    _CASE_ID,
    _RESULT_ID,
    CHECKSUMS_NAME,
    FULL_ARCHIVE_NAME,
    MANIFEST_VERSION,
    MAX_ARCHIVE_BYTES,
    MAX_MEMBER_BYTES,
    MAX_TOTAL_BYTES,
    PARTIAL_ARCHIVE_NAME,
    PUBLICATION_NAME,
    PUBLICATION_VERSION,
    RESULT_MANIFEST_NAME,
)
from debugmate.results.report import CitationRow


class ResultVerificationError(ValueError):
    """Fixed rejection that never includes a file path, provider body or secret."""

    def __init__(self, code: str = "result_bundle_invalid") -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class VerifiedResultBundle:
    path: Path
    manifest: ResultManifest
    publication: dict[str, object]


@dataclass(slots=True)
class _VerifiedDownloadState:
    owner_ref: weakref.ReferenceType[VerifiedDownload]
    payload: bytes
    member_id: str
    filename: str
    mime_type: str
    identity: object


_DOWNLOAD_LOCK = threading.RLock()
_DOWNLOAD_STATES: dict[object, _VerifiedDownloadState] = {}


class VerifiedDownload:
    """Opaque, one-shot bytes from a freshly reverified bundle member.

    It intentionally has no filesystem path.  The returned bytes are read and
    hash-checked while the verifier owns the operation, so a caller cannot
    re-open a swapped server file after its authorization decision.
    """

    __slots__ = ("_token", "__weakref__")

    def __init__(self, *_arguments: object, **_kwargs: object) -> None:
        raise TypeError("VerifiedDownload requires the resolver")

    @classmethod
    def _issue(
        cls, *, payload: bytes, member_id: str, filename: str, mime_type: str, identity: object
    ) -> VerifiedDownload:
        value = object.__new__(cls)
        token = object()
        object.__setattr__(value, "_token", token)

        def forget(reference: weakref.ReferenceType[VerifiedDownload]) -> None:
            with _DOWNLOAD_LOCK:
                state = _DOWNLOAD_STATES.get(token)
                if state is not None and state.owner_ref is reference:
                    _DOWNLOAD_STATES.pop(token, None)

        reference = weakref.ref(value, forget)
        with _DOWNLOAD_LOCK:
            _DOWNLOAD_STATES[token] = _VerifiedDownloadState(
                owner_ref=reference,
                payload=payload,
                member_id=member_id,
                filename=filename,
                mime_type=mime_type,
                identity=identity,
            )
        return value

    def _state(self, *, consume: bool) -> _VerifiedDownloadState:
        try:
            token = object.__getattribute__(self, "_token")
            with _DOWNLOAD_LOCK:
                state = _DOWNLOAD_STATES.get(token)
                if state is None or state.owner_ref() is not self:
                    raise ValueError("download capability")
                if consume:
                    _DOWNLOAD_STATES.pop(token, None)
                return state
        except Exception:
            raise ResultVerificationError("download_invalid") from None

    @property
    def member_id(self) -> str:
        return self._state(consume=False).member_id

    @property
    def filename(self) -> str:
        return self._state(consume=False).filename

    @property
    def mime_type(self) -> str:
        return self._state(consume=False).mime_type

    def read_bytes(self) -> bytes:
        """Consume the already-verified byte copy exactly once."""

        return self._state(consume=True).payload

    def __copy__(self) -> VerifiedDownload:
        raise TypeError("VerifiedDownload is not copyable")

    def __deepcopy__(self, _memo: object) -> VerifiedDownload:
        raise TypeError("VerifiedDownload is not copyable")

    def __reduce__(self) -> object:
        raise TypeError("VerifiedDownload is not serialisable")

    def __reduce_ex__(self, _protocol: int) -> object:
        raise TypeError("VerifiedDownload is not serialisable")


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


def _canonical_model(raw: bytes) -> ResultManifest:
    try:
        manifest = ResultManifest.model_validate_json(raw, strict=True)
        if raw != canonical_json_bytes(manifest.model_dump(mode="json")):
            raise ValueError("noncanonical")
        return manifest
    except (ValidationError, ValueError, TypeError, json.JSONDecodeError):
        raise ResultVerificationError("result_manifest_invalid") from None


def _mask_known_identifiers(value: str) -> str:
    return re.sub(
        r"(?:case|run|fact|evidence|candidate)_[0-9a-f]{32}|gen_[0-9a-f]{32}|[0-9a-f]{64}",
        "VERIFIED_IDENTIFIER",
        value,
    )


def _assert_safe_text(value: bytes) -> str:
    try:
        text = value.decode("utf-8")
        assert_export_safe(_mask_known_identifiers(text))
        return text
    except Exception:
        raise ResultVerificationError("result_privacy_invalid") from None


def _business_records(manifest: ResultManifest) -> dict[str, object]:
    expected = {"diagnosis", "report", "recap_text", "citations", "source_manifest"}
    if manifest.availability.card:
        expected.add("card")
    if manifest.availability.audio:
        expected.add("audio")
    actual = {record.kind for record in manifest.artifacts}
    if actual != expected:
        raise ResultVerificationError("result_member_invalid")
    records = {record.kind: record for record in manifest.artifacts}
    for kind, record in records.items():
        expected_path, expected_mime = _BUSINESS_SPECS[kind]
        if record.path != expected_path or record.mime_type != expected_mime:
            raise ResultVerificationError("result_member_invalid")
    return records


def _expected_citation_rows(diagnosis: DiagnosisRecord) -> tuple[CitationRow, ...]:
    """Rebuild citation evidence/fact/candidate relationships from diagnosis.

    The source summary alone cannot prove a rendered URL or support edge.  The
    committed diagnosis is itself manifest-hashed and schema-validated, so it
    is the authoritative graph for public citation rows during disk restore.
    """

    fact_ids = {item.fact_id for item in diagnosis.observed_facts}
    evidence_ids = {item.evidence_id for item in diagnosis.evidence}
    if len(fact_ids) != len(diagnosis.observed_facts) or len(evidence_ids) != len(
        diagnosis.evidence
    ):
        raise ResultVerificationError("citation_verify_failed")
    links = tuple(diagnosis.support_links)
    for link in links:
        if (
            not link.fact_ids
            or not link.evidence_ids
            or len(link.fact_ids) != len(set(link.fact_ids))
            or len(link.evidence_ids) != len(set(link.evidence_ids))
            or not set(link.fact_ids) <= fact_ids
            or not set(link.evidence_ids) <= evidence_ids
        ):
            raise ResultVerificationError("citation_verify_failed")

    rows: list[CitationRow] = []
    for evidence in sorted(diagnosis.evidence, key=lambda value: value.evidence_id):
        supported_facts = tuple(
            sorted(
                {
                    fact_id
                    for link in links
                    if evidence.evidence_id in link.evidence_ids
                    for fact_id in link.fact_ids
                }
            )
        )
        supported_candidates: list[str] = []
        for candidate in diagnosis.root_cause_candidates:
            if (
                candidate.claim_kind.value != "grounded"
                or evidence.evidence_id not in candidate.evidence_ids
            ):
                continue
            matching_edges = sum(
                1
                for link in links
                if set(candidate.fact_ids) == set(link.fact_ids)
                and set(candidate.evidence_ids) == set(link.evidence_ids)
            )
            if matching_edges != 1:
                raise ResultVerificationError("citation_verify_failed")
            supported_candidates.append(candidate.candidate_id)
        rows.append(
            CitationRow(
                evidence_id=evidence.evidence_id,
                source_label=evidence.source_id,
                source_url=evidence.source_url,
                source_locator=evidence.locator,
                chunk_id=evidence.chunk_id,
                source_id=evidence.source_id,
                knowledge_build_id=evidence.knowledge_build_id,
                supported_candidate_ids=tuple(sorted(supported_candidates)),
                supported_fact_ids=supported_facts,
            )
        )
    return tuple(rows)


def _validate_business_payloads(root: Path, manifest: ResultManifest) -> dict[str, bytes]:
    records = _business_records(manifest)
    values: dict[str, bytes] = {}
    for kind, record in records.items():
        path = root / record.path
        if not _safe_file(path, root):
            raise ResultVerificationError("result_path_invalid")
        payload = path.read_bytes()
        if (
            not payload
            or len(payload) != record.bytes
            or len(payload) > MAX_MEMBER_BYTES
            or sha256_bytes(payload) != record.sha256
        ):
            raise ResultVerificationError("result_hash_invalid")
        values[kind] = payload
    if sum(map(len, values.values())) > MAX_TOTAL_BYTES:
        raise ResultVerificationError("result_too_large")

    try:
        diagnosis = DiagnosisRecord.model_validate_json(values["diagnosis"], strict=True)
        if (
            diagnosis.case_id != manifest.identity.case_id
            or diagnosis.schema_version != manifest.identity.schema_version
            or sha256_bytes(canonical_json_bytes(diagnosis.model_dump(mode="json")))
            != manifest.identity.diagnosis_sha256
        ):
            raise ValueError("identity")
        assert_export_safe(diagnosis.model_dump(mode="json"))
    except Exception:
        raise ResultVerificationError("diagnosis_verify_failed") from None

    _assert_safe_text(values["report"])
    recap = _assert_safe_text(values["recap_text"])
    if not recap:
        raise ResultVerificationError("recap_verify_failed")
    try:
        citation_payload = json.loads(values["citations"].decode("utf-8"))
        if (
            set(citation_payload) != {"identity", "rows"}
            or canonical_json_bytes(citation_payload) != values["citations"]
        ):
            raise ValueError("canonical")
        if citation_payload.get("identity") != manifest.identity.model_dump(mode="json"):
            raise ValueError("identity")
        rows = tuple(
            CitationRow.model_validate_json(canonical_json_bytes(item), strict=True)
            for item in citation_payload.get("rows", [])
        )
        if len(rows) != len(citation_payload.get("rows", [])):
            raise ValueError("rows")
        if rows != _expected_citation_rows(diagnosis):
            raise ValueError("source graph")
        assert_export_safe(_mask_known_identifiers(values["citations"].decode("utf-8")))
    except Exception:
        raise ResultVerificationError("citation_verify_failed") from None

    try:
        source_payload = json.loads(values["source_manifest"].decode("utf-8"))
        allowed = {
            "source_contract_version",
            "case_id",
            "source_run_id",
            "diagnosis_sha256",
            "schema_version",
            "facts_revision",
            "facts_sha256",
            "routing_rule_version",
            "knowledge_build_id",
            "prompt_version",
            "workflow_version",
            "node_states",
        }
        if (
            set(source_payload) != allowed
            or canonical_json_bytes(source_payload) != values["source_manifest"]
        ):
            raise ValueError("summary")
        if (
            source_payload["source_contract_version"] != "1.0.0"
            or source_payload["case_id"] != manifest.identity.case_id
            or source_payload["source_run_id"] != manifest.identity.source_run_id
            or source_payload["diagnosis_sha256"] != manifest.identity.diagnosis_sha256
            or source_payload["schema_version"] != manifest.identity.schema_version
        ):
            raise ValueError("summary identity")
        source_summary = SourceManifestSummary.model_validate(
            {
                "manifest_version": source_payload["source_contract_version"],
                "case_id": source_payload["case_id"],
                "run_id": source_payload["source_run_id"],
                "facts_revision": source_payload["facts_revision"],
                "facts_sha256": source_payload["facts_sha256"],
                "routing_rule_version": source_payload["routing_rule_version"],
                "knowledge_build_id": source_payload["knowledge_build_id"],
                "schema_version": source_payload["schema_version"],
                "prompt_version": source_payload["prompt_version"],
                "workflow_version": source_payload["workflow_version"],
                # JSON decodes the canonical tuple as a list; construct the
                # tuple required by the strict source-summary contract before
                # model validation rather than weakening strict mode.
                "node_states": tuple(source_payload["node_states"]),
            },
            strict=True,
        )
        if len({item.stage for item in source_summary.node_states}) != len(
            source_summary.node_states
        ):
            raise ValueError("duplicate node")
        # Preserve the narrow, concrete entry contract rather than retaining a
        # generic JSON list that could disguise copied provider bodies.
        if tuple(
            NodeStateEntry.model_validate(item, strict=True)
            for item in source_payload["node_states"]
        ) != source_summary.node_states:
            raise ValueError("node state")
        assert_export_safe(source_payload)
    except Exception:
        raise ResultVerificationError("source_summary_invalid") from None

    if manifest.availability.card:
        try:
            with Image.open(root / _BUSINESS_SPECS["card"][0]) as image:
                expected_size = image.size
            verify_card_png(root / _BUSINESS_SPECS["card"][0], expected_size=expected_size)
        except Exception:
            raise ResultVerificationError("card_verify_failed") from None
    if manifest.availability.audio:
        try:
            probe = probe_mp3(
                root / _BUSINESS_SPECS["audio"][0], timeout_seconds=15.0, max_bytes=8_000_000
            )
            audio = manifest.audio
            if (
                audio is None
                or not audio.available
                or probe.sha256 != audio.sha256
                or probe.duration_ms != audio.duration_ms
                or probe.bytes != records["audio"].bytes
            ):
                raise ValueError("audio")
        except Exception:
            raise ResultVerificationError("audio_verify_failed") from None
    return values


def _parse_checksums(value: bytes) -> dict[str, str]:
    try:
        text = value.decode("ascii")
        rows = [line for line in text.splitlines() if line]
        parsed = {}
        for row in rows:
            digest, name = row.split("  ", 1)
            if not re.fullmatch(r"[0-9a-f]{64}", digest) or not name or name in parsed:
                raise ValueError("row")
            parsed[name] = digest
        if text != "".join(f"{digest}  {name}\n" for name, digest in sorted(parsed.items())):
            raise ValueError("order")
        return parsed
    except Exception:
        raise ResultVerificationError("checksums_invalid") from None


def _safe_zip_name(name: str) -> bool:
    return bool(
        name
        and "\\" not in name
        and "\x00" not in name
        and ":" not in name
        and not name.startswith("/")
        and all(part not in {"", ".", ".."} for part in name.split("/"))
    )


def _read_bounded_archive(path: Path, root: Path) -> tuple[bytes, str]:
    """Freeze one raw archive before hashing or passing it to ``ZipFile``.

    ZIP permits both a self-extracting prefix and a trailing payload.  They are
    not part of DebugMate's deterministic archive contract, so the verifier
    reads a single descriptor-backed byte copy first and makes all later ZIP
    work operate on that copy alone.
    """

    if not _safe_file(path, root):
        raise ResultVerificationError("archive_verify_failed")
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size <= 0
            or before.st_size > MAX_ARCHIVE_BYTES
        ):
            raise ValueError("archive shape")
        chunks: list[bytes] = []
        total = 0
        while total < before.st_size:
            block = os.read(descriptor, min(64 * 1024, before.st_size - total))
            if not block:
                break
            total += len(block)
            if total > before.st_size:
                raise ValueError("archive bound")
            chunks.append(block)
        after = os.fstat(descriptor)
        raw = b"".join(chunks)
        if (
            after.st_dev != before.st_dev
            or after.st_ino != before.st_ino
            or after.st_size != before.st_size
            or len(raw) != before.st_size
            or raw[:4] != b"PK\x03\x04"
        ):
            raise ValueError("archive bytes")
        return raw, sha256_bytes(raw)
    except (OSError, ValueError):
        raise ResultVerificationError("archive_verify_failed") from None
    finally:
        if descriptor >= 0:
            with suppress(OSError):
                os.close(descriptor)


def _assert_exact_zip_boundary(archive: zipfile.ZipFile, raw: bytes) -> None:
    """Reject bytes outside the central directory and EOCD of our ZIP format."""

    try:
        infos = archive.infolist()
        central_bytes = sum(
            46
            + len(info.filename.encode("ascii"))
            + len(info.extra)
            + len(info.comment)
            for info in infos
        )
        expected_end = archive.start_dir + central_bytes + 22 + len(archive.comment)
        if expected_end != len(raw):
            raise ValueError("archive boundary")
    except (AttributeError, UnicodeEncodeError, ValueError):
        raise ResultVerificationError("archive_verify_failed") from None


def _verify_archive(
    root: Path, manifest: ResultManifest, values: dict[str, bytes]
) -> tuple[str, str]:
    archive_name = (
        FULL_ARCHIVE_NAME if manifest.status is ResultStatus.COMPLETED else PARTIAL_ARCHIVE_NAME
    )
    archive_path = root / archive_name
    archive_bytes, archive_sha256 = _read_bounded_archive(archive_path, root)
    member_values = {_BUSINESS_SPECS[kind][0]: payload for kind, payload in values.items()}
    manifest_bytes = (root / RESULT_MANIFEST_NAME).read_bytes()
    member_values[RESULT_MANIFEST_NAME] = manifest_bytes
    checksums_path = root / CHECKSUMS_NAME
    if not _safe_file(checksums_path, root):
        raise ResultVerificationError("checksums_invalid")
    checksums = _parse_checksums(checksums_path.read_bytes())
    expected_names = sorted((*member_values, CHECKSUMS_NAME))
    if set(checksums) != set(member_values) or any(
        checksums[name] != sha256_bytes(payload) for name, payload in member_values.items()
    ):
        raise ResultVerificationError("checksums_invalid")
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            # Keep the path only as harmless diagnostic metadata; test and
            # instrumentation hooks must not make us reopen a mutable path.
            archive.filename = str(archive_path)
            _assert_exact_zip_boundary(archive, archive_bytes)
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if (
                len(infos) != len(expected_names)
                or names != expected_names
                or len(names) != len(set(names))
            ):
                raise ValueError("members")
            if archive.comment:
                raise ValueError("comment")
            total = compressed_total = 0
            # Validate the complete central-directory contract before opening
            # any payload.  In particular, never call ``testzip`` here: it
            # decompresses members before size/ratio policy is known.
            for info in infos:
                if (
                    not _safe_zip_name(info.filename)
                    or info.filename == PUBLICATION_NAME
                    or info.date_time != (1980, 1, 1, 0, 0, 0)
                    or info.create_system != 3
                    or info.external_attr != 0o100444 << 16
                    or info.extra
                    or info.comment
                    or info.compress_type != zipfile.ZIP_DEFLATED
                    or info.flag_bits != 0
                    or info.is_dir()
                    or info.header_offset < 0
                    or info.CRC < 0
                    or info.file_size <= 0
                    or info.file_size > MAX_MEMBER_BYTES
                    or info.compress_size <= 0
                    or info.compress_size > MAX_MEMBER_BYTES
                    or info.file_size > info.compress_size * 100
                ):
                    raise ValueError("metadata")
                total += info.file_size
                compressed_total += info.compress_size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("size")
                if compressed_total > MAX_TOTAL_BYTES:
                    raise ValueError("compressed size")

            for info in infos:
                expected = (
                    checksums_path.read_bytes()
                    if info.filename == CHECKSUMS_NAME
                    else member_values[info.filename]
                )
                if len(expected) != info.file_size:
                    raise ValueError("payload")
                chunks: list[bytes] = []
                total_read = 0
                crc = 0
                with archive.open(info, "r") as member:
                    while True:
                        block = member.read(min(64 * 1024, info.file_size + 1 - total_read))
                        if not block:
                            break
                        total_read += len(block)
                        if total_read > info.file_size:
                            raise ValueError("unbounded payload")
                        crc = zlib.crc32(block, crc)
                        chunks.append(block)
                data = b"".join(chunks)
                if (
                    total_read != info.file_size
                    or (crc & 0xFFFFFFFF) != info.CRC
                    or sha256_bytes(data) != sha256_bytes(expected)
                ):
                    raise ValueError("payload")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError):
        raise ResultVerificationError("archive_verify_failed") from None
    return archive_name, archive_sha256


def _verify_publication(
    root: Path, manifest: ResultManifest, archive_name: str, archive_sha256: str
) -> dict[str, object]:
    path = root / PUBLICATION_NAME
    if not _safe_file(path, root):
        raise ResultVerificationError("publication_invalid")
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        expected_keys = {
            "publication_version",
            "result_id",
            "identity",
            "status",
            "archive_name",
            "archive_sha256",
        }
        if (
            not isinstance(payload, dict)
            or set(payload) != expected_keys
            or raw != canonical_json_bytes(payload)
            or payload["publication_version"] != PUBLICATION_VERSION
            or payload["result_id"] != manifest.result_id
            or payload["identity"] != manifest.identity.model_dump(mode="json")
            or payload["status"] != manifest.status.value
            or payload["archive_name"] != archive_name
            or payload["archive_sha256"] != archive_sha256
        ):
            raise ValueError("publication")
        return payload
    except Exception:
        raise ResultVerificationError("publication_invalid") from None


def verify_result_bundle(path: Path, *, allow_temporary: bool = False) -> VerifiedResultBundle:
    """Re-read every relevant byte from disk before a result is restored or served."""

    root = Path(path)
    try:
        if not root.is_absolute() or not _safe_directory(root):
            raise ValueError("root")
        manifest_path = root / RESULT_MANIFEST_NAME
        if not _safe_file(manifest_path, root):
            raise ValueError("manifest")
        manifest = _canonical_model(manifest_path.read_bytes())
        if (
            manifest.manifest_version != MANIFEST_VERSION
            or _CASE_ID.fullmatch(manifest.identity.case_id) is None
            or _RESULT_ID.fullmatch(manifest.result_id) is None
            or (
                root.name != manifest.result_id
                and not (allow_temporary and root.name == f".tmp-{manifest.result_id}")
            )
            or root.parent.name != manifest.identity.case_id
        ):
            raise ValueError("identity")
        values = _validate_business_payloads(root, manifest)
        expected_id = _result_id_from_manifest(manifest, values)
        if manifest.result_id != expected_id:
            raise ValueError("result id")
        archive_name = (
            FULL_ARCHIVE_NAME if manifest.status is ResultStatus.COMPLETED else PARTIAL_ARCHIVE_NAME
        )
        expected_files = {
            *(record.path for record in manifest.artifacts),
            RESULT_MANIFEST_NAME,
            CHECKSUMS_NAME,
            archive_name,
            PUBLICATION_NAME,
        }
        if {item.name for item in root.iterdir()} != expected_files or any(
            not _safe_file(root / name, root) for name in expected_files
        ):
            raise ValueError("extra")
        verified_archive_name, archive_sha256 = _verify_archive(root, manifest, values)
        if verified_archive_name != archive_name:
            raise ValueError("archive")
        publication = _verify_publication(root, manifest, archive_name, archive_sha256)
        return VerifiedResultBundle(path=root, manifest=manifest, publication=publication)
    except ResultVerificationError:
        raise
    except Exception:
        raise ResultVerificationError() from None


def _result_id_from_manifest(manifest: ResultManifest, values: dict[str, bytes]) -> str:
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "identity": manifest.identity.model_dump(mode="json"),
        "mode": manifest.mode.value,
        "fixture_id": manifest.fixture_id,
        "fixture_name": manifest.fixture_name,
        "status": manifest.status.value,
        "availability": manifest.availability.model_dump(mode="json"),
        "failure": manifest.failure.model_dump(mode="json") if manifest.failure else None,
        "audio": manifest.audio.model_dump(mode="json") if manifest.audio else None,
        "business": {
            "diagnosis": sha256_bytes(values["diagnosis"]),
            "report": sha256_bytes(values["report"]),
            "recap_text": sha256_bytes(values["recap_text"]),
            "citations": sha256_bytes(values["citations"]),
            "source_manifest": sha256_bytes(values["source_manifest"]),
            "card": sha256_bytes(values["card"]) if "card" in values else None,
            "audio": manifest.audio.sha256 if manifest.audio else None,
        },
    }
    return f"result_{sha256_bytes(canonical_json_bytes(payload))[:32]}"


def _read_verified_member(
    path: Path, root: Path, *, expected_bytes: int, expected_sha256: str
) -> bytes:
    """Read a bounded member once and prove the pathname did not swap mid-read."""

    if expected_bytes <= 0 or expected_bytes > MAX_TOTAL_BYTES or not _safe_file(path, root):
        raise ResultVerificationError("download_invalid")
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size != expected_bytes:
            raise ValueError("shape")
        chunks: list[bytes] = []
        total = 0
        while True:
            block = os.read(descriptor, min(64 * 1024, expected_bytes + 1 - total))
            if not block:
                break
            total += len(block)
            if total > expected_bytes:
                raise ValueError("bound")
            chunks.append(block)
        after = os.fstat(descriptor)
        payload = b"".join(chunks)
        if (
            after.st_dev != before.st_dev
            or after.st_ino != before.st_ino
            or after.st_size != before.st_size
            or len(payload) != expected_bytes
            or sha256_bytes(payload) != expected_sha256
        ):
            raise ValueError("hash")
        return payload
    except (OSError, ValueError):
        raise ResultVerificationError("download_invalid") from None
    finally:
        if descriptor >= 0:
            with suppress(OSError):
                os.close(descriptor)


def resolve_verified_download(
    results_root: Path, case_id: str, result_id: str, member_id: str
) -> VerifiedDownload:
    """Issue one opaque byte copy after a full fresh on-disk revalidation."""

    try:
        if _CASE_ID.fullmatch(case_id) is None or _RESULT_ID.fullmatch(result_id) is None:
            raise ValueError("id")
        root = Path(results_root)
        if not root.is_absolute() or not _safe_directory(root):
            raise ValueError("root")
        bundle_path = root / case_id / result_id
        if bundle_path.parent.parent != root:
            raise ValueError("confinement")
        bundle = verify_result_bundle(bundle_path)
        names = {
            "bundle": FULL_ARCHIVE_NAME
            if bundle.manifest.status is ResultStatus.COMPLETED
            else PARTIAL_ARCHIVE_NAME,
            "report": _BUSINESS_SPECS["report"][0],
            "card": _BUSINESS_SPECS["card"][0],
            "audio": _BUSINESS_SPECS["audio"][0],
            "citations": _BUSINESS_SPECS["citations"][0],
        }
        name = names.get(member_id)
        if name is None or name not in {item.name for item in bundle.path.iterdir()}:
            raise ValueError("member")
        selected = bundle.path / name
        if not _safe_file(selected, bundle.path):
            raise ValueError("path")
        if member_id == "bundle":
            digest = bundle.publication["archive_sha256"]
            if not isinstance(digest, str):
                raise ValueError("archive")
            payload = _read_verified_member(
                selected,
                bundle.path,
                expected_bytes=selected.stat(follow_symlinks=False).st_size,
                expected_sha256=digest,
            )
            mime_type = "application/zip"
        else:
            record = next((item for item in bundle.manifest.artifacts if item.path == name), None)
            if (
                record is None
            ):
                raise ValueError("member")
            payload = _read_verified_member(
                selected,
                bundle.path,
                expected_bytes=record.bytes,
                expected_sha256=record.sha256,
            )
            mime_type = record.mime_type
        return VerifiedDownload._issue(
            payload=payload,
            member_id=member_id,
            filename=name,
            mime_type=mime_type,
            identity=bundle.manifest.identity,
        )
    except ResultVerificationError:
        raise
    except Exception:
        raise ResultVerificationError("download_invalid") from None
