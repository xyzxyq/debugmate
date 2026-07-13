---
phase: 04
slug: multimodal-results-ui
status: verified
shadcn_initialized: false
preset: none
created: 2026-07-13
verified: 2026-07-13
ui_safety_gate: passed
primary_viewport: 1366x768
framework: gradio-6-blocks
---

# Phase 04 — UI Design Contract

> DebugMate 三模态诊断工作台的视觉与交互合同。实现、测试和视觉验收均以本文件为准；本阶段不包含 Phase 5 评测界面或 Phase 6 课程包装。

---

## Design Intent

DebugMate 是专业诊断工具，不是营销落地页。页面打开后第一屏直接呈现状态与工作区，不设置 hero、宣传插画、功能轮播、价格卡或大面积品牌留白。信息密度应接近 IDE 的“问题/证据/结果”工作台：紧凑、稳定、可扫描，但正文与命令仍须舒适可读。

视觉层不得创造运行真实性：`live`、`replay`、`completed`、`partial`、`failed` 和 TTS fallback 均来自严格 `ResultViewState`/manifest；状态必须同时使用图标、中文文字和颜色，不能仅靠颜色表达。

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | Gradio 6.20.0 native Blocks/components |
| Icons | Unicode text-safe symbols limited to `●`、`▶`、`✓`、`⚠`、`✕`、`↺`; icons always accompanied by text |
| UI font | `Inter`, `Segoe UI`, `Microsoft YaHei UI`, `Microsoft YaHei`, sans-serif |
| Monospace | `Cascadia Mono`, `Consolas`, monospace |
| Styling | one small versioned CSS string passed to `gr.Blocks(css=...)`; no JS framework and no external CDN |
| Theme | light professional workbench; system-independent fixed light palette for reproducible screenshots |

Gradio native components are the interaction authority. CSS may set tokens, grids, density, borders, focus rings, and bounded scroll regions; it must not restyle controls so heavily that native disabled/loading/focus behavior becomes ambiguous.

## Layout Contract

### Primary frame: 1366 × 768

- App content width: `min(100%, 1440px)`, centered; at 1366 px use 16 px page gutters.
- Top status bar: 56 px minimum height, sticky within the page top; one line at desktop, wrapping to two lines only below 1100 px.
- Main workbench: three visible regions in a 12-column grid with 16 px gutters:
  - **输入与抽取** — 3 columns, minimum 280 px.
  - **诊断与证据** — 4 columns, minimum 360 px.
  - **三模态结果** — 5 columns, minimum 440 px.
- At 1366 × 768, the top bar, all three region headings, the primary action, current status, and result tabs must be visible without horizontal scrolling. Long content may scroll inside bounded panels; the whole page must not create nested horizontal scrollbars.
- Region surfaces use 1 px border and 8 px radius. Do not use floating glass panels, gradients, oversized shadows, decorative blobs, or full-width banner art.
- Results region uses native `Tabs`: `文字报告` / `诊断卡` / `语音复盘` / `引用与下载`. The active tab must remain keyboard reachable. Tabs control vertical length; they do not conceal the overall outcome status.
- Input screenshot and long details use `Accordion` with explicit labels. The six extracted fields remain visible as a compact editable group; they are not hidden behind six separate accordions.

### Component hierarchy

```text
gr.Blocks #debugmate-app
├─ Header #status-bar
│  ├─ product label “DebugMate 诊断工作台”
│  ├─ case ID + source run ID (truncated visually, full accessible value)
│  ├─ mode badge: 实时 / 离线回放
│  ├─ outcome badge: 等待 / 运行中 / 已完成 / 部分完成 / 失败
│  └─ backend + fallback notice
├─ Main #workbench-grid
│  ├─ Section #input-extraction
│  │  ├─ replay fixture Dropdown (allowlist values only)
│  │  ├─ redacted input Textbox
│  │  ├─ redacted Image preview (Accordion)
│  │  ├─ six explicit extraction fields
│  │  ├─ correction change summary
│  │  ├─ “确认修改并重新诊断” Button
│  │  └─ correction confirmation panel
│  ├─ Section #diagnosis-evidence
│  │  ├─ category + confidence
│  │  ├─ root-cause candidates with “有依据/推断” labels
│  │  ├─ fact/evidence cross-reference Dataframe
│  │  ├─ command details Accordion
│  │  └─ failure/retry details panel
│  └─ Section #multimodal-results
│     ├─ result identity + availability summary
│     ├─ Tabs
│     │  ├─ Markdown report
│     │  ├─ Image card
│     │  ├─ Audio player + recap text
│     │  └─ citations Dataframe + native File/DownloadButton
│     └─ persistent action row: retry eligible stage / download bundle
└─ Footer #runtime-note
   └─ privacy + “命令仅供查看，不会自动执行”
```

## Spacing Scale

All declared spacing values are multiples of 4.

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4 px | icon/text gap, badge internal gap |
| `space-2` | 8 px | inline controls, compact row gap |
| `space-3` | 12 px | field stack, panel internal grouping |
| `space-4` | 16 px | grid gutter, region padding, page gutter |
| `space-5` | 20 px | major subsection separation |
| `space-6` | 24 px | heading-to-major-content separation |
| `space-8` | 32 px | only between vertically stacked regions below tablet breakpoint |

Exceptions: 1 px borders and 2 px focus outline are non-spacing dimensions. No 40–64 px decorative gaps; vertical space is reserved for evidence and results.

## Typography

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Metadata | 12 px | 500 | 1.4 | IDs, backend, generation/version data |
| Label | 13 px | 600 | 1.4 | fields, badges, table headers |
| Body | 14 px | 400 | 1.55 | descriptions, evidence, failure guidance |
| Body strong | 14 px | 600 | 1.5 | root causes, available results |
| Section heading | 16 px | 650 | 1.35 | three region titles, tab subsection titles |
| Page title | 18 px | 700 | 1.3 | `DebugMate 诊断工作台` only |
| Code/traceback | 13 px | 400 | 1.55 | commands, package names, traceback lines |

- No display typography above 20 px. The product name must not displace diagnostic content.
- Chinese text uses the UI stack; commands, exception names, package versions, stable IDs, hashes, and redacted paths use monospace.
- Report Markdown may render H2 at 18 px and H3 at 16 px but must not exceed the page title.
- Do not use all-caps English labels except canonical technical values such as `MP3`, `PNG`, `SHA-256`, `TTS`.

## Color Tokens

| Token / role | Value | Usage |
|--------------|-------|-------|
| `--bg-canvas` | `#F4F6F8` | page background |
| `--bg-surface` | `#FFFFFF` | region and control surfaces |
| `--bg-subtle` | `#F8FAFC` | metadata rows, table alternate background |
| `--border` | `#CBD5E1` | panel/control borders |
| `--border-strong` | `#94A3B8` | active region and separators |
| `--text` | `#172033` | primary text |
| `--text-muted` | `#526174` | secondary text; never below this contrast on white |
| `--accent` | `#2457D6` | primary action, active tab, focus-related emphasis |
| `--accent-hover` | `#1D46AE` | primary action hover |
| `--info-bg` / `--info-text` | `#E8F1FF` / `#174EA6` | live/running information |
| `--success-bg` / `--success-text` | `#E8F7EE` / `#176B3A` | completed |
| `--warning-bg` / `--warning-text` | `#FFF4D6` / `#7A4B00` | replay, partial, fallback |
| `--danger-bg` / `--danger-text` | `#FDECEC` / `#A12828` | failed and destructive confirmation |
| `--focus` | `#1D4ED8` | 2 px keyboard focus outline |

The 60/30/10 balance is canvas/surface/accent-and-status. Accent is reserved for the main submit/retry action, active tab underline, links, and keyboard focus. It is not applied to every border, heading, or badge. `partial`, `replay`, and `fallback` may share warning color but always have distinct literal text.

## State and Visibility Contract

`replay` is an orthogonal mode (`replay=true`), not a substitute for outcome completion. UI implementations may expose a combined view helper, but must preserve both mode and `idle|running|completed|partial|failed` state.

| State | Top status | Main action | Result behavior | Required detail |
|-------|------------|-------------|-----------------|-----------------|
| idle | `● 等待诊断` | `开始诊断` or `加载回放案例` enabled when input/fixture valid | tabs visible but disabled/empty | short next-step empty state |
| running | `▶ 正在生成结果 · {stage label}` | triggering actions disabled; no duplicate submit | retain last verified result only if explicitly labeled `上一结果`; otherwise skeleton/status | ordered completed stages and current stage from queue events |
| completed | `✓ 已完成` | correction and eligible full rerun enabled | all verified available modalities shown | source/backend, identity, full bundle download |
| partial | `⚠ 部分完成` | stage-scoped retry enabled if declared | show every verified artifact; missing tab contains explicit reason, never placeholder media | failed node, completed/inherited stages, retry scope, safe error code, partial ZIP label |
| failed | `✕ 诊断失败` | only safe declared retry/reselect action enabled | no unverified artifacts; verified inherited/previous artifacts clearly separated | failed node, completed/inherited stages, retry scope, safe error code |
| replay mode | separate `↺ 离线回放 · {fixture}` badge in every outcome | live wording prohibited | top bar, result summary, and download metadata identify replay | fixture ID and source run ID; never claim current cloud success |
| fallback active | `⚠ 语音已降级 · {backend}` secondary badge | no special action unless retry scope exists | valid audio remains playable | ordered failed backend(s), final backend, safe fallback reason |

### Loading

- Queue stages use fixed Chinese labels: `验证来源` → `整理诊断` → `生成报告` → `绘制诊断卡` → `生成语音` → `一致性校验` → `发布结果包`.
- Show stage text and indeterminate progress; do not invent percentages.
- Disable diagnosis, replay load, correction confirmation, and retry buttons while the same case is in flight. Keep tabs and existing verified outputs readable.
- Loading copy: `正在{阶段}，请勿重复提交。已完成 {n} 个阶段。`

### Empty

- Heading: `尚未生成诊断结果`
- Body: `提交已脱敏输入，或从固定案例中选择一个回放案例。结果会在此显示文字报告、诊断卡和语音复盘。`
- Evidence empty: `暂无可展示证据。诊断完成后将按事实 ID 与证据 ID 交叉列出。`
- Never show fake sample charts, placeholder audio, or generated “example diagnosis” in an empty live view.

### Error and partial-result panels

Use a compact semantic panel with these literal labels in order:

1. `失败节点`
2. `安全错误码`
3. `已完成阶段`
4. `继承阶段`
5. `仍可使用的结果`
6. `可重试范围`
7. `建议操作`

Do not display raw exception messages, tracebacks, absolute paths, provider response bodies, tokens, or keys.

## Three-Region Interaction Contract

### 1. 输入与抽取

- Redacted text is read-only and labeled `脱敏后的输入`; never label it “原始输入”.
- Screenshot component displays only the approved redacted image. Native image download/share affordances must be off unless the verified result contract explicitly permits them.
- Six explicit extracted fields follow the Phase 3 order and stable field labels. Each field has current value, confidence/provenance where available, and edit state.
- Editing a field changes only the local draft. Show `有 1 项未确认修改` (count varies); do not start a rerun on blur/change.
- `确认修改并重新诊断` opens a confirmation panel summarizing old → new values and this copy: `确认后将创建新的运行和结果；当前证据与结果不会被覆盖。`
- Confirmation actions: primary `创建新运行`; secondary `返回检查`; destructive styling is not used because old evidence is preserved.
- If no field changed, the confirmation action is disabled and helper copy reads `请先修改至少一个抽取字段。`

### 2. 诊断与证据

- Category is a label, not an editable selector.
- Confidence displays a textual level and exact value if present: e.g. `中等 · 0.72`; never a color-only gauge.
- Every root-cause candidate begins with `有依据` or `推断`, followed by stable candidate ID.
- Fact/evidence table columns: `事实 ID` / `观察或结论` / `证据 ID` / `来源` / `支持关系`. IDs and source references must remain copyable.
- Command items are display-only. Each includes `平台`、`影响`、`预期结果`、`回退说明`; no “运行命令”, terminal button, shell callback, or auto-install action is allowed.

### 3. 三模态结果

- Tab order is fixed: report, PNG, audio, citations/download.
- Report uses native `Markdown`; commands remain fenced code blocks and English technical strings remain unchanged.
- PNG uses native `Image`, read-only, `type="filepath"` only from an allowlisted verified result-bundle member. If unavailable: `诊断卡未生成（png_layout_failed）`; do not stretch a placeholder.
- Audio uses native `Audio`, read-only, with browser controls and no recording/upload source. Adjacent metadata shows `语音后端`、`时长`、`是否降级`、`降级原因`. If all TTS failed: show verified `recap.txt` and `语音未生成（tts_failed）` with no empty MP3 control.
- Citations use a native `Dataframe` or compact table with `证据 ID`、`标题`、`官方来源`、`版本范围`; URLs may be clickable only when already present in verified diagnosis evidence.
- Download uses native `DownloadButton` for the deterministic bundle and optional native `File` only for verified individual members. The server supplies paths from a result manifest allowlist; there is no path textbox, directory picker, arbitrary file browser, or callback accepting a user path.
- Completed CTA: `下载完整证据包`; partial CTA: `下载部分结果包`; failed state has no result ZIP unless a verified failure/partial manifest explicitly publishes one.

## Copywriting Contract

| Element | Exact or pattern copy |
|---------|-----------------------|
| Product label | `DebugMate 诊断工作台` |
| Live badge | `● 实时诊断` |
| Replay badge | `↺ 离线回放 · {fixture_name}` |
| Completed badge | `✓ 已完成` |
| Partial badge | `⚠ 部分完成` |
| Failed badge | `✕ 失败` |
| Fallback badge | `⚠ 语音已降级 · {backend}` |
| Primary live CTA | `开始诊断` |
| Correction CTA | `确认修改并重新诊断` |
| Correction confirmation | `确认后将创建新的运行和结果；当前证据与结果不会被覆盖。` |
| Retry CTA | `重试：{retry_scope_label}` |
| Full download | `下载完整证据包` |
| Partial download | `下载部分结果包` |
| Safety note | `诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。` |
| Privacy note | `页面仅展示已验证的脱敏输入与结果。` |
| Generic safe error | `此阶段未完成。请按“可重试范围”操作；详细开发日志不会显示在页面中。` |
| Invalid replay | `回放案例校验失败（replay_bundle_invalid）。请选择其他固定案例。` |
| Invalid source | `来源证据未通过校验（source_bundle_invalid），未生成结果。` |

Avoid promotional or unsupported copy: `AI 一键修复`、`精准定位`、`100% 安全`、`云端运行成功`（replay 中尤其禁止）、`自动执行`、`智能修复已完成`.

## Accessibility Contract

- Text/background contrast must meet WCAG AA: normal text at least 4.5:1, large text at least 3:1; status foreground/background pairs must be tested, not assumed.
- Every icon has adjacent visible text. Badges expose a complete accessible label such as `状态：部分完成`.
- Keyboard focus order follows DOM order: top status → input/replay controls → six fields → correction actions → diagnosis/evidence → result tabs → retry/download. No positive `tabindex` hacks.
- All interactive controls have a visible 2 px focus outline with 2 px offset. Do not remove Gradio’s focus indicator.
- Tabs, accordions, audio controls, and buttons retain native keyboard semantics. Accordion labels state content, not “更多”.
- Field errors appear as text beside the field and in a summary; red border alone is insufficient.
- Running status uses an `aria-live="polite"`-compatible Gradio output region; terminal failed/completed state should be announced once, not on every render.
- Touch targets are at least 40 × 40 px even though desktop is primary. Inline links have a minimum 24 px line box and underline on hover/focus.
- Long IDs/hashes can wrap or be horizontally scrolled within their code cell; they must not force the whole page wider.
- PNG is supplementary. Its essential diagnosis content is duplicated in accessible report/evidence components; alt text follows `诊断卡：{category}，状态{outcome}`.
- Audio is supplementary. `recap.txt` is visible as transcript so no diagnosis information is audio-only.

## Responsive Behavior

| Viewport | Layout |
|----------|--------|
| `>= 1200px` | three-region 3/4/5 grid; sticky 56 px top status; result tabs |
| `900–1199px` | two columns: input 5/12 and diagnosis 7/12; results full width below; top bar wraps |
| `640–899px` | one column; order input → diagnosis → results; action row sticky at bottom only if it does not cover content |
| `< 640px` | basic readable fallback only; one column, badges wrap, tables gain local horizontal scroll; not a Phase 4 primary acceptance target |

- No viewport may have body-level horizontal scrolling at 1366, 1024, or 768 px widths.
- At reduced widths, result tab labels remain literal; do not replace them with icon-only controls.
- Bounded panels use `max-height` only at desktop. On one-column layouts, prefer natural height to avoid nested vertical scroll traps.

## Security and Path UI Rules

- UI callbacks receive strict IDs/models, never a user-entered filesystem path.
- Replay selection values come from the repository allowlist index; the displayed label is not treated as a path.
- Every returned native file path is resolved and verified by the application service against the result manifest immediately before display/download.
- Absolute paths, temp directory names, stack traces, raw provider bodies, and secrets are never rendered in components or toast/error copy.
- No HTML from diagnosis/provider content is inserted with unsanitized `gr.HTML`; diagnosis content is rendered through native Markdown/text/table components with the established safe renderer.
- No command execution component, terminal, subprocess control, or automatic package install is present.

## Visual QA Matrix

All rows require a real browser render from the implemented Gradio app. Screenshot fixtures must use verified redacted cases, never generated mock evidence presented as a run.

| ID | Viewport / input | State | Must verify |
|----|------------------|-------|-------------|
| VQ-01 | 1366×768, default fixed `ModuleNotFoundError` case | completed + live | status and three region headings visible; no overlap/crop/body horizontal scroll; report tab and download CTA reachable |
| VQ-02 | 1366×768, same case | completed + replay | replay shown in top bar, result summary, and download metadata; no current-cloud-success wording |
| VQ-03 | 1366×768 | running at every queue stage | stage copy changes in order; submit/replay/correction/retry disabled; no invented percentage |
| VQ-04 | 1366×768, long report and long command | completed | bounded report/code scroll; command not clipped; third region remains usable |
| VQ-05 | 1366×768, tall PNG | completed | image aspect ratio preserved, no horizontal overflow, accessible report remains present |
| VQ-06 | 1366×768 | partial: `tts_failed` | report/PNG/recap visible, no audio placeholder, partial badge and partial download copy, retry scope visible |
| VQ-07 | 1366×768 | partial: `png_layout_failed` | report/audio retained, explicit card error, no blank fake image |
| VQ-08 | 1366×768 | failed: `source_bundle_invalid` | no unverified output/download, seven failure-detail labels, safe error only |
| VQ-09 | 1366×768 | fallback to edge or SAPI | final backend and reason visible; outcome semantics not confused with failure |
| VQ-10 | 1366×768 | one edited extraction field | pending-change count; old/new confirmation; no rerun before `创建新运行` |
| VQ-11 | 1024×768 | completed | two-column then full-width result layout; no body horizontal scroll |
| VQ-12 | 768×1024 | completed | one-column reading order, full literal tab labels, controls not hidden |
| VQ-13 | 1366×768, keyboard only | all interactive states | logical tab order, visible focus, tabs/accordion/audio/download operable |
| VQ-14 | 1366×768, simulated deuteranopia/grayscale | completed/partial/failed/replay | every status distinguishable by icon and text without color |
| VQ-15 | 1366×768, 200% browser zoom | completed | primary actions and status remain available; no text overlap or loss of content |

Visual acceptance evidence must include screenshots for VQ-01, VQ-02, VQ-06, VQ-08, VQ-10, VQ-11, and VQ-13 plus a short matrix record for all remaining rows. Automated component visibility tests complement but do not replace browser inspection.

## Anti-Patterns (Rejected)

- Marketing hero, splash page, feature cards, decorative AI illustration, gradient/glassmorphism backdrop.
- One giant vertical form with results only below the fold at 1366×768.
- Color-only state dots, unlabeled icon buttons, generic “出错了” messages.
- Treating `replay` as successful live execution or hiding replay metadata inside a collapsed panel.
- Treating fallback as invisible implementation detail; showing audio without backend/fallback reason.
- Calling a partial result `完成`, offering `下载完整证据包`, or generating placeholder MP3/PNG.
- Editable category/root cause/evidence fields in Phase 4; only six Phase 3 extraction fields may enter the correction flow.
- Rerunning on field blur/change without explicit confirmation.
- Button labeled `运行命令`, shell/terminal callbacks, or automatic dependency installation.
- Custom upload/path textbox wired directly to `File` or `DownloadButton`; arbitrary filesystem browsing.
- Rendering provider text through raw HTML, exposing stack traces, absolute paths, temp paths, keys, or raw responses.
- Tiny 11 px body copy, display-scale headings, excessive whitespace, cards-within-cards, or shadows used as hierarchy.
- JavaScript-driven fake progress percentages or browser-memory-only recovery.
- Replacing native report/image/audio/download components with screenshots or custom visual facsimiles.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable |
| third-party registries | none | prohibited for Phase 4 |
| Gradio native | Blocks, Row, Column, Group, Tabs/Tab, Accordion, Markdown, Textbox, Image, Audio, Dataframe, Dropdown, Button/DownloadButton, File, State | pin Gradio 6.20.0; offline app smoke; component visibility matrix; path allowlist tests |

## Implementation Handoff Checklist

- [ ] `ResultViewState` is mapped by a pure presentation function; component callbacks do not infer status from missing files.
- [ ] `replay` and outcome status are stored and rendered independently.
- [ ] Six-field correction uses draft → summary → explicit confirmation → new run/result.
- [ ] All three region headings and status bar meet the 1366×768 first-screen contract.
- [ ] Native Markdown/Image/Audio/Dataframe/File/DownloadButton components receive only verified outputs.
- [ ] Completed/partial/failed/fallback copy matches this contract.
- [ ] CSS uses the declared tokens and responsive breakpoints; no external font or asset request is required.
- [ ] Keyboard, zoom, grayscale, long content, and failure-state visual QA is recorded.
- [ ] No Phase 5 evaluation dashboard or Phase 6 presentation/video UI is added.

## D4 Decision Traceability

| Decisions | UI contract consequence |
|-----------|-------------------------|
| D4-01–D4-04 | UI consumes only strict verified outcome/result identities; no raw dictionary, mutable evidence, or overwritten result is exposed. |
| D4-05–D4-06 | Report structure, grounded/inference labels, stable ID links, and read-only command safety metadata are fixed. |
| D4-07–D4-09 | Native image view presents the verified deterministic PNG; layout failure becomes an explicit partial state, never clipping or placeholder art. |
| D4-10–D4-13 | Audio and transcript share one diagnosis; 30–60 s metadata, backend, fallback reason, and all-TTS-failed behavior are visible. |
| D4-14–D4-16 | Download labels distinguish full/partial bundles and paths can only come from the revalidated result manifest allowlist. |
| D4-17 | First screen is a dense three-region Gradio workbench with a persistent status bar and no marketing hero. |
| D4-18 | Only the six extraction fields enter an explicit, confirmed correction flow that creates a new run/result. |
| D4-19 | Report, image, audio, citations, file, and download controls remain native Gradio 6 components. |
| D4-20 | Replay is identified in the top bar, result summary, and download metadata, with fixture/source identity and no live-success claim. |
| D4-21 | Idle/running/completed/partial/failed outcomes plus orthogonal replay/fallback semantics have explicit visibility and copy rules. |
| D4-22 | Queue stages, disabled duplicate actions, idempotency behavior, and verified-manifest refresh recovery are specified. |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS — all declared text/status pairs meet WCAG AA for normal text
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS — Gradio-native only; no third-party registry

### UI Safety Gate Results

| Review dimension | Result | Evidence |
|------------------|--------|----------|
| Visual hierarchy and design system | PASS | Three-region workbench, restrained token system, and explicit anti-marketing rules keep diagnostic evidence primary. |
| Layout and responsiveness | PASS | 1366×768 first-screen contract, 1024/768 breakpoints, overflow rules, and VQ-01/VQ-11/VQ-12/VQ-15 provide implementable acceptance criteria. |
| Component and state completeness | PASS | Native components cover input, six-field correction, evidence, all three modalities, citations, downloads, and idle/running/completed/partial/failed views. |
| Interaction, error, replay, and fallback semantics | PASS | Replay remains orthogonal to outcome; confirmation, retry scope, queue stages, previous-result labeling, and partial/fallback behavior are explicit and non-deceptive. |
| Accessibility and copy | PASS | Keyboard order, focus, transcript/alt-text equivalents, zoom/grayscale QA, safe literal errors, and icon-plus-text statuses are specified. |
| Implementation, testability, and safety | PASS | Gradio 6 native APIs support the declared Image buttons, disabled Tabs, Audio output, and DownloadButton paths; pure visibility mapping, browser QA, manifest revalidation, and path allowlisting are mandatory. |

**Approval:** verified — ready for Phase 4 implementation planning
