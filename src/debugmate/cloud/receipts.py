"""Atomic one-way persistence for Dify dispatch receipts."""

from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import datetime
from pathlib import Path

from debugmate.cloud.contracts import (
    CloudFailureCode,
    DifyAttempt,
    DifyReceipt,
    DifyUsage,
    ReceiptStatus,
)


class ReceiptStoreError(ValueError):
    """Safe fail-closed receipt persistence error."""


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(path.stat(follow_symlinks=False).st_file_attributes & 0x400)
    except (AttributeError, FileNotFoundError, OSError):
        return False


def _has_unsafe_ancestor(path: Path) -> bool:
    current = path
    while current != current.parent:
        if current.exists() and _is_link_or_reparse(current):
            return True
        current = current.parent
    return current.exists() and _is_link_or_reparse(current)


class DifyReceiptStore:
    """Persist one canonical JSON receipt and allow one terminal transition."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._lock = threading.RLock()
        if not self._root.is_absolute():
            raise ReceiptStoreError("receipt root must be absolute")

    def _prepare_root(self) -> None:
        parent = self._root.parent
        if not parent.is_dir() or _has_unsafe_ancestor(parent):
            raise ReceiptStoreError("receipt root parent is invalid")
        if self._root.exists() and (
            not self._root.is_dir() or _is_link_or_reparse(self._root)
        ):
            raise ReceiptStoreError("receipt root must be a non-link directory")
        self._root.mkdir(exist_ok=True)
        if not self._root.is_dir() or _is_link_or_reparse(self._root):
            raise ReceiptStoreError("receipt root must be a non-link directory")

    def _path(self, receipt_id: str) -> Path:
        if re.fullmatch(r"[0-9a-f]{64}", receipt_id) is None:
            raise ReceiptStoreError("receipt identity is invalid")
        return self._root / f"{receipt_id}.json"

    @staticmethod
    def _canonical_bytes(receipt: DifyReceipt) -> bytes:
        return json.dumps(
            receipt.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @contextmanager
    def _exclusive_receipt_lock(self, receipt_id: str) -> Iterator[None]:
        self._prepare_root()
        lock_path = self._root / f".{receipt_id}.lock"
        descriptor: int | None = None
        try:
            descriptor = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
            os.close(descriptor)
            descriptor = None
            yield
        except FileExistsError:
            raise ReceiptStoreError("receipt update is already in progress") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if lock_path.exists() and not _is_link_or_reparse(lock_path):
                with suppress(OSError):
                    lock_path.unlink()

    def _write_new(self, receipt: DifyReceipt) -> None:
        target = self._path(receipt.receipt_id)
        temporary = self._root / f".{receipt.receipt_id}.tmp"
        with self._exclusive_receipt_lock(receipt.receipt_id):
            try:
                if target.exists() or temporary.exists():
                    raise ReceiptStoreError("receipt already exists")
                raw = self._canonical_bytes(receipt)
                with temporary.open("xb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            except FileExistsError:
                raise ReceiptStoreError("receipt already exists") from None
            finally:
                if temporary.exists() and not _is_link_or_reparse(temporary):
                    with suppress(OSError):
                        temporary.unlink()

    def _replace(self, receipt: DifyReceipt) -> None:
        target = self._path(receipt.receipt_id)
        temporary = self._root / f".{receipt.receipt_id}.tmp"
        if temporary.exists():
            raise ReceiptStoreError("receipt temporary record already exists")
        try:
            raw = self._canonical_bytes(receipt)
            with temporary.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists() and not _is_link_or_reparse(temporary):
                with suppress(OSError):
                    temporary.unlink()

    def begin(self, receipt: DifyReceipt) -> DifyReceipt:
        with self._lock:
            try:
                strict = DifyReceipt.model_validate(receipt.model_dump(), strict=True)
                if strict.status is not ReceiptStatus.STARTED:
                    raise ReceiptStoreError("receipt begin requires started status")
                self._write_new(strict)
                return strict
            except ReceiptStoreError:
                raise
            except Exception:
                raise ReceiptStoreError("receipt begin is invalid") from None

    def read(self, receipt_id: str) -> DifyReceipt:
        with self._lock:
            try:
                self._prepare_root()
                path = self._path(receipt_id)
                if not path.is_file() or _is_link_or_reparse(path):
                    raise ValueError("receipt record is missing or unsafe")
                raw = path.read_bytes()
                receipt = DifyReceipt.model_validate_json(raw, strict=True)
                if receipt.receipt_id != receipt_id or raw != self._canonical_bytes(receipt):
                    raise ValueError("receipt record is not canonical")
                return receipt
            except Exception:
                raise ReceiptStoreError("receipt record is invalid") from None

    def finish(
        self,
        receipt_id: str,
        *,
        status: ReceiptStatus,
        terminal_at: datetime,
        attempts: tuple[DifyAttempt, ...],
        usage: DifyUsage | None = None,
        accepted_result_id: str | None = None,
        failure_code: CloudFailureCode | None = None,
        safe_failure_detail: str | None = None,
    ) -> DifyReceipt:
        with self._lock, self._exclusive_receipt_lock(receipt_id):
            current = self.read(receipt_id)
            if current.status is not ReceiptStatus.STARTED:
                raise ReceiptStoreError("terminal receipt is immutable")
            if status is ReceiptStatus.STARTED:
                raise ReceiptStoreError("receipt finish requires a terminal status")
            try:
                terminal = DifyReceipt(
                    **current.model_dump(
                        exclude={
                            "status",
                            "terminal_at",
                            "attempts",
                            "usage",
                            "accepted_result_id",
                            "failure_code",
                            "safe_failure_detail",
                        }
                    ),
                    status=status,
                    terminal_at=terminal_at,
                    attempts=attempts,
                    usage=usage or DifyUsage(),
                    accepted_result_id=accepted_result_id,
                    failure_code=failure_code,
                    safe_failure_detail=safe_failure_detail,
                )
                self._replace(terminal)
                return terminal
            except ReceiptStoreError:
                raise
            except Exception:
                raise ReceiptStoreError("terminal receipt is invalid") from None
