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

## Phase 1 能力探针

离线 fixture 探针不需要账号：

```powershell
.\.venv\Scripts\python.exe -m debugmate.cli fixture-probe --output .artifacts\phase1
```

配置 `DIFY_API_KEY` 后才可运行真实云端探针：

```powershell
.\.venv\Scripts\python.exe -m debugmate.cli cloud-probe --output .artifacts\phase1-cloud
```

也可使用 Windows 一键脚本：

```powershell
.\scripts\run_phase1_probe.ps1
```

状态语义：`pass` 表示有本地证据路径与 SHA-256 的真实通过；`fail` 表示已真实执行但合同失败；`blocked` 表示缺少账号、额度或必要外部能力；`not-tested` 表示尚未执行，绝不能从 fixture 成功推断。

每次运行写入 `evidence/<case_id>/` 或命令指定的输出根目录，至少包含 `input.redacted.json`、`probe-results.json`、`manifest.json`，fixture 还包含 `diagnosis.json`。可用以下命令复算：

```powershell
.\.venv\Scripts\python.exe -m debugmate.cli verify-bundle <bundle-path>
```

## 当前限制

- 本仓库尚未获得当前用户 Dify 账号的真实 C01–C07 证据，能力矩阵保持 `not-tested`。
- `app.dsl.yml.example` 只是不可运行占位文件，真实 DSL 必须在平台配置后导出并重导入验证。
- Phase 2 才会建立正式知识源 manifest 与输入脱敏流水线；Phase 4 才会生成 PNG/MP3 和 Gradio 结果页。
