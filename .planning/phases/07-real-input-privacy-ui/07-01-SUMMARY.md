---
phase: 07-real-input-privacy-ui
plan: 01
subsystem: testing
tags: [pytest, playwright, powershell, privacy, race-safety]

requires:
  - phase: 04-multimodal-results-ui
    provides: Existing Gradio result states, replay flow, and browser evidence conventions
provides:
  - Hash-pinned Phase 07 execution baseline with a strict frozen-scope gate
  - Four exact failing privacy, revision-race, local-only construction, and orthogonal-state contracts
  - Isolated Phase 07 Edge selector, scenario, and value-free evidence-ledger contracts
affects: [07-02, 07-03, 07-04, 07-05]

tech-stack:
  added: []
  patterns:
    - Frozen-scope SHA-256 baseline with independent tracked-target discovery
    - Fail-expecting RED verifier that rejects collection and infrastructure errors
    - Phase-specific browser evidence namespace with an exact allowlist

key-files:
  created:
    - .planning/phases/07-real-input-privacy-ui/07-EXECUTION-BASELINE.json
    - scripts/assert-phase7-frozen-scope.ps1
    - scripts/assert-phase7-red.ps1
    - tests/ui/test_real_input.py
  modified:
    - tests/privacy/test_preview_integration.py
    - tests/ui/test_browser.py

key-decisions:
  - "Pinned dependency readiness is recorded as execution infrastructure and does not complete any Phase 07 product requirement."
  - "Four named RED sentinels are the sole expected failures, so import, collection, and unrelated failures cannot create a false green."
  - "Phase 07 browser evidence is isolated under evidence/ui/phase7 and cannot modify Phase 04 or course-v0.1 captures."

patterns-established:
  - "Frozen media guard: compare exact tracked targets, baseline hashes, baseline-commit dirtiness, worktree dirtiness, and untracked frozen paths."
  - "Evidence ledger guard: accept only viewport, state, mode, OCR status/backend, overflow, screenshot hash, and UTC verification time."

requirements-completed: []

duration: 25 min
completed: 2026-08-09
---

# Phase 7 Plan 1: Execution Baseline and RED Contracts Summary

**A pinned, dependency-ready Wave 0 with strict frozen-media protection, four exact RED product contracts, and an isolated value-free Edge evidence namespace.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-09T08:04:30Z
- **Completed:** 2026-08-09T08:29:28Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Captured SHA-256 values for all 14 tracked frozen deliverable/evidence targets and added a validator that rejects malformed baselines, coverage drift, hash drift, committed drift, worktree changes, and untracked frozen files.
- Restored the pinned Python 3.13 test environment and verified the exact Gradio, Pydantic, RapidOCR, Playwright, Pillow, pytest, and Ruff versions with no broken dependencies.
- Added four deliberately failing Phase 07 sentinels for screenshot audit/hash binding, atomic revision consumption, construction-time local-only behavior, and orthogonal UI state without implementing future production behavior.
- Added Phase 07 Edge scaffolding for the prescribed selectors and P7-VQ scenarios, plus a strict value-free ledger contract isolated from prior evidence namespaces.

## Task Commits

Each task was committed atomically:

1. **Task 1: Establish pinned environment and immutable execution baseline** - `1ca517c` (chore)
2. **Task 2: Freeze privacy, race, construction, and state contracts in RED** - `99f04cc` (test)
3. **Task 3: Freeze Phase 07 Edge selectors and evidence ledger contracts** - `b6f90cb` (test)

## Files Created/Modified

- `.planning/phases/07-real-input-privacy-ui/07-EXECUTION-BASELINE.json` - Execution-start commit and hashes for 14 frozen targets.
- `scripts/assert-phase7-frozen-scope.ps1` - Exact-schema, target-coverage, hash, commit, and dirty-state validator.
- `scripts/assert-phase7-red.ps1` - Clean-collection and exact-four-failure RED semantic gate.
- `tests/ui/test_real_input.py` - Revision/race, local-only, and UI-state Wave 0 sentinels.
- `tests/privacy/test_preview_integration.py` - Screenshot audit, value-freedom, and preview-hash binding cases.
- `tests/ui/test_browser.py` - Phase 07 selector/scenario registry, evidence ledger, and Edge collection scaffolding.

## Decisions Made

- Kept `requirements-completed` empty because this plan establishes executable contracts only; Plans 07-02 through 07-04 must make the product behavior pass.
- Required every real-input construction path, including replay construction, to remain locally constructible before any user action.
- Used a new `evidence/ui/phase7` namespace and exact ledger allowlist so future evidence cannot overwrite frozen Phase 04/course captures or retain input values.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Prevented PowerShell from treating Git's CRLF advisory as validator failure**

- **Found during:** Task 1 negative/positive baseline verification
- **Issue:** A Git safe-CRLF advisory written to stderr was promoted by PowerShell and could falsely fail an otherwise valid frozen-scope check.
- **Fix:** Ran validator-owned Git commands with `core.safecrlf=false` while preserving explicit exit-code and stderr handling.
- **Files modified:** `scripts/assert-phase7-frozen-scope.ps1`
- **Commit:** `1ca517c`

## Issues Encountered

- The editable dependency installation remained active longer than the first command yield. The process was inspected, allowed to finish, and then verified with exact imports and `pip check`; no manual action or authentication was required.

## Known Stubs

No product stubs were introduced. The four named failures are intentional Wave 0 contract gates assigned to Plans 07-02 through 07-04, and the browser cases intentionally collect without writing screenshots until Plan 07-05.

## Threat Surface

No new production endpoint, authentication path, file-access boundary, or schema boundary was introduced. This plan changes only test/readiness infrastructure and a frozen-file integrity check.

## User Setup Required

None - no external service configuration or credentials are required for this plan.

## Next Phase Readiness

- Plan 07-02 can implement screenshot audit/hash binding against exact failing cases.
- Plan 07-03 can implement revision-token atomicity and invalidate stale work against the frozen race matrix.
- Plan 07-04 can assemble the real-input UI against fixed selectors and orthogonal-state expectations.
- Plan 07-05 can capture real Edge evidence only after the product contracts turn green.

## Self-Check: PASSED

- All six authorized files exist.
- Commits `1ca517c`, `99f04cc`, and `b6f90cb` exist in repository history.
- Frozen-scope validation, pinned dependency checks, RED semantic verification, Phase 07 Edge collection, ledger tests, and Ruff all pass.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` were not modified by this plan executor.

---
*Phase: 07-real-input-privacy-ui*
*Completed: 2026-08-09*
