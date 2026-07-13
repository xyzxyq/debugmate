---
phase: 04-multimodal-results-ui
plan: 04
status: resolved-with-explicit-platform-limits
review_base: a92e4a7
closing_red_commit: f4080f3
closing_green_commit: 2c88383
---

# 04-04 TOCTOU Remediation Report

## Scope

This follow-up first closed the last two Important findings and one Minor finding
from the Plan 04-04 audio review: media-tool replacement after metadata-cache
reuse, candidate-root Junction replacement during canonicalization, and unbounded
child stdout/stderr written to temporary files. The closing review then found two
additional Important gaps inside the already-leased candidate run: an unleased
`TemporaryDirectory` child could be replaced during an adapter call, and edge-tts
had no deterministic local timeout. Those two closing gaps are reproduced and
resolved by `f4080f3` / `2c88383` below.

## Controls and executable evidence

| Finding | Test-first evidence | Implemented control | Result |
|---|---|---|---|
| Same-size replacement with restored mtime could reuse `_VERIFIED_EXECUTABLES`. | `test_media_resolver_rejects_same_size_mtime_restored_tamper_in_child_process` starts an independent interpreter, validates a fixture binary, then replaces its bytes with the same length and restored timestamps before its second lookup. | `_VERIFIED_EXECUTABLES` is removed. Every resolver call rechecks the fixed WinGet layout, final regular/no-reparse file, every ancestor, and exact SHA-256. Before a media `Popen`, the command path is resolved and rehashed again under a Windows read handle that denies write/delete sharing. | Resolved on the target Windows host. |
| A caller-selected target root could be changed into a Junction after checks and before canonicalization. | `test_candidate_capability_blocks_junction_swap_during_canonicalization` reads the candidate bytes, attempts to rename the active run directory, creates a real `mklink /J` to an outside directory, and would then write `recap.mp3`. It asserts that the outside file was never created. | `TtsFallbackChain.synthesize(recap, request, candidate_root)` accepts `TrustedCandidateRoot`, never a raw `Path`. Normal production uses `TrustedCandidateRoot.application_owned()`; the raw-path constructor is sealed. Each request allocates an identity-derived private candidate run under that capability. Root and run directories are held with Windows directory handles that deny delete/rename through adapter, probe, and canonicalization work. | Resolved for the demonstrated Junction race. |
| Child output could fill a `TemporaryFile` and was capped only after process exit. | `test_bounded_runner_terminates_an_output_flood_before_persisting_it` runs a real Python child that continuously floods both stdout and stderr. | `_run_bounded_process` drains both pipes concurrently. Each stream reads at most `max_output_bytes + 1`; the first overflow immediately kills the child and raises `ProcessOutputLimitExceeded`. No child output is written to a temporary file. | Resolved. |
| The `TemporaryDirectory` child inside a correctly leased run could still be renamed into a real Junction while an adapter was writing its candidate. Its default cleanup could then call `rmtree` on the substituted path and surface a raw `OSError`. | `test_leased_temp_child_blocks_junction_swap_during_adapter` performs a real `Path.replace` attempt against the exact adapter temp child; if the rename had succeeded it would create a real `mklink /J` to an outside directory and write the candidate there. It records the outside state both before and after the attempted write. The prior implementation reproduced both the outside-write condition and raw `TemporaryDirectory.cleanup()` error. | `TtsFallbackChain` now creates the child with `mkdtemp`, rechecks it, and acquires a Windows read+DELETE directory handle with no delete sharing **before** constructing any candidate path. That lease remains active across every adapter, candidate probe, canonicalization and final probe. Cleanup is non-recursive: under the active lease it removes only direct regular, non-reparse files, then marks that exact empty open directory for deletion with `SetFileInformationByHandle`; an uncertain directory is left private rather than reopened or traversed. All cleanup errors are swallowed and cannot replace the fixed TTS outcome/error. | Resolved on the target Windows host. |
| A stalled edge-tts `Communicate.save()` had no fixed upper bound and could delay the entire fallback chain indefinitely. | `test_edge_timeout_is_bounded_cancelled_and_falls_through_to_sapi` replaces `Communicate.save()` with a never-completing coroutine, records the `asyncio.wait_for` timeout, measures elapsed time and confirms the SAPI fallback returns a verified candidate. | `EdgeTtsAdapter(timeout_seconds=30.0)` validates a fixed positive finite constructor value. It wraps the save task in `asyncio.wait_for`, explicitly cancels and awaits it on timeout, deletes its target value-free, and raises only `tts_backend_failed` to the chain. | Resolved; a `0.05s` test timeout fell through to SAPI in under one second. |

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

For the closing temporary-child cleanup, a failed safety recheck or an unknown
direct entry intentionally leaves a private orphan rather than recursively
removing it. This is a bounded housekeeping trade-off, not a publication path:
the object stays below the factory-owned candidate root, receives no result
manifest reference and cannot override the typed TTS response. A later local
maintenance command may remove only roots it can freshly prove are non-reparse.

## Fresh verification after the changes

- `tests/results/test_tts_chain.py`: `23 passed`, including the real adapter-time
  Junction replacement attempt and never-completing edge coroutine.
- Focused audio suite (`test_tts_chain`, `test_media`, `test_tts_live` with
  external gates excluded): `48 passed, 2 deselected`.
- Real local TTS gate: `pytest -m tts tests/results/test_tts_live.py`:
  `1 passed, 2 skipped` (Dify credential and network TTS remain explicit open
  gates).
- Full offline suite: `628 passed, 25 deselected`.
- `ruff check src/debugmate/results tests/results tests/diagnosis/test_command_safety.py`
  and `pip check`: passed.
- The real local route remained `Microsoft Huihui Desktop -> WAV -> FFmpeg ->
  MP3 -> ffprobe`; no external paid service was configured.
