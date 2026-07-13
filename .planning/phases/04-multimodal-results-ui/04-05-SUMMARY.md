---
phase: 04-multimodal-results-ui
plan: 05
status: complete
---

# 04-05 Result Bundle Verification Summary

## Delivered

- Added a fail-closed cross-modal consistency gate.  It recreates the report,
  citations and recap from the verified presentation model, checks every shared
  identity field, rescans exported text, verifies the PNG, and issues a weak
  capability for the exact validated object only.
- A publisher cannot accept a renderer object, a copied dataclass, a raw path,
  or a replacement candidate.  Successful audio is copied only through the
  existing one-shot `TtsSynthesisOutcome` handoff.
- Added atomic immutable result publication under
  `results/<case_id>/<result_id>`, with exclusive temporary siblings,
  deterministic full/partial ZIPs, canonical manifests, sorted checksums and
  an acyclic outside-archive publication record.
- Added an on-disk verifier and fixed-member download resolver.  Both re-read
  the manifest, file graph, hashes, privacy data, media/PNG and ZIP metadata at
  request time.  The reusable `result-verify` CLI emits path-free JSON.
- Kept Phase 3 evidence and its audio fail-closed boundary untouched.

## Security Coverage

- Direct tests cover identity drift, forged candidate/citation/recap data,
  changed card bytes, audio partial availability, ZIP slip, oversized ZIP
  member, stale manifest version, extra/tampered files, file-swap/symlink
  download attempts, unsafe member labels and interrupted atomic writes.
- ZIP verification enforces exact allowlists, fixed order and metadata, CRC,
  member/total/ratio bounds, no publication member, and the frozen
  manifest/checksum/publication hash graph.

## Verification

- `python -m pytest -q tests/results` — 179 passed, 5 deselected.
- `python -m pytest -q` — 651 passed, 27 deselected (offline defaults).
- `python -m ruff check src/debugmate/results src/debugmate/cli.py tests/results`
  and `python -m pip check` — passed.

## Compatibility Note

`ResultManifest` accepts the established TTS fallback retry scope `tts` for
an explicit audio-only partial result, while retaining `audio` and the exact
card retry contract.  This aligns the terminal bundle contract with the
already fail-closed Phase 04 TTS chain.

The verifier also reconstructs the narrow typed source-summary contract before
serving a bundle; JSON list encoding is converted to the contract's tuple
shape before strict validation, without accepting extra provider data.

## Security Remediation Addendum

The independent review found five blocking boundaries that ordinary frozen
models and ordinary path checks could not close.  They are repaired in
`04-05-SECURITY-REMEDIATION.md`:

- candidate data is now a registry-only immutable publication snapshot;
- the loader issues and revalidates an exact Phase 3 source proof before the
  gate accepts it;
- publication accepts only a factory-issued result root and keeps root/case/
  temporary directories under no-delete leases;
- downloads return one-shot verified bytes rather than a reopenable path; and
- ZIP verification validates every central-directory entry before opening any
  payload, then streams bounded CRC/hash checks.

Updated verification after the remediation:

- `python -m pytest -q tests/results` — 187 passed, 5 deselected.
- `python -m pytest -q -m "not cloud and not ocr and not network and not browser and not tts"`
  — 659 passed, 27 deselected.
- Targeted Ruff, `pip check`, and `git diff --check` — passed.
