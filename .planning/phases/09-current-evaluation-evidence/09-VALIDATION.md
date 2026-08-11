---
phase: 09
slug: current-evaluation-evidence
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-10
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for current representative-case and prompt-comparison evidence.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_contracts.py tests/evaluation/test_case_matrix.py tests/evaluation/test_prompt_comparison.py` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest -q` |
| **Formal phase command** | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-phase9-evaluation.ps1` |
| **Estimated runtime** | Quick feedback under 30 seconds; full suite and formal evidence runner may take several minutes |

---

## Sampling Rate

- **After every task commit:** Run the task's focused evaluation tests and Ruff on changed Python files.
- **After every plan wave:** Run all `tests/evaluation`, existing privacy/evidence/result focused suites, and the Phase 9 scope verifier.
- **Before phase verification:** Default offline pytest, formal Phase 9 runner, checksums, privacy scan, and frozen-media scope gate must all be green.
- **Max feedback latency:** 30 seconds for contract tasks; long live/media validation is reserved for explicit wave and final gates.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | EVAL-01 | T-09-01, T-09-05 | Strict 3–5-row matrix with P9-C04 fixed as deterministic `local_fallback`/`partial` audio-unavailable terminal state; historical evidence and fabricated artifacts rejected | unit | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_contracts.py tests/evaluation/test_case_matrix.py` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | EVAL-03 | T-09-02, T-09-03 | V1–V4 share exact sanitized input/facts/retrieval identity; every row binds conclusion, accepted diagnosis/result/candidate hashes, source evidence and truthful provenance | unit | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_prompt_comparison.py` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | EVAL-05 | T-09-04, T-09-06 | Eligibility requires privacy pass, exact artifact identity, current provenance and valid media | integration | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_course_source_manifest.py tests/results/test_security_abuse.py` | partial/W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | EVID-03 | T-09-04, T-09-07 | Reports are deterministic projections; Phase 10 media paths remain frozen | integration + scope | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_reports.py; powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify-phase9-scope.ps1` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 3 | EVAL-01, EVAL-03, EVAL-05, EVID-03 | T-09-01 through T-09-08 | Atomic runner fails closed without Phase 08 live prerequisite and promotes only a fully verified ledger | E2E | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-phase9-evaluation.ps1` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Threat References

| Ref | Threat | Required control |
|-----|--------|------------------|
| T-09-01 | Historical Phase 5/6 or C01–C07 evidence relabelled current | Require the formal Phase 08 Plan 07 summary, manifest, current contract and exact hashes |
| T-09-02 | Prompt variant output provenance inflated | Separate `generated_live` from `verified_contract`; bind prompt file SHA-256 |
| T-09-03 | Different inputs/facts/retrieval used across V1–V4 | One immutable common-input identity and equality gate |
| T-09-04 | Secret, private path, approval material or raw provider data leaks | Allowlisted projections plus adversarial privacy/secret scans without echoing the rejected value |
| T-09-05 | Insufficient row fabricates report/PNG/MP3/ZIP or fixed P9-C04 local-fallback partial row misstates audio availability | State-aware availability contract, exact local_fallback/partial audio-unavailable fixture, and explicit rejection tests |
| T-09-06 | Corrupt or mismatched citation/media/ZIP enters course sources | Reopen with existing result validators; verify MIME, members, SHA-256 and FFprobe metadata |
| T-09-07 | Phase 9 overwrites frozen final screenshots, PPTX, MP4 or SRT | Baseline inventory and fail-on-diff/new-file scope gate |
| T-09-08 | Failed partial run replaces last good evaluation ledger | Sibling staging, all gates before atomic promotion, rollback residue tests |

---

## Wave 0 Requirements

- [ ] `src/debugmate/evaluation/contracts.py` — strict bounded models for case, prompt and Phase 10 source manifests.
- [ ] `tests/evaluation/test_contracts.py` — strict/extra-forbid/path/hash/provenance contracts.
- [ ] `tests/evaluation/test_case_matrix.py` — 3–5 range, exact coverage tags and status/artifact rules.
- [ ] `tests/evaluation/test_prompt_comparison.py` — exact common identity and generation-vs-verification truth.
- [ ] `tests/evaluation/test_course_source_manifest.py` — EVAL-05 eligibility and current provenance.
- [ ] `tests/evaluation/test_reports.py` — deterministic JSON/Markdown projections.
- [ ] `scripts/verify-phase9-scope.ps1` — privacy, secret, tracked-evidence and frozen Phase 10 paths.
- [ ] `scripts/run-phase9-evaluation.ps1` — dependency gate, offline/live orchestration and atomic promotion.

No test framework installation is required.

## Resolved Execution Decisions

- The formal Phase 09 runner hard-requires completed `08-07-SUMMARY.md` plus the exact checksum-valid Phase 08 evidence bundle; missing evidence is `blocked`, never live pass.
- V2–V4 default to `verified_contract` against the exact accepted V1 output; `generated_live` requires each row's own provider-run evidence and prompt hash.
- `P9-C04-fallback-failure` is fixed as the deterministic `execution_backend=local_fallback`, `status=partial`, audio-unavailable terminal result. It retains only the availability allowed by the existing partial-result contract.

---

## Manual-Only Verifications

All Phase 09 behaviors have automated verification. Real Dify execution is an explicit credentialed automated gate whose prerequisite is Phase 08 Plan 07; missing credentials produce `blocked`, never a manual evidence override. Human visual/listening review belongs to Phase 10 after media generation.

---

## Validation Sign-Off

- [x] All anticipated tasks have automated verification or Wave 0 dependencies.
- [x] Sampling continuity has no three consecutive tasks without automated feedback.
- [x] Wave 0 covers every currently missing evaluation test/script.
- [x] No watch-mode flags are used.
- [x] Focused feedback target is under 30 seconds; long gates are isolated.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** approved for planning 2026-08-10; formal execution remains dependency-gated by Phase 08 Plan 07.
