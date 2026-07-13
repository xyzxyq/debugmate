---
phase: 04-multimodal-results-ui
plan: 04
status: secure-audio-refactor
---

# 04-04 Secure Audio Refactor and Plan 05 Handoff

## Controlled target contract

`TtsAdapter` no longer accepts a `Path` or any caller-selected output
directory.  Its sole synthesis contract is:

```python
synthesize(recap: SafeRecapText, request_identity: TtsRequestIdentity,
           rate_profile: RateProfile) -> AudioPayload
```

`AudioPayload` is frozen and carries only backend, rate, request identity,
optional approved voice and bounded audio bytes.  It has no path field.  Dify
returns bounded HTTP bytes, edge returns bounded bytes from its isolated child,
and SAPI returns bounded MP3 bytes after its local conversion.  Every adapter
revalidates the safe recap and identity immediately before its trust boundary.

`TtsFallbackChain` remains the only filesystem authority.  It requires a
factory-issued `TrustedCandidateRoot`, creates a random private run under a
root/run Windows directory lease, and never accepts a raw UI/API directory.
For each attempt it allocates a regular non-reparse candidate with
`CreateFileW(CREATE_NEW)` and read-only sharing.  The handle stays open with
write/delete sharing denied while the chain writes, probes and reads that exact
file.  The path's device, inode and byte size are checked against the held
handle before and after `ffprobe`.

FFmpeg canonicalisation now receives candidate bytes on stdin and returns MP3
bytes on stdout; it never receives a named output.  Only after final media
verification can the chain allocate `recap.mp3` via the same `CREATE_NEW`
lease, write it once, run `ffprobe` while the handle is still held, and retain
the final private candidate for the publisher.  A planted hardlink/Junction or
an unexpected existing name fails closed and is never overwritten.

### Final secure-review handoff control

The earlier prose requirement is now an executable API rather than a convention:
`TtsFallbackChain.synthesize()` returns `TtsSynthesisOutcome`. Its `audio` field
is the unchanged JSON-serialisable `AudioResult`; only a successful outcome also
carries an opaque `AudioHandoff`. The handoff has no public path/root field,
cannot be directly constructed or copied, and accepts only the exact in-memory
`AudioResult` object from that same outcome. Thus an equal `model_copy()` or a
forged record cannot obtain bytes.

Plan 05 calls `handoff.take_verified_bytes(outcome.audio)` exactly once. The
handoff keeps the private final-file descriptor plus root/run leases alive,
rechecks pathname identity, runs `ffprobe` again, compares duration/hash/byte
facts to `AudioResult`, reads that same descriptor, verifies its SHA-256, then
unlinks the private candidate and releases every lease. It returns bytes only;
it cannot be redirected to a result directory and exposes no raw path. A stale,
changed, copied or reused capability returns only `audio_handoff_invalid` with
no command/path cause or context.

Two adjacent final-boundary repairs are covered by permanent regressions:

- `SapiTtsAdapter` converts a direct `subprocess.TimeoutExpired` (including its
  sensitive command) to an isolated `tts_backend_failed` whose args, cause and
  context contain no process value.
- The edge worker receives `--rate=-10%` / `--rate=+10%`; a real isolated
  `python -I -m ... --validate-arguments` subprocess proves both approved rates
  parse without contacting the network.
- Mocked `ffprobe` JSON asserts the exact inclusive `30_000`, `45_000` and
  `60_000` millisecond values pass, while `29_999` and `60_001` fail.

## Backend-specific boundaries

- **Dify:** streams a size-capped `audio/mpeg`/`audio/mp3` response into an
  in-memory bounded payload.  It has no output-file write operation.
- **edge:** launches `python -I -m debugmate.results.tts.edge_worker` with a
  fixed voice/rate argv.  The safe recap travels only through bounded stdin and
  audio only through bounded stdout.  Parent timeout kills the worker process,
  so a cancellation-swallowing coroutine cannot delay SAPI fallback.
- **SAPI:** the fixed repository PowerShell script receives only approved voice
  and rate arguments, reads UTF-8 recap from stdin, and writes one WAV stream
  to stdout.  Fixed FFmpeg converts WAV stdin to tag-free MP3 stdout.  SAPI no
  longer creates a text input, WAV, `TemporaryDirectory` child or external
  output path.

## Exact duration rule

The public `MediaProbe` contract is exactly `30_000 <= duration_ms <= 60_000`.
The former MPEG-frame tolerance was removed.  Real fixture inputs are selected
inside the inclusive boundary (rather than weakening the verifier); dedicated
tests reject `29.981` and `60.001` seconds and accept real 30/45/60-second
fixtures.

## Attack and local evidence

- Dify `httpx.MockTransport` plants a real hardlink at the eventual final name;
  the chain raises `tts_target_invalid` and the outside file remains unchanged.
- Nested Windows Junction roots reject before an adapter call.  The real SAPI
  gate also runs while a nested Junction exists and confirms no external recap
  file is created; SAPI has no file output argument to redirect.
- A subprocess worker which sleeps indefinitely is force-killed at `0.05s`,
  followed by verified SAPI fallback.
- The real Windows SAPI marker passes through SAPI -> WAV stdout -> FFmpeg
  stdin/stdout -> MP3 -> `ffprobe`; Dify and edge remain explicit external
  open gates when credentials/network opt-in are absent.

After the final handoff repair, the local `tts` marker was run again and returned
`3 passed, 2 skipped`: direct SAPI, the Junction safety check and the complete
leased-chain route all passed. Dify remains **OPEN / skipped** without
`DIFY_API_KEY`; edge remains **OPEN / skipped** without explicit
`DEBUGMATE_ALLOW_NETWORK_TTS=1` approval.

## Plan 05 handoff

Plan 05 must treat the private final `recap.mp3` only as a candidate.  It must
not hand a result/download directory to `TtsFallbackChain`, and it must not
reuse a prior path check.  Its consistency gate must freshly re-probe/re-hash
the held candidate after locating it through controlled identity/root logic,
then copy only verified bytes into its separate atomic `ResultBundle`
transaction.  The publisher's final verifier owns all public paths, ZIP members
and download resolution; this pre-publication chain intentionally exposes no
raw source, provider body, temporary path or output path in `AudioResult`.
