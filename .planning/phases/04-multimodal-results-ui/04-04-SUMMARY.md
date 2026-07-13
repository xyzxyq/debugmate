---
phase: 04-multimodal-results-ui
plan: 04
status: complete
completed: 2026-07-13
requirements: [MULTI-03, MULTI-05]
---

# Plan 04-04 Summary: Verified audio recap and fallback chain

## Outcome

Implemented one deterministic, identity-bound six-unit Chinese recap and the fixed
`Dify -> edge-tts -> Windows SAPI` synthesis chain. Every accepted candidate is
size-bounded, signature-screened and verified by `ffprobe` as one mono, tag-free MP3 in
the inclusive course duration window. Failure retains the transcript separately and
returns a typed `tts_failed` partial result without a placeholder MP3.

## TDD commits

- `d65daa7` RED: safe recap contract.
- `e436b39` GREEN: deterministic privacy-scanned recap.
- `99a80e0` RED: real-media probe attacks.
- `9d903db` GREEN: bounded tag-free MP3 probe.
- `8cd3c25` RED: ordered fallback contract.
- `5850dea` RED: real local SAPI media gate.
- `e67e348` GREEN: adapters, process boundary, fallback and live gates.

## Security and degradation truth

- TTS adapters accept only `SafeRecapText`, an identity, a controlled target and a
  discrete rate profile. The chain rechecks recap privacy and complete identity before
  every adapter boundary.
- Attempt records contain only backend, rate, status, fixed safe code, duration and
  hash. They contain no recap value, credential, HTTP body, command line or absolute
  path.
- SAPI receives recap content through a controlled UTF-8 file. PowerShell uses a fixed
  repository-owned `-File` script; FFmpeg uses fixed argv with metadata and ID3/Xing
  suppression. Both subprocesses use `shell=False`.
- Only an out-of-range duration receives one deterministic current-backend rate retry.
  Transport, content and process failures fall through immediately.
- Dify response content type and byte size are bounded; edge uses the fixed
  `zh-CN-XiaoxiaoNeural` voice; no paid service or credential was created.

## Fresh real-local evidence

The required Windows marker executed the actual path
`Microsoft Huihui Desktop -> WAV -> FFmpeg MP3 -> ffprobe` and passed:

- backend: `sapi`
- voice: `Microsoft Huihui Desktop`
- rate profile / SAPI rate: `normal` / `2`
- duration: `45,035 ms`
- channels / codec: `1` / `mp3`
- bytes: `180,140`
- SHA-256: `9caf9f15cd359cc9fdbb8635a935df84777b875cc567bcbd146a5d8710c0824c`
- intermediate WAV cleanup: verified

The exact hash is fresh-run evidence and can change if the installed Windows voice or
encoder build changes; acceptance is always based on the public media probe.

## External gates

- Dify cloud TTS: **OPEN / clean skip** because `DIFY_API_KEY` is absent.
- edge-tts network TTS: **OPEN / clean skip** because
  `DEBUGMATE_ALLOW_NETWORK_TTS=1` was not explicitly enabled.

Neither external skip is represented as a pass. The offline and guaranteed local SAPI
paths remain independent from network availability.

## Verification

- `tests/results/test_recap.py`: 6 passed.
- `tests/results/test_media.py`: 18 passed with real FFmpeg fixtures.
- `tests/results/test_tts_chain.py`: 5 passed.
- `pytest -m tts tests/results/test_tts_live.py`: 1 passed, 2 explicit external skips.
- External marker selection: 2 skipped, 1 deselected.

