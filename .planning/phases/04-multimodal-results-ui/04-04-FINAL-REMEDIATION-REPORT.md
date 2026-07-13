---
phase: 04-multimodal-results-ui
plan: 04
status: resolved
review_base: 77ce92a
red_commit: 178d70e
green_commit: b8b8d38
---

# 04-04 Final Independent Review Remediation Report

## Scope and method

This report closes the final independent review against `77ce92a`. Each finding
started with an executable RED regression in `178d70e`; the minimal production
repair and its passing checks are in `b8b8d38`. The remote Dify and edge TTS gates
remain explicitly open when their credential/network preconditions are absent.

## Finding-to-control mapping

| Final finding | Implemented control | Reproduced and verified evidence | Status |
|---|---|---|---|
| `PATH` could select a fake FFmpeg/ffprobe; SAPI read mutable `SYSTEMROOT`. | `trusted_media_tools()` never calls `which` or uses `PATH`. It obtains Local AppData through the Windows known-folder API, accepts only the fixed WinGet 8.1 binary layout, verifies regular/no-reparse ancestry and the pinned SHA-256 for each executable. SAPI obtains the system directory with `GetSystemDirectoryW`, and accepts only its fixed PowerShell path. | `test_production_media_tools_ignore_path_shadowing`; `test_sapi_ignores_a_forged_systemroot_environment`; real SAPI run. | Resolved |
| A `model_construct` value could bypass complete recap validation at chain entry. | `validate_tts_request()` reparses raw model fields with `strict=True`, re-running the six-unit canonical join, SHA-256, privacy and request-identity checks. `TtsFallbackChain.synthesize()` performs this before any identity access or adapter call. | `test_chain_rejects_a_constructed_seven_unit_recap_before_any_adapter_call`; adapter validation regressions. | Resolved |
| A candidate root could traverse a Junction/reparse point before or during directory creation. | Only absolute roots are accepted. Existing ancestors are checked before `mkdir`; all ancestors are rechecked immediately after it, around temporary directory creation, before every adapter call and before/after final publication. Candidate and final paths must remain regular/no-reparse under that root. | `test_chain_rejects_nested_junction_root_before_adapter_or_outside_write` creates an actual Windows Junction to an outside directory and proves no adapter call and no outside write. | Resolved |
| The AST process guard allowed too many `Popen` shapes. | The sole audited process form is exactly `subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False)` in `media._run_bounded_process`. Any extra keyword, non-literal/missing false shell, different command expression or stream endpoint is rejected. | `test_process_allowlist_rejects_extra_or_wrong_popen_boundary_arguments`; repository process capability scan. | Resolved |

## Trusted-binary decision and boundary

The course host has the approved WinGet FFmpeg 8.1 executable hashes:

- `ffmpeg.exe`: `d1e2a156261ecc675081943197a85f08f2868784a0af499171ede89353edad31`
- `ffprobe.exe`: `70872c3ffbc43d0b2c570f9837f54d6e9a832f4ca25463e9735b6a3ec0621478`

This is intentionally fail-closed: an unpinned media package, a replacement file,
a symlink/Junction in its ancestry, or a changed executable timestamp/size is not
executed. A future approved tool upgrade requires a deliberate source review and
hash update; it does not silently fall back to `PATH`.

## Fresh local media evidence

After the final remediation, the required local SAPI path was run again:

`Microsoft Huihui Desktop -> WAV -> fixed FFmpeg argv -> MP3 -> fixed ffprobe argv`

- backend / voice / rate: `sapi` / `Microsoft Huihui Desktop` / `normal`
- duration / codec / channels: `45,035 ms` / `mp3` / `1`
- bytes / SHA-256: `180,140` / `9caf9f15cd359cc9fdbb8635a935df84777b875cc567bcbd146a5d8710c0824c`
- Dify: **OPEN / skipped** because `DIFY_API_KEY` is absent.
- edge: **OPEN / skipped** because `DEBUGMATE_ALLOW_NETWORK_TTS=1` was not set.

The local hash is fresh host evidence; acceptance remains based on the public
tag-free mono MP3 probe, not a hard-coded audio output hash.

## Final verification

- Focused review suite (`test_media`, `test_tts_chain`, `test_command_safety`):
  `81 passed`.
- Real local gate: `pytest -m tts tests/results/test_tts_live.py` returned
  `1 passed, 2 explicit external skips`.
- Full offline suite: `622 passed, 25 deselected`.
- `ruff check src/debugmate/results tests/results tests/diagnosis/test_command_safety.py`:
  passed.
- `pip check`: no broken requirements.
- `git diff --check HEAD~2..HEAD`: passed.
