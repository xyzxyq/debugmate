from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image

from debugmate.hashing import sha256_file
from debugmate.privacy.models import ApprovedRedactedInput, RedactedFields

pytestmark = pytest.mark.cloud


def test_live_vlm_is_candidate_only_through_production_chain(tmp_path: Path) -> None:
    from debugmate.diagnosis.extraction import SourceKind
    from debugmate.diagnosis.providers import (
        DifyVlmCandidateProvider,
        ProductionExtractionProvider,
    )

    api_key = os.getenv("DEBUGMATE_VLM_API_KEY")
    endpoint = os.getenv("DEBUGMATE_VLM_ENDPOINT")
    if not api_key or not endpoint:
        pytest.skip("live VLM credentials are not configured")
    screenshot = tmp_path / "cloud.png"
    Image.new("RGB", (640, 160), "white").save(screenshot)
    approved = ApprovedRedactedInput(
        case_id="case_0123456789abcdef0123456789abcdef",
        redacted=RedactedFields(
            error_text="ModuleNotFoundError: No module named 'fictional_pkg'",
            redacted_screenshot_path="cloud.png",
            redacted_screenshot_sha256=sha256_file(screenshot),
        ),
        preview_hash="1" * 64,
        approval_id="approval_cloud_smoke",
        approval_signature="2" * 64,
        approved_at_utc=datetime(2026, 7, 12, tzinfo=UTC),
    )

    class EmptyOcr:
        def recognize(self, path: Path):
            return []

    vlm = DifyVlmCandidateProvider(endpoint=endpoint, api_key=api_key)
    record = ProductionExtractionProvider(
        redacted_root=tmp_path, ocr_backend=EmptyOcr(), vlm_candidate_provider=vlm
    ).extract(approved)
    assert vlm.backend_name == "dify-vlm"
    assert record.candidates
    assert all(candidate.source_kind is SourceKind.VLM for candidate in record.candidates)
    assert not hasattr(record, "facts")
