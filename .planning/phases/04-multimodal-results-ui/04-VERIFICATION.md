# Phase 04 V0.1 Verification

**Verdict:** PASS for local Windows course demonstration V0.1. This is not a production-readiness claim.

## Verified Outcomes

- A completed replay shows redacted input, extracted fields, facts, citations, report, PNG, audio and download in one Gradio page.
- Report, PNG, MP3 and ZIP derive from the same verified diagnosis identity.
- Browser download validation checks filename, MIME, ZIP readability, artifact checksums and visible `source_run_id` equality.
- Partial TTS and PNG failures show failed node, safe code, still-available results and minimal retry scope.
- Replay mode is visibly labelled and is not presented as Dify/cloud live output.
- Keyboard path, status announcement, 200% zoom geometry, status icon/text distinction and long-content layout pass in real Microsoft Edge.

## Representative Commands and Results

- UI/view/callback tests: 58 passed.
- Result and UI app tests: 264 passed, 5 deselected.
- VQ-13 and VQ-15: 2 passed.
- VQ-14: 1 passed.
- Long-content regression: 1 passed.
- V0.1 same-run ZIP download: 1 passed.
- Output privacy scanner: 21 passed.

## Course Evidence

- `evidence/course-v0.1/manifest.json`
- `evidence/course-v0.1/screenshots/01-completed-overview.png`
- `evidence/course-v0.1/screenshots/02-tts-partial.png`
- `evidence/course-v0.1/screenshots/03-card-partial.png`

## Remaining Human Check

Before final submission, open the PPTX once in PowerPoint/WPS and flip through all 13 slides, then listen to part of the generated video for intelligible Chinese and acceptable volume. The automated checks verified package structure, hashes, H.264/AAC decoding, non-silent audio and a 358.923-second duration, but do not claim subjective human listening or application-specific PowerPoint rendering.
