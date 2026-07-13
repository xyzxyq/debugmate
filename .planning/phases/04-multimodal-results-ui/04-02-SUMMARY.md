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
  - "Citation source_label is the already-verified source_id literal; EvidenceAnchor has no title, so no title is claimed or invented."
patterns-established:
  - "Report, card and recap implementations consume the same sealed PresentationModel and ArtifactIdentity."
  - "Renderer failures cross the boundary only as report_render_failed or citation_render_failed with no exception chain."
requirements-progressed: [MULTI-01, UX-01]
duration: 94m
completed: 2026-07-13
---

# Phase 4 Plan 02: Deterministic Text Results Summary

**A verified Phase 3 diagnosis now has exactly one immutable semantic projection, one fixed Chinese Markdown report and one identity-bound canonical citation export.**

## Performance

- **Duration:** 94m including three independent-review remediation cycles
- **Completed:** 2026-07-13T10:28:26+08:00
- **Tasks:** 3 strict TDD tasks plus one adversarial identity-hardening cycle
- **Focused tests:** 44 passed
- **Full offline suite:** 554 passed, 22 deselected

## Accomplishments

- Added frozen strict presentation records retaining every fact/evidence/candidate/support ID, exact technical literal, command and uncertainty field from one verified `LoadedDiagnosisSource`.
- Revalidated the complete prepared context and current font bytes, then bound report/card/recap versions and font SHA-256 into one `ArtifactIdentity` with no timestamp or machine path.
- Added a canonical projection seal plus a locked weak-reference instance registry; only the exact live object returned by `build_presentation` can render, while copies, constructs and private-state rewrites fail.
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
9. **Public re-signing RED/GREEN** — `bd9611b` / `853c045`: a caller could previously recompute the public seal and call public revalidation; the public authorities were removed.
10. **Honest source-label RED/GREEN** — `bdacd99` / `2b55fb2`: the absent `official_title` field failed first; citations now export the verified `source_id` under `source_label` and claim no title.
11. **Grounded support-edge RED/GREEN** — `b9cb91c` / `4e53826`: an inference with no support link previously appeared in `supported_candidate_ids`; only a grounded candidate joined through a complete fact/evidence support edge is now emitted.
12. **Copied private-state RED/GREEN** — `72249d9` / `85d133f`: copying private authority and rewriting its fingerprint reproduced acceptance; renderers now require the exact weak-registered build instance.
13. **Partial/cross-spliced graph RED/GREEN** — `054b036` / `6e46953`: partial-fact and cross-spliced graphs failed first; partial-fact, partial-evidence and cross-spliced variants now all reject unless one support edge exactly equals both candidate ID sets.
14. **Registry lifecycle evidence** — `eec969d`: 32 concurrent renders are byte-identical and the weak registry does not keep an otherwise unreachable presentation alive.
15. **In-place mutation RED/GREEN** — `24490ee` / `1c01c0d`: limitations, inferred causes and command ordering could be changed on the registered object with `object.__setattr__` and a recomputed seal; the registry now retains the immutable original seal snapshot.
16. **Duplicate exact-edge RED/GREEN** — `aa41fd1` / `3a66a08`: two identical complete edges previously passed; every grounded candidate now requires exactly one match.

## Verification Gates

- `python -m pytest -q tests/results/test_presentation.py tests/results/test_report.py` — **44 passed**.
- `python -m pytest -q` — **554 passed, 22 deselected**.
- `python -m ruff check .` — **passed**.
- `python -m pip check` — **no broken requirements**.
- `git diff --check HEAD~6..HEAD` — **passed**.
- Renderer dependency grep for provider, network, subprocess and filesystem calls — **no matches**.
- Production/plan grep for `seal_for`, `revalidate_presentation` and `official_title` — **no matches**; only negative assertions and adversarial test helpers retain those strings.

## Deviations from Plan

### Auto-fixed Issue

**[Rule 2 - Missing critical safety] A frozen Pydantic instance could still be copied with an unvalidated identity or semantic update.**

- **Found during:** post-Task-3 adversarial review.
- **Risk:** report and citation artifacts could share each other's forged identity while no longer representing the original presenter output.
- **Fix:** added `projection_sha256`, canonical whole-model verification and build-only construction authorization; the later registry remediation below closes copyable capability state.
- **Evidence:** both forged identity and forged content failed in RED, then both report and citation renderers rejected them after GREEN.

### Independent Review Remediation

**1. [Important] Public projection re-signing was still possible.**

- **Verified issue:** `seal_for` plus `revalidate_presentation` allowed a caller to change a projection, recompute the seal and obtain renderer acceptance.
- **Fix:** removed both public authorities. This was subsequently strengthened to exact instance registration after review proved private attributes remained copyable.
- **Evidence:** a caller-resealed `model_copy` fails in both report and citation renderers, while an unchanged build result remains accepted.

**2. [Important] `source_id` was mislabeled as an official title.**

- **Verified issue:** Phase 3 `EvidenceAnchor` contains no verified title or version-range field.
- **Fix:** renamed the exported field to `source_label`, preserving the exact verified `source_id`; updated the authoritative plan contract and tests. No lookup or invented title was added.

**3. [Important] Inferred candidates were overstated as citation-supported.**

- **Verified issue:** candidate support was derived from `candidate.evidence_ids` alone.
- **Fix:** `supported_candidate_ids` includes only grounded candidates with a complete verified support edge; the second review strengthened this from intersection to exact fact/evidence set equality.

### Second Independent Review Remediation

**1. [Important] Private Pydantic attributes remained copyable capability state.**

- **Verified issue:** `model_copy`, a recomputed public hash and direct `__pydantic_private__` fingerprint replacement could still forge renderer acceptance.
- **Fix:** replaced copyable authority fields with a module-internal `id -> weakref` registry protected by `RLock`. Registration occurs only for the exact object returned by `build_presentation`; validation checks `reference() is value`, preventing copied objects and object-ID reuse confusion.
- **Lifecycle:** weakref callbacks remove only the matching reference, so dead objects do not leak and a later reused ID cannot inherit authority. Concurrent render validation is lock-protected.
- **Evidence:** the exact private-state attack now fails; 32 concurrent renders agree; deleting the final strong reference clears the weak reference.

**2. [Important] Fact/evidence intersection was not a complete grounded graph.**

- **Verified issue:** a candidate could join one fact to both evidence IDs or cross-splice two partial links and still appear fully supported.
- **Fix:** one support link must have fact-ID and evidence-ID sets exactly equal to the grounded candidate's complete sets. Candidate IDs are emitted only after this validation.
- **Evidence:** partial-fact, partial-evidence and cross-spliced verified-source fixtures all reject; an exact complete edge succeeds.

**Test authenticity:** renderer variants now rebuild through a cloned, integrity-updated source bundle, `load_verified_outcome`, prepared context and `build_presentation`. Tests contain no helper or registry call that grants production authenticity to a forged projection.

### Third Independent Review Remediation

**1. [Important] The registered object itself could be changed in place.**

- **Verified issue:** Python's `object.__setattr__` can bypass Pydantic frozen enforcement. Changing limitations, root causes or commands on the exact registered object and recomputing `projection_sha256` passed the weakref-only registry.
- **Fix:** each registry entry now stores `(weakref, original_projection_sha256)`. Validation requires the exact instance, registry snapshot equal to object seal, and object seal equal to a fresh current-payload hash.
- **Lifecycle invariants retained:** the callback compares the stored weakref before removal, the identity check prevents ID-reuse authority, the registry retains no strong model reference, and every access remains under `RLock`.

**2. [Minor] Duplicate identical complete support edges were ambiguous.**

- **Verified issue:** `any(exact_match)` treated two identical complete edges as valid.
- **Fix:** exact matches are counted and must equal one. Zero, duplicate, partial and cross-spliced support graphs all reject before citation export.

## Remaining Scope

- PNG card rendering, recap/TTS, publication bundles and Gradio UI intentionally remain in Plans 04-03 through 04-07.
- No cloud, TTS, browser or OCR gate is needed for this deterministic textual plan; those explicit gates remain isolated by their Phase 4 plans and markers.
