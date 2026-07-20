---
phase: quick-260720-ksx-phase-4-ui-debugmate-windows
plan: 01
subsystem: ui
tags: [gradio-6, playwright, msedge, accessibility, responsive-ui]
requires:
  - phase: 04-multimodal-results-ui
    provides: strict ResultViewState, verified DiagnosisRecord, capability downloads, session leases
provides:
  - student-first two-step diagnosis flow with progressive disclosure
  - strict state and verified-diagnosis presentation contracts
  - atomic per-gr.Tab locking for Gradio 6.20
  - real Edge desktop and mobile after screenshots
affects: [phase-04-ui, course-demo, future-ui-uat]
tech-stack:
  added: []
  patterns:
    - pure state-to-view mapping separated from verified diagnosis-to-summary mapping
    - native per-tab interaction updates driven by one tabs_enabled fact
key-files:
  created:
    - output/playwright/after-student-idle-desktop.png
    - output/playwright/after-student-completed-desktop.png
    - output/playwright/after-student-completed-mobile.png
  modified:
    - .planning/phases/04-multimodal-results-ui/04-UI-SPEC.md
    - src/debugmate/ui/presentation.py
    - src/debugmate/ui/app.py
    - tests/ui/test_app.py
    - tests/ui/test_view_state.py
    - tests/ui/test_browser.py
    - .gitignore
key-decisions:
  - "Gradio 6.20 tabs are locked by retaining and atomically updating four gr.Tab references; gr.Tabs is never given an unsupported interactive property."
  - "Student summaries localize known categories and precede the untouched evidence report; original enums, IDs and hashes remain available in technical surfaces."
  - "Replay, correction, retry and technical metadata use native state-aware disclosures without weakening session, capability or manifest validation."
patterns-established:
  - "Presentation split: ResultViewState owns outcome/tone/permissions; strict DiagnosisRecord owns category/cause/action."
  - "Progressive disclosure: examples default closed, correction completed/partial-only, retry partial-only, failed tabs locked."
requirements-completed: []
duration: 55min
completed: 2026-07-20
---

# Quick Task 260720-ksx: Student-Friendly DebugMate UI Summary

**A numbered student diagnosis flow with truthful semantic states, localized conclusion summaries, native locked tabs, and verified Windows Edge responsive evidence.**

## Performance

- **Duration:** 55 min
- **Completed:** 2026-07-20
- **Tasks:** 3
- **Files modified/created:** 10

## Accomplishments

- Added immutable pure presentation contracts for neutral/blue/green/amber/red states and strictly validated diagnosis summaries.
- Reworked the UI around `1. 生成脱敏预览` → `2. 确认并开始诊断`, with examples, correction, retry and technical data disclosed only in valid states.
- Implemented the corrected Gradio 6.20 contract: four retained `gr.Tab` components update atomically from `payload.view.tabs_enabled`; idle/running/failed are locked and completed/partial are enabled.
- Localized stable diagnosis categories and placed an ID-free `结论速览` before the unchanged verified technical report.
- Captured and visually inspected real Edge screenshots at 1366×768 idle/completed and 375×812 completed.

## Task Commits

1. **Task 1: Pure state and verified diagnosis presentation contracts** — `096a57e`
2. **Task 2: Student-first layout, disclosures, responsive contract and tests** — `97cf1c4`
3. **Task 3: Real Windows Edge screenshots and interaction acceptance** — screenshots intentionally left uncommitted for the orchestrator, as requested

## Files Created/Modified

- `.planning/phases/04-multimodal-results-ui/04-UI-SPEC.md` — records the audited student workflow, state tones, disclosure rules and supported tab contract.
- `src/debugmate/ui/presentation.py` — pure state view model plus localized, fail-closed verified diagnosis summary.
- `src/debugmate/ui/app.py` — numbered workflow, progressive disclosures, semantic overview, conclusion-first report and per-tab atomic updates.
- `tests/ui/test_app.py` — configuration, callback identity and idle/running/completed/partial/failed tab matrix coverage.
- `tests/ui/test_view_state.py` — pure presentation mapping, empty-boundary and type-failure coverage.
- `tests/ui/test_browser.py` — real Edge interaction, disclosure, responsive and screenshot capture coverage.
- `.gitignore` — ignores generated `.debugmate-runtime/` test output.
- `output/playwright/after-student-*.png` — current-code Edge screenshots, intentionally uncommitted.

## Verification

- `pytest -q tests/ui/test_app.py tests/ui/test_view_state.py tests/ui/test_callbacks.py` — **62 passed**.
- Focused real Edge regressions for student flow, completed contrast and long-content/tall-card — **3 passed**.
- Earlier focused Edge state/layout run plus targeted reruns covered idle/running/completed, responsive geometry, keyboard, partial/failed/fallback and long content; QA-runner-only cases skipped when its capability server was absent.
- `pytest -q tests/ui/test_app.py tests/ui/test_browser.py` — **32 passed, 46 browser-marked deselected** under the repository's default marker policy.
- Ruff and `git diff --check` — passed.
- No owned pytest, Edge or `debugmate.ui.serve` process remained after verification.

## Screenshot Evidence

| File | Geometry | Bytes | SHA-256 |
|------|----------|------:|---------|
| `after-student-idle-desktop.png` | 1366×768 | 98304 | `531ccdf0e05ea937eab10066631863bf946e7e55a70126e50861d6abc2fa46e6` |
| `after-student-completed-desktop.png` | 1366×768 | 188633 | `b53034ad17510e615a1dae6c1cdc3a743049ab4c4d40d6912461bacff9747e3c` |
| `after-student-completed-mobile.png` | 375×812 | 49049 | `28a49bfb74c4341f302f09e30fb3cd63923e428785f009199f9a0489431cdf15` |

## Decisions Made

- Kept `DiagnosisRecord`, `ResultViewState`, capability URLs, manifest verification, one-time preview approval, session leases, replay allowlist, correction identities and retry identities unchanged.
- Used native `gr.Tab(interactive=...)` updates because `gr.Tabs` in Gradio 6.20 has no interactive contract.
- Kept the verified report artifact byte-for-byte as the technical evidence surface and added a separate student-readable summary above it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ignored generated local runtime output**
- **Found during:** Task 3 verification
- **Issue:** Real browser runs created `.debugmate-runtime/` as untracked generated output.
- **Fix:** Added the runtime directory to `.gitignore`; no generated evidence was committed.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` no longer reports runtime output.
- **Committed in:** `97cf1c4`

**2. [Rule 1 - Bug] Updated legacy browser selectors for progressive disclosures**
- **Found during:** Task 3 real Edge regression
- **Issue:** Older tests still assumed replay and command controls were always visible and used superseded labels.
- **Fix:** Opened native disclosures before interacting and retained all original security assertions.
- **Files modified:** `tests/ui/test_browser.py`
- **Verification:** focused real Edge student, contrast and long-content tests passed.
- **Committed in:** `97cf1c4`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both changes were required to validate the planned progressive disclosure flow; no product scope or trust boundary expanded.

## Issues Encountered

- One isolated loopback fixture race returned `ERR_CONNECTION_REFUSED` after `/config` readiness. A clean retry passed; process inspection confirmed no stale server before or after the retry.
- The first visual review showed English category text and an ID-heavy report entry point. The student summary was localized and moved ahead of the unchanged evidence report, then screenshots and Edge tests were rerun.

## Known Stubs

None. Empty root-cause candidates render explicit evidence-insufficient copy rather than a guessed diagnosis.

## Threat Flags

None. Changes are presentation-only and introduce no network endpoint, authentication path, filesystem trust boundary or schema change.

## User Setup Required

None.

## Next Phase Readiness

- UI is ready for orchestrator review and later course-material synchronization.
- Screenshots remain outside Git by explicit instruction and should only be promoted if the orchestrator authorizes evidence packaging.

## Self-Check: PASSED

- Verified all six modified implementation/spec/test files exist.
- Verified commits `096a57e` and `97cf1c4` exist in Git history.
- Verified all three screenshot files exist, are valid PNGs, have the declared geometry and exceed 10 KB.
- Verified no owned test/browser/server process remains.

---
*Quick task: 260720-ksx*
*Completed: 2026-07-20*
