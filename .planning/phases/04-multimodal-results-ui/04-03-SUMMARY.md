---
phase: 04-multimodal-results-ui
plan: 03
subsystem: deterministic-visual-results
tags: [pillow, png, prepared-generation-context, deterministic-layout, partial-results]
requires:
  - phase: 04-multimodal-results-ui
    plan: 02
    provides: sealed exact-instance PresentationModel and prepared generation identity
provides:
  - 1600px measure-before-paint diagnostic card layout
  - prepared-font revalidation without lookup or fallback
  - deterministic metadata-free RGB single-frame PNG candidate
  - typed value-free card partial failure and cleanup
affects: [phase-4-tts, phase-4-publisher, phase-4-ui]
requirements-progressed: [MULTI-02, MULTI-05, UX-04]
completed: 2026-07-13
---

# Phase 4 Plan 03: Deterministic Pillow Card Summary

**The exact sealed PresentationModel now produces one measured, identity-bound and disk-reverified Pillow PNG, or an explicit safe card-only partial failure.**

## Accomplishments

- Added `verify_prepared_font` that revalidates the indivisible `PreparedGenerationContext`, current confined non-link font bytes, generation profile, all renderer contract versions and the exact registered presentation instance.
- Added a deterministic 1600px layout tree with fixed title and identity bar, case suffix, source run and generation version, evidence IDs, grounding labels, confidence, fixed section order, token-safe measurement and complete pre-paint bounds validation.
- Added Pillow-only RGB painting followed by pixels-only re-encoding, canonical single `IHDR`/`IDAT`/`IEND` encoding, CRC/order/length checks, compressed-byte and decoded-pixel gates, single-frame/mode/size/metadata checks and a second verification after atomic placement.
- Added typed `png_layout_failed`, `png_render_failed` and `png_verify_failed` failures. They expose only stage/retry scope and keep report, recap text and audio independently eligible.
- Added fail-closed cleanup for layout, paint, temporary-file and final-disk verification failures; no placeholder, crop, font substitution or second image is emitted.

## TDD Evidence and Commits

1. `95f2c74` — RED card contract; collection failed because the card module did not exist.
2. `74ae7b1` — GREEN prepared-font verification and measured layout.
3. `dacf0e4` — RED final-disk cleanup attack reproduced a success-looking target remaining after verification failure.
4. `6cd4a64` — GREEN deterministic clean PNG paint/reopen verification and final-target cleanup.
5. `5292fa3` — locked partial, cleanup, multilingual long-token and resource boundary behavior.
6. `b91e1b1` — separated exact-height and exact-pixel gates and their immediate overflow cases.
7. `82be205` — RED traceability, CRC, duplicate/split/order and pre-decode resource attacks.
8. `4a6b661` — GREEN identity/evidence rendering, canonical chunks, CRC validation and independent resource gates.
9. `c5ae359` — fixed font-hash-qualified geometry golden plus decompression-bomb mapping evidence.

## Verification

- Focused card suite: **15 passed**.
- Full offline suite: **569 passed, 22 deselected**.
- Ruff: **passed**.
- `pip check`: **no broken requirements**.
- `git diff --check ad87b2a`: **passed**.
- Repeated identical rendering is asserted byte-for-byte and by SHA-256; every produced test PNG is reopened from disk and checked as PNG/RGB/one-frame/1600px/empty metadata.

## Deviations from Plan

- The tested project font uses a byte-for-byte copy of the approved Windows Chinese font because the repository intentionally does not vendor a large font binary. Its exact SHA-256 remains part of both generation and layout identity.
- Pillow BASIC layout is selected explicitly. RAQM was not requested because this Windows wheel lacks it and an implicit RAQM-to-basic fallback would violate renderer determinism.

## Independent Review Remediation

- Added the approved visible identity bar and retained evidence IDs/grounding/confidence in the card rather than relying on the downloadable report for traceability.
- Replaced the permissive PNG walk with a canonical three-chunk contract that validates every CRC and rejects duplicate, split, reordered or trailing chunks, including corrupt `IEND`.
- Added a compressed-byte gate before reading, parsed and bounded `IHDR` before decoding, and independently enforced 1600px width, maximum height/pixels and safe decompression-bomb handling instead of trusting caller-provided dimensions.
- Upgraded the structural golden from section-count assertions to a font-SHA-qualified canvas height, title/identity element, every section rectangle and every measured line bound; no machine path is recorded.

## Remaining Scope

- Recap/TTS, result bundle publication and Gradio consumption remain in Plans 04-04 through 04-06.
- Browser visual-quality evidence and final independent verification remain owned by Plan 04-07.
