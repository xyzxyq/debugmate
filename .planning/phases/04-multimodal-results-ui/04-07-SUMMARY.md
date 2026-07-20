---
phase: 04-multimodal-results-ui
plan: 07
status: completed_with_gap
completed: 2026-07-14
---

# Plan 04-07 Summary — execution evidence with blocked browser acceptance

## Delivered verification assets

- Added five-state disk-reread E2E proof in `tests/results/test_result_e2e.py`
  and one public-boundary adversarial test for each `T4-01` through `T4-14` in
  `tests/results/test_security_abuse.py`. Their focused command passed
  `19 passed`.
- Recorded default offline, Schema round-trip, public full/partial result,
  deterministic ZIP, static, dependency and product-tree secret gates in
  `04-07-EXECUTION-LOG.md`. At the recorded execution head, default pytest
  passed `725 passed, 27 deselected`; Ruff, `pip check` and `git diff --check`
  passed.
- Recorded a current-code real Windows SAPI → FFmpeg/ffprobe proof in
  `evidence/media/phase4/local-sapi.json`: mono MP3, 45,144 ms, 180,576 bytes,
  decode exit 0, SHA-256
  `10fb8c17b2c1c31b51055a71fa223deeb9ae9412f0f9218c1936bd4b933f0db6`.
  Automated signal checks found non-silent PCM and no full-scale clipping.
  Human listening is explicitly `human_needed`, not represented as passed.
- Recorded Dify TTS as clean-skipped/open because `DIFY_API_KEY` is absent and
  edge TTS as clean-skipped/open because network TTS was not explicitly
  enabled. Neither is substituted for local SAPI proof.
- Added a pinned-Playwright/explicit-Edge browser harness and real VQ-01
  screenshot. It launches the exact loopback serve command, waits for
  `/config`, uses `domcontentloaded` instead of Gradio-incompatible
  `networkidle`, captures evidence before asserting, and cleans up its captured
  server port.

## Blocking result

The VQ-01 browser harness correctly fails against the current application:
the three regions measure `[67, 67, 67]` pixels instead of the required
minimum `[280, 360, 440]`, and the fixed replay selector is not visible. The
root layout selector recursively matches a nested Gradio group. This is
recorded as `GAP-01` in `04-07-GAPS.md`, with an actual screenshot at
`evidence/ui/phase4/VQ-01.png` (SHA-256
`12be2e55e45f78ddee0f8c6cdbc9cce4ffdd4c494192d63c2c22c6ef61fd10cc`).

Per the plan's verification-only contract, no source or CSS was changed.
VQ-02 through VQ-15, final browser screenshots, `visual-qa.json`, final Phase
4 acceptance and independent verification are intentionally blocked pending a
new explicit UI gap plan.

## Handoff

`04-08-PLAN.md` owns the production UI layout repair and required browser
regeneration. After it passes, rerun Plan 04-07 Task 4 from a clean browser
evidence directory; do not treat the current VQ-01 screenshot as a passing
course-demo result.
