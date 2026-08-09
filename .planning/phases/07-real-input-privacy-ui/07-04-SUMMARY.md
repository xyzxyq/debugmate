---
phase: 07-real-input-privacy-ui
plan: 04
subsystem: ui
tags: [gradio, privacy, uploads, concurrency, accessibility, responsive]

requires:
  - phase: 07-real-input-privacy-ui
    provides: Revision-aware preview authority, screenshot audit, shared RapidOCR and local-only service assembly from Plans 07-02 and 07-03
provides:
  - Orthogonal replay, privacy-preview and result-state presentation with deterministic precedence
  - Four-field Gradio input flow with cache-root screenshot confinement and local redacted preview approval
  - One serialized edit, preview, approval and replay authority lane with browser and server invalidation
  - Responsive student workbench using locked AA status colors and accessible interaction targets
affects: [07-05, 08-dify-unified-live-chain]

tech-stack:
  added: []
  patterns:
    - Revision snapshot, expensive local preview, compare-and-publish, atomic consume
    - Capability-served redacted screenshot bytes with no browser-visible server path
    - Orthogonal mode/privacy/result rendering and deterministic status precedence

key-files:
  created:
    - .planning/phases/07-real-input-privacy-ui/deferred-items.md
  modified:
    - src/debugmate/ui/presentation.py
    - src/debugmate/ui/app.py
    - src/debugmate/ui/serve.py
    - tests/ui/test_real_input.py
    - tests/ui/test_app.py
    - tests/ui/test_view_state.py
    - tests/diagnosis/test_workflow_e2e.py

key-decisions:
  - "Only error text or a root-confined screenshot can satisfy primary input; optional code and environment never initiate diagnosis alone."
  - "The browser receives an opaque one-time preview token and capability URL only; raw input, filesystem paths, approval signatures and server preview objects remain private."
  - "Replay invalidates both server authority and browser preview surfaces before fixture service access while preserving every Phase 04 result output position."

patterns-established:
  - "Upload boundary order: absolute lexical confinement, root/component lstat, symlink/reparse rejection, strict resolution, regular-file check, then existing byte/image validation."
  - "Accessible shell: 1440px maximum canvas, 320–360px rail above 1100px, one-column below, 4/8/16/24/32 spacing, 8px radii, 40px targets and 2px focus rings."

requirements-completed: [INP-01, INP-02, SAFE-01, UX-01]

duration: 58 min active execution
completed: 2026-08-09
---

# Phase 7 Plan 4: Real Input Privacy Workbench Summary

**A four-field local Gradio workflow now converts real text or cache-confined screenshots into revision-bound redacted previews, one-time approved diagnosis input and a responsive AA student result page.**

## Performance

- **Duration:** 58 min active execution across the original and continuation executors
- **Started:** 2026-08-09T09:21:51Z
- **Completed:** 2026-08-09T14:30:52Z
- **Tasks:** 3
- **Files modified:** 7 implementation/test files

## Accomplishments

- Added a pure combined presentation model that keeps live/replay mode, privacy-preview lifecycle and result generation state independent, with deterministic precedence and deduplicated `aria-live` announcements.
- Replaced the obsolete fixed preview seam with exactly four real inputs and seven redacted preview surfaces, deterministic environment parsing, local primary-input rejection and one serialized callback lane.
- Confined screenshot filepaths to the configured absolute Gradio cache, rejected parent traversal plus every symlink/reparse component before bytes or OCR, then reused the established format/size/pixel validation.
- Published redacted screenshots through the existing bounded in-memory loopback capability store, so no raw input, approval secret or server filesystem path crosses into the browser.
- Wired revision snapshot/publish, edit invalidation, atomic consume and replay-first invalidation while retaining Phase 04 result, correction, retry, download and media IDs and output positions.
- Shipped the locked AA status palette, 12/14/16/18px typography, 400/700 weights, 40px controls, 2px focus ring, 8px radii and 1100px responsive rail breakpoint without shadows, gradients or new assets.

## Task Commits

1. **Task 1 RED: Specify orthogonal privacy presentation** - `97c7537` (test)
2. **Task 1 GREEN: Implement orthogonal privacy presentation** - `8b1bd16` (feat)
3. **Task 2 RED: Specify real input boundaries** - `99a4c4e` (test)
4. **Task 2 GREEN: Wire safe real input callbacks** - `142eb45` (feat)
5. **Task 3 RED: Specify responsive AA workbench** - `1851adc` (test)
6. **Task 3 GREEN: Deliver responsive AA workbench** - `0e47817` (feat)
7. **Task 3 correctness follow-up: Clear browser preview on replay** - `1600ecf` (fix)
8. **Cross-stage regression fix: Update workflow approval fixtures** - `8228fbf` (fix)

## Files Created/Modified

- `src/debugmate/ui/presentation.py` - Orthogonal privacy/result/mode state and accessible combined rendering.
- `src/debugmate/ui/app.py` - Four inputs, seven preview surfaces, safe upload/capability boundary, queued callbacks and responsive AA shell.
- `src/debugmate/ui/serve.py` - Absolute Gradio cache initialization, shared preview dependency injection and 10 MiB launch limit.
- `tests/ui/test_view_state.py` - Presentation precedence and announcement contracts.
- `tests/ui/test_real_input.py` - DOM, environment parser and upload-confinement contracts.
- `tests/ui/test_app.py` - Callback authority, replay invalidation, component, responsive and accessibility regressions.
- `tests/diagnosis/test_workflow_e2e.py` - Shared strict approval fixture updated for required screenshot audit state.
- `.planning/phases/07-real-input-privacy-ui/deferred-items.md` - Out-of-scope full-suite baseline failures discovered during verification.

## Decisions Made

- Kept optional code and environment in one collapsed disclosure and normalized only known environment keys; unkeyed or duplicate lines receive stable `detail_###` identifiers instead of being discarded.
- Preserved the Phase 04 positional result output list. Preview-only clearers are appended before the session lease, maintaining all established result indices and tab permissions.
- Used the existing loopback capability endpoint for redacted screenshot bytes rather than handing Gradio a server-side artifact path.
- Set `GRADIO_TEMP_DIR` before dependency and Blocks construction and pass the same absolute cache root into callbacks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated a stale local-only TTS test double**
- **Found during:** Task 2 full UI verification
- **Issue:** The test double accepted only positional adapters while production already required the established `local_only=True` constructor contract.
- **Fix:** Made the test double accept and assert the keyword without changing production media assembly.
- **Files modified:** `tests/ui/test_app.py`
- **Commit:** `142eb45`

**2. [Rule 1 - Bug] Cleared browser preview authority when replay starts**
- **Found during:** Final truth audit after Task 3
- **Issue:** Replay invalidated the server record, but the browser could retain the now-unusable token and preview-only surfaces.
- **Fix:** Replay now clears the opaque token, code/environment/screenshot preview, validity and OCR surface in the same queued stream while preserving result outputs.
- **Files modified:** `src/debugmate/ui/app.py`, `tests/ui/test_app.py`
- **Commit:** `1600ecf`

**3. [Rule 1 - Bug] Restored cross-stage workflow fixtures after the strict preview contract**
- **Found during:** Repository-wide verification
- **Issue:** The shared workflow `_approved` factory did not construct the Phase 07-required `screenshot_audit`, causing 64 workflow, evidence and result test failures.
- **Fix:** Added deterministic not-applicable/completed screenshot audit state based on whether the fixture supplies a screenshot.
- **Files modified:** `tests/diagnosis/test_workflow_e2e.py`
- **Commit:** `8228fbf`

## Deferred Issues

- The repository-wide suite reports `913 passed, 92 deselected, 1 failed`. The sole remaining baseline is command-safety rejecting `src/debugmate/dify_live_evidence.py`'s pre-existing `subprocess` import; it is recorded in `deferred-items.md` and was not introduced or modified by this plan.

## Known Stubs

None. All four inputs are connected, every supplied preview category has a real data source, and redacted screenshots use verified capability bytes.

## User Setup Required

None - ordinary live input and replay remain local-only and require no API key, cloud login or paid service.

## Next Phase Readiness

- Plan 07-05 can exercise the finished real-input DOM and serialized authority lane with production OCR/browser evidence.
- Phase 08–10 planning, Phase 04 evidence and course media remain frozen; the 14-target baseline validator passes.
- The full-suite baseline failures should be addressed by their owning diagnosis/evidence plans, not by the Phase 07 UI executor.

## Self-Check: PASSED

- All seven implementation/test files, this summary and `deferred-items.md` exist.
- All eight task/deviation commits (`97c7537`, `8b1bd16`, `99a4c4e`, `142eb45`, `1851adc`, `0e47817`, `1600ecf`, `8228fbf`) exist in repository history.
- Plan-scoped UI/presentation: 72 passed; affected cross-stage workflow/evidence/result tests: 107 passed; scoped Ruff: passed.
- Repository-wide verification: 913 passed, 92 deselected, 1 known pre-existing command-safety failure.
- The frozen-scope validator confirms all 14 tracked targets match the captured baseline.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` were not modified, staged or reverted by this executor.

---
*Phase: 07-real-input-privacy-ui*
*Completed: 2026-08-09*
