---
phase: 09-current-evaluation-evidence
reviewed: 2026-08-11T10:09:41Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - evaluation/phase9/cases.json
  - evaluation/phase9/prompt-criteria.json
  - scripts/verify-phase9-scope.ps1
  - src/debugmate/evaluation/__init__.py
  - src/debugmate/evaluation/collector.py
  - src/debugmate/evaluation/contracts.py
  - src/debugmate/evaluation/reports.py
  - tests/evaluation/test_case_matrix.py
  - tests/evaluation/test_course_source_manifest.py
  - tests/evaluation/test_prompt_comparison.py
  - tests/evaluation/test_reports.py
  - tests/evaluation/test_evaluation_contracts.py
  - tests/test_pytest_collection.py
findings:
  critical: 2
  warning: 3
  info: 0
  total: 5
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-08-11T10:09:41Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

The Phase 09 Wave 1–2 contracts, collector, deterministic projections, frozen-scope gate, and post-plan pytest basename guard were reviewed. The current fixtures and hashes are internally consistent, and the focused and extended test suites pass. However, the review found two integrity safeguards that can be bypassed and three eligibility/provenance paths that will fail or accept incomplete evidence once Phase 08 evidence becomes available.

The absent `08-07-SUMMARY.md` and `evidence/dify-live/phase8/manifest.json` are the declared dependency blocking Phase 09-03; their absence is not reported as an implementation defect. The findings below concern Wave 1–2 behavior after that dependency is satisfied.

Verification completed:

- `pytest` focused listed tests: 34 passed.
- `pytest tests/evaluation tests/test_pytest_collection.py tests/results/test_security_abuse.py`: 48 passed.
- Ruff on the reviewed Python scope: passed.
- `scripts/verify-phase9-scope.ps1` against the current clean worktree: passed.

## Critical Issues

### CR-01: Prompt provenance is hash-bound to a file but not bound to that file's evidence content

**File:** `src/debugmate/evaluation/contracts.py:473-526`
**Issue:** `PromptSourceEvidence` verifies only that a referenced file exists at an allowed path and has the declared hash. For `evaluation_provider_run`, any current file below `evidence/evaluation/phase9/` is accepted; `accepted_v1_contract` has no path/content restriction at all. `PromptComparisonRow` then accepts arbitrary diagnosis/result/candidate hashes and a `generated_live` label without reopening the referenced evidence and proving that it contains the same case, common input, prompt hash, accepted result, candidate, and conclusion. A self-consistent fabricated payload can therefore pass the schema and be rendered as live or contract-verified evidence.
**Fix:** Parse the referenced evidence through a strict manifest model and compare its recorded case/input/facts/retrieval/build/schema/prompt/diagnosis/result/candidate identities to the row. Restrict `accepted_v1_contract` to the exact accepted V1 evidence type and source. Reject a `generated_live` row unless its own provider-run manifest proves every binding.

```python
evidence = PromptRunManifest.model_validate_json(reference_path.read_bytes(), strict=True)
if evidence.binding != row.expected_binding() or evidence.prompt_sha256 != row.prompt_file.sha256:
    raise ValueError("prompt source evidence does not prove the comparison row")
```

### CR-02: Frozen-media enforcement can be bypassed by committing the drift before the gate runs

**File:** `scripts/verify-phase9-scope.ps1:35-42`
**Issue:** `Assert-FrozenTargets` only inspects `git status --porcelain`. A changed PPTX, MP4, SRT, screenshot, or media manifest disappears from that output once committed, so the gate passes even though the supposedly frozen bytes differ from the pre-Phase-09 baseline. The test at `tests/evaluation/test_reports.py:111-141` covers only unstaged drift and an untracked file, leaving the committed-drift bypass untested. This does not meet the plan's byte-for-byte baseline guarantee.
**Fix:** Pass an immutable pre-phase baseline commit or a checked-in frozen hash inventory to the gate, and compare every protected path against it in addition to rejecting dirty/untracked targets. Add a test that commits a changed frozen file after the baseline and proves the gate still fails.

```powershell
$changed = Invoke-GitChecked -Root $Root -Arguments @(
    'diff', '--name-only', "$BaselineCommit..HEAD", '--',
    'deliverables', 'evidence/course-v0.1'
)
```

## Warnings

### WR-01: Phase 08 formal acceptance manifest is validated with an incompatible run-bundle verifier

**File:** `src/debugmate/evaluation/collector.py:97-109`
**Issue:** `validate_phase8_live_source()` calls `verify_bundle(manifest.parent)`. That verifier expects a generic `RunManifest` bundle whose directory identity matches its `case_id`; the fixed directory here is named `phase8`, while valid product case IDs use `case_<32 hex>`. Phase 08 Plan 08-07 also defines this file as a formal acceptance manifest binding the QA run, worktree scope, and inner artifacts, not as the generic per-run manifest. Once the dependency files exist, valid formal evidence will still be classified as `phase8_manifest_invalid`.
**Fix:** Introduce or reuse the strict Phase 08 formal acceptance-manifest/checksum validator. Validate the exact `manifest.json`, `live-run.json`, required inner artifacts, backend, zero-skip status, and checksums instead of passing the formal root to `verify_bundle()`.

### WR-02: The deterministic result path cannot satisfy the existing result verifier's identity contract

**File:** `src/debugmate/evaluation/collector.py:113-140`
**Issue:** The collector always opens `evidence/evaluation/phase9/<P9 case>/result`. `verify_result_bundle()` requires the leaf directory name to equal `result_<hash>` and its parent directory name to equal the product `case_<32 hex>` identity. The registry's `P9-C0*` directory and literal `result` leaf satisfy neither constraint, so every otherwise valid staged result is rejected and no case can become Phase 10 eligible. Current tests assert only the missing-bundle branch and do not construct one valid eligible bundle.
**Fix:** Stage or discover the bundle using the verifier's native `<product-case-id>/<result-id>` layout beneath the locked P9 case root, require exactly one bounded non-link candidate, and then verify its identity maps to the staged outcome and registry row. Add a positive test that produces a real supported bundle and reaches `phase10_eligible=True`.

### WR-03: Citation/build binding is optional on the eligibility path

**File:** `src/debugmate/evaluation/collector.py:154-170`
**Issue:** `_validate_staged_outcome()` returns success when `outcome.json` is absent, and it also skips `bind_retrieval_evidence()` unless both `retrieval.json` and `knowledge-build.json` exist. Thus an otherwise valid result can become eligible with neither file, or with only one of the pair, even though Wave 2 requires citation evidence to be bound to the exact retrieval trace and knowledge build. `verify_result_bundle()` validates the result's internal citation graph, but it does not prove those citations came from the declared retrieval/build evidence.
**Fix:** For every diagnosis-bearing row considered for eligibility, require all three staged files as a set, reject links/reparse points, strictly validate them, bind retrieval to the build manifest, and compare the resulting anchors and identities with the outcome/result. Return stable missing/mismatch exclusion codes. Add tests for no files, each one-file/two-file subset, and a fully valid bound set.

---

_Reviewed: 2026-08-11T10:09:41Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
