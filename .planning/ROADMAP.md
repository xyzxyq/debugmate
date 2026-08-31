# Roadmap: DebugMate

## Overview

DebugMate V0.1 以“尽快形成完整课程作品”为目标。前三阶段已有工程资产继续保留；第四阶段只收尾本地三模态演示闭环；第五阶段压缩为 3-5 个代表性案例和提示词迭代摘要；第六阶段直接生成 PPT、讲解稿与视频素材。不再以公开部署或生产发布标准扩大验收。

## Phases

- [x] **Phase 1: 工程骨架与平台能力闸门** - 冻结案例标识、运行证据和仓库事实源，并验证 Dify 主链能力。 (completed 2026-07-10)
- [x] **Phase 2: 知识库与输入安全** - 建立可重建的官方知识库和输入/输出双重安全边界。 (completed 2026-07-12)
- [x] **Phase 3: 可追溯诊断工作流** - 从截图与文本稳定生成有引用、可纠错、说明不确定性的结构化诊断。 (completed 2026-07-13)
- [x] **Phase 4: 三模态产物与统一结果页** - 从同一诊断对象生成文字、PNG、MP3，并支持查看、下载、回放和降级。 (completed 2026-07-19)
- [x] **Phase 5: 代表性案例与提示词说明** - 用 3-5 个案例说明效果、提示词优化、局限与改进。 (completed 2026-07-19)
- [x] **Phase 6: 课程提交包** - 从真实运行素材生成 PPT、讲解稿、字幕和最终视频。 (completed 2026-07-19)
- [x] **Phase 7: 真实输入与隐私预览接线** - 让普通 Gradio 页面接受真实文本、代码、环境和截图，并复用本地脱敏、预览与审批合同。 (completed 2026-08-09)
- [~] **Phase 8: Dify 统一实时诊断链** - 17 源 readback、本地零跳过 runner、安全闸门与当前 DSL 已完成；待 Dify 控制台重新发布后完成同次 `run_envelope`、Edge、TTS/ZIP 证据晋升。
- [ ] **Phase 9: 当前代表案例与提示词证据** - 用当前实现重跑 3–5 个代表案例并形成 V1–V4 同案例对照、隐私与一致性证据。
- [ ] **Phase 10: 最终课程提交包刷新** - 最后统一刷新真实截图、PPTX、讲解稿、字幕、视频和全部材料 manifest，并完成最终 QA。

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
**Plans**: 6 plans

- `03-01` — `DiagnosisRecord v1.1` 合同迁移、显式证据图与命令安全。
- `03-02` — OCR/VLM 候选抽取、本地事实规范化与纠错 revision。
- `03-03` — provisional/final 路由、最多三问充分性矩阵与证据绑定。
- `03-04` — 候选诊断适配器、本地裁决与最多一次受控修复。
- `03-05` — HMAC approval 门禁、端到端工作流、CLI 与固定案例矩阵。
- `03-06` — 原子 evidence、隐私复扫、Schema/secret/full-suite 最终门禁。
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
**Plans**: 12 plans（04-11 与 04-12 已按 V0.1 收束）
**UI hint**: yes

### Phase 5: 代表性案例与提示词说明
**Goal**: 用少量可复现案例说明诊断效果、提示词迭代、隐私与多模态一致性，并如实记录局限。
**Depends on**: Phase 4  
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05  
**Success Criteria** (what must be TRUE):
  1. 开发者可重复运行 3-5 个覆盖成功、信息不足或失败、长内容及平台降级的代表性案例。
  2. 关键正确案例可由本机确定性故障脚本重新生成真实 Traceback，并与评测期望关联。
  3. V1–V4 提示词、修改目标、固定案例输出和采用/拒绝理由均可对照查看。
  4. 生成一份简洁结果表，至少记录案例状态、引用、三模态文件和主要局限；不要求生产级统计显著性或成本基准。
  5. 进入 PPT 和视频的案例必须能够真实重放且不含明显敏感信息。
**Plans**: 1 lightweight plan
**UI hint**: no

### Phase 6: 课程提交包
**Goal**: 从真实运行素材生成并检查可提交的 PPT、讲解稿和视频录制素材。
**Depends on**: Phase 5  
**Requirements**: EVID-03, EVID-04, EVID-05  
**Success Criteria** (what must be TRUE):
  1. 项目可从真实 evidence 目录自动生成提示词对比表、评测图表、案例卡、工作流图和 PPT 素材清单。
  2. 提交包包含作品说明、运行 README、知识库说明、真实效果截图、PPTX、讲解稿、AI 配音、字幕和最终讲解视频。
  3. 提交前检查占位符、缺失素材、不可播放文件、明显 PPT 溢出和视频时长；不建设生产发布流水线。
  4. 讲解材料中的关键结论、图片和音频均可追溯到仓库源文件、生成脚本和通过门禁的运行证据。
**Plans**: 1 lightweight plan
**UI hint**: no

### Phase 7: 真实输入与隐私预览接线
**Goal**: 用户可在普通 Gradio 页面提交报错文本、代码、环境或截图，在任何云调用前查看并确认真实脱敏预览。
**Depends on**: Phase 4
**Requirements**: INP-01, INP-02, SAFE-01, UX-01
**Gap Closure**: Closes UI input, screenshot upload, OCR and privacy-preview gaps from the V0.1 milestone audit.
**Success Criteria** (what must be TRUE):
  1. 页面提供报错文本、代码、环境和截图输入；文本与截图均为空时在本机拒绝。
  2. 截图经过既有格式/尺寸验证、生产 OCR 候选与确定性遮挡，不再使用 Noop OCR 作为普通模式入口。
  3. 预览和批准仅使用服务器保存的一次性 token；浏览器不能伪造批准后的输入或路径。
  4. 固定回放仍作为独立、明确标记的演示模式存在，不与真实输入混淆。
**Plans**: pending
**UI hint**: yes

### Phase 8: Dify 统一实时诊断链
**Goal**: 已批准的脱敏输入通过同一次 Dify workflow 生成严格 DiagnosisRecord，并继续派生本地 Markdown、PNG、MP3、Gradio 结果和 ZIP。
**Depends on**: Phase 7
**Requirements**: KNOW-03, KNOW-04, DIAG-02, MULTI-03, UX-01, EVID-01
**Gap Closure**: Closes the DifyBackend/CloudGateway product wiring and unified-run evidence gaps.
**Success Criteria** (what must be TRUE):
  1. 普通 live 模式使用环境变量配置的 Dify backend，缺少配置时明确降级而不是伪装云端成功。
  2. 同一次 run 的上传、视觉抽取、知识检索、结构化诊断、运行指纹和本地产物身份可追溯。
  3. Dify 返回必须经过本地严格 Schema 与证据校验，失败只允许一次受控修复并诚实呈现。
  4. 一个真实脱敏案例可端到端生成 Markdown、PNG、MP3、UI 和 ZIP，且证据 bundle 不泄露秘密。
**Plans**: pending
**UI hint**: yes

### Phase 9: 当前代表案例与提示词证据
**Goal**: 以当前代码和当前 Dify 合同重跑少量代表案例，形成可复算的案例表与 V1–V4 同案例对照。
**Depends on**: Phase 8
**Requirements**: EVAL-01, EVAL-03, EVAL-05, EVID-03
**Gap Closure**: Closes stale representative-case, prompt-comparison and course-source evidence gaps.
**Success Criteria** (what must be TRUE):
  1. 3–5 个案例覆盖 live 成功、信息不足、长内容、隐私和降级/失败状态。
  2. V1–V4 使用同一脱敏案例生成或验证输出，并记录采用、拒绝和限制理由。
  3. 案例表绑定当前 run/evidence、引用、三模态文件、隐私扫描和局限。
  4. 进入最终媒体的案例均能从版本化输入和脚本重建。
**Plans**: pending
**UI hint**: no

### Phase 10: 最终课程提交包刷新
**Goal**: 从 Phase 9 的当前真实证据统一生成并检查最终截图、PPTX、讲解稿、AI 配音、字幕和视频。
**Depends on**: Phase 9
**Requirements**: EVID-03, EVID-04, EVID-05
**Gap Closure**: Closes historical-media freshness, claim consistency, manifest drift and final QA gaps.
**Success Criteria** (what must be TRUE):
  1. 最终截图来自当前 UI，课程文案准确区分 live Dify、local fallback 和固定回放。
  2. PPTX、视频、字幕、讲解稿和 manifests 全部由当前证据生成，哈希相互一致。
  3. 自动 QA 检查占位符、敏感信息、PPT 溢出、音视频可播放性、字幕时序、时长和材料 freshness。
  4. 完成最终 PPT 翻页检查与视频/配音听验；若本机工具可自动检查则先自动完成，只有不可替代的人耳/视觉判断才请求用户。
**Plans**: pending
**UI hint**: no

## Progress

**Execution Order:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9 → Phase 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 工程骨架与平台能力闸门 | 3/3 | Complete    | 2026-07-10 |
| 2. 知识库与输入安全 | 3/3 | Complete | 2026-07-12 |
| 3. 可追溯诊断工作流 | 6/6 | Complete | 2026-07-13 |
| 4. 三模态产物与统一结果页 | 12/12 | Complete | 2026-07-19 |
| 5. 代表性案例与提示词说明 | 1/1 | Complete | 2026-07-19 |
| 6. 课程提交包 | 1/1 | Complete | 2026-07-19 |
| 7. 真实输入与隐私预览接线 | 5/5 | Complete    | 2026-08-09 |
| 8. Dify 统一实时诊断链 | 0/0 | Pending | — |
| 9. 当前代表案例与提示词证据 | 0/0 | Pending | — |
| 10. 最终课程提交包刷新 | 0/0 | Pending | — |

---
*Roadmap created: 2026-07-10*  
*Granularity: standard*  
*V0.1 scope reduced: 2026-07-19; requirement identifiers retained for traceability*
