# Phase 07: 真实输入与隐私预览接线 - Research

**Researched:** 2026-08-09  
**Domain:** Gradio 6 本地真实输入、截图 OCR 脱敏、服务器授权状态与本地结果接线  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### 输入结构
- 主输入是多行报错文本，截图可作为替代或补充；两者至少提供一项。
- 代码片段和环境信息是可选的独立字段，环境使用学生可理解的文本/键值表单，不要求手写 JSON。
- 截图仅接受既有白名单格式和大小合同，不新增任意文件或目录上传。
- 保留固定回放下拉框，但在视觉和状态文案上与“诊断我的报错”明确分区。

### 隐私预览与批准
- 浏览器只持有一次性 opaque preview token；批准后的严格输入保存在服务器端。
- 预览必须显示脱敏后的文本、代码、环境、截图和审计摘要；不在 DOM 中保存原始秘密或本机绝对路径。
- 修改任一输入后使旧 preview token 失效，必须重新生成预览并再次确认。
- 文本与截图均缺失时在本机拒绝，且不得调用 OCR、Dify 或结果服务。

### 截图与 OCR
- 普通模式使用现有截图验证、RapidOCR provider 和确定性像素遮挡；启动失败时诚实呈现本地 OCR 不可用，不得静默切换 Noop OCR。
- 用户预览和批准的是脱敏截图；云端或后续诊断只能读取经过根目录约束与 SHA-256 复验的版本。
- OCR 候选继续通过现有可纠错字段呈现，Phase 7 只负责输入和预览接线，不改写诊断语义。

### 交互和可访问性
- 延续当前学生优先双区布局；输入侧栏增加真实表单，但首屏不堆叠工程元数据。
- 主要动作按“填写 → 生成脱敏预览 → 确认并诊断”顺序呈现。
- 空值、无效截图、OCR 失败和过期预览都使用文本加状态提示，并保持键盘操作和 200% 缩放可用。

### the agent's Discretion
- 字段具体标签、帮助文案、合理默认高度和折叠方式。
- 现有 callback/service 的内部拆分，只要不扩张云端或文件系统权限边界。
- 定向测试与真实 Edge 证据的最小充分组合。

### Deferred Ideas (OUT OF SCOPE)
- Dify backend、统一 live run 和云端故障降级：Phase 8。
- 代表案例、提示词同案例比较：Phase 9。
- PPTX、视频、字幕、最终截图：Phase 10。
- 目录上传、语音输入、多用户和命令执行：V0.1 范围外。
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INP-01 | 用户可以提交报错文本、终端截图、代码片段和基础环境信息，且文本或截图至少提供一项。 | 四字段原生 Gradio 表单、`InputEnvelope` 适配、主输入本地门禁与单文件回调形态。 [VERIFIED: `.planning/REQUIREMENTS.md`; `src/debugmate/privacy/models.py`] |
| INP-02 | 系统可以从截图中抽取异常类型、Traceback关键行、包名、版本、设备和路径候选，并向用户回显抽取结果。 | 复用 `ProductionExtractionProvider` 对已批准脱敏截图的六字段 OCR 抽取和 Phase 4 纠错展示，不在浏览器重写语义。 [VERIFIED: `src/debugmate/diagnosis/providers.py`; `src/debugmate/ui/app.py`] |
| SAFE-01 | 系统在任何输入离开本机前遮蔽 Token、密码、邮箱、用户名、绝对路径和常见私有标识，并保存脱敏审计结果。 | `build_preview()`、截图验证/遮挡、HMAC 审批、服务器一次性 token、图片审计补口与零云调用门禁。 [VERIFIED: `src/debugmate/privacy/*`; `07-CONTEXT.md`] |
| UX-01 | 用户可以在单一Gradio结果页查看脱敏后的输入、关键抽取字段、检索依据、文字报告、PNG和音频播放器。 | 在现有 Phase 4 单页和稳定结果组件前增量加入隐私状态/预览，不复制结果页。 [VERIFIED: `src/debugmate/ui/app.py`; `.planning/phases/04-multimodal-results-ui/04-VERIFICATION.md`] |
</phase_requirements>

## Summary

本阶段应被规划为“严格隐私边界接线”，不是重新实现 OCR、脱敏或结果生成。现有代码已经有严格 `InputEnvelope` / `PreviewBundle` / `ApprovedRedactedInput`、文本规则、PNG/JPEG 字节验证、RapidOCR 规范化、确定性黑框遮挡、HMAC 批准、已批准截图根目录约束与 SHA-256 复验，以及 Phase 4 的服务器结果状态和单页展示。规划应保留这些边界，只把真实 Gradio 四字段输入送入它们。 [VERIFIED: `src/debugmate/privacy/models.py`; `text_redactor.py`; `image_models.py`; `image_redactor.py`; `approval.py`; `src/debugmate/diagnosis/providers.py`; `src/debugmate/ui/app.py`]

当前普通入口仍有四个实质缺口：`LocalPreviewStore.create()` 自行构造固定 `LOCAL_RULE_DEMO_*`；`build_preview()` 虽得到截图 findings，却没有把截图遮挡数/OCR 状态放入 `PreviewBundle`；`serve.py` 给生产抽取 provider 注入 `_NoopOcr`；普通 replay 组合默认仍可能构造 Dify/Edge TTS。现有 store 也只有 session/TTL/one-time consume，没有每会话 `input_revision`、输入修改失效或 revision-aware 原子消费。 [VERIFIED: `src/debugmate/ui/local_live.py`; `src/debugmate/privacy/text_redactor.py:195-255`; `src/debugmate/ui/serve.py:37-41,92-127,175-206`]

正确实施顺序是：先扩展严格预览审计与 revision-aware 服务器 store；再让 `serve.py` 构造一个共享的生产 `RapidOcrBackend` 并把同一 redacted root 注入预览和本地诊断；最后增量改造 `build_app()` 的四字段表单、状态矩阵和独立 replay，并用单元/竞态/结构/真实 Edge 四层验证。Gradio 共享 queue 只做调度降并发，安全正确性必须由服务器锁、session、revision、TTL 和一次性消费共同保证。 [VERIFIED: codebase analysis; CITED: https://www.gradio.app/main/guides/queuing]

**Primary recommendation:** 用一个服务器持有的 `LiveInputStore` 统一本会话 revision、严格 preview、图片展示 capability 和一次性批准；浏览器回调只提交原始表单到本地预览边界，之后只携带 opaque token，不接 Dify。 [VERIFIED: `07-CONTEXT.md`; codebase analysis]

## Project Constraints

- 本工作是 Phase 研究/规划输入，不授权修改产品实现；本文件之外不应修改产品、PPTX、视频、字幕、最终截图或 Phase 4 历史证据。 [VERIFIED: `AGENTS.md`; task scope; `07-CONTEXT.md`]
- 首版是本地 Windows 桌面浏览器课程演示，优先真实性、隐私、可复现与低人工量；不得把 fixed replay、本地规则或 local SAPI 说成 Dify 实时成功。 [VERIFIED: `AGENTS.md`; `.planning/PROJECT.md`; `.planning/STATE.md`]
- 仓库没有 `CLAUDE.md`，也没有 `.claude/skills/` 或 `.agents/skills/` 项目技能；没有额外项目级实现规则需要合并。 [VERIFIED: filesystem inspection 2026-08-09]

## Standard Stack

### Core

| Library / contract | Pinned version | Purpose | Prescription |
|---|---:|---|---|
| Gradio | 6.20.0 | 四字段输入、预览、状态与既有单页结果 | 保持项目 pin，不在本阶段升级；6.20.0 发布于 2026-07-07，registry 当前为 6.22.0，但 UI-SPEC 明确锁定 6.20.0。 [VERIFIED: PyPI JSON 2026-08-09; `pyproject.toml`; `07-UI-SPEC.md`] |
| Pydantic | 2.13.4 | 严格 input/preview/approval/presentation 合同 | 延续 `strict=True, extra='forbid'`，不要用 dict 代替服务器权限对象。 [VERIFIED: PyPI JSON; `src/debugmate/privacy/models.py`] |
| RapidOCR | 3.9.1 | 本地中文/英文终端截图 OCR | 普通截图路径只构造 `RapidOcrBackend()`；保留 lazy engine 和安全异常包装。项目 pin 3.9.1 发布于 2026-07-02；registry 当前 3.9.2，本阶段不顺带升级。 [VERIFIED: PyPI JSON; `pyproject.toml`; `src/debugmate/privacy/rapidocr_backend.py`] |
| ONNX Runtime CPU | 1.27.0 | RapidOCR CPU 推理 | 使用现有 CPU pin；官方 RapidOCR 文档推荐先用 ONNX Runtime CPU。 [VERIFIED: PyPI JSON; CITED: https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/] |
| Pillow | 12.3.0 | 实字节验证与确定性黑框 PNG | 复用现有两次打开/verify、像素上限、RGB 重写和原子发布。 [VERIFIED: PyPI JSON; `image_models.py`; `image_redactor.py`] |
| HMAC-SHA256 / `secrets` | Python stdlib | 预览批准签名与 token | 继续使用随机 token、至少 32 字节 key、30 分钟最大 TTL；不要自定义加密协议。 [VERIFIED: `src/debugmate/privacy/approval.py`] |

### Supporting

| Tool | Version / contract | Use |
|---|---:|---|
| pytest | 9.1.1 | store、race、callback、结构、隐私回归和 marker 门禁。 [VERIFIED: `pyproject.toml`; PyPI JSON] |
| Playwright | 1.61.0 + `channel="msedge"` | 显式真实 Edge 的键盘、缩放、宽度、状态与无泄露证据。 [VERIFIED: `pyproject.toml`; `tests/ui/test_browser.py`] |
| Ruff | 0.15.21 | 聚焦与全仓静态检查。 [VERIFIED: `pyproject.toml`; PyPI JSON] |
| Existing local result service | strict Phase 4 contract | 批准后仅调用 `diagnose_and_compose_events(ApprovedRedactedInput)`，不复制报告/PNG/MP3/ZIP 逻辑。 [VERIFIED: `src/debugmate/results/service.py`; `src/debugmate/ui/app.py`] |

### Alternatives Considered

| Instead of | Rejected alternative | Why |
|---|---|---|
| Native `gr.File` single upload | 自定义 HTML/JS uploader、目录或多文件 | 违反 UI-SPEC 和范围，扩大路径、XSS 与任意文件边界。 [VERIFIED: `07-UI-SPEC.md`; CITED: https://www.gradio.app/docs/gradio/file] |
| Existing RapidOCR adapter | OCR 文本框手工上传、Noop、云 OCR | Noop 会伪造截图已处理；云 OCR 会在脱敏前泄露；手工 OCR 不满足真实截图闭环。 [VERIFIED: `07-CONTEXT.md`] |
| Revision-aware server store | 仅 `gr.State` token 比较或前端 disabled | 浏览器状态可伪造，且不能关闭 late preview / edit→approve / duplicate approve 竞态。 [VERIFIED: `07-UI-SPEC.md`; codebase analysis] |

**Installation / repair (Wave 0):**

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pip check
```

项目根 `.venv` 的 Python 3.13.5、ONNX Runtime 1.27.0、Pillow 12.3.0、pytest 9.1.1 和 Ruff 0.15.21 当前存在，但 Gradio、RapidOCR、Pydantic、Playwright 与 editable `debugmate` 当前不可导入；执行计划必须先修复环境再把测试结果计为通过。 [VERIFIED: local environment probe 2026-08-09]

## Architecture Patterns

### Recommended File Boundaries

```text
src/debugmate/privacy/models.py          # 增加 value-free screenshot preview audit 合同
src/debugmate/privacy/text_redactor.py   # build_preview 保留/绑定截图审计到 preview hash
src/debugmate/ui/local_live.py           # 泛化为 session + revision + TTL + one-time token store
src/debugmate/ui/presentation.py         # PrivacyPreviewState 和状态组合纯函数
src/debugmate/ui/app.py                  # 四字段、预览组件、queued callbacks、现有结果页增量接线
src/debugmate/ui/serve.py                # 一次构造 RapidOcrBackend；live/replay construction-time local-only
tests/privacy/                           # 图片审计、hash、失败清理与既有隐私回归
tests/ui/test_real_input.py              # 新增聚焦 callback/竞态/结构合同（建议新文件）
tests/ui/test_local_live.py              # store 原子性和 local-only service
tests/ui/test_browser.py                 # Phase 07 Edge 场景，不覆盖 Phase 4 evidence
```

这些边界最少侵入 Phase 4 结果服务；`results/service.py` 和报告/PNG/MP3/publisher 应保持原合同，除非只需补充类型注解或测试 seam。 [VERIFIED: codebase dependency inspection]

### Pattern 1: Server-owned Revisioned Preview Store

每个 session 记录独立的单调 `input_revision`，token record 至少绑定 `session_hash`、`revision`、`PreviewBundle`、到期时间和只读图片展示 capability；严格对象与路径均 `repr=False`。 [VERIFIED: `07-UI-SPEC.md`]

推荐 API：

```python
revision = store.invalidate_and_increment(session)
snapshot = store.snapshot_revision(session)
preview = build_preview(envelope, redacted_root, ocr_backend)  # heavy work outside lock
presentation = store.publish_if_current(session, snapshot, preview)
record = store.consume_current(token, session)  # compare session/revision/TTL + pop under one lock
```

OCR 不应在 store lock 内执行，否则一个慢截图会阻塞全部 session；发布前再次加锁比较 revision。共享 Gradio `concurrency_id` 可以把事件并发降到 1，但官方文档只保证共享并发池，不应把跨 listener 的安全顺序当成唯一保证。 [CITED: https://www.gradio.app/main/guides/queuing; VERIFIED: codebase analysis]

### Pattern 2: One Production OCR Instance, Two Safe Reads

`serve.main()` 应创建一次 `RapidOcrBackend()`，并把同一实例与同一 `runtime_root / "redacted"` 同时注入 preview store 和 `ProductionExtractionProvider`。第一次 OCR 原始、已验证截图以决定遮挡；批准后的诊断 provider 再 OCR 已遮挡 PNG 生成六字段候选。不要缓存原始 OCR 文本到 browser/store，也不要为两个路径构造两个模型实例。 [VERIFIED: `rapidocr_backend.py`; `image_redactor.py`; `diagnosis/providers.py`; codebase analysis]

RapidOCR 官方 3.9 文档确认 `RapidOCR()` 的结果包含等长 `boxes`、`txts`、`scores`，现有 adapter 已安全规范化为 `OcrToken` 并将初始化、推理、输出形状错误统一为不含路径/文本的 `OcrUnavailable`。 [CITED: https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/; VERIFIED: `rapidocr_backend.py`]

### Pattern 3: Bind Screenshot Audit to the Preview

现有 `build_preview()` 调用 `redact_screenshot()` 后只保留输出 hash，丢弃 `ScreenshotRedactionResult.findings`；因此 UI 目前无法诚实显示截图遮挡数/OCR 状态。应增加严格、value-free 的 `ScreenshotPreviewAudit`（`provided`、`ocr_status`、`finding_count`、`counts_by_kind`），将其纳入 `PreviewBundle` 和 `preview_hash`，但不要把 OCR 原文、匹配值、本机路径或 box 明细返回浏览器。 [VERIFIED: `text_redactor.py:195-255`; `image_redactor.py:34-55`; `07-UI-SPEC.md`]

不要把 screenshot findings 塞入现有 `SecretCandidate`：后者以文本 span 为合同，截图 finding 是 box 合同。两个审计域应聚合展示、分别严格校验。 [VERIFIED: `privacy/models.py`; `image_redactor.py`]

### Pattern 4: Gradio 6.20 Single-file Callback Shape

```python
screenshot = gr.File(
    file_count="single",
    type="filepath",
    file_types=[".png", ".jpg", ".jpeg"],
    elem_id="screenshot-input",
)

def prepare_real_preview(
    error_text: str | None,
    screenshot_path: str | None,
    code: str | None,
    environment_text: str | None,
    request: gr.Request,
) -> tuple[object, ...]:
    ...

preview_button.click(
    prepare_real_preview,
    inputs=[error_text, screenshot, code, environment],
    outputs=[...],
    queue=True,
    trigger_mode="once",
    concurrency_limit=1,
    concurrency_id="debugmate-case",
    api_name=False,
    postprocess=False,
)
```

对 `file_count="single"` + `type="filepath"`，函数输入是单个服务器临时路径字符串或 `None`，不是 list；`file_types` 只是前端便利过滤，仍必须由 `validate_screenshot()` 检查真实字节、解码格式、大小与像素。 [CITED: https://www.gradio.app/docs/gradio/file; VERIFIED: `image_models.py`]

四个输入的 `.change()`、preview、approve 都使用同一 queued lane 和 `trigger_mode="once"`。`.change()` 会被用户输入和函数更新触发，正适合统一失效；避免同时叠加 `.upload()`/`.clear()` 造成双增 revision，除非去重有明确测试。 [CITED: https://www.gradio.app/docs/gradio/file; VERIFIED: `07-UI-SPEC.md`]

### Pattern 5: Do Not Return a Server Path to the Preview Image

`gr.Image` 输出可接 URL；使用独立、只读、随机 content capability 显示已复验的 redacted PNG，不把 redacted absolute path 或 Gradio temp path放进 callback payload/DOM。该 capability 只能读图片，不能作为 preview token 或批准输入。 [CITED: https://www.gradio.app/docs/gradio/image; VERIFIED: `07-UI-SPEC.md`; existing `_UiContentStore` pattern in `app.py`]

Gradio 会让 cache 中和用户上传的文件通过文件 URL 可访问，并建议设置上传大小、最小化 `allowed_paths`；Phase 07 应设置 `launch(max_file_size="10mb")` 作为入口限流，同时保留服务端 10 MiB 精确检查，且不新增广泛 `allowed_paths`。 [CITED: https://gradio.app/guides/file-access]

### Pattern 6: Orthogonal UI Truth

保留 `ResultMode` 和 `ResultViewState`，新增独立 `PrivacyPreviewState`，用纯函数生成最高优先级状态、可见性、按钮权限和唯一 aria-live 文案。不要把“preview approved”解释为“diagnosis completed”，也不要因新输入 edit 删除上一次已验证结果；它只能把上一次结果标成“上次结果”。 [VERIFIED: `07-UI-SPEC.md:212-239`; `src/debugmate/results/contracts.py`; `src/debugmate/ui/presentation.py`]

### Pattern 7: Construction-time Local-only

Phase 07 的普通 `serve.py` 不应 import/instantiate/probe Dify、Edge TTS、HTTPX 或 socket network adapters。live 与 replay 都只用本地规则、固定脱敏 fixture 和 SAPI；本地音频不可用时沿用真实 partial，不访问网络。当前 `replay_local_only=False` 默认会让 replay 走 Dify→Edge→SAPI 候选链，必须在本阶段关闭。 [VERIFIED: `src/debugmate/ui/serve.py:92-127,175-206`; `07-UI-SPEC.md:241-251`]

### Anti-Patterns to Avoid

- 只清空浏览器 token，不调用服务器 `invalidate_and_increment()`。 [VERIFIED: threat analysis]
- 在 preview callback 输出 `PreviewBundle.model_dump()`、`ApprovedRedactedInput`、签名、hash 或任一路径。 [VERIFIED: `07-UI-SPEC.md`]
- OCR 失败后用 text-only preview 继续批准仍附带的截图。 [VERIFIED: `07-CONTEXT.md`]
- 依赖扩展名/MIME 或 Gradio file filter 代替真实字节验证。 [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html]
- 复用 upload input 自带预览作为“脱敏截图”；必须有独立只读 redacted preview。 [VERIFIED: `07-UI-SPEC.md`]
- 顺带重构 Phase 4 结果发布、刷新媒体或接 Dify。 [VERIFIED: phase boundary]

## Threat and Race Model

| Threat / ordering | Failure if naïve | Required invariant / test |
|---|---|---|
| `change → approve` | 旧 token 批准旧输入 | change 在服务器锁内增 revision 并删 token；approve 比较 current revision 后才 pop，零 diagnosis。 [VERIFIED: `07-UI-SPEC.md`] |
| `approve → change` | 同 token 可重放或结果冒充当前输入 | approve 最多原子成功一次；之后 change 增 revision，浏览器无可复用 token，已开始 run 可完成但输入状态已是新 revision。 [VERIFIED: `07-UI-SPEC.md`] |
| preview N 慢，change 后 preview N 返回 | 旧 redacted 内容重新启用 confirm | publish 时在锁内复核 captured revision；N 不得发布 token/ready。 [VERIFIED: `07-UI-SPEC.md`] |
| preview N 晚于 preview N+1 | 旧 response 覆盖新 preview | 服务器 revision + publish guard；浏览器只接受当前 revision presentation。 [VERIFIED: codebase analysis] |
| 双击 approve | 触发两次 diagnosis | compare-and-pop 是单锁事务；第二次找不到 token。 [VERIFIED: existing store pattern; `07-UI-SPEC.md`] |
| token copied to another session | 跨会话批准 | record 强绑定 request `session_hash`；不接受浏览器提供 session。 [VERIFIED: `local_live.py`; `test_local_live.py`] |
| token expired/tampered/evicted | 使用失效授权 | purge/check/pop 均在锁内；显示统一 safe copy，零 downstream。 [VERIFIED: `local_live.py`; `approval.py`] |
| replay starts with live token outstanding | 回放结束后旧 live token仍可批准 | replay 开始先服务器失效当前 live authority；不读取/覆盖四字段。 [VERIFIED: `07-UI-SPEC.md`] |
| arbitrary path submitted as File value | 读取本机任意文件 | 将 Gradio upload 缓存限定在独立 root，回调只接受该 root 内服务器上传文件；真实文件名不用于输出路径。 [CITED: https://gradio.app/guides/file-access; CITED: https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload] |
| same-case redacted output symlink/TOCTOU | 覆盖或读取 root 外文件 | `resolve_artifact_path`、拒绝 source==output、原图 hash 二次读取、输出原子 replace、批准后再次 root-confine + SHA-256。 [VERIFIED: `text_redactor.py`; `image_redactor.py`; `diagnosis/providers.py`] |
| decompression bomb / giant pixels | CPU/内存 DoS | 10 MiB + 20 MP 双门禁，先 validation 后 OCR；入口 `max_file_size` 只是额外保护。 [VERIFIED: `image_models.py`; CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html] |
| OCR exception contains path/secret | DOM/log 泄露 | 捕获为固定 `ocr_unavailable`；不使用 raw exception、filename、OCR text。 [VERIFIED: `rapidocr_backend.py`; `07-UI-SPEC.md`] |
| replay constructs network adapter | Phase 边界和真实性违规 | 构造前 poison Dify/Edge/httpx/socket；live/replay 都必须零构造、零连接。 [VERIFIED: `07-UI-SPEC.md`; current gap in `serve.py`] |

**STRIDE summary:** token/path篡改属于 Tampering/Elevation of Privilege；跨 session、DOM/path/exception 泄露属于 Information Disclosure；巨大或恶意图片属于 Denial of Service；replay 冒充 live 属于 Spoofing/Repudiation。Phase 07 的标准缓解分别是严格模型+HMAC+原子 revision store、root confinement+safe copy、双尺寸门禁和正交 mode truth。 [VERIFIED: codebase threat analysis]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| OCR 引擎 | 自写 OCR / regex 猜图片文字 | `RapidOcrBackend` + RapidOCR 3.9.1 | 已有结果规范化和安全失败合同。 [VERIFIED: codebase; CITED: RapidOCR docs] |
| 图片格式识别 | 扩展名/MIME 判断 | Pillow `verify()` + reopen + format/pixel checks | 文件名和 Content-Type 可伪造。 [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html; VERIFIED: `image_models.py`] |
| 图片脱敏 | 浏览器 canvas 或模糊遮挡 | `redact_screenshot()` 的 3 px clamp + opaque black + deterministic PNG | 现有输出可哈希、可复验、不依赖浏览器。 [VERIFIED: `image_redactor.py`] |
| 授权签名 | 自定义 token 加密/JSON 签名 | `secrets` + existing HMAC approval | 已有 key/TTL/constant-time verify。 [VERIFIED: `approval.py`] |
| 结果页/下载 | 新建第二个 live 页面或直接返回文件路径 | Phase 4 `ResultApplicationService` + capability endpoint | 既有结果 identity、重验和下载合同已通过验证。 [VERIFIED: Phase 4 verification] |
| 前端状态框架 | 自定义 JS/localStorage 状态机 | Gradio native controls + server-owned store + pure presentation function | 避免把权限放进不可信浏览器。 [VERIFIED: `07-UI-SPEC.md`] |

**Key insight:** 本阶段唯一需要新增的基础设施是很小的 revision-aware server store 和 screenshot preview audit；OCR、脱敏、批准、诊断与结果发布均应复用。 [VERIFIED: codebase gap analysis]

## Common Pitfalls

### Pitfall 1: 图片审计“看起来存在”但实际只统计文本

**What goes wrong:** `preview.audit.candidate_count` 目前不含 screenshot findings，UI 若直接显示会低报遮挡数。  
**How to avoid:** 单独严格建模 screenshot audit，并纳入 preview hash；用截图含敏感框/零敏感框两类测试。  
**Warning sign:** OCR 确实画了黑框，但 audit 仍为 0。 [VERIFIED: `text_redactor.py`; `image_redactor.py`]

### Pitfall 2: 把 shared queue 当成锁

**What goes wrong:** queue 降并发不等于浏览器权限验证，也不替代 revision 比较。  
**How to avoid:** 所有 invalidation/publish/consume 仍在 store lock 内做 compare-and-set。  
**Warning sign:** callback 测试通过，但直接并发 store 单测可产生两个批准。 [CITED: https://www.gradio.app/main/guides/queuing; VERIFIED: threat analysis]

### Pitfall 3: OCR 失败后留下旧 PNG

**What goes wrong:** 用户可能批准上次成功的同 case 文件。  
**How to avoid:** 沿用 `build_preview()` 先删旧输出、失败不返回 preview/token，并测试 stale output cleanup。  
**Warning sign:** OCR exception 后 `redacted.png` 仍存在或 preview image 未清空。 [VERIFIED: `test_preview_integration.py`]

### Pitfall 4: 生产 preview 用 RapidOCR，诊断抽取仍用 Noop

**What goes wrong:** 用户看到遮挡，但批准后的 INP-02 六字段没有截图 OCR 候选。  
**How to avoid:** `serve.py` 一次构造并共享同一个 backend；源代码门禁拒绝普通 path 中 `_NoopOcr`。  
**Warning sign:** screenshot-only preview成功，结果六字段全空且 OCR backend call count 只有一次。 [VERIFIED: current `serve.py` gap]

### Pitfall 5: replay 只在文案上“离线”

**What goes wrong:** 当前 replay composer 默认可能构造 Dify/Edge TTS。  
**How to avoid:** ordinary Phase 07 assembly 不 import network adapters，服务构造前 poison network factories。  
**Warning sign:** 没点 live 也会读取 API settings 或触发 httpx/socket。 [VERIFIED: `serve.py`]

### Pitfall 6: 返回 redacted absolute path 给 `gr.Image`

**What goes wrong:** 浏览器响应、DOM 或截图泄露本机路径；路径还可能被误用为批准权限。  
**How to avoid:** 返回单独的 read-only content capability URL；批准只接受 preview token。  
**Warning sign:** callback repr/config/network response出现盘符、`AppData`、`.debugmate-runtime`。 [VERIFIED: UI-SPEC; Gradio file-access docs]

### Pitfall 7: 环境文本解析不确定

**What goes wrong:** 同一输入生成不同 dict/hash，或重复 key 静默覆盖。  
**How to avoid:** 建立小型确定性 parser：按行/中文分号切分；首个 `:`/`=` 分隔 key/value；规范化已知 key（如 python/device），重复或无 key 项使用稳定 `detail_001` 顺序键；测试 CRLF、空行、重复 key 和中文标点。 [VERIFIED: requirement-to-contract analysis]

## Code Examples

### Atomic consume before approval

```python
# Source pattern: existing LocalPreviewStore + Phase 07 UI-SPEC
record = preview_store.consume_current(
    token=preview_token,
    request_session=request.session_hash,
)
if record is None:
    return expired_preview_payload()

# Only a successfully consumed, server-owned PreviewBundle reaches HMAC approval.
approved = approve_preview(record.preview, approval_key)
yield from callbacks.diagnose_events(approved, request=request)
```

`consume_current()` 必须在一把锁内验证 session、TTL、record revision==current revision 后 pop；不能先 read 后 approve 再 delete。 [VERIFIED: `07-UI-SPEC.md`; existing `LocalPreviewStore.consume()`]

### Honest OCR failure

```python
try:
    preview = build_preview(envelope, redacted_root, rapid_ocr)
except OcrUnavailable:
    store.invalidate_current(session)
    return ocr_unavailable_presentation(code="ocr_unavailable")
```

返回文案固定，不插入 `str(exc)`；截图仍存在时不允许批准文本部分。 [VERIFIED: `rapidocr_backend.py`; `07-UI-SPEC.md`]

### Input change callback

```python
def invalidate_live_input(request: gr.Request) -> tuple[object, ...]:
    store.invalidate_and_increment(request.session_hash)
    return (
        None,  # browser preview token
        gr.update(interactive=False),
        stale_preview_state(),
        clear_confirmable_preview(),
    )
```

四字段共用同一个 callback/event lane；截图替换或移除总是 semantic change。 [VERIFIED: `07-UI-SPEC.md`]

## State of the Art

| Old/current gap | Phase 07 approach | Impact |
|---|---|---|
| 固定 `LOCAL_RULE_DEMO_*` preview | 四字段 strict `InputEnvelope` snapshot | 普通页面终于处理真实输入。 [VERIFIED: `local_live.py`] |
| `_NoopOcr` ordinary service | shared lazy `RapidOcrBackend` | preview 与 INP-02 extraction 都是真实 OCR。 [VERIFIED: `serve.py`; RapidOCR docs] |
| token only session/TTL-bound | session + revision + TTL + one-time atomic consume | 关闭 stale/duplicate/cross-mode races。 [VERIFIED: UI-SPEC] |
| combined text display | 分字段 redacted preview + image capability + value-free audit | 用户能逐项确认，DOM 不持路径。 [VERIFIED: UI-SPEC] |
| replay may construct network TTS | construction-time local-only replay | 不用“未调用”掩盖已构造的云依赖。 [VERIFIED: `serve.py`; UI-SPEC] |

**Deprecated/outdated for this phase:** `_NoopOcr` ordinary assembly、fixed payload ordinary preview、`replay_local_only=False`、仅凭前端 disabled/token equality、13 px/500/600/650 app-shell typography。 [VERIFIED: UI-SPEC; current CSS/source]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---:|---:|---|
| CPython root venv | all tests/app | ✓ | 3.13.5 | — [VERIFIED: local probe] |
| Gradio | app import | ✗ | pinned 6.20.0 | install project dependencies; no functional fallback [VERIFIED: local import probe] |
| RapidOCR | screenshot preview | ✗ | pinned 3.9.1 | text-only after user removes screenshot; never Noop [VERIFIED: local import probe; CONTEXT] |
| ONNX Runtime CPU | RapidOCR | ✓ | 1.27.0 | — [VERIFIED: local pip probe] |
| Pydantic | contracts | ✗ | pinned 2.13.4 | install; no fallback [VERIFIED: local import probe] |
| Pillow | screenshot validation/redaction | ✓ | 12.3.0 | — [VERIFIED: local pip probe] |
| pytest / Ruff | validation | ✓ | 9.1.1 / 0.15.21 | — [VERIFIED: local pip probe] |
| Playwright Python | real Edge tests | ✗ | pinned 1.61.0 | install; structural/unit tests do not replace Edge acceptance [VERIFIED: local import probe] |
| Microsoft Edge | browser QA | ✓ | 151.0.4129.72 | explicit environment skip only if unavailable [VERIFIED: local file version probe] |
| FFmpeg / FFprobe | existing local result chain | ✓ | 8.1 | existing partial audio behavior [VERIFIED: local CLI probe] |

**Missing dependencies with no fallback:** Gradio、Pydantic 必须安装后才能收集 UI/contract tests。 [VERIFIED: environment audit]

**Missing dependencies with honest fallback:** RapidOCR 缺失时 screenshot path 必须显示 `ocr_unavailable` 且不能批准；Playwright 缺失时 browser tests 必须明确 skip/blocked，不能记 pass。 [VERIFIED: UI-SPEC]

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 9.1.1 + Playwright 1.61.0 explicit Microsoft Edge [VERIFIED: `pyproject.toml`] |
| Config file | `pyproject.toml`（默认排除 cloud/ocr/network/browser/tts） [VERIFIED: `pyproject.toml`] |
| Quick run command | `.\.venv\Scripts\python.exe -m pytest -q --disable-warnings --maxfail=1 tests\privacy tests\ui\test_real_input.py tests\ui\test_local_live.py tests\ui\test_app.py` [VERIFIED: recommended test map] |
| Full suite command | `.\.venv\Scripts\python.exe -m pytest` then `.\.venv\Scripts\python.exe -m ruff check src tests` [VERIFIED: existing project gates] |
| OCR smoke | `.\.venv\Scripts\python.exe -m pytest -q -m ocr tests\privacy\test_rapidocr_smoke.py` [VERIFIED: existing marker/test] |
| Browser focus | `.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "phase7 or p7_"` [VERIFIED: recommended Phase 07 namespace] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| INP-01 | four fields; text/screenshot minimum; whitespace and code/env-only rejection before OCR/service | unit + callback + config | `pytest -q tests/ui/test_real_input.py -k "input or primary or structure"` | ❌ Wave 0 |
| INP-02 | production OCR on approved redacted screenshot yields six existing fields/correction path | integration + OCR smoke | `pytest -q tests/diagnosis/test_extraction_providers.py tests/ui/test_real_input.py -k "screenshot or extraction"` | ⚠ extend existing |
| SAFE-01 | text/image redaction audit, root/hash recheck, opaque one-time revision token, honest failure | privacy + race + abuse | `pytest -q tests/privacy tests/ui/test_real_input.py tests/ui/test_local_live.py -k "preview or token or race or ocr or path"` | ⚠ extend/new |
| UX-01 | one page shows all preview fields and preserves Phase 4 result/replay truth | structural + browser | `pytest -q tests/ui/test_app.py tests/ui/test_view_state.py`; browser focus above | ⚠ extend existing |

### Mandatory Race/Abuse Matrix

- `change→approve`, `approve→change`, slow preview N→change, preview N→preview N+1, duplicate approve, expired/tampered/copied token, replay invalidation, OCR failure→remove screenshot→text-only recovery。 [VERIFIED: UI-SPEC]
- Invalid bytes、wrong extension with valid/invalid bytes、>10 MiB、>20 MP、changed bytes、source==output、symlink escape、unsafe write、absolute/redacted path injection。 [VERIFIED: existing privacy tests; OWASP upload guidance]
- Poison Dify/Edge adapters, HTTPX clients and socket connection before ordinary service construction for both live and replay。 [VERIFIED: UI-SPEC]
- Inspect app config/callback objects: exact stable IDs and component props; all four `.change()` plus preview/approve use `queue=True`, `trigger_mode="once"`, `concurrency_id="debugmate-case"`, `concurrency_limit=1`。 [VERIFIED: UI-SPEC]
- Inspect callback outputs/repr/config/browser storage/DOM for secret sentinel, raw form values, token, approval signature, disk paths, OCR model paths and Gradio temp paths。 [VERIFIED: UI-SPEC]

### Sampling Rate

- **Per task commit:** focused new test file + directly affected existing privacy/UI tests + scoped Ruff. [VERIFIED: project TDD pattern]
- **Per wave merge:** default offline suite + full Ruff; real OCR only at the OCR assembly wave. [VERIFIED: `pyproject.toml` markers]
- **Phase gate:** focused browser Phase 07 scenarios, default full suite, Ruff, dependency check, secret/path scan, and no modified locked media/evidence. [VERIFIED: UI-SPEC; Phase 4 gate pattern]

### Wave 0 Gaps

- [ ] Repair `.venv` with `pip install -e ".[dev]"`; run import/version and `pip check`. [VERIFIED: environment audit]
- [ ] Create `tests/ui/test_real_input.py` for four-field callback/store/race/local-only contracts. [VERIFIED: test gap analysis]
- [ ] Extend `tests/privacy/test_preview_integration.py` for screenshot audit binding and zero-finding copy. [VERIFIED: current test coverage gap]
- [ ] Add Phase 07 browser selector namespace and a new evidence path/ledger; never overwrite Phase 4 or course-final screenshots. [VERIFIED: UI-SPEC]
- [ ] Add a production RapidOCR construction/source test for ordinary `serve.py`; keep fake/noop only in isolated tests. [VERIFIED: current gap]

### Real Edge Minimum Sufficient Gate

Required fresh states are idle real form, ready text+screenshot preview, per-field stale invalidation, honest OCR unavailable, independent replay, 1024/768 responsive layouts, keyboard-only, and 200% zoom. These are Phase 07 engineering QA captures under a new namespace, not final course screenshots. [VERIFIED: `07-UI-SPEC.md:391-412`]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no for V0.1 single-user loopback | Do not invent accounts; request session binding is authorization context, not user authentication. [VERIFIED: project scope] |
| V3 Session Management | yes | server request session + random one-time token + TTL + cross-session rejection + revision invalidation. [VERIFIED: store/UI-SPEC] |
| V4 Access Control | yes | preview token, result session lease and content capability are non-substitutable; browser paths/payloads never authorize reads. [VERIFIED: UI-SPEC] |
| V5 Input Validation | yes | Pydantic strict models, primary-input validation, deterministic environment parse, image byte/format/size/pixel validation. [VERIFIED: codebase] |
| V6 Cryptography | yes | stdlib HMAC-SHA256, `secrets`, constant-time compare; never hand-roll. [VERIFIED: `approval.py`] |
| V12 / ASVS 5.0 File Handling | yes | allowlisted image content, generated output names, root confinement, rehash, safe errors, size limits. [CITED: https://owasp.org/www-project-application-security-verification-standard/; CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html] |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Arbitrary local path/file upload | Tampering / EoP | native single upload, constrained temp root, real-byte validation, generated redacted path, no browser path authority. [CITED: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html] |
| Stale/cross-session preview approval | Spoofing / Tampering | session+revision+TTL+one-time atomic compare/pop. [VERIFIED: UI-SPEC] |
| Raw secret/path in DOM/error/log | Information Disclosure | repr-hidden strict state, redacted-only presentation, safe error code, URL capability. [VERIFIED: codebase/UI-SPEC] |
| Duplicate or late callbacks | Tampering / DoS | bounded queue plus server CAS; deduplicated aria-live. [VERIFIED: UI-SPEC] |
| Replay presented as live | Spoofing / Repudiation | orthogonal ResultMode, amber/literal replay labels, no live approval badge. [VERIFIED: UI-SPEC] |
| Malicious image resource use | DoS | 10 MiB and 20 MP gates before OCR, deterministic decode/rewrite. [VERIFIED: `image_models.py`] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| — | None. Recommendations are derived from locked context, inspected code/tests, official docs, registry metadata and local environment probes. | — | — |

## Open Questions

1. **Should screenshot audit extend `PreviewBundle` or be a sibling strict preview result?**
   - What we know: current `PreviewBundle` cannot represent screenshot findings/OCR status, while approval signs `preview_hash` and redacted fields. [VERIFIED: codebase]
   - Recommendation: extend `PreviewBundle` with a value-free `ScreenshotPreviewAudit` included in `preview_hash`; this best binds what the user reviewed. [VERIFIED: architecture analysis]

2. **Where should the Gradio upload cache root be configured?**
   - What we know: Gradio supports `GRADIO_TEMP_DIR`, upload files are placed in its cache, and broad cache paths can be served. [CITED: https://gradio.app/guides/file-access]
   - Recommendation: ordinary `serve.py` owns an absolute `.debugmate-runtime/gradio-cache` before app construction, preview accepts only files resolved under that root, and launch uses the 10 MiB max. Verify exact behavior in an integration test because the root venv is currently incomplete. [VERIFIED: environment/code analysis]

3. **How much Phase 07 Edge evidence is sufficient?**
   - What we know: UI-SPEC mandates nine fresh categories and existing Phase 4 already covers general result tabs/downloads. [VERIFIED: UI-SPEC; Phase 4 verification]
   - Recommendation: capture the mandated Phase 07 privacy/input states only; reuse but rerun targeted existing result regressions, do not refresh final media. [VERIFIED: phase boundary]

## Sources

### Primary (HIGH confidence)

- Repository code and tests: `src/debugmate/privacy/*`, `src/debugmate/diagnosis/providers.py`, `src/debugmate/ui/{app,local_live,presentation,serve}.py`, `src/debugmate/results/service.py`, `tests/privacy/*`, `tests/ui/*` — live contracts and gaps inspected 2026-08-09.
- `.planning/phases/07-real-input-privacy-ui/07-CONTEXT.md` and `07-UI-SPEC.md` — locked phase and UI/security decisions.
- [Gradio File documentation](https://www.gradio.app/docs/gradio/file) — single/filepath value and event behavior.
- [Gradio queuing](https://www.gradio.app/main/guides/queuing) — `concurrency_limit` and shared `concurrency_id`.
- [Gradio file access](https://gradio.app/guides/file-access) — cache exposure, `GRADIO_TEMP_DIR`, upload size and allowed-path guidance.
- [RapidOCR usage](https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/) — 3.9 defaults, CPU recommendation, result contract.
- PyPI JSON for gradio, rapidocr, onnxruntime, pydantic, Pillow, pytest and Ruff — versions/publish dates checked 2026-08-09.
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) — content, filename, storage and size controls.
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) — security verification categories.

### Secondary (MEDIUM confidence)

- `.planning/phases/04-multimodal-results-ui/04-VERIFICATION.md`, `04-09-SUMMARY.md`, `04-11-SUMMARY.md`, `04-12-SUMMARY.md` — historical execution counts and validated Phase 4 patterns; current code was separately inspected.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pinned project metadata, PyPI JSON and official docs agree.
- Architecture: HIGH — recommended path is a narrow extension of inspected strict contracts and locked UI-SPEC.
- Race/security model: HIGH — UI-SPEC enumerates event orders; existing lock/token tests provide a base.
- Environment readiness: HIGH — probed exact root venv imports and local CLI/file versions on 2026-08-09.
- Browser integration details: MEDIUM-HIGH — official Gradio contracts verified, but exact 6.20 runtime behavior must be rerun after repairing the incomplete venv.

**Research date:** 2026-08-09  
**Valid until:** 2026-09-08 for the pinned Phase 07 stack; re-check registry/docs only if changing pins.
