# Project Research Summary

**Project:** DebugMate：面向 AI 专业学习场景的多模态报错诊断与复盘智能体  
**Domain:** 多模态 RAG 诊断智能体 / 课程工程交付  
**Researched:** 2026-07-10  
**Confidence:** HIGH（Dify/Python 主链路）；MEDIUM（云端额度、账号与 TTS provider 需现场探针）

## Executive Summary

DebugMate 不应实现为一个“会解释报错的聊天框”，而应实现为一条可审计、可回放的诊断生产线。用户提交文本或截图后，系统先在本地完成完整性检查和敏感信息清理，再由云端视觉模型、错误路由、专属知识库和诊断模型生成唯一的结构化 `DiagnosisRecord`；文字报告、PNG 诊断图和 MP3 语音复盘全部从该对象派生，并连同引用、版本、哈希和运行日志归档。

正式实现路径统一为 **Dify Cloud + Windows 本地 Python 薄客户端**。Dify 负责多模态模型调用、知识库 RAG 和工作流编排；Python 负责脱敏、契约校验、确定性图像与音频产物、Gradio 结果页、评测和课程证据包。扣子 Coze 只在 Dify 账号或网络不可用时进行最多 4 小时的替代能力探针，不同时维护两套正式工作流。

最大风险不是模型“答不出来”，而是看似完成却无法证明：引用并不支持结论、日志或截图泄露 Token、多模态输出互相矛盾、评测被同一模型污染、云平台配置无法导出、演示依赖临时 URL。路线图必须先冻结数据契约和证据规范，再构建知识库与诊断链，最后才做 UI、评测和 PPT/视频自动化。

## Key Findings

### Recommended Stack

**Core technologies:**

- **Dify Cloud:** 视觉输入、知识检索、诊断 Workflow 和结构化 JSON 输出；用 DSL、API 和运行 ID 保存可迁移证据。
- **Python 3.13:** 本地脱敏、Dify API 适配、Pydantic/JSON Schema 校验、证据归档与自动化脚本。
- **Gradio:** 单用户课程演示页，统一展示输入、引用、文字报告、PNG 和 MP3。
- **Pillow/Graphviz 或模板渲染:** 从 `DiagnosisRecord` 确定性生成诊断卡和流程图，避免生成式图片出现错字或与诊断不一致。
- **Dify TTS 主路径 + 本地降级:** 首选 Dify Text-to-Audio；不可用时依次降级到 `edge-tts` 或 Windows SAPI + FFmpeg，并在 manifest 中记录后端。
- **Git + evidence manifest:** 知识源、提示词、Schema、评测集、DSL 和每次运行证据均进入仓库；云端状态不是唯一事实源。

不建议在本机自托管 Dify/Coze、同时维护两个云平台、首版引入 LangChain/LlamaIndex 或本地向量数据库。这些选择不会增加课程核心价值，却会显著增加 Windows 依赖和调试成本。

详见 [STACK.md](./STACK.md)。

### Expected Features

**Must have:**

- 文本/截图/代码/环境信息输入与自动字段抽取。
- 上传前和展示前双重敏感信息脱敏。
- 六类高频 AI/Python 报错路由。
- 带来源 URL、版本范围、抓取时间和哈希的专属知识库。
- 检索命中片段、元数据和引用位置可见。
- 结构化 `DiagnosisRecord`，区分事实、推断、缺失信息和置信度。
- 文字、PNG、MP3 三模态一致输出和统一结果页。
- 失败降级、运行追踪、可下载证据包。
- V1–V4 提示词对比和可重复评测集。
- 自动生成课程 PPT/视频所需的真实证据素材。

**Differentiators:**

- 一份诊断三种表达，并用相同 `case_id`、摘要哈希和版本验证一致性。
- 证据阶梯、不确定性表达和下一条最有信息量的检查命令。
- 学习型诊断、最小复现建议和 30–60 秒因果链语音复盘。
- 自动课程证据包、知识覆盖报告和提交前质量门禁。

**Defer:**

- 自动执行修复命令、全语言/全框架覆盖、完整仓库扫描、多人账号、社区、支付、移动原生应用和复杂多智能体自治。

详见 [FEATURES.md](./FEATURES.md)。

### Architecture Approach

架构采用“端口与适配器 + 阶段状态机 + 证据优先 RAG + 确定性多模态渲染”。稳定内核不依赖具体平台：

1. **Input/Redaction:** 接收文本和图片，提取字段，先脱敏再出本机。
2. **Platform Adapter:** 调用 Dify 文件、Workflow、知识检索和 TTS API；Coze/fixture 只实现相同窄接口。
3. **Diagnosis Domain:** 以 Pydantic/JSON Schema 冻结 `DiagnosisRecord v1`，所有下游只读该对象。
4. **Renderers:** 生成 Markdown/HTML、PNG 和 MP3，并写入相同案例标识和版本信息。
5. **Evidence Store:** 保存脱敏输入哈希、提示词/知识/模型版本、命中片段、原始 JSON、产物哈希、时延和成本。
6. **Evaluation:** 对固定案例运行契约、引用、隐私、一致性和错误诊断评分。
7. **Deliverables:** 从真实 evidence 目录汇总截图、表格、PPT 数据和视频素材。

详见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

### Critical Pitfalls

1. **间接提示注入:** 日志和知识文档都按不可信数据处理，不允许覆盖系统策略或调用外部动作。
2. **敏感信息多链路泄漏:** 先本地脱敏，再上传；日志、错误页、PNG、MP3和PPT均做二次扫描。
3. **引用存在但不支持结论:** 每个根因候选必须绑定命中片段，引用一致性进入评测门禁。
4. **平台锁定:** DSL、知识源、提示词、Schema、案例和产物均保存在 Git；空工作区做一次重建 smoke test。
5. **Schema 漂移:** 三种模态不能各自自由生成；只允许从已校验 `DiagnosisRecord` 派生。
6. **OCR/VLM 字符误读:** 回显关键行和不确定字符；高风险字段需要用户确认或降置信度。
7. **危险修复命令:** 首版不自动执行；每条命令注明平台、影响、预期和回退。
8. **评测泄漏:** 生成、调优和评分角色分离；关键案例用确定性故障脚本真实复现。
9. **伪证据:** 只使用真实运行截图、日志和文件哈希；回放案例明确标注为回放。
10. **云端成本/延迟失控:** 阶段缓存、流式调用、幂等重试和案例级成本账本。
11. **Windows 路径/编码:** UTF-8、`pathlib`、ASCII 临时目录和 FFprobe/文件头校验。

详见 [PITFALLS.md](./PITFALLS.md)。

## Implications for Roadmap

### Phase 1: 工程骨架与平台能力闸门

**Rationale:** 在配置大量云节点前确认账号、文件上传、结构化输出、知识检索、DSL/API和TTS是否真实可用。  
**Delivers:** 仓库结构、`DiagnosisRecord v1`、安全 fixture、Dify smoke test、平台决策记录。  
**Avoids:** 平台锁定、Schema 漂移和后期推倒重来。

### Phase 2: 知识库与输入安全

**Rationale:** 诊断可信度取决于知识源和脱敏，而不是提示词长度。  
**Delivers:** 官方知识源 manifest、自动抓取/清洗/切片、Dify 同步、检索测试、双重脱敏器。  
**Avoids:** 事实库污染、敏感信息泄漏和无效引用。

### Phase 3: 诊断工作流

**Rationale:** 先让一个文本/截图案例稳定生成合规结构化诊断，再扩展表现层。  
**Delivers:** VLM 抽取、输入完整性检查、六类路由、RAG、诊断提示词和 `DiagnosisRecord` 校验。  
**Avoids:** OCR误读、自由文本不可测和危险建议。

### Phase 4: 多模态产物与统一界面

**Rationale:** 三模态必须共享单一事实源，适合在核心诊断稳定后实现。  
**Delivers:** Markdown/HTML、PNG、MP3、Gradio结果页、下载包和降级链。  
**Avoids:** 文字/图像/语音各说各话和临时 URL 失效。

### Phase 5: 评测、提示词迭代与可靠性

**Rationale:** 课程必须展示提示词优化和局限，且需要真实量化证据。  
**Delivers:** 可复现故障脚本、固定评测集、V1–V4实验、引用/隐私/一致性/成本指标和回归门禁。  
**Avoids:** 评测泄漏、只挑成功案例和“看似完成”。

### Phase 6: 课程交付自动化

**Rationale:** 最终PPT与视频必须从真实工程证据生成，而不是临时拼接。  
**Delivers:** 项目说明、运行截图、案例卡、PPT/PPTX、讲解稿、TTS配音、字幕、最终视频和提交包QA。  
**Avoids:** 版本不一致、占位符、伪截图和遗漏硬性要求。

### Phase Ordering Rationale

- 平台能力和数据契约是所有后续模块的前置依赖。
- 知识库与脱敏必须早于真实云端诊断。
- 核心诊断先于多模态渲染，避免对不稳定输出做包装。
- 评测在核心闭环后建立，但故障 fixture 从 Phase 1 即开始积累。
- PPT/视频只在证据门禁通过后生成，确保所有展示均可追溯。

### Research Flags

- **Phase 1:** 需要现场核验 Dify Cloud 账号额度、可用视觉模型、TTS provider、DSL导入导出和API限制。
- **Phase 2:** 需要核对各官方文档的抓取许可、版本元数据和切片质量。
- **Phase 3:** 需要验证结构化输出在所选模型上的稳定性和引用映射方式。
- **Phase 4:** Dify TTS 不可用时应立即启用本地降级，不扩大云平台调试范围。
- **Phase 5:** 评测标准需在看见模型输出前冻结一部分，降低调优泄漏。

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Dify官方API/知识库/DSL资料和本机Python条件足够；账号额度需探针 |
| Features | HIGH | 来自课程硬要求、明确用户约束和官方平台能力 |
| Architecture | HIGH | 端口适配、Schema单一事实源和证据归档均为成熟工程模式 |
| Pitfalls | HIGH | OWASP/NIST及平台官方文档支持，且与课程真实性约束一致 |

**Overall confidence:** HIGH

### Gaps to Address

- **Dify现场能力:** Phase 1 用一个截图、一个Markdown知识文档和一个MP3请求完成真实端到端探针。
- **API/模型费用:** 在任何付费配置前记录免费额度和单案例估算，超预算则换模型或启用降级。
- **知识文档许可:** 每个来源记录 terms/licence note；交付包优先保存自编摘要和来源链接，不大规模再分发受限原文。
- **最终界面形态:** 以Gradio为默认，待Phase 1确认平台Webapp可展示全部证据后再决定是否双入口。

## Sources

### Primary (HIGH confidence)

- [Dify 30-Minute Quick Start](https://docs.dify.ai/en/guides/application-orchestrate/creating-an-application) — Workflow、文本/文档/图像输入和视觉分流。
- [Dify Knowledge Retrieval](https://docs.dify.ai/en/use-dify/nodes/knowledge-retrieval) — 命中片段、元数据过滤和视觉上下文。
- [Dify Text-to-Audio API](https://docs.dify.ai/api-reference/tts/convert-text-to-audio) — MP3音频响应契约。
- [Dify official repository](https://github.com/langgenius/dify) — 云端/自托管边界和DSL生态。
- [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — 提示注入、敏感信息、不安全输出和过度授权风险。
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) — 可追溯、测量和风险治理原则。

### Secondary (MEDIUM confidence)

- [Coze official overview](https://www.coze.cn/overview) — 工作流、云端部署和多媒体产物方向；细粒度导出能力需账号内实测。
- [Coze Python SDK](https://github.com/coze-dev/coze-py) — Workflow、Dataset、文件与音频相关SDK表面。

---
*Research completed: 2026-07-10*  
*Ready for roadmap: yes*
