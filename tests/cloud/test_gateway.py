from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from debugmate.adapters.base import FileUploadResult
from debugmate.contracts import new_case_id
from debugmate.gateway import CloudGateway
from debugmate.hashing import sha256_file
from debugmate.privacy.approval import ApprovalInvalid, approve_preview
from debugmate.privacy.models import InputEnvelope, PreviewBundle
from debugmate.privacy.text_redactor import redact_input

KEY = b"test-key-32-bytes-minimum-value!"


class SnapshotBackend:
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
        return FileUploadResult(
            file_id="transient-upload-id",
            filename=filename,
            backend="dify",
            file_id_fingerprint="a" * 64,
            mime_type=mime_type,
            size=len(content),
        )

    def run_workflow(self, inputs: dict[str, object], user: str) -> object:
        self.calls.append(("run", inputs, user))
        return {"ok": True}


def _preview() -> PreviewBundle:
    return redact_input(
        InputEnvelope(
            case_id=new_case_id(),
            error_text="ModuleNotFoundError: No module named 'demo_pkg'",
        )
    )


def _image_bytes(image_format: str = "PNG") -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 6), "white").save(output, format=image_format)
    return output.getvalue()


def _approved_image(root: Path, relative: str, content: bytes) -> object:
    image = root / relative
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(content)
    source = _preview()
    redacted = source.redacted.model_copy(
        update={
            "redacted_screenshot_path": relative,
            "redacted_screenshot_sha256": sha256_file(image),
        }
    )
    bound = source.model_copy(update={"redacted": redacted, "preview_hash": "f" * 64})
    return approve_preview(bound, KEY)


@pytest.mark.parametrize(
    ("suffix", "image_format", "expected_mime"),
    [("png", "PNG", "image/png"), ("jpg", "JPEG", "image/jpeg")],
)
def test_gateway_uploads_one_immutable_verified_snapshot_with_exact_input_shape(
    tmp_path: Path, suffix: str, image_format: str, expected_mime: str
) -> None:
    relative = f"case/redacted.{suffix}"
    content = _image_bytes(image_format)
    approved = _approved_image(tmp_path, relative, content)
    backend = SnapshotBackend()

    result = CloudGateway(
        backend, approval_key=KEY, user="stable-dify-user", redacted_root=tmp_path
    ).run(approved)

    assert result == {"ok": True}
    assert backend.calls[0] == (
        "upload",
        {"content": content, "filename": f"redacted.{suffix}", "mime_type": expected_mime},
        "stable-dify-user",
    )
    assert backend.calls[1] == (
        "run",
        {
            "error_text": approved.redacted.error_text,
            "code": approved.redacted.code,
            "environment": approved.redacted.environment,
            "case_id": approved.case_id,
            "image_input": {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": "transient-upload-id",
            },
        },
        "stable-dify-user",
    )
    workflow_inputs = backend.calls[1][1]
    assert isinstance(workflow_inputs, dict)
    assert "file_id" not in workflow_inputs
    assert "screenshot_file_id" not in workflow_inputs


def test_text_only_gateway_omits_image_input_and_upload(tmp_path: Path) -> None:
    approved = approve_preview(_preview(), KEY)
    backend = SnapshotBackend()

    CloudGateway(
        backend, approval_key=KEY, user="stable-dify-user", redacted_root=tmp_path
    ).run(approved)

    assert [call[0] for call in backend.calls] == ["run"]
    inputs = backend.calls[0][1]
    assert isinstance(inputs, dict)
    assert "image_input" not in inputs


def test_post_approval_replacement_fails_before_any_backend_call(tmp_path: Path) -> None:
    approved = _approved_image(tmp_path, "case/redacted.png", _image_bytes())
    (tmp_path / "case" / "redacted.png").write_bytes(_image_bytes("JPEG"))
    backend = SnapshotBackend()

    with pytest.raises(ApprovalInvalid):
        CloudGateway(backend, approval_key=KEY, redacted_root=tmp_path).run(approved)

    assert backend.calls == []


def test_extension_and_decoded_mime_mismatch_fails_before_network(tmp_path: Path) -> None:
    approved = _approved_image(tmp_path, "case/redacted.jpg", _image_bytes("PNG"))
    backend = SnapshotBackend()

    with pytest.raises(ApprovalInvalid):
        CloudGateway(backend, approval_key=KEY, redacted_root=tmp_path).run(approved)

    assert backend.calls == []


def test_linked_screenshot_is_rejected_even_when_target_stays_under_root(tmp_path: Path) -> None:
    target = tmp_path / "case" / "target.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(_image_bytes())
    link = target.with_name("redacted.png")
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("file links are unavailable on this Windows host")
    source = _preview()
    redacted = source.redacted.model_copy(
        update={
            "redacted_screenshot_path": "case/redacted.png",
            "redacted_screenshot_sha256": sha256_file(link),
        }
    )
    approved = approve_preview(
        source.model_copy(update={"redacted": redacted, "preview_hash": "e" * 64}), KEY
    )
    backend = SnapshotBackend()

    with pytest.raises(ApprovalInvalid):
        CloudGateway(backend, approval_key=KEY, redacted_root=tmp_path).run(approved)

    assert backend.calls == []
