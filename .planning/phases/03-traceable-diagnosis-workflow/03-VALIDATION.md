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
| 03-01-01 | 01 | 1 | DIAG-02/03/04 | T3-01 schema spoof | Strict v1.1 graph and migration reject dangling or extra fields | contract | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_contract_v11.py tests\test_contracts.py` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | SAFE-04 | T3-02 command execution | CommandStep remains inert structured data; scoped shell/import guard rejects execution capability | unit | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_command_safety.py tests\diagnosis\test_contract_v11.py` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | INP-02 | T3-03 OCR/VLM trust | Provider verifies approved screenshot path/hash and returns candidate-only provenance | port+integration | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_extraction_providers.py tests\diagnosis\test_extraction_correction.py -k "extraction or provenance or normalization or privacy"` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | DIAG-06 | T3-03 correction trust | Stable IDs and optimistic locks create an immutable facts revision | unit | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_extraction_correction.py` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | DIAG-01 | T3-05 route manipulation | Six categories + unknown, deterministic provisional/final route and fact/rule evidence | policy | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_router.py` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | INP-03 | T3-04 forced certainty | At most three unique questions; unresolved round 1 stops before generation | policy | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_sufficiency.py tests\diagnosis\test_router.py` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 3 | DIAG-03 | T3-06 forged citation | Fact/source/build/locator links are exact and validated | integration | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_evidence_binding.py` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 4 | SAFE-04/DIAG-02/03/04/05 | T3-07 model contract drift | Candidate-only adapter, strict local validation and exactly one repair | port+integration | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_generation_repair.py tests\test_fixture_adapter.py` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 5 | INP-02/03, SAFE-04, DIAG-01/02/03/04/05/06 | T3-08 approval/rerun | verify_approval precedes input_approved/provider calls; fixture workflow and correction rerun are deterministic | e2e | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_workflow_e2e.py tests\test_probe_cli.py` | ❌ W0 | ⬜ pending |
| 03-06-01 | 06 | 6 | INP-02/03, SAFE-04, DIAG-01/02/03/04/05/06 | T3-09 evidence leak | Evidence is summary-only, privacy-scanned, atomic and immutable; every committed diagnosis fixture validates against v1.1 and tracked product/fixture files pass the secret scan | evidence+gate | `.\.venv\Scripts\python.exe -m pytest -q -m "not cloud and not ocr"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; .\.venv\Scripts\python.exe -m ruff check .; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; .\.venv\Scripts\python.exe -m pip check; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; git diff --check; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; $diagnosisFixtures = @(git ls-files 'fixtures/**/diagnosis.json'); if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; if ($diagnosisFixtures.Count -eq 0) { Write-Error "No committed diagnosis fixtures found"; exit 1 }; foreach ($fixture in $diagnosisFixtures) { & .\.venv\Scripts\python.exe -m jsonschema -i $fixture contracts\diagnosis-record-v1.1.schema.json; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }; git grep -n -I -E "SECRET_SENTINEL_DO_NOT_LOG|sk-[A-Za-z0-9_-]{8,}|BEGIN( [A-Z0-9]+)* PRIVATE KEY|20795" -- src contracts fixtures knowledge prompts platform scripts README.md pyproject.toml; if ($LASTEXITCODE -eq 0) { Write-Error "Potential secret found in tracked product or fixture files"; exit 1 } elseif ($LASTEXITCODE -ne 1) { exit $LASTEXITCODE }` | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] Create `tests/diagnosis/` and shared fictional case/retrieval/candidate fixtures.
- [ ] Add committed `contracts/diagnosis-record-v1.1.schema.json` generated from the Pydantic source of truth.
- [ ] Add marker-isolated `cloud` and `ocr` smoke stubs that skip cleanly without credentials/models.
- [ ] Add a Schema hash/generation check so committed JSON cannot drift from Pydantic.

## Non-Blocking External Verifications

| Behavior | Requirement | Why External | Test Instructions |
|---|---|---|---|
| Real Dify candidate diagnosis and repair | DIAG-02/05 | Requires account, app workflow and API key; never blocks offline sign-off | Run one approved synthetic case with `pytest -m cloud`; record backend/run ID/prompt/schema/knowledge build and compare evidence bundle. |
| Real screenshot VLM extraction quality | INP-02/DIAG-06 | Requires configured vision model; never blocks offline sign-off | Run the marker-isolated VLM cloud test over one redacted fictional screenshot; review candidates, apply one correction and confirm rerun identity chain. |

## Validation Sign-Off

- [x] Every phase requirement has at least one planned automated proof.
- [x] Critical trust boundaries are tested in adjacent layers.
- [x] Default suite remains offline and no watch-mode flags are used.
- [x] Feedback latency target is below 15 seconds.
- [x] `nyquist_compliant: true` is set.

**Approval:** approved 2026-07-12
