"""Bind trusted retrieval traces to stable diagnosis evidence and support links."""

from __future__ import annotations

import json
from pathlib import Path

from debugmate.contracts import (
    ClaimKind,
    EvidenceAnchor,
    RootCauseCandidate,
    SupportLink,
    SupportType,
)
from debugmate.hashing import canonical_json_bytes, sha256_bytes
from debugmate.knowledge.retrieval import RetrievalTrace, validate_retrieval_trace


def _strict_trace(value: object) -> RetrievalTrace:
    if isinstance(value, RetrievalTrace):
        return RetrievalTrace.model_validate(value.model_dump(), strict=True)
    return RetrievalTrace.model_validate_json(json.dumps(value), strict=True)


def _evidence_id(
    *, case_id: str, knowledge_build_id: str, chunk_id: str, source_id: str, locator: str
) -> str:
    digest = sha256_bytes(
        canonical_json_bytes(
            {
                "case_id": case_id,
                "knowledge_build_id": knowledge_build_id,
                "chunk_id": chunk_id,
                "source_id": source_id,
                "locator": locator,
            }
        )
    )
    return f"evidence_{digest[:32]}"


def bind_retrieval_evidence(
    trace: RetrievalTrace,
    *,
    case_id: str,
    expected_build_id: str,
    build_manifest: Path | dict[str, object],
) -> list[EvidenceAnchor]:
    """Create summary-only anchors after exact case/build/source/locator validation."""

    strict_trace = _strict_trace(trace)
    if strict_trace.case_id != case_id:
        raise ValueError("retrieval trace case ID does not match diagnosis case ID")
    if strict_trace.knowledge_build_id != expected_build_id:
        raise ValueError("retrieval trace does not match expected knowledge build")
    validated = validate_retrieval_trace(strict_trace, build_manifest)

    anchors = [
        EvidenceAnchor(
            evidence_id=_evidence_id(
                case_id=strict_trace.case_id,
                knowledge_build_id=validated.knowledge_build_id,
                chunk_id=hit.chunk_id,
                source_id=hit.source_id,
                locator=hit.locator,
            ),
            chunk_id=hit.chunk_id,
            content_summary=hit.content_summary,
            source_id=hit.source_id,
            source_url=hit.source_url,
            locator=hit.locator,
            relevance_score=hit.relevance_score,
            knowledge_build_id=validated.knowledge_build_id,
        )
        for hit in validated.hits
    ]
    evidence_ids = [anchor.evidence_id for anchor in anchors]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("retrieval trace produces duplicate evidence anchors")
    return anchors


def build_support_graph(
    candidates: list[RootCauseCandidate],
    *,
    confirmed_fact_ids: set[str],
    evidence_anchors: list[EvidenceAnchor],
) -> tuple[list[RootCauseCandidate], list[SupportLink]]:
    """Validate exact support targets and create links only for grounded claims."""

    strict_candidates = [
        RootCauseCandidate.model_validate(candidate.model_dump(), strict=True)
        for candidate in candidates
    ]
    strict_anchors = [
        EvidenceAnchor.model_validate(anchor.model_dump(), strict=True)
        for anchor in evidence_anchors
    ]
    candidate_ids = [candidate.candidate_id for candidate in strict_candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("support graph contains duplicate candidate IDs")
    anchor_ids = [anchor.evidence_id for anchor in strict_anchors]
    if len(anchor_ids) != len(set(anchor_ids)):
        raise ValueError("support graph contains duplicate evidence anchors")
    known_evidence = set(anchor_ids)

    links: list[SupportLink] = []
    for candidate in strict_candidates:
        if unknown := set(candidate.fact_ids) - confirmed_fact_ids:
            raise ValueError(f"candidate references unknown fact IDs: {sorted(unknown)}")
        if unknown := set(candidate.evidence_ids) - known_evidence:
            raise ValueError(f"candidate references unknown evidence IDs: {sorted(unknown)}")
        if candidate.claim_kind is ClaimKind.GROUNDED:
            links.append(
                SupportLink(
                    fact_ids=list(candidate.fact_ids),
                    evidence_ids=list(candidate.evidence_ids),
                    support_type=SupportType.SUPPORTS,
                )
            )
    return strict_candidates, links
