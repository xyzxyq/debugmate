---
phase: 03-traceable-diagnosis-workflow
status: all_fixed
findings_in_scope: 2
fixed: 2
skipped: 0
iteration: 3
fixed_at: 2026-07-12
---

# Phase 3 Code Review Fix Report — Iteration 3

## Result

Both remaining final re-review warnings were closed with adversarial tests and two atomic
implementation commits. This report is intentionally left uncommitted for the controller's
final re-review loop.

## Fixes

1. **Mandatory, exact workflow extraction provenance** (`42bdbfd`)
   - Every workflow outcome now retains its `ExtractionRecord`; an imported outcome cannot
     remove `extraction.json` while continuing to claim an executed extraction stage.
   - Facts without an extraction record are restricted to explicit user provenance.
   - When the extraction contains matching `(field_id, value)` candidates, the fact must
     retain the complete canonical candidate-ID set and exact derived source kinds; stripping
     those edges and relabelling the fact as user-only is rejected.
   - Legitimate follow-up facts remain supported only when no matching extraction candidate
     exists and their provenance is exactly `[user]`.

2. **Canonical correction history and source-proven transition** (`ff2487f`)
   - Correction provenance now records its base revision and privacy-scanned reason, verifies
     the reason hash, and derives `correction_id` canonically from the complete immutable
     correction data.
   - Correction revisions must be contiguous, base hashes cannot be reused, and strict public
     outcome validation revalidates nested Pydantic contracts instead of trusting `model_copy`.
   - Published fact summaries now include safe per-value SHA-256 fingerprints while excluding
     raw correction reasons.
   - Corrected publication verifies the source bundle's complete correction prefix, latest
     base revision/hash, old fact ID/field/value hash, new value hash, exact provenance/source
     transition, and byte-for-byte-equivalent unaffected fact summaries before creating a new
     bundle.
   - Revision-1 and revision-2 legitimate reruns publish successfully; arbitrary IDs/reason
     hashes, duplicate/gapped/omitted records, wrong base hashes, arbitrary/self sources, and
     mismatched transitions fail closed.

## Verification

- Focused extraction/correction/workflow/evidence suite: `107 passed`.
- Full offline suite: `462 passed, 22 deselected`.
- Ruff: `All checks passed!` for `src` and `tests`.
- Pip dependency check: `No broken requirements found.`
- `git diff --check`: no implementation patch errors; only the pre-existing
  `.planning/config.json` line-ending warning.
- Worktree after commits contains only the pre-existing `.planning/config.json` change plus
  this intentionally uncommitted iteration-3 report.
