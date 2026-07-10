# DebugMate

## 项目定位

DebugMate 是面向人工智能专业学习场景的多模态报错诊断与复盘智能体。用户提交报错文本、截图、代码与环境信息后，系统将生成同源的文字诊断、确定性诊断图和语音复盘。

## Phase 1

当前阶段只建立平台无关的诊断契约、可审计证据链和 Dify 能力探针。仓库内置的 fixture 仅用于离线契约验证，**不是 Dify 云端运行结果，也不能作为云端能力通过证据**。

## 本地开发

项目要求 CPython 3.13：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q -m "not cloud"
.\.venv\Scripts\python.exe -m ruff check src
```

## 安全边界

- API 密钥只从环境变量读取，不写入仓库、日志或证据包。
- Phase 1 只生成诊断建议，**不会执行任何修复命令**。
- 示例使用虚构路径与身份；云端探针不得上传个人日志。
- 只有带本地哈希和运行状态的真实输出才能进入课程展示材料。
