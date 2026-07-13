---
phase: 04-multimodal-results-ui
plan: 02
subsystem: deterministic-text-results
tags: [presentation-model, markdown, citations, privacy, identity-seal]
requires:
  - phase: 04-multimodal-results-ui
    plan: 01
    provides: verified completed source, ArtifactIdentity and PreparedGenerationContext
provides:
  - one frozen sealed PresentationModel shared by all later renderers
  - fixed nine-section safe Chinese Markdown report with deterministic golden
  - canonical verified HTTPS citation export bound to the report identity
affects: [phase-4-card, phase-4-recap, phase-4-publisher, phase-4-ui]
tech-stack:
  added: []
  patterns: [canonical-projection-seal, fixed-template-rendering, verified-citation-graph]
key-files:
  created:
    - src/debugmate/results/presentation.py
    - src/debugmate/results/report.py
    - tests/results/test_presentation.py
    - tests/results/test_report.py
    - tests/results/golden/module-not-found-report.md
key-decisions:
  - "Renderer inputs are authorized and canonical-sealed projections, not mutable DiagnosisRecord copies or provider payloads."
  - "Only command bodies bypass Markdown escaping; their fence is deterministically longer than every embedded backtick run."
  - "Citation titles are the already-verified source_id literals; no renderer performs title lookup, URL repair or content-summary export."
patterns-established:
  - "Report, card and recap implementations consume the same sealed PresentationModel and ArtifactIdentity."
  - "Renderer failures cross the boundary only as report_render_failed or citation_render_failed with no exception chain."
requirements-progressed: [MULTI-01, UX-01]
duration: 34m
completed: 2026-07-13
---

# Phase 4 Plan 02: Deterministic Text Results Summary

**A verified Phase 3 diagnosis now has exactly one immutable semantic projection, one fixed Chinese Markdown report and one identity-bound canonical citation export.**

## Performance

- **Duration:** 34m
- **Completed:** 2026-07-13T10:28:26+08:00
- **Tasks:** 3 strict TDD tasks plus one adversarial identity-hardening cycle
- **Focused tests:** 32 passed
- **Full offline suite:** 542 passed, 22 deselected

## Accomplishments

- Added frozen strict presentation records retaining every fact/evidence/candidate/support ID, exact technical literal, command and uncertainty field from one verified `LoadedDiagnosisSource`.
- Revalidated the complete prepared context and current font bytes, then bound report/card/recap versions and font SHA-256 into one `ArtifactIdentity` with no timestamp or machine path.
- Added a canonical projection seal and module-private validation authority so direct construction, `model_copy` identity changes and semantic changes fail before any renderer emits bytes.
- Rendered a deterministic UTF-8/LF Chinese report with exactly nine fixed sections, grounded/inference labels, adjacent command safety metadata and dynamically safe command fences.
- Escaped Markdown, HTML, link, image and fence structure while preserving English error/package/version/path literals and command bodies byte-for-byte; unsafe secret/path/instruction content fails closed without echo.
- Exported stable-ID ordered canonical citation JSON containing only verified source metadata and supported fact/candidate IDs; raw chunk bodies, provider text and reasoning are absent.
- Required verified HTTPS URLs without credentials and cross-checked every grounded evidence reference against the retained support graph.

## TDD Evidence and Commits

1. **Presentation RED** — `dd35614`: 2 expected failures, 8 boundary cases already fail-closed.
2. **Presentation GREEN** — `6fa0221`: 10 passed.
3. **Report RED** — `56fcf0a`: 7 expected rendering failures, 4 rejection cases already fail-closed.
4. **Report GREEN** — `afe1ef2`: 11 passed and reviewed golden matched byte-for-byte.
5. **Citation RED** — `630792d`: 1 expected positive-path failure, 8 rejection cases already fail-closed.
6. **Citation GREEN** — `c44ce4f`: 9 citation tests passed.
7. **Projection-forgery RED** — `337c6b1`: missing seal and changed identity/content both reproduced.
8. **Projection-forgery GREEN** — `7dddc01`: 32 combined presentation/report tests passed.

## Verification Gates

- `python -m pytest -q tests/results/test_presentation.py tests/results/test_report.py` — **32 passed**.
- `python -m pytest -q` — **542 passed, 22 deselected**.
- `python -m ruff check .` — **passed**.
- `python -m pip check` — **no broken requirements**.
- `git diff --check HEAD~6..HEAD` — **passed**.
- Renderer dependency grep for provider, network, subprocess and filesystem calls — **no matches**.

## Deviations from Plan

### Auto-fixed Issue

**[Rule 2 - Missing critical safety] A frozen Pydantic instance could still be copied with an unvalidated identity or semantic update.**

- **Found during:** post-Task-3 adversarial review.
- **Risk:** report and citation artifacts could share each other's forged identity while no longer representing the original presenter output.
- **Fix:** added `projection_sha256`, canonical whole-model verification and module-private construction/revalidation authority.
- **Evidence:** both forged identity and forged content failed in RED, then both report and citation renderers rejected them after GREEN.

## Remaining Scope

- PNG card rendering, recap/TTS, publication bundles and Gradio UI intentionally remain in Plans 04-03 through 04-07.
- No cloud, TTS, browser or OCR gate is needed for this deterministic textual plan; those explicit gates remain isolated by their Phase 4 plans and markers.
