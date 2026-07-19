# DebugMate V0.1 Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish a stable Windows course-demo V0.1 and its PPT/video source material without public-deployment or production-release gates.

**Architecture:** Keep the existing strict diagnosis/result pipeline and Gradio workbench. Finish only representative UI accessibility, one positive ZIP download verification, a small evidence/case set, and course deliverables. Existing hardening remains, but no new release-grade transaction or fault-matrix infrastructure is added.

**Tech Stack:** CPython 3.13, Gradio 6, Pydantic 2, Pillow, local SAPI/FFmpeg, pytest, Playwright Edge, PowerPoint/Python document tooling.

## Global Constraints

- V0.1 runs locally on Windows and is not publicly deployed.
- Report, PNG, MP3, and ZIP must derive from one verified diagnosis object.
- Screenshots and video use real runs only.
- No new paid API or subscription is introduced.
- Dify/LLM remains an optional enhancement path; deterministic local replay is the recording-safe fallback.
- Representative verification replaces exhaustive release certification.

---

### Task 1: Close the Current Accessible Demo UI

**Files:**
- Modify: `src/debugmate/ui/app.py`
- Modify: `tests/ui/test_app.py`
- Modify: `tests/ui/test_browser.py`

**Interfaces:**
- Consumes: `CallbackPayload.view.accessible_status`, verified fact/citation/command rows.
- Produces: one keyboard-reachable workbench and stable Markdown read-only tables.

- [ ] **Step 1: Preserve the RED evidence**

Record that the original UI lacked an `aria-live` status, read focus styles during transition, exposed focusable hidden tab duplicates, and trapped Tab inside read-only Dataframes.

- [ ] **Step 2: Finish the minimal implementation**

Use one controlled live-region template fed only by `accessible_status`; render fact, citation, and command rows as escaped Markdown tables; hide Gradio's `aria-hidden` duplicate tab container; keep a stable 2 px focus outline.

- [ ] **Step 3: Run representative tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py tests\ui\test_view_state.py tests\ui\test_callbacks.py
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "vq_13 or vq_15"
.\scripts\run-phase4-truth-state-qa.ps1 -TestExpression 'vq_14'
```

Expected: all selected tests pass; no skipped selected VQ remains.

- [ ] **Step 4: Run one regression sample**

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "long_content"
```

Expected: the long report/command and tall-card sample passes.

- [ ] **Step 5: Commit**

```powershell
git add src/debugmate/ui/app.py tests/ui/test_app.py tests/ui/test_browser.py
git commit -m "fix(04-11): finish accessible V0.1 workbench"
```

### Task 2: Add One Positive Same-Run Download Check

**Files:**
- Modify: `tests/ui/test_browser.py`
- Modify only if required: `src/debugmate/ui/app.py`

**Interfaces:**
- Consumes: the visible `source_run_id`, browser download response, existing result ZIP manifest.
- Produces: `_verify_v01_download(bytes, visible_source_run_id) -> None`.

- [ ] **Step 1: Write the failing positive-path test**

Add one Edge test that activates the completed replay, captures the actual HTTP response body for `debugmate-result.zip`, and compares the ZIP manifest `source_run_id` with the visible metadata.

- [ ] **Step 2: Run RED**

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "v01_download"
```

Expected: fail because the current helper reads Playwright's temporary path or lacks the same-run comparison.

- [ ] **Step 3: Implement only the positive validator**

Validate response status, MIME, exact filename, bounded size, ZIP readability, manifest presence, checksums, and `source_run_id`. Do not add an adversarial filename/ZIP fault matrix.

- [ ] **Step 4: Run GREEN and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "v01_download"
git add tests/ui/test_browser.py src/debugmate/ui/app.py
git commit -m "test(04-11): verify V0.1 result download"
```

### Task 3: Produce the Small Course Evidence Set

**Files:**
- Create: `evidence/course-v0.1/manifest.json`
- Create: `evidence/course-v0.1/screenshots/`
- Create or update: `fixtures/replay/index.json`
- Create: `docs/course/v0.1-demo-cases.md`

**Interfaces:**
- Consumes: verified replay cases and real browser screenshots.
- Produces: 3–5 case descriptions and a simple hash manifest for recording material.

- [ ] **Step 1: Select representative cases**

Use completed replay, long-content completed, TTS partial/fallback, and safe source failure. Add a fifth corrected-run case only if already stable.

- [ ] **Step 2: Capture real screenshots**

Capture one completed overview, one long-content/commands view, one partial/fallback view, one safe failure, and one download/result identity view.

- [ ] **Step 3: Write a simple manifest**

Record only relative path, SHA-256, viewport, case label, status, and capture date. Do not implement immutable generations, atomic pointers, or failure injection.

- [ ] **Step 4: Verify and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py tests\results
git diff --check
git add evidence/course-v0.1 docs/course/v0.1-demo-cases.md fixtures/replay/index.json
git commit -m "docs: add DebugMate V0.1 course evidence"
```

### Task 4: Build the Course Submission Package

**Files:**
- Create: `docs/course/README.md`
- Create: `docs/course/presentation-outline.md`
- Create: `docs/course/video-script.md`
- Create: `deliverables/DebugMate-V0.1.pptx`
- Create: `deliverables/asset-manifest.json`

**Interfaces:**
- Consumes: V0.1 evidence manifest, knowledge sources, prompts, workflow description, screenshots, PNG, and MP3.
- Produces: the final PPT and a recording-ready script longer than 3 minutes.

- [ ] **Step 1: Write the course narrative**

Cover problem background, tools, knowledge base, workflow, prompt iterations, privacy preview, multimodal outputs, representative tests, limitations, and future improvements.

- [ ] **Step 2: Generate the PPT**

Use 10–14 slides with real screenshots and concise speaker notes. Clearly label fixed replay versus live/local diagnosis.

- [ ] **Step 3: Write the video script**

Target 5–7 minutes: 1 minute background, 2 minutes workflow/demo, 1.5 minutes multimodal results, 1 minute prompt/issues, 0.5 minute conclusion.

- [ ] **Step 4: Validate the package**

Check that every referenced file exists, images render, MP3 plays, no placeholder remains, and the script exceeds 3 minutes at normal Mandarin speech speed.

- [ ] **Step 5: Commit**

```powershell
git add docs/course deliverables
git commit -m "docs: assemble DebugMate V0.1 course submission"
```

## Self-Review

- The plan covers every V0.1 must-have in the approved scope design.
- No public deployment, atomic evidence publication, exhaustive attack matrix, or full 15-row gate remains.
- Each task ends with a runnable demonstration or course artifact.
- No paid external dependency is introduced.
