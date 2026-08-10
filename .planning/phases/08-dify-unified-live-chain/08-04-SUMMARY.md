---
phase: 08-dify-unified-live-chain
plan: 04
subsystem: result-provenance
tags: [pydantic, execution-backend, manifests, cache-identity, tdd]

requires:
  - phase: 08-dify-unified-live-chain
    plan: 01
    provides: strict ExecutionBackend enum and cloud boundary contracts
  - phase: 08-dify-unified-live-chain
    plan: 03
    provides: bounded Dify run envelope and immutable gateway inputs
provides:
  - required execution backend truth on diagnosis outcomes, result manifests and view states
  - backend-aware immutable result identity and disk re-verification
  - explicit provenance across live, replay, running, completed, partial and failed states
affects: [08-05, 08-06, 08-07, phase-09-evaluation, phase-10-deliverables]

tech-stack:
  added: []
  patterns:
    - execution provenance is independent from ResultMode, generator identity and TTS backend
    - backend participates in canonical result identity and verified immutable reuse
    - stale manifest and outcome shapes are rejected instead of inferred

key-files:
  created:
    - tests/results/test_backend_provenance.py
  modified:
    - src/debugmate/diagnosis/workflow.py
    - src/debugmate/results/contracts.py
    - src/debugmate/results/publisher.py
    - src/debugmate/results/loader.py
    - src/debugmate/results/service.py
    - src/debugmate/results/verifier.py
    - fixtures/replay/module-not-found/outcome.json

key-decisions:
  - "ResultMode remains exactly live|replay; ExecutionBackend is a required orthogonal enum on every trusted outcome, manifest and view."
  - "Result manifest version is 1.1.0 and stale backend-ambiguous manifests are rejected rather than migrated by inference."
  - "Execution backend is part of canonical result identity, so byte-identical local and Dify outputs cannot reuse or relabel one immutable result."

requirements-completed: [UX-01, EVID-01]
duration: 41min
completed: 2026-08-10
---

# Phase 08 Plan 04: Backend Provenance and Result Contract Summary

**Strict execution-backend provenance now survives diagnosis, publication, disk verification, service recovery and every result state without conflating Dify/local/replay execution with media fallback.**

## Performance

- **Duration:** 41 min
- **Started:** 2026-08-10T03:49:06Z
- **Completed:** 2026-08-10T04:30:58Z
- **Tasks:** 2
- **Files modified:** 23

## Accomplishments

- Added required `ExecutionBackend` provenance to `DiagnosisRunOutcome`, `ResultManifest`, `LoadedDiagnosisSource` and `ResultViewState` while keeping `ResultMode` exactly `live|replay`.
- Enforced legal cross-products: live accepts only `dify|local_fallback`, replay requires `replay`, and no filename, artifact, audio backend or generator backend can substitute for the explicit field.
- Bumped the result manifest once to `1.1.0`, included backend in canonical result ID derivation and disk re-derivation, and verified immutable reuse against the same backend.
- Preserved Phase 4 complete, card-partial and audio-partial behavior while ensuring pre-diagnosis failures expose no identity, audio or artifacts.
- Migrated the deterministic replay outcome and strict UI/QA constructors without changing presentation, renderer CSS/layout or frozen course media.

## Task Commits

1. **Task 1 RED: backend provenance contracts** - `b85745b` (test)
2. **Task 1 GREEN: strict outcome/manifest/view backend contract** - `a26911f` (feat)
3. **Task 2 RED: backend-aware publication identity** - `d7d1d62` (test)
4. **Task 2 GREEN: publisher/loader/service propagation** - `b56e7f5` (feat)
5. **Aggregate compatibility: strict UI state migration** - `6fbe7ef` (fix)
6. **Aggregate compatibility: partial composer migration** - `8b50df7` (fix)

## Files Created/Modified

- `tests/results/test_backend_provenance.py` - Orthogonality, cross-product, media fallback, state and cache discrimination regressions.
- `src/debugmate/diagnosis/workflow.py` - Required execution backend on outcomes and inherited replay provenance for corrections.
- `src/debugmate/results/contracts.py` - Manifest 1.1 and strict mode/backend validators.
- `src/debugmate/results/publisher.py` - Backend-aware result ID, manifest, immutable reuse and publication flow.
- `src/debugmate/results/loader.py` - Verified source exposes the strict outcome backend directly.
- `src/debugmate/results/service.py` - Explicit backend propagation through composition, progress, terminal, retry, restore and failure states.
- `src/debugmate/results/verifier.py` - Disk result-ID re-derivation includes manifest backend.
- `fixtures/replay/module-not-found/outcome.json` and `scripts/generate-replay-fixture.py` - Deterministic replay provenance migration.
- UI/QA and associated tests - Required constructor migration only; no backend presentation work or visual redesign.

## Decisions Made

- Preserved diagnosis `backend` as generator/provider identity and `AudioResult.backend` as TTS identity; neither is execution truth.
- Required manifest backend validation from self-contained bytes and refused stale `1.0.0` result manifests instead of guessing their origin.
- Preserved replay provenance across confirmed replay corrections even when the injected local workflow performs deterministic recomposition.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved stale workflow test path**
- **Found during:** Task 1 read-first gate
- **Issue:** The plan referenced removed `tests/diagnosis/test_workflow.py`; current ownership is split across `test_workflow_e2e.py` and `test_workflow_evidence.py`.
- **Fix:** Applied and verified the planned assertions in the two live owner files.
- **Files modified:** `tests/diagnosis/test_workflow_e2e.py`, `tests/diagnosis/test_workflow_evidence.py`
- **Verification:** Task 1 focused group passed 101 tests.
- **Committed in:** `a26911f`

**2. [Rule 3 - Blocking] Migrated strict replay and UI constructors**
- **Found during:** Task 1 focused and default offline collection
- **Issue:** The newly required field made the deterministic replay outcome and existing UI/QA test constructors backend-ambiguous.
- **Fix:** Regenerated only the replay outcome with `replay` provenance and supplied explicit local/replay values at existing constructors. No UI display behavior changed.
- **Files modified:** replay outcome/generator, `src/debugmate/ui/*.py`, diagnosis/UI/result tests
- **Verification:** UI focused regression passed 91 tests; replay canonical regeneration passed.
- **Committed in:** `a26911f`, `6fbe7ef`

**3. [Rule 1 - Bug] Bound verifier result-ID re-derivation to backend**
- **Found during:** Task 2 focused publisher verification
- **Issue:** Publisher identity included execution backend but disk verification initially re-derived the old backend-free identity.
- **Fix:** Added manifest backend to verifier canonical identity input.
- **Files modified:** `src/debugmate/results/verifier.py`
- **Verification:** Task 2 focused group passed 120 tests, including distinct Dify/local IDs.
- **Committed in:** `b56e7f5`

**4. [Rule 3 - Blocking] Migrated two partial-result composer fixtures**
- **Found during:** First default offline regression
- **Issue:** Card-partial and audio-partial E2E composers still used the old callable signature and safely failed before publication.
- **Fix:** Threaded the explicit replay backend through both fixtures.
- **Files modified:** `tests/results/test_result_e2e.py`
- **Verification:** Both directed partial E2E tests passed; final default suite passed 1087 tests.
- **Committed in:** `8b50df7`

---

**Total deviations:** 4 auto-fixed (1 bug, 3 blocking compatibility/path issues)
**Impact on plan:** All were required strict-contract migrations or identity correctness fixes. No network, visual feature, media refresh or future-phase implementation was added.

## Issues Encountered

- The first default suite found only two stale partial composer signatures: 1085 passed and 2 failed. After their focused migration, the second complete run passed.
- The default suite continues to emit one existing Starlette/httpx deprecation warning from installed dependencies.

## User Setup Required

None. This plan is fully offline and consumed no credentials, network quota or provider response.

## Known Stubs

None. Stub scan hits are existing HTML input placeholder attributes and CSS selectors, not unwired runtime data.

## Verification Evidence

- Task 1 strict workflow/contracts/provenance: 101 passed.
- Task 2 publisher/loader/service/media/provenance: 120 passed.
- Strict UI compatibility regression: 91 passed.
- Directed card/audio partial regression: 2 passed.
- Final default offline suite: 1087 passed, 58 deselected, one dependency warning.
- Scoped Ruff and `git diff --check`: passed.
- Frozen Phase 9/10, PPTX, MP4, SRT and course screenshot scan: no diff.
- Secret/raw-ID/provider-body scan: no new execution-provenance leak surface.

## Next Phase Readiness

- Plans 08-05/08-06 can consume one explicit execution backend across orchestration and UI presentation without reading generator or TTS identities.
- Plan 08-07 can assert backend-aware same-run result/receipt evidence and reject stale result manifests.
- Phase 9/10 evaluation and final media remain untouched.

## Self-Check: PASSED

- All planned source/test files and `tests/results/test_backend_provenance.py` exist.
- All six TDD/task/compatibility commits resolve in Git history.
- Focused, UI, partial, Ruff and full offline verification gates passed.
- Only the pre-existing concurrent `.planning/STATE.md` modification remains unstaged and uncommitted.

---
*Phase: 08-dify-unified-live-chain*
*Completed: 2026-08-10*
