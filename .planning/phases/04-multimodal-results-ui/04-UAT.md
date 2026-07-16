---
status: partial
phase: 04-multimodal-results-ui
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md, 04-05-SUMMARY.md, 04-06-SUMMARY.md, 04-07-SUMMARY.md, 04-08-SUMMARY.md, 04-09-SUMMARY.md]
started: 2026-07-16T09:17:28.211Z
updated: 2026-07-16T09:17:28.211Z
---

## Current Test

[testing paused — 12 items outstanding: 11 evidence gaps and 1 physical listening check]

## Tests

### 1. Cold-start loopback workbench
expected: A clean local launch opens the DebugMate workbench in Edge and reaches a usable idle state without relying on a stale server.
result: pass

### 2. Privacy preview and explicit approval
expected: The user sees the redacted text/image preview and must explicitly approve it before any diagnosis begins.
result: pass

### 3. Genuine completed live diagnosis
expected: A real approved input produces a completed live result at 1366×768 with the three workbench regions, truthful live identity, citations, downloads, and no body-level horizontal overflow.
result: pass

### 4. Same-run report, card, citations, audio, and downloads
expected: The result tabs and download actions expose artifacts derived from the same run identity, with evidence locators and official source URLs visible.
result: pass

### 5. Local SAPI recap human listening quality
expected: A human listener confirms the generated Chinese recap is understandable, non-silent, unclipped, and free from obvious mojibake or severe pronunciation failure.
result: blocked
blocked_by: physical-device
reason: Machine evidence proves a 45.144-second mono, decodable, non-silent MP3, but an independent human listening judgment cannot be honestly automated.

### 6. Completed replay truth labels
expected: Loading a completed replay labels the top status, result summary, and download metadata as replay and never implies a fresh cloud success.
result: issue
reported: "Independent evidence audit found no completed replay browser run or formal VQ-02 screenshot."
severity: major

### 7. Running queue and repeat-submit protection
expected: A live run shows ordered queue stages, disables conflicting actions while running, and uses no invented percentage progress.
result: issue
reported: "Independent evidence audit found no real running-state browser capture or interaction assertion for VQ-03."
severity: major

### 8. Long report and command resilience
expected: Long reports and commands remain readable through local scrolling without clipping, while the result region stays usable.
result: issue
reported: "Independent evidence audit found no completed long-content browser evidence for VQ-04."
severity: major

### 9. Tall diagnosis-card resilience
expected: A tall PNG keeps its aspect ratio, causes no horizontal overflow, and leaves the accessible text report available.
result: issue
reported: "Independent evidence audit found no tall-card browser evidence for VQ-05."
severity: major

### 10. Partial TTS failure truthfulness
expected: A tts_failed run is labeled partial, preserves report/card/recap text, shows no empty audio artifact, and exposes a scoped retry.
result: issue
reported: "Independent evidence audit found no real partial TTS-failure browser evidence for VQ-06."
severity: major

### 11. Partial PNG failure truthfulness
expected: A png_layout_failed run is labeled partial, preserves report/audio, and shows an explicit card-generation error rather than a fake empty image.
result: issue
reported: "Independent evidence audit found no real partial PNG-failure browser evidence for VQ-07."
severity: major

### 12. Invalid source bundle safe failure
expected: A source_bundle_invalid run is failed, exposes the required safe error details, and offers no unverified artifacts or downloads.
result: issue
reported: "Independent evidence audit found no failed-state browser evidence for VQ-08."
severity: major

### 13. Fallback backend semantics
expected: When Edge or SAPI fallback is used, the final backend and fallback reason are visible without presenting the fallback itself as a failed diagnosis.
result: issue
reported: "Machine media evidence exists, but no browser UAT proves the backend and reason presentation required by VQ-09."
severity: major

### 14. Correction creates a new run
expected: Editing an extracted field shows pending changes and old-to-new values, and diagnosis does not rerun until the user selects Create new run.
result: issue
reported: "Independent evidence audit found no correction-workflow browser interaction for VQ-10."
severity: major

### 15. Completed responsive layouts
expected: Completed results work at 1024×768 and 768×1024 with the specified region order, full tab labels, visible controls, and no body horizontal overflow.
result: issue
reported: "Existing VQ-11/VQ-12 browser geometry evidence covers only idle state, not completed results or the required formal screenshots."
severity: major

### 16. Keyboard, non-color, and 200% zoom accessibility
expected: The workbench is operable using only the keyboard, status remains distinguishable without color, and 200% zoom loses no status or primary action.
result: issue
reported: "Independent evidence audit found no VQ-13 through VQ-15 keyboard, grayscale, or zoom evidence."
severity: major

### 17. Complete Phase 4 visual ledger and independent sign-off
expected: Formal evidence contains VQ-01 through VQ-15 entries with screenshot hashes, viewport/state/mode/backend truth, and an independent verifier reconciles requirements and planning documents.
result: issue
reported: "Only VQ-01 formal evidence exists; visual-qa.json, VQ-02 through VQ-15 screenshots, and independent Phase 4 verification are missing."
severity: major

## Summary

total: 17
passed: 4
issues: 12
pending: 0
skipped: 0
blocked: 1

## Gaps

- truth: "Completed replay is truthfully labeled in status, summary, and download metadata."
  status: failed
  reason: "Independent evidence audit found no completed replay browser run or formal VQ-02 screenshot."
  severity: major
  test: 6
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Running stages and repeat-submit protection are observable without invented progress."
  status: failed
  reason: "Independent evidence audit found no real running-state browser capture or interaction assertion for VQ-03."
  severity: major
  test: 7
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Long reports and command blocks remain readable and locally scrollable."
  status: failed
  reason: "Independent evidence audit found no completed long-content browser evidence for VQ-04."
  severity: major
  test: 8
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Tall diagnostic cards preserve aspect ratio without horizontal overflow."
  status: failed
  reason: "Independent evidence audit found no tall-card browser evidence for VQ-05."
  severity: major
  test: 9
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "TTS failure produces a truthful partial result with scoped recovery and no fake audio."
  status: failed
  reason: "Independent evidence audit found no real partial TTS-failure browser evidence for VQ-06."
  severity: major
  test: 10
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "PNG failure produces a truthful partial result with preserved valid artifacts and no fake image."
  status: failed
  reason: "Independent evidence audit found no real partial PNG-failure browser evidence for VQ-07."
  severity: major
  test: 11
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Invalid source bundles fail safely without exposing unverified outputs or downloads."
  status: failed
  reason: "Independent evidence audit found no failed-state browser evidence for VQ-08."
  severity: major
  test: 12
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Fallback backend and reason are visible without confusing fallback with failure."
  status: failed
  reason: "No browser UAT proves the fallback presentation required by VQ-09."
  severity: major
  test: 13
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Corrections remain pending until the user explicitly creates a new run."
  status: failed
  reason: "Independent evidence audit found no correction-workflow browser interaction for VQ-10."
  severity: major
  test: 14
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Completed results satisfy the responsive contracts at 1024×768 and 768×1024."
  status: failed
  reason: "Existing responsive evidence covers idle state only; completed-state VQ-11/VQ-12 proof is missing."
  severity: major
  test: 15
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Keyboard, non-color status, and 200% zoom accessibility are independently verified."
  status: failed
  reason: "No VQ-13 through VQ-15 browser evidence exists."
  severity: major
  test: 16
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "A complete VQ-01 through VQ-15 visual ledger supports independent Phase 4 sign-off."
  status: failed
  reason: "Only VQ-01 formal evidence exists; the remaining screenshots, ledger entries, and verifier report are missing."
  severity: major
  test: 17
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
