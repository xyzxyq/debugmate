---
phase: 09-current-evaluation-evidence
fixed_at: 2026-08-11T10:34:43Z
review_path: .planning/phases/09-current-evaluation-evidence/09-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 09: Code Review Fix Report

**Fixed at:** 2026-08-11T10:34:43Z
**Source review:** `.planning/phases/09-current-evaluation-evidence/09-REVIEW.md`
**Iteration:** 1

**Summary:**

- Findings in scope: 5
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: Prompt provenance is hash-bound to a file but not bound to that file's evidence content

**Files modified:** `src/debugmate/evaluation/contracts.py`, `tests/evaluation/test_prompt_comparison.py`, `tests/evaluation/test_reports.py`, `evidence/evaluation/phase9/accepted-v1-contract.json`, `evidence/evaluation/phase9/run-v2.json`
**Commit:** d0efb8b
**Applied fix:** Added strict accepted-V1 and provider-run manifest contracts, reopened hash-bound evidence bytes, and compared every common-input, prompt, conclusion, diagnosis, result, and candidate identity before accepting comparison provenance. Generated-live rows now require their own provider-run receipt, while the V1 contract is restricted to one exact source.

### CR-02: Frozen-media enforcement can be bypassed by committing the drift before the gate runs

**Files modified:** `scripts/verify-phase9-scope.ps1`, `tests/evaluation/test_reports.py`
**Commit:** 1b5dfe3
**Status:** fixed: requires human verification
**Applied fix:** Bound the scope gate to immutable pre-Phase-09 commit `c8c5d82b8cc5773b387de668ccc866faa8e9bebb`, verified ancestry, compared the protected path range through HEAD, retained dirty/untracked rejection, and added a committed-drift bypass regression test.

### WR-01: Phase 08 formal acceptance manifest is validated with an incompatible run-bundle verifier

**Files modified:** `src/debugmate/evaluation/collector.py`, `tests/evaluation/test_course_source_manifest.py`
**Commit:** 1e716da
**Applied fix:** Replaced generic run-bundle verification with strict Phase 08 formal manifest and live-run models. The validator now requires zero-skip cloud and Edge summaries, exact inner artifacts, the 17-source readback contract, backend and QA-run bindings, output hashes, regular non-link files, and complete checksums.

### WR-02: The deterministic result path cannot satisfy the existing result verifier's identity contract

**Files modified:** `src/debugmate/evaluation/collector.py`, `tests/results/test_phase9_collection.py`
**Commit:** d058c44
**Status:** fixed: requires human verification
**Applied fix:** Replaced the literal `result` path with bounded discovery of exactly one native `<product-case-id>/<result-id>` candidate beneath the locked P9 case root. The collector rejects links, reparse points, excessive or ambiguous candidates and verifies directory, manifest, backend, status, and availability identities. A real publisher/verifier test reaches `phase10_eligible=True`.

### WR-03: Citation/build binding is optional on the eligibility path

**Files modified:** `src/debugmate/evaluation/collector.py`, `tests/results/test_phase9_collection.py`
**Commit:** 4038f77
**Status:** fixed: requires human verification
**Applied fix:** Made `outcome.json`, `retrieval.json`, and `knowledge-build.json` mandatory as a complete regular-file set for any otherwise eligible diagnosis result. Strict parsing, retrieval-to-build binding, anchor comparison, and case/run/diagnosis/backend/status identity checks now fail closed with stable exclusion codes. Tests cover all seven incomplete subsets and one fully bound eligible bundle.

## Verification

- Phase 9 evaluation, native-result, and collection guard: 46 passed.
- Result security abuse guard: 14 passed.
- Phase 9 scope gate: `phase9_scope_gate_passed`.
- Ruff on the changed Phase 9 Python/test scope: passed.
- No Phase 09-03 formal runner or cloud API was invoked.

---

_Fixed: 2026-08-11T10:34:43Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
