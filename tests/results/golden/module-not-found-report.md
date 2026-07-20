# DebugMate 诊断报告

## 1. 案例与版本摘要
- 案例 ID：case_00000000000000000000000000000000
- 来源运行 ID：run_19a9caf71e973d78e0698ae92732dc6d
- 诊断摘要：21e01cfd2f250a08d850a191630efae2531a762f83b3552ab31a44582940779a
- Schema：1.1.0
- 生成版本：gen_7b40b699ce9091d025b174f75ddb16b3
- 类别：dependency_environment

## 2. 已观察事实
- `fact_5dd97b9dd15e4e21db630cdd2a9fc765` · `version` · 3.13.5 · 置信度 1.00 · 来源 text · 定位 fact:fact_5dd97b9dd15e4e21db630cdd2a9fc765
- `fact_bca9692bc3505d603a3df89f9546df40` · `traceback_key_line` · ModuleNotFoundError: No module named 'demo_missing_pkg' · 置信度 1.00 · 来源 text · 定位 fact:fact_bca9692bc3505d603a3df89f9546df40
- `fact_d10bd74dfa10944e11a20a8c669b7b39` · `package` · demo_missing_pkg · 置信度 1.00 · 来源 text · 定位 fact:fact_d10bd74dfa10944e11a20a8c669b7b39
- `fact_d15385d635ae0944ba6ae5c3efc9d0f7` · `exception_type` · ModuleNotFoundError · 置信度 1.00 · 来源 text · 定位 fact:fact_d15385d635ae0944ba6ae5c3efc9d0f7

## 3. 根因候选与证据
- 无根因候选；报告未补写诊断结论。

## 4. 检查步骤
### 1
- 平台：windows_powershell
- 影响：read-only
- 预期结果：The active Python executable path is displayed.
- 回滚说明：No rollback is needed for a read-only command.
```text
python -c "print(__import__('sys').executable)"
```

### 2
- 平台：windows_powershell
- 影响：read-only
- 预期结果：Package metadata or a not-found message is displayed.
- 回滚说明：No rollback is needed for a read-only command.
```text
python -m pip show demo_missing_pkg
```

## 5. 修复步骤
### 1
- 平台：windows_powershell
- 影响：changes-environment
- 预期结果：The package is installed into the active environment.
- 回滚说明：python -m pip uninstall demo_missing_pkg
```text
python -m pip install demo_missing_pkg
```

## 6. 验证步骤
### 1
- 平台：windows_powershell
- 影响：read-only
- 预期结果：The command exits without ModuleNotFoundError.
- 回滚说明：No rollback is needed for a read-only command.
```text
python -c "import demo_missing_pkg"
```

## 7. 缺失信息
- The interpreter path and intended virtual environment are not supplied.

## 8. 置信度、适用条件与局限
- 总体置信度：0.86
- This fixture does not inspect a real Python environment and does not execute commands.

## 9. 引用清单
- `evidence_44444444444444444444444444444444` · python-docs · https://docs.python.org/3/ · 定位 fixture · chunk `fixture:1` · build `3333333333333333333333333333333333333333333333333333333333333333`
