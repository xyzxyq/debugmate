"""Fresh, public on-disk verification for immutable DebugMate result bundles."""

from __future__ import annotations

import json
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from pydantic import ValidationError

from debugmate.contracts import DiagnosisRecord
from debugmate.hashing import canonical_json_bytes, sha256_bytes, sha256_file
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.card import verify_card_png
from debugmate.results.contracts import ResultManifest, ResultStatus
from debugmate.results.media import probe_mp3
from debugmate.results.publisher import (
    _BUSINESS_SPECS,
    _CASE_ID,
    _RESULT_ID,
    CHECKSUMS_NAME,
    FULL_ARCHIVE_NAME,
    MANIFEST_VERSION,
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
        if canonical_json_bytes(citation_payload) != values["citations"]:
            raise ValueError("canonical")
        if citation_payload.get("identity") != manifest.identity.model_dump(mode="json"):
            raise ValueError("identity")
        rows = tuple(
            CitationRow.model_validate_json(canonical_json_bytes(item), strict=True)
            for item in citation_payload.get("rows", [])
        )
        if len(rows) != len(citation_payload.get("rows", [])):
            raise ValueError("rows")
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


def _verify_archive(root: Path, manifest: ResultManifest, values: dict[str, bytes]) -> str:
    archive_name = (
        FULL_ARCHIVE_NAME if manifest.status is ResultStatus.COMPLETED else PARTIAL_ARCHIVE_NAME
    )
    archive_path = root / archive_name
    if not _safe_file(archive_path, root):
        raise ResultVerificationError("archive_verify_failed")
    member_values = {_BUSINESS_SPECS[kind][0]: payload for kind, payload in values.items()}
    manifest_bytes = (root / RESULT_MANIFEST_NAME).read_bytes()
    member_values[RESULT_MANIFEST_NAME] = manifest_bytes
    checksums = _parse_checksums((root / CHECKSUMS_NAME).read_bytes())
    expected_names = sorted((*member_values, CHECKSUMS_NAME))
    if set(checksums) != set(member_values) or any(
        checksums[name] != sha256_bytes(payload) for name, payload in member_values.items()
    ):
        raise ResultVerificationError("checksums_invalid")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            if (
                len(infos) != len(expected_names)
                or [info.filename for info in infos] != expected_names
            ):
                raise ValueError("members")
            if archive.comment or archive.testzip() is not None:
                raise ValueError("crc")
            total = 0
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
                    or info.file_size <= 0
                    or info.file_size > MAX_MEMBER_BYTES
                    or info.file_size / max(1, info.compress_size) > 100
                ):
                    raise ValueError("metadata")
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    raise ValueError("size")
                data = archive.read(info)
                expected = (
                    (root / CHECKSUMS_NAME).read_bytes()
                    if info.filename == CHECKSUMS_NAME
                    else member_values[info.filename]
                )
                if data != expected:
                    raise ValueError("payload")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, RuntimeError):
        raise ResultVerificationError("archive_verify_failed") from None
    return archive_name


def _verify_publication(
    root: Path, manifest: ResultManifest, archive_name: str
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
            or payload["archive_sha256"] != sha256_file(root / archive_name)
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
        if _verify_archive(root, manifest, values) != archive_name:
            raise ValueError("archive")
        publication = _verify_publication(root, manifest, archive_name)
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


def resolve_verified_download(
    results_root: Path, case_id: str, result_id: str, member_id: str
) -> Path:
    """Resolve one fixed member ID only after a complete fresh disk verification."""

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
            if sha256_file(selected) != bundle.publication["archive_sha256"]:
                raise ValueError("archive")
        else:
            record = next((item for item in bundle.manifest.artifacts if item.path == name), None)
            if (
                record is None
                or selected.stat().st_size != record.bytes
                or sha256_file(selected) != record.sha256
            ):
                raise ValueError("member")
        return selected
    except ResultVerificationError:
        raise
    except Exception:
        raise ResultVerificationError("download_invalid") from None
