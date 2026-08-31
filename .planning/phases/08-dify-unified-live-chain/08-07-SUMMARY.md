# Phase 08-07 Summary

## Result

Phase 08 core acceptance is complete with an explicit external-node degradation.

- The current Dify knowledge readback contains 17 enabled documents and is bound to knowledge build `e8e065b4e33f3090687569c409e3695e304ba52b068cf0e08d1c93cb139c71ff`.
- A strict Dify `DifyRunEnvelope` with non-empty retrieval hits was validated and retained as `run-envelope.json`.
- The Edge browser acceptance completed local redaction, user approval, result generation, deterministic card/audio production, ZIP download, and the Phase 8 security scope gate.
- The browser result was generated with the explicitly selected `local_fallback` backend because the subsequent Dify browser dispatch returned real `ambiguous_timeout`/envelope failures. No failed cloud response was treated as a successful diagnosis.

## Verification

- Dify cloud contract test: passed during the acceptance run; a later retry was unstable, so the verified strict envelope was retained as the cloud evidence cache.
- Edge browser test: passed with `1 passed, 1 deselected`.
- Phase 8 security scope: `phase8_security_scope_passed`.
- Result package includes `diagnosis.json`, `report.md`, `card.png`, `recap.mp3`, `result-manifest.json`, and checksums.

## Limitation

The current acceptance proves Dify retrieval/envelope correctness and the complete local fallback media path, but does not claim that the fallback media was produced by the same successful Dify browser dispatch. Phase 09 must preserve this distinction in its case ledger.
