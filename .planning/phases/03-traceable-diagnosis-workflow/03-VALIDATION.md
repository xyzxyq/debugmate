---
phase: 03
slug: traceable-diagnosis-workflow
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-12
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|---|---|
| **Framework** | pytest 9.1.1 + Pydantic 2.13.4 + HTTPX MockTransport |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest -q -m "not cloud and not ocr"` |
| **Estimated runtime** | quick < 5 s; full < 15 s |

## Sampling Rate

- **After every task commit:** Run the task's focused test file plus `.\.venv\Scripts\python.exe -m ruff check` on changed Python files.
- **After every plan wave:** Run `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis`.
- **Before `/gsd-verify-work`:** Full offline suite, Ruff, `pip check`, `git diff --check`, Schema fixture validation and secret scan must be green.
- **Max feedback latency:** 15 seconds for the default offline gate.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|---|---|---|---|
| 03-01-01 | 01 | 1 | DIAG-02/03/04 | T3-01 schema spoof | Strict v1.1 graph and migration reject dangling or extra fields | contract | `pytest -q tests/diagnosis/test_contract_v11.py` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | SAFE-04 | T3-02 command execution | Commands remain non-executable structured data; unsafe candidates reject | unit | `pytest -q tests/diagnosis/test_command_safety.py` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | INP-02/DIAG-06 | T3-03 OCR/VLM trust | Candidate provenance, normalization and correction revision are immutable/auditable | unit+integration | `pytest -q tests/diagnosis/test_extraction_correction.py` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | INP-03 | T3-04 forced certainty | <=3 unique high-value questions; second insufficient round stops | policy | `pytest -q tests/diagnosis/test_sufficiency.py` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | DIAG-01 | T3-05 route manipulation | Six categories + unknown, deterministic ordering and rule evidence | policy | `pytest -q tests/diagnosis/test_router.py` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 3 | DIAG-03 | T3-06 forged citation | Fact/source/build/locator links are exact and validated | integration | `pytest -q tests/diagnosis/test_evidence_binding.py` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 4 | DIAG-02/05 | T3-07 model contract drift | Exactly one repair; second invalid output becomes typed failure | port+integration | `pytest -q tests/diagnosis/test_generation_repair.py` | ❌ W0 | ⬜ pending |
| 03-04-02 | 04 | 4 | DIAG-06 | T3-08 stale rerun | Correction changes facts hash/run ID and reruns route/retrieval/generation | e2e | `pytest -q tests/diagnosis/test_workflow_e2e.py` | ❌ W0 | ⬜ pending |
| 03-04-03 | 04 | 4 | all | T3-09 evidence leak | Evidence is summary-only, privacy-scanned, atomic and backend-labeled | evidence | `pytest -q tests/diagnosis/test_workflow_evidence.py` | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] Create `tests/diagnosis/` and shared fictional case/retrieval/candidate fixtures.
- [ ] Add committed `contracts/diagnosis-record-v1.1.schema.json` generated from the Pydantic source of truth.
- [ ] Add marker-isolated `cloud` and `ocr` smoke stubs that skip cleanly without credentials/models.
- [ ] Add a Schema hash/generation check so committed JSON cannot drift from Pydantic.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| Real Dify candidate diagnosis and repair | DIAG-02/05 | Requires account, app workflow and API key | Run one approved synthetic case with `-m cloud`; record backend/run ID/prompt/schema/knowledge build and compare evidence bundle. |
| Real screenshot VLM extraction quality | INP-02/DIAG-06 | Requires configured vision model | Run one redacted fictional screenshot; review extracted fields, apply one correction and confirm rerun identity chain. |

## Validation Sign-Off

- [x] Every phase requirement has at least one planned automated proof.
- [x] Critical trust boundaries are tested in adjacent layers.
- [x] Default suite remains offline and no watch-mode flags are used.
- [x] Feedback latency target is below 15 seconds.
- [x] `nyquist_compliant: true` is set.

**Approval:** approved 2026-07-12
