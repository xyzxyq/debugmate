---
phase: 09-current-evaluation-evidence
plan: 02
subsystem: evaluation-evidence
tags: [pydantic, pytest, powershell, privacy, deterministic-reports]
requires:
  - phase: 09-current-evaluation-evidence
    provides: strict locked-case and prompt-comparison contracts from Plan 01
  - phase: 08-dify-unified-live-chain
    provides: the formal Phase 08 source contract that live eligibility must reopen
provides:
  - hash-bound current-source collection with explicit Phase 10 eligibility reasons
  - canonical JSON and privacy-safe Markdown evidence projections
  - frozen-media PowerShell gate for Phase 10 boundary protection
affects: [09-03, phase-10-course-media, evaluation-runner]
tech-stack:
  added: []
  patterns:
    - fail-closed reopening through existing evidence and result validators
    - canonical JSON projections with grouped display-only SHA-256 fingerprints
    - Git-status frozen-media gate plus scoped projection privacy scan
key-files:
  created:
    - src/debugmate/evaluation/collector.py
    - src/debugmate/evaluation/reports.py
    - scripts/verify-phase9-scope.ps1
    - tests/evaluation/test_course_source_manifest.py
    - tests/evaluation/test_reports.py
  modified: []
key-decisions:
  - "Treat absent Phase 08 formal evidence as an explicit ineligible state, never as a live-success fallback."
  - "Show SHA-256 values in Markdown as grouped fingerprints so the existing export scanner can distinguish them from credentials."
  - "Freeze course PPTX, MP4, SRT, screenshots, and final manifests through a fail-closed Git-status gate."
patterns-established:
  - "Collector rows expose only source-relative paths, hashes, safe state, limitation, and stable exclusion codes."
  - "Projection renderers return bytes only; a later runner owns staging and file publication."
requirements-completed: [EVAL-05, EVID-03]
duration: 13min
completed: 2026-08-11
---

# Phase 09 Plan 02: Current Source Eligibility and Deterministic Reports Summary

**Fail-closed Phase 10 source eligibility with validator-reopened evidence, reproducible JSON/Markdown reports, and a frozen-media scope gate.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-08-11T08:43:13Z
- **Completed:** 2026-08-11T08:56:34Z
- **Tasks:** 2/2
- **Files modified:** 5

## Accomplishments

- Added a current-evidence collector that preserves all four locked case states while requiring exact Phase 08, privacy, citation, diagnosis, and result-bundle validation before Phase 10 eligibility.
- Added canonical JSON and Markdown projections for case results, V1–V4 comparison bindings, workflow sources, and the Phase 10 source ledger.
- Added a PowerShell gate that rejects course-builder use plus new or modified frozen PPTX, MP4, SRT, screenshot, and final-manifest targets.

## Task Commits

1. **Task 1: Collect current case sources and calculate Phase 10 eligibility**
   - `2b351bb` — `test(09-02): add failing current-source and Phase 10 eligibility tests`
   - `d418721` — `feat(09-02): collect hash-bound case evidence and eligibility`
2. **Task 2: Render deterministic source reports and enforce the frozen-media scope gate**
   - `e0c775c` — `test(09-02): add failing deterministic-report and frozen-scope tests`
   - `599b9aa` — `feat(09-02): add Phase 09 source projections and scope gate`

## Files Created/Modified

- `src/debugmate/evaluation/collector.py` — Reopens allowed evidence/result paths and produces safe eligibility rows and a Phase 10 subset ledger.
- `src/debugmate/evaluation/reports.py` — Renders deterministic, privacy-scanned JSON and Markdown projections without writing media.
- `scripts/verify-phase9-scope.ps1` — Fails on frozen course-media drift, builder invocations, or unsafe Phase 09 projections.
- `tests/evaluation/test_course_source_manifest.py` — Covers current Phase 08 source gating and truthful locked-case eligibility.
- `tests/evaluation/test_reports.py` — Covers deterministic report bytes, prompt bindings, privacy rejection, and frozen-target enforcement.

## Decisions Made

- Phase 08's missing formal summary and manifest produce `phase8_formal_evidence_missing`, retaining an honest blocked/ineligible row rather than claiming a live result.
- Result media is trusted only through `verify_result_bundle`; the collector never infers validity from filenames or report text.
- Markdown displays SHA-256 as eight grouped components, retaining an auditable fingerprint while allowing the established export scanner to reject credential-like tokens.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected strict revalidation of already typed evidence models**
- **Found during:** Task 2
- **Issue:** JSON-mode serialization changed enums and tuples before strict revalidation, causing valid report inputs to fail validation.
- **Fix:** Revalidate Python-mode model payloads, then canonicalize only at the report boundary.
- **Files modified:** `src/debugmate/evaluation/reports.py`
- **Verification:** `tests/evaluation/test_reports.py` passes with byte-identical projections.
- **Committed in:** `599b9aa`

**2. [Rule 2 - Missing Critical] Preserved hash evidence without weakening the privacy scanner**
- **Found during:** Task 2
- **Issue:** Raw 64-character SHA-256 strings in Markdown were indistinguishable from high-entropy credential tokens to the existing export scanner.
- **Fix:** Render display-only grouped SHA-256 fingerprints in Markdown while retaining canonical raw hashes in scanner-aware JSON fields.
- **Files modified:** `src/debugmate/evaluation/reports.py`
- **Verification:** All generated JSON and Markdown projections pass `assert_export_safe`.
- **Committed in:** `599b9aa`

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical privacy control).

## Issues Encountered

- The upstream Phase 08 formal summary and manifest are not present. This is correctly represented as a blocked current-live source and does not prevent offline collector/report implementation.

## User Setup Required

None - no external service configuration is required for this plan.

## Known Stubs

None. The `phase8_formal_evidence_missing` result is an intentional fail-closed eligibility state; it is validated source evidence rather than an unwired report placeholder.

## Next Phase Readiness

- Plan 03 can consume the collector, projection, and scope gate for staged, atomic evaluation evidence publication.
- A truthful formal Phase 09 pass remains blocked until Phase 08 Plan 07 publishes its checksum-valid formal evidence bundle.

## Self-Check: PASSED

- All five planned collector, projection, scope-gate, and test files exist.
- All four TDD RED/GREEN commits resolve in Git history: `2b351bb`, `d418721`, `e0c775c`, and `599b9aa`.
- `47 passed` for `tests/evaluation` plus `tests/results/test_security_abuse.py`; scoped Ruff, PowerShell parsing, and `verify-phase9-scope.ps1` all passed.
- The scope gate reports `phase9_scope_gate_passed`; no report output was promoted and frozen Phase 10 media remains outside this plan's change set.

*Phase: 09-current-evaluation-evidence*
*Completed: 2026-08-11*
