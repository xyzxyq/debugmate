---
phase: 07-real-input-privacy-ui
plan: 02
subsystem: privacy
tags: [pydantic, screenshot-audit, concurrency, revision, one-time-token]

requires:
  - phase: 07-real-input-privacy-ui
    provides: Wave 0 screenshot-audit and revision-race RED contracts from Plan 07-01
provides:
  - Strict value-free screenshot OCR audit bound into every preview hash
  - Revision-aware bounded server authority with atomic publish, consume, invalidate, expiry, and eviction
  - Browser-safe redacted presentation that excludes strict approval objects and filesystem paths
affects: [07-03, 07-04, 07-05, 08-dify-unified-live-chain]

tech-stack:
  added: []
  patterns:
    - Value-free screenshot facts serialized separately from OCR text and box findings
    - Heavy preview work outside the lock followed by lock-atomic revision publication
    - Session, revision, TTL, and one-time token checked in one consume transaction

key-files:
  created: []
  modified:
    - src/debugmate/privacy/models.py
    - src/debugmate/privacy/text_redactor.py
    - src/debugmate/ui/local_live.py
    - tests/privacy/test_models.py
    - tests/ui/test_local_live.py

key-decisions:
  - "Screenshot audit objects retain SecretKind keys in memory while path-like kinds use reversible value-free codes in JSON."
  - "The preview store bounds both session revisions and token records, evicting the oldest session and all of its authorities deterministically."
  - "Publishing replaces any prior token for the same session revision, so one session has only one active approval authority."

patterns-established:
  - "Preview hash binding: canonical payload includes text audit and screenshot audit before SHA-256 calculation."
  - "Revision CAS: snapshot outside expensive work, publish only when current, compare-and-pop once under RLock."

requirements-completed: [INP-01, INP-02, SAFE-01, UX-01]

duration: 13 min
completed: 2026-08-09
---

# Phase 7 Plan 2: Screenshot Audit and Revision Authority Summary

**Strict screenshot audit facts now participate in preview hashes, while a bounded revision-aware store closes stale, cross-session, expired, replay, and duplicate approval races.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-08-09T08:36:26Z
- **Completed:** 2026-08-09T08:48:59Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added frozen `ScreenshotOcrStatus` and `ScreenshotPreviewAudit` contracts for explicit text-only, successful OCR, zero-finding, and sensitive-finding previews without OCR text, boxes, paths, or matched values.
- Bound screenshot audit JSON into the exact canonical payload used for `preview_hash`, preserving deterministic hashes across workspaces and existing approval behavior.
- Replaced fixed demo authority with per-session monotonic revisions, bounded records, TTL checks, deterministic eviction, stale-publication rejection, and lock-atomic one-time consumption.
- Proved change/approve ordering, slow preview rejection, N/N+1 publication, duplicate consumption, cross-session copying, token tampering, expiry, and replay invalidation through direct threaded tests.

## Task Commits

1. **Task 1: Bind value-free screenshot audit into PreviewBundle and preview hash** - `c43024a` (feat; RED contracts inherited from `99f04cc`)
2. **Task 2 RED: Specify revisioned preview authority** - `fc3076a` (test)
3. **Task 2 GREEN: Enforce revisioned preview authority** - `3eb5a96` (feat)

## Files Created/Modified

- `src/debugmate/privacy/models.py` - Defines strict frozen screenshot status/audit contracts and makes the audit mandatory on `PreviewBundle`.
- `src/debugmate/privacy/text_redactor.py` - Creates text-only/completed screenshot audits and includes them in canonical preview hashing.
- `src/debugmate/ui/local_live.py` - Provides bounded revision snapshots, atomic current publication/consumption, invalidation, expiry, and safe presentation.
- `tests/privacy/test_models.py` - Updates strict preview JSON round-trip fixtures for the mandatory screenshot audit.
- `tests/ui/test_local_live.py` - Migrates direct store coverage to the revision API and adds capacity, invalidation, and presentation-disclosure regressions.

## Decisions Made

- Kept screenshot findings separate from text `SecretCandidate` spans; only value-free aggregate counts cross into the preview contract.
- Used reversible `WINDOWS_ABSOLUTE` and `UNIX_ABSOLUTE` JSON audit codes so serialized screenshot summaries contain no path vocabulary while in-memory keys remain exact `SecretKind` values.
- Kept OCR/redaction outside the store lock. `publish_if_current` revalidates the strict preview before entering the short lock transaction.
- Removed `LOCAL_RULE_DEMO_*`, `create()`, and `consume()` rather than retaining a compatibility authority bypass; later Phase 07 assembly plans must call the revision API.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The first GREEN run showed that the `WINDOWS_PATH` enum name itself triggered the value-free serialized-audit guard. A reversible audit-only JSON code fixed the disclosure contract without weakening the RED assertion or changing in-memory category identity.
- The existing strict model round-trip fixture required the newly mandatory screenshot audit; it was intentionally updated rather than adding a permissive production default.

## Known Stubs

None. No placeholder data source or empty browser presentation was introduced.

## Threat Surface

No unplanned endpoint, network path, authentication flow, file access, or schema boundary was added. The planned preview-token authority surface is covered by T-07-RACE, T-07-SESSION, T-07-OCR-AUDIT, and T-07-STORE-DOS mitigations.

## User Setup Required

None - no external service configuration or credentials are required.

## Next Phase Readiness

- Plan 07-03 can assemble real input preparation around `snapshot_revision()` and `publish_if_current()` without holding the lock during OCR.
- Plan 07-04 can consume only `consume_current()` records and replace the old app callback references to removed fixed-demo methods.
- Phase 08 remains frozen; no cloud or Dify path was introduced.

## Self-Check: PASSED

- All five modified implementation/test files and this summary exist.
- Task commits `c43024a`, `fc3076a`, and `3eb5a96` exist in repository history.
- Privacy, direct store/race, Ruff, and the 14-target frozen-scope gate pass.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` were not modified or staged by this executor.

---
*Phase: 07-real-input-privacy-ui*
*Completed: 2026-08-09*
