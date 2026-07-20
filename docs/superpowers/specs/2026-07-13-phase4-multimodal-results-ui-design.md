# DebugMate Phase 4：三模态产物与统一结果页设计

**日期：** 2026-07-13  
**状态：** 已批准，可进入实现计划  
**需求范围：** `MULTI-01`～`MULTI-05`、`UX-01`～`UX-04`

## 1. 目标与验收边界

Phase 4 将一个已经严格校验、且来源证据可验证的诊断运行转换为可复核的三模态结果：结构化中文 Markdown 报告、确定性 PNG 诊断卡、30–60 秒中文 MP3。三者必须绑定同一 `case_id`、源 `run_id`、诊断摘要哈希、Schema 版本和生成版本，并在一个 Gradio 6 工作台中展示、回放和下载。

本阶段不重新推理根因，不让 LLM 润色事实，不执行报告中的命令，不构建 Phase 5 评测门禁，也不生成 Phase 6 的 PPT、字幕或视频。Phase 4 可以把现有纠错/重跑 API 接到页面，但不会改变 Phase 3 的诊断合同。

验收成立需同时满足：

1. 三模态均从同一 `DiagnosisRecord 1.1.0` 派生，英文错误原文和命令保持不变。
2. PNG 内容可读、无 metadata、布局可重复；MP3 可解码且时长为 30–60 秒。
3. result bundle 和下载 ZIP 的所有成员都有 SHA-256，且共享身份字段一致。
4. 回放、主后端降级、部分成功和失败不会被展示为完整实时成功。
5. 页面仅展示或导出脱敏、allowlist 内的数据。

需求到设计证据的映射如下：

| 需求 | 设计落点 |
|---|---|
| `MULTI-01` | `ReportRenderer` 的固定中文结构与英文原文/命令保留规则 |
| `MULTI-02` | `CardRenderer` 的 Pillow 确定性布局、流程内容和 PNG 验证 |
| `MULTI-03` | `RecapComposer`、30–60 秒门禁和三级 TTS 链 |
| `MULTI-04` | `ArtifactIdentity`、canonical diagnosis hash 和一致性门禁 |
| `MULTI-05` | PNG 显式部分失败、TTS 后端降级和 manifest 标识 |
| `UX-01` | 单页 Gradio 工作台的输入、抽取、证据、报告、PNG 和 Audio 组件 |
| `UX-02` | 原子 result bundle、确定性 ZIP、source/result manifest 和 checksums |
| `UX-03` | allowlist replay index、source bundle 验证和三处回放标识 |
| `UX-04` | `ResultViewState`、失败节点、完成阶段、重试范围和降级结果 |

## 2. 总体架构

系统采用单向数据流，领域产物生成与 UI 完全分离：

```text
verified Phase 3 source bundle
        |
        v
OutcomeLoader -- strict validate + source bundle verify
        |
        v
DiagnosisPresenter -- one immutable presentation model
        |                 |                  |
        v                 v                  v
ReportRenderer       CardRenderer       RecapComposer
 (Markdown)           (Pillow PNG)       (Chinese text)
                                              |
                                              v
                                    TtsFallbackChain
                                  Dify -> edge -> SAPI
        \                 |                  /
         \                |                 /
          v               v                v
              ResultConsistencyGate
                        |
                        v
              AtomicResultPublisher
                        |
                 result bundle + ZIP
                        |
                        v
                 ResultViewState
                        |
                        v
                    Gradio UI
```

`DiagnosisPresenter` 是三个 renderer 的共同只读输入。它只做稳定排序、中文标签映射、命令展示包装和 ID 交叉引用，不创造新结论。UI 不直接读取 provider 响应，也不自行拼接报告或产物路径。

## 3. 数据合同

### 3.1 输入合同

公开入口接收 `DiagnosisRunOutcome` 和 source bundle 根目录。加载器执行以下顺序：

1. 以 strict 模式重新构造 `DiagnosisRunOutcome`。
2. 调用现有 `validate_diagnosis_outcome()`。
3. 只允许 `completed` 生成完整三模态；其他状态转换为失败/等待视图。
4. 调用 `verify_bundle()` 校验 `evidence/<case_id>/<run_id>`。
5. 比对 source manifest 的 case、run、facts、Schema、工作流和知识 build 身份。
6. 从 outcome 取得 `DiagnosisRecord`，计算 canonical `diagnosis_sha256`。

任何一步失败都在创建 result 临时目录前结束。

### 3.2 PresentationModel

`PresentationModel` 包含：

- `case_id`、`source_run_id`、`diagnosis_sha256`、`schema_version`；
- 类别中文标签、总体置信度和局限；
- 按原合同顺序排列的观察事实；
- 根因候选及其 claim kind、事实 ID、证据 ID、适用条件和反证/限制；
- 检查、修复、验证命令及完整安全元数据；
- 缺失信息、引用显示项和确定性复盘段落；
- `generation_version`，由 presenter/report/card/recap 合同版本共同组成。

该模型使用 frozen、strict、extra-forbid 的 Pydantic 合同。三个 renderer 都必须回传相同 `ArtifactIdentity`。

### 3.3 ResultManifest

`ResultManifest` 至少记录：

- manifest/result/generation 版本；
- `result_id`、`case_id`、`source_run_id`、facts revision；
- `diagnosis_sha256`、Schema/Prompt/Workflow/knowledge 版本；
- 模式 `live` 或 `replay`，回放 fixture ID；
- 状态 `completed`、`partial` 或 `failed`；
- report/card/recap/TTS 的 backend、版本、attempt 和降级原因；
- 字体文件 SHA-256、ffprobe 摘要和音频时长毫秒；
- 每个成员的相对 POSIX 路径、MIME、字节数和 SHA-256；
- 完成阶段、失败节点、安全错误码和可重试范围。

`result_id` 在全部候选文件通过本地验证后，由源身份、生成版本、backend 选择和产物哈希计算。发布采用临时同级目录原子 rename；已存在的同名目录不可覆盖。

## 4. 组件设计

### 4.1 OutcomeLoader

职责是重验严格合同、验证 Phase 3 bundle、构建 presentation 输入。它不生成文件。对不存在、篡改、版本不一致、非 completed 或诊断缺失分别返回固定安全错误码，不回显绝对路径或原始异常。

### 4.2 ReportRenderer

输出 UTF-8 `report.md`，结构固定为：

1. 案例与版本摘要；
2. 已观察事实；
3. 根因候选、事实支撑与知识支撑；
4. 检查步骤；
5. 修复步骤；
6. 验证步骤；
7. 缺失信息；
8. 置信度、适用条件与局限；
9. 引用清单。

英文 Traceback 行、异常名、包版本、脱敏路径标记和命令保持原值。命令使用代码块，并紧邻展示 platform、impact、expected result 和 rollback。推断候选使用“推断”标签，有知识与事实支持的候选使用“有依据”标签。

### 4.3 CardRenderer

Pillow renderer 固定宽度 1600 px，通过字体度量和统一断行计算画布高度。卡片包含：标题和身份条、现象、根因候选、带编号的检查路径、修复步骤、验证步骤、证据与置信度。视觉流程为从上至下的实线连接，不用生成式图形。

字体解析顺序是仓库字体资产、Windows 白名单字体；命中字体的真实文件哈希参与 renderer version。渲染后重新打开 PNG，确认单帧、尺寸、格式和空 metadata。超过安全画布高度返回 `png_layout_failed`，不会缩成不可读小字或截断。

### 4.4 RecapComposer

复盘稿固定为六段语义：问题现象、首要根因及不确定性、首个检查动作、首个修复动作、验证动作、剩余局限。它优先吸收 `DiagnosisRecord.recap_text`，但使用本地模板确保所有必要段落存在并控制为适合 30–60 秒的长度。英文错误名保留，长命令只口述其目的，不逐字符朗读。

讲稿写入 `recap.txt` 前经过输出隐私复扫，且其 SHA-256 写入 audio request metadata。

### 4.5 TtsFallbackChain

三个 adapter 暴露同一窄接口：`synthesize(text, target, request_identity) -> AudioAttempt`。

顺序固定为：

1. Dify TTS；
2. edge-tts；
3. Windows SAPI 生成 WAV，再由 FFmpeg 规范化为 MP3。

每次失败只记录固定错误码和安全摘要。候选文件必须通过 MP3 signature、ffprobe 可解码/单音轨/时长检查。时长不在 30–60 秒时，当前后端可按确定性语速表重试一次；仍失败则进入下一个后端。三个后端都失败时返回 partial，不生成占位音频。

### 4.6 ResultConsistencyGate 与 Publisher

一致性门禁检查所有 `ArtifactIdentity` 相等；报告和讲稿经过隐私复扫；PNG 经过清洗；MP3 经过媒体探测；引用只来自 diagnosis evidence；文件路径通过 confinement。Publisher 只接收门禁成功的候选集合，写出 result manifest、`checksums.sha256` 和确定性 ZIP。

ZIP 成员排序固定、路径为 POSIX 相对路径、时间戳固定，不包含临时文件、原始截图、provider body、开发日志或密钥。完整包至少含 diagnosis、report、card、recap text/audio、citations、source manifest、result manifest 和 checksums。partial 包文件名、manifest 和 UI 三处同时标注 partial。

### 4.7 ResultApplicationService

应用服务提供四个操作：

- 从真实 completed outcome 生成结果；
- 从 allowlist replay index 加载固定案例；
- 对已有 result manifest 做重新验证并恢复视图；
- 调用 Phase 3 correction/rerun 后生成新的 result。

它负责幂等/防重入和状态事件，不执行诊断命令。每次 correction 都创建新的 source run 和 result，旧目录保持不变。

### 4.8 Gradio UI

Gradio `Blocks` 第一屏就是工具工作台：

- 顶部状态条：案例 ID、实时/回放徽标、总体状态、source/backend、降级提示；
- 输入与抽取区：脱敏文本/截图预览、六个结构化字段、确认纠错与重新诊断；
- 诊断与证据区：类别、根因、置信度、事实/证据交叉引用和命令安全元数据；
- 三模态结果区：Markdown 报告、PNG、Audio player、TTS backend 与下载按钮；
- 失败详情区：失败节点、已完成/继承阶段、可重试范围、已可用结果和安全错误码。

桌面 1366×768 为主要视口。使用 tab/accordion 控制纵向长度，不设置装饰性 hero。状态同时使用图标、文字和颜色，确保录屏与无障碍可读。Gradio queue 推送阶段状态；运行中禁用重复提交。所有 `File`/`DownloadButton` 路径都来自已验证 result bundle。

## 5. 数据流

### 5.1 实时完成路径

1. UI 收到 Phase 3 completed outcome。
2. Loader 重验 outcome 和 source bundle。
3. Presenter 生成唯一 presentation model 与 diagnosis hash。
4. 报告、PNG、复盘稿分别在临时工作区生成。
5. TTS fallback chain 生成并验证 MP3。
6. 一致性门禁比较身份、隐私与媒体有效性。
7. Publisher 原子发布 result bundle 和 ZIP。
8. UI 从 result manifest 构建 completed 或 partial 视图。

### 5.2 回放路径

1. 用户从仓库 allowlist 选择固定案例。
2. 服务校验 replay index、source bundle 和 result bundle。
3. 已有合法结果直接恢复；缺少结果时从已验证 diagnosis 重新派生。
4. view state、页面徽标和 result manifest 均设置 replay 信息。
5. UI 不显示“本次调用云端成功”。

### 5.3 纠错路径

1. 用户修改一个显式字段并确认。
2. UI 构造 Phase 3 correction overlay，调用现有 rerun。
3. 新 source outcome 通过严格校验并发布新的 Phase 3 bundle。
4. Phase 4 为新 source run 生成新 result bundle。
5. 页面切换到新结果，同时保留旧结果可回放。

## 6. 错误与降级处理

错误按阶段使用固定码，不把原始异常文本带到页面：

| 阶段 | 典型错误码 | 页面行为 | 可重试范围 |
|---|---|---|---|
| source load | `source_bundle_invalid` | failed，不生成产物 | 修复/重新选择 source |
| presentation | `diagnosis_identity_mismatch` | failed | 重新运行诊断 |
| report | `report_render_failed` | failed | report 阶段 |
| PNG | `png_layout_failed` / `png_verify_failed` | partial，保留报告/音频 | card 阶段 |
| TTS | `tts_backend_failed` / `audio_duration_invalid` | 自动尝试下一后端 | 当前或下一 backend |
| all TTS | `tts_failed` | partial，保留 report/card/recap text | audio 阶段 |
| consistency | `artifact_identity_mismatch` | failed，禁止发布完整包 | 全部 renderer |
| publish | `result_publish_failed` | failed，清理 temp | publisher |
| replay | `replay_bundle_invalid` | failed，明确回放失败 | 重新选择 fixture |

`ResultViewState` 的状态转换是：`idle -> running -> completed|partial|failed`；回放在完成视图上附加独立 `replay=true` 语义，不覆盖真实完成度。刷新时只从验证过的 manifest 恢复。partial 允许下载明确标识的 partial 包，但不得进入“完整可交付”状态。

## 7. 测试策略

### 7.1 合同与身份测试

- strict/extra-forbid/JSON round-trip；
- diagnosis hash 的 canonical 稳定性；
- case/run/schema/generation 字段任一篡改均失败；
- source bundle 缺失、篡改和非 completed outcome 在写文件前失败；
- result ID、artifact identity、manifest 与 checksum 的交叉验证。

### 7.2 报告测试

- 固定 fixture 的结构 golden；
- 英文错误、命令和稳定 ID 原样存在；
- grounded/inference 标签准确；
- 命令安全元数据完整；
- 不存在 diagnosis 外新增结论；
- 输出隐私扫描通过。

### 7.3 PNG 测试

- 固定字体 fixture 下尺寸和 pixel hash golden；
- 中文、英文、命令、长行与换行边界；
- 无 ancillary metadata、单帧、正确 PNG header；
- 超高内容显式失败且不截断；
- 字体 fallback 和字体哈希写入 manifest。

### 7.4 音频测试

- 默认用 fake TTS + 已提交的短小合法 MP3 fixture，离线测试不访问网络；
- Dify 失败后 edge、edge 失败后 SAPI 的顺序与 attempt 记录；
- MP3 头错误、ffprobe 失败、多音轨、短于 30 秒、长于 60 秒；
- 确定性语速重试最多一次；
- 全后端失败产生 partial 而非空音频；
- 真实 Dify/edge/SAPI smoke tests 使用独立 marker。

### 7.5 Publisher 与 ZIP 测试

- 临时目录原子发布、异常清理和不可覆盖；
- ZIP 成员 allowlist、稳定排序/时间戳、POSIX 路径；
- ZIP 解包后 manifest/checksum 全量验证；
- partial、replay、降级状态在文件名和 manifest 中一致；
- 敏感文本、绝对路径、未清洗 PNG 或无效 MP3 均阻止发布。

### 7.6 UI 测试

- 对 `ResultViewState` 做纯函数组件可见性矩阵测试；
- completed/partial/failed/replay 的 badge、失败节点、重试范围和 download 状态；
- 输入抽取字段和 correction/rerun 事件绑定；
- 双击防重入、刷新恢复、非法路径拒绝；
- Gradio app smoke test；
- 在 1366×768 浏览器实测首屏、长报告、PNG 和 audio，不允许重叠、裁切或按钮不可见。

全量离线 suite 是默认阻断门禁；真实 TTS 和浏览器视觉检查是显式 smoke gate，并在无凭据/voice 时记录为外部门禁，不能伪造通过。

## 8. 安全与隐私

- source、result 和 download 三个边界都重新验证合同与路径 confinement。
- 报告、复盘稿、引用 JSON、manifest 安全消息都通过输出隐私扫描。
- PNG 删除 metadata 并扫描可打印嵌入字符串；MP3 不写用户文本、绝对路径或密钥 metadata。
- UI 只使用 result bundle 内的 allowlist 路径，不接受用户提供的任意下载路径。
- TTS adapter 只接收脱敏复盘稿；日志只保存 request identity、backend、时长和安全错误码。
- 所有诊断命令只展示，不提供 shell、subprocess 或自动安装入口。

## 9. 实现分解建议

为降低共享状态和回归风险，实施计划按以下依赖顺序拆分：

1. 结果身份合同、presentation model 和 source loader；
2. Markdown renderer 与引用导出；
3. Pillow card renderer 与字体/metadata 门禁；
4. recap composer、TTS ports、三级 fallback 与媒体验证；
5. result consistency gate、原子 publisher 和确定性 ZIP；
6. application service、replay index、失败恢复和 Gradio UI；
7. 全量回归、真实 TTS smoke、浏览器视觉验收与阶段验证。

这些任务不需要改写 Phase 3 的推理逻辑，也不依赖 Phase 5 或 Phase 6 才能独立验收。

## 10. 自审结果

- **完整性检查：** 所有关键 backend、路径、状态和失败行为均已选定，文档不存在未决项。
- **一致性检查：** 架构、数据流、下载合同和 UI 都以同一 validated outcome/source bundle 为入口，不存在裸 JSON 绕过；result bundle 与 Phase 3 evidence 分离，未破坏不可变性。
- **范围检查：** 仅覆盖三模态生成、统一结果页、回放、下载和降级；评测与课程包装已明确推迟。
- **歧义检查：** “确定性”限定为同一生成版本、字体资产和输入下的报告/PNG布局与身份；TTS 音频本身允许 backend 差异，但实际 backend、音频哈希和时长必须记录。
- **真实性检查：** 回放、partial 和降级都有机器可读字段与可见徽标，不会被描述为实时完整成功。

本设计在用户的持续自动授权下已批准；下一步应由 `superpowers:writing-plans` 或 GSD Phase 4 planner 将其转化为可验证实现计划。
