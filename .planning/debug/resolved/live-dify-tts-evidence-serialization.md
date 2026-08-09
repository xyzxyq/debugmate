---
status: resolved
trigger: "The real Dify /text-to-audio endpoint is healthy, but live TTS evidence serialization fails when candidate.model_dump_json() tries to encode raw MP3 bytes as UTF-8 JSON."
created: 2026-08-09T11:04:57.7583292+08:00
updated: 2026-08-09T11:30:00+08:00
---

## Current Focus

hypothesis: Confirmed: the live-test helper serializes the private TTS transport candidate instead of a JSON-safe metadata projection, so Pydantic applies its default UTF-8 bytes serializer to valid MP3 bytes.
test: Human verification confirmed by the primary agent.
expecting: Resolved session is archived and its pattern is added to the knowledge base.
next_action: Archive this session and append the confirmed pattern without creating a commit.

## Symptoms

expected: The live Dify TTS gate accepts a real MP3 payload, writes and validates evidence, and passes without embedding raw audio bytes as UTF-8 JSON.
actual: Dify synthesis succeeds, then evidence serialization fails on raw bytes.
errors: "PydanticSerializationError at tests/results/test_tts_live.py:70 candidate.model_dump_json(): invalid UTF-8 sequence from MP3 byte 0xFF."
reproduction: "With DIFY env configured and TTS enabled, run worktree Python with PYTHONPATH=current/src: python -m pytest -q -m \"cloud and tts\" tests/results/test_tts_live.py"
started: First observable after enabling real Dify TTS on 2026-08-09; previous runs never reached a successful binary payload because cloud TTS was disabled.

## Eliminated

## Evidence

- timestamp: 2026-08-09T11:04:57.7583292+08:00
  checked: Working tree ownership boundaries
  found: .planning/STATE.md and platform/dify/app.dsl.yml already contain uncommitted changes.
  implication: Preserve both files and constrain edits to the live TTS test and this debug session.
- timestamp: 2026-08-09T11:04:57.7583292+08:00
  checked: Knowledge base keyword overlap
  found: No entry overlaps the MP3 bytes, UTF-8, Pydantic serialization symptom set by two or more keywords.
  implication: Treat this as a new data-shape/encoding investigation.
- timestamp: 2026-08-09T11:04:57.7583292+08:00
  checked: tests/results/test_tts_live.py
  found: _assert_live_candidate validates candidate.audio_bytes as MP3 and then calls candidate.model_dump_json() solely to check that recap text and the API-key variable name are absent.
  implication: Raw audio bytes are not needed for the evidence assertions and should not be JSON-serialized.
- timestamp: 2026-08-09T11:09:00+08:00
  checked: src/debugmate/results/tts/base.py and adjacent TTS tests
  found: AudioPayload intentionally carries bounded private audio_bytes; downstream public audio contracts omit raw bytes, and existing tests treat candidate bytes as transport data rather than JSON evidence.
  implication: The production contract is coherent; the serialization mistake is isolated to the live-test evidence assertion.
- timestamp: 2026-08-09T11:11:00+08:00
  checked: Exact pytest command via the shell-default Python
  found: C:/miniconda/python.exe lacks pytest, so execution stopped before test collection.
  implication: This is an interpreter-selection issue, not evidence about the reported application failure.
- timestamp: 2026-08-09T11:15:00+08:00
  checked: Exact cloud-and-TTS gate using the worktree virtual environment with current/src on PYTHONPATH
  found: Dify synthesis and MP3 assertions succeeded; candidate.model_dump_json then raised PydanticSerializationError because byte 0xFF at audio_bytes index 0 is invalid UTF-8.
  implication: The reported failure is reproduced and the serialization boundary hypothesis is confirmed.
- timestamp: 2026-08-09T11:22:00+08:00
  checked: Offline non-UTF-8 evidence regression and Ruff
  found: Regression test passed (1 passed) and Ruff reported All checks passed.
  implication: The metadata projection is JSON-safe and the changed test file remains lint-clean.
- timestamp: 2026-08-09T11:22:00+08:00
  checked: Exact live cloud-and-TTS gate after the fix
  found: 1 passed, 5 deselected in 6.63 seconds.
  implication: The real Dify MP3 path now completes both media validation and evidence leak assertions.
- timestamp: 2026-08-09T11:22:00+08:00
  checked: Adjacent offline TTS contract suite and diff hygiene
  found: tests/results/test_tts_chain.py passed 26 tests; git diff --check found no errors (only the repository's LF-to-CRLF warning).
  implication: Adjacent adapter, fallback, and private handoff behavior remains intact.

## Resolution

root_cause: tests/results/test_tts_live.py serialized the entire private AudioPayload for metadata leak assertions. Pydantic's default JSON bytes handling decodes bytes as UTF-8, but valid MP3 begins with arbitrary binary such as 0xFF, so successful live payloads fail serialization.
fix: Added a typed metadata-only evidence projection that excludes audio_bytes and an offline regression test using MP3-like non-UTF-8 bytes.
verification: Primary agent independently confirmed the real cloud marker (1 passed, 5 deselected in 6.93 seconds), regression plus adjacent TTS suite (27 passed), Ruff, and a clean diff check apart from the LF-to-CRLF warning.
files_changed: [tests/results/test_tts_live.py]
