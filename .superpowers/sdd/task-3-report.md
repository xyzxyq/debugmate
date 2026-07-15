# Task 3 Report — deliberate local preview/approval UI

## Outcome

Implemented the two-step, same-session local live path without duplicating the
Task 2 diagnosis/result pipeline:

1. the browser requests a fixed local demo redaction preview;
2. server-owned state stores the `PreviewBundle` behind a random opaque token;
3. the same browser session explicitly approves that one-time token;
4. the approved strict input is passed directly to the existing
   `ResultApplicationService` live event stream.

The real Edge gate finishes as `completed` + `live`, with null fixture fields,
local-rule provenance, enabled bundle download, and no horizontal overflow.

## RED evidence

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py tests\ui\test_callbacks.py
```

Result before production changes: **6 failed, 13 passed**. The failures were the
expected missing-feature failures: no `prepare_local_preview` callback and no
two-action controls/config.

During browser integration, a focused regression test also demonstrated that a
real Starlette `URL` request object was rejected by the string-only loopback
normalizer. The exact RED was one failed test with
`ResultServiceError: download_invalid`.

## GREEN evidence

Focused callback/session/store suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py tests\ui\test_callbacks.py tests\ui\test_local_live.py
```

Result: **29 passed, 1 warning in 50.33s**.

Focused real Edge live gate:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_browser.py -m browser -k vq_01_real_loopback_local_approval_produces_completed_live_result
```

Result: **1 passed, 19 deselected in 38.19s** after the request-boundary fix.
The final DOM observation showed completed/live state, a fresh `run_*` identity,
empty failure details, and live rather than replay metadata.

Brief browser command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py tests\ui\test_callbacks.py tests\ui\test_browser.py -m browser
```

Result: **20 passed, 22 deselected, 1 warning in 84.61s**.

Lint:

```powershell
.\.venv\Scripts\python.exe -m ruff check src\debugmate\ui tests\ui
```

Result: **All checks passed**.

`git diff --check` also completed with exit code 0.

## Browser and service ownership

- Browser: real Microsoft Edge, headless, `1366x768`, literal loopback URL.
- Navigation used `domcontentloaded`, component readiness, and a bounded terminal
  state poll; it did not use `networkidle`.
- The standard browser fixture owned each temporary serve process and cleaned it
  in `finally`.
- During root-cause isolation, temporary servers were tracked by exact PID and
  port. The final explicit audit reported `SERVE_COUNT=0`; the last diagnostic
  port was verified closed.
- Task 3 did not create a final evidence ledger or archived screenshot.

## Files

- `src/debugmate/ui/local_live.py`
- `src/debugmate/ui/app.py`
- `src/debugmate/ui/serve.py`
- `tests/ui/test_app.py`
- `tests/ui/test_callbacks.py`
- `tests/ui/test_browser.py`
- `tests/ui/test_local_live.py`
- `.superpowers/sdd/task-3-report.md`

Atomic commit subject:
`feat(04-09): require preview approval for local live diagnosis`.

## Self-review

- Raw input is constructed only on the server and passed through `redact_input`
  before storage or display.
- Browser `gr.State` receives only a cryptographically random opaque token.
- Store records are bounded, TTL-limited, session-bound, and atomically consumed
  before approval; missing, expired, tampered, copied, cross-session, and reused
  tokens make zero diagnosis calls.
- The approval key is generated once by `serve` and shared only with the local
  workflow and app callback; every approval/case/run identity remains fresh.
- Live execution reuses `_local_service`, the local-rule workflow, and local-only
  SAPI path. No Dify or Edge TTS adapter is constructed by the live path.
- Replay, correction, capability URLs, loopback request verification, and the
  existing 04-08 workbench grid remain intact.
- Real ASGI requests carry `starlette.datastructures.URL`; the loopback boundary
  now explicitly accepts only `str` or that exact URL type, then applies the
  existing strict scheme/host/port/query validation. Arbitrary stringifiable
  objects remain rejected.
- Temporary DEBUG instrumentation used during root-cause analysis was removed;
  source audit found no `DEBUGMATE_TASK3` marker.

## Concerns

- Test output retains the existing Starlette deprecation warning from
  `fastapi.testclient`; it is unrelated to this task and does not affect the
  browser or live-service gate.

## Review follow-up: UTF-8 truthfulness and atomic expiry

RED evidence:

- A deterministic fake-clock/RLock test held the preview-store lock while a
  consumer captured time, advanced the clock beyond the one-second TTL, and
  then released the lock. The previous implementation incorrectly returned a
  `LocalPreviewRecord` instead of `None`.
- UI configuration tests failed on the requested exact UTF-8 controls because
  the source still contained mojibake. The live callback test also showed that
  terminal metadata omitted the explicit null fixture fields.
- The first real-Edge review run exposed an overly broad test poll: running copy
  containing `已完成 0 个阶段` was mistaken for terminal completion. The
  poll now waits for the exact terminal badge `✓ 已完成`.

GREEN evidence:

- `LocalPreviewStore.consume()` now obtains the clock value inside the same
  lock immediately before expiry purge, session check, and one-time pop.
- The live controls and backend provenance use exact UTF-8 Chinese, and the
  test-only static result marker was removed. Terminal live metadata is derived
  from the verified state and includes the fresh source run plus
  `fixture_id=null` and `fixture_name=null` without replay fixture copy.
- Focused UI/local-live/callback suite: `30 passed`.
- Real Microsoft Edge review case: `1 passed, 19 deselected`; it opened the real
  report and citation/download tabs and verified report content, citations, and
  an enabled evidence-bundle download.
- Full browser gate: `20 passed, 22 deselected`.
- Ruff and `git diff --check` passed; production UI source contains none of the
  reviewed mojibake fragments; final server audit reported `SERVE_COUNT=0`.
