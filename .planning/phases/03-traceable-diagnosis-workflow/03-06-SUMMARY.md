---
phase: 03-traceable-diagnosis-workflow
plan: 06
subsystem: diagnosis-evidence
tags: [atomic-publication, manifest-hashes, privacy-scan, immutable-runs, offline-gates]
requires:
  - phase: 03-traceable-diagnosis-workflow
    plan: 05
    provides: approval-gated typed workflow outcomes and immutable correction reruns
provides:
  - run-specific immutable diagnosis evidence directories with atomic publication
  - privacy-scanned allowlisted stage summaries and hash-verifiable manifests
  - correction lineage preserving original and revised evidence bundles
  - blocking offline Schema, secret, test, lint, dependency and diff gates
affects: [phase-4-results, phase-5-evaluation, course-delivery-evidence]
tech-stack:
  added: []
  patterns: [case-run-evidence-lineage, fail-closed-temp-cleanup, summary-only-publication]
key-files:
  created:
    - tests/diagnosis/test_workflow_evidence.py
  modified:
    - src/debugmate/evidence.py
    - src/debugmate/diagnosis/workflow.py
    - src/debugmate/cli.py
    - src/debugmate/privacy/output_scan.py
key-decisions:
  - "Diagnosis evidence is addressed by case_id/run_id so a correction can never overwrite the prior revision."
  - "Extraction and facts evidence retains IDs, hashes, provenance and confidence but omits fact and candidate values."
  - "Only locally validated DiagnosisRecord is publishable; provider bodies, raw candidates, raw chunks, reasoning and Phase 4 media remain excluded."
patterns-established:
  - "Every publication reconstructs strict workflow models, rechecks fact/evidence/diagnosis lineage, privacy-scans each artifact and atomically renames only after manifest creation."
  - "A failed publication removes its run-specific temporary sibling and leaves no normal or partial diagnosis directory."
requirements-completed: [INP-02, INP-03, SAFE-04, DIAG-01, DIAG-02, DIAG-03, DIAG-04, DIAG-05, DIAG-06]
duration: 12m
completed: 2026-07-12
---

# Phase 3 Plan 06: Immutable Diagnosis Evidence and Offline Gates Summary

**Every typed workflow outcome now publishes an atomic, privacy-scanned and hash-verifiable case/run bundle while correction reruns preserve both immutable revisions.**

## Performance

- **Duration:** 12m
- **Started:** 2026-07-12T15:09:00+08:00
- **Completed:** 2026-07-12T15:21:07+08:00
- **Tasks:** 1 TDD task
- **Files modified:** 6

## Accomplishments

- Added run-specific `case_id/run_id` publication with temporary-directory cleanup, duplicate-run refusal and manifest verification of both directory identities.
- Published only the stage-appropriate allowlist: extraction/fact summaries, sufficiency, routing, retrieval anchors, validated diagnosis or typed generation failure, plus the manifest.
- Bound manifests to backend, workflow/prompt/Schema/router versions, case/run identity, facts revision/hash, knowledge build, generation/transport attempts, node states and artifact SHA-256 values.
- Revalidated facts, routing, evidence anchors and the validated diagnosis graph before publication; forged anchors and unsafe output fail before a normal bundle can appear.
- Added strict JSON CLI publication and preserved Phase 2's prohibition on MP3, PNG, report and arbitrary binary output.
- Proved original and corrected runs retain distinct directories, revisions, facts hashes and run identities while both bundles remain independently verifiable.

## Task Commits

1. **RED: immutable workflow evidence contracts** - `5e31d2c` (test)
2. **GREEN: atomic diagnosis evidence publication** - `f3490e9` (feat)

## Files Created/Modified

- `src/debugmate/evidence.py` - Run-specific bundles, lineage validation, stage summaries, manifests and fail-closed cleanup.
- `src/debugmate/diagnosis/workflow.py` - Persisted backend/version/build/attempt metadata and workflow publication seam.
- `src/debugmate/cli.py` - Strict `diagnosis-publish` JSON command.
- `src/debugmate/privacy/output_scan.py` - Exact allowlisting for stable extraction, question, correction and provenance identifiers.
- `tests/diagnosis/test_workflow_evidence.py` - Four outcomes, hashes, privacy, forgery, atomicity, correction and CLI proofs.
- `.planning/phases/03-traceable-diagnosis-workflow/03-06-SUMMARY.md` - Plan completion record.

## Decisions Made

- Run directories are nested below stable case directories because `case_id` remains constant across a correction while `run_id`, revision and facts hash must change.
- Fact and extraction evidence intentionally excludes values; downstream audit uses stable IDs, field kinds, source provenance, confidence, hashes and the separately validated diagnosis contract.
- Completed outcomes may include only the locally validated `DiagnosisRecord`; raw adapter candidates and provider internals are never accepted as evidence artifacts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PowerShell retained clean `git grep` exit code 1 after the documented success branch**

- **Found during:** Final exact automated gate
- **Issue:** The plan correctly treats `git grep` exit 1 as "no match", but the host process still returned the last native exit code after the conditional completed.
- **Fix:** Re-ran the identical tracked-file scan and branch with a terminal `exit 0`; no match was found and all intended secret-scan semantics passed.
- **Files modified:** None; the plan and product configuration were not changed.
- **Verification:** The explicit scan returned 0, while product, contracts, fixtures, knowledge, prompts, platform, scripts, README and pyproject remained in scope.

---

**Total deviations:** 1 auto-fixed (1 blocking shell exit-semantics issue). **Impact:** No acceptance scope or exclusion was weakened.

## Issues Encountered

- The deprecated `python -m jsonschema` CLI emitted its upstream deprecation warning but validated every tracked diagnosis fixture successfully; dependency versions were not changed outside the plan.

## Verification

- Focused workflow evidence/E2E: `31 passed`
- Complete offline suite: `429 passed, 22 deselected`
- Full repository Ruff: passed
- `pip check`: no broken requirements
- Every tracked `fixtures/**/diagnosis.json`: valid against `contracts/diagnosis-record-v1.1.schema.json`
- Tracked product/config/contract/fixture/knowledge/prompt/platform/script secret scan: clean with only planning/tests excluded by path selection
- `git diff --check`: passed; only the pre-existing `.planning/config.json` modification remains outside executor commits

## User Setup Required

None - offline acceptance requires no cloud, OCR or VLM credentials. External marker tests remain optional and explicitly identify their real backend when run.

## Next Phase Readiness

- Phase 4 can consume verified diagnosis bundles without reading provider responses or reconstructing workflow policy.
- Phase 3 is ready for phase verification; no unresolved offline blocker remains.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` and `.planning/config.json` were not edited or committed by this executor.

## Self-Check: PASSED

- RED and GREEN commits are present.
- Required source/test/summary files exist.
- The full offline gate, focused gate, Schema validation and tracked-file secret scan have fresh evidence.
- The sole dirty file remains the orchestrator-owned pre-existing `.planning/config.json`.

---
*Phase: 03-traceable-diagnosis-workflow*
*Completed: 2026-07-12*
