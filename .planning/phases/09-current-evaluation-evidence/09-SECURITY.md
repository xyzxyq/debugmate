---
phase: 09-current-evaluation-evidence
phase_number: "09"
slug: current-evaluation-evidence
scope:
  - 09-01
  - 09-02
status: verified
threats_total: 10
threats_closed: 10
threats_open: 0
asvs_level: 1
block_on: high
deferred_to_09_03: true
created: 2026-08-11
audited: 2026-08-11
---

# Phase 09 — Security

> Scoped security verification for executed Plans 09-01 and 09-02 only. Plan 09-03 live collection and atomic promotion remain dependency-blocked on Phase 08 Plan 07 and are explicitly not claimed as closed here.

---

## Scope and Configuration

- **Audited implementation:** Phase 09 Plans 01 and 02, their current source registries, evaluation contracts, collector, projections, scope gate, and focused tests.
- **Excluded implementation:** Phase 09 Plan 03, cloud/provider execution, formal live-evidence publication, final report promotion, and all Phase 10 media.
- **Security enforcement:** enabled by default because `.planning/config.json` does not explicitly disable it.
- **ASVS level:** 1 (workflow default).
- **Blocking threshold:** high (workflow default). Every registered high-severity threat below is closed by an implemented fail-closed control; no risk was accepted or transferred.

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Registry JSON → evaluation contracts | Registry content is untrusted until strict roots, hashes, bounds, and state rules pass. | Safe case metadata and repository references |
| Prompt/output identity → comparison | A label or filename is not proof that a provider used a prompt. | Prompt hashes, accepted-output hashes, provenance receipts |
| Phase 08 formal evidence → P9-C01 | Historical or incomplete artifacts must not become current live proof. | Formal summary, manifest, checksums, live-run identity |
| Run/result bundles → collector | Bundle paths and claims are untrusted until reopened and identity-bound. | Diagnosis, retrieval, build, citations, result artifacts |
| Validated contracts → reports | Projection code must preserve validated meaning and privacy. | Canonical JSON and review-only Markdown |
| Phase 09 workspace → frozen Phase 10 media | Evaluation work must not change final course assets. | PPTX, MP4, SRT, screenshots, final manifests |

## Threat Register

The duplicate IDs T-09-04 and T-09-05 are retained as separate plan-register entries because Plans 09-01 and 09-02 assign them distinct components and mitigation obligations.

| Threat ID | Plan | Category | Component | Disposition | Mitigation | Status | Evidence |
|-----------|------|----------|-----------|-------------|------------|--------|----------|
| T-09-01 | 09-01 | Spoofing | P9-C01 source reference | mitigate | Exact Phase 08 Plan 07 paths/hashes; strict formal manifest/checksum/readback/live-run validation; absence or drift fails closed. | closed | `src/debugmate/evaluation/contracts.py:177`, `src/debugmate/evaluation/contracts.py:297`, `src/debugmate/evaluation/collector.py:225`, `src/debugmate/evaluation/collector.py:256`; `tests/evaluation/test_evaluation_contracts.py:48`, `tests/evaluation/test_course_source_manifest.py:110` |
| T-09-02 | 09-01 | Spoofing / Repudiation | V1–V4 provenance | mitigate | Strict provenance enum and hash-bound evidence receipt; `generated_live` requires its own accepted provider-run evidence and cannot be serialized from `verified_contract`. | closed | `src/debugmate/evaluation/contracts.py:524`, `src/debugmate/evaluation/contracts.py:551`, `src/debugmate/evaluation/contracts.py:574`; `tests/evaluation/test_prompt_comparison.py:144`, `tests/evaluation/test_prompt_comparison.py:158` |
| T-09-03 | 09-01 | Tampering | Common comparison identity | mitigate | One immutable case/input/facts/retrieval/build/schema identity is equality-gated across all four rows; accepted V1 bindings cannot drift. | closed | `src/debugmate/evaluation/contracts.py:426`, `src/debugmate/evaluation/contracts.py:606`, `src/debugmate/evaluation/contracts.py:613`; `tests/evaluation/test_prompt_comparison.py:120`, `tests/evaluation/test_prompt_comparison.py:132` |
| T-09-05 | 09-01 | Tampering | Case artifact availability | mitigate | Terminal-state contracts reject fabricated artifacts for insufficient-data rows and enforce the exact local-fallback partial/audio-unavailable state. | closed | `src/debugmate/evaluation/contracts.py:264`, `src/debugmate/evaluation/contracts.py:280`; `tests/evaluation/test_case_matrix.py:34`, `tests/evaluation/test_case_matrix.py:47`, `tests/evaluation/test_case_matrix.py:61` |
| T-09-04 | 09-01 | Information disclosure | Registry and comparison values | mitigate | Allowlisted normalized repository paths, forbidden markers/frozen suffixes, regular-file checks, bounded safe text, and export scanning deny raw/provider/approval/historical-media values. | closed | `src/debugmate/evaluation/contracts.py:32`, `src/debugmate/evaluation/contracts.py:45`, `src/debugmate/evaluation/contracts.py:79`, `src/debugmate/evaluation/contracts.py:241`, `src/debugmate/evaluation/contracts.py:446`; `tests/evaluation/test_evaluation_contracts.py:33` |
| T-09-04 | 09-02 | Information disclosure | Collector / projections | mitigate | Collector exposes allowlisted claim-safe fields and stable codes; JSON and Markdown are recursively export-scanned; rejected unsafe values are not echoed. | closed | `src/debugmate/evaluation/collector.py:153`, `src/debugmate/evaluation/collector.py:171`, `src/debugmate/evaluation/collector.py:512`, `src/debugmate/evaluation/reports.py:45`; `tests/evaluation/test_reports.py:29`, `tests/evaluation/test_reports.py:75` |
| T-09-06 | 09-02 | Tampering | Result / citation / media inputs | mitigate | Exact formal artifacts and checksums are reopened; result bundles use the product verifier; diagnosis, retrieval, knowledge build, anchors, backend, status, and result identity are cross-bound before eligibility. | closed | `src/debugmate/evaluation/collector.py:225`, `src/debugmate/evaluation/collector.py:326`, `src/debugmate/evaluation/collector.py:387`, `src/debugmate/evaluation/collector.py:441`, `src/debugmate/evaluation/collector.py:451`; `tests/evaluation/test_course_source_manifest.py:145`, `tests/results/test_phase9_collection.py:118`, `tests/results/test_phase9_collection.py:148` |
| T-09-07 | 09-02 | Tampering | Course media paths | mitigate | Immutable pre-Phase-09 baseline ancestry and committed/dirty/untracked checks protect final media; Phase 09 projection media and course-builder invocations are denied. | closed | `scripts/verify-phase9-scope.ps1:17`, `scripts/verify-phase9-scope.ps1:36`, `scripts/verify-phase9-scope.ps1:50`, `scripts/verify-phase9-scope.ps1:78`, `scripts/verify-phase9-scope.ps1:92`; `tests/evaluation/test_reports.py:131` |
| T-09-05 | 09-02 | Spoofing | Eligibility labels | mitigate | Eligibility is computed only after source currentness, privacy, citations, verified result, complete diagnosis evidence, completed status, and audio availability; every failure gets a stable exclusion reason. | closed | `src/debugmate/evaluation/collector.py:496`, `src/debugmate/evaluation/collector.py:526`, `src/debugmate/evaluation/collector.py:531`, `src/debugmate/evaluation/collector.py:539`, `src/debugmate/evaluation/collector.py:552`, `src/debugmate/evaluation/collector.py:563`; `tests/evaluation/test_course_source_manifest.py:123`, `tests/results/test_phase9_collection.py:118` |
| T-09-SIZE | 09-02 | Denial of Service | Source / read operations | mitigate | Strict field/list bounds, out-of-root and link rejection, exact artifact inventories, and bounded result-directory discovery limit read breadth and recursive content. | closed | `src/debugmate/evaluation/contracts.py:45`, `src/debugmate/evaluation/contracts.py:79`, `src/debugmate/evaluation/collector.py:61`, `src/debugmate/evaluation/collector.py:291`, `src/debugmate/evaluation/collector.py:303`; `tests/evaluation/test_evaluation_contracts.py:73` |

## Threat Flags

Neither `09-01-SUMMARY.md` nor `09-02-SUMMARY.md` contains a `## Threat Flags` section or an unmapped implementation flag. The clean iteration-2 review reports zero findings after all five iteration-1 fixes were verified.

### Unregistered Flags

None.

## Deferred to Plan 09-03 — Not Closed by This Audit

The following are execution dependencies, not implementation gaps in Plans 09-01/02 and not closed threats in this report:

- Formal live evidence for P9-C01 remains unavailable because `.planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md` and `evidence/dify-live/phase8/manifest.json` are absent.
- The Phase 09-03 runner, atomic staging/promotion, promoted checksums and final live evaluation ledger were not executed or audited; `09-03-SUMMARY.md` is absent.
- No cloud API or browser was called. No generated-live V1–V4 result, live success, or atomic promotion is claimed.
- Current code correctly represents this dependency as `phase8_formal_evidence_missing` and `phase10_eligible=false`; this fail-closed behavior is covered by `tests/evaluation/test_course_source_manifest.py:110` and `tests/evaluation/test_course_source_manifest.py:123`.

## Accepted Risks Log

No accepted risks. All audited entries use the `mitigate` disposition; no `accept` or `transfer` entries were registered in Plans 09-01/02.

## Verification Evidence

| Gate | Result |
|------|--------|
| Focused offline Pytest: `tests/evaluation`, `tests/results/test_phase9_collection.py`, `tests/results/test_security_abuse.py`, `tests/test_pytest_collection.py` | 60 passed |
| Scoped Ruff: evaluation implementation and focused tests | All checks passed |
| `scripts/verify-phase9-scope.ps1` | `phase9_scope_gate_passed` |
| Phase 09 code review iteration 2 | clean; 0 critical, 0 warning, 0 info |
| Phase 10 media mutation | None performed |
| Cloud/provider calls | None performed |

## Security Audit Trail

| Audit Date | Scope | Threat Entries | Closed | Open | Deferred Work | Run By |
|------------|-------|----------------|--------|------|---------------|--------|
| 2026-08-11 | Plans 09-01 and 09-02 | 10 | 10 | 0 | Plan 09-03 live collection and atomic promotion | Codex (gsd-security-auditor) |

## Sign-Off

- [x] Every Plan 09-01/02 threat was classified by disposition.
- [x] Every registered mitigation was found in current implementation and focused tests.
- [x] Summary threat flags and iteration-2 review/fix evidence were incorporated.
- [x] `threats_open: 0` is confirmed for the audited 09-01/02 scope.
- [x] Phase 09-03 live/promotion work is marked deferred rather than closed.
- [x] `status: verified` is set in frontmatter.

**Approval:** verified 2026-08-11 for Plans 09-01 and 09-02 only.
