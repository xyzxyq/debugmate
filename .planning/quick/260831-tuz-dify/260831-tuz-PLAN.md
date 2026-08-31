# Quick Task 260831-tuz: 稳定 Dify 知识检索查询词

## Objective

降低 Dify Knowledge Retrieval 使用完整诊断 JSON 作为查询词时的偶发空命中概率。

## Tasks

### 1. 使用短检索查询

- **Files:** `platform/dify/app.dsl.yml`, `tests/platform/test_dify_dsl.py`
- **Action:** 将 Knowledge Retrieval 查询变量改为开始节点的 `error_text`；LLM 继续使用完整 `prompt_payload`，检索净化和同次运行信封保持不变。
- **Verify:** DSL 聚焦测试、Ruff、YAML 解析，并用 Dify Dataset API 验证错误文本查询存在记录。
- **Done:** 检索节点不再绑定完整 JSON，且错误文本查询能进入检索链。

### 2. 提交并同步

- **Files:** 本次任务代码和 GSD 记录。
- **Action:** 原子提交并推送 GitHub，保留外部验收所需的手动发布步骤。
- **Verify:** 远端 `master` 与本地提交一致。
- **Done:** 用户可重新导入发布 DSL 并复跑云端验收。
