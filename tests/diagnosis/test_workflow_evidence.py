from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.diagnosis.test_workflow_e2e import _approved, _rows, _workflow

from debugmate.cli import main
from debugmate.contracts import EvidenceAnchor
from debugmate.diagnosis.correction import CorrectionOverlay
from debugmate.diagnosis.extraction import FieldId, SourceKind, facts_hash
from debugmate.diagnosis.workflow import derive_run_identities, validate_diagnosis_outcome
from debugmate.evidence import (
    UnsafeEvidenceContent,
    publish_diagnosis_evidence,
    verify_bundle,
)
from debugmate.hashing import sha256_bytes


def _outcome(case_key: str, tmp_path: Path):
    row = next(item for item in _rows() if item["case_key"] == case_key)
    workflow, *_ = _workflow(row, tmp_path)
    answers = {FieldId(key): value for key, value in row.get("answers", {}).items()}
    return workflow.run(_approved(row["case_id"]), followup_answers=answers or None)


def _rehash_outcome(outcome, facts):
    routing = outcome.routing
    idempotency_key, run_id = derive_run_identities(facts, routing, outcome.knowledge_build_id)
    return outcome.model_copy(
        update={
            "revision": facts.revision,
            "facts_sha256": facts.facts_sha256,
            "facts": facts,
            "idempotency_key": idempotency_key,
            "run_id": run_id,
        }
    )


@pytest.mark.parametrize(
    ("case_key", "expected", "forbidden"),
    [
        (
            "module_not_found",
            {
                "extraction.json",
                "case-facts.json",
                "sufficiency.json",
                "routing.json",
                "retrieval.json",
                "diagnosis.json",
                "manifest.json",
            },
            {"failure.json"},
        ),
        (
            "needs_information",
            {
                "extraction.json",
                "case-facts.json",
                "sufficiency.json",
                "routing.json",
                "manifest.json",
            },
            {"retrieval.json", "diagnosis.json", "failure.json"},
        ),
        (
            "insufficient_information",
            {
                "extraction.json",
                "case-facts.json",
                "sufficiency.json",
                "routing.json",
                "manifest.json",
            },
            {"retrieval.json", "diagnosis.json", "failure.json"},
        ),
        (
            "generation_failed",
            {
                "extraction.json",
                "case-facts.json",
                "sufficiency.json",
                "routing.json",
                "retrieval.json",
                "failure.json",
                "manifest.json",
            },
            {"diagnosis.json"},
        ),
    ],
)
def test_outcomes_publish_only_allowlisted_privacy_safe_summaries(
    case_key: str,
    expected: set[str],
    forbidden: set[str],
    tmp_path: Path,
) -> None:
    outcome = _outcome(case_key, tmp_path)

    published = publish_diagnosis_evidence(outcome, tmp_path / "evidence")
    verification = verify_bundle(published)

    assert published == tmp_path / "evidence" / outcome.case_id / outcome.run_id
    assert verification.ok is True
    assert {item.name for item in published.iterdir()} == expected
    assert not {item.name for item in published.iterdir()} & forbidden
    assert verification.manifest is not None
    manifest = verification.manifest
    assert manifest.backend == "fixture"
    assert manifest.run_id == outcome.run_id
    assert manifest.facts_revision == outcome.revision
    assert manifest.facts_sha256 == outcome.facts_sha256
    assert manifest.routing_rule_version == outcome.routing.rule_version
    assert manifest.knowledge_build_id == outcome.knowledge_build_id
    assert manifest.schema_version == "1.1.0"
    assert manifest.generation_attempts == outcome.generation_attempts
    assert manifest.transport_attempts == outcome.transport_attempts
    assert set(manifest.node_states) == set(outcome.completed_stages)
    rendered = "\n".join(path.read_text(encoding="utf-8") for path in published.glob("*.json"))
    for forbidden_key in (
        "raw_chunk",
        "response_body",
        "reasoning",
        "chain_of_thought",
        "recap.mp3",
        "card.png",
        "report.md",
    ):
        assert forbidden_key not in rendered


def test_artifact_hashes_are_recomputed_and_tampering_is_detected(tmp_path: Path) -> None:
    published = publish_diagnosis_evidence(_outcome("module_not_found", tmp_path), tmp_path / "e")
    assert verify_bundle(published).ok is True

    (published / "routing.json").write_text("{}", encoding="utf-8")

    result = verify_bundle(published)
    assert result.ok is False
    assert any(issue == "sha256 mismatch: routing.json" for issue in result.issues)


def test_privacy_failure_removes_temporary_bundle_and_publishes_nothing(tmp_path: Path) -> None:
    outcome = _outcome("module_not_found", tmp_path)
    unsafe_routing = outcome.routing.model_copy(
        update={"reason": "Authorization: Bearer SECRET_SENTINEL_DO_NOT_LOG"}
    )
    unsafe = outcome.model_copy(update={"routing": unsafe_routing})
    root = tmp_path / "evidence"

    with pytest.raises(UnsafeEvidenceContent):
        publish_diagnosis_evidence(unsafe, root)

    assert not (root / outcome.case_id / outcome.run_id).exists()
    assert list(root.rglob(".tmp-*")) == []


def test_forged_retrieval_anchor_is_rejected_without_partial_diagnosis(tmp_path: Path) -> None:
    outcome = _outcome("module_not_found", tmp_path)
    forged = EvidenceAnchor.model_validate(
        {
            **outcome.evidence[0].model_dump(mode="json"),
            "evidence_id": "evidence_" + "f" * 32,
        }
    )
    unsafe = outcome.model_copy(update={"evidence": [forged]})
    root = tmp_path / "evidence"

    with pytest.raises(ValueError, match="evidence"):
        publish_diagnosis_evidence(unsafe, root)

    assert not (root / outcome.case_id / outcome.run_id).exists()
    assert list(root.rglob("diagnosis.json")) == []


def test_corrected_runs_preserve_both_bundles(tmp_path: Path) -> None:
    row = next(item for item in _rows() if item["case_key"] == "correction_rerun")
    workflow, *_ = _workflow(row, tmp_path)
    original = workflow.run(_approved(row["case_id"]))
    target = next(fact for fact in original.facts.facts if fact.field_id is FieldId.EXCEPTION_TYPE)
    overlay = CorrectionOverlay(
        case_id=original.case_id,
        base_revision=original.revision,
        base_facts_sha256=original.facts_sha256,
        field_id=target.field_id,
        fact_id=target.fact_id,
        old_value_sha256=sha256_bytes(target.value.encode()),
        replacement="AttributeError",
        reason="confirmed from redacted traceback",
    )
    corrected = workflow.rerun(original, overlay)
    root = tmp_path / "evidence"

    first = publish_diagnosis_evidence(original, root)
    first_manifest = (first / "manifest.json").read_bytes()
    second = publish_diagnosis_evidence(corrected, root)

    assert first != second
    assert first.is_dir() and second.is_dir()
    assert (first / "manifest.json").read_bytes() == first_manifest
    assert verify_bundle(first).ok is True
    assert verify_bundle(second).ok is True
    assert original.revision != corrected.revision
    assert original.run_id != corrected.run_id
    assert original.facts_sha256 != corrected.facts_sha256
    corrected_manifest = verify_bundle(second).manifest
    assert corrected_manifest is not None
    assert corrected_manifest.source_run_id == original.run_id
    assert corrected_manifest.node_states["input_approved"] == "inherited"
    assert corrected_manifest.node_states["extracted"] == "inherited"
    assert corrected_manifest.node_states["facts_confirmed"] == "inherited"
    assert corrected_manifest.node_states["facts_corrected"] == "completed"


def test_duplicate_run_is_immutable(tmp_path: Path) -> None:
    outcome = _outcome("module_not_found", tmp_path)
    root = tmp_path / "evidence"
    publish_diagnosis_evidence(outcome, root)

    with pytest.raises(FileExistsError):
        publish_diagnosis_evidence(outcome, root)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"run_id": "run_" + "f" * 32}, "run_id"),
        ({"idempotency_key": "idem_" + "f" * 32}, "idempotency"),
        ({"schema_version": "9.9.9"}, "version"),
        ({"prompt_version": "forged"}, "version"),
        ({"workflow_version": "forged"}, "version"),
        ({"completed_stages": ["input_approved", "published"]}, "stages"),
    ],
)
def test_publication_rejects_tampered_identity_versions_and_stages(
    changes: dict[str, object], message: str, tmp_path: Path
) -> None:
    outcome = _outcome("module_not_found", tmp_path)
    tampered = outcome.model_copy(update=changes)
    root = tmp_path / "evidence"

    with pytest.raises(ValueError, match=message):
        publish_diagnosis_evidence(tampered, root)

    assert not root.exists() or not any(root.rglob("manifest.json"))


@pytest.mark.parametrize("changes", [{"revision": 999}, {"facts_sha256": "f" * 64}])
def test_shared_validator_rejects_top_level_fact_state_tampering(
    changes: dict[str, object], tmp_path: Path
) -> None:
    outcome = _outcome("module_not_found", tmp_path)

    with pytest.raises(ValueError, match="revision|facts hash"):
        validate_diagnosis_outcome(outcome.model_copy(update=changes))


def test_fact_provenance_must_match_exact_extraction_candidate(tmp_path: Path) -> None:
    outcome = _outcome("module_not_found", tmp_path)
    assert outcome.extraction is not None
    target = next(fact for fact in outcome.facts.facts if fact.provenance_candidate_ids)
    unrelated = next(
        candidate
        for candidate in outcome.extraction.candidates
        if candidate.field_id is not target.field_id
    )
    forged_fact = target.model_copy(
        update={
            "provenance_candidate_ids": [unrelated.candidate_id],
            "source_kinds": [unrelated.source_kind],
        }
    )
    forged_items = [
        forged_fact if item.fact_id == target.fact_id else item for item in outcome.facts.facts
    ]
    forged_items.sort(key=lambda item: item.fact_id)
    forged_facts = outcome.facts.model_copy(
        update={
            "facts": forged_items,
            "facts_sha256": facts_hash(
                outcome.case_id,
                outcome.facts.revision,
                forged_items,
                outcome.facts.applied_corrections,
            ),
        }
    )
    forged = _rehash_outcome(outcome, forged_facts)

    with pytest.raises(ValueError, match="provenance"):
        validate_diagnosis_outcome(forged)
    with pytest.raises(ValueError, match="provenance"):
        publish_diagnosis_evidence(forged, tmp_path / "evidence")


def test_fact_source_kinds_must_exactly_match_extraction_candidates(tmp_path: Path) -> None:
    outcome = _outcome("module_not_found", tmp_path)
    target = next(fact for fact in outcome.facts.facts if fact.provenance_candidate_ids)
    forged_fact = target.model_copy(update={"source_kinds": [SourceKind.VLM]})
    forged_items = [
        forged_fact if item.fact_id == target.fact_id else item for item in outcome.facts.facts
    ]
    forged_items.sort(key=lambda item: item.fact_id)
    forged_facts = outcome.facts.model_copy(
        update={
            "facts": forged_items,
            "facts_sha256": facts_hash(
                outcome.case_id,
                outcome.facts.revision,
                forged_items,
                outcome.facts.applied_corrections,
            ),
        }
    )

    with pytest.raises(ValueError, match="provenance"):
        validate_diagnosis_outcome(_rehash_outcome(outcome, forged_facts))


def test_cli_publishes_strict_outcome_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    outcome = _outcome("module_not_found", tmp_path)
    source = tmp_path / "outcome.json"
    source.write_text(outcome.model_dump_json(), encoding="utf-8")
    root = tmp_path / "evidence"

    assert main(["diagnosis-publish", str(source), "--output", str(root)]) == 0

    response = json.loads(capsys.readouterr().out)
    published = Path(response["bundle_path"])
    assert response == {
        "backend": "fixture",
        "bundle_path": str(published.resolve()),
        "run_id": outcome.run_id,
        "status": "completed",
    }
    assert verify_bundle(published).ok is True
