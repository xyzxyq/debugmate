# Quick Task 260831-tnv: 支持 Dify Knowledge Retrieval result 包装结构

## Objective

让知识证据净化器读取 Dify 工作流 Knowledge Retrieval 实际返回的 `{ "result": [...] }` 包装结构，避免有效命中被误判为空。

## Tasks

### 1. 兼容 result 包装并增加测试

- **Files:** `platform/dify/app.dsl.yml`, `tests/platform/test_dify_dsl.py`
- **Action:** 在 retrieval records 解析器中支持 `result` 列表，同时保留 `records` 和裸数组兼容；添加真实工作流包装形状测试。
- **Verify:** DSL 聚焦测试、Ruff、YAML 解析。
- **Done:** `{ "result": [...] }` 能产生带来源元数据的检索命中。

### 2. 提交并同步

- **Files:** 本次任务代码和 GSD 记录。
- **Action:** 原子提交本次修复并推送 GitHub，保留现有未相关证据改动。
- **Verify:** 远端 `master` 与本地提交一致。
- **Done:** 用户可重新导入发布 DSL 并复跑云端案例。
