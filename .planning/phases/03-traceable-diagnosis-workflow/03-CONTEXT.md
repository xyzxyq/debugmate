# Phase 3: 可追溯诊断工作流 - Context

**Gathered:** 2026-07-12
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段把已确认的脱敏文本/截图输入转换为可纠错的结构化事实，完成信息充分性判断、六类错误路由、知识检索绑定和严格诊断生成，产出经过本地契约校验的 `DiagnosisRecord v1`。本阶段提供纠错与重跑的领域/API 边界，但不建设最终 Gradio 页面；文字报告、PNG、MP3 和统一结果页属于 Phase 4。

</domain>

<decisions>
## Implementation Decisions

### 抽取事实与纠错重跑
- **D3-01:** 建立严格 `ExtractionRecord`/`CaseFacts`，异常类型、Traceback 关键行、包名、版本、设备和路径候选均带稳定字段 ID、来源（text/OCR/VLM/user）、置信度和原始定位信息。
- **D3-02:** OCR/VLM 输出只能作为候选事实，不能直接成为诊断结论；本地规范化、类型校验和隐私复扫通过后才可进入事实草稿。
- **D3-03:** 用户纠错使用显式 correction overlay，保留原候选、修改前后哈希和 revision；重跑沿用同一 `case_id`，但生成新的事实哈希、run ID 和诊断记录。
- **D3-04:** Phase 3 交付 JSON/CLI/API 纠错边界与回放测试；可视化字段编辑器留给 Phase 4 结果页集成。

### 信息充分性与有限追问
- **D3-05:** 使用按错误类别维护的确定性充分性矩阵来识别缺失信息，优先级由“能否改变路由或根因排序”决定，不让 LLM 自由生成无限追问。
- **D3-06:** 每次只返回最多三项高价值问题，问题必须指向结构化字段和预期格式；同一缺失项不得重复追问。
- **D3-07:** 经过一次补充后仍缺少关键事实时，工作流以 `insufficient_information` 显式结束；允许返回已知事实、缺失项和安全检查建议，但不得伪造确定根因。

### 路由、证据与不确定性
- **D3-08:** 六类路由采用确定性规则优先、受限模型候选补充；规则冲突或置信度低于门槛时使用 `unknown`，不为了覆盖率强行归类。
- **D3-09:** `DiagnosisRecord v1` 在同一 major 版本内进行可迁移的契约升级：观察事实和引用拥有稳定 ID，根因候选通过显式 support links 同时绑定事实 ID 与检索锚点，禁止仅靠相似文本暗示支撑关系。
- **D3-10:** 事实、推断和未知必须在结构中分开表达；每个根因候选包含置信度、适用条件和反证/限制，无引用支持的内容只能标为推断。
- **D3-11:** 检索只接受已验证知识 build ID 和严格 `RetrievalTrace`；诊断 evidence 保存命中摘要、来源、分数和 locator，不保存完整 raw chunk。

### 结构化生成与安全失败
- **D3-12:** 云端 Dify/视觉模型只产生候选抽取或候选诊断；本地 Python 是最终合同、引用完整性、命令安全和 evidence 发布的裁决者。
- **D3-13:** 模型 JSON 首次不合规时最多进行一次受控修复，修复提示只包含 Schema 错误路径和脱敏候选；第二次失败即返回结构化失败，不拼接自由文本结果。
- **D3-14:** 检查、修复和验证命令始终是数据，必须包含平台、影响、预期结果和回退；工作流、CLI 和适配器均不提供执行命令的能力。
- **D3-15:** 默认测试使用可复现 fixture/replay，覆盖六类错误、`unknown`、信息不足、纠错重跑、引用不足和 Schema 修复；真实 Dify/VLM 运行保持 marker 隔离并明确标注 backend。

### the agent's Discretion
- 充分性矩阵和路由规则的内部组织、阈值常量以及稳定 ID 的具体编码方式。
- 一次受控修复的实现位置（适配器或领域服务），只要原始响应不进入 evidence 且仅重试一次。
- Phase 3 CLI 子命令命名、终端展示格式和测试 fixture 的具体虚构包名。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目边界与验收
- `.planning/PROJECT.md` — 核心价值、真实性、低人工投入、成本和不自动执行命令的约束。
- `.planning/REQUIREMENTS.md` — `INP-02`、`INP-03`、`SAFE-04`、`DIAG-01`～`DIAG-06` 的验收要求。
- `.planning/ROADMAP.md` §Phase 3 — 阶段目标、成功标准与 Phase 4 边界。
- `.planning/STATE.md` — Phase 2 已完成能力与 Dify/TTS 外部门禁。

### 合同、架构与风险
- `contracts/diagnosis-record-v1.schema.json` — 当前 `DiagnosisRecord v1` 基线，任何升级必须提供迁移和 fixture 更新。
- `.planning/research/ARCHITECTURE.md` — 单一事实源、诊断生成器、适配器和 evidence 架构。
- `.planning/research/PITFALLS.md` — Schema 漂移、伪引用、提示注入、命令执行和多模态不一致风险。
- `.planning/research/STACK.md` — Dify + Python 薄客户端、Pydantic 严格校验和本地降级策略。
- `.planning/research/SUMMARY.md` — Phase 3 建议的 VLM 抽取、路由、RAG 和诊断链路。

### 已完成的输入与知识边界
- `.planning/phases/02-knowledge-input-safety/02-CONTEXT.md` — 脱敏确认、官方知识、LLM 非权威和离线默认的锁定决定。
- `.planning/phases/02-knowledge-input-safety/02-VERIFICATION.md` — Phase 2 已验证能力、检索证据边界和真实云端门禁。
- `docs/superpowers/specs/2026-07-10-phase2-knowledge-input-safety-design.md` — 输入安全、知识来源与 evidence 约束。
- `platform/dify/README.md` — Dify 工作流输出与 `DiagnosisRecord` 适配约定。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/debugmate/contracts.py`: 已有严格 `DiagnosisRecord`、七类 `ErrorCategory`、`Citation`、`CommandStep` 和 Schema 生成入口，可在 major v1 内迁移扩展。
- `src/debugmate/privacy/`: 已有文本/截图脱敏、OCR 候选、预览确认和 HMAC approval，可作为事实抽取唯一入口。
- `src/debugmate/knowledge/retrieval.py`: 已有严格 RetrievalTrace、来源锚点校验、离线真实检索和评测，可直接供诊断 evidence binding 使用。
- `src/debugmate/gateway.py`: 只接受 `ApprovedRedactedInput` 的云端门禁，可扩展为 Phase 3 诊断用例入口。
- `src/debugmate/evidence.py`: 已有原子 evidence、隐私复扫和 fail-closed 二进制门禁，可保存事实、检索、诊断和失败记录。
- `src/debugmate/adapters/dify.py` / `fixture.py`: 已有 Dify 与 fixture 后端窄接口、严格响应校验和错误分类。

### Established Patterns
- 所有外部/模型对象在公共边界重新严格验证，阻断 `model_copy`、dict 和多余字段绕过。
- 真实在线、OCR 和 cloud 测试使用 marker 隔离；默认回归完全离线。
- 只有脱敏、带来源且哈希绑定的数据能进入云端或 evidence；错误消息不得回显原始模型响应和敏感值。
- 所有可提交事实由 Git 中的 Schema、prompt、fixture、测试和生成脚本定义，平台 UI 不是事实源。

### Integration Points
- 在 `CloudGateway.run()` 前后插入结构化抽取/充分性/路由/检索/诊断 orchestration，而不把领域逻辑放进 Dify adapter。
- 扩展 `DiagnosisBackend` 或新增更窄的 extraction/diagnosis ports，保持 fixture 与 Dify 同合同。
- Phase 3 诊断完成后由 Phase 4 只读已验证 `DiagnosisRecord` 生成文字、PNG 和 MP3。

</code_context>

<specifics>
## Specific Ideas

- 固定演示主案例继续使用 `ModuleNotFoundError`，同时自动生成路径权限、Python runtime、tensor shape/dtype、CUDA OOM、model loading 与 unknown fixture，保证六类路由可见。
- 诊断结果应像“工程排障记录”而不是聊天回答：老师能看见输入事实、为什么这样分类、引用了哪一段官方文档、还缺什么以及下一步如何验证。
- 所有失败状态都要能进入真实 PPT/视频素材，但必须标注 fixture、offline replay、Dify cloud 或 insufficient，不能把回放当实时云运行。

</specifics>

<deferred>
## Deferred Ideas

- Gradio 字段编辑器、统一结果页、文字报告、PNG 和 MP3 — Phase 4。
- 自动执行修复命令 — 明确不在 v1 范围内。
- 提示词 V1～V4 系统评测、质量门禁与课程图表 — Phase 5。

</deferred>

---

*Phase: 03-traceable-diagnosis-workflow*
*Context gathered: 2026-07-12*
