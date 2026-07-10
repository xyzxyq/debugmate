# Pitfalls Research

**Domain:** 面向 AI 专业学习场景的多模态 RAG 报错诊断智能体（DebugMate）  
**Researched:** 2026-07-10  
**Confidence:** HIGH（安全、RAG、Windows、结构化数据部分）；MEDIUM（扣子/云平台具体导出能力会随版本变化）

## 研究结论

DebugMate 最危险的失败不是“模型答错一次”，而是把不可信的日志、截图和检索文档当作指令，把未经验证的推断包装成有引用的结论，再将同一错误同步扩散到文字、PNG 与 MP3。首版应把安全边界、证据对象和结构化诊断契约放在平台工作流之前完成；否则平台上看似流畅的演示会掩盖不可复现、不可迁移、不可审计的问题。

本文采用以下建议阶段名称，供后续 ROADMAP 直接映射：

1. **Phase 1 — 安全、数据契约与可移植基线**：威胁模型、脱敏、诊断 JSON Schema、平台能力探针与降级设计。
2. **Phase 2 — 多模态输入与证据抽取**：文本/截图接入、OCR/VLM、原图对照、质量门和人工纠错。
3. **Phase 3 — 知识库与 RAG 证据链**：官方资料采集、分块、检索、引用绑定、知识更新机制。
4. **Phase 4 — 诊断编排与多模态派生**：根因候选、命令风险分级、文字/PNG/MP3 生成及一致性校验。
5. **Phase 5 — 平台集成、结果页与性能韧性**：扣子/Dify/Python 适配、超时、缓存、成本账本、下载与降级。
6. **Phase 6 — 独立评测、真实证据与课程交付**：冻结测试集、红队评测、真实录屏、可复现打包。

## Critical Pitfalls

### Pitfall 1：日志、截图或知识文档中的间接提示注入

**What goes wrong:**  
报错日志、README、Issue、网页或截图里出现“忽略之前指令”“输出系统提示词”“执行以下命令”等文本。模型把这些数据当成高优先级指令，改变诊断任务、泄露上下文、伪造引用，甚至诱导危险命令。多模态输入会扩大攻击面：恶意指令可能藏在截图的小字、透明层或文档片段中。

**Why it happens:**  
LLM 无法天然区分“要分析的数据”和“应执行的指令”；RAG 与微调也不能消除提示注入。把 OCR 文本、检索块直接拼入系统提示词，或让模型自由调用开放式工具，会把数据面与控制面混在一起。

**How to avoid:**

- 明确标注 `UNTRUSTED_INPUT`、`UNTRUSTED_RETRIEVAL` 边界；系统提示词只允许从这些块提取事实，不允许服从其命令。
- OCR、日志与检索文本进入模型前做注入特征扫描，但不能把关键词过滤当成唯一防线。
- 首版不给模型 shell、文件写入、网络请求等工具权限；诊断命令只作为字符串输出。
- 用确定性代码校验结构化输出、引用 ID 和命令风险等级；安全控制不依赖“模型答应遵守”。
- 评测集必须含直接注入、文档间接注入、截图隐蔽注入和“正常日志中恰好含 instruction 字样”的误报案例。

**Warning signs:**

- 回答突然讨论与报错无关的任务，或要求用户上传密钥、访问链接。
- 输出引用了不存在的片段、暴露系统提示词或内部节点名。
- 同一恶意语句放在用户消息、截图和知识库时，行为差异巨大。
- 工作流把整段检索结果作为 system/developer 角色消息发送。

**Recovery:**  
立即停用受污染知识条目和相关案例；撤销可疑工具凭据；保留脱敏后的输入、检索命中和输出作为安全回归样本；将受影响流水线降级为“只读诊断、无工具调用”，修复边界标记与输出验证后再恢复。

**Phase to address:** Phase 1 定义信任边界；Phase 2/3 实施输入与检索隔离；Phase 6 红队复验。

---

### Pitfall 2：Token、用户名、绝对路径和环境信息在多条链路泄漏

**What goes wrong:**  
`HF_TOKEN`、API Key、Git URL 凭据、邮箱、Windows 用户名、项目绝对路径或私有仓库名出现在 OCR 文本、LLM 请求、检索索引、调试日志、PNG、MP3、下载包、PPT 或录屏中。只在 UI 上遮罩不够，因为原始值可能已经进入云平台日志或音频旁白。

**Why it happens:**  
脱敏通常只覆盖纯文本正则，却遗漏截图像素、URL 编码、PowerShell 环境变量、异常对象、模型回显、图片元数据和生成后的二次传播。开发期“先记全量日志再说”会把秘密永久写入 Git 历史或平台运行记录。

**How to avoid:**

- 在上传后、任何云端调用前执行统一 `sanitize()`；文本、OCR、代码、环境字段使用相同脱敏规则和占位符映射。
- 默认只存脱敏输入；原图若必须保留，只存本地临时目录并设短期清理策略，课程材料使用虚构身份与路径重放。
- 采用“允许记录字段”而不是“禁止记录字段”日志策略；严禁记录 Authorization、Cookie、完整请求体和环境变量全集。
- 对文字、JSON、PNG 可见文本、MP3 转写稿、字幕、PPT 和视频帧做提交前 secret/PII 扫描。
- 密钥仅从环境变量/平台 Secret 注入，不进入提示词、DSL、Schema、测试夹具或截图。

**Warning signs:**

- 运行日志包含 `sk-`、`hf_`、`Bearer`、`C:\Users\真实用户名`、带凭据的 URL。
- 结果页遮罩了文本，但下载的 JSON、PNG、MP3 或 debug URL 仍含原值。
- 平台导出的 DSL/YAML 中出现 token 或模型供应商密钥字段。
- 演示案例依赖用户真实机器截图，无法安全公开仓库。

**Recovery:**  
先撤销并轮换密钥，而不是只删除文件；从索引、日志、对象存储、平台历史、Git 历史和交付物全部清理；重新生成所有派生模态；增加该泄漏形态的回归测试并记录受影响范围。

**Phase to address:** Phase 1 设计脱敏与存储策略；Phase 2 实现像素/OCR 双层脱敏；Phase 6 全交付物扫描。

---

### Pitfall 3：RAG “有引用”但引用不支持结论

**What goes wrong:**  
回答附了官方链接或 chunk 编号，却发生“引用邻近但不蕴含”“版本不匹配”“只支持部分结论”“引用对象与展示链接错位”。用户看到引用便误以为根因已被证明，实际上检索到的只是同一技术主题。

**Why it happens:**  
只评估 top-k 相关度，不评估回答 groundedness、citation correctness/completeness；模型生成自由文本后再补链接；分块切断前置条件、版本范围和命令适用平台；知识库更新后 chunk ID 改变但旧答案仍指向旧位置。

**How to avoid:**

- 每个可验证事实绑定稳定 `evidence_id`、来源 URL、标题、版本/更新时间、原文片段和内容哈希；模型只能引用本次检索返回的 ID。
- 诊断对象中分开保存 `facts`、`inferences`、`missing_information`；推断不得伪装为来源原文。
- 对每条高风险修复建议做“claim → evidence”蕴含检查，并设置无证据时的拒答/降置信分支。
- 分块保留章节标题、平台、版本与前后条件；知识更新后执行引用失效检测。
- 评测同时测检索命中、groundedness、citation correctness、citation completeness 和最终技术正确性；不能用一个总分代替。

**Warning signs:**

- 多个不同结论都引用同一宽泛首页。
- 引用片段没有出现回答中的关键版本、错误码或前置条件。
- 点击引用只能到文档首页，无法定位支持段落。
- 知识库重建后相同案例引用到不同内容，测试却仍显示通过。

**Recovery:**  
冻结当前索引快照并重放失败案例；将不支持的句子降级为推断或删除；重新分块和建立稳定证据 ID；对所有已发布金标案例跑引用审计，避免只修单个答案。

**Phase to address:** Phase 3 核心完成；Phase 4 强制消费证据对象；Phase 6 独立审计。

---

### Pitfall 4：被扣子或单一云平台锁定，导不出可运行作品

**What goes wrong:**  
工作流只存在于平台 UI；模型节点、知识库、TTS、文件 URL、运行日志或插件无法完整导出。账号额度、登录、地区、模型下架或节点变更时，作品无法演示，也无法在 Dify/Python 路径重建。

**Why it happens:**  
在确认能力边界前就深度搭建平台工作流；把平台变量名、临时文件 URL、专有节点输出直接作为核心领域模型；误以为“有导出按钮”就等于知识文件、Secrets、插件和媒体文件都能迁移。

**How to avoid:**

- 平台无关资产必须先落库：知识源、chunk manifest、提示词、JSON Schema、评测集、渲染模板、TTS 文稿、预期输入输出。
- 定义窄适配器接口：`extract_input`、`retrieve`、`diagnose`、`render_png`、`synthesize_mp3`；平台节点只负责映射字段。
- 在 Phase 1 做 capability spike：真实测试图片上传、结构化输出、引用、PNG/MP3 生成、文件下载、DSL 导出/导入、Secrets 排除和运行日志可追溯。
- 每次发布保存平台版本截图/导出文件，并用第二工作区或本地适配器做恢复演练。
- 预设降级：扣子不可用时，使用 Dify DSL 或 Python Web；TTS 不可用时使用本地可复现 TTS；图片生成受限时用结构化绘图模板生成 PNG。

**Warning signs:**

- 仓库中没有能描述工作流图和变量契约的文件。
- 导出包只有 YAML/DSL，但导入后提示缺失模型、插件、知识库或 Secret。
- 结果文件是短期签名 URL，几小时后失效。
- 只有平台截图能证明功能，无法从仓库重放同一案例。

**Recovery:**  
先导出当前可获得的 DSL、提示词、节点截图与测试记录；把节点逻辑逆向为平台无关接口；优先恢复结构化诊断 JSON 和本地三模态派生，再迁移 UI。不要在原平台上继续堆叠专有节点。

**Phase to address:** Phase 1 能力探针与适配层；Phase 5 导入/导出和降级演练；Phase 6 离线重放验收。

---

### Pitfall 5：诊断 Schema 漂移，文字、PNG、MP3 各说各话

**What goes wrong:**  
模型更改字段名、类型或枚举；文字说根因是 CUDA OOM，PNG 却画成依赖冲突，MP3 使用上一轮缓存或遗漏限制。某一模态失败时，结果页仍把旧文件与新诊断拼在一起。

**Why it happens:**  
三个生成器分别从自然语言重新理解问题；JSON 只“看起来像结构化”但没有版本、强校验和关联 ID；平台节点默默把空字段转字符串；缓存键只用案例名而不含诊断哈希。

**How to avoid:**

- 建立版本化 `diagnosis.schema.json`，必含 `schema_version`、`diagnosis_id`、`input_hash`、`evidence_ids`、根因候选、步骤、风险、置信度和局限；限制额外字段并进行运行时校验。
- 文字、PNG、MP3 只能读取通过校验的同一个 immutable diagnosis 对象，禁止再次调用模型重新判因。
- 派生物写入 `diagnosis_id`/内容哈希元数据；结果页只聚合同 ID 且生成成功的文件。
- 增加 schema migration 和 golden fixture；改字段必须显式升级版本并重跑三种渲染契约测试。
- MP3 通过 TTS 文稿生成，保存文稿并做转写抽查；PNG 做文字抽取/像素尺寸/打开测试。

**Warning signs:**

- 前端出现大量 `fieldA || field_b || ...` 兼容代码。
- 同一案例重复运行时文件名相同但内容或 diagnosis_id 不一致。
- 文字通过测试，PNG/MP3 只检查“文件存在”。
- 修改提示词后没有任何 schema 或渲染器测试失败。

**Recovery:**  
选择一个已验证 Schema 版本作为事实源；编写一次性迁移器处理已保存结果；清除派生缓存并从诊断对象全量重建 PNG/MP3；给导致漂移的样本增加契约回归测试。

**Phase to address:** Phase 1 定义契约；Phase 4 实施派生与一致性校验；Phase 5 结果页按 ID 聚合。

---

### Pitfall 6：OCR/VLM 把一个字符读错，诊断路线整体偏离

**What goes wrong:**  
`0/O`、`1/l/I`、`cuda:0/cuda:O`、版本号、路径分隔符、括号、引号或 Traceback 行号被误读；截图裁剪、缩放、压缩、暗色主题和中文路径进一步降低精度。错误文本仍以高置信度进入检索，导致检索与修复都“合理但错误”。

**Why it happens:**  
把 VLM 描述当作 OCR 真值；不保留原图坐标和候选；只测试清晰截图；为了降低成本过度压缩；没有让用户确认关键字段，也没有用代码/环境字段交叉验证。

**How to avoid:**

- 原图保留本地对照，记录尺寸、缩放和裁剪；低分辨率、过度压缩、文字区域过小直接触发质量提示。
- 输出带 bbox/来源的抽取对象，对错误类型、包名、版本、路径、设备号给出字段级置信度和候选值。
- 用 Traceback 语法、包名词典、版本正则和用户提供的代码/环境做交叉校验，但不得静默“纠正”为另一个有效值。
- 关键字段低置信时先让用户确认，或同时检索有限候选并在结论中保持不确定性。
- 评测集包含暗色/亮色、缩放、模糊、中文路径、长 Traceback、终端换行、遮挡和注入小字。

**Warning signs:**

- OCR 文本无法通过 Traceback/版本/路径基本语法检查。
- 原图和抽取文本没有并排查看入口。
- 模型从模糊截图给出精确版本结论且没有低置信提示。
- 清晰截图准确率高，但真实手机拍屏或缩放截图骤降。

**Recovery:**  
保留原图重新执行不同预处理/OCR 路径；向用户展示差异字段并确认；废弃依赖错误抽取的检索和诊断，而不是只改最终文字；把失败图像加入固定视觉回归集。

**Phase to address:** Phase 2 核心完成；Phase 3 检索前质量门；Phase 6 真实截图回归。

---

### Pitfall 7：生成了危险、不可逆或平台错误的修复命令

**What goes wrong:**  
建议 `rm -rf`、递归删除环境、全局卸载、关闭安全策略、修改注册表、覆盖 PATH、强制降级驱动、从未知源执行脚本，或把 Linux 命令给 Windows 用户。即使系统不自动执行，学生复制粘贴也可能破坏环境或泄露凭据。

**Why it happens:**  
模型追求“立即修好”；知识片段缺少平台和版本前置条件；提示词没有命令分类；结果页用一键复制把说明与高风险命令混在一起；验证命令和修复命令没有区分。

**How to avoid:**

- 命令对象必须包含 `platform`、`shell`、`risk_level`、`requires_admin`、`reversible`、`preconditions`、`expected_effect`、`rollback`。
- 默认先给只读检查和最小作用域修复；禁止无约束 shell、远程脚本管道执行、递归删除、凭据输出和关闭安全控制。
- 高风险命令不显示“一键运行”；必须警示、备份/回滚方案和用户显式确认。首版坚持不自动执行。
- 用 allow/deny 规则做确定性扫描，并为 PowerShell、cmd、bash 分开模板；无法确认平台时只给信息收集命令。
- 评测复制粘贴后的真实行为，不能只让 LLM judge 判断“看起来安全”。

**Warning signs:**

- 命令没有 shell 标签、前置条件或回滚说明。
- 为解决局部包冲突建议删除整个环境或全局缓存。
- Windows 案例出现 `sudo`/`rm`，Linux 案例出现注册表命令。
- “验证命令”本身会写文件、安装包或修改系统状态。

**Recovery:**  
撤下含危险命令的知识/提示词版本；标记并审计所有已生成案例；将命令改为结构化对象和规则扫描；提供环境恢复指引，但不要假装能够恢复已丢失数据；增加命令安全金标。

**Phase to address:** Phase 1 定义安全政策；Phase 4 实施命令对象与扫描；Phase 6 沙箱/人工复核。

---

### Pitfall 8：评测集由同一模型生成、调优、评分，造成评测泄漏

**What goes wrong:**  
同一批合成案例被用于写知识库、优化四版提示词和最终评分；同一模型既生成参考答案又做 judge。分数持续上升，但面对新截图、未见版本或真实学生描述时失败。

**Why it happens:**  
时间有限，复用数据最省事；自动生成案例表面多样但模板高度同质；开发者反复查看隐藏测试答案；只报告平均分，不报告类别、失败样本和置信区间。

**How to avoid:**

- 从一开始划分 `dev`、`regression`、`held_out`、`adversarial`，held-out 在最终评测前冻结且不进入提示词/知识库。
- 生成器、诊断模型和 judge 尽量角色分离；关键指标使用确定性规则和人工抽样，不让单一 LLM judge 决定一切。
- 对合成案例保存生成提示、随机种子/模型版本和来源；加入少量独立构造的真实可复现错误。
- 分类别报告 OCR、路由、检索、引用、诊断、隐私、安全和三模态一致性；保留失败案例而非只展示精选成功样本。
- 四版提示词对比使用固定 dev 集，最终结论必须在未见 held-out 上复验。

**Warning signs:**

- 评测准确率接近满分，但所有案例句式和错误类型高度相似。
- 修改提示词时直接查看并针对最终测试答案调规则。
- judge 的理由复述参考答案，却没有核查实际证据或命令。
- 报告只有总分、没有数据版本、类别分数和失败清单。

**Recovery:**  
作废被污染的“最终分数”；重新冻结由不同流程产生的 held-out；保留旧集做回归而非删除；在报告中诚实标注评测污染与重新测得的结果。

**Phase to address:** Phase 1 先定义数据分割；Phase 3/4 只用 dev 调优；Phase 6 由独立 held-out 验收。

---

### Pitfall 9：用生成截图、回放文件或剪辑掩盖真实运行证据

**What goes wrong:**  
PPT/视频中的“平台运行截图”、指标图或终端画面实际来自图像生成、手工拼接、旧缓存或预先准备的静态结果；演示中点击运行但播放的是上一轮文件。即使最终答案正确，也破坏课程作品可信度。

**Why it happens:**  
云平台不稳定、延迟高，临近提交时倾向于“美化证据”；没有区分产品插图与运行证据；产物缺少 run_id、输入哈希、时间戳和可重放记录。

**How to avoid:**

- 运行证据必须来自真实端到端执行，保留 `run_id`、输入哈希、配置/提示词版本、知识库快照、开始/结束时间、节点状态和输出哈希。
- PPT 可使用生成式装饰图，但必须明确标注；不得把生成图当 UI 截图、评测曲线或运行结果。
- 演示录制采用单次连续流程，展示输入、运行状态、引用和三模态文件；允许准备降级演示，但必须标注“预录真实运行”。
- 产物 manifest 将每个截图/视频片段追溯到源 run；随机抽一个案例从仓库脚本重放。
- 成功与失败运行都保留，避免只有精选成功证据。

**Warning signs:**

- 截图没有浏览器/平台上下文、时间或 run_id，文字过度完美。
- 视频中的结果瞬间出现，且网络/节点日志没有对应请求。
- 文件时间、manifest 与录屏时间不一致。
- PPT 中指标图无法找到生成脚本和原始 JSON。

**Recovery:**  
移除不可追溯证据；重新执行并录制真实流水线；若平台当前不可用，明确展示本地可复现路径与平台故障，不用伪造成功；在报告中区分真实证据、示意图和后期排版。

**Phase to address:** Phase 1 定义 provenance；Phase 5 记录 run manifest；Phase 6 强制重放与证据审计。

---

### Pitfall 10：平台宣称支持导出，但目标格式或运行语义并不受支持

**What goes wrong:**  
扣子/Dify 可以导出部分工作流，却不能导出知识库内容、插件、模型绑定、Secrets、媒体附件、已发布版本或运行历史；导出的 DSL 在另一个工作区导入后节点缺失。平台能生成音频但不能下载 MP3，或只能返回临时 URL；PNG/MP3 MIME、扩展名与真实内容不一致。

**Why it happens:**  
把营销层面的“支持文件/导出”理解为完整、稳定、可离线的工程接口；没有在目标账号、浏览器和提交机器上实测；不检查导出包 manifest 与文件魔数。

**How to avoid:**

- 建立能力矩阵，逐项验证：输入格式/大小、结构化输出、知识库引用、工作流导出、导入覆盖、Secrets 行为、文件持久性、PNG/MP3 下载、API 调用、日志与额度。
- 能力探针必须产出真实小文件并在全新工作区导入/运行，不接受“按钮存在”作为通过。
- 媒体下载后检查 HTTP 状态、MIME、扩展名、文件魔数、可解码性、时长/尺寸和 diagnosis_id。
- 所有平台专有资源在仓库维护 manifest 与人工恢复步骤；对不可导出的资源准备脚本化重建或本地替代。
- 在平台/模型版本变更后重新跑 smoke test。

**Warning signs:**

- 导入日志有 warning，但页面仍显示“导入成功”。
- `.mp3` 实际是 JSON 错误页，`.png` 实际是 HTML 登录页。
- 下载链接含短期签名参数，换浏览器或隔天即失效。
- DSL 中引用内部 resource_id，但仓库没有资源映射表。

**Recovery:**  
保存原平台配置快照；列出缺失资源而非反复导入；用 manifest 重建知识库/插件/模型绑定；把媒体转为本地持久文件并重新校验；若关键能力不可补齐，按预设降级到 Dify 或 Python Web。

**Phase to address:** Phase 1 能力矩阵；Phase 5 集成验收与降级；Phase 6 提交机重放。

---

### Pitfall 11：串联 VLM、RAG、LLM、绘图和 TTS 后，成本与延迟失控

**What goes wrong:**  
一次诊断触发多次大模型、重复 OCR/检索、长上下文、图片生成和 TTS；最终等待几十秒到数分钟，免费额度迅速耗尽。某节点重试导致整条链重复付费，课程现场超时后没有可解释的部分结果。

**Why it happens:**  
只测单节点；模型与上下文默认选最大；生成 PNG 也用昂贵图像模型而不是模板渲染；没有请求预算、超时、缓存、并行和熔断；平台隐藏了 token/费用细节。

**How to avoid:**

- 为每次 run 建立预算：最大输入图大小、检索块数、上下文 token、模型调用次数、TTS 字数、重试次数、总成本和 P95 延迟。
- OCR/脱敏/路由尽量确定性或小模型；诊断只做一次主推理；PNG 用结构化模板/图表渲染；TTS 使用已生成的短复盘稿。
- 诊断对象生成后，PNG 与 MP3 可并行；每个节点独立超时和重试，重试不能重跑已成功的昂贵节点。
- 缓存键包含输入哈希、模型/提示词/知识库/Schema 版本；缓存命中仍校验隐私和 diagnosis_id。
- 结果页渐进显示文字/节点状态；TTS 或 PNG 失败时明确降级，不把整个诊断判死。
- 记录每节点 token、费用、耗时、重试和错误；现场演示前检查额度并保留真实预录降级。

**Warning signs:**

- 同一输入重复运行费用相同，说明缓存未命中。
- 平均延迟尚可但 P95/P99 极高，或免费额度下频繁 429。
- PNG 生成比诊断本身更慢、更贵。
- 一个 TTS 错误导致 OCR、检索和诊断全部重跑。

**Recovery:**  
从 trace 找出最贵/最慢节点；暂时切换模板 PNG、本地 TTS、小模型或缩短上下文；启用节点级 checkpoint；保留核心文字诊断与引用，明确标记未生成模态并允许稍后重试。

**Phase to address:** Phase 1 预算目标；Phase 4 节点设计；Phase 5 性能、缓存和降级压测。

---

### Pitfall 12：Windows 路径、PowerShell 语义和字符编码破坏可复现性

**What goes wrong:**  
中文目录、空格、反斜杠、通配符、驱动器号、长路径、CRLF、BOM、系统代码页使脚本、JSONL、字幕、FFmpeg 或知识采集失败。开发机可运行，换到 Windows PowerShell 5.1、PowerShell 7、cmd 或另一个用户名后出现乱码/找不到文件。

**Why it happens:**  
把路径当普通字符串拼接；混用 shell；依赖当前工作目录；省略编码；假设所有 Windows 应用都支持长路径；测试数据写死 `C:\Users\20795`；JSON 中反斜杠转义错误。

**How to avoid:**

- Python 使用 `pathlib.Path`，PowerShell 使用 `-LiteralPath`、`Join-Path` 和明确绝对路径；不要把用户输入拼成 shell 命令。
- 仓库文本统一 UTF-8，并在读写/API/子进程边界显式编码；针对 Windows PowerShell 5.1 与 PowerShell 7 的 BOM 差异做测试。
- 测试矩阵覆盖中文、空格、`[]`、超长目录、不同驱动器、CRLF、UTF-8 BOM/无 BOM；fixtures 使用虚构用户名。
- 临时工具链若不支持非 ASCII，使用短 ASCII 工作目录，但最终产物回写时保存路径映射和 provenance。
- 文件名使用稳定 slug + diagnosis_id；不要让错误消息直接变成文件名。
- 对 FFmpeg、浏览器下载和平台上传使用参数数组/原生 API，而不是字符串拼接命令。

**Warning signs:**

- `Get-Content` 显示正常但 Python/FFmpeg/平台中乱码，或反之。
- 代码里大量 `path.split('\\')`、手工引号和硬编码用户目录。
- 只有仓库根目录运行成功，从其他目录调用就失败。
- 同一测试在 PowerShell 7 通过、Windows PowerShell 5.1 失败。

**Recovery:**  
先保存原始字节和失败路径；定位是文件编码、控制台显示还是子进程参数问题；将读写统一为显式编码和 Path API；用 ASCII 临时路径隔离脆弱工具；将失败路径加入跨 shell 回归，而不是只改本机配置。

**Phase to address:** Phase 1 制定路径/编码约定；Phase 2/4/5 持续跨 shell 测试；Phase 6 在干净 Windows 路径重放。

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| 把自然语言回答直接喂给 PNG/TTS | 原型很快 | 三模态矛盾、无法契约测试 | 仅一次性纸面原型，不能进入 MVP |
| 只在提示词里要求脱敏和安全 | 无需编写规则 | 可被注入绕过，无法审计 | Never |
| 把平台 UI 当唯一源文件 | 少写代码/文档 | 锁定、丢失、不可重放 | Never |
| 全量记录请求与响应 | 调试方便 | 密钥/路径/隐私泄漏 | 仅本地虚构数据且短期清理 |
| 所有知识条目固定长度切块 | 实现简单 | 条件与结论分离、引用错位 | 仅用于建立基准，须与结构化分块对比 |
| 只用 LLM judge | 自动评分快 | 偏见、同源泄漏、不可解释 | 可作辅助指标，不能作为唯一验收 |
| 只检查 PNG/MP3 文件存在 | 测试简单 | HTML/JSON 冒充媒体、内容过期 | Never |
| 为演示预先缓存结果但不标注 | 现场稳定 | 证据真实性受损 | 仅真实运行预录且明确标注 |
| 将平台临时 URL 直接写入交付物 | 无需下载存储 | 链接过期、需登录 | 只可作运行日志，不作最终成果 |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| 扣子 Coze | 未验证导出、知识库、TTS 与文件持久化就深度实现 | Phase 1 做真实能力探针；仓库保存平台无关资产和降级适配器 |
| Dify | 认为 DSL 包含 Secrets、知识文件、插件与所有已发布状态 | 在空工作区导入并执行 smoke test；资源单独 manifest；Secrets 手动重绑 |
| VLM/OCR | 只保存一段自由文本 | 保存字段、bbox、置信度、原图引用与候选；低置信人工确认 |
| 向量库/知识库 | 用易变行号或数组下标作 citation ID | 使用来源 URL + 版本 + 片段哈希的稳定 evidence_id |
| TTS | 直接用完整报告，忽略长度与读法 | 从诊断对象生成短复盘稿；保存稿件、音色/模型版本并转写抽查 |
| PNG 渲染 | 用图像模型生成含大量技术文字的流程图 | 优先确定性模板/SVG/Canvas 后导出 PNG；校验文字与 diagnosis_id |
| FFmpeg | 拼接命令字符串，中文路径/引号失败 | 使用参数数组、绝对路径、显式编码并检查退出码/ffprobe |
| 云模型 API | 只处理 200/失败，不处理 429、超时和部分成功 | 节点级重试、幂等键、预算、熔断、部分结果与 request/run ID |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| 每个模态重新推理根因 | 三个答案不一致，成本约 3 倍 | 一次生成诊断对象，确定性派生 | 从第 1 个真实案例就可能出错 |
| 上传原始超大截图 | OCR/VLM 慢、超时、费用高 | 保留原图，生成合适分辨率的分析副本；不做破坏性压缩 | 手机长截图、多屏 Traceback |
| 检索 top-k 过大 | 上下文长、噪声高、引用混乱 | 类别过滤 + rerank + token 预算 | 知识库扩到数百片段后明显 |
| 串行生成 PNG 与 MP3 | 文字完成后仍长时间等待 | 诊断对象通过校验后并行派生 | 任何云 TTS/图片节点出现抖动时 |
| 整条工作流重试 | 重复付费、产生多个不一致 run | 节点 checkpoint、幂等键、只重试失败节点 | 第一次 429/超时即暴露 |
| 缓存键不含版本 | 修改提示词后仍展示旧结果 | 输入、模型、提示词、KB、Schema 版本共同哈希 | 第一次提示词迭代后 |
| TTS 朗读完整报告 | 音频冗长、费用/延迟高 | 60–120 秒复盘摘要并保留限制 | 报告超过约 500–800 中文字 |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| 把日志/文档/OCR 当指令 | 间接提示注入、数据泄漏、错误命令 | 不可信数据隔离、外部规则校验、无开放式工具 |
| 密钥写入系统提示词或 DSL | 提示词泄漏后直接失陷 | Secret 管理、最小权限、轮换、导出扫描 |
| 只遮罩 UI 文本 | JSON、图片、音频、日志仍泄密 | 入站统一脱敏 + 全派生物扫描 |
| 允许模型自由生成/执行 shell | 任意命令、环境破坏 | 首版只输出；结构化命令、allowlist、人工确认 |
| 信任扩展名 | 恶意/错误内容冒充 PNG/MP3 | MIME、魔数、解码、大小/时长检查 |
| 把系统提示词当安全控制 | 可被提取或绕过 | 授权、过滤、Schema 验证在模型外实施 |
| 使用真实学生环境做公开评测 | 路径、账号、仓库泄漏 | 虚构可复现 fixture；真实样本仅脱敏后本地保留 |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| 置信度只显示一个百分比 | 用户误以为结论已被证明 | 分开显示抽取、检索、根因置信度及缺失信息 |
| 引用只给文档首页 | 无法核实具体结论 | 展示片段、章节、版本、更新时间和可点击原链接 |
| 命令无平台/风险标签 | 用户复制错误或危险命令 | Windows/PowerShell 等标签、风险、前置条件、回滚 |
| OCR 错误不可编辑 | 一个字符错误导致整链错误 | 原图与抽取并排、关键字段可确认/修正后重跑 |
| 三模态失败全显示“系统错误” | 用户失去已完成诊断 | 节点状态、部分结果、单模态重试和降级说明 |
| 音频只是逐字朗读长报告 | 多模态形式化、低学习价值 | 结构化 60–120 秒复盘：根因、检查、修复、验证、限制 |
| PNG 只做装饰 | 无法体现同一诊断派生 | 图中必须对应根因候选、证据、决策节点与验证闭环 |
| 只展示成功样例 | 教师难判断边界与可信度 | 展示信息不足、安全拦截和失败降级案例 |

## "Looks Done But Isn't" Checklist

- [ ] **多模态闭环：** 不是“有三个文件”就算完成；随机抽一个 run，验证文字、PNG、MP3 的 `diagnosis_id`、根因、步骤和限制一致。
- [ ] **图片输入：** 不是能上传截图就算完成；用模糊、暗色、中文路径、长 Traceback 和注入小字验证抽取质量门与用户确认。
- [ ] **隐私：** 不是结果页打码就算完成；扫描原始日志、JSON、PNG 可见文字/元数据、MP3 转写、字幕、PPT、视频和 Git 历史。
- [ ] **RAG 引用：** 不是答案带链接就算完成；逐条验证 claim 被具体片段支持，版本/平台一致，并检查引用完整性。
- [ ] **知识库：** 不是上传若干 PDF 就算完成；能列出来源、版本、更新时间、分块 manifest、内容哈希和失效更新流程。
- [ ] **结构化输出：** 不是模型输出 JSON 就算完成；用正式 Schema 验证必填项、枚举、额外字段、版本和迁移。
- [ ] **命令安全：** 不是“不自动执行”就算完成；所有命令仍有平台、风险、权限、前置条件、预期结果和回滚，并经过规则扫描。
- [ ] **平台导出：** 不是有 DSL 文件就算完成；在全新工作区导入、重新绑定非导出资源并跑通一个端到端案例。
- [ ] **媒体文件：** 不是扩展名为 `.png`/`.mp3` 就算完成；检查魔数、MIME、可解码性、尺寸/时长、内容与 diagnosis_id。
- [ ] **下载：** 不是当前浏览器能打开就算完成；换会话、换机器或隔天验证，最终交付使用仓库内持久文件而非临时 URL。
- [ ] **评测：** 不是总分上涨就算完成；确认 held-out 未进入提示词、知识库和规则调优，报告分类分数与失败样本。
- [ ] **提示词优化：** 不是保存 V1–V4 文本就算完成；同一 dev 集可重跑、记录变更假设、指标差异和回归。
- [ ] **真实性：** 不是截图看起来像运行就算完成；每张证据可追溯到 run manifest、配置版本、输入/输出哈希和生成脚本。
- [ ] **性能：** 不是单次成功就算完成；记录冷/热启动、P50/P95、token、费用、429、超时及部分失败降级。
- [ ] **Windows 可复现：** 不是开发机根目录可运行就算完成；在含中文/空格的干净路径、不同用户名和目标 PowerShell 版本重放。
- [ ] **现场演示：** 不是提前缓存就算完成；区分实时运行与“预录的真实运行”，并准备平台离线时的本地降级证据。
- [ ] **课程可提交性：** 不是网页能用就算完成；PPT、视频、字幕、讲解稿、原始评测、生成脚本和来源清单均可追溯。

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| 间接提示注入 | HIGH | 隔离污染源 → 撤销凭据/工具 → 降级只读 → 修复边界与验证 → 红队重放 |
| Token/路径泄漏 | HIGH | 立即轮换密钥 → 清理平台/索引/日志/Git/交付物 → 重生成派生模态 → 增加回归 |
| 引用不支持结论 | MEDIUM | 冻结索引 → claim-evidence 审计 → 重新分块/绑定 → 全金标重评 |
| 平台锁定/不可导出 | HIGH | 保存可见配置 → 逆向平台无关契约 → 本地恢复诊断对象 → 重建适配器 |
| Schema 漂移 | MEDIUM | 固定最后可信版本 → 迁移历史数据 → 清缓存 → 全量重建三模态 |
| OCR/VLM 误读 | LOW–MEDIUM | 原图重抽取 → 候选对比/用户确认 → 废弃错误诊断 → 加入视觉回归 |
| 危险命令 | HIGH | 撤下版本 → 审计全部输出 → 结构化风险字段与规则扫描 → 更新金标 |
| 评测泄漏 | MEDIUM | 作废分数 → 新建冻结 held-out → 独立 judge/人工抽查 → 如实披露 |
| 伪造/不可追溯证据 | HIGH | 移除证据 → 真实重跑与录制 → 建 manifest → 明确标注示意图/预录 |
| 成本/延迟失控 | LOW–MEDIUM | trace 定位 → 小模型/模板/短上下文 → 节点 checkpoint → 部分结果降级 |
| Windows 路径/编码 | MEDIUM | 保存原始字节 → 分离显示/编码/参数问题 → Path API + 显式编码 → 跨 shell 回归 |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 间接提示注入 | Phase 1、2、3 | 文本/文档/截图三类注入均不能改变任务或泄露上下文；无工具调用 |
| Token/路径泄漏 | Phase 1、2、6 | 注入 canary secret 后，全日志和所有派生/交付物扫描为零命中 |
| RAG 引用错配 | Phase 3、6 | 固定金标逐 claim 校验 citation correctness/completeness 与版本一致性 |
| 平台锁定 | Phase 1、5 | 空工作区或 Python fallback 可恢复同一案例并生成三种产物 |
| Schema 漂移 | Phase 1、4 | 所有 fixture 通过 Schema；三模态同 diagnosis_id/哈希且语义一致 |
| OCR/VLM 误读 | Phase 2、6 | 真实截图集字段准确率、低置信召回和人工确认流程达到门槛 |
| 危险修复命令 | Phase 1、4、6 | denylist/allowlist、平台标签、回滚字段和人工安全金标全部通过 |
| 评测泄漏 | Phase 1、6 | held-out 哈希/访问记录证明未用于开发；独立评分可重现 |
| 伪造证据 | Phase 5、6 | 随机证据可追溯到 run manifest、输入/输出哈希和真实重放 |
| 不完整导出 | Phase 1、5、6 | DSL/配置在全新环境导入，缺失资源清单为零或有验证过的重建步骤 |
| 成本与延迟 | Phase 4、5 | 达成每 run 预算、P95、最大重试和部分失败降级指标 |
| Windows 路径/编码 | Phase 1–6 | 中文/空格/长路径、PS 5.1/7、UTF-8 BOM/无 BOM 测试矩阵通过 |

## Sources

### 安全与隐私

- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — RAG 不能消除提示注入；建议隔离外部内容、验证输出、最小权限与人工批准。
- [OWASP LLM02:2025 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/) — 输入清理、访问控制、数据源限制和脱敏要求。
- [OWASP LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) — 避免开放式工具、最小功能/权限、高风险动作需人工批准。
- [OWASP LLM07:2025 System Prompt Leakage](https://genai.owasp.org/llmrisk/llm072025-system-prompt-leakage/) — 系统提示词不应保存 Secret，也不能充当确定性安全控制。
- [NIST: Strengthening AI Agent Hijacking Evaluations](https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations) — 间接提示注入/agent hijacking 的现实风险与评测必要性。

### RAG、Schema 与评测

- [Microsoft Foundry: RAG Evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/rag-evaluators) — 检索质量、groundedness、相关性和完整性应分别评估。
- [Azure Architecture Center: RAG LLM Evaluation Phase](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-llm-evaluation-phase) — groundedness 不等于 correctness，应组合指标和外部可信来源。
- [JSON Schema Getting Started](https://json-schema.org/learn/getting-started-step-by-step) 与 [Additional Properties](https://tour.json-schema.org/content/03-Objects/02-Additional-Properties) — 用类型、必填项与额外字段约束结构化诊断契约。
- [Google Responsible Generative AI: Evaluate model and system for safety](https://ai.google.dev/responsible/docs/evaluation) — 评测数据需要覆盖、差异性、对抗样本和 held-out；测试泄漏会削弱有效性。

### 多模态、平台与运行环境

- [Google Cloud Vision: Supported image formats and dimensions](https://cloud.google.com/vision/docs/supported-files) — OCR 对分辨率、压缩、大小和延迟存在实际权衡。
- [Dify: Introducing Workflow / DSL portability](https://dify.ai/blog/dify-ai-workflow) 与 [Dify 30-Minute Quick Start](https://docs.dify.ai/en/guides/application-orchestrate/creating-an-application) — Dify 支持 DSL 与工作流测试，但发布后仍需端到端复验；平台外资源仍需自行清单化。
- [OpenAI API data controls](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint) — 云模型请求可能进入滥用监控日志或应用状态，必须在调用前脱敏并理解保留策略。
- [OpenAI API backward compatibility / request and rate-limit IDs](https://platform.openai.com/docs/api-reference/backward-compatibility) — 生产诊断应记录 request ID 和限流信息以便追踪超时/429。
- [Microsoft: Maximum Path Length Limitation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation) — Windows 长路径支持需要应用 opt-in，不能假设全局有效。
- [PowerShell: about_Character_Encoding](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_character_encoding) 与 [about_Path_Syntax](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_path_syntax) — Windows PowerShell/PowerShell 的编码差异及 `LiteralPath`/Win32 路径注意事项。
- [W3C PNG Specification, Third Edition](https://www.w3.org/TR/png-3/) — PNG 的正式媒体类型、魔数/完整性与文本块安全注意事项。

---
*Pitfalls research for: DebugMate multimodal RAG debugging and learning agent*  
*Researched: 2026-07-10*
