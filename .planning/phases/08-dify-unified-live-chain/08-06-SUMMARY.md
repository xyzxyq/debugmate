---
phase: 08-dify-unified-live-chain
plan: 06
subsystem: ui
tags: [dify, gradio, consent, fallback, multimodal, offline-tests]

requires:
  - phase: 08-05
    provides: strict Dify live workflow outcomes and safe cloud failures
  - phase: 07-real-input-privacy-ui
    provides: atomic preview approval and stable Gradio result-page contract
provides:
  - zero-I/O startup selection between configured Dify and explicit local fallback
  - backend-aware consent, progress, failure and blocking-action UI truth
  - offline proof that Dify outcomes reuse the existing report, PNG, MP3 and ZIP chain
affects: [08-07, phase-8-verification, live-acceptance]

tech-stack:
  added: []
  patterns:
    - server-side backend selection from locally verified configuration authority
    - execution backend remains independent from the audio fallback backend

key-files:
  created:
    - tests/ui/test_dify_live.py
  modified:
    - src/debugmate/ui/serve.py
    - src/debugmate/ui/app.py
    - src/debugmate/ui/presentation.py
    - src/debugmate/results/service.py
    - tests/results/test_result_e2e.py

key-decisions:
  - "A verified knowledge readback attestation, not the dataset API key, authorizes ordinary configured Dify construction."
  - "Once Dify is selected, cloud failures remain Dify failures; local composition is never presented as a successful diagnosis fallback."
  - "Execution backend labels are carried explicitly through idle, running, failure, result and ZIP states, independently of Dify/Edge/SAPI audio selection."

patterns-established:
  - "No-I/O factory: dependency construction reads and hashes local authority only; outbound work begins after atomic consent."
  - "Coarse progress truth: upload, Dify workflow and strict local validation precede the existing result stages without percentages."

requirements-completed: [MULTI-03, UX-01]

duration: 47min
completed: 2026-08-10
---

# Phase 8 Plan 06: Ordinary Dify Live Service and UI Wiring Summary

**Configured Dify now starts only from complete local authority and atomic consent, while the unchanged Gradio workbench truthfully exposes backend/stage/failure state and reuses the verified Markdown/PNG/MP3/ZIP pipeline.**

## Performance

- **Duration:** 47 min
- **Started:** 2026-08-10T13:17:21+08:00
- **Completed:** 2026-08-10T14:04:00+08:00
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Added deterministic, construction-time network-free selection of `dify` or `local_fallback`; replay remains a separate allowlisted offline path.
- Preserved the Phase 7 layout and stable component IDs while adding Dify-specific consent, explicit backend labels, coarse live stages, and disabled duplicate/input/replay actions during a blocking run.
- Proved with strict offline integration fixtures that a Dify diagnosis keeps one identity through report, card, 30–60 second MP3, manifest and ZIP, including truthful SAPI fallback and TTS-partial behavior.
- Kept invalid cloud outcomes artifact-free and prevented every configured-cloud failure path from becoming silent local success.

## Task Commits

Each TDD task was committed atomically:

1. **Task 1: Select configured Dify or honest local fallback with zero construction I/O**
   - `6548bc3` — RED dependency-factory contracts
   - `baf3919` — GREEN deterministic Dify/local dependency assembly
2. **Task 2: Wire consent, coarse live stages and backend truth into the existing Phase 7 page**
   - `76a0fa5` — RED UI truth contracts
   - `4f75f31` — GREEN consent, stage and backend presentation
3. **Task 3: Prove verified Dify outcomes reuse the existing MP3 and ZIP result chain**
   - `fd50ca8` — RED multimodal chain integration test
   - `cea7f42` — GREEN complete/partial Dify chain verification

Additional TDD correctness fix:

- `96ce26f` — RED configured-backend failure-label regression
- `935d056` — GREEN preserve backend in initial and safe-failure UI states

## Files Created/Modified

- `src/debugmate/ui/serve.py` — Builds either Dify or explicit local fallback dependencies from local settings, contract hashes and readback attestation without outbound I/O.
- `src/debugmate/ui/app.py` — Carries the configured backend through initial, running and safe-failure states; adds consent truth and blocks conflicting actions during live execution.
- `src/debugmate/ui/presentation.py` — Maps typed backends and coarse stages to safe student-facing labels.
- `src/debugmate/results/service.py` — Emits the real Dify upload/workflow/validation prefix before the existing result-composition stages.
- `tests/ui/test_dify_live.py` — Covers selection, consent boundary, no-network construction, failure isolation, stages, controls and backend truth.
- `tests/ui/test_app.py` — Updates the preserved Phase 7 contract for explicit local fallback copy.
- `tests/ui/test_view_state.py` — Verifies backend-aware view projection.
- `tests/ui/test_real_input.py` — Keeps real-input callback expectations aligned with the extended output tuple.
- `tests/results/test_result_e2e.py` — Verifies complete and TTS-partial Dify outcomes through existing artifacts and ZIP manifests.

## Decisions Made

- Missing `DIFY_DATASET_API_KEY` does not invalidate an ordinary runtime whose app configuration and local readback attestation are already complete; that key remains a sync/final-live-gate concern.
- Fallback selection occurs only before dispatch. After Dify starts, auth, quota, transport and contract failures stay typed Dify failures with no local diagnostic invocation.
- Backend truth is an explicit state dimension. A Dify diagnosis may legitimately use SAPI for audio while remaining `execution_backend=dify`.
- Replay remains fixed, allowlisted and offline; it does not share the ordinary live backend selector.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added real Dify service-stage streaming**
- **Found during:** Task 2
- **Issue:** UI labels alone could not truthfully show upload, Dify workflow and local validation boundaries because the service emitted only result-composition stages.
- **Fix:** Added an execution-backend-specific stage prefix while leaving replay/local stage order and all result-generation semantics unchanged.
- **Files modified:** `src/debugmate/results/service.py`
- **Verification:** Task 2 focused suite passed 88 tests; aggregate suites also passed.
- **Committed in:** `4f75f31`

**2. [Rule 1 - Bug] Preserved configured backend in initial and safe-failure frames**
- **Found during:** pre-verification backend-truth audit
- **Issue:** The configured Dify page could initially display the legacy local preprocessing label, and callback validation failures could be projected as `local_fallback`.
- **Fix:** Parameterized the live idle state and callbacks with the server-selected backend and used it for initial, running and safe-failure views.
- **Files modified:** `src/debugmate/ui/app.py`, `tests/ui/test_app.py`, `tests/ui/test_dify_live.py`
- **Verification:** RED failed on unsupported backend-aware callbacks; GREEN targeted tests passed 2/2 and the default suite passed.
- **Committed in:** `96ce26f`, `935d056`

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 2)
**Impact on plan:** Both fixes were necessary to make progress and backend labels reflect real service state; no visual redesign or new network surface was introduced.

## Issues Encountered

- The first Task 3 partial assertion expected no audio object, but the existing truthful contract intentionally preserves an `AudioResult` carrying safe `tts_failed` metadata while omitting MP3 bytes/hash. The test was corrected to preserve that established partial contract.
- The existing complete-result fixture defaulted to local fallback. Its test helper now accepts an explicit live backend so the legacy test stays local and the new strict Dify case proves backend propagation.

## Verification

- Task 3 focused chain: **41 passed**.
- Privacy/diagnosis/results/UI aggregate: **800 passed, 40 deselected**.
- Default offline suite: **1107 passed, 58 deselected**; deselected live/cloud/browser/TTS gates made no real service calls.
- Ruff: **All checks passed** for `src` and `tests`.
- Phase 7 CSS/layout and stable component IDs remain covered; no Phase 9/10, media, or final-screenshot files changed.

## Known Stubs

None. The `placeholder` matches in `app.py` are real form accessibility/input hints and CSS selectors, not unwired result data.

## Security and Privacy

- No secret values, raw provider bodies, backend selector, or browser-controlled key/config state were added.
- The only outbound-capable path remains behind `consume_current -> approve_preview -> diagnose`.
- No new endpoint, authentication path, file trust boundary or schema was introduced by this plan.

## User Setup Required

None for offline/default operation. Real Dify credentials and acceptance remain intentionally isolated to Plan 08-07.

## Next Phase Readiness

- Plan 08-07 can exercise the real configured Dify acceptance gate without changing ordinary UI or result-generation code.
- No implementation blocker remains; real cloud availability, quota and provider configuration are explicit external acceptance conditions only.

## Self-Check: PASSED

- All nine created/modified implementation and test files exist.
- All eight task/correctness commits are present in repository history.
- `08-06-SUMMARY.md` exists and records the offline gate counts.

---
*Phase: 08-dify-unified-live-chain*
*Completed: 2026-08-10*
