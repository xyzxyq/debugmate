---
phase: 03-traceable-diagnosis-workflow
plan: 04
subsystem: diagnosis-generation
tags: [pydantic, candidate-adapter, contract-repair, privacy, dify]
requires:
  - phase: 03-traceable-diagnosis-workflow
    plan: 01
    provides: DiagnosisRecord 1.1 strict graph and inert command policy
  - phase: 03-traceable-diagnosis-workflow
    plan: 03
    provides: final routing decisions and build-bound evidence anchors
provides:
  - bounded candidate-only fixture and Dify adapter port
  - local DiagnosisGenerator publication authority with strict semantic and privacy validation
  - exactly one controlled contract repair followed by typed generation failure
affects: [03-05-workflow, 03-06-evidence, phase-4-results]
tech-stack:
  added: []
  patterns: [candidate-only-adapter, local-publication-authority, bounded-repair-budget]
key-files:
  created:
    - src/debugmate/diagnosis/generation.py
    - tests/diagnosis/test_generation_repair.py
    - tests/diagnosis/test_dify_diagnosis_cloud.py
  modified:
    - src/debugmate/adapters/base.py
    - src/debugmate/adapters/fixture.py
    - src/debugmate/adapters/dify.py
    - src/debugmate/gateway.py
    - src/debugmate/probe.py
    - tests/test_fixture_adapter.py
    - tests/test_probe_cli.py
    - platform/dify/README.md
key-decisions:
  - "Adapters expose only a bounded JSON candidate and safe run metadata; they never construct DiagnosisRecord."
  - "Privacy and unsafe-command failures are non-repairable, while bounded contract errors receive exactly one repair."
  - "Legacy capability probes must pass adapter candidates through DiagnosisGenerator before publishing evidence."
patterns-established:
  - "Transport retry count remains independent from the local two-call generation ceiling."
  - "Repair inputs contain only Schema version, bounded code/pointer pairs, and the already-redacted candidate."
requirements-completed: [SAFE-04, DIAG-02, DIAG-03, DIAG-04, DIAG-05]
duration: 11m
completed: 2026-07-12
---

# Phase 3 Plan 04: Candidate Generation and Controlled Repair Summary

**Fixture and Dify outputs are now untrusted bounded candidates that only a strict local generator can publish, with one controlled repair and explicit failure after a second rejection.**

## Performance

- **Duration:** 11m
- **Started:** 2026-07-12T14:42:41+08:00
- **Completed:** 2026-07-12T14:53:47+08:00
- **Tasks:** 1
- **Files modified:** 11

## Accomplishments

- Replaced adapter-side `DiagnosisRecord` construction with a 256 KiB JSON-only `CandidateRunResult` boundary for fixture and Dify transports.
- Added strict local case, final-route, fact, evidence, knowledge-build, support-graph, command and privacy validation.
- Added first-call success, one successful repair, invalid-twice typed failure, non-repairable safety failure and transport-retry independence proofs.
- Added a credential/app-gated real Dify smoke that is excluded by default and skips cleanly without configuration.
- Kept provider response bodies, headers and outer reasoning fields outside the documented candidate output.

## Task Commits

The task followed RED-to-GREEN TDD and atomic compatibility verification:

1. **RED: candidate generation and repair contracts** - `3dcd0a4` (test)
2. **GREEN: candidate-only adapters and local publication authority** - `cee67eb` (feat)
3. **Compatibility fix: route legacy probes through local validation** - `8c56f34` (fix)
4. **Boundary proof: exclude provider internals** - `047143a` (test)

## Files Created/Modified

- `src/debugmate/diagnosis/generation.py` - Strict generation request, safe issue contract, one repair and typed outcomes.
- `src/debugmate/adapters/base.py` - Candidate-only port and bounded JSON envelope.
- `src/debugmate/adapters/fixture.py` - Deterministic fixture candidate transport without diagnosis publication.
- `src/debugmate/adapters/dify.py` - Documented output unwrapping with narrow expected-error handling.
- `src/debugmate/gateway.py` - Candidate return type at the approved cloud boundary.
- `src/debugmate/probe.py` - Local generator validation before legacy probe evidence publication.
- `tests/diagnosis/test_generation_repair.py` - Parse, Schema, semantic, safety, repair, retry and leakage proofs.
- `tests/diagnosis/test_dify_diagnosis_cloud.py` - Optional real Dify candidate smoke.
- `tests/test_fixture_adapter.py` - Candidate-only fixture adapter contract.
- `tests/test_probe_cli.py` - Probe compatibility assertions for the narrowed adapter.
- `platform/dify/README.md` - Candidate output, local authority, repair budget and cloud-smoke instructions.

## Decisions Made

- Candidate envelopes accept JSON values only, deep-copy the payload and reject payloads over 256 KiB before domain validation.
- A repairable candidate may cause one second generation call; privacy and unsafe-command failures stop immediately without echoing the candidate into a repair request.
- Full fact and evidence objects must match the validated request, not only their IDs, preventing forged values under reused identifiers.
- The generator can validate an already-returned candidate so approved upload/probe flows do not make an unnecessary second initial cloud call.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Migrated Phase 1 probe and gateway consumers to the candidate-only port**

- **Found during:** Full offline verification after GREEN
- **Issue:** Existing gateway imports and capability probes still required the removed `WorkflowRunResult.diagnosis`, causing collection errors and five probe regressions.
- **Fix:** Updated the gateway return type and routed fixture/cloud probe candidates through `DiagnosisGenerator` before writing validated evidence.
- **Files modified:** `src/debugmate/gateway.py`, `src/debugmate/probe.py`, `tests/test_probe_cli.py`
- **Verification:** Probe-focused tests pass and the complete offline suite reports 397 passed.
- **Committed in:** `8c56f34`

---

**Total deviations:** 1 auto-fixed (1 blocking compatibility issue). **Impact:** The fix preserves prior probe behavior while enforcing the new local publication boundary; no workflow, UI, media or command execution scope was added.

## Issues Encountered

- Strict Python-object validation rejects enum strings even when strict JSON validation correctly accepts JSON enum values. Candidate validation therefore uses `model_validate_json(..., strict=True)` as required by the project contract while retaining strict primitive types.

## Verification

- Focused generation and fixture adapter: `25 passed`
- Complete diagnosis suite: `116 passed, 3 deselected`
- Complete offline suite: `397 passed, 22 deselected`
- Explicit Dify cloud marker without credentials/app configuration: `1 skipped`
- Full repository Ruff: passed
- `pip check`: no broken requirements
- Adapter publication/raw-provider static scan and `git diff --check`: passed

## User Setup Required

None for offline acceptance. The optional real Dify smoke requires `DIFY_API_KEY` and `DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED=1` and remains a non-blocking external gate.

## Next Phase Readiness

- Plan 03-05 can orchestrate approved extraction, final routing, retrieval and generation through the candidate-only port.
- Typed `completed` and `generation_failed` outcomes expose attempts, safe issues, completed stages and retry scope without partial diagnosis publication.
- No unresolved offline blocker remains; the pre-existing `.planning/config.json` modification is untouched and uncommitted.

## Self-Check: PASSED

- All required created files exist.
- Four 03-04 task/fix commits are present in Git history.
- Focused, diagnosis, full offline, cloud-skip, Ruff, dependency, boundary and diff gates pass.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` and `.planning/config.json` were not edited or committed by this executor.

---
*Phase: 03-traceable-diagnosis-workflow*
*Completed: 2026-07-12*
