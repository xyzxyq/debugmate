---
phase: 03-traceable-diagnosis-workflow
status: clean
depth: deep
reviewed_at: 2026-07-13
reviewed_commits:
  - 9f1d1ad
files_reviewed: 41
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
---

# Phase 3 Post-gap Contract and Regression Review

## Result

Commit `9f1d1ad` closes the sole remaining Phase 3 warning without weakening the
existing extraction-backed correction path. No actionable correctness, contract,
serialization, privacy, or evidence-lineage finding remains in the reviewed scope.

## Verified Gap Closure

The complete formerly failing path now succeeds through the public workflow and
evidence boundaries:

1. An insufficient case accepts one bounded follow-up answer and creates revision 1
   with an exact provenance-free, `user`-only fact.
2. The revision-1 outcome survives strict `DiagnosisRunOutcome` JSON serialization
   and deserialization.
3. Its source evidence bundle publishes and passes `verify_bundle()`.
4. `DiagnosisWorkflow.rerun()` corrects that fact into contiguous revision 2 while
   recording the source fact's candidate IDs, source kinds, and confidence in the
   canonical correction record.
5. The revision-2 outcome survives the same strict JSON round trip and shared outcome
   validation.
6. Corrected publication verifies the revision-1 source bundle before accepting the
   new transition, and both source and corrected bundles pass `verify_bundle()`.

`DiagnosisWorkflow.rerun()` now validates both the imported previous outcome and its
newly assembled outcome. A producer-side contract mismatch therefore fails before an
invalid result can be returned.

## Preserved Normal Path and Invariants

- Normal extraction-backed revision 1 and revision 2 corrections still preserve the
  exact candidate set, source-kind evolution, confidence transition, correction
  prefix, source run identity, and contiguous revision chain.
- Correction IDs now hash the immutable source provenance snapshot, so altering that
  snapshot invalidates canonical serialization rather than silently changing meaning.
- The first correction accepts an absent extraction candidate only for the canonical
  empty-candidate, `user`-only, confidence-1.0 state. Provenance-free OCR/VLM sources,
  invented candidate IDs, and incomplete or gapped correction histories remain
  rejected.
- Corrected publication compares the recorded source snapshot against the exact fact
  in the already hash-verified source bundle and rejects missing, mismatched, or
  unrelated source bundles.
- Existing strict Pydantic model dumps, JSON round trips, gateway boundaries, evidence
  summaries, and immutable bundle verification remain compatible with the current
  Phase 3 contract.

## Verification Evidence

- Focused correction/workflow/evidence suite:
  `74 passed`.
- Full offline suite, `python -m pytest -q -m "not cloud and not ocr"`:
  `468 passed, 22 deselected`.
- `python -m ruff check src tests`: passed.
- `python -m pip check`: no broken requirements.
- `git diff --check`: no implementation whitespace error; only the pre-existing
  Windows line-ending notice for `.planning/config.json` was emitted.
- Manual review covered `CorrectionProvenance`, canonical correction IDs,
  `apply_correction()`, extraction/fact cross-validation, `DiagnosisWorkflow.rerun()`,
  corrected source-bundle validation, evidence serialization, and both positive and
  adversarial regression tests.

## Residual Test Boundary

Cloud and OCR markers remain intentionally excluded from this offline review. They do
not exercise the local correction/evidence contract changed by `9f1d1ad`; their live
credential and model-resource gates remain separate project verification work.
