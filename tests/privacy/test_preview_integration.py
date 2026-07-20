from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from debugmate.adapters.base import FileUploadResult
from debugmate.contracts import new_case_id
from debugmate.gateway import CloudGateway
from debugmate.hashing import sha256_file
from debugmate.privacy.approval import approve_preview
from debugmate.privacy.image_redactor import OcrUnavailable, UnsafeRedactionPath
from debugmate.privacy.models import InputEnvelope, RedactedFields
from debugmate.privacy.ocr import OcrToken
from debugmate.privacy.rapidocr_backend import RapidOcrBackend
from debugmate.privacy.text_redactor import build_preview, redact_input


class FakeOcr:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def recognize(self, path: Path) -> list[OcrToken]:
        self.calls.append(path)
        return [
            OcrToken(
                text=r"C:\Users\student\secret.py",
                box=((10, 10), (180, 10), (180, 35), (10, 35)),
                score=0.99,
            )
        ]


class FailingOcr:
    def recognize(self, path: Path) -> list[OcrToken]:
        raise RuntimeError(f"OCR failed for {path}")


def _input(source: Path) -> InputEnvelope:
    return InputEnvelope(
        case_id=new_case_id(),
        error_text="mail=student@example.com",
        screenshot_path=str(source),
    )


def test_preview_binds_redacted_screenshot_hash(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)

    preview = build_preview(_input(source), tmp_path / "workspace", FakeOcr())

    relative_output = Path(preview.redacted.redacted_screenshot_path or "")
    output = tmp_path / "workspace" / relative_output
    assert relative_output.as_posix() == f"{preview.case_id}/redacted.png"
    assert preview.redacted.redacted_screenshot_sha256 == sha256_file(output)
    assert preview.preview_hash != preview.source_hash


def test_build_preview_revalidates_model_copy_bypasses(tmp_path: Path) -> None:
    valid = InputEnvelope(case_id=new_case_id(), error_text="Traceback")
    invalid_environment = valid.model_copy(update={"environment": {"python": 313}})
    missing_primary = valid.model_copy(update={"error_text": None, "screenshot_path": None})
    unexpected_field = valid.model_copy(update={"raw_secret": "must-not-pass"})

    with pytest.raises(ValidationError):
        build_preview(invalid_environment, tmp_path / "workspace", FakeOcr())
    with pytest.raises(ValidationError):
        build_preview(missing_primary, tmp_path / "workspace", FakeOcr())
    with pytest.raises(ValidationError):
        build_preview(unexpected_field, tmp_path / "workspace", FakeOcr())


def test_preview_hashes_and_json_are_workspace_independent(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)
    value = _input(source)

    first = build_preview(value, tmp_path / "workspace-a", FakeOcr())
    second = build_preview(value, tmp_path / "workspace-b", FakeOcr())

    assert first.source_hash == second.source_hash
    assert first.preview_hash == second.preview_hash
    assert str(tmp_path) not in first.model_dump_json()


@pytest.mark.parametrize(
    "updates",
    [
        {"redacted_screenshot_path": "redacted.png"},
        {"redacted_screenshot_sha256": "a" * 64},
    ],
)
def test_redacted_screenshot_path_and_hash_are_atomic(updates: dict[str, str]) -> None:
    with pytest.raises(ValidationError, match="must be provided together"):
        RedactedFields.model_validate(updates)


def test_source_hash_changes_when_original_screenshot_bytes_change(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)
    value = _input(source)
    first = build_preview(value, tmp_path / "workspace", FakeOcr())

    Image.new("RGB", (200, 80), "gray").save(source)
    second = build_preview(value, tmp_path / "workspace", FakeOcr())

    assert first.source_hash != second.source_hash


def test_source_hash_ignores_local_path_for_identical_screenshot_bytes(tmp_path: Path) -> None:
    first_source = tmp_path / "first.png"
    second_source = tmp_path / "second.png"
    Image.new("RGB", (200, 80), "white").save(first_source)
    second_source.write_bytes(first_source.read_bytes())
    case_id = new_case_id()
    first_value = InputEnvelope(
        case_id=case_id, error_text="Traceback", screenshot_path=str(first_source)
    )
    second_value = InputEnvelope(
        case_id=case_id, error_text="Traceback", screenshot_path=str(second_source)
    )

    first = build_preview(first_value, tmp_path / "workspace-a", FakeOcr())
    second = build_preview(second_value, tmp_path / "workspace-b", FakeOcr())

    assert first.source_hash == second.source_hash
    assert first.preview_hash == second.preview_hash


def test_same_input_produces_stable_preview_hash(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)
    value = _input(source)

    first = build_preview(value, tmp_path / "workspace", FakeOcr())
    second = build_preview(value, tmp_path / "workspace", FakeOcr())

    assert first.source_hash == second.source_hash
    assert first.preview_hash == second.preview_hash


def test_text_only_preview_remains_hash_compatible(tmp_path: Path) -> None:
    value = InputEnvelope(case_id=new_case_id(), error_text="mail=student@example.com")

    expected = redact_input(value)
    actual = build_preview(value, tmp_path / "workspace", FakeOcr())

    assert actual.source_hash == expected.source_hash
    assert actual.preview_hash == expected.preview_hash


def test_ocr_failure_returns_no_preview_and_writes_no_output(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)
    value = _input(source)
    output = tmp_path / "workspace" / str(value.case_id) / "redacted.png"

    with pytest.raises(OcrUnavailable) as caught:
        build_preview(value, tmp_path / "workspace", FailingOcr())

    assert str(source) not in str(caught.value)
    assert not output.exists()


def test_failed_rebuild_removes_stale_same_case_output(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)
    value = _input(source)
    workspace = tmp_path / "workspace"
    output = workspace / str(value.case_id) / "redacted.png"
    build_preview(value, workspace, FakeOcr())
    assert output.exists()

    with pytest.raises(OcrUnavailable):
        build_preview(value, workspace, FailingOcr())

    assert not output.exists()


def test_outputs_are_isolated_by_case(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)
    first_value = _input(source)
    second_value = _input(source)

    first = build_preview(first_value, tmp_path / "workspace", FakeOcr())
    second = build_preview(second_value, tmp_path / "workspace", FakeOcr())

    first_path = Path(first.redacted.redacted_screenshot_path or "")
    second_path = Path(second.redacted.redacted_screenshot_path or "")
    assert first_path != second_path
    assert first_path.parent.name == str(first_value.case_id)
    assert second_path.parent.name == str(second_value.case_id)


def test_case_output_cannot_escape_workspace_through_link(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)
    value = _input(source)
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    try:
        (workspace / str(value.case_id)).symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory links are unavailable on this Windows host")

    with pytest.raises(ValueError, match="escapes workspace"):
        build_preview(value, workspace, FakeOcr())

    assert not (outside / "redacted.png").exists()


def test_output_cannot_overwrite_source_screenshot(tmp_path: Path) -> None:
    value = _input(tmp_path / "placeholder.png")
    source = tmp_path / "workspace" / str(value.case_id) / "redacted.png"
    source.parent.mkdir(parents=True)
    Image.new("RGB", (200, 80), "white").save(source)
    value = value.model_copy(update={"screenshot_path": str(source)})

    with pytest.raises(UnsafeRedactionPath):
        build_preview(value, tmp_path / "workspace", FakeOcr())


def test_approved_preview_uploads_only_the_redacted_screenshot(tmp_path: Path) -> None:
    class RecordingBackend:
        def __init__(self) -> None:
            self.uploads: list[Path] = []
            self.workflow_inputs: list[dict[str, object]] = []

        def upload_file(self, path: Path, user: str) -> FileUploadResult:
            del user
            self.uploads.append(path)
            return FileUploadResult(file_id="redacted-file", filename=path.name, backend="fake")

        def run_workflow(self, inputs: dict[str, object], user: str) -> object:
            del user
            self.workflow_inputs.append(inputs)
            return {"ok": True}

    source = tmp_path / "source.png"
    Image.new("RGB", (200, 80), "white").save(source)
    workspace = tmp_path / "workspace"
    preview = build_preview(_input(source), workspace, FakeOcr())
    approved = approve_preview(preview, b"preview-approval-key-at-least-32-bytes")
    backend = RecordingBackend()

    result = CloudGateway(
        backend,
        approval_key=b"preview-approval-key-at-least-32-bytes",
        redacted_root=workspace,
    ).run(approved)

    expected = workspace / str(preview.case_id) / "redacted.png"
    assert result == {"ok": True}
    assert backend.uploads == [expected]
    assert source not in backend.uploads
    assert backend.workflow_inputs[0]["screenshot_file_id"] == "redacted-file"
    with Image.open(expected) as image:
        assert image.convert("RGB").getpixel((50, 20)) == (0, 0, 0)


def test_rapidocr_adapter_is_lazy_and_normalizes_v3_result() -> None:
    calls: list[str] = []

    class Engine:
        def __call__(self, path: str):
            calls.append(path)
            return type(
                "Result",
                (),
                {
                    "boxes": [[[0.4, 1.5], [9.6, 1.5], [9.6, 8.5], [0.4, 8.5]]],
                    "txts": ["student@example.com"],
                    "scores": [0.875],
                },
            )()

    factories: list[bool] = []
    backend = RapidOcrBackend(factory=lambda: (factories.append(True), Engine())[1])
    assert factories == []
    assert "Engine" not in repr(backend)

    tokens = backend.recognize(Path("synthetic.png"))

    assert factories == [True]
    assert len(tokens) == 1
    assert tokens[0].box == ((0, 2), (10, 2), (10, 8), (0, 8))
    assert tokens[0].text == "student@example.com"
    assert tokens[0].score == 0.875
    backend.recognize(Path("synthetic.png"))
    assert factories == [True]


def test_rapidocr_adapter_accepts_injected_engine_without_factory() -> None:
    result = type("EmptyResult", (), {"boxes": None, "txts": None, "scores": None})()
    backend = RapidOcrBackend(engine=lambda path: result)

    assert backend.recognize(Path("synthetic.png")) == []


@pytest.mark.parametrize(
    "result",
    [
        object(),
        type("BadLengths", (), {"boxes": [], "txts": ["secret"], "scores": [0.9]})(),
        type("BadText", (), {"boxes": [[[0, 0]] * 4], "txts": [1], "scores": [0.9]})(),
        type("BadScore", (), {"boxes": [[[0, 0]] * 4], "txts": ["secret"], "scores": [2.0]})(),
    ],
)
def test_rapidocr_adapter_wraps_normalization_errors_without_leaks(result: object) -> None:
    backend = RapidOcrBackend(factory=lambda: lambda path: result)

    with pytest.raises(OcrUnavailable) as caught:
        backend.recognize(Path(r"C:\private\secret.png"))

    assert "secret.png" not in str(caught.value)
    assert "secret" not in str(caught.value)


def test_rapidocr_adapter_wraps_initialization_and_inference_errors() -> None:
    def failing_factory():
        raise RuntimeError(r"model failed at C:\private\model.onnx")

    backend = RapidOcrBackend(factory=failing_factory)
    with pytest.raises(OcrUnavailable) as initialized:
        backend.recognize(Path("input.png"))
    assert "model.onnx" not in str(initialized.value)

    def failing_engine(path: str):
        raise RuntimeError(f"bad OCR text and path {path}")

    backend = RapidOcrBackend(factory=lambda: failing_engine)
    with pytest.raises(OcrUnavailable) as inferred:
        backend.recognize(Path(r"C:\private\secret.png"))
    assert "secret.png" not in str(inferred.value)
