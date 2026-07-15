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
formal run passed `1 passed in 29.16s`; only the captured process was stopped
and port `57117` was proved closed. The runner uses no fixture path, public
host, owner takeover, or shell redirection.

The real Microsoft Edge screenshot is exactly `1366 x 768`. Visual inspection
confirmed readable UTF-8 Chinese, completed and live status, the three
workbench headings, the report tab, citation/download tab and enabled download
CTA, and visible `local-rule-v1` provenance without horizontal crop. Browser
metrics were `scrollWidth=1366`, `clientWidth=1366`, so
`body_horizontal_overflow=false`.

| Evidence | SHA-256 |
|---|---|
| `evidence/ui/phase4/VQ-01-live-local.png` | `35d9aa50a4ff9df0ea99ffca3cc771d4be238547d3f717ab51dd14dcbaf2c155` |
| `evidence/ui/phase4/local-live-vq01.json` | `825431440c8a6fa325829d7d9dfd0e0eac40f7e80104990815000ff7920c18c7` |

The machine ledger has exactly the approved 14-field allowlist. It records
`completed`, `live`, null fixture fields, `local-rule-v1`, zero overflow, the
runner owner, UTC verification time, the screenshot hash, and only SHA-256
digests of case/run/result identities. It contains no raw identity, path,
input text, approval signature, token, or secret. The fresh result manifest
was uniquely created during this browser run and cross-checked against the DOM
source-run identity before the screenshot and ledger were written. Its safe
manifest fields were `status=completed`, `mode=live`, null fixtures, and
`backend=local-rule-v1`.

## TDD and focused safety proof

The structural RED command was run before implementation:

```text
.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "local_live_runner_has_single_owner_and_evidence_contract or local_live_ledger_has_exact_redacted_allowlist"
2 failed, 20 deselected
```

Both failures were the expected missing runner and missing ledger. After the
implementation and real evidence run, the same structural command reported
`2 passed, 20 deselected in 0.28s`.

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
769 passed, 49 deselected, 1 warning in 189.41s; exit 0

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
3 passed, 2 skipped in 9.35s; exit 0
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
