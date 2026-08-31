# Dify Phase 1 重建与能力闸门

本目录保存可重建的 Dify 配置边界。`app.dsl.yml` 是由真实平台导出维护的版本化安全合同；提交前已移除远端知识库绑定值，导入后必须在控制台重新绑定已验证知识库。`app.dsl.yml.example` 只是**不可运行的结构样例**，不能冒充真实 DSL 或执行证据。DSL 已保存并不自动证明当前产品链，仍需版本化的“重导入后复跑”记录。

## 设置顺序

1. 在 Dify Cloud 创建最小 Workflow 应用，输入变量为 `error_text`、`image_input`、`code`、`environment`。
2. 配置视觉模型节点，只使用仓库内虚构 `ModuleNotFoundError` 案例。
3. 创建最小知识库与 Knowledge Retrieval 节点，保留命中 chunk 的标题和来源元数据。
4. 让最终节点在 `outputs.run_envelope` 中输出包含直接检索 trace 与严格诊断候选的同次运行信封；平台成功不等于本地发布成功。
5. 在 API Access 中取得应用密钥，并仅通过本机环境变量 `DIFY_API_KEY` 提供；知识库管理 API 如需单独密钥，使用 `DIFY_DATASET_API_KEY`。
6. 默认端点为 `DIFY_BASE_URL=https://api.dify.ai/v1`，调用身份为 `DIFY_USER=debugmate-local`。
7. 导出真实 DSL 到本目录，重新导入为新应用，并把导入结果截图/日志放入对应 evidence bundle 后，C06 才能为 `pass`。
8. 如账号提供 TTS provider，调用真实 TTS 保存 MP3；没有 provider 时保持 C07 为 `blocked` 或 `not-tested`。

## 候选诊断与本地裁决

- fixture 与 Dify adapter 都只返回有大小上限的 `CandidateRunResult`，不在 adapter 内构造或发布
  `DiagnosisRecord`。
- 本地 `DiagnosisGenerator` 是唯一诊断发布边界；它严格复核 Schema、case ID、最终路由、事实、
  evidence、knowledge build、命令策略和隐私扫描。
- 可修复的 JSON/合同错误最多发起一次 `contract_repair`。修复请求只含 Schema 版本、有限错误码、
  JSON pointer 和已经脱敏的候选；第二次失败返回 `generation_failed`，不保留部分诊断。
- HTTP transport 的一次网络重试与本地 contract repair 是独立预算，不能互相增加次数。
- 真实 smoke 仅在显式设置 `DIFY_API_KEY` 和
  `DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED=1` 后通过
  `pytest -m cloud tests/diagnosis/test_dify_diagnosis_cloud.py` 运行；缺少任一配置时安全跳过。

## 七项能力

当前逐项状态以 [`capability-matrix.json`](capability-matrix.json) 为唯一机器可读来源：

| 能力 | 状态 | 版本化证据或未通过原因 |
|---|---|---|
| C01 Authentication/API | `pass` | [`dify-upload.json`](../../evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/dify-upload.json) |
| C02 File upload | `pass` | 与 C01 共享同一份真实上传响应证据 |
| C03 Vision extraction | `pass` | [`vision-retrieval-evidence.json`](../../evidence/dify-live/2026-08-09/c03-c04/vision-retrieval-evidence.json) 绑定 target-free request manifest、真实 PNG 上传、Workflow run 指纹和 exact VLM extraction |
| C04 Knowledge retrieval | `pass` | 同一能力记录另绑定 [`retriever-resource.json`](../../evidence/dify-live/2026-08-09/c03-c04/retriever-resource.json)；主证据来自 Knowledge Retrieval node execution direct output，含 chunk/source URL/locator/score |
| C05 Structured JSON | `pass` | [`diagnosis.json`](../../evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/diagnosis.json) 已通过严格合同校验 |
| C06 DSL export/import | `pass` | [`dsl-roundtrip-evidence.json`](../../evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json) 绑定 distinct source/independent app 指纹、byte-exact re-export、相同规范化结构哈希与 authoritative reconstructed-app rerun |
| C07 TTS MP3 | `pass` | [`dify-recap.mp3`](../../evidence/dify-live/2026-08-09/tts/dify-recap.mp3) 与 [`tts-evidence.json`](../../evidence/dify-live/2026-08-09/tts/tts-evidence.json) |

任何能力只有在 `evidence_path` 存在且 SHA-256 可复算时才能标记 `pass`。fixture 成功不等于 C01–C07 通过。

C03/C04 的 `pass` 分别由图像请求链和 direct retrieval node log 证明，不能只从 DSL 节点或 diagnosis.evidence 推断；C06 的 `pass` 则由 independent import、re-export、规范化结构相等和 reconstructed-app rerun 的 Git-tracked 精确哈希链证明。此次提升没有刷新课程 PPTX、视频、字幕或最终截图。

## Phase 08 同次运行产品合同

上表 C01–C07 是 2026-08-08/09 留存的**隔离能力证据**，不是 Phase 08 当前
`approved input → upload → direct retrieval → diagnosis → local validation` 同次运行产品证据。
尤其是历史 C04 的 direct retrieval node log 只能证明当时检索能力存在，不能替代当前
`run_envelope.retrieval_trace`。

当前 DSL 将 Knowledge Retrieval 节点的直接 `result` 先送入确定性“知识证据净化”节点：只保留最多
4 个唯一命中、HTTPS 来源、来源/定位、短摘要、分数和指纹，再把该 trace 与限长 extraction facts、
DiagnosisRecord 1.1.0 候选及版本身份封装为唯一 End 输出 `run_envelope`。`file_id` 不作为工作流文件输入；
图片只接受上传后 singular `image_input`，纯文本调用必须省略该字段。

本次离线任务**没有声称已经完成**新版 DSL 的 Dify live 验证。Phase 08 通过前仍必须执行并留存：

1. 导入当前 DSL，并重新绑定通过 17 源 readback 的知识库；
2. 发布应用后重新导出，确认安全语义合同与仓库版本一致；
3. 用一份当前已批准脱敏 PNG 验证上传和 singular `image_input`；
4. 运行一次 blocking workflow，严格校验同一 `run_envelope` 的 extraction、direct retrieval、diagnosis 和合同身份；
5. 只保存安全指纹、allowlisted usage 和本地验证结果，不保存任何远端原始标识或 provider body。

## Phase 08 当前验收状态（2026-08-31）

- 本地 17 源知识构建与 Dify 真实 readback 已完成，严格回读保存在
  [`knowledge-readback.json`](../../evidence/dify-live/phase8/knowledge-readback.json)。
- 仓库 DSL 已绑定当前知识构建 `e8e065b4...`，并新增零跳过 cloud/Edge runner 与安全范围闸门：
  [`run-phase8-live-qa.ps1`](../../scripts/run-phase8-live-qa.ps1)、
  [`verify-phase8-security-scope.ps1`](../../scripts/verify-phase8-security-scope.ps1)。
- 当前真实 cloud smoke 已能完成知识同步、图片上传和 Workflow 调用，但远端已发布应用仍返回旧版
  `diagnosis` 输出，尚未返回仓库要求的 `run_envelope`；本地适配器按设计拒绝伪造信封。
- 继续验收前必须在 Dify 控制台导入本文件、重新绑定当前知识库并发布；随后执行：
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-phase8-live-qa.ps1`

## 版本化现场证据复验

[`evidence/dify-live/`](../../evidence/dify-live/) 保存无秘密的现场证据。cloud bundle 原样保留 2026-08-08 探针结果；`c03-c04/` 保存图像请求与检索节点证据；`c06/` 保存准确 blocker；TTS 目录保存 2026-08-09 通过正式 Dify live gate 生成并经 FFprobe 检查的 MP3。

```powershell
$python = (Resolve-Path -LiteralPath '.venv\Scripts\python.exe').Path
$env:PYTHONPATH = (Resolve-Path -LiteralPath 'src').Path
$bundle = (Resolve-Path -LiteralPath 'evidence\dify-live\2026-08-08\cloud-probe\case_d2c4d21672c14d9bad7f7fe95ee86653').Path
& $python -m debugmate.cli verify-bundle $bundle
& $python -m debugmate.dify_live_evidence validate-published --repository-root . --evidence-root 'evidence\dify-live\2026-08-09'
ffprobe -v error -show_entries stream=codec_name,channels -show_entries format=duration,size -of json 'evidence\dify-live\2026-08-09\tts\dify-recap.mp3'
Get-FileHash -Algorithm SHA256 -LiteralPath 'evidence\dify-live\2026-08-09\tts\dify-recap.mp3'
```

## 时间与成本闸门

在线配置与探针累计最多投入 **4 小时**。网络、账号、配额或节点配置无法解决时，记录 `blocked` 并保留 fixture 路径；不得充值、购买模型额度或订阅，除非事先取得用户明确确认。

## DSL 证据要求

真实 DSL 必须完成“导出 → Git 保存 → 新应用重导入 → 固定虚构案例复跑”。只有四步都有证据时才更新 capability matrix；平台截图不能替代 DSL 与本地 manifest。
