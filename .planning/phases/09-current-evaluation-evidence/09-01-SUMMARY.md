---
phase: 09-current-evaluation-evidence
plan: 01
subsystem: evaluation-contracts
tags: [pydantic, pytest, sha256, provenance, evaluation, tdd]

requires:
  - phase: 08-dify-unified-live-chain
    provides: backend-aware result contracts and the formal Phase 08 live-evidence acceptance boundary
provides:
  - a strict four-case current-evidence registry with truthful terminal-state rules
  - hash-bound V1-V4 prompt criteria and same-case comparison provenance contracts
  - a fail-closed P9-C01 live-success gate requiring current Phase 08 formal evidence
affects: [09-02, 09-03, phase-10-course-delivery]

tech-stack:
  added: []
  patterns:
    - strict frozen Pydantic contracts with current-file SHA-256 verification
    - explicit generated_live versus verified_contract provenance labels
    - static evaluation criteria never stand in for missing live evidence

key-files:
  created:
    - evaluation/phase9/cases.json
    - evaluation/phase9/prompt-criteria.json
    - src/debugmate/evaluation/contracts.py
    - tests/evaluation/test_contracts.py
    - tests/evaluation/test_case_matrix.py
    - tests/evaluation/test_prompt_comparison.py
  modified:
    - src/debugmate/evaluation/__init__.py

key-decisions:
  - "P9-C01 starts blocked and can claim live success only after both Phase 08 formal artifacts exist as hash-valid regular files."
  - "P9-C04 preserves the established audio-partial state: report, card, recap text and partial bundle are available; MP3 audio is not."
  - "The V2 and V3 criteria bind the repository's current v2-citations.md and v3-reliability.md files, as recorded by prompts/README.md."

patterns-established:
  - "Evaluation sources are normalized repository-relative allowlisted paths with SHA-256 bindings."
  - "Prompt comparisons require one immutable sanitized-input, facts, retrieval, knowledge-build and schema identity."

requirements-completed: [EVAL-01, EVAL-03]

duration: 15min
completed: 2026-08-11
---

# Phase 09 Plan 01: Current-Evidence Registry and Prompt Contracts Summary

**Four-case current-evidence registry and SHA-256-bound V1-V4 same-case provenance contracts that prevent blocked or contract-only rows from masquerading as live results.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-11T16:22:11+08:00
- **Completed:** 2026-08-11T16:37:08+08:00
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added the exact four locked Phase 09 cases and mechanically asserted the complete coverage set: live success, insufficient data, long content, privacy and fallback/failure.
- Made P9-C01 fail closed: it remains `blocked` until `08-07-SUMMARY.md` and `evidence/dify-live/phase8/manifest.json` are present, regular, and SHA-256-valid.
- Bound the four current prompt files to their hashes and added a comparison contract that rejects common-input, accepted-output, source-evidence, prompt-hash, and provenance drift.
- Preserved the established partial-result truth for P9-C04: the audio retry scope is explicit and no unavailable MP3 may be claimed.

## Task Commits

TDD RED and GREEN outcomes were committed separately:

1. **Task 1 RED: case-contract and coverage-matrix tests** - `978f6ba` (test)
2. **Task 1 GREEN: strict four-case registry contracts** - `688e6be` (feat)
3. **Task 2 RED: same-case prompt provenance tests** - `639ab60` (test)
4. **Task 2 GREEN: immutable V1-V4 comparison contracts** - `73e1187` (feat)

## Files Created/Modified

- `evaluation/phase9/cases.json` - Versioned four-row registry with current source hashes, terminal state, availability, privacy and limitation fields.
- `evaluation/phase9/prompt-criteria.json` - Current V1-V4 file hashes, objectives, adoption rationales and limitations without fabricated provider results.
- `src/debugmate/evaluation/contracts.py` - Strict evaluation paths, case/source contracts, Phase 10 source seam and prompt comparison/provenance models.
- `tests/evaluation/test_contracts.py` and `tests/evaluation/test_case_matrix.py` - Adversarial path, hash, coverage, live-gate and terminal-availability coverage.
- `tests/evaluation/test_prompt_comparison.py` - Exact same-input and source/provenance drift coverage.

## Decisions Made

- Kept P9-C01 as a blocked registry row instead of supplying synthetic Phase 08 output hashes. The missing formal Phase 08 artifacts are an explicit collection gate, not evidence of a live pass.
- Reused the existing `ResultManifest` audio-partial semantics rather than creating a second, incompatible media-state vocabulary.
- Used the repository's actual V2/V3 prompt filenames (`v2-citations.md`, `v3-reliability.md`) after confirming the names in `prompts/README.md` and their current hashes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected P9-C04 availability assertions to the established result contract**
- **Found during:** Task 1 GREEN verification
- **Issue:** The initial RED test used evaluation-only `card_png`/`recap_mp3` names that did not match the existing `ArtifactAvailability` model, and incorrectly implied MP3 availability for the audio-partial state.
- **Fix:** Aligned tests and the registry with `report`, `card`, `recap_text`, `audio` and `bundle`; audio remains unavailable and retryable only at the audio stage.
- **Files modified:** `tests/evaluation/test_case_matrix.py`, `src/debugmate/evaluation/contracts.py`, `evaluation/phase9/cases.json`
- **Verification:** 13 focused Task 1 tests passed; Ruff passed.
- **Committed in:** `688e6be`

**2. [Rule 1 - Bug] Rejected forbidden path markers with filename extensions**
- **Found during:** Task 1 GREEN verification
- **Issue:** `approval.json` was not rejected because the first path rule compared complete path components only.
- **Fix:** Applied forbidden-marker matching to each normalized path component while retaining root and traversal confinement.
- **Files modified:** `src/debugmate/evaluation/contracts.py`
- **Verification:** Unsafe approval-path regression test passed; Task 1 suite passed.
- **Committed in:** `688e6be`

**3. [Rule 1 - Bug] Accepted decoded JSON list and enum wire values at the comparison boundary**
- **Found during:** Task 2 GREEN verification
- **Issue:** A decoded JSON comparison payload could not instantiate the strict model because its row collection and enum wire values were rejected before semantic validation.
- **Fix:** Kept bounded ordering and enum validation while accepting standard JSON list/string wire values at this explicit data boundary.
- **Files modified:** `src/debugmate/evaluation/contracts.py`
- **Verification:** 13 focused Task 2 tests passed; Ruff passed.
- **Committed in:** `73e1187`

**4. [Rule 3 - Blocking] Bound criteria to the current V2/V3 prompt filenames**
- **Found during:** Task 2 source inspection
- **Issue:** The plan's `v2-evidence-discipline.md` and `v3-decision-boundaries.md` references do not exist in the repository.
- **Fix:** Used the current, README-declared `v2-citations.md` and `v3-reliability.md` files and their SHA-256 values.
- **Files modified:** `evaluation/phase9/prompt-criteria.json`, `tests/evaluation/test_prompt_comparison.py`, `src/debugmate/evaluation/contracts.py`
- **Verification:** Criteria hash and exact-lineage tests passed.
- **Committed in:** `73e1187`

---

**Total deviations:** 4 auto-fixed (3 Rule 1 bugs, 1 Rule 3 blocking path mismatch).
**Impact on plan:** All changes preserve the planned contract and truth boundaries; no cloud call, Phase 08 evidence publication, Phase 10 media generation, or frozen final asset modification occurred.

## Issues Encountered

- The formal Phase 08 acceptance summary and live manifest are still absent. This plan intentionally records P9-C01 as `blocked`; it does not attempt a live call or claim an offline substitute is a live pass.

## User Setup Required

None - this plan is fully offline and did not read credentials, call Dify, or require provider configuration.

## Known Stubs

None. The blocked P9-C01 row is an intentional, validated terminal state that prevents a false live claim; it is not an unwired display placeholder.

## Next Phase Readiness

- Plan 09-02 can consume the strict case and prompt contracts to validate eligible source evidence and deterministic report projections.
- Plan 09-03 remains hard-gated by a completed, checksum-valid Phase 08 formal evidence bundle before it may promote a live evaluation ledger.
- Phase 10 media, PPTX, video, SRT and final screenshots remain untouched.

## Self-Check: PASSED

- All seven planned registry, contract, test and summary files exist.
- All four TDD task commits resolve in Git history.
- The frozen Phase 10 path gate reports no changed or newly introduced media, PPTX, MP4 or SRT target.

---
*Phase: 09-current-evaluation-evidence*
*Completed: 2026-08-11*
