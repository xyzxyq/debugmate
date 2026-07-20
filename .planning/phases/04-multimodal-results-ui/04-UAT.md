---
status: diagnosed
phase: 04-multimodal-results-ui
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md, 04-03-SUMMARY.md, 04-04-SUMMARY.md, 04-05-SUMMARY.md, 04-06-SUMMARY.md, 04-07-SUMMARY.md, 04-08-SUMMARY.md, 04-09-SUMMARY.md]
started: 2026-07-16T09:17:28.211Z
updated: 2026-07-16T09:35:00.000Z
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
  root_cause: "Replay truth is implemented, but the browser suite and the VQ-01-only runner never drive a completed replay through the real DOM."
  artifacts:
    - path: "src/debugmate/results/service.py"
      issue: "Strict replay and seven-stage flow exist but are not exercised by formal browser QA."
    - path: "tests/ui/test_browser.py"
      issue: "No completed replay truth-label scenario."
  missing:
    - "Add a real Edge completed replay scenario asserting replay labels in top status, result summary, and download metadata."
    - "Publish the VQ-02 screenshot and ledger row transactionally."
  debug_session: "diagnose_state_truth"
- truth: "Running stages and repeat-submit protection are observable without invented progress."
  status: failed
  reason: "Independent evidence audit found no real running-state browser capture or interaction assertion for VQ-03."
  severity: major
  test: 7
  root_cause: "The seven running stages exist at service/view-model level, but no deterministic stage gate lets the browser harness observe their ordered DOM transitions."
  artifacts:
    - path: "src/debugmate/ui/app.py"
      issue: "Running-state disabling exists but lacks formal browser timing coverage."
    - path: "tests/ui/test_browser.py"
      issue: "No controllable running-stage scenario."
  missing:
    - "Add a QA-only deterministic stage gate and real Edge assertions for stage order, disabled conflicting actions, and absence of invented percentages."
    - "Publish the VQ-03 ledger row."
  debug_session: "diagnose_state_truth"
- truth: "Long reports and command blocks remain readable and locally scrollable."
  status: failed
  reason: "Independent evidence audit found no completed long-content browser evidence for VQ-04."
  severity: major
  test: 8
  root_cause: "There is no strict long-content outcome loadable by the real Gradio UI, and the command accordion contains static safety copy instead of diagnosis commands."
  artifacts:
    - path: "fixtures/replay/index.json"
      issue: "Only one short ModuleNotFoundError replay is allowlisted."
    - path: "src/debugmate/ui/app.py"
      issue: "Replay choice is hard-coded and the command accordion is not bound to result commands."
  missing:
    - "Create a deterministic strict long-content replay fixture and expose it through the service allowlist."
    - "Bind the command accordion to diagnosis commands and verify local scrolling, uncut commands, and no body overflow in VQ-04."
  debug_session: "diagnose_layout"
- truth: "Tall diagnostic cards preserve aspect ratio without horizontal overflow."
  status: failed
  reason: "Independent evidence audit found no tall-card browser evidence for VQ-05."
  severity: major
  test: 9
  root_cause: "The existing diagnostic card is already tall, but browser QA only checks image visibility and never measures aspect ratio, container fit, or overflow."
  artifacts:
    - path: "tests/results/golden/card-layout.json"
      issue: "Provides a 1600x1913 tall card suitable for QA."
    - path: "tests/ui/test_browser.py"
      issue: "No tall-card geometry assertions or VQ-05 evidence."
  missing:
    - "Use the existing completed result to assert natural dimensions, displayed aspect ratio, container width, and body overflow in real Edge."
    - "Publish the VQ-05 screenshot and ledger row."
  debug_session: "diagnose_layout"
- truth: "TTS failure produces a truthful partial result with scoped recovery and no fake audio."
  status: failed
  reason: "Independent evidence audit found no real partial TTS-failure browser evidence for VQ-06."
  severity: major
  test: 10
  root_cause: "TTS partial rendering and retry service methods exist, but no deterministic browser failure scenario exists and build_app does not bind a scoped retry control."
  artifacts:
    - path: "src/debugmate/results/service.py"
      issue: "retry_stage exists and is not exposed by the Gradio page."
    - path: "src/debugmate/ui/app.py"
      issue: "UiCallbacks.retry exists but no retry button/click binding is rendered."
  missing:
    - "Add a QA-only deterministic tts_failed outcome and a TTS-scoped retry control wired to the existing service."
    - "Verify preserved report/card/recap, absent audio, partial bundle, and retry truth in VQ-06."
  debug_session: "diagnose_state_truth"
- truth: "PNG failure produces a truthful partial result with preserved valid artifacts and no fake image."
  status: failed
  reason: "Independent evidence audit found no real partial PNG-failure browser evidence for VQ-07."
  severity: major
  test: 11
  root_cause: "PNG partial rendering and retry service methods exist, but no deterministic browser card-failure scenario exists and the scoped retry facade is not bound in the page."
  artifacts:
    - path: "src/debugmate/results/service.py"
      issue: "Card-stage retry exists below the UI."
    - path: "src/debugmate/ui/app.py"
      issue: "No card-scoped retry control or event binding."
  missing:
    - "Add a QA-only deterministic png_layout_failed outcome and bind card-scoped retry."
    - "Verify preserved report/audio, explicit card error, no fake image, and partial bundle in VQ-07."
  debug_session: "diagnose_state_truth"
- truth: "Invalid source bundles fail safely without exposing unverified outputs or downloads."
  status: failed
  reason: "Independent evidence audit found no failed-state browser evidence for VQ-08."
  severity: major
  test: 12
  root_cause: "Safe failure presentation exists, but fixed valid inputs cannot deterministically reach source_bundle_invalid from a real browser session."
  artifacts:
    - path: "src/debugmate/ui/presentation.py"
      issue: "Safe failed-state mapping exists without a browser-reachable controlled corruption scenario."
    - path: "tests/ui/test_browser.py"
      issue: "No VQ-08 safe-failure DOM assertions."
  missing:
    - "Create an isolated QA-only invalid-source terminal state without mutating committed source fixtures."
    - "Assert seven safe failure fields, absence of media/downloads/paths/exception bodies, and publish VQ-08 evidence."
  debug_session: "diagnose_state_truth"
- truth: "Fallback backend and reason are visible without confusing fallback with failure."
  status: failed
  reason: "No browser UAT proves the fallback presentation required by VQ-09."
  severity: major
  test: 13
  root_cause: "Fallback selection and presentation exist, but environmental Dify/Edge behavior is nondeterministic and no QA composer forces an auditable fallback chain."
  artifacts:
    - path: "src/debugmate/ui/serve.py"
      issue: "Runtime backend availability cannot produce a stable formal fallback scenario."
    - path: "src/debugmate/ui/presentation.py"
      issue: "Fallback metadata exists but lacks browser acceptance evidence."
  missing:
    - "Create a deterministic QA outcome representing failed prior backends followed by SAPI or Edge success."
    - "Assert completed semantics, final backend, fallback reason, and publish VQ-09 evidence."
  debug_session: "diagnose_state_truth"
- truth: "Corrections remain pending until the user explicitly creates a new run."
  status: failed
  reason: "Independent evidence audit found no correction-workflow browser interaction for VQ-10."
  severity: major
  test: 14
  root_cause: "Correction lineage and callbacks exist, but no browser test covers the full edit, pending diff, explicit create-new-run, and old-result recovery event chain."
  artifacts:
    - path: "src/debugmate/ui/app.py"
      issue: "Correction controls are implemented without real DOM end-to-end evidence."
    - path: "tests/ui/test_browser.py"
      issue: "No VQ-10 correction interaction."
  missing:
    - "Add a real Edge correction flow asserting unchanged identity before confirmation, one pending old-to-new diff, new identity after confirmation, and recoverable prior result."
    - "Publish VQ-10 screenshot and ledger row."
  debug_session: "diagnose_state_truth"
- truth: "Completed results satisfy the responsive contracts at 1024×768 and 768×1024."
  status: failed
  reason: "Existing responsive evidence covers idle state only; completed-state VQ-11/VQ-12 proof is missing."
  severity: major
  test: 15
  root_cause: "Responsive CSS and idle geometry tests exist, but formal browser QA never loads completed results at 1024x768 or 768x1024."
  artifacts:
    - path: "src/debugmate/ui/app.py"
      issue: "Responsive breakpoints exist and remain unverified for completed content."
    - path: "tests/ui/test_browser.py"
      issue: "VQ-11 and VQ-12 cover idle geometry only."
  missing:
    - "Load a strict completed replay at both viewports and assert region geometry/order, four literal tabs, visible actions, and no body overflow."
    - "Publish required VQ-11 and VQ-12 screenshots and ledger rows."
  debug_session: "diagnose_layout"
- truth: "Keyboard, non-color status, and 200% zoom accessibility are independently verified."
  status: failed
  reason: "No VQ-13 through VQ-15 browser evidence exists."
  severity: major
  test: 16
  root_cause: "Status text/icon foundations and focus CSS exist, but there are no keyboard-only, grayscale four-state, or real 200-percent browser zoom scenarios; accessible_status is not exposed as a live status surface."
  artifacts:
    - path: "src/debugmate/ui/app.py"
      issue: "Focus styling exists, but accessible_status is not consumed by the rendered status surface."
    - path: "tests/ui/test_browser.py"
      issue: "No VQ-13 through VQ-15 acceptance coverage."
  missing:
    - "Add real Edge keyboard focus/order and activation assertions for tabs, accordions, audio, and download."
    - "Verify completed/partial/failed/replay under test-side grayscale and completed state at real 2.0 browser zoom."
    - "Wire an accessible live status surface if the RED browser test proves the current DOM contract fails."
  debug_session: "diagnose_multimodal_access"
- truth: "A complete VQ-01 through VQ-15 visual ledger supports independent Phase 4 sign-off."
  status: failed
  reason: "Only VQ-01 formal evidence exists; the remaining screenshots, ledger entries, and verifier report are missing."
  severity: major
  test: 17
  root_cause: "The verification-only 04-07 wave stopped after VQ-01 failed; 04-08 repaired idle geometry and 04-09 proved only VQ-01, so the full matrix runner and set-level transactional publisher were never completed."
  artifacts:
    - path: "scripts/run-phase4-local-live-qa.ps1"
      issue: "Intentionally publishes only a transactional VQ-01 pair."
    - path: "evidence/ui/phase4"
      issue: "visual-qa.json and VQ-02 through VQ-15 evidence are absent."
  missing:
    - "Build one bounded loopback/real Edge runner for all 15 scenarios with staged screenshots and a 15-row visual-qa.json."
    - "Validate unique IDs, hashes, state/mode/backend/viewport/overflow fields, required screenshots, browser downloads, ZIP manifest and same-run identities before atomic set promotion."
    - "Run an independent Phase 4 verifier and generate 04-VERIFICATION.md; keep human listening as human_needed."
  debug_session: "diagnose_multimodal_access"
