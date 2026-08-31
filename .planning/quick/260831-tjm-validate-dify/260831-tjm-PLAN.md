# Quick Task 260831-tjm: 扩展 Dify 安全收口以拦截中文安装建议

## Objective

在没有可追溯知识证据时，阻止 Dify 诊断复盘文字通过中文自然语言变相建议安装未知 Python 包。

## Tasks

### 1. 扩展安全收口规则

- **Files:** `platform/dify/app.dsl.yml`
- **Action:** 扩展安装建议匹配规则，覆盖英文安装命令、中文“通过 pip 安装”和“安装此模块”等表达；命中时沿用现有安全复盘文本。
- **Verify:** DSL 安全收口测试覆盖中文表达。
- **Done:** 无 evidence 时 `fixes` 为空，`recap_text` 不包含安装未知包的建议，置信度上限仍为 0.70。

### 2. 回归验证与提交

- **Files:** `tests/platform/test_dify_dsl.py`
- **Action:** 增加中文安装建议测试，运行聚焦测试和 Ruff，提交代码并同步 GitHub。
- **Verify:** pytest 与 Ruff 通过，远端 `master` 包含本次提交。
- **Done:** 本地代码与 GitHub 同步，等待用户重新导入 DSL 做云端复跑。
