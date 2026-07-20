---
phase: 04-multimodal-results-ui
plan: 08
status: completed_with_gap
completed: 2026-07-15
---

# Plan 04-08 Summary — layout repaired, semantic VQ-01 still open

## Delivered repair and evidence

- `2269ff194464d54d6fdaea685952e203ee77711c` preserved the original
  GAP-01 screenshot and established the RED browser baseline.
- `5cb361142a7aea9d500abb042c7a7aa31ea7f247` scoped the Gradio workbench
  grid once and kept the selected input explicitly replay-only.
- `97e11405113461b20ce8a8502bd7aa8ea9d6ed12` covered the 1024 px and
  768 px responsive layouts in real Edge.
- `2d4aa5b3f05ec7d34cfb51c98dc472f4c0e930dc`,
  `171e72e11fcf36309d0ef170a499f19f67b61f66`, and
  `fd9e83ea287c6314ae75ef0df7aea5ab29dcd430` established one server owner,
  guaranteed cleanup on failure, and made `/config` root validation strict.

The final 1366 x 768 Edge measurement was `280`, `373.328125`, and
`466.671875` px for the three regions, with body width `1366/1366` and no
horizontal overflow. The inspected screenshot visibly contains the status
bar, three workbench headings, selected fixed replay case and replay action;
it remains idle geometry evidence, not a completed/live VQ result.

Evidence hashes at final verification:

- original `VQ-01.png` and archived failure:
  `12be2e55e45f78ddee0f8c6cdbc9cce4ffdd4c494192d63c2c22c6ef61fd10cc`;
- repaired layout screenshot:
  `e3d839f4c5ac745d1f75280def49be77889de8eb64c6aab09eca7705aeda5699`.

## Fresh verification on 2026-07-15

- `pytest -q tests/ui/test_app.py`: `8 passed`, exit `0`.
- `pytest -q -m browser tests/ui/test_browser.py`: `19 passed`, exit `0`.
- `scripts/run-phase4-browser-layout-qa.ps1`: `16 passed, 3 deselected`,
  exit `0`; its captured server stopped and port `59832` was confirmed closed.
- complete default `pytest`: collected `773`; `727 passed, 46 deselected`,
  one existing Starlette/httpx deprecation warning, explicit
  `PYTEST_EXIT_CODE=0`.
- Ruff: exit `0`; `pip check`: exit `0`; `git diff --check`: exit `0`.
- required product-tree secret scan: exit `1`, the expected clean/no-match
  result.
- final process inspection found no project-owned `pytest` or
  `debugmate.ui.serve` process, and no listener remained on runner port
  `59832`.

## Truthful remaining state

CSS geometry and deterministic server ownership are repaired. Semantic VQ-01
is still OPEN until a fresh, non-replay
`ApprovedRedactedInput -> DiagnosisWorkflow -> ResultViewState` execution
proves `mode=live`, `fixture_id=None`, new run/result identities, and explicit
local-rule provenance. `04-09-PLAN.md` owns that work; VQ-02 through VQ-15 and
the full visual ledger remain open.

The prior Dify and edge-TTS gates retain their recorded clean-skipped/open
status, and human listening retains `human_needed`. They were not rerun or
relabeled by 04-08. The original `04-07` GAP-01 record remains unchanged.
