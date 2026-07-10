# Dify Phase 1 重建与能力闸门

本目录保存可重建的 Dify 配置边界。当前 `app.dsl.yml.example` 是**不可运行的结构占位文件**，不能冒充真实导出的 DSL；实际账号配置完成后，必须用平台导出的 DSL 替换并记录重导入证据。

## 设置顺序

1. 在 Dify Cloud 创建最小 Workflow 应用，输入变量为 `error_text`、`error_image`、`code`、`environment`。
2. 配置视觉模型节点，只使用仓库内虚构 `ModuleNotFoundError` 案例。
3. 创建最小知识库与 Knowledge Retrieval 节点，保留命中 chunk 的标题和来源元数据。
4. 让最终节点只输出符合 `contracts/diagnosis-record-v1.schema.json` 的 `diagnosis_json`。
5. 在 API Access 中取得应用密钥，并仅通过本机环境变量 `DIFY_API_KEY` 提供；知识库管理 API 如需单独密钥，使用 `DIFY_DATASET_API_KEY`。
6. 默认端点为 `DIFY_BASE_URL=https://api.dify.ai/v1`，调用身份为 `DIFY_USER=debugmate-local`。
7. 导出真实 DSL 到本目录，重新导入为新应用，并把导入结果截图/日志放入对应 evidence bundle 后，C06 才能为 `pass`。
8. 如账号提供 TTS provider，调用真实 TTS 保存 MP3；没有 provider 时保持 C07 为 `blocked` 或 `not-tested`。

## 七项能力

- C01：Authentication/API，真实非 401/403 响应及 run/request ID。
- C02：File upload，虚构输入上传后得到 file ID。
- C03：Vision extraction，真实提取截图中的 `ModuleNotFoundError` 关键文本。
- C04：Knowledge retrieval，返回至少一个带来源元数据的 chunk。
- C05：Structured JSON，响应通过 `DiagnosisRecord` 严格验证。
- C06：DSL export/import，真实导出并成功重导入，且有本地证据文件。
- C07：TTS MP3，保存的字节通过 MP3 文件头与后续 FFprobe 验证。

任何能力只有在 `evidence_path` 存在且 SHA-256 可复算时才能标记 `pass`。fixture 成功不等于 C01–C07 通过。

## 时间与成本闸门

在线配置与探针累计最多投入 **4 小时**。网络、账号、配额或节点配置无法解决时，记录 `blocked` 并保留 fixture 路径；不得充值、购买模型额度或订阅，除非事先取得用户明确确认。

## DSL 证据要求

真实 DSL 必须完成“导出 → Git 保存 → 新应用重导入 → 固定虚构案例复跑”。只有四步都有证据时才更新 capability matrix；平台截图不能替代 DSL 与本地 manifest。
