---
status: complete
phase: 04-multimodal-results-ui
source:
  - 04-01-SUMMARY.md
  - 04-02-SUMMARY.md
  - 04-03-SUMMARY.md
  - 04-04-SUMMARY.md
  - 04-05-SUMMARY.md
  - 04-06-SUMMARY.md
  - 04-07-SUMMARY.md
  - 04-08-SUMMARY.md
  - 04-09-SUMMARY.md
  - 04-10-SUMMARY.md
  - 04-11-SUMMARY.md
  - 04-12-SUMMARY.md
  - 04-VERIFICATION.md
updated: 2026-08-08T10:18:34Z
---

# Phase 04 UAT Reconciliation

## Current Test

[testing complete]

The 2026-07-16 file recorded 11 browser/evidence issues before Plans 04-10 through 04-12, the student-first UI quick task, the full explicit Edge run, and the review fixes existed. Those stale issue rows are reconciled below against current code and evidence. No row is upgraded from historical assertions alone: each automated pass is backed by a current contract test, real Edge check, result E2E, or hash-verified course evidence.

## Tests

### 1. Cold-start loopback workbench

expected: A clean local launch opens the DebugMate workbench in Edge and reaches a usable idle state without relying on a stale server.
result: pass
evidence: Current real-Edge UI regression and loopback ownership/cleanup contracts pass.

### 2. Privacy preview and explicit approval

expected: The user sees the redacted text/image preview and must explicitly approve it before any diagnosis begins.
result: pass
evidence: Server-held one-time preview token, same-session consume, explicit approval, tamper/cross-session/reuse rejection are covered by current UI contracts.

### 3. Genuine completed live diagnosis

expected: A real approved input produces a completed live local-rule result with truthful identity, citations and downloads.
result: pass
evidence: Local live path remains `InputEnvelope -> redact_input -> approve_preview -> DiagnosisWorkflow -> ResultApplicationService`, with `mode=live`, no fixture identity and `local-rule-v1` provenance.

### 4. Same-run report, card, citations, audio and downloads

expected: Result tabs and downloads expose artifacts derived from the same verified run identity.
result: pass
evidence: Completed result E2E and real Edge ZIP download verify manifest/checksums and visible `source_run_id` equality.

### 5. Local SAPI recap human listening quality

expected: A human listener confirms the generated Chinese recap is understandable, non-silent, unclipped and free from obvious mojibake or severe pronunciation failure.
result: pass
evidence: On 2026-08-08 the user listened to the current 50.580-second Local SAPI MP3 on a physical playback device and explicitly reported `听验通过`; the checked file SHA-256 was `f5c8cd13f4d12f8c2e42fb3fe58bdb3b2aeed7f7a03fbb7e0b91b72bb8173374`.

### 6. Completed replay truth labels

expected: Completed replay is labelled as replay in status, summary and download metadata and never implies fresh cloud success.
result: pass
evidence: Real Edge replay/truth-state coverage and strict `ResultMode.REPLAY` UI mapping pass; fixed replay remains explicitly non-Dify.

### 7. Running queue and repeat-submit protection

expected: A live run shows ordered stages, disables conflicting actions and uses no invented percentage progress.
result: pass
evidence: Current UI contracts and truth-state Edge suite cover ordered running stages, live status announcement and disabled conflicting actions.

### 8. Long report and command resilience

expected: Long reports and commands remain readable through local scrolling without clipping.
result: pass
evidence: `long-content` replay, real Edge long-content regression and mobile/desktop wrap checks pass; replay regeneration now preserves its index entry.

### 9. Tall diagnosis-card resilience

expected: A tall PNG preserves aspect ratio without horizontal overflow and keeps text report accessible.
result: pass
evidence: Real Edge long-content/tall-card representative scenario passed in the current targeted run.

### 10. Partial TTS failure truthfulness

expected: `tts_failed` is partial, preserves report/card/recap text, exposes no fake audio and offers TTS-scoped retry.
result: pass
evidence: Fresh TTS-partial E2E confirms `recap.mp3` is absent, preserved artifacts verify, and only the partial ZIP resolves.

### 11. Partial PNG failure truthfulness

expected: `png_layout_failed` is partial, preserves report/audio and exposes no fake image.
result: pass
evidence: Current truth-state UI/Edge coverage and hash-verified course screenshot `03-card-partial.png` demonstrate explicit card failure with preserved valid artifacts.

### 12. Invalid source bundle safe failure

expected: An invalid source bundle fails safely without unverified media/downloads or raw path/exception disclosure.
result: pass
evidence: Loader, presentation and security-abuse contracts reject tampered/mismatched bundles before result publication and map only fixed safe failure fields.

### 13. Fallback backend semantics

expected: Final backend and fallback reason are visible without presenting fallback as diagnosis failure.
result: pass
evidence: Truth-state Edge coverage and `evidence/media/phase4/local-sapi.json` record SAPI fallback explicitly; Dify/edge remain open/not-tested rather than false passes.

### 14. Correction creates a new run

expected: Pending corrections do not alter the old result until explicit create-new-run confirmation.
result: pass
evidence: Current UI callback and browser contracts cover pending diff, explicit confirmation, fresh identity and prior-result recovery semantics.

### 15. Completed responsive layouts

expected: Completed results remain usable at representative desktop/mobile widths and 200% zoom without body horizontal overflow.
result: pass
evidence: Current real Edge suite covers 1366 desktop, 375 mobile, long content and VQ-15 200% zoom; targeted Edge gate passed 4/4.

### 16. Keyboard, non-color and 200% zoom accessibility

expected: Workbench is keyboard operable; statuses retain icon/text distinction; 200% zoom preserves status and primary action.
result: pass
evidence: VQ-13, VQ-14 and VQ-15 contracts are covered by current Edge records; UI status uses literal text/icon and `aria-live`, not color alone.

### 17. Proportionate Phase 04 V0.1 sign-off

expected: The local course demo has representative real Edge, artifact, privacy and degraded-state evidence, without claiming production or cloud readiness.
result: pass
evidence: 04-11/04-12 acceptance, current quick UI verification, full explicit Edge `39 passed / 7 environment-gated skipped / 0 failed`, merged default offline `845 passed / 73 deselected / 0 failed`, course manifest 3/3 hash match, and `04-VERIFICATION.md` reconciliation.

## Summary

total: 17
passed: 17
issues: 0
pending: 0
skipped: 0
blocked: 0

## Completed Human Check

- truth: "Local SAPI 中文复盘在实体播放设备上可懂且无明显主观音质问题。"
  status: passed
  confirmed_by: user
  confirmed_on: 2026-08-08
  result: "听验通过"

## Explicit Boundaries

- Dify C01-C07 remain `not-tested`; no local/replay evidence is counted as cloud proof.
- PPTX, video, subtitles and final showcase screenshots remain locked for the last authorized refresh and were not regenerated here.
- Acceptance is for a local Windows course demonstration V0.1, not production readiness.
