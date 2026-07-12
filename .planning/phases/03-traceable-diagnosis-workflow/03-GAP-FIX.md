---
phase: 03-traceable-diagnosis-workflow
status: passed
finding: followup-user-fact-correction-provenance
fixed: 1
commit: 9f1d1ad
verified_at: 2026-07-13
---

# Phase 03 Gap Fix

## Result

The remaining Phase 03 review finding is closed. A provenance-free, user-only fact
created by the bounded follow-up round can now be corrected in the next contiguous
revision, strictly JSON-round-tripped, published against its verified source bundle,
and independently verified. `DiagnosisWorkflow.rerun()` validates the newly assembled
outcome before returning it.

## Implementation

- `CorrectionProvenance` now records the exact source fact candidate IDs, source kinds,
  and confidence. These immutable fields participate in the canonical correction ID.
- `apply_correction()` copies that source snapshot from the exact optimistic-lock target.
- Shared fact validation accepts a first correction only when its source snapshot is
  either the exact matching extraction candidate set or the canonical empty-candidate,
  user-only follow-up state. Later corrections must preserve the exact prior transition.
- Corrected publication compares the recorded source snapshot with the fact in the
  already hash-verified source bundle before beginning a new evidence bundle.
- Empty-candidate OCR/VLM claims, nonexistent candidate IDs, and corrected USER facts
  without a verified source bundle remain fail-closed.

## TDD Evidence

- RED: the focused new tests produced three expected failures: follow-up correction
  validation, source-bundle publication routing, and missing producer-boundary validation.
- GREEN focused suite: `74 passed` across workflow evidence, workflow E2E, and correction.
- Full offline suite: `468 passed, 22 deselected`.
- Ruff: passed for `src` and `tests`.
- `pip check`: no broken requirements.
- Targeted `git diff --check`: passed; only existing Windows line-ending notices appeared.

## Security Invariants Preserved

- Extraction-backed corrections still require the complete exact candidate and source set.
- Provenance-free correction sources are valid only as `source_kinds=[user]` with confidence
  `1.0`; OCR/VLM cannot be relabelled by dropping candidate provenance.
- The source bundle proves source case/run/revision/hash, correction prefix, source fact ID,
  field, value hash, candidate IDs, source kinds, confidence, and the exact final transition.
- Publication still occurs only after shared outcome validation and source-bundle validation.

## Commit

`9f1d1ad fix(03): bind follow-up correction source provenance`
