# Deferred Items

## 2026-08-09 — Plan 07-04 full-suite baseline failures

- `tests/diagnosis/test_command_safety.py` rejects the pre-existing `subprocess` import in `src/debugmate/dify_live_evidence.py`.
- The Phase 07 `PreviewBundle.screenshot_audit` cross-stage test-factory regression was fixed in `8228fbf`; the full suite now has only the command-safety baseline failure (`913 passed, 1 failed, 92 deselected`).
- Plan-scoped UI/presentation verification is green (`72 passed`), Ruff is green, and the Phase 07 frozen-scope gate passes.
