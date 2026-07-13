---
phase: 04-multimodal-results-ui
plan: 04
status: resolved-with-explicit-platform-limits
review_base: a92e4a7
---

# 04-04 TOCTOU Remediation Report

## Scope

This follow-up closes the last two Important findings and one Minor finding from
the Plan 04-04 audio review: media-tool replacement after metadata-cache reuse,
candidate-root Junction replacement during canonicalization, and unbounded child
stdout/stderr written to temporary files.

## Controls and executable evidence

| Finding | Test-first evidence | Implemented control | Result |
|---|---|---|---|
| Same-size replacement with restored mtime could reuse `_VERIFIED_EXECUTABLES`. | `test_media_resolver_rejects_same_size_mtime_restored_tamper_in_child_process` starts an independent interpreter, validates a fixture binary, then replaces its bytes with the same length and restored timestamps before its second lookup. | `_VERIFIED_EXECUTABLES` is removed. Every resolver call rechecks the fixed WinGet layout, final regular/no-reparse file, every ancestor, and exact SHA-256. Before a media `Popen`, the command path is resolved and rehashed again under a Windows read handle that denies write/delete sharing. | Resolved on the target Windows host. |
| A caller-selected target root could be changed into a Junction after checks and before canonicalization. | `test_candidate_capability_blocks_junction_swap_during_canonicalization` reads the candidate bytes, attempts to rename the active run directory, creates a real `mklink /J` to an outside directory, and would then write `recap.mp3`. It asserts that the outside file was never created. | `TtsFallbackChain.synthesize(recap, request, candidate_root)` accepts `TrustedCandidateRoot`, never a raw `Path`. Normal production uses `TrustedCandidateRoot.application_owned()`; the raw-path constructor is sealed. Each request allocates an identity-derived private candidate run under that capability. Root and run directories are held with Windows directory handles that deny delete/rename through adapter, probe, and canonicalization work. | Resolved for the demonstrated Junction race. |
| Child output could fill a `TemporaryFile` and was capped only after process exit. | `test_bounded_runner_terminates_an_output_flood_before_persisting_it` runs a real Python child that continuously floods both stdout and stderr. | `_run_bounded_process` drains both pipes concurrently. Each stream reads at most `max_output_bytes + 1`; the first overflow immediately kills the child and raises `ProcessOutputLimitExceeded`. No child output is written to a temporary file. | Resolved. |

## API and publication boundary

`TtsFallbackChain` no longer treats a web/UI/API supplied output directory as an
authority. The required third argument is a factory-issued
`TrustedCandidateRoot`; a raw `Path` and direct `TrustedCandidateRoot(path)` both
raise `TypeError`. `TrustedCandidateRoot.for_testing(...)` is an explicit test
injection seam only.

The audio output remains a private Phase 4 candidate, not a result publication.
Plan 05 must re-probe/re-hash the candidate and copy it into its own atomic
`ResultBundle` transaction. It must not ask the TTS chain to write into a bundle
or download root.

## Windows boundary and residual limits

The media lease uses `CreateFileW` with read-only access and without
`FILE_SHARE_WRITE` or `FILE_SHARE_DELETE`. The process path is rehashed after
that handle is acquired and the handle stays open through `Popen`, so ordinary
same-user replacement/rename attempts are blocked during the demonstrated
validation-to-execution interval.

CPython `subprocess.Popen` launches an executable by pathname; it does not offer
a supported Windows execute-by-open-file-handle API. Therefore this is not a
claim of kernel-level code identity against an administrator, kernel driver, or
another actor able to bypass Windows sharing rules. There is also an unavoidable
user-mode path-resolution interval before the directory/executable handle is
first obtained. The attack surface is materially narrowed because production
uses a fixed application-owned root and fixed pinned media locations; the
documented `for_testing` factory is not a UI/API boundary.

The output cap prevents unbounded disk or Python-heap accumulation. A child may
still fill the bounded operating-system pipe buffer between a reader's final
read and `TerminateProcess`; that bounded kernel buffering is not persisted and
is not represented as accepted output.

## Fresh verification after the changes

- `tests/results/test_tts_chain.py`: `21 passed`.
- `tests/results/test_media.py` plus `tests/diagnosis/test_command_safety.py`:
  `64 passed`.
- Real local TTS gate: `pytest -m tts tests/results/test_tts_live.py`:
  `1 passed, 2 skipped` (Dify credential and network TTS remain explicit open
  gates).
- The real local route remained `Microsoft Huihui Desktop -> WAV -> FFmpeg ->
  MP3 -> ffprobe`; no external paid service was configured.
