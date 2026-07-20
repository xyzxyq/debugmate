from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from debugmate.contracts import ErrorCategory
from debugmate.knowledge.models import KnowledgeSource, SourceRegistry, load_registry

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "knowledge" / "sources.json"
SCHEMA_PATH = ROOT / "knowledge" / "manifest.schema.json"

REQUIRED_MANIFEST_FIELDS = {
    "source_id",
    "title",
    "url",
    "final_url",
    "product",
    "version_scope",
    "platform",
    "allowed_domain",
    "heading_patterns",
    "error_categories",
    "retrieved_at",
    "status_code",
    "etag",
    "last_modified",
    "sha256",
    "license_or_terms_note",
    "selection_reason",
}

EXPECTED_URLS = {
    "python-errors": "https://docs.python.org/3/tutorial/errors.html",
    "python-venv": "https://docs.python.org/3/library/venv.html",
    "python-import": "https://docs.python.org/3/reference/import.html",
    "pip-resolution": "https://pip.pypa.io/en/stable/topics/dependency-resolution/",
    "pip-user-guide": "https://pip.pypa.io/en/stable/user_guide/",
    "pytorch-cuda": "https://docs.pytorch.org/docs/2.13/notes/cuda.html",
    "pytorch-serialization": "https://docs.pytorch.org/docs/2.13/notes/serialization.html",
    "pytorch-tensor-view": (
        "https://docs.pytorch.org/docs/2.13/generated/torch.Tensor.view.html"
    ),
    "cuda-compatibility": "https://docs.nvidia.com/deploy/cuda-compatibility/latest/",
    "cuda-windows-install": (
        "https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/"
    ),
    "hf-installation": "https://huggingface.co/docs/transformers/en/installation",
    "hf-cache": "https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache",
    "ultralytics-install": "https://docs.ultralytics.com/quickstart",
    "ultralytics-predict": "https://docs.ultralytics.com/modes/predict",
    "windows-env": (
        "https://learn.microsoft.com/en-us/powershell/module/"
        "microsoft.powershell.core/about/about_environment_variables?view=powershell-7.5"
    ),
    "windows-policy": (
        "https://learn.microsoft.com/en-us/powershell/module/"
        "microsoft.powershell.core/about/about_execution_policies?view=powershell-7.5"
    ),
    "windows-path-format": (
        "https://learn.microsoft.com/en-us/dotnet/standard/io/file-path-formats"
    ),
}

EXPECTED_DRIFTED_HEADING_PATTERNS = {
    "pytorch-cuda": [
        r"^CUDA semantics(?: #)?$",
        r"^Asynchronous execution(?: #)?$",
        r"^Memory management(?: #)?$",
    ],
    "pytorch-serialization": [
        r"^Serialization semantics(?: #)?$",
        r"^Saving and loading tensors(?: #)?$",
        r"^torch\.load with weights_only=True(?: #)?$",
    ],
    "pytorch-tensor-view": [r"^torch\.Tensor\.view(?: #)?$"],
    "cuda-compatibility": [r"^CUDA Compatibility(?: #)?$"],
    "ultralytics-install": [
        r"^(?:Link to this section )?Install Ultralytics(?: #)?$",
        r"^(?:Link to this section )?Headless Server Installation(?: #)?$",
        r"^(?:Link to this section )?Use Ultralytics with Python(?: #)?$",
    ],
    "ultralytics-predict": [
        r"^(?:Link to this section )?Model Prediction with Ultralytics YOLO(?: #)?$",
        r"^(?:Link to this section )?Key Features of Predict Mode(?: #)?$",
        r"^(?:Link to this section )?Inference Sources(?: #)?$",
    ],
    "windows-env": [
        r"^about_Environment_Variables$",
        r"^Use the variable syntax$",
        r"^Create persistent environment variables in Windows$",
        r"^Path information$",
    ],
}


def _valid_source(**overrides: object) -> dict[str, object]:
    source: dict[str, object] = {
        "source_id": "python-errors",
        "title": "Python Errors and Exceptions",
        "url": EXPECTED_URLS["python-errors"],
        "product": "python",
        "version_scope": "Python 3",
        "platform": "cross-platform",
        "allowed_domain": "docs.python.org",
        "heading_patterns": ["Errors and Exceptions", "Exceptions"],
        "error_categories": [ErrorCategory.PYTHON_RUNTIME],
        "license_or_terms_note": "Python documentation license and terms apply.",
        "selection_reason": "Canonical language reference for Python runtime failures.",
    }
    source.update(overrides)
    return source


def _valid_manifest_entry() -> dict[str, object]:
    return {
        "source_id": "python-errors",
        "title": "Python Tutorial: Errors and Exceptions",
        "url": EXPECTED_URLS["python-errors"],
        "final_url": EXPECTED_URLS["python-errors"],
        "product": "python",
        "version_scope": "Python 3",
        "platform": "cross-platform",
        "allowed_domain": "docs.python.org",
        "heading_patterns": ["Syntax Errors", "Exceptions"],
        "error_categories": ["python_runtime"],
        "retrieved_at": "2026-07-11T08:30:00Z",
        "status_code": 200,
        "etag": '"python-errors-v1"',
        "last_modified": None,
        "sha256": "a" * 64,
        "license_or_terms_note": "Python documentation license applies.",
        "selection_reason": "Canonical Python runtime error reference.",
    }


def _manifest_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def test_registry_contains_exact_curated_official_urls() -> None:
    registry = load_registry(REGISTRY_PATH)

    assert len(registry.sources) == 17
    assert {source.source_id: source.url for source in registry.sources} == EXPECTED_URLS


def test_registry_covers_exact_product_families() -> None:
    registry = load_registry(REGISTRY_PATH)
    counts = Counter(source.product for source in registry.sources)

    assert set(counts) == {
        "python",
        "pip",
        "pytorch",
        "cuda",
        "huggingface",
        "ultralytics",
        "windows",
    }
    assert counts == {
        "python": 3,
        "pip": 2,
        "pytorch": 3,
        "cuda": 2,
        "huggingface": 2,
        "ultralytics": 2,
        "windows": 3,
    }


def test_registry_entries_have_non_empty_extraction_and_category_metadata() -> None:
    registry = load_registry(REGISTRY_PATH)

    assert all(source.heading_patterns for source in registry.sources)
    assert all(source.error_categories for source in registry.sources)
    assert all(source.license_or_terms_note.strip() for source in registry.sources)
    assert all(source.selection_reason.strip() for source in registry.sources)


def test_drifted_sources_keep_live_verified_heading_patterns() -> None:
    registry = load_registry(REGISTRY_PATH)
    by_id = {source.source_id: source for source in registry.sources}

    assert {
        source_id: by_id[source_id].heading_patterns
        for source_id in EXPECTED_DRIFTED_HEADING_PATTERNS
    } == EXPECTED_DRIFTED_HEADING_PATTERNS


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", "http://docs.python.org/3/tutorial/errors.html"),
        ("allowed_domain", "python.org"),
        ("error_categories", []),
        ("heading_patterns", []),
    ],
)
def test_source_rejects_unsafe_or_incomplete_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        KnowledgeSource.model_validate(_valid_source(**{field: value}), strict=True)


def test_source_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        KnowledgeSource.model_validate(_valid_source(retrieved_at="2026-07-11"), strict=True)


@pytest.mark.parametrize("duplicate_field", ["source_id", "url"])
def test_registry_rejects_duplicate_ids_and_urls(duplicate_field: str) -> None:
    first = _valid_source()
    second = _valid_source(
        source_id="python-venv",
        url=EXPECTED_URLS["python-venv"],
    )
    second[duplicate_field] = first[duplicate_field]

    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(
            {"registry_version": "1.0.0", "sources": [first, second]},
            strict=True,
        )


def test_registry_rejects_unknown_top_level_fields() -> None:
    with pytest.raises(ValidationError):
        SourceRegistry.model_validate(
            {
                "registry_version": "1.0.0",
                "sources": [_valid_source()],
                "comment": "not part of the contract",
            },
            strict=True,
        )


def test_committed_manifest_schema_is_strict_and_keeps_audit_fields() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["type"] == "array"
    assert schema["items"]["additionalProperties"] is False
    assert set(schema["items"]["required"]) == REQUIRED_MANIFEST_FIELDS


def test_realistic_fetched_manifest_is_valid() -> None:
    _manifest_validator().validate([_valid_manifest_entry()])


@pytest.mark.parametrize(
    "missing_field",
    [
        "source_id",
        "allowed_domain",
        "heading_patterns",
        "error_categories",
        "selection_reason",
        "final_url",
        "status_code",
        "etag",
        "last_modified",
    ],
)
def test_fetched_manifest_rejects_missing_audit_evidence(missing_field: str) -> None:
    entry = _valid_manifest_entry()
    del entry[missing_field]

    errors = list(_manifest_validator().iter_errors([entry]))

    assert errors
    assert any(error.validator == "required" for error in errors)


def test_registry_file_is_valid_against_generated_model_schema() -> None:
    raw = REGISTRY_PATH.read_text(encoding="utf-8")

    registry = SourceRegistry.model_validate_json(raw, strict=True)
    assert registry.model_dump(mode="json") == json.loads(raw)
