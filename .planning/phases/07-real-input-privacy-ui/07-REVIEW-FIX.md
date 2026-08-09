---
phase: 07-real-input-privacy-ui
fixed_at: 2026-08-09T16:48:35.7739621Z
review_path: .planning/phases/07-real-input-privacy-ui/07-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 07: Code Review Fix Report

**Fixed at:** 2026-08-09T16:48:35.7739621Z
**Source review:** `.planning/phases/07-real-input-privacy-ui/07-REVIEW.md`
**Iteration:** 1

**Summary:**

- Findings in scope: 6
- Fixed: 6
- Skipped: 0

## Fixed Issues

### WR-01: Evidence records fabricated run identities for scenarios that never start a run

**Status:** fixed: requires human verification
**Files modified:** `tests/ui/test_browser.py`, `scripts/run-phase7-real-input-qa.ps1`, `evidence/ui/phase7/P7-VQ-*.json`, and regenerated affected evidence PNGs
**Commit:** 8b26f76
**Applied fix:** Removed synthetic identity hashing from identityless scenarios. The completed replay scenario now waits for the actual run, downloads and validates the server-produced bundle manifest, and hashes only observed case, run, and result identifiers.

### WR-02: Phase 7 evidence validation trusts metadata without validating scenario semantics

**Status:** fixed: requires human verification
**Files modified:** `scripts/run-phase7-real-input-qa.ps1`, `tests/ui/test_browser.py`, and regenerated `evidence/ui/phase7` artifacts
**Commit:** f0e5a22
**Applied fix:** Added an explicit scenario truth map and strict validation for privacy state, result status, mode, OCR fields, viewport keys, field types, and identity presence. Added one valid-set test and fourteen fault-injection cases.

### WR-03: Raw preview uploads remain in Gradio cache after preview processing

**Status:** fixed
**Files modified:** `src/debugmate/ui/app.py`, `tests/ui/test_app.py`
**Commit:** d2b1b54
**Applied fix:** Added confined cached-upload deletion in a `finally` path so raw preview files are removed after successful preview processing, stale preview invalidation, and OCR failure. Regression tests cover all three paths.

### WR-04: Stale correction leases remain valid after ordinary session publication

**Status:** fixed: requires human verification
**Files modified:** `src/debugmate/ui/app.py`, `tests/ui/test_app.py`
**Commit:** c081b87
**Applied fix:** Ordinary identityless publication now revokes the previous correction-lease source; only checked correction transitions preserve it. Regression tests prove stale completed-to-running and failed-to-stale corrections are rejected while a valid correction transition remains supported.

### WR-05: Security scope validation excludes changed scripts and configuration from secret scanning

**Status:** fixed
**Files modified:** `scripts/verify-phase7-security-scope.ps1`, `scripts/run-phase7-real-input-qa.ps1`, `tests/ui/test_browser.py`, `tests/ui/test_local_live.py`, `tests/ui/test_view_state.py`, `tests/privacy/test_models.py`, `tests/privacy/test_preview_integration.py`
**Commit:** d5cc913
**Applied fix:** Expanded the changed-file secret scan to all reviewable text types, including scripts, platform files, and configuration. Binary/media and planning/output exclusions are explicit, and narrowly scoped line markers distinguish synthetic test secrets from scanner-pattern literals. Eight scanner fixture tests cover the policy.

### WR-06: Non-Phase-7 browser tests use a stale replay disclosure label

**Status:** fixed
**Files modified:** `tests/ui/test_browser.py`
**Commit:** e04a242
**Applied fix:** Centralized the current replay disclosure label and replaced stale `查看示例` selectors and duplicated label literals across the browser suite.

## Verification

- Full Phase 7 OCR and real-Edge evidence runner passed after the evidence changes: OCR `1 passed`, browser `10 passed`, and nine evidence pairs were promoted.
- Scoped Phase 7 non-browser/non-OCR regression suite: `186 passed, 31 deselected`.
- WR-06 isolated real-Edge replay-disclosure regression: `1 passed, 89 deselected`.
- Final security scope gate passed with 14 frozen targets and 37 scanned files, with zero secret findings.
- Ruff checks passed for all touched Python files, and `git diff --check` was clean.
- The repository-wide non-browser/non-OCR run completed with `997 passed, 4 failed, 3 skipped, 33 deselected`; the four failures were outside Phase 7 scope (an existing command-safety policy conflict, two upstream HTTP 429 responses, and one configured live Dify TTS gate).

---

_Fixed: 2026-08-09T16:48:35.7739621Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
