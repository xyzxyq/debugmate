---
phase: 04-multimodal-results-ui
plan: 04
status: resolved
review_base: 1c8a40d
remediation_commits: [de33ca0, a588510]
---

# 04-04 Independent Review Remediation Report

## Scope and decision

This report closes the independent review findings against the post-review state
starting at `1c8a40d`. Every change below began with a focused failing regression
test, then received the minimum implementation change and a targeted re-run. The
remote Dify and edge gates remain deliberately **open** when their explicit
credential/network preconditions are absent; they are not represented as passed.

## Finding-to-control mapping

| Finding | Current control | Regression evidence | Status |
|---|---|---|---|
| Process AST policy exempted entire modules | `test_command_safety.py` now permits only the audited `media.py` `subprocess.Popen(command, stdin, stdout, stderr, shell=False)` structure. It rejects every other subprocess API, missing/non-literal `shell=False`, direct subprocess imports, `os.system`, `os.spawn*`, `os.exec*`, and `os.startfile`. SAPI no longer owns a direct subprocess call. | `test_process_allowlist_is_call_precise_and_requires_literal_shell_false`; `test_process_audit_detects_direct_os_imports_and_process_families`; repository-wide source scan | Resolved in `de33ca0` |
| Direct adapter use could bypass the safe recap contract | All adapters call `validate_tts_request`, which strictly revalidates `SafeRecapText`, scans its text, checks canonical units/hash, and binds request identity before any network or process boundary. | `test_all_adapters_reject_constructed_secret_and_mismatched_identity`; live-gate `_assert_value_free_rejection` | Already present, rechecked |
| Fallback order or retry could drift | `TtsFallbackChain` only accepts the exact `dify`, `edge_tts`, `sapi` tuple. It retries only `duration_out_of_range` once with the fixed faster profile, otherwise falls through. | `test_chain_rejects_missing_duplicate_custom_or_reordered_backends`; `test_duration_failure_retries_once_then_falls_through`; `test_non_duration_failure_never_retries_and_all_failed_is_partial` | Already present, rechecked |
| Candidate metadata/path might be forged | Candidate acceptance requires the temporary expected path, exact backend, rate, request identity, regular non-reparse file and an initial bounded public probe. A directory substituted at the candidate path is recorded as `tts_candidate_invalid` without leaking a path. | `test_chain_rejects_external_or_identity_mismatched_candidate`; `test_directory_candidate_is_a_value_free_invalid_attempt` | Resolved in `a588510` |
| Appended/trailing payload could be published | A candidate first passes `probe_mp3`, then `canonicalize_mp3` re-encodes only the first audio stream into the tag-free profile, and the final path is probed again before its hash/duration are published. | `test_canonicalize_reencodes_tagged_mp3_and_drops_trailing_secret`; `test_chain_canonicalizes_a_verified_candidate_before_publication` | Resolved in `de33ca0` |
| Process output could become unbounded Python memory | `media._run_bounded_process` sends stdout/stderr to temporary files, then reads only `max_output_bytes + 1`; `ffprobe`, canonical FFmpeg, SAPI PowerShell, and SAPI FFmpeg all use it. | `test_ffprobe_output_is_file_bounded_before_python_memory`; `test_sapi_uses_bounded_file_boundary_and_never_places_recap_in_argv` | Resolved in `de33ca0` |
| SAPI could trust injected roots/binaries/scripts | Constructor only accepts the resolved repository root, fixed `powershell.exe` under `%SYSTEMROOT%\\System32`, and an absolute resolved regular `ffmpeg.exe`; the repository script is checked as an in-root regular, non-link/reparse file. The PowerShell script has a fixed `-File` boundary, constrained voice/rate, and receives recap only through its UTF-8 file. | `test_sapi_rejects_untrusted_executable_or_script_roots_without_echoing_values`; `test_sapi_rejects_a_non_regular_resolved_ffmpeg_binary`; real local marker | Resolved in `de33ca0` and `a588510` |
| Canonicalization or final probing could escape the fallback | Candidate probe, canonicalization, and final probe now sit in the same attempt boundary. A safe media error records `audio_invalid` (or the one allowed duration retry) and advances deterministically. | `test_canonicalization_failure_falls_through_to_the_next_backend` | Resolved in `a588510` |
| Target/cleanup exceptions could expose filesystem values | Dify writes, SAPI target preparation, Edge cleanup, and chain candidate/final cleanup all suppress filesystem values and surface only fixed adapter/attempt codes. | `test_dify_target_write_failure_is_value_free`; `test_sapi_target_setup_failure_is_value_free`; `test_edge_cleanup_failure_does_not_leak_a_directory_target` | Resolved in `a588510` |

## Gate truth and fresh local evidence

The Windows-only local gate traversed the real path:

`Microsoft Huihui Desktop -> WAV -> fixed FFmpeg argv -> MP3 -> ffprobe`.

It passed after remediation with backend `sapi`, voice `Microsoft Huihui Desktop`,
rate profile `normal` (SAPI rate `2`), duration `45,035 ms`, codec `mp3`, one
channel, `180,140` bytes, and SHA-256
`9caf9f15cd359cc9fdbb8635a935df84777b875cc567bcbd146a5d8710c0824c`.

The Dify marker clean-skips because `DIFY_API_KEY` is absent. The edge marker
clean-skips because `DEBUGMATE_ALLOW_NETWORK_TTS=1` was not explicitly enabled.
Both tests assert backend/rate/request identity, MP3 evidence, and value-free
rejection when they are deliberately enabled.

## Verification commands

- Focused remediation suite: recap, media, TTS chain, live-gate and command safety:
  `83 passed, 3 deselected`.
- `pytest -m tts tests/results/test_tts_live.py`: `1 passed, 2 skipped`.
- `ruff check src/debugmate/results tests/results tests/diagnosis/test_command_safety.py`: passed.
- `pip check`: no broken requirements.

The full offline marker exclusion run is retained as the final Phase 04 execution
gate and should be read together with the independent verifier's final evidence.

## Final review follow-up

The later independent review identified a separate final set of process-path,
input-revalidation, reparse-root and AST-shape findings. They are deliberately
not folded into the historical table above: their complete reproduced-test and
control mapping is recorded in `04-04-FINAL-REMEDIATION-REPORT.md`, with RED
commit `178d70e`, GREEN commit `b8b8d38`, fresh local SAPI evidence and the final
offline regression result.
