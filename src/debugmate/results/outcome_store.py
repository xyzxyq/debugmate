"""Atomic, integrity-checked repository for full redacted diagnosis outcomes."""

from __future__ import annotations

import hmac
import re
import shutil
from pathlib import Path

from debugmate.diagnosis.workflow import DiagnosisRunOutcome
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.privacy.output_scan import assert_export_safe
from debugmate.results.loader import (
    ResultLoadError,
    _has_unsafe_ancestor,
    _is_link_or_reparse,
    _strict_outcome,
    atomic_replace_directory,
)


class DiagnosisOutcomeStore:
    """Persist complete redacted outcomes at an identity-derived immutable record."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        if not self._root.is_absolute():
            raise ResultLoadError("outcome_store_invalid", "store")

    def _prepare_root(self) -> None:
        parent = self._root.parent
        if not parent.is_dir() or _has_unsafe_ancestor(parent):
            raise ResultLoadError("outcome_store_invalid", "store")
        if self._root.exists() and (
            not self._root.is_dir() or _is_link_or_reparse(self._root)
        ):
            raise ResultLoadError("outcome_store_invalid", "store")
        self._root.mkdir(exist_ok=True)

    def write(self, outcome: DiagnosisRunOutcome) -> Path:
        try:
            strict = _strict_outcome(outcome)
            payload = strict.model_dump(mode="json")
            scan_payload = dict(payload)
            scan_payload.pop("idempotency_key", None)
            extraction = dict(scan_payload["extraction"])
            extraction["source_hashes"] = {
                f"{key}_sha256": value
                for key, value in extraction["source_hashes"].items()
            }
            scan_payload["extraction"] = extraction
            assert_export_safe(scan_payload)
            raw = canonical_json_bytes(payload)
            self._prepare_root()
            target = self._root / strict.run_id
            temporary = self._root / f".tmp-{strict.run_id}"
            if target.exists() or temporary.exists():
                raise ValueError("outcome record already exists")
            temporary.mkdir()
            (temporary / "outcome.json").write_bytes(raw)
            (temporary / "outcome.sha256").write_text(sha256_bytes(raw), encoding="ascii")
            atomic_replace_directory(temporary, target)
            return target
        except ResultLoadError:
            raise
        except Exception as exc:
            if "temporary" in locals() and temporary.exists() and not temporary.is_symlink():
                shutil.rmtree(temporary)
            raise ResultLoadError("outcome_store_invalid", "store") from exc

    def read(self, run_id: str) -> DiagnosisRunOutcome:
        try:
            if re.fullmatch(r"run_[0-9a-f]{32}", run_id) is None:
                raise ValueError("invalid run identity")
            self._prepare_root()
            record = self._root / run_id
            if (
                not record.is_dir()
                or _is_link_or_reparse(record)
                or record.name != run_id
                or {item.name for item in record.iterdir()}
                != {"outcome.json", "outcome.sha256"}
            ):
                raise ValueError("invalid outcome record")
            for item in record.iterdir():
                if not item.is_file() or _is_link_or_reparse(item):
                    raise ValueError("unsafe outcome member")
            raw = (record / "outcome.json").read_bytes()
            expected = (record / "outcome.sha256").read_text(encoding="ascii")
            if not hmac.compare_digest(expected, sha256_bytes(raw)):
                raise ValueError("outcome integrity mismatch")
            outcome = DiagnosisRunOutcome.model_validate_json(raw, strict=True)
            outcome = _strict_outcome(outcome)
            canonical = canonical_json_bytes(outcome.model_dump(mode="json"))
            if outcome.run_id != run_id or raw != canonical:
                raise ValueError("outcome record is not canonical or directory-bound")
            return outcome
        except ResultLoadError:
            raise
        except Exception as exc:
            raise ResultLoadError("outcome_store_invalid", "store") from exc
