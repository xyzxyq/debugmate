---
phase: 03-traceable-diagnosis-workflow
status: all_fixed
findings_in_scope: 4
fixed: 4
skipped: 0
iteration: 2
fixed_at: 2026-07-12
---

# Phase 3 Code Review Fix Report — Iteration 2

## Result

All four iteration-2 findings were fixed using test-first adversarial regressions. The
report is intentionally left uncommitted for the controller's review loop.

## Fixes

1. **Key-aware structured environment extraction** (`5bfb7e7`)
   - Canonically serializes sorted environment entries as `KEY: value`.
   - Explicitly maps established `PYTHON`/`python` keys to `version` and `DEVICE` to
     `device`, while retaining deterministic text locators into the serialized view.

2. **Complete shared outcome-state binding** (`4b96f4c`)
   - The shared validator now binds top-level revision and facts hash to nested
     immutable facts before rerun or publication.
   - Rerun rejects forged top-level fact state even when the nested graph is valid.

3. **Exact fact-to-extraction provenance binding** (`4b96f4c`)
   - Every provenance candidate must exist in the exact `ExtractionRecord`, match the
     fact field/value history, and contribute to the exact canonical candidate set.
   - Source kinds must equal the candidate-derived set; corrected facts additionally
     require a valid user-correction chain back to the extracted source value.

4. **Independently verifiable correction source lineage** (`0ab5d7c`)
   - Correction provenance records its immutable base facts hash.
   - Corrected outcomes bind source run, source revision, and source facts hash and
     reject missing, self, revision-zero, or no-correction inherited lineage.
   - Publication verifies the already-published immutable source bundle before
     beginning a corrected evidence bundle, rejecting arbitrary or tampered sources.

## Verification

- Focused adversarial and workflow suite: `68 passed`.
- Full offline suite: `453 passed, 22 deselected`.
- Ruff: `All checks passed!` for `src` and `tests`.
- Pip dependency check: `No broken requirements found.`
- `git diff --check`: clean except the pre-existing `.planning/config.json` line-ending
  warning; no implementation patch errors.
