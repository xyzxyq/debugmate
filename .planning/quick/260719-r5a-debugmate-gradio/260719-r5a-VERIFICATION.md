---
quick_id: 260719-r5a
status: passed
verified_on: 2026-07-19
source_commit: 57613c9
---

# Quick Task 260719-r5a Verification

## Result

All Task 3 requirements passed.

## Checks

| Check | Exact command or method | Result |
|---|---|---|
| Real Edge truth states | `./scripts/run-phase4-truth-state-qa.ps1 -TestExpression 'vq_02 or vq_06 or vq_07'` | `2 passed, 43 deselected in 98.65s` |
| Screenshot provenance | Sort `evidence/ui/phase4/staging/*` by `LastWriteTime`; compare latest `894b540bfb974cdcadc972d2ccf97322` with accepted `89b99c394cf545679ab1dafa17ba204e` | Three PNG byte lengths and SHA-256 values identical |
| Visual inspection | Open all three PNGs from latest staging `894b540bfb974cdcadc972d2ccf97322` with the image viewer at original detail | Completed, TTS-partial, and card-partial states are legible, continuously dark, three-column, full-page Edge captures; audio surface is dark |
| Screenshot geometry | Pillow inspection | `1366x1087`, `1366x1357`, `1366x1357`; manifest viewport contract remains `1366x768`, `full_page` |
| Dark palette | Count pixels with RGB channels at most `(25,30,35)` and pixels within 3 levels of `#0b0f14` | Dark: `77.7151%`, `78.0217%`, `72.7722%`; near canvas: `40.8609%`, `40.1378%`, `34.7033%` |
| PPT build | `& 'C:\Users\20795\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\build-course-ppt.py` | Exit 0 |
| PPT package | Open PPTX as ZIP; count members matching `^ppt/slides/slide\d+\.xml$` | Exactly 13 |
| Video build | `.\.venv\Scripts\python.exe scripts\build-course-video.py` | Exit 0 |
| Video duration | `ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 deliverables\DebugMate-V0.1-demo.mp4` | `358.922982` seconds, greater than 180 |
| Video decode | `ffmpeg -v error -i deliverables\DebugMate-V0.1-demo.mp4 -f null NUL` | Exit 0, no decode errors |
| Manifest integrity | Recompute every referenced file byte length and SHA-256 from `evidence/course-v0.1/manifest.json`, `deliverables/asset-manifest.json`, and `deliverables/video-manifest.json` | 10 unique referenced files verified, 0 mismatches |
| Evidence tests | `.\.venv\Scripts\python.exe -m pytest -q tests\test_evidence.py` | 39 passed in 1.90s |
| Diff hygiene | `git diff --check` | Pass |

## Manifest anchors

- Evidence manifest source commit: `57613c9`.
- PPTX: 492927 bytes, SHA-256 `3522a589932ae37cb4c6c6c0aa493cbca5773e047ffaf7ecca98f585fb6b87a9`.
- MP4: 10469035 bytes, SHA-256 `78464aadd30599bbc2d6776f062b001be6022f34b56000fb0fe021cd4aaecb1b`.

## Verdict

`passed` — course-facing evidence and derived deliverables match the final dark workbench UI and are machine-verifiable.
