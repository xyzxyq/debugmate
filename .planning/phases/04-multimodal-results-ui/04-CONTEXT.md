# Phase 4: 三模态产物与统一结果页 - Context

**Gathered:** 2026-07-13  
**Status:** Ready for planning

<domain>
## Phase Boundary

本阶段只消费已经通过 Phase 3 严格校验、且来源 evidence bundle 可验证的 `DiagnosisRunOutcome`；从其中同一份 `DiagnosisRecord 1.1.0` 派生中文 Markdown 报告、确定性 PNG 诊断卡、30–60 秒中文 MP3，并在 Gradio 6 单页中展示脱敏输入、抽取字段、检索依据、三模态结果、运行/回放/失败/降级状态和下载入口。本阶段允许把 Phase 3 已有纠错/重跑 API 接到界面，但不改变诊断推理合同。

Phase 5 的评测集、提示词 V1–V4、质量指标和课程准入门禁，以及 Phase 6 的 PPT、讲解稿、字幕和视频包装均不属于本阶段。

</domain>

<decisions>
## Implementation Decisions

### 单一事实源与结果合同
- **D4-01:** 正常三模态生成只接受 `status=completed` 且通过 `validate_diagnosis_outcome()` 的 `DiagnosisRunOutcome`，并在读取时再次验证其 Phase 3 source bundle；不接受裸字典、自由文本或未经验证的 `DiagnosisRecord` 文件。
- **D4-02:** 新增严格 `ResultManifest`/`ArtifactIdentity` 合同。三个产物共同记录 `case_id`、源 `run_id`、`diagnosis_sha256`、`schema_version=1.1.0`、统一 `generation_version` 和各自产物哈希；任何一项缺失或不一致都阻止结果包发布。
- **D4-03:** `diagnosis_sha256` 只由 `DiagnosisRecord.model_dump(mode="json")` 的 canonical JSON 计算。报告、PNG 与复盘稿不得反向修改诊断事实；展示文案只能是确定性标签、排序、裁剪和格式化。
- **D4-04:** Phase 4 结果使用独立的 `results/<case_id>/<result_id>/` 原子目录，不向 Phase 3 已封存的 `evidence/<case_id>/<run_id>/` 追加文件。`result_id` 由源身份、生成版本、后端选择和最终产物哈希派生；同一路径禁止覆盖。

### 中文报告
- **D4-05:** 报告使用纯 Python 确定性模板，固定为：案例/版本摘要、已观察事实、根因候选与证据、检查步骤、修复步骤、验证步骤、缺失信息、置信度与局限、引用清单。英文 Traceback、错误名、包名、脱敏路径标记和命令保持原样，不做机器翻译。
- **D4-06:** 根因候选显式标注“有依据”或“推断”，事实和证据以稳定 ID 交叉引用；命令以代码块展示，并同时显示平台、影响、预期结果和回退说明。报告不增加诊断对象中不存在的修复建议。

### 确定性 PNG
- **D4-07:** PNG 使用 Pillow 本地绘制，不使用生成式图片、Mermaid CLI、浏览器截图或 Graphviz。画布固定宽度 1600 px，高度由统一换行和布局算法计算；内容顺序固定为“现象 → 根因候选 → 检查 → 修复 → 验证”，并显示 case ID 后 8 位、置信度、证据编号和生成版本。
- **D4-08:** 中文字体按项目内已批准字体资产优先、Windows 字体白名单降级；实际字体文件 SHA-256 写入 manifest 并参与 renderer 版本。PNG 保存后删除 ancillary metadata，再重新打开验证格式、尺寸、单帧和无 metadata。
- **D4-09:** 内容超出单张安全高度时不静默截断；渲染器返回明确的 `png_layout_failed`，界面保留文字/音频可用结果并显示可重试范围。首版不生成多页 PDF。

### 复盘稿与 MP3 降级链
- **D4-10:** 复盘稿由同一诊断对象确定性整理为 30–60 秒中文口播，固定包含现象、首要根因、一个检查动作、一个修复动作、一个验证动作和局限；英文错误名与命令仅保留必要短句。`recap_text` 是主要素材，但仍由本地模板控制长度和结构。
- **D4-11:** TTS 按 `Dify TTS → edge-tts → Windows SAPI WAV + FFmpeg MP3` 顺序尝试。每次尝试记录 backend、错误码、开始/结束状态和降级原因；不记录密钥、上游原始响应或敏感文本。
- **D4-12:** 所有候选音频先验证 MP3 文件头，再用 `ffprobe` 验证可解码、单音轨和 30–60 秒时长。超出时长仅允许一次基于确定性语速档位的重试；仍不合规则该后端失败并进入下一后端。最终后端和降级原因必须显示在页面与 manifest。
- **D4-13:** 三个 TTS 后端均失败时不得伪造或提交空 MP3；保留报告、PNG 和复盘稿，结果状态为 `partial`，清楚显示 `tts_failed` 与重试方式。

### 一致性、隐私与下载包
- **D4-14:** 发布前统一执行：源 bundle 校验、DiagnosisRecord 严格校验、文本/讲稿输出隐私复扫、PNG 清洗、MP3 有效性检查、共享身份字段比对、逐文件 SHA-256 和 manifest 自校验。失败只可发布显式失败记录，不可发布“可交付”结果包。
- **D4-15:** 下载文件为确定性 ZIP，成员按 POSIX 路径排序并使用固定 ZIP 时间戳；至少包含 `diagnosis.json`、`report.md`、`card.png`、`recap.txt`、`recap.mp3`、`citations.json`、`source-manifest.json`、`result-manifest.json` 和 `checksums.sha256`。部分结果 ZIP 只能在文件名和 manifest 中标识 `partial`，不能伪装完整。
- **D4-16:** ZIP 中只复制经过 allowlist 与输出隐私扫描的源摘要，不打包原始未脱敏截图、原始模型响应、API 日志或密钥。下载前再次从磁盘验证 result manifest 与全部哈希。

### Gradio 6 单页体验
- **D4-17:** 使用紧凑的 Gradio `Blocks` 工作台，不做营销首页。顶部常驻案例 ID、模式徽标（实时/离线回放）、总体状态、后端与降级提示；主体分为“输入与抽取”“诊断与证据”“三模态结果”三个可扫描区域，下载与重试动作常驻结果区。
- **D4-18:** 页面展示的输入只来自脱敏 evidence；抽取字段以六个显式字段呈现，并可调用 Phase 3 correction/rerun 边界。未确认修改不得重新诊断；重新诊断产生新 run/result，不覆盖旧证据。
- **D4-19:** 报告、PNG、Audio、引用表和文件下载使用 Gradio 6 原生组件；服务器回调只传递受控路径或严格模型，不把任意用户路径交给 `File`/`DownloadButton`。
- **D4-20:** 固定案例回放从仓库内 allowlist fixture/evidence 索引加载，先验证 bundle 后展示；页面顶部和下载 manifest 始终标注 `replay=true`、fixture 名称和源 run ID，禁用“实时云端成功”措辞。
- **D4-21:** UI 使用统一 `ResultViewState`：`idle / running / completed / partial / failed / replay`。失败视图必须显示失败节点、已完成/继承阶段、可重试范围、已成功的降级产物和安全错误码；异常堆栈只写本地开发日志且经过脱敏，不回显页面。
- **D4-22:** 长任务通过 Gradio queue 顺序发出阶段状态；同一 case 的重复点击用幂等键和按钮禁用防重入。刷新后可从已验证 manifest 恢复，不依赖浏览器内存。

### the agent's Discretion
- 中文视觉主题的具体中性色、间距和图标，只要保持工具型界面、桌面 1366×768 可用且不出现装饰性 hero。
- Pillow 卡片的色板和圆角细节、报告标题措辞、引用表列宽。
- 内部模块文件名与测试夹具命名，只要领域渲染、TTS 适配器、结果发布和 UI 层保持单向依赖。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 项目边界与验收
- `.planning/PROJECT.md` — 核心价值、多模态真实性、低人工投入、隐私、成本与 Windows 约束。
- `.planning/REQUIREMENTS.md` — 本阶段唯一需求 `MULTI-01`～`MULTI-05`、`UX-01`～`UX-04`。
- `.planning/ROADMAP.md` §Phase 4 — 阶段目标和五项成功标准。
- `.planning/STATE.md` — Phase 3 完成状态与仍需现场验证的 Dify/TTS 外部门禁。
- `.planning/phases/03-traceable-diagnosis-workflow/03-VERIFICATION.md` — 当前可消费的严格 outcome、证据与回放边界。
- `.planning/phases/03-traceable-diagnosis-workflow/03-REVIEW.md` — Phase 3 最终无未解决代码质量问题及回归边界。
- `.planning/phases/03-traceable-diagnosis-workflow/03-SECURITY.md` — 不可信输入、不可变 evidence 与输出安全边界。

### 技术、架构与正式设计
- `docs/superpowers/specs/2026-07-13-phase4-multimodal-results-ui-design.md` — 本阶段已批准的组件、数据流、错误处理、测试和 UI 行为设计。
- `.planning/research/STACK.md` — Gradio 6.20、Pillow 12.3、Dify TTS、edge-tts、SAPI/FFmpeg 以及 Windows 兼容决策。
- `.planning/research/ARCHITECTURE.md` — DiagnosisRecord 单一事实源、产物生成与 evidence 分层。
- `.planning/research/PITFALLS.md` — 三模态漂移、音频伪证据、平台依赖、隐私和演示真实性风险。

### 当前代码合同
- `src/debugmate/contracts.py` — `DiagnosisRecord 1.1.0`、事实/证据/根因/命令的权威合同。
- `src/debugmate/diagnosis/workflow.py` — `DiagnosisRunOutcome`、状态机、纠错重跑和公共校验入口。
- `src/debugmate/evidence.py` — 原子目录、manifest、哈希校验、PNG 清洗和当前音频 fail-closed 边界。
- `src/debugmate/privacy/output_scan.py` — 所有可展示/导出文本的隐私复扫边界。
- `src/debugmate/gateway.py` — 真实诊断与纠错重跑的现有调用边界。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DiagnosisRecord` 已包含观察事实、证据锚点、显式 support links、根因候选、检查/修复/验证命令、置信度、局限和 `recap_text`，足以确定性派生三种模态，无需再次调用 LLM。
- `DiagnosisRunOutcome` 已记录 case/run/revision、完成与继承阶段、后端、知识 build、schema/prompt/workflow 版本，可直接形成 `ResultViewState` 和失败/回放元数据。
- `EvidenceBundle` 已有临时目录、原子 finalize、artifact SHA-256、路径 confinement、PNG 清洗、文本输出安全扫描和 bundle verifier；Phase 4 应扩展或复用这些原语，而不是另写宽松文件 API。
- `gateway.py` 和 `DiagnosisWorkflow.rerun()` 已提供严格重跑边界，UI 只需适配，不应复制纠错逻辑。

### Established Patterns
- 公共边界必须通过 Pydantic strict round-trip 重验；`model_copy`、裸 dict 和多余字段不能绕过合同。
- 默认测试完全离线，cloud、OCR 和真实 TTS 使用 marker/显式 smoke test 隔离。
- 任何二进制证据都先写临时位置、清洗/探测/哈希后才能原子发布；失败不得留下看似成功的目录。
- 页面和下载包只展示脱敏摘要；原始 provider body、堆栈和本机绝对路径不得进入证据。

### Integration Points
- 在现有 `publish_diagnosis_evidence()` 之后新增只读 `ResultComposer`，验证 source bundle 后生成独立 result bundle。
- 将当前 `AudioEvidenceNotReady` fail-closed 分支替换为 Phase 4 严格 MP3 契约，但保留二进制扫描和 manifest 一致性检查。
- 新增 TTS 窄端口及 Dify/edge/SAPI 三个适配器；领域层只认识 `AudioAttempt`/`AudioResult`，不依赖 SDK 响应形状。
- Gradio 回调调用应用服务并读取 `ResultViewState`；组件事件不直接操作 adapter、evidence 私有字段或 shell。

</code_context>

<specifics>
## Specific Ideas

- 默认演示使用已验证的 `ModuleNotFoundError` 固定案例：英文错误原文、Windows PowerShell 检查命令、官方 Python/pip 引用、PNG 排障路径和中文语音可在同屏清楚展示。
- 页面第一屏直接进入诊断工作台；状态、证据与三模态结果比品牌装饰更重要。
- “回放”“降级”“部分成功”使用文字徽标与图标双重编码，不只依赖颜色，方便课程录屏和无障碍阅读。

</specifics>

<deferred>
## Deferred Ideas

- 评测集、真实故障脚本、三模态指标、V1～V4 提示词比较和课程准入门禁 — Phase 5。
- PPTX、讲解稿、配音、字幕、最终视频、素材清单和提交前 QA — Phase 6。
- 多用户账号、移动原生界面、历史搜索、个人复习卡和知识图谱 — v2 或明确后续阶段。
- 自动执行任何检查、修复或验证命令 — 明确不在 v1 范围内。

</deferred>

---

*Phase: 04-multimodal-results-ui*  
*Context gathered: 2026-07-13*
