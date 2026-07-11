"""Deterministic, value-free redaction for DebugMate text inputs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from debugmate.hashing import (
    UnsafeArtifactPath,
    canonical_json_bytes,
    resolve_artifact_path,
    sha256_bytes,
)
from debugmate.privacy.models import (
    InputEnvelope,
    PreviewBundle,
    RedactedFields,
    RedactionAudit,
    SecretCandidate,
    SecretKind,
)
from debugmate.privacy.ocr import OcrBackend
from debugmate.privacy.patterns import REDACTION_RULES, field_kind_rule

RULE_VERSION = "privacy-rules-v1"


@dataclass(frozen=True, slots=True)
class _RankedCandidate:
    candidate: SecretCandidate
    priority: int


def _candidate(
    *,
    kind: SecretKind,
    field: str,
    start: int,
    end: int,
    rule_id: str,
    confidence: float,
    matched: str,
) -> SecretCandidate:
    return SecretCandidate(
        kind=kind,
        field=field,
        start=start,
        end=end,
        rule_id=rule_id,
        confidence=confidence,
        match_sha256=sha256_bytes(matched.encode("utf-8")),
    )


def scan_text(field: str, text: str) -> list[SecretCandidate]:
    """Return non-overlapping findings without retaining matched values."""

    ranked: list[_RankedCandidate] = []
    field_name = field.rsplit(".", 1)[-1].lower()
    field_rule = field_kind_rule(field_name)
    if field_rule is not None and text:
        kind, rule_id, confidence, priority = field_rule
        ranked.append(
            _RankedCandidate(
                _candidate(
                    kind=kind,
                    field=field,
                    start=0,
                    end=len(text),
                    rule_id=rule_id,
                    confidence=confidence,
                    matched=text,
                ),
                priority,
            )
        )

    for priority, rule in enumerate(REDACTION_RULES):
        for match in rule.pattern.finditer(text):
            ranked.append(
                _RankedCandidate(
                    _candidate(
                        kind=rule.kind,
                        field=field,
                        start=match.start(),
                        end=match.end(),
                        rule_id=rule.rule_id,
                        confidence=rule.confidence,
                        matched=match.group(0),
                    ),
                    priority,
                )
            )

    selected: list[_RankedCandidate] = []
    for item in sorted(
        ranked,
        key=lambda value: (
            value.priority,
            -(value.candidate.end - value.candidate.start),
            value.candidate.start,
        ),
    ):
        candidate = item.candidate
        if any(
            candidate.start < existing.candidate.end
            and existing.candidate.start < candidate.end
            for existing in selected
        ):
            continue
        selected.append(item)

    return sorted(
        (item.candidate for item in selected),
        key=lambda value: (value.field, value.start, value.end, value.rule_id),
    )


def apply_candidates(text: str, candidates: Sequence[SecretCandidate]) -> str:
    """Replace candidate spans from right to left so offsets remain valid."""

    output = text
    for item in sorted(candidates, key=lambda value: value.start, reverse=True):
        output = (
            output[: item.start]
            + f"[REDACTED:{item.kind.value}]"
            + output[item.end :]
        )
    return output


def _redact_optional(field: str, text: str | None) -> tuple[str | None, list[SecretCandidate]]:
    if text is None:
        return None, []
    candidates = scan_text(field, text)
    return apply_candidates(text, candidates), candidates


def redact_input(value: InputEnvelope) -> PreviewBundle:
    """Build a stable, value-free preview from one local input envelope."""

    error_text, error_candidates = _redact_optional("error_text", value.error_text)
    code, code_candidates = _redact_optional("code", value.code)

    environment: dict[str, str] = {}
    environment_candidates: list[SecretCandidate] = []
    for key in sorted(value.environment):
        field = f"environment.{key}"
        candidates = scan_text(field, value.environment[key])
        environment[key] = apply_candidates(value.environment[key], candidates)
        environment_candidates.extend(candidates)

    candidates = sorted(
        [*error_candidates, *code_candidates, *environment_candidates],
        key=lambda item: (item.field, item.start, item.end, item.rule_id),
    )
    counts = Counter(item.kind for item in candidates)
    audit = RedactionAudit(
        candidate_count=len(candidates),
        counts_by_kind={kind: counts[kind] for kind in sorted(counts, key=lambda item: item.value)},
    )
    redacted = RedactedFields(
        error_text=error_text,
        code=code,
        environment=environment,
        redacted_screenshot_path=None,
        redacted_screenshot_sha256=None,
    )

    source_hash = sha256_bytes(canonical_json_bytes(value.model_dump(mode="json")))
    preview_payload = {
        "case_id": value.case_id,
        "redacted": redacted.model_dump(mode="json"),
        "candidates": [item.model_dump(mode="json") for item in candidates],
        "audit": audit.model_dump(mode="json"),
        "source_hash": source_hash,
        "rule_version": RULE_VERSION,
    }
    preview_hash = sha256_bytes(canonical_json_bytes(preview_payload))
    return PreviewBundle(
        case_id=value.case_id,
        redacted=redacted,
        candidates=candidates,
        audit=audit,
        source_hash=source_hash,
        preview_hash=preview_hash,
        rule_version=RULE_VERSION,
        created_at_utc=datetime.now(UTC),
    )


def build_preview(
    value: InputEnvelope,
    workspace: Path,
    ocr_backend: OcrBackend,
) -> PreviewBundle:
    """Build a text preview and, when present, a locally redacted screenshot."""

    value = InputEnvelope.model_validate(dict(value.__dict__))
    preview = redact_input(value)
    if value.screenshot_path is None:
        return preview

    from debugmate.privacy.image_redactor import (
        RedactionWriteError,
        UnsafeRedactionPath,
        redact_screenshot,
    )

    workspace_path = Path(workspace).resolve()
    relative_output = Path(str(value.case_id)) / "redacted.png"
    try:
        output = resolve_artifact_path(workspace_path, relative_output)
    except UnsafeArtifactPath:
        raise ValueError("redacted screenshot output escapes workspace") from None
    source_path = Path(value.screenshot_path)
    if source_path.resolve() == output:
        raise UnsafeRedactionPath("redacted output must differ from the source screenshot")
    try:
        output.unlink(missing_ok=True)
    except OSError:
        raise RedactionWriteError("stale redacted screenshot could not be removed") from None
    result = redact_screenshot(source_path, output, ocr_backend)
    redacted = RedactedFields.model_validate(
        {
            **preview.redacted.model_dump(mode="json"),
            "redacted_screenshot_path": relative_output.as_posix(),
            "redacted_screenshot_sha256": result.output_sha256,
        }
    )
    source_payload = value.model_dump(mode="json")
    source_payload.pop("screenshot_path", None)
    source_payload["screenshot_sha256"] = result.source_sha256
    source_hash = sha256_bytes(canonical_json_bytes(source_payload))
    preview_payload = {
        "case_id": value.case_id,
        "redacted": redacted.model_dump(mode="json"),
        "candidates": [item.model_dump(mode="json") for item in preview.candidates],
        "audit": preview.audit.model_dump(mode="json"),
        "source_hash": source_hash,
        "rule_version": RULE_VERSION,
    }
    return PreviewBundle(
        case_id=value.case_id,
        redacted=redacted,
        candidates=preview.candidates,
        audit=preview.audit,
        source_hash=source_hash,
        preview_hash=sha256_bytes(canonical_json_bytes(preview_payload)),
        rule_version=RULE_VERSION,
        created_at_utc=preview.created_at_utc,
    )
