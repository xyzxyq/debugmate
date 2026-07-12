---
phase: 03-traceable-diagnosis-workflow
plan: 05
subsystem: diagnosis-workflow
tags: [approval-gate, workflow, cli, correction, pydantic, tdd]
requires:
  - phase: 02-knowledge-input-safety
    plan: 03
    provides: signed ApprovedRedactedInput and root-confined redacted artifacts
  - phase: 03-traceable-diagnosis-workflow
    plan: 04
    provides: candidate-only generation with local validation and bounded repair
provides:
  - approval-gated ten-stage diagnosis workflow with bounded early outcomes
  - strict diagnosis, correction and rerun JSON boundaries
  - versioned seven-route and bounded-outcome fixture matrix
  - non-interactive six-slot extraction and correction-target CLI view
affects: [03-06-evidence, phase-4-results]
tech-stack:
  added: []
  patterns: [verify-before-stage, immutable-rerun, deterministic-idempotency, strict-json-boundary]
key-files:
  created:
    - src/debugmate/diagnosis/workflow.py
    - fixtures/cases/module_not_found/candidates.json
    - tests/fixtures/diagnosis/workflow_cases.json
    - tests/diagnosis/test_workflow_e2e.py
  modified:
    - src/debugmate/gateway.py
    - src/debugmate/cli.py
    - tests/test_probe_cli.py
key-decisions:
  - "Approval signature, freshness, configured key, root confinement and screenshot hash are verified before input_approved and every provider call."
  - "Ready cases still receive an explicit final route; accepted answers create a new immutable facts revision before final routing."
  - "Correction reruns retain case identity while deriving new facts, run and idempotency identities without mutating the prior outcome."
patterns-established:
  - "Stage prefix contract: early outcomes contain only the completed prefix of the ten canonical stages."
  - "CLI extraction views always expose six ordered slots and stable candidate, fact and correction field identifiers."
requirements-completed: [INP-02, INP-03, SAFE-04, DIAG-01, DIAG-02, DIAG-03, DIAG-04, DIAG-05, DIAG-06]
duration: 24m
completed: 2026-07-12
---

# Phase 3 Plan 05: Approval-Gated Workflow and CLI Summary

**Signed, hash-bound redacted inputs now drive a deterministic pausable diagnosis workflow, with immutable correction reruns and versioned offline route/outcome coverage.**

## Performance

- **Duration:** 24m
- **Started:** 2026-07-12T14:42:00+08:00
- **Completed:** 2026-07-12T15:06:34+08:00
- **Tasks:** 1 TDD task
- **Files modified:** 8

## Accomplishments

- Added approval-key, freshness, signature, screenshot-root and screenshot-hash checks before the first named stage or any extraction, retrieval or generation call.
- Orchestrated provisional routing, category-aware sufficiency, accepted-answer revision, final routing, retrieval and locally validated generation in the locked ten-stage order.
- Added deterministic needs-information, insufficient-information, generation-failed and completed outcomes; early outcomes expose only completed stages and at most three questions.
- Added correction reruns with immutable prior output, stable case identity and distinct revision, facts hash, run ID and idempotency key.
- Added one primary module-not-found candidate fixture plus a single versioned matrix covering all other categories, unknown and bounded workflow variants.
- Added strict JSON diagnosis/correction/rerun seams and a CLI view with all six extraction slots, provenance, confidence and stable correction targets.

## Task Commits

1. **RED: approval, workflow, fixture and CLI contracts** - `00c497a` (test)
2. **GREEN: approval-gated workflow and strict boundaries** - `52ea79c` (feat)

## Files Created/Modified

- `src/debugmate/diagnosis/workflow.py` - Approval-first orchestration, typed outcomes, stage prefixes and immutable reruns.
- `src/debugmate/gateway.py` - Strict JSON diagnosis, correction and rerun domain boundaries while leaving `CloudGateway` transport-only.
- `src/debugmate/cli.py` - Six-slot extraction and correction-target diagnosis view with backend/revision/run/status metadata.
- `fixtures/cases/module_not_found/candidates.json` - Primary dependency/environment candidate fixture.
- `tests/fixtures/diagnosis/workflow_cases.json` - Single versioned matrix for remaining routes and bounded outcomes.
- `tests/diagnosis/test_workflow_e2e.py` - Approval zero-call, stage-order, route, outcome, artifact and rerun proofs.
- `tests/test_probe_cli.py` - Explicit six-slot CLI and stable correction identifier contract.

## Decisions Made

- Workflow entry performs approval and screenshot verification itself even though the production extraction provider independently rechecks the artifact; this defense-in-depth is necessary to prove zero provider calls.
- Idempotency identity binds facts hash, final router rule version, knowledge build ID and Diagnosis schema version; run identity additionally binds case and revision.
- Reruns begin from immutable corrected facts and do not call extraction again, while their stage record remains a canonical prefix for Phase 4 consumption.

## Deviations from Plan

None - the plan was implemented within the Phase 3 JSON/CLI boundary. No UI, report, image, audio, TTS or command-execution capability was added.

## Issues Encountered

- Initial completed fixture rows omitted category high-value fields, correctly producing `needs_information`; the matrix was completed with fictional version/package/device/path values so each intended completed route satisfies the locked policy rather than bypassing it.

## Verification

- Focused E2E and CLI suite: `40 passed`
- Complete offline suite: `421 passed, 20 deselected`
- Full repository Ruff: passed
- `pip check`: no broken requirements
- Prohibited Phase 4/execution capability scan and `git diff --check`: passed

## User Setup Required

None - all required acceptance paths are deterministic and offline.

## Next Phase Readiness

- Plan 03-06 can atomically persist the typed outcome and preserve both original and corrected rerun bundles.
- Phase 4 can consume backend, revision, run/status, ordered stages, six extraction slots and the validated diagnosis without implementing workflow policy.
- No unresolved offline blocker remains. The pre-existing `.planning/config.json` modification remains untouched and uncommitted.

## Self-Check: PASSED

- All required artifacts exist and the RED/GREEN commits are present.
- Approval, wrong-key, stale, forged, unsafe/missing/changed screenshot cases prove zero provider calls.
- Seven routes and four bounded outcomes are covered from committed fixtures.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` and `.planning/config.json` were not edited or committed by this executor.

---
*Phase: 03-traceable-diagnosis-workflow*
*Completed: 2026-07-12*
