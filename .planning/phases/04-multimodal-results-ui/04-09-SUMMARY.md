---
phase: 04-multimodal-results-ui
plan: 09
status: completed_vq01_only
completed: 2026-07-15
---

# Plan 04-09 Summary — real local-live VQ-01 only

## Scope and evidence

This plan closes only the local, non-network VQ-01 proof. It does not close
VQ-02 through VQ-15, does not complete Phase 4, and does not revise the 04-07
Dify or edge-TTS outcomes.

`scripts/run-phase4-local-live-qa.ps1` reserved a literal IPv4 loopback port,
released the reservation, started exactly one captured hidden
`.venv\Scripts\python.exe -m debugmate.ui.serve --host 127.0.0.1 --port N`
process, required the root `/config` object with a `components` list, injected
the base URL and screenshot path, and ran only the VQ-01 live browser test. Its
formal review-fix run passed `1 passed in 38.60s`; only the captured process was stopped
and port `57328` was proved closed. The runner uses no fixture path, public
host, owner takeover, or shell redirection.

The real Microsoft Edge screenshot is exactly `1366 x 768`. Visual inspection
confirmed readable UTF-8 Chinese, completed and live status, the three
workbench headings, the report tab, citation/download tab and enabled download
CTA, and visible `local-rule-v1` provenance without horizontal crop. Browser
metrics were `scrollWidth=1366`, `clientWidth=1366`, so
`body_horizontal_overflow=false`.

| Evidence | SHA-256 |
|---|---|
| `evidence/ui/phase4/VQ-01-live-local.png` | `ac1a0af845a6c292f1fa304755d76968f56604b0a1c2fac8d88a21680b706d84` |
| `evidence/ui/phase4/local-live-vq01.json` | `00fe952e1f06736fa9b83f61dbbef1457ea53ffa5b5aa3682713a3987a96f861` |

The machine ledger has exactly the approved 14-field allowlist. It records
`completed`, `live`, null fixture fields, `local-rule-v1`, zero overflow, the
runner owner, UTC verification time, the screenshot hash, and only SHA-256
digests of case/run/result identities. It contains no raw identity, path,
input text, approval signature, token, or secret. The fresh result manifest
was uniquely created during this browser run and cross-checked against the DOM
source-run identity. That identity located the strict source evidence manifest
at `.debugmate-runtime/evidence/<case>/<source_run>/manifest.json`; its
`case_id` and `run_id` matched the fresh result manifest and DOM, and its
observed backend was exactly `local-rule-v1`. The observed value, not UI copy,
was written to the ledger. The screenshot and ledger were written only after
all semantic assertions and this source-manifest check passed.

The runner now creates unique same-directory staging and backup paths before
starting Edge. Existing formal evidence is moved to backup first; pytest writes
only the staging paths injected through `DEBUGMATE_UI_SCREENSHOT_PATH` and
`DEBUGMATE_UI_LEDGER_PATH`. Before same-volume promotion, the runner validates
the PNG signature, exact ledger allowlist and semantics, UTC-Z timestamp, and
the ledger screenshot hash. Promotion is pair-aware and rollback restores the
old bytes if pytest, validation, promotion, or captured-owner cleanup fails.
The final successful run left zero staging/backup files and zero
`debugmate.ui.serve` processes.

## TDD and focused safety proof

The structural RED command was run before implementation:

```text
.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "local_live_runner_has_single_owner_and_evidence_contract or local_live_ledger_has_exact_redacted_allowlist"
2 failed, 20 deselected
```

Both failures were the expected missing runner and missing ledger. After the
implementation and real evidence run, the same structural command reported
`2 passed, 20 deselected in 0.28s`.

Review-fix RED added the evidence transaction and source-manifest boundary:

```text
.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "local_live_runner_has_single_owner_and_evidence_contract or local_live_runner_failure_restores_old_pair_and_clears_staging or source_manifest_backend_is_strictly_observed_and_identity_bound or local_live_ledger_has_exact_redacted_allowlist"
3 failed, 1 passed, 20 deselected in 2.81s
```

The failures were the missing ledger-path injection, transaction helpers and
strict source-manifest loader. GREEN was `4 passed, 20 deselected in 1.21s`.
The controlled failure uses a pytest temporary evidence directory, starts no
server, and proves the old PNG/JSON bytes are exactly restored with no staging
or backup residue. During real-run hardening, browser/assertion and staging UTC
validation failures also restored the prior formal pair and closed only ports
`51022`, `50263`, and `53129` before the final successful publication.

Focused non-network and fresh-identity proof:

```text
.venv\Scripts\python.exe -m pytest -q tests\ui\test_local_live.py -k "creates_verified_fresh_live_result or never_constructs_cloud_tts_or_touches_network"
2 passed, 6 deselected in 34.12s
```

The first test makes two consecutive normal calls and proves distinct
case/source-run/result identities rather than comparing replay fixtures. The
second poisons Dify TTS, edge TTS, HTTP, socket and replay boundaries and still
passes the local live path; live audio is local SAPI only.

Approval remains a separate action from preview. Missing, tampered and
cross-session preview tokens do not invoke the workflow:

```text
.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py -k "requires_preview_then_same_session_approval or rejects_missing_tampered_or_cross_session_token"
4 passed, 12 deselected, 1 warning in 5.15s
```

## Full gates

```text
.venv\Scripts\python.exe -m pytest
769 passed, 51 deselected, 1 warning in 229.18s; exit 0

.venv\Scripts\python.exe -m ruff check src tests
All checks passed; exit 0

.venv\Scripts\python.exe -m pip check
No broken requirements found; exit 0

git diff --check
silent; exit 0

git grep -n -I -E "SECRET_SENTINEL_DO_NOT_LOG|sk-[A-Za-z0-9_-]{8,}|BEGIN( [A-Z0-9]+)* PRIVATE KEY|20795" -- src contracts fixtures knowledge prompts platform scripts README.md pyproject.toml
no matches; exit 1 (expected clean result)
```

The only full-pytest warning is the existing Starlette TestClient/httpx
deprecation warning.

The required current-code audio marker was rerun:

```text
.venv\Scripts\python.exe -m pytest -q -m tts tests\results\test_tts_live.py
3 passed, 2 skipped in 12.90s; exit 0
```

The retained SAPI record remains mono MP3, 45,144 ms, 180,576 bytes, decode
exit `0`, non-silent with zero full-scale clipping samples, SHA-256
`10fb8c17b2c1c31b51055a71fa223deeb9ae9412f0f9218c1936bd4b933f0db6`.
Human listening remains exactly `human_needed`. Dify remains open because the
key is absent; edge TTS remains open because network TTS was not approved.

## Remaining truth

VQ-02 through VQ-15 remain open. The full visual ledger and independent Phase
4 verification remain pending. This VQ-01 local-live evidence does not alter
the 04-07 external-gate conclusions or claim full Phase 4 completion.
