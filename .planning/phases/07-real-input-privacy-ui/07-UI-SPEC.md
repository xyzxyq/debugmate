---
phase: 07
slug: real-input-privacy-ui
status: draft
shadcn_initialized: false
preset: none
created: 2026-08-09
primary_viewport: 1366x768
framework: gradio-6-blocks
requirements: [INP-01, INP-02, SAFE-01, UX-01]
---

# Phase 07 — UI Design Contract

> DebugMate 真实输入、隐私预览与一次性批准的视觉和交互合同。Phase 07 只接通本地输入、OCR、脱敏预览、批准及既有本地诊断入口；不得连接 Dify，不得修改 PPTX、视频、字幕或课程最终截图。

---

## Design Intent

DebugMate 继续是面向 AI 专业学生的学习诊断工具，不是工程控制台或营销页。页面打开后直接进入“填写真实报错 → 检查脱敏预览 → 明确确认”的工作，不展示 hero、宣传插画、流程装饰图或大面积工程元数据。

本阶段在 Phase 04 已实现的学生友好双区工作台上增量扩展：左侧是窄而清晰的真实输入轨道，右侧是宽的隐私预览与诊断结果工作区。右侧始终优先回答用户当前最需要知道的问题：输入是否可用、是否已完成本地脱敏、截图 OCR 是否可用、旧预览是否仍有效，以及确认后会发生什么。

以下决定为锁定合同：

- 普通模式接受报错文本、代码、环境和单张终端截图；报错文本与截图至少提供一项。
- 所有文本扫描、截图校验、RapidOCR、确定性像素遮挡和批准都在本机完成；Phase 07 页面和状态文案不得暗示 Dify 或任何云端已经运行。
- 浏览器在预览之后只持有会话绑定的一次性 opaque token；严格 `PreviewBundle`、`ApprovedRedactedInput`、原始路径、脱敏路径和批准签名均由服务器持有。
- 任一输入发生真实变化后，旧 token 立即在服务器失效，确认按钮立即禁用，旧预览退出“可确认”状态；用户必须重新生成预览。
- 截图存在时必须使用生产 `RapidOcrBackend`。OCR 初始化、推理或规范化失败时整张截图不能进入可确认状态，不得静默切换 `_NoopOcr`。
- 固定回放是独立的演示模式，不读取、不覆盖、不批准上方真实输入，也不得被称为实时诊断。

### Source decisions

| Source | Contract decisions used |
|--------|-------------------------|
| `07-CONTEXT.md` | 输入字段、至少一项主输入、一次性 token、输入修改失效、RapidOCR、回放分离、双区布局、键盘与 200% 缩放 |
| `REQUIREMENTS.md` | INP-01、INP-02、SAFE-01、UX-01 的展示和验收状态 |
| Phase 04 UI-SPEC | Gradio 原生组件、结果优先层级、状态诚实性、技术详情折叠、无命令执行、浏览器 QA 基线 |
| Current `app.py` | 现有双区 CSS、稳定 elem IDs、会话服务器状态、一次性预览 token 回调和结果组件 |
| Current `local_live.py` / `serve.py` | 固定 payload 与 `_NoopOcr` 是待替换缺口；审批密钥与预览 store 已有可复用边界 |
| Current `tests/ui` | Edge、键盘、缩放、回放、结果状态、路径与 capability 不泄露的既有断言 |

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | Gradio 6.20.0 native Blocks/components |
| Icons | Unicode text-safe symbols：`●`、`▶`、`✓`、`⚠`、`✕`、`↺`；始终伴随可见中文文字 |
| UI font | `Inter`, `Segoe UI`, `Microsoft YaHei UI`, `Microsoft YaHei`, sans-serif |
| Monospace | `Cascadia Mono`, `Consolas`, monospace |
| Styling | 继续使用版本化 `WORKBENCH_CSS`；不加载外部 CDN、字体、图片或脚本 |
| Theme | 固定浅色、低装饰、学生学习工具工作台 |

项目是 Python/Gradio，不是 React、Next.js 或 Vite；shadcn 初始化门禁不适用。禁止引入第三方 UI registry、前端框架或自定义文件选择器。

Gradio 原生组件负责交互语义。CSS 只控制 token、双区网格、密度、边框、焦点、响应式和局部溢出，不得通过 CSS 隐藏原生 disabled、loading、focus、file validation 或错误状态。

## Layout Contract

### Primary frame: 1366 × 768

- 页面最大宽度保持 `1440px`，1366 px 下左右 gutter 为 16 px。
- 顶部命令条最小高 56 px：左侧 `DebugMate 学习诊断助手` 与一句工作说明，右侧显示模式和当前阶段；不展示 case/run/hash。
- 主工作台是两区网格，间距 16 px：
  - **开始诊断**：`minmax(320px, 360px)`，承载真实输入、两步动作和独立回放入口。
  - **隐私预览与诊断结果**：`minmax(0, 1fr)`，先展示当前隐私状态和可确认预览，确认后延续现有学生概览与多模态结果。
- 首屏必须看见产品标题、真实模式标识、`报错文本`、`终端截图`、`1. 生成脱敏预览`、右侧当前状态标题；不能要求用户先展开技术详情才知道下一步。
- 代码和环境作为 `补充诊断信息（可选）` Accordion；默认折叠以控制首屏密度，但其摘要必须明确包含“代码、环境”。
- 回放放在输入区底部、视觉分隔线之后的 `演示回放（独立模式）` Accordion，默认折叠。它不能与真实输入 CTA 并排或使用主色按钮。
- 右侧在 `preview_ready` 时先显示隐私预览；在确认并开始本地诊断后，保持 Phase 04 的顺序：学生概览 → 唯一下一步 → 多模态结果 → 技术详情。
- 区域表面继续使用 1 px border、8 px radius、无阴影或仅现有 `box-shadow: none`。禁止卡片套卡片、渐变、玻璃效果和装饰性背景。

### Component hierarchy

```text
gr.Blocks #debugmate-app
├─ Header .command-bar
│  ├─ “DebugMate 学习诊断助手”
│  ├─ mode badge: ● 诊断我的报错 / ↺ 离线回放
│  └─ accessible live status
├─ Main #workbench-grid
│  ├─ Aside .control-rail
│  │  ├─ Textbox #error-input — 报错文本（与截图至少填一项）
│  │  ├─ gr.File #screenshot-input — 固定单文件 PNG/JPEG 输入
│  │  ├─ Accordion “补充诊断信息（可选）”
│  │  │  ├─ Textbox #code-input — 相关代码
│  │  │  └─ Textbox #environment-input — 环境信息
│  │  ├─ inline validation summary #input-validation
│  │  ├─ Button #local-preview — 1. 生成脱敏预览
│  │  ├─ Button #local-approve — 2. 确认并开始诊断
│  │  └─ Accordion “演示回放（独立模式）”
│  │     ├─ warning mode note
│  │     ├─ allowlisted fixture Dropdown
│  │     └─ secondary Button #replay-action
│  └─ Main .diagnosis-canvas
│     ├─ state summary #privacy-overview
│     ├─ Group #privacy-preview
│     │  ├─ redacted error text #preview-error-text
│     │  ├─ redacted code #preview-code
│     │  ├─ redacted environment key/value rows #preview-environment
│     │  ├─ read-only gr.Image #preview-screenshot
│     │  ├─ OCR/redaction audit summary #preview-audit
│     │  ├─ validity status #preview-validity
│     │  └─ technical OCR error #ocr-technical-error
│     ├─ verified extraction fields (existing six-field disclosure)
│     ├─ current student diagnosis overview and next action
│     └─ existing Phase 04 result workspace and disclosures
└─ Footer
   └─ local privacy, no-cloud-in-Phase-07, no-command-execution note
```

Component IDs above are Phase 07 contracts. Existing stable IDs such as `diagnostic-status`, `accessible-status`, `result-tabs`, `technical-details`, `diagnostic-report`, `diagnostic-card`, `diagnostic-audio`, `download-result` and `replay-action` remain unchanged.

## Input Contract

| Field | Component and default | Exact label/help | Validation and behavior |
|-------|-----------------------|------------------|-------------------------|
| Error text | `gr.Textbox`, 8 lines, empty | Label: `报错文本（与截图至少填一项）`; placeholder: `粘贴完整 Traceback 或终端报错。请保留第一行和最后一行。` | Whitespace-only counts as empty. Keep line breaks and English exception text. Never auto-submit. |
| Screenshot | exactly `gr.File(file_count="single", type="filepath", file_types=[".png", ".jpg", ".jpeg"])`, empty, stable `elem_id="screenshot-input"` | Label: `终端截图（可选）`; help: `仅支持 PNG/JPEG，最大 10 MiB、2000 万像素；先在本机 OCR 和遮挡。` | Exactly one file reference enters the raw local boundary. Extension filtering is convenience only; the server validates real bytes, decoded format, size and pixels. No directory, ZIP, multiple file, arbitrary type or URL input. |
| Code | `gr.Textbox`, 6 lines, empty, inside optional Accordion | Label: `相关代码（可选）`; placeholder: `粘贴触发报错附近的最小代码片段。` | Preserve indentation. Scan and redact independently from error text. |
| Environment | `gr.Textbox`, 4 lines, empty, inside optional Accordion | Label: `环境信息（可选）`; placeholder: `例如：Python 3.13.5；PyTorch 2.x；Windows 11；CUDA 12.x` | Student-readable free text, one fact per line preferred. Do not require JSON or expose a raw dict editor. Parse to a server-owned deterministic key/value representation. |

Additional rules:

- Text and screenshot are the only primary inputs. If both are empty, reject locally before OCR, preview store, approval, result service or any future cloud gateway is called.
- Code and environment alone cannot satisfy the primary-input requirement.
- Raw values may exist only in their user-edited native input controls and the server's short-lived raw processing object. They must not be echoed into hidden DOM nodes, `gr.State`, local/session storage, URLs, logs, analytics, HTML, error text or callback outputs.
- The screenshot input may show the user's locally selected image only as the native editable input. The preview/result side must render only the separately generated redacted PNG; no raw path or Gradio temp path may be returned to the browser.
- Filename is never treated as a trusted path. The server copies/reads through its constrained upload boundary, validates bytes, and stores only server-owned identity and hashes.
- The input component and preview component are distinct. `#screenshot-input` is the only editable upload surface. `#preview-screenshot` is exactly a read-only `gr.Image(type="filepath", interactive=False, sources=None, buttons=[])` and receives only the root-confined, SHA-256-reverified redacted PNG.
- No field starts OCR or diagnosis on blur. Changes only update validation and invalidate prior preview authority.

## Privacy Preview Contract

### Preview contents

`preview_ready` must show all supplied categories even if a category has zero findings:

1. `脱敏后的报错文本` — read-only, stable `elem_id="preview-error-text"`; absent copy `未提供报错文本。`
2. `脱敏后的代码` — read-only, stable `elem_id="preview-code"`; absent copy `未提供代码。`
3. `脱敏后的环境` — deterministic key/value rows, stable `elem_id="preview-environment"`; absent copy `未提供环境信息。`
4. `脱敏后的截图` — only the verified deterministic PNG, stable `elem_id="preview-screenshot"`; absent copy `未提供截图。`
5. `隐私检查摘要` — stable `elem_id="preview-audit"`; candidate total, counts by secret kind, screenshot遮挡数, OCR status and privacy rule version. It must never list the matched secret value.

Preview validity always renders in `#preview-validity`. The safe technical OCR error renders only in `#ocr-technical-error`; it contains `ocr_unavailable` and approved recovery copy, never a raw exception or path. These seven IDs are stable structural and Edge-test hooks and must not be replaced by positional selectors.

The summary translates stable kinds for students: `TOKEN → Token`、`PASSWORD → 密码`、`EMAIL → 邮箱`、`USERNAME → 用户名`、`WINDOWS_PATH/UNIX_PATH → 绝对路径`、`PRIVATE_KEY → 私钥`、`PRIVATE_HOST → 私有地址`、`HIGH_ENTROPY → 高熵字符串`.

Zero findings copy is exact: `未检测到可自动遮蔽的敏感项；这不等于绝对安全，请仍检查预览内容。`

When a screenshot is present and OCR succeeds with zero sensitive boxes, show: `本地 OCR 已完成，未发现需要自动遮挡的截图区域；请人工确认脱敏截图。` Do not say “截图安全”。

### Server authority and token lifecycle

- The server owns a monotonically increasing integer `input_revision` per valid Gradio session. It begins at `0`; each accepted semantic change event increments it under the same preview-store lock. The browser may receive the number for presentation/debug tests, but cannot set, decrement or authorize with it.
- All four input change callbacks, `1. 生成脱敏预览`, and `2. 确认并开始诊断` use the same queued lane: `queue=True`, `concurrency_id="debugmate-case"`, `concurrency_limit=1`, `trigger_mode="once"`. No Phase 07 input/preview/approve callback runs with `queue=False`.
- `1. 生成脱敏预览` snapshots the server's current `input_revision`, constructs a strict `InputEnvelope`, calls `build_preview(...)` with production `RapidOcrBackend`, and stores `(session, revision, PreviewBundle)` server-side. Before publishing the token it atomically verifies that the current revision still equals the snapshot.
- The browser receives only rendered redacted values plus an opaque random token. The server record binds the token to session and exact `input_revision`; the token expires no later than the existing 30-minute approval TTL, is bounded by the preview store and is never written to visible HTML/logs/screenshots.
- `2. 确认并开始诊断` is disabled until the server confirms `preview_ready` for the current input revision.
- Confirmation enters the same serial queue and, under one preview-store lock, atomically compares token session and bound revision against the current server revision, checks TTL, and consumes the token. Only that successful compare-and-consume may call `approve_preview`. Missing, copied, expired, tampered, cross-session, reused or revision-mismatched tokens fail closed and never call diagnosis.
- `approve_preview(...)` and `ApprovedRedactedInput` remain server-only. The browser cannot send `PreviewBundle` fields, redacted screenshot paths, `approval_id`, signature, source hash or an approved payload.
- The approved screenshot is resolved under the configured redacted root and SHA-256 reverified immediately before any downstream read.
- Phase 07 may hand the approved object only to the existing local diagnosis service. A Dify adapter, cloud gateway, Dify upload, Dify status or “云端成功” wording is prohibited until Phase 08.

### Input change invalidation

Any semantic change to error text, screenshot, code or environment is submitted through the shared `debugmate-case` serial lane and triggers all of the following atomically:

1. Server increments the session's monotonic `input_revision`, then invalidates the current preview token and stored preview under the same lock.
2. Browser token state becomes `None`; confirm button becomes disabled before another queued action can run.
3. Preview validity status changes to `⚠ 输入已修改，旧预览已失效。请重新生成脱敏预览。`
4. Redacted preview and audit are cleared from the confirmable region; stale data must not remain visually indistinguishable from current data.
5. No OCR, approval or diagnosis starts automatically.

Whitespace normalization must be deterministic. A value that normalizes to the identical server source hash may remain unchanged only if the server proves equality; the browser must never decide token validity from DOM equality. Replacing/removing a screenshot always invalidates. Because changes, preview, and approve are serialized, their queue order is authoritative. A preview completion whose captured revision is no longer current cannot publish a token; an approve event queued after a change observes the incremented revision and fails closed.

## Screenshot and OCR Contract

- Accepted bytes: PNG or JPEG only, at most 10 MiB and 20,000,000 pixels, with positive dimensions. Extension and MIME alone are insufficient.
- Validation occurs before OCR. The source bytes are hashed at validation and re-read against that hash before redaction; changed bytes fail closed.
- `RapidOcrBackend` is lazy-initialized but is the only ordinary screenshot OCR backend. `_NoopOcr` is allowed only in isolated text-only tests or explicit fixture utilities, never in the ordinary `serve.py` construction used by the page.
- Sensitive OCR boxes receive the established 3 px expansion, image-bounds clamp and opaque black fill. The preview image is the exact published deterministic PNG.
- OCR tokens may feed the existing production extraction provider. After a verified local diagnosis, the existing six student-readable fields remain in this order: `异常类型`、`关键回溯行`、`包/模块`、`版本`、`设备`、`路径`; provenance/confidence remains visible where available, and correction continues through the existing explicit new-run flow.
- Phase 07 must not reinterpret OCR candidates in browser code or silently invent missing values. No OCR text or raw screenshot is inserted into unsafe `gr.HTML`.

### OCR failure behavior

If RapidOCR cannot initialize, infer or normalize output, no screenshot preview/token/approved screenshot is produced. Show exactly:

- Heading: `本地 OCR 暂不可用`
- Body: `截图尚未完成脱敏，不能确认或继续。请移除截图后仅用报错文本继续，或修复 RapidOCR 后重新生成预览。未进行云端调用。`
- Safe code in technical disclosure: `ocr_unavailable`

Do not show raw exception, model path, cache path, filename, absolute path or OCR-returned text. If text is also present, it may be retained in the editable input but the combined preview remains unconfirmable until the screenshot is removed or OCR succeeds.

### Invalid screenshot behavior

| Cause | Exact user copy |
|-------|-----------------|
| unsupported/invalid bytes | `无法读取这张截图。请上传有效的 PNG 或 JPEG 文件。` |
| over 10 MiB | `截图超过 10 MiB。请裁剪或压缩后重新上传。` |
| over 20 megapixels | `截图超过 2000 万像素。请缩小后重新上传。` |
| bytes changed during processing | `截图在本地处理期间发生变化，请重新选择文件。` |
| redacted output cannot be written safely | `脱敏截图未能安全保存，请重新生成预览。` |

Every case keeps confirm disabled and states `未进行云端调用。`

## State and Visibility Contract

Three orthogonal, strictly typed values drive the UI; implementations must not flatten them into one enum or infer one from another:

1. `mode: ResultMode = live | replay` — existing mode truth.
2. `privacy: PrivacyPreviewState = idle | invalid | preparing | ready | stale | error | approving | approved` — Phase 07 local-input authority only.
3. `result: ResultViewState` — existing `idle | running | completed | partial | failed` result truth, identity, availability and recovery permissions.

`PrivacyPreviewState` is a new strict server-authored presentation state. It never stores raw fields or paths. `approved` means the one-time token was atomically consumed into a server-only `ApprovedRedactedInput`; it does not mean diagnosis completed.

### Combination, precedence and visibility

| Mode | PrivacyPreviewState | ResultViewState | Primary top status | Secondary visible truth | Preview / result visibility | Buttons | `aria-live` announcement priority |
|------|---------------------|-----------------|--------------------|-------------------------|-----------------------------|---------|----------------------------------|
| live | idle | idle | `● 等待输入` | local-only mode badge | privacy empty visible; result hidden | preview enabled only for valid primary input; confirm disabled | privacy idle once on load |
| live | invalid | idle or previous terminal | `⚠ 还缺少主要报错` | previous terminal result remains labeled `上次结果：{status}` if present | field summary visible; old result may remain read-only below | preview/confirm disabled | privacy invalid overrides previous result announcement |
| live | preparing | any non-running result | `▶ 正在本地生成脱敏预览` | previous result badge may remain secondary | indeterminate privacy progress; no confirmable preview | all inputs/actions/replay disabled | privacy preparing; no percentage |
| live | ready | idle or previous terminal | `✓ 脱敏预览已就绪` | previous result remains `上次结果` only | current redacted preview visible; old result may remain below | preview enabled; confirm enabled | privacy ready overrides previous terminal result |
| live | stale | idle or previous terminal | `⚠ 预览已失效` | previous result remains explicitly `上次结果` | stale preview cleared; prior verified result not destroyed | preview enabled if valid; confirm disabled | privacy stale overrides previous terminal result |
| live | error | idle or previous terminal | `✕ 本地 OCR 暂不可用` or safe validation heading | previous result remains `上次结果` | safe error visible; no confirmable screenshot/preview | confirm disabled; preview retry/removal allowed | privacy error overrides previous terminal result |
| live | approving | idle or previous terminal | `▶ 正在确认脱敏输入` | current preview validity retained | redacted preview remains visible | inputs, preview, confirm and replay disabled | privacy approving |
| live | approved | running | existing `▶ 正在生成结果 · {stage}` | `✓ 已确认脱敏输入` secondary badge | privacy preview moves to named disclosure; result progress primary | duplicate live/replay actions disabled | `ResultViewState.running` overrides approved privacy |
| live | approved | completed / partial / failed | existing verified result badge | `✓ 已确认脱敏输入` secondary badge | student result first; privacy preview available in named disclosure | existing verified correction/retry/download rules | terminal result announced once; privacy approved is not re-announced |
| replay | idle | idle / running / terminal | `↺ 离线回放 · {fixture_name}` plus existing outcome | `本地固定案例` | live privacy panel is non-authoritative and collapsed; replay result follows existing rules | live preview/confirm unavailable during replay | replay mode/outcome only |

Priority rule is deterministic: replay mode truth > live `ResultViewState.running/terminal` after `privacy=approved` > active privacy work/error (`preparing|approving|error|stale|invalid|ready`) > idle. A previous terminal result never suppresses a new stale/error warning, and a new input edit never mutates or relabels that previous verified result as current.

No stage may use an invented percentage. The single existing `aria-live="polite"` surface emits only the highest-priority transition in the table. Lower-priority badges update visually without duplicate live announcements; repeated renders of the same state are deduplicated server-side.

## Replay Separation Contract

- Real-input mode is the default and uses the visible badge `● 诊断我的报错（本地预处理）`.
- Replay control group title is `演示回放（独立模式）`; helper copy is `回放只读取仓库中的固定脱敏案例，不会使用或修改上方真实输入。`.
- Replay CTA remains secondary and exact: `加载回放案例`.
- Opening or selecting a replay fixture does not generate a preview, issue a live preview token, copy fixture data into the real inputs or clear typed inputs.
- Starting replay invalidates any unconsumed live preview token to prevent a later cross-mode confirm. Returning to live requires a new preview if one was invalidated.
- Replay outcome keeps `fixture_id`/fixture name in technical and download metadata but not in the student diagnosis headline.
- Replay must never display `实时诊断`、`真实输入已处理`、`云端运行成功` or a live approval badge.
- Phase 07 ordinary `serve.py` is local-only for both live and replay. It must not import, instantiate or probe `DifyTtsAdapter`, `EdgeTtsAdapter`, a Dify workflow backend or any other network adapter on either path. Replay composition uses only verified local fixtures, local knowledge/rules and an explicitly local audio path such as SAPI; unavailable local audio is represented as the existing honest partial state.
- The local-only promise is construction-time, not merely “adapter was not called”. Tests poison Dify, Edge, HTTPX and socket connection factories before app/service construction for both live and replay and require zero construction and zero network attempts.

## Spacing Scale

All spacing values are multiples of 4.

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4 px | icon/text gap, compact audit rows |
| `space-2` | 8 px | inline controls, badge padding, field help gap and compact field stacks |
| `space-4` | 16 px | preview subsections, page gutter, grid gap and region padding |
| `space-6` | 24 px | major state-to-content separation |
| `space-8` | 32 px | stacked region separation below breakpoint only |

Exceptions: 1 px borders, 2 px focus outline with 2 px offset, 3 px OCR box expansion, and minimum 40 px control height are non-spacing dimensions. Icon-only touch targets do not exist; all actions use visible text and are at least 40 × 40 px.

## Typography

Use exactly these four sizes and two weights (`400`, `700`) across the Phase 07 app shell, including inherited Phase 04 controls. This is an explicit migration of the current CSS, not a second typography system: existing 13 px labels become 14 px; weight 500 becomes 400; weights 600 and 650 become 700. Existing 12/14/16/18 px roles remain. Tests inspect the shipped CSS and computed app-shell styles to reject 13 px and weights 500/600/650. The body of the immutable verified report artifact may preserve its semantic Markdown hierarchy, but app chrome, preview, tabs, labels and metadata must use this table.

| Role | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| Metadata / help | 12 px | 400 | 1.5 | limits, audit counts, backend and privacy notes |
| Body / input | 14 px | 400 | 1.55 | field values, preview text, errors, explanations |
| Label / section | 16 px | 700 | 1.35 | field groups, right-side state sections |
| Page title | 18 px | 700 | 1.3 | `DebugMate 学习诊断助手` only |

Commands, tracebacks, package names, versions, hashes and redaction markers use the monospace stack at 14 px/400. No display text above 18 px and no all-caps English labels except canonical `OCR`、`PNG`、`JPEG`、`SHA-256`、`Dify`.

## Color

Preserve the current implemented light canvas/surface/accent palette, but replace the current light status foregrounds with the AA dark status tokens below. Do not reintroduce the older Phase 04 draft palette.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#F5F7FB` | page canvas and whitespace around the working surface |
| Secondary (30%) | `#FFFFFF`, `#F8FAFC`, `#EDF2F7` | main work surface, preview subsections, input rail |
| Accent (10%) | `#007AFF`, soft `#E9F2FF` | current primary step, focus, active result tab, links, preview-valid emphasis |
| Text | `#0F172A`; muted `#5F6B7A` | primary and secondary copy |
| Border | `#D8DEE8` | controls, surfaces, dividers |
| Information status | text `#0056B3` on `#E9F2FF` | preparing, approving and running status text/surfaces |
| Success status | text `#166534` on `#ECFDF3` | valid preview and completed only |
| Warning status | text `#92400E` on `#FFF7ED` | stale preview, replay, partial and caution only |
| Error status | text `#B42318` on `#FFF1F2` | invalid input, OCR failure and failed state only |

Accent is reserved for `2. 确认并开始诊断` when enabled, keyboard focus outlines, active tab, safe links and the current step. It is not applied to every input border, heading, audit count or replay action. Status always combines icon, text and color.

The lighter legacy status foregrounds `#007AFF`, `#34C759`, `#FF9F0A` and `#FF3B30` are not used for status text. Automated tests calculate WCAG relative luminance/contrast for all four exact foreground/background pairs and require at least 4.5:1; real Edge tests also verify computed effective contrast after opacity and ancestor compositing. Disabled controls must retain at least 4.5:1 and opacity at least 0.8.

## Copywriting Contract

| Element | Exact copy |
|---------|------------|
| Product label | `DebugMate 学习诊断助手` |
| Real mode badge | `● 诊断我的报错（本地预处理）` |
| Input heading | `开始诊断` |
| Input helper | `填写真实报错，先在本机检查脱敏结果，再明确确认。` |
| Preview CTA | `1. 生成脱敏预览` |
| Confirm CTA | `2. 确认并开始诊断` |
| Preview empty heading | `先生成脱敏预览` |
| Preview empty body | `填写报错文本或上传终端截图。DebugMate 会先在本机遮蔽敏感信息。` |
| Preview ready | `脱敏预览已就绪，请逐项检查后再确认。` |
| Stale preview | `输入已修改，旧预览已失效。请重新生成脱敏预览。` |
| Missing primary | `请填写报错文本或上传终端截图，至少提供一项。` |
| OCR failure | `截图尚未完成脱敏，不能确认或继续。请移除截图后仅用报错文本继续，或修复 RapidOCR 后重新生成预览。未进行云端调用。` |
| Token invalid/expired | `这份预览已失效或已使用。请重新生成脱敏预览。` |
| Replay section | `演示回放（独立模式）` |
| Replay helper | `回放只读取仓库中的固定脱敏案例，不会使用或修改上方真实输入。` |
| Privacy note | `Phase 07 只在本机校验、OCR、脱敏和批准，不连接 Dify。` |
| Safety note | `诊断中的命令仅供查看，DebugMate 不会自动执行命令或安装软件。` |

There are no user-triggered destructive actions in Phase 07, so no destructive confirmation dialog is specified. Clearing/replacing an input is reversible and simply invalidates preview authority. Avoid unsupported wording: `绝对安全`、`100% 脱敏`、`AI 一键修复`、`精准识别`、`已上传云端`、`Dify 正在诊断`、`云端运行成功`.

## Accessibility Contract

- WCAG AA contrast: normal text at least 4.5:1; status text/background pairs tested in real Edge.
- Every status icon has adjacent visible text and an accessible label such as `状态：脱敏预览已就绪`.
- DOM/focus order is fixed: header status → error text → screenshot → optional code/environment disclosure → preview CTA → confirm CTA → replay disclosure → privacy preview → extraction correction → student diagnosis → result tabs → technical details/download.
- No positive `tabindex`, keyboard trap or focus jump into hidden result tabs. Disabled confirm is skipped/announced according to native Gradio semantics.
- All controls retain a visible 2 px focus outline with 2 px offset. Accordion names describe content; never use `更多`.
- Primary-input errors appear beside the affected group and in `#input-validation`; red outline alone is insufficient.
- Preview generation, stale transition, OCR failure, approval failure and terminal diagnosis are announced through the polite live region. Input keystrokes are not announced on every character.
- Screenshot has visible alt text: input `用户选择的终端截图，仅在本机处理`; preview `已完成本地遮挡的终端截图`. Essential privacy status is duplicated as text.
- Redaction marker text such as `[REDACTED:TOKEN]` remains selectable. Long traceback/code wraps without forcing body-level horizontal scrolling; local code panels may scroll horizontally only when wrapping would change meaning.
- At 200% zoom, both step buttons, invalid/stale message and mode label remain reachable without horizontal page scroll or overlapping text.
- Touch targets are at least 40 × 40 px. Tabs/accordions/file controls remain native and keyboard-operable.

## Responsive Behavior

| Viewport | Contract |
|----------|----------|
| `>= 1100px` | two zones: 320–360 px input rail + flexible preview/result workspace; sticky command bar |
| `900–1099px` | one column in order input → privacy preview/diagnosis → results; command bar may wrap |
| `640–899px` | one column, natural-height panels, full literal action labels, no nested vertical scroll trap |
| `< 640px` | readable fallback; inputs/buttons full width, badges wrap, tables use local horizontal scroll |

Acceptance widths are 1366, 1024, 768 and 375 px. No body-level horizontal scrolling at any acceptance width. At 375 px, screenshot upload, both numbered CTAs and error copy fit without clipping. At reduced widths, do not make a sticky action bar that covers validation or preview content.

## Security and UI Boundary Rules

- UI callbacks accept scalar form values and one native screenshot upload reference only at the raw local input boundary. Every later callback accepts only server-issued opaque token or strict server-owned IDs.
- No browser callback accepts a user-provided server path, redacted output path, case directory, result directory, URL or JSON-approved payload.
- Preview token, session lease and content capability are different opaque authorities and cannot substitute for one another.
- Raw error/code/environment/screenshot content never enters replay metadata, result metadata, analytics, traceback, log text, screenshot ledger or error response.
- No local absolute path, Gradio temp path, OCR cache/model path or secret candidate match appears in the DOM, `/config`, component props, browser storage, screenshots or downloads.
- Use native Markdown/Textbox/Image/Table surfaces; provider/user text is never rendered as unsanitized `gr.HTML`. The only existing HTML component remains the fixed accessible status template.
- Phase 07 has no command execution, terminal, shell callback, package installation, arbitrary directory upload, URL fetch, Dify upload or cloud API call.
- Ordinary `serve.py` must construct `RapidOcrBackend` for screenshot paths and fail honestly if unavailable. Test-only Noop/fake OCR remains isolated from the ordinary page assembly.

## Test Contract

Implementation follows RED-first focused tests, then existing suite and Ruff. The following tests are mandatory contracts, not optional suggestions.

### Structural and callback tests

- App config exposes exactly four real input fields with stable IDs `error-input`, `screenshot-input`, `code-input`, `environment-input` and keeps result/replay IDs stable. It exposes all preview hooks exactly once: `preview-error-text`, `preview-code`, `preview-environment`, `preview-screenshot`, `preview-audit`, `preview-validity`, `ocr-technical-error`.
- Text + no screenshot, screenshot + no text, and text + screenshot can generate preview; code/environment-only and all-empty inputs are rejected before OCR/service calls.
- Whitespace-only error text is empty.
- Screenshot config is exactly one `gr.File` with `file_count="single"`, `type="filepath"` and the declared PNG/JPG/JPEG filter. Server tests ignore extension/MIME trust, validate real bytes, and reject invalid bytes, over 10 MiB, over 20 MP, changed bytes, unsafe write and multiple/arbitrary files with exact safe copy. The only preview surface is the separate read-only `gr.Image` contract.
- Ordinary `serve.py` constructs production RapidOCR and contains no `_NoopOcr` in the ordinary app path.
- Preview callback returns only opaque token + redacted presentation; no `PreviewBundle`, `ApprovedRedactedInput`, approval signature, raw value or path appears in callback output/repr/config.
- Token is fresh, bounded, session-bound, TTL-bound and one-time. Missing, tampered, copied, expired, cross-session and reused tokens cause zero diagnosis calls.
- Changing each of the four inputs separately increments the monotonic server revision, invalidates the server record and browser token, disables confirm and emits stale copy. A late response from an older preview revision cannot re-enable confirm.
- Config tests assert all four change callbacks, preview and approve use `queue=True`, `concurrency_id="debugmate-case"`, `concurrency_limit=1`, `trigger_mode="once"`; no input authority callback uses `queue=False`.
- Race tests cover exact event orders: change→approve rejects revision mismatch with zero diagnosis; approve→change permits at most the already atomic approval then increments revision and leaves no reusable token; preview(revision N)→server increment→preview completion cannot publish; two approve events for one token yield exactly one approval/diagnosis; stale preview N can never overwrite ready preview N+1.
- Confirm can run only from `PrivacyPreviewState.ready`; the compare-current-revision-and-consume operation is one locked transaction before approval creation.
- OCR failure produces no redacted output, no token, no approval and no diagnosis call; it shows `ocr_unavailable` without raw exception/path.
- Removing a failing screenshot while valid text remains allows a new text-only preview; it does not reuse the failed token.
- Replay selection/load never reads raw form values, never issues a live preview token and invalidates any outstanding live token before replay starts.
- Dify/Edge adapter constructors, gateway/network calls, HTTPX and socket connection boundaries are poisoned before service construction in both Phase 07 live-input and replay tests; all must have zero construction and zero calls. Ordinary `serve.py` source/config tests reject Dify/Edge network adapter imports on the Phase 07 assembly path.
- State-combination unit tests exhaust the table across mode, every `PrivacyPreviewState` and relevant `ResultViewState`; they assert top-status precedence, secondary badges, preview/result visibility, action permissions and exactly one deduplicated `aria-live` message.
- Color tests calculate WCAG contrast for `#0056B3/#E9F2FF`, `#166534/#ECFDF3`, `#92400E/#FFF7ED`, and `#B42318/#FFF1F2`, each at least 4.5:1; Edge computed-style tests include opacity/ancestor compositing.
- Typography tests prove the app shell uses only 12/14/16/18 px and weights 400/700, with no remaining 13 px or weights 500/600/650 outside immutable report artifact content.

### Existing regression tests

- All existing `tests/ui` contracts continue to pass: result truth, two-zone geometry, keyboard, 200% zoom, responsive layout, replay truth, content capability, correction, retry and download.
- Existing privacy tests continue to pass for deterministic text redaction, image validation/redaction, OCR failure cleanup, root confinement, rehashing and HMAC approval.
- Run focused unit/callback tests, focused browser tests with explicit environment gates, then default offline regression and Ruff. Environment-gated browser/OCR skips are reported as skips, not silently counted as passes.

## Real Edge and Screenshot Contract

All visual evidence comes from the implemented loopback Gradio app in real Microsoft Edge. Synthetic screenshots may be test input; generated/mock product screenshots cannot be presented as UI evidence. Phase 07 evidence is stored under a new Phase 07 evidence namespace and must not overwrite Phase 04 evidence or any course final screenshot.

| ID | Viewport / state | Must verify |
|----|------------------|-------------|
| P7-VQ-01 | 1366×768, idle live mode | real text/screenshot fields and step 1 visible; confirm disabled; right side says local preview first; two-zone result-priority geometry; no horizontal overflow |
| P7-VQ-02 | 1366×768, valid text + valid synthetic screenshot, preview ready | redacted text/code/environment and only redacted screenshot visible; audit counts and caution copy; confirm enabled; no raw path/secret/token |
| P7-VQ-03 | 1366×768, edit each field after preview | stale message, preview authority cleared and confirm disabled immediately; no diagnosis call |
| P7-VQ-04 | 1366×768, RapidOCR unavailable | exact honest OCR failure, no preview image/token/confirm/cloud wording; text-only recovery route visible |
| P7-VQ-05 | 1366×768, invalid/oversize screenshot | exact safe validation copy; field and summary errors; no OCR or downstream call |
| P7-VQ-06 | 1366×768, live local approval | mode says local/live, not replay or Dify; existing verified local result remains student-first |
| P7-VQ-07 | 1366×768, replay | independent amber replay label in control, status and metadata; typed live inputs not used or overwritten; no live-success wording |
| P7-VQ-08 | 1024×768 and 768×1024 | ordered one-column flow input → preview/diagnosis → results; numbered actions and replay remain reachable; no body overflow |
| P7-VQ-09 | 375×812 | full labels wrap, input help/errors readable, buttons at least 40 px, no clipped filename/copy or body overflow |
| P7-VQ-10 | 1366×768, keyboard only | logical focus order, visible focus, file/accordion/buttons operable, confirm state announced, no hidden-tab focus |
| P7-VQ-11 | 1366×768 at 200% zoom | current state, both actions, stale/OCR error and preview content reachable; no overlap, clipping or body overflow |
| P7-VQ-12 | grayscale | live/replay/ready/stale/OCR-failed states remain distinguishable by icon and literal text |

Required new browser screenshot evidence: P7-VQ-01, P7-VQ-02, P7-VQ-03, P7-VQ-04, P7-VQ-07, P7-VQ-08 (both widths), P7-VQ-10 and P7-VQ-11. Each evidence row records viewport, state, mode, OCR backend/status, body overflow boolean, screenshot SHA-256 and UTC timestamp. It stores only hashed case/source/result identities when applicable and never raw token, path, secret or screenshot text.

These are engineering QA screenshots only. Phase 07 must not refresh `deliverables/*.pptx`, video, subtitles, presentation manifests, course final screenshots or Phase 10 media sources.

## Anti-Patterns (Rejected)

- Retaining the fixed `LOCAL_RULE_DEMO_*` payload as the ordinary “诊断我的报错” input.
- Keeping `_NoopOcr` in ordinary `serve.py` while claiming screenshot support.
- One giant engineering form with JSON environment, paths, hashes, model settings or backend selectors above the student task.
- Showing the raw screenshot in the preview/result area, or calling the upload preview “脱敏截图”.
- Leaving confirm enabled after an input edit, trusting browser token equality, or accepting a browser-submitted approved payload/path.
- Silently using text-only or Noop OCR after screenshot OCR fails.
- Saying `未发现风险`、`截图安全` or `100% 脱敏` when the detector finds zero candidates.
- Mixing replay controls with the live primary CTA or presenting a replay result as current live/cloud execution.
- Calling Dify, adding API-key fields, or showing Dify progress/status in Phase 07.
- Raw HTML for user/provider content, positive tabindex, color-only states, tiny help text, hidden focus rings or button labels truncated at 200% zoom.
- Modifying PPTX, MP4, SRT, course final screenshot or old Phase 04 evidence during this phase.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not applicable — project is Gradio/Python |
| third-party registries | none | prohibited for Phase 07 |
| Gradio native | Blocks, Group, Column, Accordion, Markdown, Textbox, single `File` screenshot input, separate read-only `Image` preview, Dropdown, Button, State, Tabs/Tab, Audio, DownloadButton | pinned Gradio 6.20.0; structural config tests, strict callback tests and real Edge QA |

## Implementation Handoff Checklist

- [ ] Fixed local demo payload is replaced by strict real form input; text/screenshot minimum is enforced locally.
- [ ] Screenshot input uses existing byte/format/size/pixel validation and production RapidOCR.
- [ ] Redacted text, code, environment, screenshot and value-free audit are all visible before confirm.
- [ ] `PrivacyPreviewState`, existing `ResultViewState` and `ResultMode` remain independent and implement the declared combination/precedence table.
- [ ] Browser holds only a session-bound one-time opaque preview token; strict preview/approval/path state remains server-only.
- [ ] All input changes, preview and approve share the serial `debugmate-case` lane; monotonic server revision and atomic compare-and-consume close all stale-token races.
- [ ] OCR failure and invalid screenshot states use exact honest copy and zero downstream calls.
- [ ] Replay remains allowlisted, separately labeled and isolated from live inputs/tokens.
- [ ] Existing student overview, correction, result tabs, media, retry and downloads remain subordinate to verified server truth.
- [ ] Live and replay are both construction-time local-only; ordinary Phase 07 assembly constructs neither Dify nor Edge/network adapters.
- [ ] Keyboard, 200% zoom, 1366/1024/768/375 widths, grayscale and real Edge screenshots satisfy this contract.
- [ ] No PPTX, video, subtitle, course final screenshot or existing Phase 04 evidence is modified.

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** VERIFIED — 2026-08-09
