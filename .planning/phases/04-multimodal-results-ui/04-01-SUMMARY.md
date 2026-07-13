---
phase: 04-multimodal-results-ui
plan: 01
subsystem: result-foundation
tags: [strict-contracts, verified-source, outcome-store, replay-fixture, generation-context]
requires:
  - phase: 03-traceable-diagnosis-workflow
    provides: completed strict outcomes and immutable case/run evidence bundles
provides:
  - exactly pinned Phase 4 runtime and offline pytest marker isolation
  - reproducible committed completed outcome plus current-verifier Phase 3 source bundle
  - strict frozen result identities, terminal state and audio-attempt contracts
  - one indivisible generation profile and verified resolved-font context
  - fail-closed completed-outcome loader and atomic full-redacted-outcome store
affects: [phase-4-presentation, phase-4-card, phase-4-audio, phase-4-publisher, phase-4-ui]
tech-stack:
  added: [gradio-6.20.0, edge-tts-7.2.8, playwright-1.61.0]
  patterns: [canonical-generation-identity, source-revalidation, immutable-outcome-store]
key-files:
  created:
    - src/debugmate/results/contracts.py
    - src/debugmate/results/font.py
    - src/debugmate/results/loader.py
    - src/debugmate/results/outcome_store.py
    - scripts/generate-replay-fixture.py
    - fixtures/replay/index.json
    - tests/results/test_contracts.py
    - tests/results/test_loader.py
  modified:
    - pyproject.toml
key-decisions:
  - "Generation identity is the canonical profile hash of renderer contract versions and the exact resolved font name/SHA-256."
  - "Replay source_path addresses the current Phase 3 case_id/run_id directory below a controlled replay source root."
  - "Outcome storage writes canonical outcome bytes plus a detached integrity hash and refuses overwrite, links, reparse ancestors and noncanonical rereads."
patterns-established:
  - "No renderer receives an outcome until strict outcome validation, current verify_bundle and exact manifest/diagnosis cross-identity checks pass."
  - "Public source failures expose only fixed code/stage values and a value-free message."
requirements-progressed: [MULTI-04, UX-04]
duration: 16m
completed: 2026-07-13
---

# Phase 4 Plan 01: Strict Result Foundation Summary

**Phase 4 now has a pinned, reproducible and fail-closed foundation: only a completed Phase 3 outcome whose immutable source bundle and diagnosis identity reverify can reach presentation code.**

## Performance

- **Duration:** 16m
- **Started:** 2026-07-13T09:30:00+08:00
- **Completed:** 2026-07-13T09:46:00+08:00
- **Tasks:** 3 TDD tasks plus one adversarial reparse hardening cycle
- **Files changed:** 21 including this summary

## Accomplishments

- Pinned Gradio `6.20.0`, edge-tts `7.2.8` and Playwright `1.61.0`; default pytest now excludes cloud, OCR, network, browser and real TTS while retaining deterministic fake-media tests.
- Verified the installed Microsoft Edge Playwright channel by launching a headless page with explicit `channel="msedge"`; no global Python runtime or browser installation was changed.
- Added a deterministic generator and committed fictional replay outcome/source assets. Regeneration is byte-identical, the outcome strict-validates, and the source bundle passes the current Phase 3 verifier.
- Froze strict identities, artifact availability, safe failures, audio attempts/results, terminal manifests and UI state without raw error/path fields or hash-cycle members.
- Bound report/card/recap contract versions and actual font bytes into one immutable `PreparedGenerationContext`; project fonts take precedence and links/escapes fail closed.
- Added a strict loader that revalidates the full workflow outcome, Phase 3 bundle, source manifest, node states and diagnosis bytes before computing canonical `diagnosis_sha256`.
- Added an atomic outcome store that persists the complete redacted strict outcome, refuses duplicates and detects byte, identity, directory, symlink and reparse-ancestor tampering.

## Task Commits

1. **Wave 0 dependencies and reproducible fixture** — `05f24b1` (`test`)
2. **RED result-contract attacks** — `075733f` (`test`)
3. **GREEN strict identities and prepared generation context** — `e9c9ad7` (`feat`)
4. **RED/GREEN verified loader and outcome store** — `a625057` (`feat`)
5. **Adversarial reparse-ancestor RED/GREEN** — `90c960d` (`fix`)

## Decisions Made

- The committed replay directory uses `source/<case_id>/<run_id>/...` beneath its controlled fixture root. This retains the existing Phase 3 verifier's directory-identity guarantee instead of weakening or special-casing `verify_bundle()`.
- `result-manifest.json`, `checksums.sha256`, ZIP and `publication.json` are reserved non-business members; artifact contracts cannot list them, preventing a self-referential publication graph.
- `publication.json` and deterministic ZIP construction remain Plan 04-05 responsibilities; this plan freezes the acyclic member boundary they must consume.
- Outcome-store integrity is byte-exact: harmless whitespace changes are still rejected because restored course evidence must equal the canonical persisted record.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replay source needed the Phase 3 case/run directory shape**

- **Found during:** Task 1 committed fixture verification
- **Issue:** A flat `module-not-found/source/manifest.json` cannot pass current `verify_bundle()` because Phase 3 deliberately binds manifest identity to `case_id/run_id` directory names.
- **Fix:** Preserved the verifier and generated `module-not-found/source/<case_id>/<run_id>/...`; the replay index stores that controlled relative bundle path.
- **Verification:** Both committed verification and temporary regeneration pass; all paths remain relative and confined under `fixtures/replay`.

**2. [Rule 2 - Missing critical safety] Nested reparse ancestors were not rejected by the first store boundary**

- **Found during:** Post-GREEN adversarial self-review
- **Issue:** Checking only the immediate parent could miss a link/reparse point higher in the outcome-store path.
- **Fix:** Added a failing nested-link test and full ancestor traversal used by source and store boundaries.
- **Verification:** `test_outcome_store_rejects_a_reparse_ancestor` failed before the fix and passes afterward; all 16 loader/store tests pass.

---

**Total deviations:** 2 auto-fixed (1 blocking compatibility issue, 1 safety hardening). **Impact:** No scope was reduced; both fixes preserve stricter Phase 3 identity and confinement guarantees.

## Verification

- Focused result contracts + loader/store: `31 passed`
- Complete default offline suite: `499 passed, 22 deselected`
- Full repository Ruff: passed
- `pip check`: no broken requirements
- Exact dependency import/version smoke: passed
- Deterministic replay regeneration and current `verify_bundle()`: passed
- Playwright explicit Microsoft Edge channel smoke: passed
- `git diff --check` over implementation commits: passed
- Phase 3 evidence/audio fail-closed behavior: preserved by the full regression suite

## External Gate Status

- **Dify/VLM and cloud TTS:** not invoked; credentials/provider availability remain explicit later-phase external gates.
- **Real edge/SAPI TTS:** intentionally not invoked in this plan; only the pinned import contract was verified.
- **Browser runtime:** passed locally with installed Microsoft Edge using the explicit Playwright channel.
- **Package installation network:** used only for the approved exact dependency installation; no paid API or model request occurred.

## User Setup Required

None for offline continuation. No API key, paid service or global runtime modification is required for the next plan.

## Next Plan Readiness

- Plan 04-02 can consume only `LoadedDiagnosisSource` plus the indivisible `PreparedGenerationContext` to build the frozen presentation/report/citation projection.
- Later renderers can bind every artifact to the same canonical `ArtifactIdentity` without resolving a second font or trusting filenames.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` and `.planning/config.json` were not modified by this executor.

## Self-Check: PASSED

- All three tasks followed RED → observed expected failure → minimal GREEN → refactor/verification.
- Every task/hardening unit has a selective atomic commit; `.superpowers` was never staged.
- Required source, generated replay, test and summary artifacts exist.
- Full offline regression, Ruff, dependency health, deterministic fixture and Edge smoke have fresh evidence.
- Working tree was clean before adding this summary; orchestrator state/config files remain untouched.

---
*Phase: 04-multimodal-results-ui*
*Completed: 2026-07-13*
