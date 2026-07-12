---
phase: 03-traceable-diagnosis-workflow
plan: 01
subsystem: diagnosis-contract
tags: [pydantic, json-schema, traceability, migration, command-safety]
requires:
  - phase: 02-knowledge-input-safety
    provides: strict retrieval traces, privacy export scans, and offline fixture boundaries
provides:
  - DiagnosisRecord 1.1.0 with stable fact, evidence, candidate and support-link graph
  - deterministic conservative DiagnosisRecord 1.0.0 to 1.1.0 migration
  - fail-closed inert command recommendation policy for five explicit platforms
affects: [03-02-extraction, 03-03-evidence-binding, 03-04-generation, phase-4-results]
tech-stack:
  added: []
  patterns: [strict-pydantic-graph-validation, canonical-schema-snapshot, conservative-migration]
key-files:
  created:
    - contracts/diagnosis-record-v1.1.schema.json
    - src/debugmate/diagnosis/migrations.py
    - tests/diagnosis/test_contract_v11.py
    - tests/diagnosis/test_command_safety.py
  modified:
    - src/debugmate/contracts.py
    - fixtures/cases/module_not_found/diagnosis.json
    - src/debugmate/privacy/output_scan.py
key-decisions:
  - "Legacy text-only candidates migrate as inference because v1.0 cannot prove citation support relationships."
  - "Stable IDs are canonical SHA-256-derived opaque identifiers and are explicitly recognized by export safety scans."
  - "Command recommendations accept only five explicit platforms and reject unsafe text before a DiagnosisRecord can publish."
patterns-established:
  - "Grounded candidates must reference existing fact and evidence IDs through at least one matching support link."
  - "Committed current Schema is canonical sorted JSON and is byte-compared with Pydantic output."
requirements-completed: [SAFE-04, DIAG-02, DIAG-03, DIAG-04]
duration: 12min
completed: 2026-07-12
---

# Phase 3 Plan 01: Diagnosis Contract Migration and Safety Summary

**DiagnosisRecord 1.1.0 now provides a strict trace graph, conservative legacy migration, and non-executable command recommendations that fail closed on unsafe shell constructs.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-12T09:57:36+08:00
- **Completed:** 2026-07-12T10:09:03+08:00
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- Added stable `ObservedFact`, `EvidenceAnchor`, `SupportLink`, and `RootCauseCandidate` records with duplicate, dangling-link, and grounded-claim validation.
- Preserved the frozen v1.0 loader and Schema while adding a deterministic one-way migration that never invents citation support.
- Added five explicit command platforms, required metadata, deny-pattern validation, and an AST guard proving command-handling code has no shell execution capability.
- Upgraded the module-not-found fixture and retained Phase 2 probe/evidence compatibility under the v1.1 contract.

## Task Commits

TDD and fixes were committed atomically:

1. **Task 1 RED: v1.1 contract and migration tests** - `8043c15` (test)
2. **Task 1 GREEN: v1.1 graph and conservative migration** - `3e3a78c` (feat)
3. **Task 2 RED: command safety policy tests** - `e49c3ce` (test)
4. **Task 2 GREEN: inert command safety enforcement** - `a6fcc8f` (feat)
5. **Verification fix: single-expression fixture command** - `7d9653b` (fix)

## Files Created/Modified

- `src/debugmate/contracts.py` - Current and legacy contracts, graph invariants, platform enum, and command deny policy.
- `src/debugmate/diagnosis/migrations.py` - Pure deterministic v1.0.0 to v1.1.0 migration.
- `contracts/diagnosis-record-v1.1.schema.json` - Canonical current JSON Schema snapshot.
- `fixtures/cases/module_not_found/diagnosis.json` - Traceable v1.1 module-not-found fixture.
- `tests/diagnosis/test_contract_v11.py` - Strict graph, Schema drift, and migration proofs.
- `tests/diagnosis/test_command_safety.py` - Platform, unsafe-pattern, whole-record, and no-execution proofs.
- `src/debugmate/privacy/output_scan.py` - Exact allowlisting for stable trace graph identifier formats.

## Verification

- Focused contracts and command safety: `69 passed`
- Fixture, adapter, probe, and diagnosis compatibility: `83 passed`
- Full offline suite: `336 passed, 19 deselected`
- Full repository Ruff: passed
- `pip check`: no broken requirements
- JSON Schema fixture validation and canonical byte comparison: passed
- Frozen v1.0 Schema diff, secret scan, and `git diff --check`: passed

## Decisions Made

- Legacy citations become unlinked evidence anchors, while legacy root causes become inference; this retains information without fabricating support.
- Current graph identifiers use semantic prefixes plus 128 bits of a canonical SHA-256 digest, avoiding user information and nondeterminism.
- Unsafe command errors expose only a policy rule ID and never echo or execute the command text.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stable trace IDs were rejected by the existing privacy export scan**

- **Found during:** Task 1 compatibility verification
- **Issue:** New `fact_*`, `evidence_*`, and `candidate_*` identifiers matched the high-entropy secret detector, blocking valid evidence bundles.
- **Fix:** Added exact key-and-format allowlisting and preserved metadata keys while recursively scanning list elements.
- **Files modified:** `src/debugmate/privacy/output_scan.py`, `tests/privacy/test_output_scan.py`
- **Verification:** Privacy, evidence, fixture, and probe tests pass in the full offline suite.
- **Committed in:** `3e3a78c`

**2. [Rule 1 - Bug] Fixture Python code contained a semicolon rejected as shell chaining**

- **Found during:** Final full offline verification after Task 2
- **Issue:** A read-only `python -c` example used two statements separated by `;`, conflicting with the required fail-closed policy.
- **Fix:** Rewrote it as an equivalent single Python expression without relaxing the command policy.
- **Files modified:** `fixtures/cases/module_not_found/diagnosis.json`
- **Verification:** Full offline suite passes with 336 tests and Schema validation passes.
- **Committed in:** `7d9653b`

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs). **Impact:** Both fixes preserve existing offline workflows and the stricter security boundary without scope expansion.

## Issues Encountered

None unresolved.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03-02 can build extraction and correction records on stable fact IDs.
- Plan 03-03 can bind trusted retrieval traces to the committed evidence/support graph.
- No external account or cloud gate blocks the next offline plan.

## Self-Check: PASSED

- Required created files exist on disk.
- Five plan commits are present in Git history.
- The only remaining dirty file is the orchestrator-owned pre-existing `.planning/config.json`.

---
*Phase: 03-traceable-diagnosis-workflow*
*Completed: 2026-07-12*
