# Phase 2 Screenshot Redaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate terminal screenshots, OCR sensitive candidates locally, create irreversible pixel redactions, and bind the resulting image into the same preview/approval contract.

**Architecture:** An OCR protocol isolates RapidOCR from deterministic tests. `ScreenshotRedactor` validates real image bytes, maps OCR tokens through the text scanner, expands/clamps boxes, paints opaque rectangles with Pillow, strips metadata and emits an audit containing hashes and boxes but no recognized secret text.

**Tech Stack:** Pillow 12.3.0, RapidOCR 3.9.1, ONNX Runtime CPU 1.27.0, Python 3.13, pytest.

## Global Constraints

- Only PNG/JPEG, maximum 10 MiB and 20 megapixels; identify format from bytes, not extension.
- OCR and redaction run locally; original screenshot is never uploaded or committed.
- Tests use generated fictional screenshots and a fake OCR backend; default suite never downloads OCR models.
- Redaction rectangles are opaque and image metadata is removed.
- OCR failure blocks screenshot upload and never silently falls back to the original image.

---

### Task 1: Image Validation and OCR Port

**Files:**
- Modify: `pyproject.toml`
- Create: `src/debugmate/privacy/ocr.py`
- Create: `src/debugmate/privacy/image_models.py`
- Test: `tests/privacy/test_image_validation.py`

**Interfaces:**
- Produces: `OcrToken(text, box, score)`, `OcrBackend.recognize(path)`, `ValidatedImage`.

- [ ] **Step 1: Write failing tests for byte format and limits**

```python
def test_extension_cannot_disguise_non_image(tmp_path):
    path = tmp_path / "fake.png"; path.write_bytes(b"not an image")
    with pytest.raises(InvalidScreenshot): validate_screenshot(path)

def test_large_dimensions_are_rejected(tmp_path):
    path = write_png(tmp_path, size=(5000, 5000))
    with pytest.raises(InvalidScreenshot, match="20 megapixels"): validate_screenshot(path)
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/privacy/test_image_validation.py`.

- [ ] **Step 3: Add dependencies and models**

Pin `Pillow==12.3.0`, `rapidocr==3.9.1`, `onnxruntime==1.27.0`. Define `OcrBackend` as a runtime-checkable protocol and immutable `OcrToken` with four integer corner points and strict score `0..1`.

- [ ] **Step 4: Implement `validate_screenshot(path)`**

Open with Pillow, call `verify()`, reopen and enforce `format in {PNG, JPEG}`, file size `<= 10*1024*1024`, width/height positive and product `<= 20_000_000`. Return canonical width, height, format and source SHA-256.

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/privacy/test_image_validation.py`.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml src/debugmate/privacy/ocr.py src/debugmate/privacy/image_models.py tests/privacy/test_image_validation.py
git commit -m "feat(02-02): validate screenshots and define OCR port"
```

### Task 2: Deterministic Screenshot Redaction

**Files:**
- Create: `src/debugmate/privacy/image_redactor.py`
- Test: `tests/privacy/test_image_redactor.py`

**Interfaces:**
- Consumes: `OcrBackend`, `scan_text`, `ValidatedImage`.
- Produces: `redact_screenshot(source, output, backend) -> ScreenshotRedactionResult`.

- [ ] **Step 1: Write failing pixel/audit tests**

```python
def test_sensitive_ocr_box_is_opaque_and_audit_has_no_text(tmp_path):
    token = OcrToken(text=r"C:\Users\student\secret.py", box=((10,10),(180,10),(180,35),(10,35)), score=0.99)
    result = redact_screenshot(source, output, FakeOcr([token]))
    image = Image.open(output).convert("RGB")
    assert image.getpixel((50, 20)) == (0, 0, 0)
    assert "student" not in result.model_dump_json()
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/privacy/test_image_redactor.py`.

- [ ] **Step 3: Implement box mapping and redaction**

For each OCR token, reuse `scan_text("screenshot", token.text)`. If sensitive, compute min/max box coordinates, expand by 3 pixels, clamp to image bounds and draw a solid black rectangle. Save PNG with no `pnginfo`, EXIF or ICC profile. The audit stores kind, rule ID, score, clamped box and match SHA-256 only.

- [ ] **Step 4: Verify deterministic bytes and OCR failure behavior**

Run twice on the same source/fake OCR and assert equal output SHA-256. A backend exception must raise `OcrUnavailable`, leave no output image and never copy the source.

- [ ] **Step 5: Commit**

```powershell
git add src/debugmate/privacy/image_redactor.py tests/privacy/test_image_redactor.py
git commit -m "feat(02-02): redact screenshot pixels from OCR candidates"
```

### Task 3: RapidOCR Adapter and Preview Integration

**Files:**
- Create: `src/debugmate/privacy/rapidocr_backend.py`
- Modify: `src/debugmate/privacy/text_redactor.py`
- Modify: `src/debugmate/privacy/models.py`
- Test: `tests/privacy/test_preview_integration.py`
- Test: `tests/privacy/test_rapidocr_smoke.py`

**Interfaces:**
- Produces: `RapidOcrBackend`, `build_preview(input, workspace, ocr_backend)`.

- [ ] **Step 1: Write failing integration tests**

```python
def test_preview_binds_redacted_screenshot_hash(tmp_path):
    preview = build_preview(input_with_screenshot(source), tmp_path, FakeOcr([sensitive_token]))
    assert preview.redacted_screenshot_path.endswith("redacted.png")
    assert preview.redacted_screenshot_sha256 == sha256_file(Path(preview.redacted_screenshot_path))
    assert preview.preview_hash != preview.source_hash
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/privacy/test_preview_integration.py`.

- [ ] **Step 3: Implement RapidOCR result normalization**

Instantiate `RapidOCR()` lazily with the installed ONNX Runtime CPU backend. Normalize library polygons/text/scores into `OcrToken`; no model object appears in repr or manifests. Wrap initialization/inference errors as `OcrUnavailable` without raw paths.

- [ ] **Step 4: Add isolated OCR smoke marker**

Add pytest marker `ocr`. `test_rapidocr_smoke.py` creates a synthetic screenshot containing `C:\Users\student`, runs the real adapter and asserts at least one token; it is excluded from `-m "not cloud and not ocr"`. Default integration tests use the fake backend.

- [ ] **Step 5: Commit**

```powershell
git add src/debugmate/privacy/rapidocr_backend.py src/debugmate/privacy/models.py src/debugmate/privacy/text_redactor.py tests/privacy/test_preview_integration.py tests/privacy/test_rapidocr_smoke.py pyproject.toml
git commit -m "feat(02-02): integrate local OCR redaction preview"
```
