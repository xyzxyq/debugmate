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
- `115ac24` hardening: cap Dify bytes while streaming, before persistence.
- `61f205e` RED: reproduce the AST process-audit blind spot with synthetic source.
- `fb938a9` GREEN: restore independent `os.system` and `subprocess.*` detection while
  retaining the two exact separately audited media modules.

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
- The repository-wide AST safety test still rejects subprocess imports and calls in every
  other module. A synthetic regression fixture proves `subprocess.run`, `Popen` and
  `os.system` are independently detected; only `media.py` and `tts/sapi.py` are delegated
  to their dedicated argv, timeout, cleanup and `shell=False` attack tests.
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

## Post-review remediation

After the independent review, the first implementation was re-audited and two
test-first remediation commits were applied:

- `de33ca0` narrows the repository AST process boundary to the single audited
  `media.py` `subprocess.Popen` shape, removes unbounded SAPI `capture_output`,
  canonicalizes every accepted candidate before publication, and fixes the real
  adapter gate fixtures to construct a valid `SafeRecapText`.
- `a588510` keeps canonicalization/final-probe failures inside the ordered fallback,
  makes failed candidate and target cleanup value-free, and rejects untrusted SAPI
  roots, executable overrides and non-regular resolved FFmpeg binaries.

The local SAPI marker was re-run after the remediation: `1 passed, 2 explicit
external skips`. The actual evidence remains `sapi`, `Microsoft Huihui Desktop`,
`normal`/SAPI rate `2`, `45,035 ms`, mono MP3, `180,140` bytes and SHA-256
`9caf9f15cd359cc9fdbb8635a935df84777b875cc567bcbd146a5d8710c0824c`.

See `04-04-REMEDIATION-REPORT.md` for the finding-to-test evidence mapping.

## Final independent-review remediation

The final review found four remaining boundary weaknesses. They were reproduced
first in `178d70e` and closed in `b8b8d38`:

- Production FFmpeg/ffprobe no longer use `PATH`; the resolver accepts only the
  fixed Windows WinGet 8.1 installation layout after regular-file, no-reparse and
  exact SHA-256 checks. SAPI now obtains the actual Windows system directory from
  the Windows API instead of `SYSTEMROOT`.
- The chain itself reparses the raw `SafeRecapText` and request fields with strict
  validation before it reads any identity field or invokes an adapter. A forged
  seven-unit `model_construct` input is rejected with no adapter call.
- The candidate root is absolute and checked from every existing ancestor before
  `mkdir`, immediately after `mkdir`, around temporary-directory creation and
  around final publication. A real nested Windows Junction to an outside directory
  is rejected before any candidate or outside write.
- The AST guard now permits exactly one `media._run_bounded_process` `Popen`
  shape: `command`, `stdin=subprocess.DEVNULL`, named `stdout`/`stderr`, and literal
  `shell=False`; additional execution options and wrong stream boundaries reject.

See `04-04-FINAL-REMEDIATION-REPORT.md` for the final finding-to-control mapping
and fresh evidence.

## TOCTOU and bounded-process follow-up

The final review's remaining executable-replacement, candidate-root swap and
child-output findings were reproduced and closed in strict RED/GREEN commits:

- `3c0e1b3` / `b09290c`: raw caller paths are no longer accepted by
  `TtsFallbackChain`; it receives a factory-issued private candidate-root
  capability and holds Windows non-delete directory leases during the actual
  canonicalization interval. A genuine Junction-swap attempt proves no outside
  file is ever created.
- `1c4560f` / `da49fb7`: media executable metadata caching is removed; every
  lookup hashes the current pinned file, with a second revalidation and
  no-write/no-delete file-handle lease immediately before `Popen`. Child output
  is concurrently pipe-drained and killed at the bounded per-stream limit,
  rather than being written to an unbounded temporary file.
- `1551fc5` / `4cb5b70`: direct construction of the capability is sealed;
  production uses the fixed application-owned candidate space and tests use an
  explicit injection factory.

The fresh post-change TTS marker still returned `1 passed, 2 explicit external
skips`. See `04-04-TOCTOU-REMEDIATION-REPORT.md` for exact attack evidence,
Plan 05 publication implications and the explicitly bounded Windows residual
limits.

## Verification

- `tests/results/test_recap.py`: 6 passed.
- `tests/results/test_media.py`: 24 passed with real FFmpeg fixtures and
  replacement/output-flood regressions.
- `tests/results/test_tts_chain.py`: 21 passed, including a real Junction race.
- `pytest -m tts tests/results/test_tts_live.py`: 1 passed, 2 explicit external skips.
- External marker selection: 2 skipped, 1 deselected.
