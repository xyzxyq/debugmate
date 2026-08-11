---
phase: 08-dify-unified-live-chain
fixed_at: 2026-08-11T09:21:17Z
review_path: .planning/phases/08-dify-unified-live-chain/08-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-08-11T09:21:17Z
**Source review:** `.planning/phases/08-dify-unified-live-chain/08-REVIEW.md`
**Iteration:** 1

**Summary:**

- Findings in scope: 4
- Fixed: 4
- Skipped: 0
- Verification: 199 passed, 1 deselected; Ruff passed

## Fixed Issues

### WR-01: Remote DSL and retrieval fingerprints are parsed but never verified

**Files modified:** `src/debugmate/cloud/workflow.py`, `src/debugmate/ui/serve.py`, `tests/cloud/test_live_workflow.py`
**Commit:** e70ae6f
**Applied fix:** Bound every accepted live envelope to the locally approved DSL semantic SHA-256, recomputed the canonical `{case_id, hits}` retrieval fingerprint, and verified the versioned retrieval-sanitizer fingerprint with constant-time comparisons. Added negative regression coverage for independent mutation of all three identities.

### WR-02: Local dispatch validation can leave a receipt permanently `STARTED`

**Files modified:** `src/debugmate/gateway.py`, `src/debugmate/cloud/workflow.py`, `tests/cloud/test_live_workflow.py`
**Commit:** 7bcafe5
**Applied fix:** Split dispatch into a local `prepare_dispatch()` snapshot and network-only `dispatch_prepared()` operation. Approval, path, hash, byte, image, and MIME validation now completes before receipt creation. Added a replaced-screenshot regression proving no receipt or backend call occurs on local validation failure.

### WR-03: Live knowledge authority accepts a self-asserted manifest identity

**Files modified:** `src/debugmate/cloud/workflow.py`, `tests/cloud/test_live_workflow.py`, `tests/ui/test_dify_live.py`
**Commit:** cd0715e
**Applied fix:** Production construction now accepts only a repository build directory or its `manifest.json` and loads it through `validate_knowledge_build()`. Raw dictionaries are rejected; deterministic tests use an explicit prevalidated capability constructor. Added a real 17-document build test proving source-metadata tampering with an unchanged claimed build ID fails before Dify I/O.

### WR-04: Evidence capture defaults to an interpreter outside the current repository

**Files modified:** `scripts/capture_dify_c03_c04_c06.ps1`, `tests/platform/test_dify_live_evidence.py`
**Commit:** 4b53c57
**Applied fix:** Made `PythonPath` optional, defaulted it after repository-root resolution to `.venv\Scripts\python.exe`, retained explicit overrides, and required the resolved interpreter to be a regular file. Added a portable static contract regression and parsed the PowerShell script successfully.

---

_Fixed: 2026-08-11T09:21:17Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
