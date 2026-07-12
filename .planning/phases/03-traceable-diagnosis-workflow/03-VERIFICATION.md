---
phase: 03-traceable-diagnosis-workflow
verified_at: 2026-07-13
status: passed
score: 25/25
requirements_verified:
  - INP-02
  - INP-03
  - SAFE-04
  - DIAG-01
  - DIAG-02
  - DIAG-03
  - DIAG-04
  - DIAG-05
  - DIAG-06
head: 28f4f47
external_gates:
  ocr: passed
  phase3_cloud: skipped_without_credentials
  repository_cloud_drift: rate_limited
---

# Phase 03 Verification

## Result

**PASSED.** Phase 03 achieves its goal: approved redacted text or screenshot input can be
converted into a strict `DiagnosisRecord 1.1.0` through an approval-first workflow with
deterministic extraction, bounded clarification, six-class routing, trusted retrieval
binding, controlled generation repair, immutable correction reruns, and atomic evidence
publication. All 25 plan truths and all nine mapped requirements are proven by current code,
adversarial tests, committed fixtures, and fresh verifier-run quality gates.

This conclusion does not depend on plan summaries. The verifier inspected the current
contracts, extraction/correction models, routing and sufficiency policies, generator,
workflow, evidence publisher, tests, fixtures, prior verification boundaries, security
audit, review/fix reports, and the post-review gap fix at HEAD `28f4f47`.

## Goal and Roadmap Success Criteria

| Criterion | Result | Current-state evidence |
|---|---|---|
| Screenshot-derived six-field candidates are visible and correctable | Passed | `FactCandidate`, typed text/OCR/VLM locators and `ProductionExtractionProvider` preserve stable candidate/source/locator metadata; `CaseFact` validates canonical field/value IDs; the CLI exposes six explicit slots and stable correction IDs. Real local OCR passed its marker gate. |
| At most three high-value questions, one round, then explicit insufficiency | Passed | `MAX_QUESTIONS = 3`; `evaluate_sufficiency()` is deterministic and returns `needs_information` or `insufficient_information`; workflow order and fixture outcomes are covered by focused tests. |
| Six categories or unknown and a Schema-valid diagnosis object | Passed | `route_case()` emits the six course categories or `unknown`; fixture matrix tests every route; completed output is validated locally as `DiagnosisRecord 1.1.0`; the committed diagnosis fixture validates against the current Schema. |
| Root causes distinguish grounded support from inference and expose uncertainty | Passed | `ObservedFact`, `EvidenceAnchor`, `SupportLink`, and `RootCauseCandidate` form a strict cross-reference graph; exact fact/evidence IDs are mandatory for grounded causes, while inference requires applicability and limitations. |
| One controlled repair, safe failure, inert annotated commands | Passed | `MAX_REPAIR_ATTEMPTS = 1`; a second invalid candidate returns typed `generation_failed` without partial diagnosis; command records require platform, impact, expected result and rollback and reject unsafe constructs; the command-handling code contains no shell execution capability. |

## Requirement Verification

| Requirement | Result | Authoritative evidence |
|---|---|---|
| INP-02 | Passed | Production extraction accepts only `ApprovedRedactedInput`, hash-verifies the approved screenshot, invokes injected OCR and optional VLM candidate ports, and maps exception type, traceback key line, package, version, device and path into typed candidates. Six-slot CLI and tests prove the display boundary. |
| INP-03 | Passed | Category-aware sufficiency asks no more than three unique field questions for one follow-up round and returns explicit `insufficient_information` when critical facts remain absent. |
| SAFE-04 | Passed | `CommandRecommendation` is inert structured data with mandatory platform/impact/expected-result/rollback fields; deny rules reject chaining, substitution, destructive and download-execute forms. AST tests prove no `subprocess`, `os.system`, `exec`, or `eval` path. |
| DIAG-01 | Passed | Deterministic provisional/final routing covers dependency/environment, path/permission, Python runtime, tensor shape/type, CUDA/VRAM, model loading, and `unknown`, including conflict and prompt-injection fallbacks. |
| DIAG-02 | Passed | The local generator is the sole publication authority for strict `DiagnosisRecord 1.1.0`; canonical Pydantic Schema is committed and the tracked diagnosis fixture passes JSON Schema validation. |
| DIAG-03 | Passed | Trusted build/source/URL/locator validation precedes evidence-anchor creation; grounded causes require exact observed-fact and evidence IDs through support links; unsupported content remains inference. |
| DIAG-04 | Passed | The contract contains root-cause candidates, checks, fixes, validation commands, missing information, confidence, limitations, applicability and environment scope, with graph and semantic validators. |
| DIAG-05 | Passed | Candidate validation permits exactly one contract repair; transport and repair counters are independent; second failure produces typed `generation_failed` with no partial `DiagnosisRecord`. |
| DIAG-06 | Passed | Optimistic-lock correction overlays target stable fact/field/hash identities, create a new immutable contiguous revision, preserve source provenance and rerun routing/retrieval/generation without overwriting the source run or bundle. |

## Plan Must-have Audit

| Plan | Truths | Result | Evidence checked |
|---|---:|---|---|
| 03-01 | 4 | 4/4 | v1.1 strict graph, frozen v1.0 loader, deterministic conservative migration, command safety and canonical Schema snapshot. |
| 03-02 | 5 | 5/5 | Candidate-only text/OCR/VLM extraction, approved screenshot hash binding, local normalization/privacy scan, immutable correction revision and marker isolation. |
| 03-03 | 5 | 5/5 | Provisional route before sufficiency, maximum-three/one-round policy, six classes plus unknown, trusted-build retrieval binding and exact grounded/inference separation. |
| 03-04 | 3 | 3/3 | Candidate-only adapters, local strict publisher, exactly one repair, separate transport/repair counts and bounded failure details. |
| 03-05 | 4 | 4/4 | Approval verification before stage/provider calls, zero-call rejection cases, required stage order, seven routes and all bounded/corrected outcomes from fictional fixtures. |
| 03-06 | 4 | 4/4 | Privacy-scanned allowlist bundles, retrieval/support lineage, distinct immutable correction bundles, and blocking offline/schema/secret gates. |

## Fresh Automated Evidence

Executed from `X:\PROJECT\校外实训\.worktrees\phase-1-foundation-platform-gate` at
HEAD `28f4f47`:

```text
python -m pytest -q -m "not cloud and not ocr"
  468 passed, 22 deselected in 7.10s

focused Phase 3 contract/workflow/evidence suite
  268 passed, 3 deselected in 3.08s

python -m ruff check .
  All checks passed!

python -m pip check
  No broken requirements found.

git diff --check
  passed; only the pre-existing .planning/config.json LF/CRLF notice was emitted

tracked fixtures/**/diagnosis.json vs diagnosis-record-v1.1.schema.json
  1/1 valid

tracked product/config/contract/fixture/knowledge/prompt/platform/script secret scan
  clean
```

The focused suite covered strict v1.1 contracts and migration, command safety, extraction
and correction, routing, sufficiency, evidence binding, one-repair generation, workflow
E2E, immutable evidence publication, fixture adapters, CLI presentation, legacy evidence
compatibility, and Schema contracts.

## Security and Regression Evidence

- `03-SECURITY.md` records all nine Phase 3 threats closed and no open high-severity threat.
- The post-gap `03-REVIEW.md` is clean with zero critical, warning, or info findings.
- `03-REVIEW-FIX.md` and `03-GAP-FIX.md` are reflected in current tests: environment input
  participates in extraction identity; facts enforce canonical IDs; workflow/run/stage
  identities are revalidated; inherited correction stages are distinguished; extraction
  provenance and correction histories remain exact and immutable; follow-up user facts can
  be safely corrected and published only against a verified source bundle.
- The full offline suite includes Phases 1 and 2, so no automated local regression was found.

## External and Deferred Gates

| Gate | Result | Interpretation |
|---|---|---|
| Real local OCR (`pytest -m ocr`) | Passed: 2 passed, 488 deselected | Actual RapidOCR-backed local path is available and did not substitute fixture output. |
| Phase 3 Dify/VLM cloud tests | Cleanly skipped: 2 skipped | No Dify diagnosis app credentials or live VLM credentials are configured. These are explicitly non-blocking external gates in the approved Phase 3 plan. |
| Full-repository cloud marker | 16 passed, 2 skipped, 2 failed | The two failures were Phase 2 official pip source drift probes receiving HTTP 429. They do not exercise Phase 3 diagnosis code, but are recorded rather than hidden. |
| Real Dify diagnosis output | Deferred | Requires account/app configuration and remains part of the Phase 1 cloud capability gate; offline fixture identity is explicit and is not represented as Dify evidence. |

## Human Verification

No human-only check blocks the Phase 3 goal. The visible Gradio correction/result experience
belongs to Phase 4; Phase 3 exposes and verifies the required six-field/correction boundary
through strict JSON and CLI contracts. A future live Dify/VLM smoke run should be captured as
external evidence once credentials are intentionally configured, but it is not required to
accept the platform-independent Phase 3 implementation.

## Final Assessment

Phase 03 is ready to be marked complete and used as the verified dependency for Phase 04.
The only dirty pre-existing file during verification was `.planning/config.json`; this
verification did not modify implementation, configuration, roadmap, state, or requirements.
