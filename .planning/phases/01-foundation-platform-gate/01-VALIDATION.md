---
phase: 1
slug: foundation-platform-gate
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + Ruff 0.15.21 |
| **Config file** | `pyproject.toml` — Wave 1 creates |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest -q -m "not cloud"` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest -q; .\.venv\Scripts\python.exe -m ruff check .` |
| **Estimated runtime** | ~30 seconds offline; cloud probe separate |

## Sampling Rate

- **After every task commit:** Run the task's focused `pytest` file.
- **After every plan wave:** Run `.\.venv\Scripts\python.exe -m pytest -q -m "not cloud"` and Ruff.
- **Before phase verification:** Full offline suite must be green; run cloud probe when credentials exist.
- **Max feedback latency:** 30 seconds for offline checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INP-04 | T1-02 | Strict schema rejects extra/type drift | unit | `pytest -q tests/test_contracts.py` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | EVID-02 | T1-04 | Repo has versioned contract/fixture paths | contract | `pytest -q tests/test_fixture_adapter.py` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | EVID-01 | T1-03 | No evidence publishes without manifest | integration | `pytest -q tests/test_evidence.py` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | EVID-01 | T1-01 | Settings/log output do not expose keys | security | `pytest -q tests/test_evidence.py -k secret` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 3 | EVID-02 | T1-04 | Fixture and Dify share narrow port | contract | `pytest -q tests/test_probe_cli.py -m "not cloud"` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 3 | EVID-01 | T1-05 | Probe states are explicit and auditable | integration | `pytest -q tests/test_probe_cli.py` | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] `pyproject.toml` — pytest markers, package metadata and Ruff config.
- [ ] `tests/test_contracts.py` — case ID and DiagnosisRecord strictness.
- [ ] `tests/test_fixture_adapter.py` — offline backend contract.
- [ ] `tests/test_evidence.py` — atomic publish, failure manifest, hash and secret tests.
- [ ] `tests/test_probe_cli.py` — CLI and capability status behavior.
- [ ] `.venv` — Python 3.13 environment with phase dependencies.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dify account/API availability | EVID-02 | Requires user's cloud account/login and possibly CAPTCHA | Log in, create/reuse app, set env vars locally, run `run_phase1_probe.ps1`, retain redacted report |
| DSL export/import | EVID-02 | Cloud UI operation and account workspace required | Export DSL, save under `platform/dify/`, import into a clean app/workspace, record result |
| TTS provider availability | EVID-01 | Depends on account provider/credits | Call TTS with fixed recap text; verify MIME and FFprobe duration; otherwise mark blocked |

## Validation Sign-Off

- [x] All planned task types have automated verification or Wave 0 dependencies.
- [x] Sampling continuity: no three consecutive tasks without automated verification.
- [x] Wave 0 covers every currently missing test/config file.
- [x] No watch-mode flags.
- [x] Offline feedback target is under 30 seconds.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-07-10 for planning
