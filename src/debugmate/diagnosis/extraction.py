"""Strict candidate extraction and immutable case-fact contracts."""

from __future__ import annotations

import hmac
import re
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from debugmate.contracts import CaseId
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.privacy.models import Sha256
from debugmate.privacy.output_scan import UnsafeExport, assert_export_safe


class FieldId(StrEnum):
    EXCEPTION_TYPE = "exception_type"
    TRACEBACK_KEY_LINE = "traceback_key_line"
    PACKAGE = "package"
    VERSION = "version"
    DEVICE = "device"
    PATH = "path"


class SourceKind(StrEnum):
    TEXT = "text"
    OCR = "ocr"
    VLM = "vlm"
    USER = "user"


Point = tuple[int, int]
Box = tuple[Point, Point, Point, Point]


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class TextLocator(StrictFrozenModel):
    kind: Literal["text"] = "text"
    input_field: Literal["error_text", "code", "environment"]
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, gt=0)

    @model_validator(mode="after")
    def require_nonempty_span(self) -> Self:
        if self.end <= self.start:
            raise ValueError("text locator end must be greater than start")
        return self


class OcrLocator(StrictFrozenModel):
    kind: Literal["ocr"] = "ocr"
    image_sha256: Sha256
    box: Box
    image_width: int = Field(strict=True, gt=0)
    image_height: int = Field(strict=True, gt=0)

    @model_validator(mode="after")
    def require_in_bounds_box(self) -> Self:
        _validate_box(self.box, self.image_width, self.image_height)
        return self


class VlmLocator(StrictFrozenModel):
    kind: Literal["vlm"] = "vlm"
    image_sha256: Sha256
    box: Box
    image_width: int = Field(strict=True, gt=0)
    image_height: int = Field(strict=True, gt=0)

    @model_validator(mode="after")
    def require_in_bounds_box(self) -> Self:
        _validate_box(self.box, self.image_width, self.image_height)
        return self


def _validate_box(box: Box, width: int, height: int) -> None:
    if len(set(box)) < 3:
        raise ValueError("image locator box must contain an area")
    for x, y in box:
        if x < 0 or y < 0 or x >= width or y >= height:
            raise ValueError("image locator box is out of bounds")


Locator = Annotated[TextLocator | OcrLocator | VlmLocator, Field(discriminator="kind")]


def _opaque_id(prefix: str, payload: object) -> str:
    return f"{prefix}_{sha256_bytes(canonical_json_bytes(payload))[:32]}"


class FactCandidate(StrictFrozenModel):
    candidate_id: str = Field(pattern=r"^candidate_[0-9a-f]{32}$")
    field_id: FieldId
    value: str = Field(min_length=1)
    source_kind: SourceKind
    confidence: float = Field(strict=True, ge=0.0, le=1.0)
    locator: Locator

    @model_validator(mode="after")
    def require_consistent_identity_and_source(self) -> Self:
        if self.source_kind.value != self.locator.kind:
            raise ValueError("candidate source kind must match its locator")
        expected = candidate_id_for(
            self.field_id, self.value, self.source_kind, self.confidence, self.locator
        )
        if self.candidate_id != expected:
            raise ValueError("candidate_id does not match canonical candidate data")
        return self


def candidate_id_for(
    field_id: FieldId,
    value: str,
    source_kind: SourceKind,
    confidence: float,
    locator: Locator,
) -> str:
    return _opaque_id(
        "candidate",
        {
            "field_id": field_id.value,
            "value": value,
            "source_kind": source_kind.value,
            "confidence": confidence,
            "locator": locator.model_dump(mode="json"),
        },
    )


def make_candidate(
    *,
    field_id: FieldId,
    value: str,
    source_kind: SourceKind,
    confidence: float,
    locator: Locator,
) -> FactCandidate:
    normalized = normalize_value(field_id, value)
    return FactCandidate(
        candidate_id=candidate_id_for(field_id, normalized, source_kind, confidence, locator),
        field_id=field_id,
        value=normalized,
        source_kind=source_kind,
        confidence=confidence,
        locator=locator,
    )


class ExtractionRecord(StrictFrozenModel):
    case_id: CaseId
    extraction_id: str = Field(pattern=r"^extraction_[0-9a-f]{32}$")
    source_hashes: dict[str, Sha256]
    candidates: list[FactCandidate]

    @model_validator(mode="after")
    def require_deterministic_record(self) -> Self:
        if list(self.source_hashes) != sorted(self.source_hashes):
            raise ValueError("source hashes must use deterministic key ordering")
        ids = [item.candidate_id for item in self.candidates]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("candidates must be unique and sorted by stable ID")
        expected = extraction_id_for(self.case_id, self.source_hashes, self.candidates)
        if self.extraction_id != expected:
            raise ValueError("extraction_id does not match canonical extraction data")
        return self


def extraction_id_for(
    case_id: str, source_hashes: dict[str, str], candidates: list[FactCandidate]
) -> str:
    return _opaque_id(
        "extraction",
        {
            "case_id": case_id,
            "source_hashes": dict(sorted(source_hashes.items())),
            "candidate_ids": sorted(item.candidate_id for item in candidates),
        },
    )


class CorrectionProvenance(StrictFrozenModel):
    correction_id: str = Field(pattern=r"^correction_[0-9a-f]{32}$")
    field_id: FieldId
    fact_id: str = Field(pattern=r"^fact_[0-9a-f]{32}$")
    source_kind: Literal[SourceKind.USER] = SourceKind.USER
    old_value_sha256: Sha256
    new_value_sha256: Sha256
    reason_sha256: Sha256


class CaseFact(StrictFrozenModel):
    fact_id: str = Field(pattern=r"^fact_[0-9a-f]{32}$")
    field_id: FieldId
    value: str = Field(min_length=1)
    provenance_candidate_ids: list[str]
    source_kinds: list[SourceKind]
    confidence: float = Field(strict=True, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def require_canonical_fact_and_provenance(self) -> Self:
        try:
            normalized = normalize_value(self.field_id, self.value)
        except ValueError as error:
            raise ValueError("fact value is not canonical") from error
        if self.value != normalized:
            raise ValueError("fact value must use canonical normalization")
        if self.fact_id != fact_id_for(self.field_id, normalized):
            raise ValueError("fact_id does not match canonical fact data")
        candidate_ids = self.provenance_candidate_ids
        if (
            candidate_ids != sorted(candidate_ids)
            or len(candidate_ids) != len(set(candidate_ids))
            or any(
                re.fullmatch(r"candidate_[0-9a-f]{32}", candidate_id) is None
                for candidate_id in candidate_ids
            )
        ):
            raise ValueError("candidate provenance IDs must be canonical, unique, and sorted")
        if self.source_kinds != sorted(self.source_kinds, key=str) or len(self.source_kinds) != len(
            set(self.source_kinds)
        ):
            raise ValueError("fact source kinds must be unique and sorted")
        return self


class CaseFacts(StrictFrozenModel):
    case_id: CaseId
    revision: int = Field(strict=True, ge=0)
    facts_sha256: Sha256
    facts: list[CaseFact]
    applied_corrections: list[CorrectionProvenance] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_canonical_hash(self) -> Self:
        if self.facts_sha256 != facts_hash(
            self.case_id, self.revision, self.facts, self.applied_corrections
        ):
            raise ValueError("facts_sha256 does not match canonical facts")
        ids = [fact.fact_id for fact in self.facts]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("facts must be unique and sorted by stable ID")
        try:
            assert_export_safe([fact.value for fact in self.facts])
        except UnsafeExport as error:
            raise ValueError("case facts contain unsafe export content") from error
        return self


def normalize_value(field_id: FieldId, value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError("fact value must not be empty")
    if len(normalized) > 2_000:
        raise ValueError("fact value exceeds the local extraction limit")
    if field_id is FieldId.EXCEPTION_TYPE and not normalized.replace(".", "").isidentifier():
        raise ValueError("exception_type must be a dotted identifier")
    if field_id is FieldId.VERSION and len(normalized) > 128:
        raise ValueError("version value is too long")
    return normalized


def fact_id_for(field_id: FieldId, value: str) -> str:
    return _opaque_id("fact", {"field_id": field_id.value, "value": value})


def facts_hash(
    case_id: str,
    revision: int,
    facts: list[CaseFact],
    corrections: list[CorrectionProvenance],
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "case_id": case_id,
                "revision": revision,
                "facts": [item.model_dump(mode="json") for item in facts],
                "applied_corrections": [item.model_dump(mode="json") for item in corrections],
            }
        )
    )


def build_case_facts(record: ExtractionRecord) -> CaseFacts:
    grouped: dict[tuple[FieldId, str], list[FactCandidate]] = {}
    for candidate in record.candidates:
        normalized = normalize_value(candidate.field_id, candidate.value)
        assert_export_safe(normalized)
        grouped.setdefault((candidate.field_id, normalized), []).append(candidate)

    facts: list[CaseFact] = []
    for (field_id, value), candidates in grouped.items():
        ordered = sorted(candidates, key=lambda item: item.candidate_id)
        facts.append(
            CaseFact(
                fact_id=fact_id_for(field_id, value),
                field_id=field_id,
                value=value,
                provenance_candidate_ids=[item.candidate_id for item in ordered],
                source_kinds=sorted({item.source_kind for item in ordered}, key=str),
                confidence=max(item.confidence for item in ordered),
            )
        )
    facts.sort(key=lambda item: item.fact_id)
    digest = facts_hash(record.case_id, 0, facts, [])
    return CaseFacts(
        case_id=record.case_id,
        revision=0,
        facts_sha256=digest,
        facts=facts,
        applied_corrections=[],
    )


def validate_facts_against_extraction(
    facts: CaseFacts, extraction: ExtractionRecord | None
) -> None:
    """Cross-bind every fact provenance edge to its exact extraction candidate set."""

    if extraction is None:
        if any(fact.provenance_candidate_ids for fact in facts.facts):
            raise ValueError("fact provenance requires an extraction record")
        return
    if extraction.case_id != facts.case_id:
        raise ValueError("fact provenance extraction does not match its case")

    candidates_by_id = {item.candidate_id: item for item in extraction.candidates}
    grouped: dict[tuple[FieldId, str], list[FactCandidate]] = {}
    for candidate in extraction.candidates:
        grouped.setdefault((candidate.field_id, candidate.value), []).append(candidate)

    corrections_by_field: dict[FieldId, list[CorrectionProvenance]] = {}
    for correction in facts.applied_corrections:
        corrections_by_field.setdefault(correction.field_id, []).append(correction)
    if len(facts.applied_corrections) > facts.revision:
        raise ValueError("fact correction history exceeds its revision")

    corrected_fields: set[FieldId] = set()
    for field_id, corrections in corrections_by_field.items():
        for previous, current in zip(corrections, corrections[1:], strict=False):
            if not hmac.compare_digest(previous.new_value_sha256, current.old_value_sha256):
                raise ValueError("fact correction provenance chain is inconsistent")
        corrected_fields.add(field_id)

    for fact in facts.facts:
        provenance = []
        for candidate_id in fact.provenance_candidate_ids:
            candidate = candidates_by_id.get(candidate_id)
            if candidate is None:
                raise ValueError("fact provenance candidate is absent from extraction")
            provenance.append(candidate)

        corrections = corrections_by_field.get(fact.field_id, [])
        if corrections:
            if not hmac.compare_digest(
                corrections[-1].new_value_sha256, sha256_bytes(fact.value.encode("utf-8"))
            ):
                raise ValueError("fact correction provenance does not bind the final value")
            initial = [
                item
                for item in extraction.candidates
                if item.field_id is fact.field_id
                and hmac.compare_digest(
                    sha256_bytes(item.value.encode("utf-8")), corrections[0].old_value_sha256
                )
            ]
            if not initial or corrections[0].fact_id != fact_id_for(
                fact.field_id, initial[0].value
            ):
                raise ValueError("fact correction provenance does not bind its source value")
            expected_candidates = sorted(item.candidate_id for item in initial)
            expected_sources = sorted(
                {*(item.source_kind for item in initial), SourceKind.USER}, key=str
            )
        elif fact.provenance_candidate_ids:
            matching = grouped.get((fact.field_id, fact.value), [])
            expected_candidates = sorted(item.candidate_id for item in matching)
            expected_sources = sorted({item.source_kind for item in matching}, key=str)
        else:
            expected_candidates = []
            expected_sources = [SourceKind.USER]

        if fact.provenance_candidate_ids != expected_candidates:
            raise ValueError("fact provenance candidates do not exactly match extraction")
        if fact.source_kinds != expected_sources:
            raise ValueError("fact provenance source kinds do not exactly match extraction")

    if corrected_fields - {fact.field_id for fact in facts.facts}:
        raise ValueError("fact correction provenance has no current fact")
