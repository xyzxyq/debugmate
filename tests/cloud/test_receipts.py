from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

import debugmate.cloud.receipts as receipt_module
from debugmate.cloud.contracts import (
    CloudFailureCode,
    DifyAttempt,
    DifyAttemptKind,
    DifyReceipt,
    DifyUsage,
    ReceiptStatus,
    new_started_receipt,
    receipt_identity,
)
from debugmate.cloud.receipts import DifyReceiptStore, ReceiptStoreError


CASE_ID = "case_0123456789abcdef0123456789abcdef"
APPROVAL_FINGERPRINT = "a" * 64
PREVIEW_HASH = "b" * 64
STARTED_AT = datetime(2026, 8, 10, 1, 2, 3, tzinfo=UTC)


def _started() -> DifyReceipt:
    return new_started_receipt(
        case_id=CASE_ID,
        approval_identity_fingerprint=APPROVAL_FINGERPRINT,
        preview_hash=PREVIEW_HASH,
        started_at=STARTED_AT,
    )


def _attempt(status: str = "succeeded") -> DifyAttempt:
    return DifyAttempt(
        kind=DifyAttemptKind.WORKFLOW,
        attempt_fingerprint="c" * 64,
        status=status,
        latency_ms=500,
    )


def test_receipt_identity_is_canonical_approval_fingerprint_plus_preview_hash() -> None:
    first = receipt_identity(APPROVAL_FINGERPRINT, PREVIEW_HASH)
    second = receipt_identity(APPROVAL_FINGERPRINT, PREVIEW_HASH)

    assert first == second
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert first != receipt_identity("d" * 64, PREVIEW_HASH)
    assert _started().receipt_id == first


def test_store_persists_started_before_one_terminal_transition(tmp_path: Path) -> None:
    root = tmp_path / "receipts"
    store = DifyReceiptStore(root)
    started = store.begin(_started())

    assert store.read(started.receipt_id).status is ReceiptStatus.STARTED
    terminal = store.finish(
        started.receipt_id,
        status=ReceiptStatus.SUCCEEDED,
        terminal_at=STARTED_AT + timedelta(seconds=1),
        attempts=(_attempt(),),
        usage=DifyUsage(total_tokens=123, total_steps=6),
        accepted_result_id="result_0123456789abcdef0123456789abcdef",
    )
    assert terminal.status is ReceiptStatus.SUCCEEDED
    assert store.read(started.receipt_id) == terminal

    with pytest.raises(ReceiptStoreError, match="terminal"):
        store.finish(
            started.receipt_id,
            status=ReceiptStatus.FAILED,
            terminal_at=STARTED_AT + timedelta(seconds=2),
            attempts=(_attempt("failed"),),
            failure_code=CloudFailureCode.WORKFLOW_ENVELOPE,
            safe_failure_detail="invalid envelope",
        )


@pytest.mark.parametrize(
    "status", [ReceiptStatus.SUCCEEDED, ReceiptStatus.UNCERTAIN, ReceiptStatus.FAILED]
)
def test_every_terminal_state_is_immutable(tmp_path: Path, status: ReceiptStatus) -> None:
    store = DifyReceiptStore(tmp_path / status.value)
    started = store.begin(_started())
    kwargs: dict[str, object] = {
        "status": status,
        "terminal_at": STARTED_AT + timedelta(seconds=1),
        "attempts": (_attempt("succeeded" if status is ReceiptStatus.SUCCEEDED else status.value),),
    }
    if status is ReceiptStatus.SUCCEEDED:
        kwargs["accepted_result_id"] = "result_0123456789abcdef0123456789abcdef"
    else:
        kwargs["failure_code"] = CloudFailureCode.AMBIGUOUS_TIMEOUT
        kwargs["safe_failure_detail"] = "safe detail"
    store.finish(started.receipt_id, **kwargs)

    for replacement in ReceiptStatus:
        with pytest.raises(ReceiptStoreError):
            store.finish(
                started.receipt_id,
                status=replacement,
                terminal_at=STARTED_AT + timedelta(seconds=2),
                attempts=(_attempt("failed"),),
                failure_code=CloudFailureCode.WORKFLOW_ENVELOPE,
                safe_failure_detail="rewrite",
            )


def test_duplicate_begin_restart_and_corrupt_json_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "receipts"
    started = _started()
    DifyReceiptStore(root).begin(started)

    with pytest.raises(ReceiptStoreError, match="already exists"):
        DifyReceiptStore(root).begin(started)

    record = root / f"{started.receipt_id}.json"
    record.write_text("{", encoding="utf-8")
    with pytest.raises(ReceiptStoreError, match="invalid"):
        DifyReceiptStore(root).read(started.receipt_id)


def test_link_or_reparse_root_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "receipts"
    original = receipt_module._is_link_or_reparse
    monkeypatch.setattr(
        receipt_module,
        "_is_link_or_reparse",
        lambda path: path == root or original(path),
    )

    with pytest.raises(ReceiptStoreError, match="root"):
        DifyReceiptStore(root).begin(_started())


def test_receipt_contract_rejects_secrets_raw_ids_and_oversized_failure_detail() -> None:
    payload = _started().model_dump()
    for forbidden in (
        "approval_id",
        "approval_signature",
        "approval_token",
        "api_key",
        "provider_body",
        "remote_run_id",
    ):
        with pytest.raises(ValidationError):
            DifyReceipt.model_validate(payload | {forbidden: "secret"}, strict=True)

    with pytest.raises(ValidationError):
        DifyReceipt.model_validate(
            payload
            | {
                "status": ReceiptStatus.FAILED,
                "terminal_at": STARTED_AT + timedelta(seconds=1),
                "failure_code": CloudFailureCode.WORKFLOW_ENVELOPE,
                "safe_failure_detail": "x" * 129,
            },
            strict=True,
        )

    serialized = json.dumps(payload, default=str, sort_keys=True)
    assert APPROVAL_FINGERPRINT not in serialized
    assert re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        serialized,
        re.I,
    ) is None
