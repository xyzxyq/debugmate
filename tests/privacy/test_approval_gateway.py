from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from debugmate.adapters.base import FileUploadResult
from debugmate.contracts import new_case_id
from debugmate.gateway import CloudGateway
from debugmate.hashing import sha256_file
from debugmate.privacy.approval import ApprovalInvalid, approve_preview, verify_approval
from debugmate.privacy.models import InputEnvelope, PreviewBundle, RedactedFields
from debugmate.privacy.text_redactor import redact_input
from debugmate.settings import DebugMateSettings

KEY = b"test-key-32-bytes-minimum-value!"


class FakeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, str]] = []

    def upload_bytes(
        self, content: bytes, *, filename: str, mime_type: str, user: str
    ) -> FileUploadResult:
        self.calls.append(
            (
                "upload",
                {"content": content, "filename": filename, "mime_type": mime_type},
                user,
            )
        )
        return FileUploadResult(file_id="file-redacted", filename=filename, backend="fake")

    def run_workflow(self, inputs: dict[str, object], user: str) -> object:
        self.calls.append(("run", inputs, user))
        return {"ok": True}


def preview() -> PreviewBundle:
    return redact_input(
        InputEnvelope(
            case_id=new_case_id(),
            error_text="mail=student@example.com",
            code="raise RuntimeError('demo')",
            environment={"PYTHON": "3.13.5"},
        )
    )


def test_mutated_preview_hash_or_case_invalidates_approval() -> None:
    approved = approve_preview(preview(), KEY)
    for tampered in (
        approved.model_copy(update={"preview_hash": "0" * 64}),
        approved.model_copy(update={"case_id": new_case_id()}),
    ):
        with pytest.raises(ApprovalInvalid):
            verify_approval(tampered, KEY)


def test_mutated_redacted_payload_invalidates_approval() -> None:
    approved = approve_preview(preview(), KEY)
    changed_fields = approved.redacted.model_copy(update={"error_text": "changed"})
    tampered = approved.model_copy(update={"redacted": changed_fields})
    with pytest.raises(ApprovalInvalid):
        verify_approval(tampered, KEY)


def test_wrong_key_expired_and_future_approvals_are_rejected() -> None:
    now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    valid = approve_preview(preview(), KEY, approved_at_utc=now)
    assert verify_approval(valid, KEY, now=now + timedelta(minutes=30)) is None

    with pytest.raises(ApprovalInvalid):
        verify_approval(valid, b"wrong-key-with-at-least-32-bytes!!", now=now)

    expired = approve_preview(preview(), KEY, approved_at_utc=now - timedelta(minutes=31))
    with pytest.raises(ApprovalInvalid):
        verify_approval(expired, KEY, now=now)

    future = approve_preview(preview(), KEY, approved_at_utc=now + timedelta(seconds=1))
    with pytest.raises(ApprovalInvalid):
        verify_approval(future, KEY, now=now)


def test_gateway_rejects_unapproved_or_invalid_input_without_backend_calls() -> None:
    backend = FakeBackend()
    source_preview = preview()
    gateway = CloudGateway(backend, approval_key=KEY, user="course-demo")

    with pytest.raises(TypeError):
        gateway.run(source_preview)  # type: ignore[arg-type]
    assert backend.calls == []

    approved = approve_preview(source_preview, KEY)
    tampered = approved.model_copy(update={"preview_hash": "0" * 64})
    with pytest.raises(ApprovalInvalid):
        gateway.run(tampered)
    assert backend.calls == []


def test_gateway_wrong_key_case_and_expiry_make_zero_backend_calls() -> None:
    source_preview = preview()
    approved = approve_preview(source_preview, KEY)
    expired = approve_preview(
        source_preview,
        KEY,
        approved_at_utc=datetime.now(UTC) - timedelta(minutes=31),
    )
    cases = [
        (approved, b"different-key-with-at-least-32-bytes!"),
        (approved.model_copy(update={"case_id": new_case_id()}), KEY),
        (expired, KEY),
    ]
    for invalid, key in cases:
        backend = FakeBackend()
        with pytest.raises(ApprovalInvalid):
            CloudGateway(backend, approval_key=key).run(invalid)
        assert backend.calls == []


def test_gateway_sends_only_allowlisted_redacted_fields() -> None:
    backend = FakeBackend()
    source_preview = preview()
    approved = approve_preview(source_preview, KEY)
    gateway = CloudGateway(backend, approval_key=KEY, user="course-demo")

    assert gateway.run(approved) == {"ok": True}
    assert backend.calls == [
        (
            "run",
            {
                "error_text": source_preview.redacted.error_text,
                "code": source_preview.redacted.code,
                "environment": source_preview.redacted.environment,
                "case_id": source_preview.case_id,
            },
            "course-demo",
        )
    ]
    payload_text = repr(backend.calls)
    assert approved.approval_id not in payload_text
    assert approved.approval_signature not in payload_text


def test_gateway_uploads_verified_redacted_screenshot_first(tmp_path: Path) -> None:
    image = tmp_path / "case" / "redacted.png"
    image.parent.mkdir()
    output = BytesIO()
    Image.new("RGB", (4, 4), "white").save(output, format="PNG")
    image_bytes = output.getvalue()
    image.write_bytes(image_bytes)
    source_preview = preview()
    redacted = source_preview.redacted.model_copy(
        update={
            "redacted_screenshot_path": "case/redacted.png",
            "redacted_screenshot_sha256": sha256_file(image),
        }
    )
    with_image = source_preview.model_copy(
        update={"redacted": redacted, "preview_hash": "f" * 64}
    )
    approved = approve_preview(with_image, KEY)
    backend = FakeBackend()

    CloudGateway(
        backend, approval_key=KEY, user="course-demo", redacted_root=tmp_path
    ).run(approved)

    assert backend.calls[0] == (
        "upload",
        {"content": image_bytes, "filename": "redacted.png", "mime_type": "image/png"},
        "course-demo",
    )
    assert backend.calls[1][0] == "run"
    payload = backend.calls[1][1]
    assert isinstance(payload, dict)
    assert payload["image_input"] == {
        "type": "image",
        "transfer_method": "local_file",
        "upload_file_id": "file-redacted",
    }
    assert "redacted_screenshot_path" not in payload


def test_changed_screenshot_is_rejected_before_backend_call(tmp_path: Path) -> None:
    image = tmp_path / "case" / "redacted.png"
    image.parent.mkdir()
    image.write_bytes(b"approved")
    source_preview = preview()
    with_image = source_preview.model_copy(
        update={
            "redacted": source_preview.redacted.model_copy(
                update={
                    "redacted_screenshot_path": "case/redacted.png",
                    "redacted_screenshot_sha256": sha256_file(image),
                }
            ),
            "preview_hash": "e" * 64,
        }
    )
    approved = approve_preview(with_image, KEY)
    image.write_bytes(b"tampered")
    backend = FakeBackend()

    with pytest.raises(ApprovalInvalid):
        CloudGateway(backend, approval_key=KEY, redacted_root=tmp_path).run(approved)
    assert backend.calls == []


def test_gateway_requires_root_for_screenshot_without_backend_calls(tmp_path: Path) -> None:
    image = tmp_path / "case" / "redacted.png"
    image.parent.mkdir()
    image.write_bytes(b"approved")
    source_preview = preview()
    redacted = source_preview.redacted.model_validate(
        {
            **source_preview.redacted.model_dump(mode="json"),
            "redacted_screenshot_path": "case/redacted.png",
            "redacted_screenshot_sha256": sha256_file(image),
        }
    )
    approved = approve_preview(
        PreviewBundle.model_validate(
            {**source_preview.model_dump(), "redacted": redacted, "preview_hash": "d" * 64}
        ),
        KEY,
    )
    backend = FakeBackend()

    with pytest.raises(ApprovalInvalid):
        CloudGateway(backend, approval_key=KEY).run(approved)
    assert backend.calls == []


def test_gateway_rejects_redacted_root_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    image = outside / "redacted.png"
    image.write_bytes(b"approved")
    try:
        (root / "case").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory links are unavailable on this Windows host")

    source_preview = preview()
    redacted = RedactedFields.model_validate(
        {
            **source_preview.redacted.model_dump(mode="json"),
            "redacted_screenshot_path": "case/redacted.png",
            "redacted_screenshot_sha256": sha256_file(image),
        }
    )
    approved = approve_preview(
        PreviewBundle.model_validate(
            {**source_preview.model_dump(), "redacted": redacted, "preview_hash": "c" * 64}
        ),
        KEY,
    )
    backend = FakeBackend()

    with pytest.raises(ApprovalInvalid):
        CloudGateway(backend, approval_key=KEY, redacted_root=root).run(approved)
    assert backend.calls == []


def test_settings_load_or_generate_non_serialized_approval_key() -> None:
    configured = DebugMateSettings.from_env({"DEBUGMATE_APPROVAL_KEY": KEY.decode()})
    first_default = DebugMateSettings.from_env({})
    second_default = DebugMateSettings.from_env({})

    assert configured.approval_key_bytes == KEY
    assert len(first_default.approval_key_bytes) >= 32
    assert first_default.approval_key_bytes != second_default.approval_key_bytes
    rendered: list[Any] = [
        repr(configured),
        configured.model_dump_json(),
        configured.safe_summary(),
    ]
    assert KEY.decode() not in repr(rendered)


def test_short_approval_keys_are_rejected_without_echoing_value() -> None:
    short = b"too-short"
    with pytest.raises(ValueError) as caught:
        approve_preview(preview(), short)
    assert short.decode() not in str(caught.value)
