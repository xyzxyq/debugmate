---
phase: 03-traceable-diagnosis-workflow
plan: 02
subsystem: diagnosis-extraction
tags: [pydantic, ocr, vlm, provenance, immutable-revisions]
requires:
  - phase: 03-01
    provides: stable diagnosis fact identifiers, strict contracts, and fail-closed export safety
provides:
  - approved-input-only text, OCR, and optional VLM candidate extraction with stable provenance
  - local normalization, locator validation, privacy rescan, and immutable CaseFacts snapshots
  - optimistic-lock correction overlays that create auditable revision lineage
affects: [03-03-routing, 03-05-workflow-rerun, phase-4-results]
tech-stack:
  added: []
  patterns: [candidate-only-external-providers, hash-bound-image-locators, immutable-correction-overlay]
key-files:
  created:
    - src/debugmate/diagnosis/extraction.py
    - src/debugmate/diagnosis/providers.py
    - src/debugmate/diagnosis/correction.py
    - tests/fixtures/diagnosis/extraction_candidates.json
    - tests/diagnosis/test_extraction_providers.py
    - tests/diagnosis/test_extraction_correction.py
    - tests/diagnosis/test_ocr_extraction_smoke.py
    - tests/diagnosis/test_vlm_extraction_cloud.py
  modified: []
key-decisions:
  - "Production extraction owns approved screenshot resolution, SHA-256 verification, OCR invocation, and optional VLM invocation; callers receive candidates only."
  - "Candidate and fact identities derive from canonical redacted values and validated locators rather than list positions or random identifiers."
  - "Corrections use case, revision, facts-hash, fact-ID, field-ID, and old-value-hash locks before creating revision+1."
patterns-established:
  - "OCR and VLM confidence remains extraction confidence and never becomes diagnosis confidence."
  - "User corrections preserve the original immutable CaseFacts bytes and record only stable IDs plus before/after hashes in provenance."
requirements-completed: [INP-02, DIAG-06]
duration: 4h 4m
completed: 2026-07-12
---

# Phase 3 Plan 02: Extraction, Normalization and Correction Replay Summary

**Approved redacted text and screenshots now produce hash-bound candidate provenance and privacy-validated immutable facts, with optimistic-lock corrections creating deterministic revision lineage.**

## Performance

- **Duration:** 4h 4m (including executor handoff)
- **Started:** 2026-07-12T10:14:55+08:00
- **Completed:** 2026-07-12T14:18:32+08:00
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added a production extraction chain that accepts only `ApprovedRedactedInput`, safely resolves and rehashes the approved screenshot, invokes injected OCR/VLM ports, and returns deterministic untrusted candidates.
- Added six allowlisted field contracts, discriminated text/OCR/VLM locators, stable candidate/fact hashes, strict normalization, bbox validation, and privacy rescanning before fact promotion.
- Added immutable correction overlays with optimistic locking, stable target IDs, privacy-safe replacement validation, deterministic correction provenance, and exact revision increments.
- Kept real OCR and VLM checks marker-isolated: real OCR passed locally, while live VLM skipped cleanly without credentials.

## Task Commits

TDD and verification fixes were committed atomically:

1. **Task 1 RED: extraction provider contracts** - `66ba8b8` (test)
2. **Task 1 GREEN: approved-input extraction chain** - `387ce7a` (feat)
3. **Task 2 RED: correction revision contracts** - `d53afb4` (test)
4. **Task 2 GREEN: immutable correction revisions** - `82611f9` (feat)
5. **Verification fix: merged live VLM candidate assertion** - `b29ce54` (fix)

## Files Created/Modified

- `src/debugmate/diagnosis/extraction.py` - Strict candidates, locators, deterministic IDs, normalized facts, and immutable snapshots.
- `src/debugmate/diagnosis/providers.py` - Approved-input extraction protocol, production OCR/VLM composition, and narrow live VLM candidate port.
- `src/debugmate/diagnosis/correction.py` - Optimistic-lock correction overlays and deterministic revision creation.
- `tests/fixtures/diagnosis/extraction_candidates.json` - Fictional, redacted six-field extraction fixture.
- `tests/diagnosis/test_extraction_providers.py` - Offline approved path/hash, provenance, VLM isolation, privacy, and failure contracts.
- `tests/diagnosis/test_extraction_correction.py` - Immutable revision, stale lock, stable target, no-op, and privacy rejection tests.
- `tests/diagnosis/test_ocr_extraction_smoke.py` - Marker-isolated real RapidOCR path through the production provider.
- `tests/diagnosis/test_vlm_extraction_cloud.py` - Credential-gated live VLM candidate-only smoke path.

## Verification

- Focused extraction/provenance/normalization/privacy tests: `13 passed`
- Correction tests: `7 passed`
- Diagnosis suite: `68 passed, 2 deselected`
- Full offline suite: `349 passed, 21 deselected`
- Explicit real OCR marker: `1 passed`
- Explicit live VLM marker: `1 skipped` because credentials were not configured
- Full repository Ruff: passed
- `pip check`: no broken requirements
- Acceptance contract introspection, prohibited capability scan, fictional fixture secret scan, and `git diff --check`: passed

## Decisions Made

- VLM output remains an optional, explicitly configured candidate source; it cannot manufacture image geometry, facts, workflow routing, or executable instructions.
- Stable IDs and hashes include normalized redacted values and validated provenance, so repeated runs are deterministic without index- or UUID-based identity.
- Corrections never overwrite a fact snapshot and never preserve raw replacement text outside the newly validated fact; provenance stores hashes instead.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Live VLM smoke rejected valid merged text candidates**

- **Found during:** Final acceptance review after Task 2
- **Issue:** The live smoke input includes approved error text, but its assertion required every merged candidate to be VLM-sourced. A correctly configured production chain would therefore fail after legitimately preserving text candidates.
- **Fix:** Assert at least one typed VLM candidate is present while retaining candidate-only output and allowing deterministic text+VLM merging.
- **Files modified:** `tests/diagnosis/test_vlm_extraction_cloud.py`
- **Verification:** Explicit cloud marker skips cleanly without credentials; Ruff and the complete offline suite pass.
- **Committed in:** `b29ce54`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug). **Impact:** The fix corrects external smoke semantics without changing production behavior or expanding scope.

## Issues Encountered

None unresolved. The live VLM external gate remains credential-dependent and non-blocking by design.

## User Setup Required

None - default and required acceptance paths are offline. Live VLM smoke remains optional and requires `DEBUGMATE_VLM_API_KEY` plus `DEBUGMATE_VLM_ENDPOINT` when explicitly selected.

## Next Phase Readiness

- Plan 03-03 can consume immutable `CaseFacts` with stable fact IDs for deterministic sufficiency, routing, and evidence binding.
- Plan 03-05 can use correction revisions as the sole rerun input without mutating prior extraction or evidence.
- No unresolved offline blocker remains.

## Self-Check: PASSED

- All eight required created files exist on disk.
- Five 03-02 task/fix commits are present in Git history.
- The complete offline, lint, dependency, marker-isolation, privacy, and diff gates pass.
- The pre-existing `.planning/config.json` modification remains untouched and uncommitted.

---
*Phase: 03-traceable-diagnosis-workflow*
*Completed: 2026-07-12*
