---
phase: 04-multimodal-results-ui
plan: 07
status: in_progress
updated: 2026-07-13
scope: verification_only
---

# Plan 04-07 Execution Log

This is execution evidence for the later independent verifier. It is not a
phase verdict and does not pre-create `04-VERIFICATION.md`.

## Task 1 — five-state E2E and public-boundary abuse matrix

HEAD before Task 2 gates: `bb2bf39`.

```text
.venv\Scripts\python.exe -m pytest -q tests\results\test_result_e2e.py tests\results\test_security_abuse.py
19 passed in 27.25s
```

- `test_result_e2e.py` covers completed, `png_layout_failed` partial,
  `tts_failed` partial, source-invalid failure, and allowlisted replay. Each
  successful state is reread by `verify_result_bundle`, restored via the public
  service, and where eligible resolved through the one-shot download boundary.
- The completed fixture uses a test-only fake SAPI adapter. Its 45-second tone
  MP3 is generated with the repository's pinned FFmpeg executable and then
  passes the real production canonicalisation, ffprobe, publish and archive
  checks. It is explicitly offline fixture media, not cloud success evidence.
- `test_security_abuse.py` has one executable public-boundary test for each
  `T4-01` through `T4-14`.

## Task 2 — blocking offline, schema, artifact and secret gates

```text
.venv\Scripts\python.exe -m pytest
725 passed, 27 deselected, 1 warning in 128.99s

.venv\Scripts\python.exe -m ruff check src tests
All checks passed!

.venv\Scripts\python.exe -m pip check
No broken requirements found.

git diff --check
passed
```

The only pytest warning was the existing Starlette TestClient/httpx
deprecation warning. It is neither a provider run nor a test failure.

### Strict result contract export and canonical-current-data round trip

The following strict result models each exported their current JSON Schema,
survived deterministic JSON serialization/deserialization, and revalidated a
canonical current instance. Schema hashes are SHA-256 over canonical JSON:

| Model | Schema SHA-256 |
|---|---|
| `ArtifactIdentity` | `3aef64f4eaf0f730d13aa04f06cb3cc7fc7e36a0853e59d119812df01576d474` |
| `ArtifactAvailability` | `9a806e59f9e661dde12ff2cc1d406d9d656d9a8b9f4ddbf27a18d3eb9a3935fa` |
| `ArtifactRecord` | `0d0650ba1fca822fbdbe0a6079975a9b7f724635a2ad9c018c189ee9b76b6731` |
| `AudioAttempt` | `62dda618ad9dfa0bd3f8ea2d802601c2ee60f5f9249f184f1ea3bee404480224` |
| `AudioResult` | `2134ee5b599b6f1beb5b26c2e0b4e1af944eae4b110ee42679aa555dc5092b46` |
| `SafeFailure` | `95950c8b25fe7da803aec86f581a4901c196124b294ff7ec98bd5c04352c6872` |
| `ResultManifest` | `c3555d5ecb65cae30c92ee91678121f0665e7a00c47dd93e54478f4f2c38887e` |
| `ResultViewState` | `e9fe35c1ca0224681306b5e96d65a4f227ead366306ce0b146c0a7de8466b48c` |

Fresh public-verifier probes emitted these value-safe identities:

| Bundle | Result ID | Archive SHA-256 |
|---|---|---|
| full | `result_1ae6b1cbe706406a0c0bd1060b698be6` | `e3fdb07ad1ff68bdf3300b33ef060fdcb8949b588b32af35e432461fcd6be9c4` |
| TTS partial | `result_cf1bce544cfa8861e2a7b2f2e6a8ed06` | `7ec61e4b83994e45cd90a622d3070b7b2f67e0441de0341918c7f157c1dadfca` |

```text
.venv\Scripts\python.exe -m pytest -q tests\results\test_publisher.py -k "independent_full_rebuilds or publish_audio_partial or verifier_and_download or zip_bomb_metadata"
4 passed, 18 deselected in 3.55s
```

This selection covers independent-root byte-identical deterministic ZIP output,
fresh full/partial publication, public download revalidation, and metadata-first
ZIP-bomb rejection before member decompression.

```text
git grep -n -I -E "SECRET_SENTINEL_DO_NOT_LOG|sk-[A-Za-z0-9_-]{8,}|BEGIN( [A-Z0-9]+)* PRIVATE KEY|20795" -- src contracts fixtures knowledge prompts platform scripts README.md pyproject.toml
PRODUCT_SECRET_SCAN=clean
```

The scan intentionally excludes planning, tests, and generated visual evidence;
it does not exclude product source, contracts, fixtures, knowledge, prompts,
platform files, scripts, README, or project configuration.

## Pending gates

- Task 4: real loopback Edge/Playwright VQ-01..VQ-15 evidence and final rerun.
- Independent Phase 4 verification remains pending and must be performed by a
  separate verifier after this execution plan is complete.

## Task 3 — real local media and truthful external gates

```text
.venv\Scripts\python.exe -m pytest -q -m tts tests\results\test_tts_live.py
3 passed, 2 skipped in 8.66s

.venv\Scripts\python.exe -m pytest -q -m "(cloud or network) and tts" tests\results\test_tts_live.py
2 skipped, 3 deselected in 1.17s
```

The three passing local-marker checks exercise the current Windows SAPI output,
the nested Junction attack boundary, and the real leased candidate plus
FFmpeg/ffprobe chain. The fresh value-safe media record is
`evidence/media/phase4/local-sapi.json`:

| Field | Observed value |
|---|---|
| backend / voice / rate | `sapi` / `Microsoft Huihui Desktop` / `normal` |
| fallback path | Dify and edge failed safely; SAPI was the final backend |
| MP3 format | 45,144 ms, mono, 180,576 bytes, decode exit `0` |
| SHA-256 | `10fb8c17b2c1c31b51055a71fa223deeb9ae9412f0f9218c1936bd4b933f0db6` |
| automatic audio signals | non-silent PCM; 0 full-scale clipping samples; peak 24,908 |
| human listening | `human_needed` — no agent claim of intelligibility is made |

| External gate | Current command result | Truthful status |
|---|---|---|
| Dify TTS | `DIFY_API_KEY` absent | clean-skipped / **open** |
| edge-tts | `DEBUGMATE_ALLOW_NETWORK_TTS` not `1` | clean-skipped / **open** |
| local SAPI | current-code marker + fresh ffprobe/decode record | passed, with separate human listening check pending |

No key, provider response body, recap text, or temporary path is retained in
the media evidence or this log.

## Task 4 — browser gate stopped by VQ-01

The project-pinned `playwright==1.61.0` successfully launched the explicit
`msedge` channel and navigated to the real loopback Gradio server.  The browser
harness uses `domcontentloaded` plus an explicit `.gradio-container` wait;
`networkidle` is intentionally not used because Gradio retains a queue
connection while healthy.

```text
.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py
FAILED tests/ui/test_browser.py::test_vq_01_real_loopback_workbench_has_three_visible_regions
actual widths: [67, 67, 67]
expected minima: [280, 360, 440]
```

The test captured a real current-app screenshot before asserting the failure:
`evidence/ui/phase4/VQ-01.png` SHA-256
`12be2e55e45f78ddee0f8c6cdbc9cce4ffdd4c494192d63c2c22c6ef61fd10cc`.
The nested grid collapse makes the fixed replay selector inaccessible, so the
remaining VQ rows cannot be honestly accepted. See `04-07-GAPS.md` GAP-01.
No source or CSS was changed in this verification-only plan.
