---
phase: 09
slug: current-evaluation-evidence
status: audited
nyquist_compliant: true
nyquist_scope:
  - 09-01
  - 09-02
pending_plans:
  - 09-03
live_acceptance_pending: true
wave_0_complete: true
created: 2026-08-10
audited: 2026-08-11
---

# Phase 09 - Validation Strategy

> Nyquist validation for executed Plans 09-01 and 09-02 only. Plan 09-03 live collection and atomic promotion remain dependency-blocked on Phase 08 Plan 07 and are not included in the compliant scope.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_evaluation_contracts.py tests/evaluation/test_case_matrix.py tests/evaluation/test_prompt_comparison.py` |
| **Executed-scope command** | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_evaluation_contracts.py tests/evaluation/test_case_matrix.py tests/evaluation/test_prompt_comparison.py tests/evaluation/test_course_source_manifest.py tests/results/test_phase9_collection.py tests/results/test_security_abuse.py tests/evaluation/test_reports.py tests/test_pytest_collection.py` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest -q` |
| **Scope command** | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-phase9-scope.ps1` |
| **Estimated runtime** | Focused contract tests under 30 seconds; executed-scope suite plus scope gate under one minute on the audited workspace |

---

## Sampling Rate

- **After every task commit:** Run the task's focused evaluation tests and Ruff on changed Python files.
- **After every plan wave:** Run all `tests/evaluation`, focused result/security coverage, and the Phase 9 scope verifier.
- **Before 09-01/02 verification:** Run the executed-scope command, scoped Ruff, and the frozen-media scope gate.
- **Before 09-03 promotion:** Require the completed Phase 08 Plan 07 evidence dependency, then run the still-pending formal Phase 9 runner and atomic-promotion checks.
- **Max feedback latency:** Under 30 seconds for contract tasks; dependency-backed live acceptance remains isolated from offline feedback.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Observable behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|---------------------|-----------|-------------------|--------|
| 09-01-01 | 01 | 1 | EVAL-01 | The exact four-case registry covers the locked scenarios, rejects unsafe/currentness drift and fabricated insufficient-case artifacts, and preserves the deterministic local-fallback partial/audio-unavailable state. | unit | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_evaluation_contracts.py tests/evaluation/test_case_matrix.py` | green (13 passed) |
| 09-01-02 | 01 | 1 | EVAL-03 | V1-V4 rows share one immutable sanitized-input identity; prompt/output/source hashes and generated-live versus contract-only provenance cannot drift. | unit | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_prompt_comparison.py` | green (15 passed) |
| 09-02-01 | 02 | 2 | EVAL-05 | Phase 10 eligibility is granted only to a validator-reopened current result with privacy, citation, result, diagnosis, retrieval and knowledge-build bindings; blocked and incomplete sources retain stable exclusion reasons. | integration | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_course_source_manifest.py tests/results/test_phase9_collection.py tests/results/test_security_abuse.py` | green (27 passed) |
| 09-02-02 | 02 | 2 | EVID-03 | Equal validated inputs produce byte-identical safe JSON/Markdown projections, unsafe values are rejected, and frozen course targets/builders are blocked. | integration + scope | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_reports.py; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-phase9-scope.ps1` | green (4 passed; scope gate passed) |
| 09-03-01 | 03 | 3 | EVAL-01, EVAL-03, EVAL-05, EVID-03 | Formal live collection and atomic promotion must fail closed without Phase 08 Plan 07 and may promote only a fully verified ledger. | E2E | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-phase9-evaluation.ps1` | pending - dependency-blocked on 08-07; not audited or counted compliant |

---

## Threat References

| Ref | Threat | Required control |
|-----|--------|------------------|
| T-09-01 | Historical Phase 5/6 or C01-C07 evidence relabelled current | Require the formal Phase 08 Plan 07 summary, manifest, current contract and exact hashes. |
| T-09-02 | Prompt variant output provenance inflated | Separate `generated_live` from `verified_contract`; bind prompt file SHA-256. |
| T-09-03 | Different inputs/facts/retrieval used across V1-V4 | One immutable common-input identity and equality gate. |
| T-09-04 | Secret, private path, approval material or raw provider data leaks | Allowlisted projections plus adversarial privacy/secret scans without echoing the rejected value. |
| T-09-05 | Unsupported artifact or eligibility claim | State-aware availability and eligibility contracts plus exact local-fallback/partial behavior. |
| T-09-06 | Corrupt or mismatched citation/media/ZIP enters course sources | Reopen with existing result validators and bind diagnosis, retrieval and build evidence. |
| T-09-07 | Phase 9 overwrites frozen final screenshots, PPTX, MP4, SRT or final manifests | Immutable baseline plus committed, dirty and untracked target checks. |
| T-09-08 | Failed partial run replaces the last good evaluation ledger | Pending 09-03 sibling staging, all-gates-before-promotion and rollback-residue tests. |

---

## Wave 0 / Executed Coverage

- [x] `src/debugmate/evaluation/contracts.py` - strict bounded case, prompt and Phase 10 source contracts.
- [x] `tests/evaluation/test_evaluation_contracts.py` - strict/extra-forbid/path/hash/currentness contracts.
- [x] `tests/evaluation/test_case_matrix.py` - exact coverage tags and terminal artifact rules.
- [x] `tests/evaluation/test_prompt_comparison.py` - immutable common identity and truthful prompt provenance.
- [x] `tests/evaluation/test_course_source_manifest.py` - formal Phase 08 source validation and fail-closed eligibility.
- [x] `tests/results/test_phase9_collection.py` - positive native result discovery and complete diagnosis-evidence requirement.
- [x] `tests/evaluation/test_reports.py` - deterministic safe projections and frozen-target enforcement.
- [x] `tests/test_pytest_collection.py` - unambiguous pytest module collection.
- [x] `scripts/verify-phase9-scope.ps1` - privacy, tracked/untracked evidence and frozen Phase 10 paths.
- [ ] `scripts/run-phase9-evaluation.ps1` and its live/atomic promotion checks - Plan 09-03 pending on 08-07 and outside this audit scope.

No test framework installation is required.

## Deferred Live Acceptance - Plan 09-03

- `.planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md` and `evidence/dify-live/phase8/manifest.json` remain absent, so live acceptance is correctly blocked.
- No cloud API, browser, formal live collection, report promotion, checksum promotion or rollback/atomicity claim was exercised by this audit.
- The 09-03 E2E command stays pending. Its coverage must not be inferred from the green 09-01/02 offline suites.
- Phase 10 screenshots, PPTX, MP4, SRT and final media manifests remain frozen and outside this validation run.

---

## Manual-Only Verifications

None for executed Plans 09-01 and 09-02. Plan 09-03 is dependency-pending, not reclassified as manual-only.

---

## Validation Audit 2026-08-11

| Metric | Count |
|--------|-------|
| Executed tasks audited | 4 |
| Behavioral coverage gaps found | 0 |
| Validation-map/documentation gaps corrected | 4 task rows plus scoped frontmatter |
| New tests required | 0 |
| Focused tests executed | 60 |
| Focused tests passed | 60 |
| Escalated implementation bugs | 0 |
| Deferred tasks | 1 (`09-03-01`) |

Additional gates: scoped Ruff passed; `scripts/verify-phase9-scope.ps1` reported `phase9_scope_gate_passed`.

## Validation Sign-Off

- [x] All four executed 09-01/02 tasks map to behavioral automated tests and were run green.
- [x] Sampling continuity has no three consecutive executed tasks without automated feedback.
- [x] No watch-mode flags are used.
- [x] `nyquist_compliant: true` is scoped only to `nyquist_scope: [09-01, 09-02]`.
- [x] Plan 09-03 live acceptance and atomic promotion remain explicitly pending and unclaimed.
- [x] No implementation, Phase 10 media, project state, roadmap or requirements file was modified.

**Approval:** Nyquist-compliant for executed Plans 09-01 and 09-02 on 2026-08-11. Plan 09-03 remains dependency-blocked on Phase 08 Plan 07 and requires a separate live/atomic validation run.
