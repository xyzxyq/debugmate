---
phase: 08
slug: dify-unified-live-chain
status: verified
scope: 08-01-through-08-06
threats_total: 25
threats_closed: 25
threats_open: 0
unregistered_flags: 0
deferred_to_08_07: 2
asvs_level: 1
block_on: high
created: 2026-08-11
updated: 2026-08-11
---

# Phase 08 — Security Verification (Plans 08-01 through 08-06)

> Retroactive verification of the threat mitigations declared in the six executed plans. Plan 08-07 was not executed and no cloud API was called during this audit. `closed` below means the declared source-code mitigation and its offline/adversarial verification exist; it does not claim that the credentialed 08-07 live acceptance evidence exists.

## Audit Configuration and Scope

| Item | Value |
|---|---|
| Audited plans | `08-01`, `08-02`, `08-03`, `08-04`, `08-05`, `08-06` |
| Excluded plan | `08-07` (external Dify dataset/app readiness is missing) |
| ASVS level | 1 (repository/default GSD security level) |
| Blocking threshold | high |
| User-selected action | Verify all open threats |
| Implementation mutation | None |
| Cloud/API activity | None |

## Trust Boundaries

| Plan | Boundary | Security property verified |
|---|---|---|
| 08-01 | QA process → product validator | Git/process capability stays outside product Python; exact path/hash inventory is validated. |
| 08-01 | Approval authority → receipt disk | Approval secrets and raw provider identifiers collapse to bounded fingerprints. |
| 08-01 | Provider envelope → local models | Provider JSON is strict, bounded, and extra fields are rejected. |
| 08-02 | Sealed knowledge build → Dify dataset | Complete preflight and explicit deletion authorization precede mutation. |
| 08-02 | Dify readback → local attestation | Counts, configuration, hashes, and metadata require exact comparison. |
| 08-03 | Environment configuration → bearer request | Only the canonical HTTPS Dify origin is accepted; redirects are disabled. |
| 08-03 | Approved screenshot → upload API | One root-confined immutable byte snapshot binds hash, image decode, and MIME. |
| 08-03 | Dify response → parser | Response size, status, retry, and trace content are bounded before trust. |
| 08-04 | Diagnosis outcome → result publication | Explicit execution backend participates in immutable result identity. |
| 08-04 | Result manifest → loader/view | Backend is verified from strict manifest bytes and is never inferred. |
| 08-05 | One-time approval → outbound side effect | Local preparation and durable `started` receipt precede dispatch. |
| 08-05 | Dify envelope → diagnosis outcome | Facts, routing, retrieval, commands, privacy, and versions are locally validated. |
| 08-05 | Accepted outcome → publication | Invalid/stale cloud results terminate without result artifacts. |
| 08-06 | Server config → selected service | Backend selection is server-side and construction performs no network I/O. |
| 08-06 | Browser preview token → outbound Dify | Atomic current-token consumption remains the sole UI authorization boundary. |
| 08-06 | Service terminal state → DOM/download | Failed cloud diagnosis exposes safe state only, with no stale artifacts/download. |

## Threat Register

Every PLAN row is retained below, including repeated phase-wide threat IDs. All 25 declared dispositions are `mitigate`; no threat is skipped.

| Plan / Threat ID | Category | Component | Disposition | Verification evidence | Status |
|---|---|---|---|---|---|
| 08-01 / T-08-COMMAND | Elevation | `dify_live_evidence.py` | mitigate | Product validator consumes required inventory at `src/debugmate/dify_live_evidence.py:547-637`; repository process-capability policy is exercised by `tests/diagnosis/test_command_safety.py:21-127`; required CLI inventory failures are tested at `tests/test_probe_cli.py:468-486`. | closed |
| 08-01 / T-08-LEAK | Information disclosure | cloud contracts/receipts | mitigate | Strict extra-forbid contract at `src/debugmate/cloud/contracts.py:27`; bounded fingerprints/summary/failure detail at `src/debugmate/cloud/contracts.py:87-181`; receipt leak/restart tests at `tests/cloud/test_receipts.py:116-177`. | closed |
| 08-01 / T-08-DUPLICATE | Tampering/DoS | receipt transitions | mitigate | Atomic `fsync` + replace at `src/debugmate/cloud/receipts.py:114-134`; one-way begin/finish state machine at `src/debugmate/cloud/receipts.py:140-184`; all terminal variants and rewrite rejection at `tests/cloud/test_receipts.py:63-116`. | closed |
| 08-01 / T-08-SIZE | DoS | run envelope | mitigate | Retrieval hit summary cap and duplicate checks at `src/debugmate/cloud/contracts.py:108-131`; adversarial oversize/duplicate/hit-count tests at `tests/cloud/test_run_envelope.py:71-86`. | closed |
| 08-02 / T-08-KNOWLEDGE | Tampering/DoS | sync planner/executor | mitigate | Complete pagination at `src/debugmate/knowledge/sync.py:696-733`, bounded indexing at `:736-775`, explicit delete gate and ordered transaction at `:897-1025`, exact comparison at `:1041-1065`; 17-source transaction test at `tests/knowledge/test_dify_readback.py:161-264`. | closed |
| 08-02 / T-08-LEAK | Information disclosure | CLI/attestation | mitigate | Attestation persists dataset/document fingerprints at `src/debugmate/knowledge/sync.py:1027-1036`; missing key is typed/value-free at `:1094`; CLI dry-run separation at `src/debugmate/cli.py:321-357`; secret/raw-ID assertions in `tests/knowledge/test_dify_readback.py:253-368`. | closed |
| 08-02 / T-08-DUPLICATE | DoS | indexing/write calls | mitigate | One sealed create/update pass followed by bounded `_poll_batches` and a single metadata batch at `src/debugmate/knowledge/sync.py:902-1003`; ordering and call-count behavior at `tests/knowledge/test_dify_readback.py:161-264`; dry-run zero HTTP at `tests/knowledge/test_coverage_sync.py:156-165`. | closed |
| 08-03 / T-08-ORIGIN | Spoofing/Information disclosure | settings/adapter | mitigate | Exact HTTPS origin/userinfo/query/fragment/path validation at `src/debugmate/settings.py:27-45`; explicit-test-origin guard and `follow_redirects=False` at `src/debugmate/adapters/dify.py:101-117,140-145`; origin tests at `tests/cloud/test_settings.py:13-40`. | closed |
| 08-03 / T-08-UPLOAD | Tampering | gateway/upload | mitigate | Link/reparse/root/regular-file checks and one-read hash/decode/MIME validation at `src/debugmate/gateway.py:54-122`; immutable preparation before network at `:148-204`; replacement and exact image-input tests at `tests/cloud/test_gateway.py:81-136`. | closed |
| 08-03 / T-08-DUPLICATE | Tampering/DoS | workflow POST | mitigate | Only connect failure retries; read/write/protocol ambiguity is terminal at `src/debugmate/adapters/dify.py:138-165`; dispatch-count tests at `tests/cloud/test_dify_adapter.py:109-139`. | closed |
| 08-03 / T-08-CITATION | Tampering | DSL retrieval trace | mitigate | DSL sanitizer receives direct retrieval output and fingerprints bounded hits at `platform/dify/app.dsl.yml:941-994`; static direct-selector and missing-trace rejection at `tests/platform/test_dify_dsl.py:113-152`; local DSL/run/node binding at `src/debugmate/cloud/workflow.py:254-316`. | closed |
| 08-03 / T-08-SIZE | DoS | response parser | mitigate | 512 KiB cap and pre-parse bounded read at `src/debugmate/adapters/dify.py:23,69-79,197`; Content-Length and streamed-body adversarial tests at `tests/cloud/test_dify_adapter.py:91-102`. | closed |
| 08-03 / T-08-LEAK | Information disclosure | errors/results | mitigate | Safe status mapping without response body/header interpolation at `src/debugmate/adapters/dify.py:149-184`; fingerprint-only IDs and safe error assertions exercised by `tests/cloud/test_dify_adapter.py`. | closed |
| 08-04 / T-08-RACE | Tampering | service/cache/result store | mitigate | Backend participates in result identity at `src/debugmate/results/publisher.py:411-440`; immutable reuse requires matching backend at `:678-719`; verifier re-derives backend-bound ID at `src/debugmate/results/verifier.py:761-783`; cross-backend test at `tests/results/test_backend_provenance.py:110-124`. | closed |
| 08-04 / T-08-LEAK | Information disclosure | view/manifest | mitigate | Manifest/view expose strict execution enum at `src/debugmate/results/contracts.py:261-280`; service propagates explicit enum at `src/debugmate/results/service.py:175-208`; strict provenance tests at `tests/results/test_backend_provenance.py:22-99`. | closed |
| 08-04 / T-08-CITATION | Spoofing | UI/result truth | mitigate | `ResultMode` remains only live/replay and illegal backend combinations fail at `src/debugmate/results/contracts.py:51,261-280`; backend is loaded from strict manifest at `src/debugmate/results/loader.py:312`; negative/inference-independent tests at `tests/results/test_backend_provenance.py:22-69,94-124`. | closed |
| 08-05 / T-08-DUPLICATE | Tampering/DoS | live workflow/receipt | mitigate | Approval and local immutable preparation precede receipt begin and dispatch at `src/debugmate/cloud/workflow.py:324-350`; duplicate receipt rejection at `:339-342`; uncertainty is terminal at `:366-379`; reuse/stale tests at `tests/cloud/test_live_workflow.py:286-303,342-362`. | closed |
| 08-05 / T-08-INJECTION | Tampering/Elevation | envelope/diagnosis | mitigate | Strict envelope/fact/version validation at `src/debugmate/cloud/workflow.py:236-269`; bounded one-repair policy at `src/debugmate/diagnosis/generation.py:22,224-285`; unsafe command/privacy candidates never repair at `tests/cloud/test_live_workflow.py:474-503`. | closed |
| 08-05 / T-08-CITATION | Tampering | retrieval binding | mitigate | Run and sanitizer fingerprints plus direct trace binding to current build at `src/debugmate/cloud/workflow.py:271-316`; forged/stale/mutation regressions at `tests/cloud/test_live_workflow.py:286-332` and `tests/diagnosis/test_evidence_binding.py:109-162`. | closed |
| 08-05 / T-08-RACE | Tampering | service/outcome store | mitigate | Receipt identity is consumed once before dispatch (`src/debugmate/cloud/workflow.py:324-350`), accepted result finishes atomically at `:504-511`, and immutable concurrent publication is adversarially covered at `tests/results/test_security_abuse.py:189-213`. | closed |
| 08-05 / T-08-LEAK | Information disclosure | repair/failure/evidence | mitigate | Repair payload is the allowlisted candidate plus `{code,pointer}` issues (`src/debugmate/diagnosis/generation.py:265-271`); receipt attempts use fingerprints; safe payload shape/no-provider-body assertion at `tests/cloud/test_live_workflow.py:432-469`; artifact export abuse tests in `tests/results/test_security_abuse.py`. | closed |
| 08-06 / T-08-RACE | Tampering | UI callbacks | mitigate | Callback ordering is `consume_current` → `approve_preview` → diagnosis at `src/debugmate/ui/app.py:2192-2205`; blocking actions/stale behavior at `tests/ui/test_dify_live.py:332-366`. | closed |
| 08-06 / T-08-LEAK | Information disclosure | UI/view/download | mitigate | UI labels derive from explicit enum at `src/debugmate/ui/presentation.py:331-344`; downloads are verified one-shot bytes rather than paths (`tests/results/test_service.py:323-335`); invalid Dify result has no download at `tests/ui/test_dify_live.py:332-348`. | closed |
| 08-06 / T-08-DUPLICATE | DoS | blocking actions | mitigate | Blocking frame disables inputs/replay/duplicate actions (`src/debugmate/ui/app.py:2219-2241`; `tests/ui/test_dify_live.py:356-366`) and exposes no cancellation claim/control. | closed |
| 08-06 / T-08-INJECTION | Elevation | displayed provider data | mitigate | Only a locally validated outcome is constructed after `validate_diagnosis_outcome` at `src/debugmate/cloud/workflow.py:401-502`; invalid cloud diagnosis remains artifact-free at `tests/ui/test_dify_live.py:332-348` and typed safe failure at `tests/results/test_service.py:129-147`. | closed |

## Deferred Final-Live Acceptance (`deferred_to_08_07`)

These are external acceptance gates, not source-code mitigation gaps and not additional/open threats in the 08-01..08-06 register.

| Deferred item | Why deferred | Required 08-07 evidence | Status |
|---|---|---|---|
| Credentialed 17-source Knowledge sync/readback | `DIFY_DATASET_API_KEY` and server-side dataset binding are unavailable; this audit must not call cloud APIs. | Fresh sanitized readback attestation proving exact 17-source count/config/hash/metadata equality. | deferred_to_08_07 |
| Current DSL import/binding and real same-run Dify product evidence | App-ready configuration/current real run is unavailable; historical C01-C07 evidence is capability-only. | Fresh import/export, real approved workflow run, direct retrieval trace, receipt/result identities, MP3/ZIP checks, and Phase 08 evidence promotion/security gate. | deferred_to_08_07 |

The implemented local gates for both items are closed and tested, but the live observations themselves are intentionally not claimed.

## Threat Flags

No `## Threat Flags` section is present in any of `08-01-SUMMARY.md` through `08-06-SUMMARY.md`. Therefore:

- mapped informational flags: none
- unregistered flags: none
- `unregistered_flags: 0`

## Accepted Risks Log

No accepted risks. Every registered threat uses the `mitigate` disposition; none was converted to `accept` or `transfer` during this audit.

## Code Review Closure Evidence

Iteration 1 identified four security-relevant warnings and `08-REVIEW-FIX.md` records all four as fixed:

| Finding | Closure used by this audit |
|---|---|
| WR-01 remote DSL/retrieval fingerprints unverified | Current workflow independently binds DSL semantic hash, recomputed run fingerprint, and sanitizer fingerprint (`src/debugmate/cloud/workflow.py:254-289`). |
| WR-02 local validation could strand `STARTED` receipt | Current gateway completes immutable local `prepare_dispatch()` before receipt creation (`src/debugmate/gateway.py:148-176`; `src/debugmate/cloud/workflow.py:324-340`). |
| WR-03 knowledge authority accepted self-asserted identity | Production authority is loaded with `validate_knowledge_build()` (`src/debugmate/cloud/workflow.py:49,108-109`). |
| WR-04 capture script defaulted outside repository | Script now resolves the repository `.venv` interpreter and validates it as a regular file; covered by `tests/platform/test_dify_live_evidence.py`. |

`08-REVIEW.md` iteration 2 reports `critical: 0`, `warning: 0`, `info: 0`, status `clean`, after a 199-pass scoped regression and Ruff/compile/PowerShell/diff checks.

## Verification Run

Executed on 2026-08-11 without live/cloud markers or credentials:

```text
.\.venv\Scripts\python.exe -m pytest -q tests/cloud tests/knowledge \
  tests/diagnosis/test_command_safety.py tests/diagnosis/test_evidence_binding.py \
  tests/results/test_backend_provenance.py tests/results/test_security_abuse.py \
  tests/results/test_service.py tests/results/test_result_e2e.py tests/platform \
  tests/test_probe_cli.py

341 passed, 18 deselected in 64.09s
```

The 18 deselections are marker-isolated live/cloud checks and are consistent with the explicit instruction not to invoke Dify. They do not negate the offline implementation mitigations; the corresponding live acceptance remains listed above as `deferred_to_08_07`.

## Security Audit Trail

| Audit Date | Scope | Threat Rows | Closed | Open | Deferred live acceptance | Run By |
|---|---|---:|---:|---:|---:|---|
| 2026-08-11 | Plans 08-01 through 08-06 | 25 | 25 | 0 | 2 | Codex `gsd-security-auditor` |

## Sign-Off

- [x] All 25 registered threat rows classified by disposition.
- [x] Every registered disposition is `mitigate` and has code/test evidence.
- [x] Summary threat flags checked; none are present.
- [x] Iteration-2 clean review and all four fix closures incorporated.
- [x] Implementation files were not modified.
- [x] No cloud API was called and 08-07 was not treated as executed.
- [x] `threats_open: 0` confirmed for executed Plans 08-01 through 08-06.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-11 for implementation mitigations in Plans 08-01 through 08-06; final credentialed/live acceptance remains `deferred_to_08_07`.
