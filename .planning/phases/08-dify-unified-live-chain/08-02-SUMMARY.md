---
phase: 08-dify-unified-live-chain
plan: 02
subsystem: knowledge-sync
tags: [dify, knowledge, metadata, readback, attestation, pydantic, tdd]

requires:
  - phase: 08-dify-unified-live-chain
    plan: 01
    provides: sealed sync contracts and safe fingerprint conventions
provides:
  - paginated fail-closed Dify document inventory before mutation
  - bounded indexing wait followed by explicit string metadata writes
  - exact 17-source readback verification and sanitized atomic attestation
  - transport-free default CLI and explicit server-bound cloud gate
affects: [08-03, 08-04, 08-05, 08-06, 08-07]

tech-stack:
  added: []
  patterns:
    - preflight then sealed plan then mutation then indexing then metadata then exact readback
    - remote identifiers exist only in runtime memory and leave the boundary as SHA-256 fingerprints
    - default CLI and PowerShell paths construct no cloud transport

key-files:
  created:
    - tests/knowledge/test_dify_readback.py
  modified:
    - src/debugmate/knowledge/sync.py
    - src/debugmate/cli.py
    - scripts/build_knowledge.ps1
    - tests/knowledge/test_coverage_sync.py

key-decisions:
  - "Dify create/update-by-text payloads contain no unsupported doc_metadata; metadata is resolved and written only after every indexing batch completes."
  - "Live dataset identity is supplied server-side through DIFY_DATASET_ID and never accepted as a CLI argument or serialized raw."
  - "An explicit live execution requires an atomic strict attestation output; default knowledge-sync remains credential-free and transport-free."

patterns-established:
  - "Knowledge transaction: complete pagination and delete authorization precede the first mutation."
  - "Readback proof: exact build/config/source/hash/metadata equality precedes sanitized attestation publication."

requirements-completed: []
duration: 16min
completed: 2026-08-10
---

# Phase 08 Plan 02: Dify Knowledge Sync and Readback Summary

**A fail-closed 17-source Dify synchronization transaction with post-index metadata, exact readback, and fingerprint-only attestation**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-09T22:40:35Z
- **Completed:** 2026-08-09T22:56:29Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added complete bounded pagination that rejects missing pages, changing totals, duplicate source/document identities, malformed metadata and unexpected remote delete candidates before mutation.
- Removed unsupported `doc_metadata` from create/update-by-text requests, waits for every returned batch to complete, creates/resolves nine required string metadata fields, and applies metadata through the batch endpoint.
- Verifies the fixed chunk/retrieval configuration plus the exact 17-source build ID, source/content hashes and source metadata before producing a strict attestation containing only dataset/document fingerprints and response hashes.
- Split local and cloud commands so default `knowledge-sync` constructs no HTTP client, while explicit execution requires the dataset key, server-side dataset binding and an atomic attestation destination.
- Added a PowerShell `-Phase8CloudSync` gate that checks value-free configuration codes before any request and otherwise retains the tested offline default path.

## Task Commits

TDD RED and GREEN outcomes were committed separately:

1. **Task 1 RED: paginated sync/readback contracts** - `f1dc764` (test)
2. **Task 1 GREEN: exact knowledge synchronization and attestation** - `cf0e4ca` (feat)
3. **Task 1 refactor: formatted readback contracts** - `03d380a` (refactor)
4. **Task 2 RED: offline/live CLI gate contracts** - `03e5173` (test)
5. **Task 2 GREEN: CLI and PowerShell explicit cloud gates** - `cd0510c` (feat)

## Files Created/Modified

- `src/debugmate/knowledge/sync.py` - Paginated inventory, indexing polling, metadata field/write APIs, exact readback and sanitized attestation.
- `src/debugmate/cli.py` - Transport-free dry-run, server-only live binding, safe typed failures and atomic attestation output.
- `scripts/build_knowledge.ps1` - Offline default plus explicit Phase 08 cloud synchronization switch.
- `tests/knowledge/test_coverage_sync.py` - Updated create-by-text contract proving metadata is not embedded in that payload.
- `tests/knowledge/test_dify_readback.py` - Adversarial pagination, full 17-source transaction, leak prevention and CLI gate coverage.

## Decisions Made

- Retained the existing sealed `create_sync_plan()` contract and added a higher-level live transaction so full remote inventory is authoritative before a new plan is sealed.
- Kept raw dataset/document/batch/field identities transient; persisted evidence uses SHA-256 fingerprints only.
- Required `--attestation-output` for explicit live CLI execution so a successful remote mutation cannot be reported without durable strict readback evidence.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Ruff initially reported mechanical import/line-layout findings in the new test and sync code; automatic formatting resolved them without behavior changes.
- No real Dify request was made because this plan's offline implementation and gates are complete without consuming credentials or quota. The final credentialed readback remains an explicit later acceptance action.

## User Setup Required

The implementation is complete offline. Closing the live KNOW-03 evidence gate requires a separately authorized run with server-side `DIFY_DATASET_API_KEY` and `DIFY_DATASET_ID`, using the explicit `-Online -Phase8CloudSync` PowerShell path and an attestation output location. No secret value is written or printed.

## Known Stubs

None.

## Verification Evidence

- Focused sync/readback tests: `26 passed, 1 deselected`.
- Complete knowledge suite: `115 passed, 18 deselected`.
- Ruff: all checks passed for `src/debugmate/knowledge`, `src/debugmate/cli.py` and `tests/knowledge`.
- PowerShell parser: `scripts/build_knowledge.ps1` parsed without errors.
- Default PowerShell offline smoke: build, retrieval evaluation, coverage, transport-free sync, knowledge tests and full Ruff all passed with `executed=false`.
- Stub scan: no `TODO`, `FIXME`, placeholder or coming-soon markers in modified files.
- Working tree scope: only the pre-existing concurrent `.planning/STATE.md` modification remained; it was never staged or committed by this plan.

## Next Phase Readiness

- Phase 08 adapter/orchestration plans can consume the strict fingerprint-only readback attestation.
- A credentialed 17-source live synchronization/readback is still required before KNOW-03 may truthfully be marked complete.
- Phase 9/10 evaluation, screenshots, PPTX, MP4, SRT and course media remained untouched.

## Self-Check: PASSED

- All five planned implementation/test files exist.
- All five task/TDD commits resolve as Git commit objects.
- Final focused tests, knowledge regression, Ruff, PowerShell parsing, offline script smoke, scope scan and stub scan passed.

---
*Phase: 08-dify-unified-live-chain*
*Completed: 2026-08-10*
