"""Immutable deterministic projection shared by every result renderer."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, ValidationInfo, model_validator

from debugmate.contracts import ClaimKind, CommandPlatform, ErrorCategory, SourceKind
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.results.contracts import (
    ArtifactIdentity,
    PreparedGenerationContext,
    StrictFrozenModel,
)
from debugmate.results.loader import LoadedDiagnosisSource

_PRESENTATION_TOKEN = object()


class PresentationBuildError(ValueError):
    """Value-free failure at the verified-source presentation boundary."""

    def __init__(self) -> None:
        super().__init__("presentation_build_failed")


class PresentationFact(StrictFrozenModel):
    fact_id: str = Field(pattern=r"^fact_[0-9a-f]{32}$")
    field_id: str
    value: str
    source_kind: SourceKind
    confidence: float = Field(strict=True, ge=0, le=1)
    locator: str


class PresentationCitation(StrictFrozenModel):
    evidence_id: str = Field(pattern=r"^evidence_[0-9a-f]{32}$")
    chunk_id: str
    content_summary: str
    source_id: str
    source_url: str
    source_locator: str
    relevance_score: float = Field(strict=True, ge=0, le=1)
    knowledge_build_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class PresentationSupport(StrictFrozenModel):
    fact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    support_type: str


class PresentationCause(StrictFrozenModel):
    candidate_id: str = Field(pattern=r"^candidate_[0-9a-f]{32}$")
    cause: str
    claim_kind: ClaimKind
    fact_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    confidence: float = Field(strict=True, ge=0, le=1)
    applicability: str
    counterevidence_or_limits: str

    @property
    def claim_label(self) -> Literal["有依据", "推断"]:
        return "有依据" if self.claim_kind is ClaimKind.GROUNDED else "推断"


class PresentationCommand(StrictFrozenModel):
    command: str
    platform: CommandPlatform
    impact: str
    expected_result: str
    rollback: str


class PresentationModel(StrictFrozenModel):
    """Complete semantic input for report, card and recap generation."""

    projection_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity: ArtifactIdentity
    report_contract_version: str
    card_contract_version: str
    recap_contract_version: str
    font_name: str
    font_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    category: ErrorCategory
    confidence: float = Field(strict=True, ge=0, le=1)
    observed_facts: tuple[PresentationFact, ...]
    citations: tuple[PresentationCitation, ...]
    support_links: tuple[PresentationSupport, ...]
    root_causes: tuple[PresentationCause, ...]
    missing_information: tuple[str, ...]
    checks: tuple[PresentationCommand, ...]
    fixes: tuple[PresentationCommand, ...]
    verification_steps: tuple[PresentationCommand, ...]
    limitations: tuple[str, ...]
    recap_text: str

    @staticmethod
    def seal_for(payload: dict[str, object]) -> str:
        return sha256_bytes(canonical_json_bytes(payload))

    @model_validator(mode="after")
    def canonical_projection_seal(self, info: ValidationInfo) -> PresentationModel:
        context = info.context if isinstance(info.context, dict) else {}
        if context.get("presentation_token") is not _PRESENTATION_TOKEN:
            raise ValueError("presentation must be built by build_presentation")
        payload = self.model_dump(mode="json", exclude={"projection_sha256"})
        if self.projection_sha256 != self.seal_for(payload):
            raise ValueError("presentation projection seal mismatch")
        return self


def _strict_source(value: object) -> LoadedDiagnosisSource:
    if not isinstance(value, LoadedDiagnosisSource):
        raise TypeError("source type")
    source = LoadedDiagnosisSource.model_validate_json(
        canonical_json_bytes(value.model_dump(mode="json")), strict=True
    )
    diagnosis = source.diagnosis
    if (
        source.outcome.diagnosis != diagnosis
        or source.case_id != diagnosis.case_id
        or source.source_run_id != source.outcome.run_id
        or source.source_manifest.case_id != source.case_id
        or source.source_manifest.run_id != source.source_run_id
        or source.source_manifest.schema_version != diagnosis.schema_version
        or source.diagnosis_sha256
        != sha256_bytes(canonical_json_bytes(diagnosis.model_dump(mode="json")))
    ):
        raise ValueError("source identity")
    return source


def _strict_context(value: object) -> PreparedGenerationContext:
    if not isinstance(value, PreparedGenerationContext):
        raise TypeError("context type")
    return PreparedGenerationContext.model_validate_json(
        canonical_json_bytes(value.model_dump(mode="json")), strict=True
    )


def revalidate_presentation(value: object) -> PresentationModel:
    """Revalidate one existing projection with the module-private build authority."""

    if not isinstance(value, PresentationModel):
        raise TypeError("presentation type")
    return PresentationModel.model_validate_json(
        canonical_json_bytes(value.model_dump(mode="json")),
        strict=True,
        context={"presentation_token": _PRESENTATION_TOKEN},
    )


def _command(value: object) -> PresentationCommand:
    return PresentationCommand.model_validate(value, from_attributes=True, strict=True)


def build_presentation(
    source: LoadedDiagnosisSource, context: PreparedGenerationContext
) -> PresentationModel:
    """Project one verified diagnosis without inference, I/O, providers or repair."""

    try:
        verified = _strict_source(source)
        prepared = _strict_context(context)
        diagnosis = verified.diagnosis
        profile = prepared.generation_profile
        identity = ArtifactIdentity(
            case_id=verified.case_id,
            source_run_id=verified.source_run_id,
            diagnosis_sha256=verified.diagnosis_sha256,
            schema_version=diagnosis.schema_version,
            generation_version=profile.generation_version,
        )
        facts = tuple(
            PresentationFact.model_validate(item, from_attributes=True, strict=True)
            for item in sorted(diagnosis.observed_facts, key=lambda item: item.fact_id)
        )
        citations = tuple(
            PresentationCitation(
                evidence_id=item.evidence_id,
                chunk_id=item.chunk_id,
                content_summary=item.content_summary,
                source_id=item.source_id,
                source_url=item.source_url,
                source_locator=item.locator,
                relevance_score=item.relevance_score,
                knowledge_build_id=item.knowledge_build_id,
            )
            for item in sorted(diagnosis.evidence, key=lambda item: item.evidence_id)
        )
        support = tuple(
            PresentationSupport(
                fact_ids=tuple(sorted(item.fact_ids)),
                evidence_ids=tuple(sorted(item.evidence_ids)),
                support_type=str(item.support_type),
            )
            for item in sorted(
                diagnosis.support_links,
                key=lambda item: (
                    tuple(sorted(item.fact_ids)),
                    tuple(sorted(item.evidence_ids)),
                    str(item.support_type),
                ),
            )
        )
        causes = tuple(
            PresentationCause(
                candidate_id=item.candidate_id,
                cause=item.cause,
                claim_kind=item.claim_kind,
                fact_ids=tuple(sorted(item.fact_ids)),
                evidence_ids=tuple(sorted(item.evidence_ids)),
                confidence=item.confidence,
                applicability=item.applicability,
                counterevidence_or_limits=item.counterevidence_or_limits,
            )
            for item in sorted(
                diagnosis.root_cause_candidates, key=lambda item: item.candidate_id
            )
        )
        payload: dict[str, object] = dict(
            identity=identity,
            report_contract_version=profile.report_contract_version,
            card_contract_version=profile.card_contract_version,
            recap_contract_version=profile.recap_contract_version,
            font_name=prepared.resolved_font.name,
            font_sha256=prepared.resolved_font.sha256,
            category=diagnosis.category,
            confidence=diagnosis.confidence,
            observed_facts=facts,
            citations=citations,
            support_links=support,
            root_causes=causes,
            missing_information=tuple(diagnosis.missing_information),
            checks=tuple(_command(item) for item in diagnosis.checks),
            fixes=tuple(_command(item) for item in diagnosis.fixes),
            verification_steps=tuple(
                _command(item) for item in diagnosis.verification_steps
            ),
            limitations=tuple(diagnosis.limitations),
            recap_text=diagnosis.recap_text,
        )
        normalized = PresentationModel.model_construct(
            **payload, projection_sha256="0" * 64
        ).model_dump(mode="json", exclude={"projection_sha256"})
        return PresentationModel.model_validate_json(
            canonical_json_bytes(
                {
                    **normalized,
                    "projection_sha256": PresentationModel.seal_for(normalized),
                }
            ),
            strict=True,
            context={"presentation_token": _PRESENTATION_TOKEN},
        )
    except Exception:
        failure = PresentationBuildError()
    raise failure from None
