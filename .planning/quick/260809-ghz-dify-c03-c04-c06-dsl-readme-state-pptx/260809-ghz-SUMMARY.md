---
phase: quick-260809-ghz-dify-c03-c04-c06-dsl-readme-state-pptx
plan: "01"
subsystem: platform-evidence
tags: [dify, vision, knowledge-retrieval, dsl, evidence, pydantic]
requires:
  - phase: quick-260809-fob-dify-c01-c07-readme-pptx
    provides: C01/C02/C05/C07 Git-tracked live evidence baseline
provides:
  - Strict C03/C04/C06 evidence validators and deterministic DSL structural comparison
  - Git-tracked real Dify C03 vision and C04 direct retrieval-node evidence
  - Accurate C06 blocked record after exhausted console import attempts
affects: [capability-matrix, platform-readme, project-state]
tech-stack:
  added: []
  patterns: [allowlisted cloud evidence, exact SHA-256 publication gate, independent capability truth]
key-files:
  created:
    - src/debugmate/dify_live_evidence.py
    - scripts/capture_dify_c03_c04_c06.ps1
    - evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json
    - evidence/dify-live/2026-08-09/c03-c04/retriever-resource.json
    - evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
  modified:
    - platform/dify/capability-matrix.json
    - platform/dify/README.md
    - README.md
    - .planning/STATE.md
key-decisions:
  - "C03 passes only from target-free non-image inputs plus exact single-fact or adjacent ordered exact VLM coverage."
  - "C04 uses the Knowledge Retrieval node-execution response as primary evidence; diagnosis.evidence is never substituted."
  - "C06 remains blocked because no independent import, re-export, structural comparison, and reconstructed-app rerun completed."
patterns-established:
  - "Candidate validation checks content/hash/path/secrets before commit; publication validation additionally requires Git tracking."
  - "Cloud identifiers that are not source/chunk metadata are stored only as SHA-256 fingerprints."
requirements-completed: []
duration: 30min
completed: 2026-08-09
---

# Quick 260809-ghz: Dify C03/C04/C06 Evidence Summary

**Real Dify image extraction and direct knowledge-retrieval evidence promoted C03/C04 to pass, while C06 remains an evidence-backed permission blocker.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-08-09T04:14:43Z
- **Completed:** 2026-08-09T04:44:00Z
- **Tasks:** 3
- **Files modified:** 15 committed files plus uncommitted SUMMARY/STATE orchestration files

## Capability Results

| Capability | Final status | Evidence | SHA-256 / key result |
|---|---|---|---|
| C01 | `pass` | Existing `dify-upload.json` | `608ebdbd5990f3e09f6cafd1682ff25441057768e1c59506e611531831b3cab1` unchanged |
| C02 | `pass` | Existing `dify-upload.json` | `608ebdbd5990f3e09f6cafd1682ff25441057768e1c59506e611531831b3cab1` unchanged |
| C03 | `pass` | `evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json` | `5be859005686b254a7432d3dba3ce93af760be3636db3f3529346bf82d5e9384`; real PNG upload and exact `source_kind=vlm` target extraction |
| C04 | `pass` | Same capability record plus `retriever-resource.json` | Resource SHA-256 `aae5be8d982b33adf99a572d1cca0a2b7f364eb0a03d369344c5094f524f4592`; direct Knowledge Retrieval node execution returned one non-empty chunk with source metadata |
| C05 | `pass` | Existing `diagnosis.json` | `75b2d9a8c2b555418173410592222e8d504fcc7530779ccbae652770658d0d26` unchanged |
| C06 | `blocked` | `evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json` | `2a038c534eb9b021161ccfff636f8af631cae082b6e36178c044a12ad98f50ca`; no re-export or reconstructed-app rerun created |
| C07 | `pass` | Existing `dify-recap.mp3` | `a7d7821743b4364e1278b650b80e3d869ce2d06621a0745a4eb5fd45bca02328` unchanged |

## Accomplishments

- Added strict Pydantic models, recursive target/prebuilt-fact rejection, secret scanning, deterministic PNG generation, live Workflow capture, and two-stage evidence validation.
- Captured a real Dify Workflow run whose non-image inputs are target-free and whose VLM output exactly matches `ModuleNotFoundError: No module named 'debugmate_demo_pkg'`.
- Captured the matching Dify console node-execution response for Knowledge Retrieval and retained only auditable chunk/source metadata.
- Parsed and compared Dify DSL structures while ignoring display-only identifiers/layout and retaining model, vision, retrieval, start/end, and topology contracts.
- Updated capability matrix and README truth without touching the current DSL, product UI, course media, or planning sources.

## Task Commits

1. **Task 1 RED: live evidence contracts** - `1b774fc`
2. **Task 1 GREEN: validators, DSL comparison, capture wrapper** - `ecd0c02`
3. **Task 2 correctness adjustment: exact ordered VLM coverage** - `16baf89`
4. **Task 2 evidence publication** - `14a6ebe`
5. **Task 3 RED: published matrix truth** - `a5f6bf0`
6. **Task 3 GREEN: matrix/docs/strict blocked contract** - `90f4042`
7. **Verifier fix: bind C04 outer evidence to retriever resource SHA-256** - `e3b9ed9`

## Files Created/Modified

- `src/debugmate/dify_live_evidence.py` - Strict evidence contracts, capture CLI, publication gate, and DSL normalization.
- `scripts/capture_dify_c03_c04_c06.ps1` - Repository-bounded staging wrapper using the verified phase-1 interpreter.
- `tests/platform/test_dify_live_evidence.py` - Spoofing, target injection, direct retrieval, secret, published matrix, and SHA tests.
- `tests/platform/test_dify_dsl.py` - DSL semantic normalization and C06 pass-gate tests.
- `tests/test_probe_cli.py` - Strictly enumerated `pass|not-tested|blocked` matrix contract; blocked requires a tracked safe reason record.
- `evidence/dify-live/2026-08-09/c03-c04/` - Real PNG/request/Workflow/retriever allowlist evidence.
- `evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json` - Accurate blocked attempt record.
- `platform/dify/capability-matrix.json`, `platform/dify/README.md`, `README.md` - Synchronized seven-capability truth.
- `.planning/STATE.md` - Synchronized state left uncommitted for root orchestration.

## Decisions Made

- Accepted C03 multi-fact evidence only when adjacent ordered facts join with canonical punctuation to the exact target; the final successful run produced a stronger single exact fact.
- Used the console node-executions response to prove C04 because the public blocking Workflow response omitted `retriever_resources`.
- Stopped C06 after the UI file chooser was permission-blocked and the authenticated-page import request returned 401; acquiring or persisting session tokens would violate the plan's privacy boundary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used the verified phase-1 Python interpreter**
- **Found during:** Task 1 RED
- **Issue:** The plan's root `.venv` interpreter did not exist; an accidental installation attempt was stopped on correction.
- **Fix:** Used `.worktrees/phase-1-foundation-platform-gate/.venv/Scripts/python.exe` with the current repository `src` on `PYTHONPATH`; the accidental root `.venv` remained ignored and untouched afterward.
- **Verification:** All focused tests and Ruff commands ran through the verified interpreter.
- **Committed in:** No repository files from the environment correction.

**2. [Rule 1 - Bug] Allowed exact ordered multi-fact VLM coverage**
- **Found during:** Task 2 C03 live capture
- **Issue:** One successful Workflow run split the exception type and exact message into adjacent `source_kind=vlm` facts.
- **Fix:** Added a narrow adjacent-order exact-join contract and negative tests for unrelated/reversed fragments; a later run returned the full target as one exact fact.
- **Files modified:** `src/debugmate/dify_live_evidence.py`, `tests/platform/test_dify_live_evidence.py`
- **Verification:** 21 focused contract tests passed.
- **Committed in:** `16baf89`

**3. [Rule 3 - Blocking] Extended the existing matrix test for a real blocked state**
- **Found during:** Task 3
- **Issue:** The pre-existing probe test accepted only `pass` and `not-tested`, conflicting with the plan's requirement to record an attempted C06 permission blocker.
- **Fix:** With root authorization, strictly enumerated `pass|not-tested|blocked` and required a tracked, hashed, secret-free blocker record.
- **Files modified:** `tests/test_probe_cli.py`
- **Verification:** Aggregate suite passed 42 tests.
- **Committed in:** `90f4042`

**4. [Rule 1 - Bug] Bound C04 publication to the exact retrieval resource bytes**
- **Found during:** Post-plan verification
- **Issue:** The outer C04 record named `retriever-resource.json` but did not bind its bytes, so a structurally valid replacement could retain the pass claim.
- **Fix:** Added the exact resource SHA-256 to the strict schema and real evidence; candidate validation recomputes it, while publication also requires a safely resolved Git-tracked, non-ignored regular file.
- **Files modified:** `src/debugmate/dify_live_evidence.py`, `tests/platform/test_dify_live_evidence.py`, C03/C04 outer evidence, capability matrix.
- **Verification:** Replacement regression passed; published validation returned C03/C04 pass and C06 blocked; 43 focused tests and Ruff passed.
- **Committed in:** `e3b9ed9`

---

**Total deviations:** 4 auto-fixed (2 bugs, 2 blocking issues)
**Impact on plan:** All fixes tightened correctness and evidence truth; no product or course-delivery scope was added.

## Issues Encountered

- C06 could not satisfy its pass gate. The console session was authenticated and app creation UI was visible, but local DSL selection was denied by browser-extension file permissions; the safe same-page import API attempt returned 401. No cookie, CSRF token, authorization header, API key, HAR, or personal path was captured.
- The first live C03 run returned split VLM facts; the second real upload/run returned the exact target in a single `source_kind=vlm` fact.

## Known Stubs

None. C06 fields are intentionally null in a `blocked` evidence record and do not represent an implemented or claimed pass path.

## User Setup Required

None for the completed C03/C04 evidence. C06 can only be re-attempted when an authorized console import channel is available; no paid plan or new credential is requested by this quick task.

## Next Phase Readiness

- C03/C04 publication gates and matrix truth are complete and reproducible.
- C06 remains the sole Dify capability blocker and must not be promoted until independent import, re-export, structural equality, and reconstructed-app rerun all succeed.
- PPTX, MP4, SRT, video, subtitles, final screenshots, product UI, `platform/dify/app.dsl.yml`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, and `.planning/ROADMAP.md were not modified.

## Self-Check: PASSED

All key artifacts and seven task/fix commits exist. Published validation, 43 focused/aggregate tests, Ruff, secret scanning, baseline committed-path allowlist, current worktree allowlist, and frozen-path checks passed.

---
*Quick: 260809-ghz*
*Completed: 2026-08-09*
