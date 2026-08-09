---
phase: 07-real-input-privacy-ui
reviewed: 2026-08-09T15:54:57Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - scripts/assert-phase7-frozen-scope.ps1
  - scripts/assert-phase7-red.ps1
  - scripts/run-phase7-real-input-qa.ps1
  - scripts/verify-phase7-security-scope.ps1
  - src/debugmate/privacy/models.py
  - src/debugmate/privacy/text_redactor.py
  - src/debugmate/ui/app.py
  - src/debugmate/ui/local_live.py
  - src/debugmate/ui/presentation.py
  - src/debugmate/ui/serve.py
  - tests/diagnosis/test_extraction_providers.py
  - tests/diagnosis/test_workflow_e2e.py
  - tests/privacy/test_models.py
  - tests/privacy/test_preview_integration.py
  - tests/ui/test_app.py
  - tests/ui/test_browser.py
  - tests/ui/test_local_live.py
  - tests/ui/test_real_input.py
  - tests/ui/test_view_state.py
findings:
  critical: 0
  warning: 6
  info: 0
  total: 6
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-08-09T15:54:57Z
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

The reviewed privacy models, local preview authority, loopback UI, PowerShell gates, and Phase 07 tests are generally defensive and fail closed at many important boundaries. The non-browser, non-OCR scoped suite completed with 201 passing tests and 31 deselected tests. Six warnings remain: formal evidence identities are synthetic rather than observed, the promotion gate does not validate several ledger claims, raw uploads have no explicit deletion lifecycle, failed request publications retain stale correction lease authority, the security scan omits changed scripts and configuration, and legacy browser tests target a removed UI label.

## Warnings

### WR-01: Formal evidence identity hashes are synthetic fixtures, not current-run observations

**File:** `tests/ui/test_browser.py:629-653`
**Issue:** `_phase7_ledger_fixture()` computes `case_id_sha256`, `source_run_id_sha256`, and `result_id_sha256` from strings such as `"P7-VQ-07:case"`. `_capture_phase7_evidence()` then promotes those values unchanged for real Edge captures. The committed P7-VQ-07 ledger therefore contains hashes that exactly match the scenario fixture strings rather than the replay result displayed during that run. This breaks the intended traceability between the screenshot, ledger, and actual result identity, and gives non-applicable idle scenarios apparently valid case/run/result hashes.
**Fix:** Populate identity hashes only from server-verified identities observed for the captured session. For states where an identity does not exist, change the ledger contract to use explicit `null` values (or omit those fields) and validate that mapping per scenario. Do not generate identity-like hashes from scenario labels.

### WR-02: The formal promotion gate accepts unvalidated semantic ledger claims

**File:** `scripts/run-phase7-real-input-qa.ps1:63-80`
**Issue:** `Assert-Phase7EvidenceSet` checks the top-level key allowlist, viewport dimensions, overflow flag, hashes, PNG header, and timestamp, but never constrains `privacy_state`, `result_status`, `mode`, `ocr_backend`, or `ocr_status`. It also does not require `viewport` to contain exactly `width` and `height`. A staging producer can therefore write arbitrary or contradictory semantic claims and still pass the final promotion gate as long as the filenames and hashes are valid. Browser-side assertions are not an independent trust boundary for the artifact promotion step.
**Fix:** Add a scenario-to-expected-values map in the PowerShell validator and enforce exact values and types for all semantic fields. Require `viewport` to contain exactly `width` and `height`, and validate cross-field combinations such as replay/completed and OCR unavailable/unavailable before promotion.

### WR-03: Raw screenshot uploads have no explicit deletion lifecycle

**File:** `src/debugmate/ui/app.py:1919-1935`
**Issue:** The callback confines and validates the Gradio cache path, then passes the raw screenshot to the preview builder, but neither the success path nor the OCR/error paths remove that raw cached upload. `serve.py` deliberately assigns a persistent project-local `GRADIO_TEMP_DIR`, so sensitive terminal screenshots can remain under `.debugmate-runtime/gradio-cache` after a redacted preview has been created or rejected. The current tests verify browser/path non-disclosure but do not verify deletion at rest.
**Fix:** Treat the validated upload as a short-lived source and delete it in a narrowly scoped `finally` block after preview construction has finished, including OCR failure paths. Verify the exact resolved path remains within the configured cache root immediately before deletion, and add tests proving successful preview, invalidation, and OCR failure leave no raw upload behind.

### WR-04: Identity-less request states retain stale correction lease authority

**File:** `src/debugmate/ui/app.py:652-680`
**Issue:** `_store()` updates `_lease_sources` only when the new state has an identity. Publishing a failed or fresh running request state after a completed result leaves the lease bound to the prior `source_run_id`. A focused reproduction shows that after publishing completed state A and then an identity-less failure, `publish_lease(lease, ..., A.source_run_id)` still succeeds. This makes the server authority registry disagree with the current session state and can authorize a stale correction flow if stale state inputs are replayed.
**Fix:** When `publish()` starts or publishes an identity-less top-level request state, explicitly clear that session lease's source binding before storing the state. Preserve the old binding only inside the intentional `publish_lease()` correction transition, where the expected prior source is checked atomically. Add a regression test covering completed -> failed/new-run -> stale correction publish.

### WR-05: The Phase 07 secret scan excludes changed scripts and configuration

**File:** `scripts/verify-phase7-security-scope.ps1:89-96`
**Issue:** The changed-file inventory is reduced to `src/*` and `evidence/ui/phase7/*`. Changed PowerShell scripts, platform DSL/configuration, and other executable source are never scanned, even though these are common places for API keys, local paths, and credentials to be introduced. The gate can report zero findings while a changed Phase 07 script contains a production secret.
**Fix:** Scan all changed reviewable text/source files, including `scripts/*` and platform/config files, with narrowly documented exclusions for generated/binary artifacts. Keep synthetic test-secret exceptions exact and line-scoped rather than excluding the whole test or script category.

### WR-06: Legacy browser helpers target a UI disclosure label that no longer exists

**File:** `tests/ui/test_browser.py:1348-1352`
**Issue:** `_open_example()` and several direct assertions still search for `"查看示例"`, while the reviewed app now labels the disclosure `"演示回放（独立模式）"`. Every browser test that calls `_click_replay()` through this helper will time out before exercising its actual assertions; additional stale references occur at lines 1390, 2441, 3253, 3270, 3465, and 3504. The Phase 07 runner's `-k` filter hides most of this regression, but the full browser suite is no longer reliable.
**Fix:** Centralize the disclosure label or stable selector in one test constant and update the helper and direct assertions to the current label. Run at least one existing non-Phase-07 replay browser test to ensure the shared helper remains valid.

---

_Reviewed: 2026-08-09T15:54:57Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
