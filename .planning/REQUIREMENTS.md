# Requirements: DebugMate

**Defined:** 2026-07-10  
**Core Value:** 对真实或可复现的 AI/Python 报错，基于专属知识库生成有依据、可执行、说明不确定性的诊断，并同步输出一致的文字、图像和语音结果。

## v1 Requirements

### 输入与抽取

- [x] **INP-01**: 用户可以提交报错文本、终端截图、代码片段和基础环境信息，且文本或截图至少提供一项。
- [ ] **INP-02**: 系统可以从截图中抽取异常类型、Traceback关键行、包名、版本、设备和路径候选，并向用户回显抽取结果。
- [ ] **INP-03**: 系统可以检测影响诊断的缺失信息，并只追问最多三项高价值信息；信息仍不足时允许以“不足以确定”结束。
- [ ] **INP-04**: 系统为每次诊断生成唯一 `case_id`，并在输入、诊断和全部输出产物之间保持关联。

### 安全与隐私

- [x] **SAFE-01**: 系统在任何输入离开本机前遮蔽 Token、密码、邮箱、用户名、绝对路径和常见私有标识，并保存脱敏审计结果。
- [x] **SAFE-02**: 系统在结果展示和证据导出前再次扫描文本、PNG元数据、音频讲稿和日志，阻止敏感内容进入课程材料。
- [x] **SAFE-03**: 系统把日志、截图、代码和知识文档都视为不可信数据，禁止其中的文本覆盖系统指令或触发外部动作。
- [ ] **SAFE-04**: 系统不自动执行诊断生成的修复命令；每条命令标注适用平台、影响、预期结果和必要的回退说明。

### 专属知识库

- [x] **KNOW-01**: 项目维护一个官方知识源 manifest，首版覆盖 Python、pip/venv、PyTorch、CUDA、Hugging Face、Ultralytics 和 Windows 路径问题。
- [x] **KNOW-02**: 每个知识源条目包含标题、URL、产品、版本范围、适用平台、抓取时间、内容哈希和许可/使用说明。
- [x] **KNOW-03**: 项目可以从本地知识源重建 Dify 知识库，并验证文档数量、元数据和检索配置与 manifest 一致。
- [x] **KNOW-04**: 系统在诊断运行中保存命中的 chunk ID、内容摘要、来源元数据、相关性分数和引用位置。
- [x] **KNOW-05**: 项目可以按错误类别输出知识覆盖、评测命中率、盲区和最后更新时间报告。

### 诊断工作流

- [ ] **DIAG-01**: 系统可以把案例路由到依赖/环境、路径/权限、Python运行时、张量形状/类型、CUDA/显存、模型加载六类之一或“未知”。
- [ ] **DIAG-02**: 系统可以根据结构化输入和知识检索结果生成符合 `DiagnosisRecord v1` JSON Schema 的诊断对象。
- [ ] **DIAG-03**: 每个根因候选都绑定观察证据和知识片段；无法由引用支持的内容必须标记为推断而非事实。
- [ ] **DIAG-04**: 诊断对象包含根因候选、检查步骤、修复步骤、验证命令、缺失信息、置信度、局限和适用环境。
- [ ] **DIAG-05**: 系统在 JSON 结构不合规时最多进行一次受控修复重试；仍失败则显式失败，不拼接伪造结果。
- [ ] **DIAG-06**: 用户可以看到影响结论的关键抽取字段并纠正 OCR/VLM 误读，然后重新运行诊断。

### 多模态输出

- [ ] **MULTI-01**: 系统可以从已校验的 `DiagnosisRecord` 生成结构化中文文字诊断报告，并保留英文错误原文和命令。
- [ ] **MULTI-02**: 系统可以从同一 `DiagnosisRecord` 确定性生成包含根因、检查路径和修复验证步骤的 PNG 诊断卡或流程图。
- [ ] **MULTI-03**: 系统可以从同一 `DiagnosisRecord` 生成30–60秒中文复盘稿并转换为可播放、可下载的 MP3。
- [ ] **MULTI-04**: 文字、PNG和MP3共享相同 `case_id`、诊断摘要哈希、Schema版本和生成版本；一致性检查失败时不得进入交付证据。
- [ ] **MULTI-05**: TTS或PNG主后端不可用时，系统可以启用已记录的本地降级后端并在结果中明确标识。

### 结果页与可回放性

- [ ] **UX-01**: 用户可以在单一Gradio结果页查看脱敏后的输入、关键抽取字段、检索依据、文字报告、PNG和音频播放器。
- [ ] **UX-02**: 用户可以下载单案例证据包，包含诊断JSON、报告、PNG、MP3、引用、运行manifest和校验值。
- [ ] **UX-03**: 系统可以加载固定脱敏案例进行离线回放，并在界面和视频中明确标注“回放”而非实时云端运行。
- [ ] **UX-04**: 任一工作流阶段失败时，用户可以看到失败节点、已完成阶段、可重试范围和可用的降级结果。

### 评测与提示词迭代

- [ ] **EVAL-01**: 项目包含可重复执行的评测集，覆盖六类报错、信息不足、易混淆、提示注入、隐私泄漏和平台降级案例。
- [ ] **EVAL-02**: 关键正确案例由本机确定性故障脚本真实生成 Traceback，而不是只由同一个LLM编造输入和答案。
- [ ] **EVAL-03**: 项目保存 V1–V4 提示词、修改目标、固定案例输出和采用/拒绝理由。
- [ ] **EVAL-04**: 评测至少计算分类正确性、Schema通过率、引用支持率、隐私泄漏数、三模态一致性、成功率、延迟和单案例成本。
- [ ] **EVAL-05**: 自动质量门禁在引用、隐私、Schema、PNG/MP3文件有效性或多模态一致性失败时标记案例不可用于PPT和视频。

### 工程证据与课程交付

- [ ] **EVID-01**: 每次运行保存脱敏输入哈希、工作流/提示词/知识库/模型版本、run ID、节点状态、时延、Token/成本和产物SHA-256。
- [ ] **EVID-02**: Git仓库保存知识源、manifest、提示词、Schema、Dify DSL、测试、评测结果和生成脚本，云平台不是唯一事实源。
- [ ] **EVID-03**: 项目可以从真实运行证据自动生成提示词对比表、评测图表、案例卡、工作流图和PPT素材清单。
- [ ] **EVID-04**: 项目交付作品说明、运行README、知识库说明、效果截图、PPTX、讲解稿、AI配音、字幕和最终讲解视频。
- [ ] **EVID-05**: 提交前QA可以检查占位符、失效链接、缺失引用、文件可播放性、PPT溢出、视频时长和材料版本一致性。

## v2 Requirements

### 扩展输入

- **EXT-01**: 用户可以上传一个经过白名单过滤的小型代码目录，系统只读分析允许的文本文件。
- **EXT-02**: 系统支持语音描述问题并自动转写为诊断输入。

### 扩展知识域

- **EXT-03**: 知识库扩展到 TensorFlow、JAX、ONNX Runtime 和更多操作系统。
- **EXT-04**: 用户可以选择知识库版本快照，比较同一报错在不同框架版本下的建议。

### 扩展体验

- **EXT-05**: 用户可以将已验证的诊断保存为个人复习卡和知识图谱节点。
- **EXT-06**: 系统支持多轮追踪同一问题的修复进度，但仍不自动执行命令。

## Out of Scope

| Feature | Reason |
|---------|--------|
| 自动执行Shell、PowerShell或包安装命令 | 可能破坏用户环境并扩大安全评测范围，不是课程核心要求 |
| 训练自有OCR、LLM、Embedding或TTS模型 | 需要数据和算力，与低人工投入目标冲突 |
| 同时维护Dify和Coze两套正式工作流 | 双倍配置和回归成本，极易造成Prompt与知识版本漂移 |
| 本机自托管Dify/Coze | 当前无Docker，部署和运维成本高于课程价值 |
| 论坛内容直接作为事实知识库 | 版本与质量不可控；首版只接受官方或可核验来源 |
| 多用户账号、权限、支付、社区和排行榜 | 与单用户课程演示无关 |
| 生成式技术插画充当诊断证据 | 容易产生错字和逻辑不一致；核心PNG必须确定性渲染 |
| 伪造终端、平台或评测截图 | 违反真实性要求，所有展示必须来自真实运行或明确标注的回放 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INP-01 | Phase 2 | Complete |
| INP-02 | Phase 3 | Pending |
| INP-03 | Phase 3 | Pending |
| INP-04 | Phase 1 | Pending |
| SAFE-01 | Phase 2 | Complete |
| SAFE-02 | Phase 2 | Complete |
| SAFE-03 | Phase 2 | Complete |
| SAFE-04 | Phase 3 | Pending |
| KNOW-01 | Phase 2 | Complete |
| KNOW-02 | Phase 2 | Complete |
| KNOW-03 | Phase 2 | Complete |
| KNOW-04 | Phase 2 | Complete |
| KNOW-05 | Phase 2 | Complete |
| DIAG-01 | Phase 3 | Pending |
| DIAG-02 | Phase 3 | Pending |
| DIAG-03 | Phase 3 | Pending |
| DIAG-04 | Phase 3 | Pending |
| DIAG-05 | Phase 3 | Pending |
| DIAG-06 | Phase 3 | Pending |
| MULTI-01 | Phase 4 | Pending |
| MULTI-02 | Phase 4 | Pending |
| MULTI-03 | Phase 4 | Pending |
| MULTI-04 | Phase 4 | Pending |
| MULTI-05 | Phase 4 | Pending |
| UX-01 | Phase 4 | Pending |
| UX-02 | Phase 4 | Pending |
| UX-03 | Phase 4 | Pending |
| UX-04 | Phase 4 | Pending |
| EVAL-01 | Phase 5 | Pending |
| EVAL-02 | Phase 5 | Pending |
| EVAL-03 | Phase 5 | Pending |
| EVAL-04 | Phase 5 | Pending |
| EVAL-05 | Phase 5 | Pending |
| EVID-01 | Phase 1 | Pending |
| EVID-02 | Phase 1 | Pending |
| EVID-03 | Phase 6 | Pending |
| EVID-04 | Phase 6 | Pending |
| EVID-05 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-10*  
*Last updated: 2026-07-10 after roadmap creation*
