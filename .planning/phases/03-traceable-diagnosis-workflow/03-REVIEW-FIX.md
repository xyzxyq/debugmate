---
phase: 03-traceable-diagnosis-workflow
status: all_fixed
findings_in_scope: 4
fixed: 4
skipped: 0
iteration: 1
fixed_at: 2026-07-12
---

# Phase 3 Code Review Fix Report

## Result

All four findings from `03-REVIEW.md` were fixed with regression coverage. No roadmap,
state, or ephemeral configuration file was committed.

## Fixes

1. **Approved environment binding** (`9a519aa`, `eacd431`)
   - Environment mappings now produce text-located candidates.
   - Canonically serialized environment data participates in source hashes,
     extraction identity, facts identity, idempotency identity, and run identity.
   - Tests cover version/device facts supplied only through environment data and an
     environment-only version change.

2. **Publication lineage validation** (`071e71a`)
   - Added a shared public validator that recomputes and constant-time compares run
     and idempotency identities before evidence directory creation.
   - Publisher-contract versions, exact status-specific stage paths, and
     status-specific field presence are validated before publication.
   - Manifest versions now come from the already validated outcome rather than
     silently replacing caller values.

3. **Canonical CaseFact reconstruction** (`676a959`)
   - Stable fact IDs must match canonical field/value data.
   - Fact values must already be normalized; provenance candidate IDs and source
     kinds must be valid, unique, and sorted.
   - The public `CaseFacts` boundary privacy-scans fact values even when an attacker
     recomputes the aggregate facts hash.

4. **Correction rerun stage semantics** (`b8bb666`)
   - Corrected reruns expose inherited input/extraction/fact-confirmation stages
     separately from newly executed stages.
   - Evidence manifests record inherited node states and retain the source run ID.
   - Rerun validates the previous outcome before applying an overlay.

## Verification

- Focused extraction tests: `7 passed`.
- Focused fact/correction/router/sufficiency tests: `35 passed`.
- Focused workflow/evidence/privacy tests: `58 passed`.
- Full offline suite: `442 passed, 22 deselected`.
- Ruff: `All checks passed!` for `src` and `tests`.

