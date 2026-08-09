---
phase: 07-real-input-privacy-ui
document: ui-review-fix
status: complete
audited_review: 07-UI-REVIEW.md
completed: 2026-08-10
commits:
  - 625c9e1
  - 35e8fc7
  - f9f2fd9
  - e8ddbfa
  - 84a662c
  - daf1d95
  - f5fd526
  - 9044085
  - 5d38def
  - a5331bf
  - 8d91aab
  - fd37757
evidence_run_id: p7qa_45b179b0439b471da0c3d50735496916
---

# Phase 07 UI Review Remediation

## Outcome

The Phase 07 privacy workflow now uses the wide diagnosis workspace for redacted preview content, hides empty preview media without removing stable component contracts, keeps both numbered actions in the desktop first screen, and stacks to one column at 200% browser zoom. Exact Phase 07 copy, local-preprocessing truth, Chinese upload guidance, interaction/status color separation, and the locked font/spacing tokens are restored.

The Phase 04 result IDs, output ordering, replay, correction, retry, media, and download contracts remain unchanged. Privacy token, revision, root-confinement, hash validation, OCR failure, raw-upload deletion, and race protections remain intact.

Iteration 2 closes the updated review's remaining top three items: the wide side is now an independent `.right-workspace-stack` with an exact 16 px vertical gap, replay hides the complete live privacy workspace while retaining its rail disclosure, and ready previews render exact compact missing-category rows without blank JSON/Image/Textbox surfaces. Stable preview selectors remain mounted through display-contents slots, while the original supplied-value component types and callback positions remain intact.

## Before / After Evidence

| Area | Before (`07-UI-REVIEW.md`) | After |
|---|---|---|
| Preview placement | Preview fields and screenshot were compressed into the 320–360 px rail. | `#privacy-overview` and `#privacy-preview` live in the wide `.privacy-workspace`; ready text, image, and audit use the available width. |
| Empty state | Empty Textbox/JSON/Image surfaces extended the rail and displaced actions. | Empty preview controls use Gradio `visible="hidden"`; supplied fields are revealed progressively by server callback updates. |
| First screen | Step 1 and Step 2 followed all empty preview components. | Both actions immediately follow the real input/optional disclosure and are visible in the 1366×768 idle capture. |
| Responsive wrapper | Layout relied on nested duplicated-ID `:has(...)` selectors. | Stable `.workbench-layout` selectors and an explicit high-resolution zoom fallback contain the layout; no `:has` remains. |
| 200% zoom | Full-page evidence visibly retained clipped desktop columns. | Live geometry is one 587 px column at 683 CSS px; the formal zoom capture is a true 1366×768 physical viewport at DPR 2, with both actions in frame and no clipped right edge. |
| Copy | Initial mode, field labels, placeholder, limits, ready/missing text, and privacy note diverged. | Exact UI-SPEC strings are present, including `● 诊断我的报错（本地预处理）`, detailed PNG/JPEG limits, and the Phase 07 local-only note. |
| Upload | Native English upload copy dominated the otherwise Chinese interface. | Visible native upload text is localized to `拖放 PNG/JPEG 截图，或点击上传`, with the locked size/pixel/OCR guidance directly below. |
| Tokens | Interaction and information status both used `#0056B3`; the font stack was implicit; a 12 px margin remained. | Interaction/focus uses `#007AFF`, information status keeps `#0056B3`, the exact UI font stack is explicit, and the correction margin uses the 16 px spacing token. |
| Wide-stack spacing (iteration 2) | The privacy and diagnosis regions occupied independent grid rows whose visual spacing could depend on the tall left rail. | `.right-workspace-stack` owns privacy, diagnosis, and results as one vertical flex stack with an exact 16 px gap; the rail no longer spans two grid rows. |
| Replay privacy state (iteration 2) | Replay results retained the unused live privacy preview surface above the diagnosis. | Replay appends one visibility update to the result tuple and hides `.privacy-workspace`; the replay badge, helper, selector, and action remain in `.control-rail`. |
| Missing categories (iteration 2) | Missing code/environment/screenshot were hidden or rendered through unsuitable JSON/Image placeholders. | Ready state shows exact compact read-only rows `未提供代码。`, `未提供环境信息。`, and `未提供截图。`; idle stays hidden and supplied values still use the original Textbox/JSON/Image controls. |

Direct inspection of the final regenerated `P7-VQ-01`, `P7-VQ-02`, `P7-VQ-07`, and `P7-VQ-11` confirms the exact 16 px stack rhythm, compact missing rows without blank surfaces, replay privacy collapse, Chinese upload surface, and unclipped zoom action frame.

## TDD and Verification

- RED contracts covered stable wrapper behavior, no `:has`, exact copy/tokens/font, hidden idle preview surfaces, first-768 action bounds, responsive region ordering, computed single-column zoom, major-region/content right bounds, and exact zoom capture dimensions.
- Focused app/real-input/local-live regression: **61 passed**.
- Focused runner transaction/ledger/inventory gates: **25 passed**.
- Focused replay regression after output-position repair: **6 passed**.
- Focused real Edge replay + zoom: **2 passed**.
- Production RapidOCR formal gate: **1 passed**, zero skips/failures/errors.
- Formal real Microsoft Edge gate: **10 passed**, 109 deselected, zero skips/failures/errors.
- Iteration 2 focused real Edge coverage: spacing/replay/responsive/zoom **6 passed**; missing/supplied preview states **2 passed**; the single transient P7-VQ-08/1024 page-load timeout passed on its isolated rerun.
- Formal evidence: exactly **9 JSON + 9 PNG** files from final run `p7qa_45b179b0439b471da0c3d50735496916`, with current timestamps and screenshot SHA-256 binding.
- Frozen scope: **14/14** tracked targets match the captured baseline.
- Secret/path scan: **0 findings across 37 files**.
- Repository pytest: **1008 passed, 58 deselected, 1 pre-existing failure**. The sole failure is the already-deferred command-safety baseline for `src/debugmate/dify_live_evidence.py: subprocess`, outside this remediation's files and scope.
- Ruff: **all checks passed**.

## Atomic Runner History

All unsuccessful formal runs restored the prior evidence set and left no staging/backup residue:

1. The first attempt passed OCR but the owned UI process exited before Edge `/config`; the runner was reordered to finish peak-memory OCR initialization before server startup.
2. Direct visual inspection found the old full-page zoom capture still clipped. Stronger computed-grid and content-edge assertions were added.
3. A misplaced media-rule tuple shifted replay outputs from 55 to 56; focused replay tests caught it and the CSS was moved back into `WORKBENCH_CSS`.
4. Playwright `full_page=True` changed the responsive breakpoint during zoom capture. `P7-VQ-11` now uses the true DPR-2 viewport and asserts its 1366×768 physical dimensions.
5. Iteration 2's first promoted run exposed `gr.JSON` decoration around a missing-environment string during direct visual inspection. Dedicated read-only absence rows restored exact copy while leaving supplied JSON/Image rendering unchanged.
6. A second visual inspection showed Gradio's string `visible="hidden"` semantics retained empty ready-state containers. Boolean-hidden child components inside stable display-contents selector slots removed those surfaces without removing stable IDs.

Each superseded evidence set was transactionally replaced; only the final all-green run remains in the exact nine-pair inventory.

## Residual Minor Items

- Gradio's internal file input retains an English accessibility label even though all visible uploader copy and detailed guidance are Chinese. Replacing native file semantics or injecting JavaScript would violate the Phase 07 native-component boundary, so this is intentionally left as a minor framework limitation.
- The ready screenshot is intentionally shown at evidence-review scale; its deterministic redaction and root/hash checks take precedence over decorative image treatment.
- The formal inventory remains the plan-locked nine scenario/viewport pairs. The existing real Edge 375×812 test remains green without adding an unapproved tenth evidence pair.

## Scope Confirmation

No PPTX, MP4, SRT, course-final screenshot, Phase 04 evidence, or Phase 08–10 artifact was modified by this remediation. `.planning/STATE.md` was not touched or staged.
