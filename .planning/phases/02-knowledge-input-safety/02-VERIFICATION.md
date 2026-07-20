# Phase 2 Verification

**Status:** PASSED with explicit external gates

**Verified:** 2026-07-12

**Head:** `479ad52`

## Requirement Evidence

| Requirement | Result | Evidence |
|---|---|---|
| INP-01 | Passed | Strict text/screenshot input contracts; missing both is rejected locally. |
| SAFE-01 | Passed | Text and screenshot redaction, value-free audit, preview approval and upload gate. |
| SAFE-02 | Passed for Phase 2 artifacts | Text/JSON/PNG are rescanned; PNG metadata is removed; unknown binary and audio publication fail closed. MP3 remains deferred to Phase 4. |
| SAFE-03 | Passed | Prompt-injection text is marked as untrusted and cannot trigger external actions; knowledge extraction never executes page instructions. |
| KNOW-01 | Passed | `knowledge/sources.json` contains exactly 17 official sources across seven required product families. |
| KNOW-02 | Passed | Real build source records merge registry and fetch metadata and validate against `knowledge/manifest.schema.json`. |
| KNOW-03 | Passed at implementation/contract level | Rebuild, sealed sync plan, source metadata, chunk 800/overlap 120 and strict readback comparison exist. Real Dify write/readback is an external credential gate. |
| KNOW-04 | Passed | Strict summary-only retrieval traces preserve chunk ID, source, URL, score and locator; raw chunks are forbidden. |
| KNOW-05 | Passed | Coverage and fixed-query evaluation report category counts, hit rates, blind spots and update times. |

## Automated Gates

```text
pytest -q -m "not cloud and not ocr"  -> 279 passed, 19 deselected
scripts/build_knowledge.ps1           -> ready/syncable; 91 passed, 18 deselected; executed=false
scripts/build_knowledge.ps1 -Online   -> 17/17 sources; 17 notes; executed=false
ruff check .                          -> passed
pip check                             -> no broken requirements
git diff --check                      -> passed
```

## Adversarial Checks

- Cross-domain and unregistered redirects are rejected.
- Nested HTML headings cannot leak the next section into the current note.
- Rewritten notes, recomputed internal hashes and renamed build directories are rejected without the out-of-band expected build identity.
- Tampered sync plans, dangerous IDs, path escapes, symlinks and stale later files all fail before the first HTTP request.
- PNG secrets in metadata or disguised file extensions are removed/rejected.
- ASCII, UTF-16 and UTF-32 secrets in unknown binaries are rejected without echoing matched values.
- MP3/audio evidence and arbitrary audio callbacks are not executed or published in Phase 2.
- Retrieval output is rescanned and cannot contain raw chunks or unvalidated sensitive summaries.

## Evidence Boundaries

- The online knowledge build is genuine and used all 17 official sources.
- Offline retrieval evidence is genuine for the deterministic `offline_fixture` backend and reports misses honestly; it is not Dify retrieval evidence.
- Dify request/readback behavior is verified with mock transport only; no real cloud dataset was mutated.
- TTS/MP3 is deliberately not tested or claimed in Phase 2.

## Final Review

Independent final adversarial review returned `REVIEW CLEAN` at HEAD `479ad52` after retesting every previously reproduced bypass.
