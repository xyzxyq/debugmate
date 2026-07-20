# DebugMate Dark Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current light three-column Gradio debug page with a refined dark developer command center while preserving all business, identity, accessibility, replay, correction, degradation, and download contracts.

**Architecture:** Keep the existing Gradio components and callback graph as the behavioral source of truth. Recompose only container hierarchy and `elem_classes`, drive appearance through one tokenized CSS string, and update browser assertions that encode the old geometry. Regenerate course evidence and derived PPT/video after the UI passes real Edge verification.

**Tech Stack:** Python 3.13, Gradio 6.20, CSS, pytest, Playwright Microsoft Edge, Pillow, FFmpeg.

## Global Constraints

- Preserve every existing `elem_id`, callback signature, output list position and service contract.
- Do not add React, Tailwind, JavaScript UI frameworks, remote fonts or paid services.
- Use `#0b0f14`, `#111820`, `#17212b`, `#e8edf2`, `#91a0ad`, `#293642`, `#27b3c2`, `#e7a84b`, `#ef6b73`, and `#4ecb8d` as the fixed design tokens.
- Keep native Tabs, Accordion, Audio and Download controls keyboard reachable.
- Course screenshots must be real Edge captures from the implemented UI.

---

### Task 1: Tokenized Dark Workbench and Stable Component Structure

**Files:**
- Modify: `src/debugmate/ui/app.py`
- Modify: `tests/ui/test_app.py`

**Interfaces:**
- Consumes: `ComponentViewModel`, existing Gradio components and callback outputs.
- Produces: CSS classes `command-bar`, `control-rail`, `diagnosis-canvas`, `result-workspace`, `section-kicker`, and `correction-panel`.

- [ ] **Step 1: Replace the old visual contract assertions**

Update `test_build_app_has_native_three_region_workbench_and_no_unsafe_components` to require the ten fixed color tokens, the six new classes, three breakpoint rules, one controlled `gr.HTML`, and all existing important `elem_id` values. Keep the assertion forbidding scripts and unsafe HTML.

- [ ] **Step 2: Run the focused test and record RED**

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py -k "native_three_region or unsafe_components"
```

Expected: failure because the new tokens/classes are absent.

- [ ] **Step 3: Recompose the Gradio containers without changing components**

In `build_app()`, add `elem_classes="command-bar"` to the sticky status group; add `control-rail`, `diagnosis-canvas`, and `result-workspace` beside the existing `region` classes; keep the fact table high enough that the key traceback row remains above the fold; move the extraction-field inputs, correction draft, correction action and confirmation accordion inside a default-closed `gr.Accordion("抽取字段与纠错", open=False, elem_classes="correction-panel")`. Do not recreate or reorder `result_outputs`, and do not add selected-tab state.

- [ ] **Step 4: Replace `WORKBENCH_CSS` with the fixed tokenized theme**

Implement the spec colors, 280px/360px/460px desktop grid, 300px + 1fr tablet grid, single-column mobile grid, compact controls, dark Markdown tables, restrained Tabs, local scroll regions and visible focus. Use only CSS; no scripts or external assets.

- [ ] **Step 5: Run unit and contract tests**

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py tests\ui\test_view_state.py tests\ui\test_callbacks.py
.\.venv\Scripts\python.exe -m ruff check src\debugmate\ui\app.py tests\ui\test_app.py
```

Expected: all selected tests and Ruff pass.

- [ ] **Step 6: Commit**

```powershell
git add src/debugmate/ui/app.py tests/ui/test_app.py
git commit -m "feat(ui): add dark command center"
```

### Task 2: Responsive and Accessible Edge Verification

**Files:**
- Modify: `tests/ui/test_browser.py`
- Modify only when a test exposes a real defect: `src/debugmate/ui/app.py`

**Interfaces:**
- Consumes: `.control-rail`, `.diagnosis-canvas`, `.result-workspace`, existing IDs and native controls.
- Produces: real Edge evidence for desktop, tablet, mobile, keyboard, zoom, long content and download.

- [ ] **Step 1: Update geometry-only tests**

At 1366px require all three logical regions above the fold with minimum widths 280/360/440. At 1024px require the control rail on the left and the other regions in the right grid flow. At 768px require ordered single-column stacking and visible replay controls. Preserve no-overflow checks.

- [ ] **Step 2: Run responsive tests and fix only observed layout failures**

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "responsive or gap_01"
```

Expected: all selected layout tests pass.

- [ ] **Step 3: Run the representative interaction matrix**

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "vq_13 or vq_15 or long_content or v01_download"
.\scripts\run-phase4-truth-state-qa.ps1 -TestExpression 'vq_14'
```

Expected: keyboard order, status announcement, 200% zoom, long content, same-run ZIP and grayscale status tests pass.

- [ ] **Step 4: Run formatting and commit**

```powershell
.\.venv\Scripts\python.exe -m ruff check src\debugmate\ui\app.py tests\ui\test_browser.py
.\.venv\Scripts\python.exe -m ruff format --check src\debugmate\ui\app.py tests\ui\test_browser.py
git add src/debugmate/ui/app.py tests/ui/test_browser.py
git commit -m "test(ui): verify dark command center"
```

### Task 3: Replace Course Evidence and Rebuild Deliverables

**Files:**
- Replace: `evidence/course-v0.1/screenshots/*.png`
- Modify: `evidence/course-v0.1/manifest.json`
- Regenerate: `deliverables/DebugMate-V0.1.pptx`, `deliverables/asset-manifest.json`, `deliverables/DebugMate-V0.1-demo.mp4`, `deliverables/video-manifest.json`
- Create: `.planning/quick/260719-r5a-debugmate-gradio/260719-r5a-SUMMARY.md`
- Create: `.planning/quick/260719-r5a-debugmate-gradio/260719-r5a-VERIFICATION.md`
- Modify: `.planning/STATE.md`

**Interfaces:**
- Consumes: real Edge screenshots at the fixed evidence paths.
- Produces: course materials whose embedded UI matches the implemented dark workbench.

- [ ] **Step 1: Capture the three current-code states**

Run `.\scripts\run-phase4-truth-state-qa.ps1 -TestExpression 'vq_02 or vq_06 or vq_07'`, identify the newest runner staging directory by `LastWriteTime`, inspect its three PNG files, then copy only the accepted current-run files to the fixed course screenshot paths.

- [ ] **Step 2: Recompute the course evidence manifest**

Use `Get-FileHash -Algorithm SHA256` and `Get-Item.Length` for each PNG. Record those values, keep viewport `1366x768` and capture type `full_page`, and set `source_commit` to the current UI commit.

- [ ] **Step 3: Rebuild PPT and video**

```powershell
& 'C:\Users\20795\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\build-course-ppt.py
.\.venv\Scripts\python.exe scripts\build-course-video.py
```

Expected: PPT contains 13 slides; video duration remains greater than 180 seconds.

- [ ] **Step 4: Verify artifacts and write GSD records**

Open the PPTX as a ZIP and require exactly 13 `ppt/slides/slide*.xml` members; recompute every asset/video/evidence manifest hash; require `ffprobe` duration >180 seconds and `ffmpeg -v error -i ... -f null NUL` exit 0; verify the three fixed screenshots have the new dark canvas pixel palette; run `git diff --check`; write summary and verification with exact test counts; append Quick Task `260719-r5a` to `.planning/STATE.md`.

- [ ] **Step 5: Commit records and regenerated assets**

```powershell
git add .planning/quick/260719-r5a-debugmate-gradio .planning/STATE.md
git add -f evidence/course-v0.1 deliverables
git commit -m "docs(ui): refresh dark workbench evidence"
```

## Self-Review

- The plan covers every approved design requirement and preserves behavioral contracts.
- No placeholder, new dependency, paid service or frontend build system is introduced.
- Every task ends with executable tests and an atomic commit.
