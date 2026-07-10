# Phase 1: 工程骨架与平台能力闸门 - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段只建立平台无关的工程骨架、冻结 `DiagnosisRecord v1` 与 evidence 目录契约，并用一个最小虚构案例验证 Dify Cloud 的文件上传、视觉输入、知识检索、结构化输出、DSL/API 和 TTS 能力。完整知识库、脱敏、诊断逻辑、多模态界面和评测分别属于后续阶段。

</domain>

<decisions>
## Implementation Decisions

### 平台能力闸门
- **D-01:** Dify Cloud 是正式主路径；Phase 1 的在线探针最长占用 4 小时，避免账号、额度或节点配置吞噬课程时间。
- **D-02:** 闸门逐项记录 `pass / fail / blocked / not-tested`，至少覆盖账号/API、文件上传、视觉模型、知识检索、结构化 JSON、DSL 导入导出和 TTS MP3。
- **D-03:** Dify 任一核心能力失败时，不隐瞒或伪造成功：先保留本地 fixture 跑通合同；若 Dify 因网络或账号不可用，再对 Coze 做一次同样受时间限制的替代探针，不并行维护两套正式流程。
- **D-04:** 任何充值、付费 API 或订阅都必须在发生前单独取得用户确认；Phase 1 默认只使用免费额度和本机工具。

### 诊断合同与案例标识
- **D-05:** `DiagnosisRecord v1` 使用 Pydantic v2 严格模式和 `extra='forbid'`，由模型生成 JSON Schema，并将 Schema 作为云端输出和本地验证的共同契约。
- **D-06:** `case_id` 使用 `case_<uuid4 hex>` 格式，不引入额外 ID 依赖；同一 case ID 必须贯穿输入、运行记录、诊断对象和后续产物。
- **D-07:** 首个合法 fixture 只包含虚构 Windows 路径、虚构用户名和可公开的 Python `ModuleNotFoundError`，不放置真实密钥、账号或个人信息。
- **D-08:** Phase 1 只验证合同、序列化、哈希和目录关联，不实现完整错误路由、引用判断或修复建议质量。

### 证据目录与运行清单
- **D-09:** 每次案例运行保存到 `evidence/<case_id>/`；Phase 1 最少包含 `input.redacted.json`、`diagnosis.json`、`manifest.json` 和 `probe-results.json`。
- **D-10:** `manifest.json` 最少记录 case ID、UTC 时间、后端、工作流/Prompt/Schema版本、输入SHA-256、run ID、节点状态、时延、Token/成本、产物路径与SHA-256。
- **D-11:** 证据写入采用“临时目录完成后原子重命名”的模式；失败运行也要生成显式状态的 manifest，不能留下看似成功的半成品目录。
- **D-12:** Phase 1 的云端探针只使用脱敏虚构输入；API key 只从环境变量读取，禁止进入命令输出、fixture、日志、DSL或Git。

### 仓库与适配器边界
- **D-13:** Python 包采用 `src/debugmate/` 布局；合同、证据、平台适配器和CLI入口分层，云平台差异不得渗入领域模型。
- **D-14:** 首版平台端口只定义 DebugMate 实际需要的窄接口：上传文件、运行诊断工作流、请求 TTS、读取最小运行元数据；不设计通用 Agent SDK。
- **D-15:** Git 仓库是唯一可提交事实源。Dify DSL、知识 manifest、Prompt、Schema、fixture 和探针报告都有固定路径；Dify 工作区只是可重建副本。
- **D-16:** Phase 1 必须提供不依赖云端的 fixture adapter，使合同测试和证据打包在没有账号/API时仍可执行；fixture 结果必须明确标记为 `backend=fixture`。

### the agent's Discretion
- `pyproject.toml` 的非功能性元数据、Ruff/pytest 细节和模块内部命名。
- 探针报告的终端表格样式与日志格式，只要机器可读 JSON 是事实源。
- 在不增加依赖的前提下选择原子写入和SHA-256辅助函数的具体组织方式。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目边界与验收
- `.planning/PROJECT.md` — 项目核心价值、低人工投入、多模态真实性和成本约束。
- `.planning/REQUIREMENTS.md` — Phase 1 对应 `INP-04`、`EVID-01`、`EVID-02` 的可测试要求。
- `.planning/ROADMAP.md` §Phase 1 — 阶段目标、成功标准和后续依赖。
- `.planning/STATE.md` — 当前阶段、Dify现场能力待验证事项。

### 技术与风险研究
- `.planning/research/STACK.md` — Dify Cloud + Python薄客户端、版本、平台闸门和降级方案。
- `.planning/research/ARCHITECTURE.md` — `DiagnosisRecord` 单一事实源、端口适配器、证据目录和构建顺序。
- `.planning/research/PITFALLS.md` — 平台锁定、Schema漂移、密钥泄漏、伪证据与Windows路径风险。
- `.planning/research/SUMMARY.md` — 研究综合结论与六阶段顺序。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 当前没有产品代码；可复用资产仅为 `.planning/` 中已核验的需求、架构、栈和风险文档。

### Established Patterns
- Git规划提交已采用原子提交，后续实现继续只暂存计划内文件。
- Windows路径必须使用 `pathlib`、UTF-8和PowerShell `-LiteralPath`；不得依赖易碎的中文路径字符串拼接。
- 云端页面不是事实源；所有重要配置和运行证据必须落盘。

### Integration Points
- Phase 1 将创建 Python 包、测试、fixture、evidence writer 和 Dify adapter seam；后续 Phase 2–4 在这些稳定边界上接入脱敏、知识库、诊断与多模态渲染。

</code_context>

<specifics>
## Specific Ideas

- 首个探针案例固定为 `ModuleNotFoundError`，因为容易真实复现、没有安全副作用，并能验证文本/截图两条输入路径。
- 探针报告应能直接成为课程PPT中的“平台选择依据”素材，但必须标注实际运行状态与日期。

</specifics>

<deferred>
## Deferred Ideas

- 正式知识库抓取、切片、元数据与重建 — Phase 2。
- OCR脱敏、提示注入防护和输入完整性追问 — Phase 2–3。
- 完整诊断路由、引用支撑和受控JSON修复 — Phase 3。
- PNG、MP3、Gradio结果页和下载包 — Phase 4。

</deferred>

---

*Phase: 01-foundation-platform-gate*
*Context gathered: 2026-07-10*
