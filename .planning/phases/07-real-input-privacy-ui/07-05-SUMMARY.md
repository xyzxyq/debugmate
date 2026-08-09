---
phase: 07-real-input-privacy-ui
plan: 05
subsystem: ui-qa
tags: [msedge, rapidocr, privacy, playwright, evidence, powershell]
requires:
  - phase: 07-04
    provides: real-input privacy workbench and presentation state
provides:
  - real Microsoft Edge acceptance matrix for Phase 07
  - atomic current-run evidence inventory with value-free SHA-bound ledgers
  - fail-closed secret/path and frozen-scope release gate
affects: [phase-08, verification, course-evidence]
tech-stack:
  added: []
  patterns: [owned-loopback-process, atomic-evidence-promotion, exact-inventory-validation]
key-files:
  created:
    - scripts/verify-phase7-security-scope.ps1
    - evidence/ui/phase7/P7-VQ-01.json
    - evidence/ui/phase7/P7-VQ-01.png
  modified:
    - tests/ui/test_browser.py
    - scripts/run-phase7-real-input-qa.ps1
    - src/debugmate/ui/app.py
    - src/debugmate/ui/serve.py
    - tests/ui/test_app.py
key-decisions:
  - "Formal evidence is exactly nine scenario/viewport pairs from one fresh qa_run_id."
  - "OCR-unavailable acceptance uses a suppressed local fault seam while exercising the real upload, preview, and store callback path."
  - "The pre-existing command-safety baseline failure is reported separately and is not treated as a Phase 07 regression."
patterns-established:
  - "Evidence promotion occurs only after OCR/Edge JUnit zero-skip gates and exact ledger/PNG validation."
  - "Frozen historical and future-phase assets are verified by baseline ancestry plus captured SHA-256 values."
requirements-completed: [INP-01, INP-02, SAFE-01, UX-01]
duration: 1h 10m
completed: 2026-08-09
---

# Phase 7 Plan 5: Real Edge Release Gate Summary

Real Microsoft Edge and production RapidOCR now prove the Phase 07 privacy workflow with an atomic, current-run, nine-pair evidence bundle and fail-closed security/frozen-scope gates.

## Performance

- **Duration:** 1h 10m
- **Started:** 2026-08-09T14:27:00Z
- **Completed:** 2026-08-09T15:37:42Z
- **Tasks:** 3
- **Files modified:** 25

## Accomplishments

- Added real Edge coverage for idle, redacted-ready, every-field stale, OCR unavailable, replay, two responsive viewports, mobile sizing, keyboard/focus, AA contrast, grayscale truth, and 200% zoom.
- Published exactly nine JSON/PNG pairs under `evidence/ui/phase7` for `qa_run_id=p7qa_458a8510aaf346c0b6b6dae37ad1cd79`; all ledgers use the exact 15-field allowlist and bind their PNG with SHA-256.
- Added an owned-process PowerShell runner that rejects any OCR/browser skip, stale identity/time, missing/extra pair, hash mismatch, transaction residue, or partial promotion.
- Added a baseline-ancestor, frozen-hash and secret/path scanner with clean and injected-failure tests.
- Restored the frozen Phase 07 copy/DOM contracts and added an honest, value-free `ocr_unavailable` presentation while keeping approval disabled.

## Task Commits

1. **Task 1: Implement the real Phase 07 Microsoft Edge scenarios** — `2d463db`
2. **Task 2: Build and dry-validate the atomic Phase 07 evidence runner** — `497462c`
3. **Task 3: Run the complete privacy, OCR, regression and frozen-scope gate** — `c493343`

## Verification

- Production RapidOCR runner JUnit: `1 passed`, zero skipped/failures/errors.
- Microsoft Edge runner JUnit: `10 passed, 68 deselected`, zero skipped/failures/errors.
- Formal inventory: 9 ledgers + 9 non-empty PNGs, one current qa run, timestamps `2026-08-09T15:29:29.742280Z` through `2026-08-09T15:30:07.395935Z`.
- Phase-scoped privacy/UI regression: `195 passed, 1 deselected`.
- Security negative tests: `5 passed`; clean scan: 0 findings across 6 files; frozen gate: all 14 targets match baseline `32d8837ec9be8d02e053e25faaa6f9beb9954f92`.
- Ruff: all checks passed.
- Default suite: `960 passed, 1 failed, 58 deselected`. The sole failure is the pre-existing, already deferred command-safety baseline: `tests/diagnosis/test_command_safety.py` rejects the existing `src/debugmate/dify_live_evidence.py: subprocess` import. No Phase 07 changed file caused a new default-suite failure.

## Decisions Made

- Kept evidence metadata value-free: stable states and hashes are durable; raw user input, OCR text, paths, tokens, approval capabilities, and result payloads are not.
- Used a suppressed server CLI switch only to make RapidOCR initialization fail deterministically; the browser still uses native file upload and the real preview callback, so the failure claim is not browser-state injection.
- Did not modify the out-of-scope command-safety baseline because it predates this plan and is already recorded in `deferred-items.md`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced incompatible Gradio config parsing**
- **Found during:** Task 3 runner startup
- **Issue:** Windows PowerShell `ConvertFrom-Json` rejected Gradio's valid empty-key config property before OCR/Edge could start.
- **Fix:** Used `JavaScriptSerializer` with explicit dictionary/list checks.
- **Files modified:** `scripts/run-phase7-real-input-qa.ps1`
- **Commit:** `c493343`

**2. [Rule 1 - Bug] Repaired incomplete frozen Phase 07 UI contracts**
- **Found during:** First complete real Edge attempt
- **Issue:** The live app still exposed legacy accordion copy, lacked stable privacy overview/preview boundaries, used non-frozen stale copy, and did not safely present OCR initialization failure.
- **Fix:** Restored frozen copy and selectors, added the privacy group, and mapped `OcrUnavailable` to exact safe copy plus technical code without exposing exception data.
- **Files modified:** `src/debugmate/ui/app.py`, `src/debugmate/ui/serve.py`, `tests/ui/test_app.py`, `tests/ui/test_browser.py`
- **Commit:** `c493343`

**3. [Rule 1 - Bug] Made PNG header validation compatible with Windows PowerShell 5.1**
- **Found during:** Post-Edge evidence validation
- **Issue:** `[Convert]::ToHexString` was unavailable after all Edge tests passed; the transaction correctly rolled back instead of publishing partial evidence.
- **Fix:** Replaced it with deterministic `BitConverter` encoding and reran the complete atomic gate successfully.
- **Files modified:** `scripts/run-phase7-real-input-qa.ps1`
- **Commit:** `c493343`

The long runner had failed attempts before the final successful run: one readiness failure before OCR/Edge, one diagnostic Edge run exposing eight contract/test issues, and one all-green Edge run followed by the PowerShell compatibility failure. Each attempt rolled back without formal evidence; only the final successful run produced the committed inventory.

## Known Stubs

None. The scanned `placeholder=` occurrences are intentional user-input hints and do not represent unwired or mock result data.

## Deferred Issues

- The pre-existing command-safety failure remains recorded in `deferred-items.md`; it is outside Plan 07-05 scope.

## Self-Check: PASSED

- All 18 formal evidence files, three task commits, both gate scripts, and this summary exist.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` were intentionally not modified or staged because the parent orchestrator owns their current updates.
