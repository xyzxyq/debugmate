# Phase 1 Code Review

## Scope

审查范围为开发分支从 `2b5fdfb` 到 `a49f71d` 的全部 Phase 1 产品代码、测试、脚本和平台资产。Superpowers 全分支审查代理读取 100KB 审查包超过 3 分钟仍无结果，已中止；以下结论来自控制器逐文件/逐合同审查和新鲜运行证据，不把代理超时视为审查通过。

## Strengths

- `DiagnosisRecord`、manifest 与 capability evidence 都使用严格 Pydantic 合同和 `extra='forbid'`。
- fixture/cloud 的 backend、状态和证据目录完全分离。
- evidence 先写临时目录、manifest 最后写入、目录原子发布，验证器会复算所有产物。
- Dify 密钥只在 `_headers()` 解封给 HTTPX；错误不记录响应体或请求头。
- Windows PowerShell、中文路径和 UTF-8/JSON 代码页差异有真实回归验证。

## Findings resolved during review

1. **Important — failed cloud probe could not publish a failed manifest.** 通过 `3c8fb71` 增加安全错误字段，并用回归测试证明失败 bundle 可验证。
2. **Important — raw Unicode CLI path was corrupted by PowerShell capture.** 通过 `16d6eae` 将机器 JSON 输出改为 ASCII 转义，并在中文目录真实 round-trip。
3. **Important — capability pass initially checked only non-empty reference.** 通过 `a49f71d` 强制 evidence path 与 manifest artifact 及 SHA-256 一致，缺失或错哈希均被拒绝。

## Open limitations

- 当前没有用户 Dify 登录态/密钥，C01–C07 尚无真实云端全量证据；这是外部设置缺口，不是离线实现通过。
- 在线工作流变量名和输出结构仍需用实际 Dify DSL/API smoke test 校准。
- Token/成本字段已纳入 manifest，但真实云端数值要在在线响应可用后填入，不能默认当作实际零成本。

## Assessment

**Offline Phase 1 readiness:** Approved.

**Cloud capability gate:** Pending external setup;不得标为全量通过。
