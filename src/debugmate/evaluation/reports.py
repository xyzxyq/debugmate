"""Deterministic, privacy-safe Phase 09 evidence projections.

These renderers accept only the strict collector and prompt-comparison models.
They produce bytes for the Phase 09 runner to stage later; this module never
writes reports, screenshots, audio, or any Phase 10 media artifact itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from debugmate.evaluation.collector import CollectedCaseSource
from debugmate.evaluation.contracts import PromptComparison
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.privacy.output_scan import assert_export_safe


@dataclass(frozen=True, slots=True)
class RenderedProjection:
    """Canonical JSON plus a review-only Markdown view of the same safe data."""

    json_bytes: bytes
    markdown_bytes: bytes

    @property
    def canonical_json_bytes(self) -> bytes:
        return self.json_bytes

    @property
    def markdown(self) -> str:
        return self.markdown_bytes.decode("utf-8")

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.json_bytes)


def _display_sha256(value: str) -> str:
    """Keep an auditable fingerprint legible without resembling a credential token."""

    return ":".join(value[index : index + 8] for index in range(0, len(value), 8))


def _projection(payload: dict[str, Any], markdown: str) -> RenderedProjection:
    """Apply the export boundary before returning canonical, stable bytes."""

    assert_export_safe(payload)
    assert_export_safe(markdown)
    return RenderedProjection(
        json_bytes=canonical_json_bytes(payload),
        markdown_bytes=markdown.encode("utf-8"),
    )


def _validated_rows(rows: tuple[CollectedCaseSource, ...]) -> tuple[CollectedCaseSource, ...]:
    validated: list[CollectedCaseSource] = []
    for row in rows:
        payload = row.model_dump()
        assert_export_safe(payload)
        validated.append(CollectedCaseSource.model_validate(payload, strict=True))
    return tuple(validated)


def _case_row(row: CollectedCaseSource) -> dict[str, Any]:
    return {
        "case_id": row.case_id,
        "source": {"path": row.source_path, "sha256": row.source_sha256},
        "actual_status": row.actual_status.value,
        "execution_backend": row.execution_backend,
        "provenance": row.provenance,
        "availability": row.availability.model_dump(mode="json"),
        "privacy_status": row.privacy_status,
        "citation": {"status": row.citation_status, "count": row.citation_count},
        "limitation": row.limitation,
        "result_bundle_path": row.result_bundle_path,
        "phase10_eligible": row.phase10_eligible,
        "exclusion_reasons": list(row.exclusion_reasons),
    }


def render_case_report(rows: tuple[CollectedCaseSource, ...]) -> RenderedProjection:
    """Render the exact case table without inferring any missing evidence."""

    validated = _validated_rows(rows)
    payload = {
        "report_version": "phase9-case-results-1.0",
        "cases": [_case_row(row) for row in validated],
    }
    lines = [
        "# Current Evaluation Cases",
        "",
        "| Case | Status | Backend | Provenance | Phase 10 eligible | Exclusion |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in validated:
        exclusion = ", ".join(row.exclusion_reasons) if row.exclusion_reasons else "none"
        cells = (
            row.case_id,
            row.actual_status.value,
            row.execution_backend,
            row.provenance,
            str(row.phase10_eligible).lower(),
            exclusion,
        )
        lines.append("| " + " | ".join(cells) + " |")
    return _projection(payload, "\n".join(lines) + "\n")


def _validated_comparison(comparison: PromptComparison) -> PromptComparison:
    return PromptComparison.model_validate(comparison.model_dump(), strict=True)


def _prompt_row(row: Any) -> dict[str, Any]:
    return {
        "version": row.version.value,
        "prompt_file": row.prompt_file.path.path,
        "prompt_sha256": row.prompt_file.sha256,
        "conclusion": row.conclusion.model_dump(mode="json"),
        "accepted_diagnosis_sha256": row.accepted_diagnosis_sha256,
        "accepted_result_sha256": row.accepted_result_sha256,
        "candidate_sha256": row.candidate_sha256,
        "source_evidence_kind": row.source_evidence.kind.value,
        "source_evidence_reference": row.source_evidence.reference.path.path,
        "source_evidence_sha256": row.source_evidence.reference.sha256,
        "provenance": row.provenance.value,
        "status": row.status,
    }


def render_prompt_comparison(comparison: PromptComparison) -> RenderedProjection:
    """Render V1--V4 bindings only after the exact same-case contract is revalidated."""

    validated = _validated_comparison(comparison)
    payload = {
        "report_version": "phase9-prompt-comparison-1.0",
        "common_input": validated.common_input.model_dump(mode="json"),
        "accepted_v1": validated.accepted_v1.model_dump(mode="json"),
        "rows": [_prompt_row(row) for row in validated.rows],
    }
    lines = [
        "# Current Prompt Comparison",
        "",
        (
            "| Version | Provenance | Status | Conclusion | Prompt SHA-256 | "
            "Diagnosis SHA-256 | Result SHA-256 | Candidate SHA-256 | Source evidence |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in validated.rows:
        cells = (
            row.version.value,
            row.provenance.value,
            row.status,
            row.conclusion.code,
            _display_sha256(row.prompt_file.sha256),
            _display_sha256(row.accepted_diagnosis_sha256),
            _display_sha256(row.accepted_result_sha256),
            _display_sha256(row.candidate_sha256),
            row.source_evidence.reference.path.path,
        )
        lines.append("| " + " | ".join(cells) + " |")
    return _projection(payload, "\n".join(lines) + "\n")


def render_workflow_source(
    rows: tuple[CollectedCaseSource, ...], comparison: PromptComparison
) -> RenderedProjection:
    """Render the bounded source identity joining case and prompt evidence."""

    validated_rows = _validated_rows(rows)
    validated_comparison = _validated_comparison(comparison)
    payload = {
        "report_version": "phase9-workflow-source-1.0",
        "common_input": validated_comparison.common_input.model_dump(mode="json"),
        "case_sources": [
            {
                "case_id": row.case_id,
                "source_path": row.source_path,
                "source_sha256": row.source_sha256,
                "execution_backend": row.execution_backend,
                "provenance": row.provenance,
                "phase10_eligible": row.phase10_eligible,
                "exclusion_reasons": list(row.exclusion_reasons),
            }
            for row in validated_rows
        ],
        "prompt_bindings": [_prompt_row(row) for row in validated_comparison.rows],
    }
    lines = [
        "# Workflow Source Evidence",
        "",
        "The following source fingerprints are the only inputs represented by this projection.",
        "",
    ]
    for row in validated_rows:
        fingerprint = _display_sha256(row.source_sha256)
        eligible = str(row.phase10_eligible).lower()
        line = f"- {row.case_id}: {fingerprint} ({row.execution_backend}; eligible={eligible})"
        lines.append(line)
    return _projection(payload, "\n".join(lines) + "\n")


def render_phase10_source(rows: tuple[CollectedCaseSource, ...]) -> RenderedProjection:
    """Render the Phase 10 input ledger while retaining ineligible exclusion reasons."""

    validated = _validated_rows(rows)
    payload = {
        "manifest_version": "phase10-source-1.0",
        "sources": [
            {
                "case_id": row.case_id,
                "source_path": row.source_path,
                "source_sha256": row.source_sha256,
                "execution_backend": row.execution_backend,
                "provenance": row.provenance,
                "limitation": row.limitation,
                "phase10_eligible": row.phase10_eligible,
                "exclusion_reasons": list(row.exclusion_reasons),
            }
            for row in validated
        ],
    }
    lines = [
        "# Phase 10 Source Ledger",
        "",
        "Only rows marked `phase10_eligible=true` may be consumed by a later media phase.",
        "",
    ]
    for row in validated:
        exclusion = ", ".join(row.exclusion_reasons) if row.exclusion_reasons else "none"
        lines.append(
            f"- {row.case_id}: eligible={str(row.phase10_eligible).lower()}; reason={exclusion}"
        )
    return _projection(payload, "\n".join(lines) + "\n")
