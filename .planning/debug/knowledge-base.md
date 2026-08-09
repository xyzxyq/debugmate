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

## live-dify-tts-evidence-serialization — Live TTS evidence serialized raw MP3 bytes as UTF-8 JSON
- **Date:** 2026-08-09
- **Error patterns:** Dify TTS, PydanticSerializationError, invalid UTF-8 sequence, MP3 bytes, audio_bytes, model_dump_json
- **Root cause:** `tests/results/test_tts_live.py` serialized the entire private `AudioPayload` for metadata leak assertions. Pydantic's default JSON bytes handling decodes bytes as UTF-8, but valid MP3 begins with arbitrary binary such as `0xFF`.
- **Fix:** Serialize a typed metadata-only projection that excludes `audio_bytes`, with an offline regression test using MP3-like non-UTF-8 bytes.
- **Files changed:** `tests/results/test_tts_live.py`
---
