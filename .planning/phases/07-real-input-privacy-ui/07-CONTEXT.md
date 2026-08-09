# Phase 7: 真实输入与隐私预览接线 - Context

**Gathered:** 2026-08-09
**Status:** Ready for planning
**Mode:** Autonomous smart discuss; proposals accepted from repository evidence and standing user preferences

<domain>
## Phase Boundary

让普通 Gradio 页面接受真实报错文本、代码、环境和截图，并在任何云调用前复用既有本地校验、文本/图像脱敏、预览与 HMAC 审批合同。本阶段不接 Dify；Phase 8 才负责云端诊断接线。固定回放必须继续作为独立、明确标记的演示模式存在。

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/debugmate/privacy/models.py`：严格 Raw/Redacted/Preview/Approved 合同。
- `src/debugmate/privacy/preview.py`、`approval.py`：文本/图像预览与 HMAC 批准。
- `src/debugmate/privacy/image_validation.py`、`image_redactor.py`：截图格式、哈希与像素遮挡。
- `src/debugmate/diagnosis/providers.py`：生产 OCR/VLM 抽取 provider。
- `src/debugmate/ui/app.py`：双区布局、opaque token callbacks、结果状态与下载能力。
- `src/debugmate/ui/local_live.py`：当前固定 demo store，需要泛化而不是复制一条旁路。

### Established Patterns
- Pydantic `strict=True`、`extra='forbid'`；路径必须 root-confined、normalized、rehashed。
- Gradio browser state 不可信，服务器持有严格状态；状态提交使用一次性 lease/token。
- 回放、live、fallback 必须在 UI 上真实区分。
- 修改产品行为先写 RED，按聚焦 pytest、Ruff、Edge 浏览器测试验证。

### Integration Points
- Phase 7 输出 `ApprovedRedactedInput`，Phase 8 将其交给 Dify/live diagnosis service。
- 当前 `prepare_local_preview` 和 `LocalPreviewStore.create()` 是替换固定 payload 的主要入口。
- `build_app()` 输入区与 callbacks 是 UI 接线位置；`serve.py` 负责生产 OCR provider 构造。

</code_context>

<specifics>
## Specific Ideas

- 用户此前明确认为当前页面不友好，因此真实输入必须保持清晰、逐步和学生可理解，不能退回工程控制台式多栏表单。
- 所有视频、PPTX、字幕和最终截图继续冻结到 Phase 10。

</specifics>

<deferred>
## Deferred Ideas

- Dify backend、统一 live run 和云端故障降级：Phase 8。
- 代表案例、提示词同案例比较：Phase 9。
- PPTX、视频、字幕、最终截图：Phase 10。
- 目录上传、语音输入、多用户和命令执行：V0.1 范围外。

</deferred>
