# Dify Phase 1 重建与能力闸门

本目录保存可重建的 Dify 配置边界。`app.dsl.yml` 是已经版本化的真实平台导出；`app.dsl.yml.example` 只是**不可运行的结构样例**，不能冒充真实 DSL 或执行证据。真实 DSL 已保存并不自动证明 C06，仍需版本化的“重导入后复跑”记录。

## 设置顺序

1. 在 Dify Cloud 创建最小 Workflow 应用，输入变量为 `error_text`、`error_image`、`code`、`environment`。
2. 配置视觉模型节点，只使用仓库内虚构 `ModuleNotFoundError` 案例。
3. 创建最小知识库与 Knowledge Retrieval 节点，保留命中 chunk 的标题和来源元数据。
4. 让最终节点在 `outputs.diagnosis` 中只输出符合
   `contracts/diagnosis-record-v1.1.schema.json` 的 JSON 候选；平台成功不等于本地发布成功。
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
| C06 DSL export/import | `blocked` | [`dsl-roundtrip-evidence.json`](../../evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json) 记录真实尝试：控制台可用，但本地文件上传被浏览器扩展权限阻断，页面内导入接口返回 401；没有重导出或复跑，不得标 pass |
| C07 TTS MP3 | `pass` | [`dify-recap.mp3`](../../evidence/dify-live/2026-08-09/tts/dify-recap.mp3) 与 [`tts-evidence.json`](../../evidence/dify-live/2026-08-09/tts/tts-evidence.json) |

任何能力只有在 `evidence_path` 存在且 SHA-256 可复算时才能标记 `pass`。fixture 成功不等于 C01–C07 通过。

C03/C04 的 `pass` 分别由图像请求链和 direct retrieval node log 证明，不能只从 DSL 节点或 diagnosis.evidence 推断；同理，历史上观察到 DSL 重导入成功也不能代替 C06 的可复算复跑记录。

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
