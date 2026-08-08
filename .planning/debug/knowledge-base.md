# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## cloud-probe-c05-semantic-mismatch — Cloud probe omitted formal generation context and flattened capability states
- **Date:** 2026-08-08
- **Error patterns:** cloud-probe, status_counts fail 7, evidence_set_mismatch, fact_set_mismatch, routing_mismatch, empty facts, empty evidence, category unknown
- **Root cause:** `run_cloud_probe` sent only `case_id`/`file_id` instead of the formal `GenerationRequest` required by local semantic validation, and broad exception handlers rebuilt all seven capability statuses uniformly, erasing completed upload evidence and misclassifying unexecuted capabilities.
- **Fix:** Send `generation_request` in the initial Dify workflow inputs, validate the returned candidate against the same request object, and maintain per-capability status/evidence across upload, workflow, validation, and error stages.
- **Files changed:** `src/debugmate/probe.py`, `tests/test_probe_cli.py`
---
