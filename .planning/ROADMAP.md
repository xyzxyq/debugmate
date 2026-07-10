# Roadmap: DebugMate

## Overview

DebugMate v1 按“契约与证据先行、可信诊断成链、三模态统一派生、真实评测守门、课程材料可追溯”的顺序推进。前两阶段先消除平台能力、数据契约、知识来源和隐私风险；第三阶段打通可引用、可纠错的诊断主链；第四阶段完成文字、PNG、MP3 与统一结果页；第五阶段用真实故障与固定指标建立质量门禁；第六阶段只从通过门禁的真实证据生成课程提交包。

## Phases

- [x] **Phase 1: 工程骨架与平台能力闸门** - 冻结案例标识、运行证据和仓库事实源，并验证 Dify 主链能力。 (completed 2026-07-10)
- [ ] **Phase 2: 知识库与输入安全** - 建立可重建的官方知识库和输入/输出双重安全边界。
- [ ] **Phase 3: 可追溯诊断工作流** - 从截图与文本稳定生成有引用、可纠错、说明不确定性的结构化诊断。
- [ ] **Phase 4: 三模态产物与统一结果页** - 从同一诊断对象生成文字、PNG、MP3，并支持查看、下载、回放和降级。
- [ ] **Phase 5: 评测、提示词迭代与可靠性门禁** - 用可复现案例和固定指标验证正确性、安全性、一致性与成本。
- [ ] **Phase 6: 课程交付自动化** - 从真实运行证据生成并检查完整的 PPT、讲解与视频提交包。

## Phase Details

### Phase 1: 工程骨架与平台能力闸门
**Goal**: 项目拥有平台无关的数据契约、可审计运行记录和可重建仓库骨架，并以真实探针决定 Dify 主路径及降级边界。  
**Depends on**: Nothing (first phase)  
**Requirements**: INP-04, EVID-01, EVID-02  
**Success Criteria** (what must be TRUE):
  1. 每个测试案例都获得唯一 `case_id`，输入、运行记录和后续产物可通过该标识关联。
  2. 一次平台探针可真实验证文件上传、视觉输入、知识检索、结构化输出、DSL/API 和 TTS，并留下可复核的能力矩阵与决策记录。
  3. 每次探针运行都保存脱敏输入哈希、run ID、节点状态、版本、时延、Token/成本和产物校验值。
  4. 在不依赖云端页面的情况下，仓库中可找到知识源、manifest、提示词、Schema、Dify DSL、测试与生成脚本的版本化位置。
**Plans**: 3 plans

- `01-01` — 工程骨架、严格诊断合同与离线 fixture 后端。
- `01-02` — 哈希、安全设置和原子 evidence bundle。
- `01-03` — Dify 适配层、七能力探针与平台重建资产。
**UI hint**: no

### Phase 2: 知识库与输入安全
**Goal**: 用户输入在进入云端前已完成完整性校验和脱敏，诊断所用知识可从官方来源重建、检索和审计。  
**Depends on**: Phase 1  
**Requirements**: INP-01, SAFE-01, SAFE-02, SAFE-03, KNOW-01, KNOW-02, KNOW-03, KNOW-04, KNOW-05  
**Success Criteria** (what must be TRUE):
  1. 用户可提交报错文本、终端截图、代码片段和环境信息；文本与截图均缺失时系统会在本机阻止提交并明确原因。
  2. Token、密码、邮箱、用户名、绝对路径和常见私有标识在离开本机前被遮蔽，且用户可查看脱敏审计结果。
  3. 结果文本、PNG 元数据、音频讲稿和日志在导出前通过二次扫描；日志、截图、代码或知识文档中的指令性文本不能覆盖系统策略或触发外部动作。
  4. 开发者可从官方知识源 manifest 重建 Dify 知识库，并验证文档数、来源元数据、内容哈希和检索配置一致。
  5. 每次检索均可回看 chunk ID、摘要、来源、相关性分数和引用位置，并可生成按错误类别划分的覆盖、命中率、盲区及更新时间报告。
**Plans**: 3 plans

- `02-01` — 严格输入合同、文本脱敏、预览审批、云端类型门禁与导出二次扫描。
- `02-02` — 本地截图校验、OCR 候选定位、确定性像素遮挡与预览集成。
- `02-03` — 精选官方源注册、抓取摘录、知识构建、覆盖/命中率与 Dify dry-run 同步。
**UI hint**: no

### Phase 3: 可追溯诊断工作流
**Goal**: 用户可将文本或截图案例转化为经过契约校验、引用支撑且允许纠错的 `DiagnosisRecord v1`。  
**Depends on**: Phase 2  
**Requirements**: INP-02, INP-03, SAFE-04, DIAG-01, DIAG-02, DIAG-03, DIAG-04, DIAG-05, DIAG-06  
**Success Criteria** (what must be TRUE):
  1. 用户上传截图后可看到异常类型、Traceback 关键行、包名、版本、设备和路径候选，并能纠正误读字段后重新诊断。
  2. 信息不足时系统只追问最多三项高价值信息；仍不足时明确返回“不足以确定”，而不是编造根因。
  3. 案例可被路由到六类高频错误之一或“未知”，并生成符合 `DiagnosisRecord v1` Schema 的诊断对象。
  4. 每个根因候选都绑定观察证据和知识片段；报告清楚区分事实、推断、缺失信息、置信度、局限与适用环境。
  5. JSON 不合规时系统最多受控修复一次；仍失败则显式失败；修复命令不会自动执行，并标明平台、影响、预期与回退说明。
**Plans**: TBD  
**UI hint**: yes

### Phase 4: 三模态产物与统一结果页
**Goal**: 用户可在单一界面查看并下载由同一已校验诊断对象派生的一致文字、PNG 与 MP3 结果。  
**Depends on**: Phase 3  
**Requirements**: MULTI-01, MULTI-02, MULTI-03, MULTI-04, MULTI-05, UX-01, UX-02, UX-03, UX-04  
**Success Criteria** (what must be TRUE):
  1. 同一 `DiagnosisRecord` 可生成结构化中文报告、确定性 PNG 诊断图和 30–60 秒可播放 MP3，且保留英文错误原文与命令。
  2. 三种产物共享 `case_id`、诊断摘要哈希、Schema 版本和生成版本；一致性检查失败的案例不会进入交付证据。
  3. 用户可在单一 Gradio 结果页查看脱敏输入、抽取字段、检索依据、文字报告、PNG 和音频播放器。
  4. 用户可下载包含诊断 JSON、报告、PNG、MP3、引用、运行 manifest 和校验值的单案例证据包。
  5. PNG/TTS 主后端不可用或工作流节点失败时，界面会显示失败节点、已完成阶段、可重试范围与本地降级结果；固定案例回放会明确标注“回放”。
**Plans**: TBD  
**UI hint**: yes

### Phase 5: 评测、提示词迭代与可靠性门禁
**Goal**: 项目可以重复、量化地证明诊断质量、安全性和三模态一致性，并阻止不合格案例进入展示材料。  
**Depends on**: Phase 4  
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05  
**Success Criteria** (what must be TRUE):
  1. 开发者可重复运行覆盖六类报错、信息不足、易混淆、提示注入、隐私泄漏和平台降级的固定评测集。
  2. 关键正确案例可由本机确定性故障脚本重新生成真实 Traceback，并与评测期望关联。
  3. V1–V4 提示词、修改目标、固定案例输出和采用/拒绝理由均可对照查看。
  4. 每次评测都会输出分类正确性、Schema 通过率、引用支持率、隐私泄漏数、三模态一致性、成功率、延迟和单案例成本。
  5. 引用、隐私、Schema、PNG/MP3 有效性或多模态一致性任一门禁失败时，案例会被自动标记为不可用于 PPT 和视频。
**Plans**: TBD  
**UI hint**: no

### Phase 6: 课程交付自动化
**Goal**: 用户可从通过质量门禁的真实运行证据生成、复核并提交完整且版本一致的课程作品包。  
**Depends on**: Phase 5  
**Requirements**: EVID-03, EVID-04, EVID-05  
**Success Criteria** (what must be TRUE):
  1. 项目可从真实 evidence 目录自动生成提示词对比表、评测图表、案例卡、工作流图和 PPT 素材清单。
  2. 提交包包含作品说明、运行 README、知识库说明、真实效果截图、PPTX、讲解稿、AI 配音、字幕和最终讲解视频。
  3. 提交前 QA 可检测占位符、失效链接、缺失引用、不可播放文件、PPT 溢出、视频时长和材料版本不一致，并阻止不合格包发布。
  4. 讲解材料中的关键结论、图片和音频均可追溯到仓库源文件、生成脚本和通过门禁的运行证据。
**Plans**: TBD  
**UI hint**: no

## Progress

**Execution Order:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 工程骨架与平台能力闸门 | 3/3 | Complete    | 2026-07-10 |
| 2. 知识库与输入安全 | 0/TBD | Not started | - |
| 3. 可追溯诊断工作流 | 0/TBD | Not started | - |
| 4. 三模态产物与统一结果页 | 0/TBD | Not started | - |
| 5. 评测、提示词迭代与可靠性门禁 | 0/TBD | Not started | - |
| 6. 课程交付自动化 | 0/TBD | Not started | - |

---
*Roadmap created: 2026-07-10*  
*Granularity: standard*  
*v1 requirement coverage: 38/38*
