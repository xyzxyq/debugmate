"""Optimistic-lock correction overlays for immutable case-fact revisions."""

from __future__ import annotations

import hmac

from pydantic import Field

from debugmate.contracts import CaseId
from debugmate.diagnosis.extraction import (
    CaseFact,
    CaseFacts,
    CorrectionProvenance,
    FieldId,
    SourceKind,
    StrictFrozenModel,
    correction_id_for,
    fact_id_for,
    facts_hash,
    normalize_value,
)
from debugmate.hashing import sha256_bytes
from debugmate.privacy.models import Sha256
from debugmate.privacy.output_scan import UnsafeExport, assert_export_safe


class CorrectionConflict(ValueError):
    """The overlay no longer describes the immutable base revision."""


class CorrectionRejected(ValueError):
    """The correction is invalid without echoing its untrusted values."""


class CorrectionOverlay(StrictFrozenModel):
    case_id: CaseId
    base_revision: int = Field(strict=True, ge=0)
    base_facts_sha256: Sha256
    field_id: FieldId
    fact_id: str = Field(pattern=r"^fact_[0-9a-f]{32}$")
    old_value_sha256: Sha256
    replacement: str = Field(min_length=1, max_length=2_000, repr=False)
    reason: str = Field(min_length=1, max_length=1_000, repr=False)


def apply_correction(base: CaseFacts, overlay: CorrectionOverlay) -> CaseFacts:
    """Create revision+1 after stable-target, privacy, and optimistic-lock checks."""

    if not isinstance(base, CaseFacts) or not isinstance(overlay, CorrectionOverlay):
        raise TypeError("apply_correction requires CaseFacts and CorrectionOverlay")
    base = CaseFacts.model_validate(base.model_dump(), strict=True)
    overlay = CorrectionOverlay.model_validate(overlay.model_dump(), strict=True)

    if overlay.case_id != base.case_id:
        raise CorrectionConflict("correction case does not match base facts")
    if overlay.base_revision != base.revision:
        raise CorrectionConflict("correction base revision is stale")
    if not hmac.compare_digest(overlay.base_facts_sha256, base.facts_sha256):
        raise CorrectionConflict("correction base facts hash is stale")

    target = next((fact for fact in base.facts if fact.fact_id == overlay.fact_id), None)
    if target is None or target.field_id is not overlay.field_id:
        raise CorrectionRejected("correction target is missing or mismatched")
    actual_old_hash = sha256_bytes(target.value.encode("utf-8"))
    if not hmac.compare_digest(overlay.old_value_sha256, actual_old_hash):
        raise CorrectionConflict("correction target value is stale")

    try:
        replacement = normalize_value(overlay.field_id, overlay.replacement)
        assert_export_safe(replacement)
        assert_export_safe(overlay.reason)
    except (ValueError, UnsafeExport):
        raise CorrectionRejected("correction replacement or reason is unsafe") from None
    if replacement == target.value:
        raise CorrectionRejected("correction is a no-op")

    new_value_hash = sha256_bytes(replacement.encode("utf-8"))
    reason_hash = sha256_bytes(overlay.reason.encode("utf-8"))
    provisional = CorrectionProvenance.model_construct(
        correction_id="correction_" + "0" * 32,
        base_revision=overlay.base_revision,
        field_id=overlay.field_id,
        fact_id=overlay.fact_id,
        base_facts_sha256=base.facts_sha256,
        old_value_sha256=actual_old_hash,
        new_value_sha256=new_value_hash,
        source_provenance_candidate_ids=list(target.provenance_candidate_ids),
        source_source_kinds=list(target.source_kinds),
        source_confidence=target.confidence,
        reason_sha256=reason_hash,
        reason=overlay.reason,
    )
    provenance = CorrectionProvenance(
        **{
            **provisional.model_dump(),
            "correction_id": correction_id_for(overlay.case_id, provisional),
        }
    )
    replacement_fact = CaseFact(
        fact_id=fact_id_for(overlay.field_id, replacement),
        field_id=overlay.field_id,
        value=replacement,
        provenance_candidate_ids=list(target.provenance_candidate_ids),
        source_kinds=sorted({*target.source_kinds, SourceKind.USER}, key=str),
        confidence=1.0,
    )
    revised_facts = [
        replacement_fact if fact.fact_id == target.fact_id else fact for fact in base.facts
    ]
    revised_facts.sort(key=lambda fact: fact.fact_id)
    if len({fact.fact_id for fact in revised_facts}) != len(revised_facts):
        raise CorrectionRejected("correction target collides with an existing fact")
    corrections = [*base.applied_corrections, provenance]
    revision = base.revision + 1
    digest = facts_hash(base.case_id, revision, revised_facts, corrections)
    return CaseFacts(
        case_id=base.case_id,
        revision=revision,
        facts_sha256=digest,
        facts=revised_facts,
        applied_corrections=corrections,
    )
