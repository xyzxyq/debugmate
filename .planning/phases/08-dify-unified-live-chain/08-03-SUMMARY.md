---
phase: 08-dify-unified-live-chain
plan: 03
subsystem: cloud-adapter
tags: [dify, httpx, pillow, pydantic, yaml, tdd]

requires:
  - phase: 08-dify-unified-live-chain
    plan: 01
    provides: strict run-envelope, usage, failure and fingerprint contracts
  - phase: 07-real-input-privacy-ui
    provides: revision-bound approved redacted screenshot identity
provides:
  - exact HTTPS Dify origin and bounded non-duplicating blocking transport
  - immutable approved screenshot byte upload with exact singular image_input
  - deterministic direct-retrieval sanitizer and same-run Dify envelope DSL
affects: [08-04, 08-05, 08-06, 08-07]

tech-stack:
  added: []
  patterns:
    - connect-only retry with ambiguous post-dispatch failures never replayed
    - one immutable screenshot snapshot drives rehash, decode, MIME verification and upload
    - direct Knowledge Retrieval output is sanitized before LLM and End publication

key-files:
  created:
    - tests/cloud/test_gateway.py
  modified:
    - src/debugmate/settings.py
    - src/debugmate/adapters/base.py
    - src/debugmate/adapters/dify.py
    - src/debugmate/gateway.py
    - platform/dify/app.dsl.yml
    - platform/dify/README.md
    - tests/cloud/test_settings.py
    - tests/cloud/test_dify_adapter.py
    - tests/platform/test_dify_dsl.py

key-decisions:
  - "Production bearer requests accept only the canonical Dify Cloud HTTPS application origin; test origins require an explicitly injected client."
  - "Workflow retries are limited to one proven connection-establishment failure; read, write and protocol ambiguity is terminal and uncertain."
  - "Historical C01-C07 remains capability evidence; the new run_envelope requires a fresh import, binding, export and live same-run check."

patterns-established:
  - "Bound before trust: response bytes are capped before JSON parsing and provider identifiers leave the adapter only as fingerprints."
  - "Approved image snapshot: root/link/regular-file checks precede one bounded read used for hash, Pillow verification and multipart upload."
  - "Same-run trace: the direct retrieval result passes through an allowlist/hit-cap sanitizer before diagnosis and envelope assembly."

requirements-completed: [KNOW-04, DIAG-02, EVID-01]
duration: 49min
completed: 2026-08-10
---

# Phase 08 Plan 03: Dify Adapter and Same-Run Envelope Summary

**A bounded Dify application boundary with immutable approved-image upload, connect-only retry, and a direct-retrieval same-run envelope**

## Performance

- **Duration:** 49 min
- **Started:** 2026-08-10T02:50:25Z
- **Completed:** 2026-08-10T03:39:12Z
- **Tasks:** 3
- **Files modified:** 16

## Accomplishments

- Restricted production bearer traffic to the canonical Dify HTTPS origin, disabled redirects, applied 10/30/95/5-second HTTPX timeouts, and bounded workflow JSON at 512 KiB before parsing.
- Limited automatic retry to one connect error/timeout; read, write and remote-protocol ambiguity dispatches exactly once and returns a safe typed uncertain failure.
- Replaced path-reopening upload with one root-confined, link-free, bounded immutable byte snapshot used for SHA-256, Pillow format verification, MIME selection and multipart upload.
- Locked image calls to singular `image_input={type:image, transfer_method:local_file, upload_file_id:...}` while text-only calls omit the key entirely.
- Added direct Knowledge Retrieval sanitization with four-hit cap, HTTPS/source/locator allowlists and 2,000-character summaries, then exported extraction facts, diagnosis, trace and contract identities in one `run_envelope`.
- Clarified that historical C01-C07 proves isolated capability only; this updated DSL still requires a fresh current live import/export/run check in Plan 08-07.

## Task Commits

1. **Task 1 RED: Dify transport safety contracts** - `afb56f3` (test)
2. **Task 1 GREEN: strict origin, bounded response and retry semantics** - `853837b` (feat)
3. **Task 2 RED: immutable upload and exact image-input contracts** - `bc27611` (test)
4. **Task 2 GREEN: approved immutable screenshot upload** - `f0a69fe` (feat)
5. **Task 3: direct retrieval same-run envelope DSL** - `2a02279` (feat)
6. **Aggregate compatibility fix** - `b5a9ba8` (fix)

## Files Created/Modified

- `src/debugmate/settings.py` - Canonical production Dify origin validation and no-I/O configuration readiness.
- `src/debugmate/adapters/base.py` - Strict envelope/usage result fields and immutable-image backend protocol.
- `src/debugmate/adapters/dify.py` - Bounded streaming transport, typed safe failures, fingerprints, upload contract and connect-only retry.
- `src/debugmate/adapters/fixture.py` - Runtime-protocol compatibility for immutable byte upload tests.
- `src/debugmate/gateway.py` - Approved screenshot confinement, link/reparse rejection, one-read verification and exact Dify input shape.
- `src/debugmate/dify_live_evidence.py` - Explicit validation of historical C06 through its immutable independent re-export after the authoritative DSL evolves.
- `platform/dify/app.dsl.yml` - Direct retrieval sanitizer and one named same-run `run_envelope` End output with remote dataset binding removed.
- `platform/dify/README.md` - Capability/product-evidence distinction and required fresh Phase 08 live checks.
- `tests/cloud/test_settings.py` - Origin and no-I/O construction contracts.
- `tests/cloud/test_dify_adapter.py` - Timeout, cap, retry, status, upload, fingerprint and leak adversarial coverage.
- `tests/cloud/test_gateway.py` - Immutable bytes, MIME, input shape, replacement, link and oversize coverage.
- `tests/platform/test_dify_dsl.py` - Static same-run trace/envelope and historical C06 evolution contracts.
- `tests/privacy/test_approval_gateway.py` and `tests/privacy/test_preview_integration.py` - Existing approval-path fixtures migrated to immutable bytes.
- `tests/diagnosis/test_generation_repair.py` and `tests/test_probe_cli.py` - Legacy assertions migrated to strict origin and fingerprint behavior.

## Decisions Made

- Kept production origin validation in `DebugMateSettings`; alternate origins are possible only through `DifyBackend(test_base_url=...)` with an injected test client, preventing environment-controlled bearer forwarding.
- Kept the raw upload ID transient only long enough to build the current workflow request; returned evidence fields contain its SHA-256 fingerprint instead.
- Removed the remote dataset binding value from the committed DSL. Importers must bind the verified dataset live, then export and revalidate the current semantic contract.
- Preserved historical C06 evidence files unchanged. Its validator uses the immutable independent re-export as the old semantic witness only when the specifically named authoritative DSL has genuinely evolved; arbitrary paths and same-semantic byte drift still fail closed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved stale Phase 7 validation paths**
- **Found during:** Task 2 read-first and focused verification
- **Issue:** The plan referenced removed files `src/debugmate/privacy/image_validation.py` and `tests/privacy/test_cloud_gate.py`.
- **Fix:** Loaded the live `privacy/image_models.py` contract and ran the approval/preview gateway suites that own the cloud gate behavior.
- **Files modified:** None for path resolution.
- **Verification:** Task 2 focused suite passed 70 tests.
- **Committed in:** N/A (execution-path adjustment only)

**2. [Rule 1 - Bug] Migrated strict adapter compatibility without exposing provider IDs**
- **Found during:** Plan-wide default offline regression
- **Issue:** Eleven legacy assertions/fixtures still expected the old path upload protocol, a fake production origin, raw run IDs, or revalidated historical C06 against the newly evolved authoritative DSL.
- **Fix:** Migrated protocols/fixtures and assertions to immutable bytes, explicit test-origin behavior and fingerprints; added a fail-closed historical-authoritative-path validation mode backed by the immutable independent re-export. Historical evidence files were not changed.
- **Files modified:** `src/debugmate/adapters/base.py`, `src/debugmate/adapters/fixture.py`, `src/debugmate/dify_live_evidence.py`, `tests/diagnosis/test_generation_repair.py`, `tests/platform/test_dify_dsl.py`, `tests/test_probe_cli.py`
- **Verification:** Affected regression group 109 passed; final default offline suite 1079 passed with 58 marker-deselected tests.
- **Committed in:** `b5a9ba8`

---

**Total deviations:** 2 auto-fixed (1 blocking path drift, 1 compatibility bug)
**Impact on plan:** Both changes were required to execute the written gates and preserve strict security/history semantics; no live call, media refresh or future-phase work was added.

## Issues Encountered

- The first combined aggregate command exceeded its 120-second tool window, and a standalone default run exceeded a later 300-second window. A single externally logged offline run established the 4:45 baseline and exposed 11 compatibility failures; after the bounded fix, the final run completed green in 5:04.
- Default pytest emits one existing Starlette/httpx deprecation warning from the installed dependency stack; it is unrelated to this plan and does not affect test outcomes.

## User Setup Required

None for this offline plan. A fresh Dify dataset binding, import/export and live run is intentionally deferred to the explicit Phase 08 live acceptance plan; no secret or quota was consumed here.

## Known Stubs

None. Static placeholder hits are Dify input-widget metadata and a test filename, not runtime data stubs.

## Verification Evidence

- Task 1 focused adapter/settings gate: 32 passed.
- Task 2 immutable gateway/adapter/approval gate: 70 passed.
- Task 3 DSL/envelope gate: 27 passed.
- Compatibility, command-safety and historical evidence gate: 109 passed.
- Scoped Ruff: all checks passed.
- Default offline regression: 1079 passed, 58 deselected, one dependency deprecation warning.
- Frozen Phase 9/10 media, deliverables and final screenshots: no diff.
- Raw dataset binding scan: absent; committed DSL uses an empty binding requiring live reconfiguration.

## Next Phase Readiness

- Ready for Plan 08-04 to consume the strict adapter envelope and durable receipt contracts in live orchestration.
- Current DSL requires the planned fresh Dify dataset binding/export/import/live verification before it can become Phase 08 product-chain evidence.
- Phase 9 evaluation and Phase 10 screenshots/PPTX/MP4/SRT remain untouched.

---
*Phase: 08-dify-unified-live-chain*
*Completed: 2026-08-10*
