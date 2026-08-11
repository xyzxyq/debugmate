---
phase: 08-dify-unified-live-chain
reviewed: 2026-08-11T09:09:07Z
depth: standard
files_reviewed: 41
files_reviewed_list:
  - fixtures/replay/module-not-found/outcome.json
  - platform/dify/README.md
  - platform/dify/app.dsl.yml
  - scripts/build_knowledge.ps1
  - scripts/capture_dify_c03_c04_c06.ps1
  - scripts/export-phase8-tracked-inventory.ps1
  - src/debugmate/adapters/base.py
  - src/debugmate/adapters/dify.py
  - src/debugmate/cli.py
  - src/debugmate/cloud/contracts.py
  - src/debugmate/cloud/receipts.py
  - src/debugmate/cloud/workflow.py
  - src/debugmate/diagnosis/workflow.py
  - src/debugmate/dify_live_evidence.py
  - src/debugmate/gateway.py
  - src/debugmate/knowledge/sync.py
  - src/debugmate/results/contracts.py
  - src/debugmate/results/loader.py
  - src/debugmate/results/publisher.py
  - src/debugmate/results/service.py
  - src/debugmate/results/verifier.py
  - src/debugmate/settings.py
  - src/debugmate/ui/app.py
  - src/debugmate/ui/presentation.py
  - src/debugmate/ui/serve.py
  - tests/cloud/test_dify_adapter.py
  - tests/cloud/test_gateway.py
  - tests/cloud/test_live_workflow.py
  - tests/cloud/test_receipts.py
  - tests/cloud/test_run_envelope.py
  - tests/cloud/test_settings.py
  - tests/diagnosis/test_generation.py
  - tests/knowledge/test_coverage_sync.py
  - tests/knowledge/test_dify_readback.py
  - tests/platform/test_dify_dsl.py
  - tests/platform/test_dify_live_evidence.py
  - tests/results/test_backend_provenance.py
  - tests/results/test_result_e2e.py
  - tests/results/test_service.py
  - tests/test_probe_cli.py
  - tests/ui/test_dify_live.py
findings:
  critical: 0
  warning: 4
  info: 0
  total: 4
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-08-11T09:09:07Z  
**Depth:** standard  
**Files Reviewed:** 41  
**Status:** issues_found

## Summary

The Phase 08 Dify live chain, knowledge synchronization, result publication, and UI integration were reviewed at standard depth. The targeted test suite passed (`193 passed, 1 deselected`), and no critical vulnerability was found. Four correctness and evidence-integrity gaps remain: remote provenance fields are accepted without local binding, a pre-dispatch validation failure can strand a receipt, the live knowledge manifest bypasses the repository's strict build verifier, and the evidence capture script defaults to a machine-specific stale worktree interpreter.

## Warnings

### WR-01: Remote DSL and retrieval fingerprints are parsed but never verified

**File:** `src/debugmate/cloud/workflow.py:202-240`  
**Issue:** `_validate_envelope()` checks the schema, prompt, and knowledge build identifiers, but it never compares `envelope.contract.dsl_semantic_sha256` with the locally approved DSL identity. It also discards `retrieval_trace.run_fingerprint` and `node_fingerprint` while rebuilding the local trace. A stale or different Dify workflow can therefore return a structurally valid envelope and be accepted as the current same-run chain, even though the two provenance fingerprints do not bind it to the approved DSL or to this case's exact retrieval payload.

**Fix:** Inject the expected DSL semantic hash into `DifyLiveWorkflow`, compare it with `secrets.compare_digest`/`hmac.compare_digest`, recompute the run fingerprint from the canonical `{case_id, hits}` payload, and compare the node fingerprint with the versioned retrieval-sanitizer identity before constructing `RetrievalTrace`. Add negative tests that mutate each of the three fingerprints while leaving the diagnosis and build ID valid.

### WR-02: Local dispatch validation can leave a receipt permanently `STARTED`

**File:** `src/debugmate/cloud/workflow.py:267-324`  
**Issue:** The receipt is persisted before `CloudGateway.run_live()`, but the dispatch block handles only `DifyAmbiguousTransportError` and `DifyError`. `run_live()` can still raise `ApprovalInvalid` while resolving, hashing, decoding, or MIME-checking an approved screenshot, and can raise local contract/type errors before network dispatch. Those exceptions escape without a terminal receipt update. The receipt identity then blocks every retry as a duplicate, leaving an immutable `STARTED` record and no truthful terminal evidence.

**Fix:** Split `CloudGateway` into a local `prepare_dispatch()` step that validates and snapshots the approved bytes before `begin()`, followed by a network-only dispatch using that immutable snapshot. Alternatively, catch all explicitly classified pre-dispatch validation errors after `begin()` and finish the receipt with a dedicated safe failure code. Add a live-workflow test using a replaced/invalid approved screenshot and assert that no receipt is stranded in `STARTED`.

### WR-03: Live knowledge authority accepts a self-asserted manifest identity

**File:** `src/debugmate/cloud/workflow.py:92-103`  
**Issue:** `_strict_manifest()` only JSON-round-trips the value and checks that `sources` is a list of length 17. It does not use the existing `validate_knowledge_build()` boundary, recompute `build_id`/`content_hash`, verify note hashes, require the exact manifest shape, or reject unsafe manifest paths. Because the manifest later authorizes retrieval evidence, a locally modified manifest that retains the attested `build_id` can change the allowed source metadata while still being treated as the sealed build.

**Fix:** Load live authority through `debugmate.knowledge.build.validate_knowledge_build()` and retain its validated immutable snapshot. Require a repository build directory/path in production; if dictionary injection is needed for tests, expose a separate test-only constructor that accepts an already validated capability rather than raw JSON. Add a test that changes source metadata without changing the claimed build ID and verify construction fails before any Dify call.

### WR-04: Evidence capture defaults to an interpreter outside the current repository

**File:** `scripts/capture_dify_c03_c04_c06.ps1:2`  
**Issue:** The default `PythonPath` is an absolute path into `.worktrees/phase-1-foundation-platform-gate`. A normal clone, moved workspace, or cleaned worktree fails at `Resolve-Path`; when the old worktree still exists, the script silently uses that environment instead of the current repository's `.venv`. This makes the Phase 08 evidence procedure non-portable and can mix current source via `PYTHONPATH` with stale dependencies from another worktree.

**Fix:** Make `PythonPath` optional and, after resolving `$repositoryRoot`, default it to `Join-Path $repositoryRoot '.venv\Scripts\python.exe'`. Keep an explicit override for controlled environments and validate the resolved interpreter is a regular file before capture.

---

_Reviewed: 2026-08-11T09:09:07Z_  
_Reviewer: Claude (gsd-code-reviewer)_  
_Depth: standard_
