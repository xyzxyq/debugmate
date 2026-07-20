"""Pure, one-way migrations for versioned diagnosis records."""

from __future__ import annotations

import hashlib
import json

from debugmate.contracts import (
    CommandStep,
    DiagnosisRecord,
    DiagnosisRecordV100,
    EvidenceAnchor,
    ObservedFact,
    RootCauseCandidate,
)


def _stable_id(prefix: str, *parts: object) -> str:
    canonical = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}_{digest}"


def _migrate_command(command: object) -> CommandStep:
    payload = command.model_dump(mode="json")  # type: ignore[attr-defined]
    payload["platform"] = {
        "windows-powershell": "windows_powershell",
        "windows-cmd": "windows_cmd",
        "linux-bash": "linux_bash",
    }.get(payload["platform"], payload["platform"])
    return CommandStep.model_validate(payload)


def migrate_v100_to_v110(record: DiagnosisRecordV100) -> DiagnosisRecord:
    """Conservatively migrate a frozen 1.0.0 record to the current contract."""

    facts = [
        ObservedFact(
            fact_id=_stable_id("fact", record.case_id, "observed", index, value),
            field_id="legacy_observed_fact",
            value=value,
            source_kind="text",
            confidence=record.confidence,
            locator=f"legacy:observed_facts:{index}",
        )
        for index, value in enumerate(record.observed_facts)
    ]

    candidates: list[RootCauseCandidate] = []
    for candidate_index, candidate in enumerate(record.root_cause_candidates):
        candidate_fact_ids: list[str] = []
        for fact_index, value in enumerate(candidate.supporting_facts):
            fact_id = _stable_id(
                "fact", record.case_id, "candidate", candidate_index, fact_index, value
            )
            facts.append(
                ObservedFact(
                    fact_id=fact_id,
                    field_id="legacy_supporting_fact",
                    value=value,
                    source_kind="text",
                    confidence=candidate.confidence,
                    locator=f"legacy:root_cause_candidates:{candidate_index}:supporting_facts:{fact_index}",
                )
            )
            candidate_fact_ids.append(fact_id)
        candidates.append(
            RootCauseCandidate(
                candidate_id=_stable_id(
                    "candidate", record.case_id, candidate_index, candidate.cause
                ),
                cause=candidate.cause,
                claim_kind="inference",
                fact_ids=candidate_fact_ids,
                evidence_ids=[],
                confidence=candidate.confidence,
                applicability="Migrated from a legacy text-only diagnosis candidate.",
                counterevidence_or_limits=(
                    "The legacy record did not prove a relationship between this candidate "
                    "and any citation."
                ),
            )
        )

    evidence = [
        EvidenceAnchor(
            evidence_id=_stable_id(
                "evidence", record.case_id, citation.source_id, citation.locator, citation.url
            ),
            chunk_id=_stable_id(
                "chunk", record.case_id, citation.source_id, citation.locator, citation.excerpt
            ),
            content_summary=citation.excerpt,
            source_id=citation.source_id,
            source_url=citation.url,
            locator=citation.locator,
            relevance_score=record.confidence,
            knowledge_build_id="legacy_v100_unverified",
        )
        for citation in record.citations
    ]

    return DiagnosisRecord(
        schema_version="1.1.0",
        case_id=record.case_id,
        category=record.category,
        observed_facts=facts,
        evidence=evidence,
        support_links=[],
        root_cause_candidates=candidates,
        missing_information=record.missing_information,
        checks=[_migrate_command(command) for command in record.checks],
        fixes=[_migrate_command(command) for command in record.fixes],
        verification_steps=[_migrate_command(command) for command in record.verification_steps],
        confidence=record.confidence,
        limitations=record.limitations,
        recap_text=record.recap_text,
    )
