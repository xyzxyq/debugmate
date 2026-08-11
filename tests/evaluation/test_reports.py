from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from tests.evaluation.test_prompt_comparison import comparison_payload

from debugmate.evaluation.collector import collect_phase9_cases
from debugmate.evaluation.contracts import CaseRegistry, PromptComparison
from debugmate.evaluation.reports import (
    render_case_report,
    render_phase10_source,
    render_prompt_comparison,
    render_workflow_source,
)
from debugmate.privacy.output_scan import UnsafeExport, assert_export_safe

CASES_PATH = Path("evaluation/phase9/cases.json")
SCOPE_SCRIPT = Path("scripts/verify-phase9-scope.ps1")


def load_rows():
    registry = CaseRegistry.model_validate_json(CASES_PATH.read_text(encoding="utf-8"))
    return collect_phase9_cases(registry)


def test_validated_inputs_have_byte_identical_safe_json_and_markdown_projections() -> None:
    rows = load_rows()
    comparison = PromptComparison.model_validate(comparison_payload())

    reports = (
        render_case_report(rows),
        render_prompt_comparison(comparison),
        render_workflow_source(rows, comparison),
        render_phase10_source(rows),
    )
    rerun = (
        render_case_report(rows),
        render_prompt_comparison(comparison),
        render_workflow_source(rows, comparison),
        render_phase10_source(rows),
    )

    assert reports == rerun
    for report in reports:
        assert report.json_bytes == report.canonical_json_bytes
        assert report.markdown.encode("utf-8") == report.markdown_bytes
        assert_export_safe(json.loads(report.json_bytes))
        assert_export_safe(report.markdown)


def test_prompt_projection_exposes_every_binding_without_inventing_scores_or_costs() -> None:
    comparison = PromptComparison.model_validate(comparison_payload())
    projection = render_prompt_comparison(comparison)
    payload = json.loads(projection.json_bytes)

    assert [row["version"] for row in payload["rows"]] == ["v1", "v2", "v3", "v4"]
    assert [row["provenance"] for row in payload["rows"]] == [
        "verified_contract",
        "blocked",
        "blocked",
        "blocked",
    ]
    assert all(row["conclusion"]["code"] == "evidence_bound_diagnosis" for row in payload["rows"])
    assert all(len(row["accepted_diagnosis_sha256"]) == 64 for row in payload["rows"])
    assert all(len(row["accepted_result_sha256"]) == 64 for row in payload["rows"])
    assert all(len(row["candidate_sha256"]) == 64 for row in payload["rows"])
    assert all(row["source_evidence_reference"] for row in payload["rows"])
    assert "score" not in projection.markdown.lower()
    assert "cost" not in projection.markdown.lower()


def test_projection_rejects_unsafe_values_without_echoing_them() -> None:
    secret = "debugmate-phase9-private-token-0123456789"
    unsafe_row = load_rows()[0].model_copy(update={"limitation": f"api_key={secret}"})

    with pytest.raises(UnsafeExport) as caught:
        render_case_report((unsafe_row,))

    assert secret not in repr(caught.value)


def _run_scope(repository_root: Path, *, invocation: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCOPE_SCRIPT.resolve()),
            "-RepositoryRoot",
            str(repository_root),
            "-InvocationText",
            invocation,
        ],
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
    )


def _git(repository_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository_root), *args],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )


def test_scope_gate_rejects_frozen_media_drift_new_targets_and_course_builders(
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "scope-repository"
    (repository_root / "deliverables").mkdir(parents=True)
    frozen = repository_root / "deliverables" / "DebugMate-V0.1.pptx"
    frozen.write_bytes(b"baseline-pptx")
    _git(repository_root, "init")
    _git(repository_root, "config", "user.email", "phase9@example.invalid")
    _git(repository_root, "config", "user.name", "Phase 09 test")
    _git(repository_root, "add", "deliverables/DebugMate-V0.1.pptx")
    _git(repository_root, "commit", "-m", "baseline")

    assert _run_scope(repository_root).returncode == 0

    frozen.write_bytes(b"drifted-pptx")
    changed = _run_scope(repository_root)
    assert changed.returncode == 1
    assert "frozen_target_changed" in changed.stderr

    frozen.write_bytes(b"baseline-pptx")
    screenshot = repository_root / "evidence" / "course-v0.1" / "screenshots" / "new.png"
    screenshot.parent.mkdir(parents=True)
    screenshot.write_bytes(b"new-screenshot")
    new_target = _run_scope(repository_root)
    assert new_target.returncode == 1
    assert "frozen_target_new" in new_target.stderr

    builder = _run_scope(repository_root, invocation="python scripts/build-course-ppt.py")
    assert builder.returncode == 1
    assert "course_builder_forbidden" in builder.stderr
