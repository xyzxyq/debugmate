---
phase: 07-real-input-privacy-ui
plan: 03
subsystem: ui
tags: [rapidocr, privacy, local-only, dependency-injection, sapi]

requires:
  - phase: 07-real-input-privacy-ui
    provides: Strict screenshot audit and revision-aware one-time preview authority from Plan 07-02
provides:
  - One explicit local dependency graph sharing a single lazy RapidOCR backend and absolute redacted root
  - Approved-screenshot SHA-256 and image revalidation before six-field OCR extraction
  - Construction-time local-only live and replay composition with no Dify, Edge, settings, HTTPX or socket adapter path
affects: [07-04, 07-05, 08-dify-unified-live-chain]

tech-stack:
  added: []
  patterns:
    - Explicit immutable dependency graph for preview and approved-input extraction
    - Source-level absence plus constructor poisoning for construction-time network isolation

key-files:
  created: []
  modified:
    - src/debugmate/ui/serve.py
    - tests/diagnosis/test_extraction_providers.py
    - tests/ui/test_local_live.py
    - tests/ui/test_real_input.py

key-decisions:
  - "Phase 07 ordinary live and replay composition always uses a local-only SAPI chain; the replay_local_only compatibility argument can no longer enable a network path."
  - "A frozen LocalAppDependencies object owns the single RapidOcrBackend and absolute redacted root that Plan 07-04 will pass into the real-input callbacks."

patterns-established:
  - "Shared OCR identity: preview construction and ProductionExtractionProvider receive the same lazy RapidOcrBackend instance."
  - "Approved screenshot order: root confinement, file existence, SHA-256 comparison and image validation all precede OCR."

requirements-completed: [INP-01, INP-02, SAFE-01, UX-01]

duration: 31 min
completed: 2026-08-09
---

# Phase 7 Plan 3: Shared OCR and Local-Only Assembly Summary

**One lazy RapidOCR backend and one trusted redacted root now span preview and approved extraction, while both live and replay construct only local SAPI media dependencies.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-08-09T08:42:00Z
- **Completed:** 2026-08-09T09:13:23Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Replaced ordinary `_NoopOcr` assembly with an explicit `LocalAppDependencies` graph that constructs exactly one lazy production `RapidOcrBackend` and one absolute redacted artifact root.
- Bound the same OCR object and root to preview construction and `ProductionExtractionProvider`, with tests proving object identity and preserving all six established correction field IDs.
- Proved an approved screenshot is root-confined, rehashed and image-validated before OCR; post-approval byte changes fail before a second OCR call.
- Removed Dify/Edge/settings imports and the network-capable replay branch from `serve.py`; ordinary live and replay now use `TtsFallbackChain((SapiTtsAdapter(...),), local_only=True)`.
- Preserved QA-only local failure/fallback injection and verified the complete local-live suite, real RapidOCR smoke, focused extraction/construction gates, Ruff and the frozen-media boundary.

## Task Commits

1. **Task 1: Construct one shared RapidOCR and one trusted redacted root** - `41f3502` (feat)
2. **Task 2: Enforce construction-time local-only live and replay composition** - `1b288a4` (feat)

## Files Created/Modified

- `src/debugmate/ui/serve.py` - Explicit shared OCR/root graph and SAPI-only live/replay composition.
- `tests/diagnosis/test_extraction_providers.py` - Six-field approved-screenshot extraction and pre-OCR rehash regression.
- `tests/ui/test_real_input.py` - Shared-backend identity, source absence and construction poison contracts.
- `tests/ui/test_local_live.py` - Network poison test compatible with intentionally absent cloud adapter symbols.

## Decisions Made

- Kept `_local_service()` as a compatibility façade returning the service while `_local_dependencies()` exposes the complete graph for Plan 07-04 UI callback wiring.
- Retained the `replay_local_only` keyword for existing QA callers, but made the default true and removed every branch that could use it to construct a network adapter.
- Kept QA-only unavailable adapters as inert local fakes so historical partial/fallback result semantics remain testable without importing Dify or Edge.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The complete local-live suite includes real SAPI/FFmpeg work and exceeded the terminal's first 30-second yield. The running process was polled to its actual terminal result: `10 passed in 44.31s`.

## Known Stubs

None. No placeholder data source, empty production backend or unconnected media path was introduced.

## User Setup Required

None - no external service, API key or cloud authentication is required.

## Next Phase Readiness

- Plan 07-04 can consume `LocalAppDependencies.build_preview`, `ocr_backend` and `redacted_root` while replacing the obsolete fixed UI callback seam.
- Phase 08 remains frozen; no Dify workflow, Edge fallback or outbound adapter was added.
- Phase 10 media and all Phase 04/course evidence remain unchanged; the 14-target frozen-scope check passes.

## Self-Check: PASSED

- All four modified implementation/test files and this summary exist.
- Task commits `41f3502` and `1b288a4` exist in repository history.
- Focused OCR/extraction: 12 passed; construction poison: 2 passed; RapidOCR smoke: 1 passed; complete local-live: 10 passed; scoped Ruff: passed.
- The frozen-scope validator confirms all 14 tracked targets match the captured baseline.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` were not modified, staged or reverted by this executor.

---
*Phase: 07-real-input-privacy-ui*
*Completed: 2026-08-09*
