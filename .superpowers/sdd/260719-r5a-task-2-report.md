# 260719-r5a Task 2 — Microsoft Edge Dark Command Center Acceptance

## Status

DONE_WITH_CONCERNS

Commit: pending (`test(ui): verify dark command center`)

## Scope

- Modified only `tests/ui/test_browser.py`.
- Did not modify `src/debugmate/ui/app.py`: the Edge findings were obsolete test geometry/focus assumptions after Task 1's approved layout and native Accordion change, not CSS defects.
- Did not alter callbacks, backend behavior, identity/security checks, download source checks, failure/degradation scenarios, content checks, or accessible-status assertions.
- Left the pre-existing untracked `--help/` and `.debugmate-runtime/` directories untouched.

## Real Browser

- Browser: Microsoft Edge `150.0.4078.83` (`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`).
- Runner: Playwright Chromium channel `msedge`, headless, loopback-only Gradio app.
- Scenarios: desktop 1366x768, tablet 1024x768, mobile 768x1024, keyboard traversal, 2x device metrics (683x384, DPR 2), long content, same-run ZIP download, and test-side grayscale state rendering.

## RED → GREEN

### Responsive/GAP-01

Initial command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "responsive or gap_01"
```

Initial result: `4 failed, 1 passed, 37 deselected in 226.55s`.

- The 1024px responsive test still required the result workspace to span the old two input/evidence columns.
- The three GAP-01 tests still referenced the replaced headings `输入与抽取` / `诊断与证据` / `三模态结果`.

After retargeting only those old-layout assertions, a remaining RED (`1 failed, 4 passed`) showed the former equal-column test also required the desktop fold to contain the replay button. The approved requirement only requires each region to begin above the fold at desktop and requires replay reachability at mobile. The test therefore retains replay visibility while checking fold geometry only for the three region headings.

Final result:

```text
5 passed, 37 deselected in 92.85s
```

The final assertions require role-specific selectors, desktop minimum widths `280/360/440`, no whole-page horizontal overflow, a 300px tablet control rail with diagnosis then result on the right, and mobile ordered stacking with reachable replay controls.

### Keyboard and 2x zoom

Initial command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "vq_13 or vq_15 or long_content or v01_download"
```

Initial result: `2 failed, 2 passed, 38 deselected in 168.84s`.

- `vq_13` expected fields inside the approved default-closed `抽取字段与纠错` native Accordion to be initially tab-reachable.
- `vq_15` attempted to scroll directly to an action inside that closed Accordion.

The browser tests now use keyboard Space to open the native Accordion, assert it becomes open, then retain the original field, confirmation, command Accordion, tab, audio, download, and clipping assertions. A follow-up focused `vq_15` run passed before the final full rerun.

Final result:

```text
4 passed, 38 deselected in 144.94s
```

This covers keyboard/status (`vq_13`), 200% zoom (`vq_15`), long content, and same-run ZIP download (`v01_download`).

### Grayscale truth-state QA

Command:

```powershell
.\scripts\run-phase4-truth-state-qa.ps1 -TestExpression 'vq_14'
```

Final result:

```text
1 passed, 41 deselected in 25.34s
```

The runner exercised completed/replay, partial-completion, and safe-failure statuses under test-side grayscale, retaining icon and text assertions.

## Static Checks

```powershell
.\.venv\Scripts\python.exe -m ruff check src\debugmate\ui\app.py tests\ui\test_browser.py
```

Result: `All checks passed!` (exit 0).

```powershell
.\.venv\Scripts\python.exe -m ruff format --check src\debugmate\ui\app.py tests\ui\test_browser.py
```

Result: exit 1; `tests/ui/test_browser.py` is formatted, but Ruff reports `Would reformat: src\debugmate\ui\app.py`.

`git diff --check` passed before the final verification cycle.

## Self-review

- The changed tests remain role/class based rather than relying on incidental Gradio region order.
- Desktop verifies all three intended regions start before the 768px fold; it no longer imposes an unsupported requirement that a lower control in the taller control rail must also fit above that fold.
- Tablet and mobile assertions directly encode the approved responsive contract and retain no-whole-page-overflow checks.
- The Accordion changes verify, rather than bypass, keyboard access to the previously asserted controls.
- No browser failure demonstrated a CSS defect, so no application CSS or behavior was changed.

## Concern

`src/debugmate/ui/app.py` has pre-existing Ruff-format drift. Formatting it would be an unrelated source-file modification and conflicts with this Task 2 boundary, which permits application changes only for an actual Edge-found CSS/accessibility defect. This is the only reason for `DONE_WITH_CONCERNS`.
