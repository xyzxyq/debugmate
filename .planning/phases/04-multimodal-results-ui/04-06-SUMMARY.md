---
phase: 04-multimodal-results-ui
plan: 06
status: complete
completed: 2026-07-13
requirements: [UX-01, UX-02, UX-03, UX-04]
---

# Plan 04-06 Summary: verified results application service and workbench

## Outcome

Delivered the Phase 4 application boundary and the native Windows-browser
workbench.  `ResultApplicationService` is the only UI facade for approved live
input, indexed replay, restore, correction, scoped retry and downloads.  The
Gradio page consumes strict view state and one-shot verified members only; it
does not accept outcome objects, paths, commands or shell input.

The loopback entry now builds the real deterministic Phase 4 chain for the
fixed replay fixture: verified source -> presentation/report/citations/card ->
recap/TTS fallback -> consistency gate -> immutable published result.  A fresh
isolated-runtime smoke run returned `completed`, `replay`, the expected
`module-not-found` fixture, a result ID and available audio.

## Delivered behavior

- Added a pure `ResultViewState -> ComponentViewModel` mapper for idle, all
  seven running stages, complete, partial, failed, replay and TTS fallback
  states.  The mapper never reads a file or calls a service.
- Extended `ResultViewState` with strict terminal `result_id` and
  identity-bound `audio`.  This was the approved minimal contract extension:
  it lets the pure mapper truthfully show result identity, audio backend and
  fallback facts without guessing from the filesystem.
- Added strict full-outcome persistence, fixture allowlisting, public result
  re-verification, immutable replay correction lineage, retry of verified
  partial bundles and one-shot `VerifiedDownload` capabilities.
- Added a compact native Gradio 6 three-region workbench, loopback-only CLI and
  `/config` readiness coverage.  No raw HTML, terminal/installer action,
  arbitrary path picker, upload or microphone boundary is present.
- Added six-field correction controls.  Field input changes only a local draft;
  the page presents the verified old -> new value summary, and only the
  explicit `创建新运行` action calls the service with `confirmed=True`.
- Materializes report/card/audio/archive only after a fresh verified member
  resolution.  Any download/media revalidation error clears component paths and
  shows only a fixed safe failure state.

## Replay recovery remediation

The isolated end-to-end replay smoke test found two production seams that the
initial structural tests did not exercise:

- A composition failure after a fixture had been verified discarded its
  fixture ID/name while returning a replay failure state.  That violated the
  strict replay identity invariant.  The service now retains the identity only
  after the index row has passed validation; unverified fixture input remains a
  non-replay safe failure and cannot invent lineage.
- The loopback composer passed the TTS request with the wrong keyword.  It now
  follows the fixed positional `TtsFallbackChain.synthesize(recap, request,
  candidate_root)` contract.

Both fixes were written from RED tests and the smoke was re-run successfully.

## Security boundaries

- UI callbacks expose strict IDs/drafts and verified bytes, never raw source
  records, filesystem paths or exception text.
- Replay is marked independently from result status and carries fixture/source
  provenance through state, manifest and download metadata.
- Correction rereads the strict stored outcome and verified source before it
  can create a distinct source run/result; original bundles remain immutable.
- The local result cache contains only server-issued derived member copies;
  failed verification removes them before the callback responds.
- The TTS chain uses configured Dify, edge and Windows SAPI adapters with
  bounded fallback behavior.  A missing cloud key remains a normal fallback
  condition, not a fabricated cloud success.

## TDD commits

- `0bdf34e` / `9ff01a4`: result-view RED/GREEN matrix and pure mapping.
- `db98176` / `9de2af0`: replay service safety boundary and facade.
- `b59738f`, `ebea4fb`, `0513360`: live/replay correction lineage and partial
  retry coverage.
- `18ab844`, `103c868`, `a1b0e4b`: native app and loopback server contract.
- `a46b520`, `09853b1`, `4f8cc40`: verified callback/download boundary.
- `2018495` / `a2470f3`: local correction draft and explicit confirmation.
- `b5c8463`, `5a97870` / `f14da96`: configured replay composer and smoke-found
  replay/TTS-contract recovery.

## Verification

- `python -m pytest -q tests/ui/test_callbacks.py` — 4 passed.
- `python -m pytest -q tests/ui tests/results/test_service.py` — 28 passed.
- `python -m pytest -q -m "not cloud and not ocr and not network and not browser and not tts"`
  — **699 passed, 27 deselected** in 94.08 seconds.
- `python -m ruff check .` — passed.
- `python -m pip check` — passed.
- `git diff --check` — passed.

## Independent-review remediation (I1-I4)

The independent review found four important gaps after the first delivery.  Each
was reproduced first and repaired in a separate RED/GREEN sequence:

- **I1 — persistent replay lineage:** `d3e11ee` / `b39a8fe`.  A restarted
  service no longer depends on the in-memory `_run_results` cache to determine
  correction provenance.  It locates only strict `result_*` records under the
  factory-issued result root, verifies every candidate manifest, requires one
  mode/fixture provenance tuple for the parent source run, and then restores
  that source.  A replay-derived correction therefore remains replay-labelled
  across restart and a second correction; an unverified or ambiguous parent
  becomes a safe failure rather than live provenance.
- **I2 — UI content TOCTOU:** `4346993`, `4ce7759` / `5354801`.  Native media
  and download components no longer receive a mutable temporary-file path.
  A `VerifiedDownload` is consumed once into bounded server memory with its
  SHA-256, MIME type, filename and a 128-bit opaque token.  The Gradio app
  serves `/debugmate-content/<token>` by rechecking the in-memory bytes before
  each response; image/audio use the token URL and DownloadButton uses the same
  URL with an attachment header.  There is no user path, cache directory or
  reopen-after-authorization boundary.
- **I3 — seven-stage UI progress:** `1d87030` / `37b2e32`.  Stage-aware result
  composition emits actual `source`, `presentation`, `report`, `card`,
  `audio`, `consistency`, `publish` completion events.  The service rejects
  out-of-order emissions, streams strict `ServiceStageEvent` running state from
  a worker, and the Gradio callback generator maps each event through the pure
  view mapper before applying the atomic component update.
- **I4 — complete verified UI payload:** `733e873`.  The result allowlist adds
  only fixed `diagnosis` and `recap_text` members.  The callback parses the
  freshly verified strict diagnosis into an explicit redacted-input summary,
  category/confidence, fact/evidence rows and citation rows, and displays the
  verified recap transcript.  Missing/invalid detail falls back to fixed empty
  UI state without exposing a filesystem path or raw exception.

Fresh review-remediation checks:

- I1 focused restart correction plus existing replay correction: 2 passed.
- I2 callbacks, including an ASGI TestClient GET of the opaque content URL:
  4 passed.
- I3 focused ordered seven-stage service event plus UI checks: 9 passed.
- I4 UI/service callback and structural checks: 15 passed.
- Final offline suite:
  `python -m pytest -q -m "not cloud and not ocr and not network and not browser and not tts"`
  — **701 passed, 27 deselected** in 98.10 seconds.  The run has one
  Starlette TestClient/httpx deprecation warning; it is not a test failure or
  a runtime/provider error.
- `python -m ruff check .`, `python -m pip check`, and `git diff --check` — passed.

## External gate

The fixed offline replay demonstration is complete without credentials.  Live
diagnosis remains intentionally unavailable until the separately planned Dify
workflow/platform gate supplies a configured workflow and approved redacted
input; no paid key, provider setup or cloud-success claim was introduced by
this plan.
