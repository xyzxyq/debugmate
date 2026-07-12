---
phase: 03-traceable-diagnosis-workflow
status: issues_found
depth: deep
reviewed_at: 2026-07-12
files_reviewed: 41
original_findings:
  closed: 4
iteration_2_findings:
  closed: 2
  partially_closed: 2
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
---

# Phase 3 Final Software Quality Re-review

## Result

The three iteration-2 implementation commits close the established structured-environment
defect, bind top-level fact state, reject mismatched candidate provenance, and require a
verified source bundle for corrected publication. The full offline suite remains green.

The phase is nevertheless **not clean**. Two public-boundary bypasses remain: extraction
provenance can be removed wholesale, and correction history can be made internally false
while retaining a verified source bundle. Both were reproduced by rebuilding the canonical
facts hash, run ID, and idempotency key and then publishing through the normal public API.

## Findings

### WARNING 1 - Removing the extraction record bypasses exact fact provenance validation

**Files:** `src/debugmate/diagnosis/extraction.py:321-330`,
`src/debugmate/diagnosis/workflow.py:171-187`

`validate_facts_against_extraction()` returns early when `extraction is None` after checking
only that candidate-ID lists are empty. It does not require an extraction record for a
workflow-produced outcome, and it does not require provenance-free facts to use
`source_kinds=[user]`. Because `DiagnosisRunOutcome.extraction` is optional, an imported
outcome can remove the complete extraction record, clear every candidate-ID list, relabel
the facts as OCR/VLM sourced, recompute `facts_sha256`, `idempotency_key`, and `run_id`, and
pass both shared validation and evidence publication.

This leaves `extraction.json` absent from the published bundle while `case-facts.json`
claims non-user source kinds that have no source record or locator. It is a direct bypass of
the exact candidate/extraction binding introduced in `4b96f4c` and makes a forged fact graph
look like a valid provider-derived diagnosis.

**Confirmed reproduction:** a normal `module_not_found` completed outcome was transformed
by setting `extraction=None`, setting every fact's `provenance_candidate_ids=[]` and
`source_kinds=[vlm]`, and recomputing canonical identities. Both
`validate_diagnosis_outcome()` and `publish_diagnosis_evidence()` accepted it and produced a
verified bundle.

**Action:** make the public workflow contract require an extraction record for every Phase 3
outcome, or explicitly model a separate user-only import path. At minimum, the no-extraction
branch must reject every non-user source and publication must reject a workflow outcome
whose extraction stage has no extraction record. Add direct validator and publication tests
for removed extraction, empty provenance with OCR/VLM source kinds, and extraction-summary
omission.

### WARNING 2 - Verified source bundles do not prove the declared correction history

**Files:** `src/debugmate/diagnosis/extraction.py:187-194`,
`src/debugmate/diagnosis/extraction.py:337-355`,
`src/debugmate/diagnosis/workflow.py:195-210`,
`src/debugmate/evidence.py:550-566`

The new source-bundle check proves only that a bundle exists with the declared source
run/revision/facts hash. The final facts validator still permits an incomplete or fabricated
correction history:

- it rejects only `len(applied_corrections) > revision`, rather than requiring one canonical
  revision step per correction;
- it never verifies `CorrectionProvenance.correction_id` from canonical correction fields;
- it does not bind each correction's `base_facts_sha256` to the preceding revision, except
  for the last record's equality to the top-level source hash;
- per-field old/new hash chaining is insufficient to prove global revision history.

Consequently a revision-2 outcome can reuse the single revision-1 correction, replace that
record's `base_facts_sha256` with the verified revision-1 source hash, use an arbitrary
pattern-valid correction ID, recompute canonical outcome identities, and publish as if a
second correction occurred. The source bundle itself remains valid, so the publication
boundary accepts the false history. Separately, changing only a correction ID and reason
hash on a revision-1 outcome is also accepted and published.

**Confirmed reproduction:** original and revision-1 bundles were published normally. A
forged revision-2 outcome containing only one altered correction record, with
`source_run_id/source_revision/source_facts_sha256` pointing to the real revision-1 bundle,
passed `validate_diagnosis_outcome()` and `publish_diagnosis_evidence()` (`GAP_VALIDATED`,
`GAP_PUBLISHED`).

**Action:** enforce canonical correction history as a complete sequence. Require correction
count/revision consistency for the Phase 3 origin contract, verify canonical correction IDs,
and bind every correction base hash to the exact preceding revision. For imported corrected
outcomes, validate the latest correction against the source bundle's fact state and preserve
enough immutable source data to prove old fact ID/value and resulting new state; a manifest
containing only the source facts digest cannot by itself prove the transition. Add validator,
rerun, and publication tamper tests for revision gaps, arbitrary correction IDs/reason
hashes, duplicated corrections, wrong base hashes, and multi-field/multi-revision ordering.

## Closure of Earlier Findings

1. **Original environment participation:** closed. Environment mappings are source-hashed,
   affect identities, and now participate in extraction.
2. **Original outcome/publication identity:** closed for top-level revision/hash, run,
   idempotency, versions, and stage path.
3. **Canonical `CaseFact`:** closed at the model boundary.
4. **Inherited-stage presentation:** closed; inherited extraction stages are not reported as
   newly executed.
5. **Iteration-2 structured environment maps:** closed. `PYTHON`, `python`, and `DEVICE`
   bare-value mappings produce deterministic version/device candidates and exact locators.
6. **Iteration-2 top-level vs nested fact state:** closed.
7. **Iteration-2 exact fact/extraction relationship:** partially closed; exact membership is
   enforced only while the optional extraction record remains present (Warning 1).
8. **Iteration-2 source-bundle relationship:** partially closed; source bundle existence and
   manifest identity are verified, but the claimed transition/history is not (Warning 2).

## Verification Evidence

- Structured environment regression covers both `PYTHON` and `python` plus separate
  `DEVICE`, including deterministic locator offsets.
- Existing focused adversarial/workflow tests remain green.
- `python -m pytest -q -m "not cloud and not ocr"`: **453 passed, 22 deselected**.
- `python -m ruff check src tests`: **passed**.
- `python -m pip check`: **passed**.
- `git diff --check`: no implementation error; only the pre-existing line-ending warning
  for `.planning/config.json`.
- Manual public-boundary adversarial checks reproduced both warnings through the real
  validator and publisher, not private helpers.

## Required Tests Before Clean Status

1. Validator and publication rejection when a workflow outcome removes its extraction or
   claims OCR/VLM facts without exact candidate provenance.
2. Canonical correction-ID and complete revision/history validation.
3. Publication rejection for revision gaps, duplicated/altered correction records, wrong
   per-step base hashes, and a transition not provable from the verified source bundle.
