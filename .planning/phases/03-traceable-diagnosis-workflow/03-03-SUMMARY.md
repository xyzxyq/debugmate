---
phase: 03-traceable-diagnosis-workflow
plan: 03
subsystem: diagnosis-policy
tags: [pydantic, deterministic-routing, sufficiency, retrieval-evidence, tdd]
requires:
  - phase: 03-traceable-diagnosis-workflow
    plan: 01
    provides: DiagnosisRecord v1.1 fact, evidence and support graph contracts
  - phase: 03-traceable-diagnosis-workflow
    plan: 02
    provides: immutable CaseFacts revisions with stable fact IDs
  - phase: 02-knowledge-input-safety
    plan: 03
    provides: trusted knowledge build identity and strict RetrievalTrace
provides:
  - deterministic provisional and final routing across six categories plus unknown
  - category-aware finite sufficiency policy with at most three questions and one round
  - strict RetrievalTrace binding to stable summary-only evidence anchors and support links
affects: [03-04-generation-repair, 03-05-workflow, 03-06-evidence, phase-4-results]
tech-stack:
  added: []
  patterns: [pure-local-policy, deterministic-hash-id, strict-public-revalidation, red-green-tdd]
key-files:
  created:
    - src/debugmate/diagnosis/routing.py
    - src/debugmate/diagnosis/sufficiency.py
    - src/debugmate/diagnosis/evidence_binding.py
    - tests/diagnosis/test_router.py
    - tests/diagnosis/test_sufficiency.py
    - tests/diagnosis/test_evidence_binding.py
  modified: []
key-decisions:
  - "Conflicting strong local rules, low scores and no match all fail closed to unknown; model categories remain recorded but untrusted."
  - "Sufficiency accepts only a validated provisional route and issued field questions; accepted answers create a new facts revision before final routing."
  - "Evidence IDs are derived only from build, chunk, source and locator after exact manifest validation; retrieval summaries stay inert data."
patterns-established:
  - "Routing stage order: provisional route -> category matrix -> immutable answer revision -> final route."
  - "Grounded support requires exact existing fact and evidence IDs; unsupported candidates remain explicit inference with applicability and limits."
requirements-completed: [INP-03, DIAG-01, DIAG-03, DIAG-04]
duration: 12m
completed: 2026-07-12
---

# Phase 3 Plan 03: Deterministic Routing, Sufficiency and Evidence Binding Summary

**Confirmed facts now route reproducibly through a bounded information policy, while only exact build-validated retrieval hits can support grounded causes.**

## Performance

- **Duration:** 12m
- **Started:** 2026-07-12T14:20:33+08:00
- **Completed:** 2026-07-12T14:32:55+08:00
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Added a versioned deterministic router with provisional/final stages, six course categories, unknown fallback, ordered rule candidates, exact fact IDs, conflict handling and inert model suggestions.
- Added per-category sufficiency matrices with deterministic priority ordering, stable field questions, a three-question cap, one follow-up round and explicit insufficient-information termination.
- Added strict case/build/source/URL/locator validation before stable summary-only evidence creation, plus exact grounded/inference support-graph validation.
- Verified prompt-like fact and retrieval text cannot change route authority, retry budget, facts or command behavior.

## Task Commits

Each TDD task was committed as a failing contract followed by its minimal implementation:

1. **Task 1 RED: deterministic router contracts** - `4909557` (test)
2. **Task 1 GREEN: provisional/final router** - `87ed891` (feat)
3. **Task 2 RED: bounded sufficiency contracts** - `ec3f1be` (test)
4. **Task 2 GREEN: category-aware sufficiency policy** - `0df8d5c` (feat)
5. **Task 3 RED: trusted evidence-binding contracts** - `cdaab9d` (test)
6. **Task 3 GREEN: evidence anchors and support graph** - `b3a4ce9` (feat)

## Files Created/Modified

- `src/debugmate/diagnosis/routing.py` - Versioned pure router with threshold, conflict and unknown behavior.
- `src/debugmate/diagnosis/sufficiency.py` - Finite category matrices, stable questions and answer-to-final-route revision seam.
- `src/debugmate/diagnosis/evidence_binding.py` - Strict RetrievalTrace conversion and exact support-graph builder.
- `tests/diagnosis/test_router.py` - Six-category, unknown, conflict, threshold, injection and determinism coverage.
- `tests/diagnosis/test_sufficiency.py` - Category matrices, caps, ranking, suppression, insufficiency and revision coverage.
- `tests/diagnosis/test_evidence_binding.py` - Trusted build, forged anchor, summary-only and grounded/inference coverage.
- `.planning/phases/03-traceable-diagnosis-workflow/03-03-SUMMARY.md` - Execution record and downstream handoff.

## Decisions Made

- A single strong local rule may route, but multiple strong categories always return `unknown`; an optional model category has no authority.
- High-value questions use the required tuple order: route impact, root-cause impact, safe-check impact, then stable field ID.
- Round one becomes `insufficient_information` only when critical fields remain; missing noncritical context does not fabricate a diagnosis blocker.
- Public retrieval input is strictly reconstructed before manifest validation so forged extras, duplicate hits and bypassed Pydantic copies fail closed.

## Deviations from Plan

None - the plan was executed with the specified pure/local boundaries and strict RED-to-GREEN task order.

## Issues Encountered

- The initial sufficiency ranking assertion placed device before version, contradicting the plan's exact root-cause-before-safe-check tuple. The test expectation was corrected before GREEN; production priority follows the plan.

## Verification

- Focused router, sufficiency and evidence-binding tests: `33 passed`
- Complete diagnosis suite: `101 passed, 2 deselected`
- Full offline suite: `382 passed, 21 deselected`
- Full repository Ruff: passed
- `pip check`: no broken requirements
- Required symbols, prohibited capability scan and `git diff --check`: passed

## User Setup Required

None - all policies and acceptance tests are local and offline.

## Next Phase Readiness

- Plan 03-04 can consume final routing decisions and validated evidence anchors for candidate generation and one-repair validation.
- Plan 03-05 can orchestrate provisional route, bounded follow-up, immutable answer revision and final route without adding policy logic to cloud adapters.
- No unresolved offline blocker remains. The pre-existing `.planning/config.json` modification remains untouched and uncommitted.

---
*Phase: 03-traceable-diagnosis-workflow*
*Completed: 2026-07-12*
