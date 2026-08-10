---
phase: 08-dify-unified-live-chain
plan: 05
subsystem: cloud-orchestration
tags: [dify, receipts, validation, repair, evidence, result-service]

requires:
  - phase: 08-02
    provides: durable one-way Dify receipts and safe terminal contracts
  - phase: 08-03
    provides: bounded Dify adapter, immutable screenshot upload, and same-run envelope
  - phase: 08-04
    provides: strict execution-backend provenance through result publication
provides:
  - consent-bound DifyLiveWorkflow with started-before-dispatch durability
  - strict same-run facts, routing, retrieval, build, diagnosis, command, and privacy validation
  - one bounded safe repair and honest failed/uncertain/succeeded receipt transitions
  - typed Dify failure propagation into the existing result application service
affects: [08-06-live-evidence, 08-07-live-acceptance, phase-09-evaluation]

tech-stack:
  added: []
  patterns:
    - approval fingerprint plus preview hash as one-time durable dispatch identity
    - provider output remains data until strict local outcome validation succeeds
    - upload, workflow, and contract-repair attempts retain fingerprints only

key-files:
  created:
    - src/debugmate/cloud/workflow.py
    - tests/cloud/test_live_workflow.py
    - tests/diagnosis/test_generation.py
  modified:
    - src/debugmate/gateway.py
    - src/debugmate/results/service.py
    - tests/results/test_service.py

key-decisions:
  - "Receipt begin is the atomic one-time consumption boundary and always precedes upload or workflow dispatch."
  - "Primary envelope facts and direct retrieval provenance remain authoritative across the optional single repair."
  - "A started cloud attempt can terminate only as succeeded, failed, or uncertain and never becomes a local success."

patterns-established:
  - "Safe cloud failure: expose only a stable code and receipt status, never exception/provider content."
  - "Repair lineage: sorted allowlisted issue code/pointer entries plus an already-redacted candidate."

requirements-completed: [KNOW-04, DIAG-02, EVID-01]

duration: 24min
completed: 2026-08-10
---

# Phase 8 Plan 5: Core Live Orchestration Summary

**Consent-bound Dify execution now produces either one locally validated same-run outcome or one durable, typed, artifact-free terminal failure.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-08-10T04:40:20Z
- **Completed:** 2026-08-10T05:03:51Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `DifyLiveWorkflow.run(ApprovedRedactedInput) -> DiagnosisRunOutcome`, with approval verification and an immutable `started` receipt before the first adapter call.
- Bound the accepted outcome to canonical facts, deterministic final routing, a direct same-run retrieval trace, the sealed 17-source build/readback attestation, strict DiagnosisRecord 1.1.0, command safety, and privacy scanning.
- Enforced one safe contract repair while keeping primary facts/evidence/build provenance immutable; privacy and dangerous-command failures never repair.
- Recorded upload, workflow, and repair as distinct fingerprint-only attempt events and mapped ambiguous workflow transport to an irreversible `uncertain` receipt.
- Propagated typed Dify validation failures through `ResultApplicationService` without creating evidence, outcome, report, card, audio, or archive artifacts.

## Task Commits

1. **Task 1 RED: live workflow adversarial contracts** - `c0268c1` (test)
2. **Task 1 GREEN: consent-bound Dify orchestration** - `57362a8` (feat)
3. **Task 2 RED: repair and publication contracts** - `d04809e` (test)
4. **Task 2 GREEN: accepted-outcome-only result integration** - `3401c0a` (feat)
5. **Task 2 hardening: distinct upload/workflow attempts** - `a0d8914` (fix)

## Files Created/Modified

- `src/debugmate/cloud/workflow.py` - durable approval/receipt/envelope/repair/outcome orchestration.
- `src/debugmate/gateway.py` - no-network approval verification, safe dispatch metadata, and narrow repair transport.
- `src/debugmate/results/service.py` - typed cloud failure projection with no false result artifacts.
- `tests/cloud/test_live_workflow.py` - success, duplicate, stale build, ambiguity, repair, privacy, and command adversarial gates.
- `tests/diagnosis/test_generation.py` - explicit one-repair budget and safe issue-shape contract.
- `tests/results/test_service.py` - artifact-free typed Dify failure integration test.

## Decisions Made

- Receipt identity hashes the approval signature before combining it with the preview hash; approval IDs and signatures are never persisted.
- Remote upload/run/node identifiers are never copied into outcomes or receipts. Adapter-provided fingerprints or locally derived SHA-256 fingerprints are used instead.
- Repair is delegated through a narrow gateway port that accepts exactly `request_kind`, `schema_version`, `issues`, and `candidate`.
- Result service preserves a cloud failure only when it is one of the allowlisted typed codes; unknown exceptions retain the existing generic safe failure.

## Deviations from Plan

None - plan executed as specified. The repository's existing generation test module is named `test_generation_repair.py`; the planned `tests/diagnosis/test_generation.py` was added for the Phase 08 live-specific invariants without moving or duplicating the earlier suite.

## Issues Encountered

- Exporting the workflow from `debugmate.cloud.__init__` introduced an adapters/cloud package import cycle. The export was removed; the required public seam remains `debugmate.cloud.workflow.DifyLiveWorkflow`.
- The first default-suite invocation used an intentionally short process timeout and was terminated before collection completed. It was rerun normally and passed in full.

## Verification

- Task 1 focused gate: **25 passed**.
- Task 2 focused gate: **35 passed**.
- Ruff plan scope: **passed**.
- Default offline suite: **1096 passed, 58 deselected, 1 third-party deprecation warning**; no cloud marker or live call selected.

## Known Stubs

None. No placeholder/TODO/FIXME or empty production data path was introduced in the created or modified production files.

## User Setup Required

None - this plan adds no external configuration and performs no live Dify call.

## Next Phase Readiness

- Plan 08-06 can use the receipt-bound accepted outcome to publish one current live evidence bundle.
- Plan 08-07 can exercise the explicit cloud-marked live acceptance path without changing the offline default suite.
- Media generation and Phase 09-10 evaluation/delivery remain intentionally frozen.

## Self-Check: PASSED

- All six created/modified implementation and test files exist.
- Commits `c0268c1`, `57362a8`, `d04809e`, `3401c0a`, and `a0d8914` exist in repository history.
- Focused tests, Ruff, and the full default offline suite passed.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` were not staged or modified by this executor.

---
*Phase: 08-dify-unified-live-chain*
*Completed: 2026-08-10*
