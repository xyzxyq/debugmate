---
phase: 08-dify-unified-live-chain
plan: 01
subsystem: cloud-security
tags: [pydantic, dify, receipts, sha256, powershell, tdd]

requires:
  - phase: 07-real-input-privacy-ui
    provides: revision-bound redacted preview approval and immutable local input identity
provides:
  - commandless evidence validation backed by an exact external tracked-file inventory
  - strict bounded Dify run envelope, usage, attempt, retrieval and backend contracts
  - atomic one-way durable receipt persistence before cloud dispatch
affects: [08-02, 08-03, 08-04, 08-05, 08-06, 08-07]

tech-stack:
  added: []
  patterns:
    - external QA acquires Git state while product Python consumes only strict path/hash data
    - provider omissions use literal not_reported rather than fabricated numeric zero
    - receipt persistence uses sibling temp fsync, atomic replace and an exclusive file lock

key-files:
  created:
    - src/debugmate/cloud/contracts.py
    - src/debugmate/cloud/receipts.py
    - scripts/export-phase8-tracked-inventory.ps1
    - tests/cloud/test_run_envelope.py
    - tests/cloud/test_receipts.py
  modified:
    - src/debugmate/dify_live_evidence.py
    - scripts/capture_dify_c03_c04_c06.ps1
    - tests/platform/test_dify_live_evidence.py
    - tests/test_probe_cli.py

key-decisions:
  - "Inventory authorization is an exact sorted repository-relative path plus SHA-256 list; product code never invokes Git."
  - "Dify usage is separate from the run envelope and every absent metric remains the literal not_reported."
  - "A receipt is one canonical JSON file with a file-locked started-to-terminal transition and no approval or provider identifiers."

patterns-established:
  - "Strict provider boundary: frozen extra-forbid models bind case, facts, diagnosis and knowledge build before downstream use."
  - "Durable side-effect receipt: persist started before dispatch and allow exactly one succeeded, uncertain or failed transition."

requirements-completed: [DIAG-02, EVID-01]

duration: 20min
completed: 2026-08-10
---

# Phase 08 Plan 01: Cloud Safety Contracts Summary

**Commandless Git-evidence authorization and bounded Dify contracts with an atomic immutable receipt state machine**

## Performance

- **Duration:** 20 min
- **Started:** 2026-08-09T22:12:06Z
- **Completed:** 2026-08-09T22:31:48Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Removed all subprocess/Git execution capability from `dify_live_evidence.py` and replaced it with exact, sorted, hash-bound external inventory validation.
- Added strict Dify envelope, retrieval trace, usage, attempt, backend, safe failure and receipt contracts with bounded strings and duplicate rejection.
- Added a durable receipt store that persists `started` before dispatch and permits one atomic terminal transition without storing approval material, raw remote IDs or provider bodies.
- Preserved historical C03/C04/C06 validation layout while requiring every CLI path to supply an explicit inventory file.

## Task Commits

TDD RED and GREEN outcomes were committed separately:

1. **Task 1 RED: tracked inventory contracts** - `353c571` (test)
2. **Task 1 GREEN: commandless evidence inventory** - `51786bc` (fix)
3. **Task 2 RED: cloud envelope and receipt contracts** - `c093a97` (test)
4. **Task 2 GREEN: strict contracts and atomic receipt store** - `39ef23a` (feat)
5. **Task 1 verification fix: exporter success status** - `0004b96` (fix)

## Files Created/Modified

- `src/debugmate/dify_live_evidence.py` - Pure inventory-backed evidence validation with no process capability.
- `src/debugmate/cloud/contracts.py` - Strict envelope, trace, usage, attempt, failure, backend and receipt models.
- `src/debugmate/cloud/receipts.py` - File-locked canonical JSON receipt persistence and terminal state machine.
- `src/debugmate/cloud/__init__.py` - Stable public imports for downstream Phase 08 plans.
- `scripts/export-phase8-tracked-inventory.ps1` - Native Git QA boundary producing only sorted `path` and `sha256` entries.
- `scripts/capture_dify_c03_c04_c06.ps1` - Explicit inventory generation and validator argument wiring.
- `tests/platform/test_dify_live_evidence.py` - Adversarial inventory, link/reparse, mismatch and exporter tests.
- `tests/test_probe_cli.py` - Required/malformed inventory CLI tests and historical evidence compatibility.
- `tests/cloud/test_run_envelope.py` - Bounded envelope, trace, usage and attempt tests.
- `tests/cloud/test_receipts.py` - Receipt identity, restart, corruption, leakage and transition tests.

## Decisions Made

- Kept the provider run envelope focused on same-run diagnosis/facts/retrieval/contract data; provider usage remains a separate strict object because omission has independent truth semantics.
- Used SHA-256 fingerprints for every provider/approval-derived identity and retained only the already approved preview hash plus local result identity in receipts.
- Used one canonical JSON file per receipt with an exclusive sibling lock, flushed temporary file and atomic replacement so separate store instances cannot race terminal rewrites.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Normalized successful PowerShell exporter exit status**
- **Found during:** Final verification after Task 2
- **Issue:** The expected `git check-ignore` miss returns native exit code 1, which could remain in `$LASTEXITCODE` and make the capture orchestrator misclassify a successful inventory export as failed.
- **Fix:** Added an explicit `exit 0` after the UTF-8 inventory write and a focused regression assertion.
- **Files modified:** `scripts/export-phase8-tracked-inventory.ps1`, `tests/platform/test_dify_live_evidence.py`
- **Verification:** 67 focused command/evidence tests passed; PowerShell parser passed.
- **Committed in:** `0004b96`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Required for the planned PowerShell capture call chain to report valid exports truthfully; no scope expansion.

## Issues Encountered

- Python-dictionary strict validation of nested enum wire values was inappropriate for provider JSON. Envelope tests were corrected to use `model_validate_json(..., strict=True)`, matching the real provider boundary while preserving strict Python-side models.

## User Setup Required

None - this plan adds offline contracts and QA tooling only. No key value was read or written.

## Known Stubs

None.

## Next Phase Readiness

- Ready for 08-02 knowledge synchronization/readback to consume safe fingerprints and typed failure codes.
- Ready for 08-03/08-04 adapter and orchestration work to use one shared envelope, usage, attempt and durable receipt contract.
- No Phase 9/10 media, course screenshots or deliverables were modified.

## Self-Check: PASSED

- All five key created files exist.
- All five TDD/task/deviation commits resolve as Git commit objects.
- Aggregate focused tests, Ruff, PowerShell parsing and frozen-path scope checks passed before summary creation.

---
*Phase: 08-dify-unified-live-chain*
*Completed: 2026-08-10*
