# DebugMate

## 项目定位

DebugMate 是面向人工智能专业学习场景的多模态报错诊断与复盘智能体。当前 V0.1 是可在 Windows 桌面浏览器运行的本地课程演示版：它帮助学生整理 Python/AI 工程报错，给出带依据且说明不确定性的诊断，并从同一份严格结构化记录生成文字报告、PNG 诊断卡和 MP3 语音复盘。

V0.1 不是公网部署、生产系统或自动修复工具。页面展示的命令只供用户审阅和手动执行，DebugMate 不会直接修改用户环境。

## 当前 V0.1 本地演示能力

- 接收报错文本、终端截图、代码片段和基础环境信息，并在缺少必要输入时阻止提交。
- 在本机识别并遮蔽 Token、密码、邮箱、用户名和绝对路径等敏感信息，先向用户展示脱敏预览，再要求显式确认。
- 从确认后的输入抽取错误事实，允许用户纠正关键字段；按本地规则和版本化知识快照完成分类、知识引用和诊断。
- 使用严格 `DiagnosisRecord` 保存根因候选、观察证据、知识引用、检查步骤、修复步骤、验证命令、置信度和局限。
- 从同一个已校验记录派生 Markdown 报告、确定性 PNG 诊断卡和 MP3 复盘，并在 Gradio 结果页统一展示。
- 下载包含诊断、报告、图片、音频、引用、manifest 和校验值的 ZIP evidence bundle；失败或降级状态会保留真实节点信息。
- 加载仓库 allowlist 中的脱敏证据包进行固定离线回放，并在状态、摘要和下载信息中标明“回放”。

## 真实工作流

```text
输入校验
  → 本地文本/截图脱敏
  → 用户检查预览并显式确认
  → 事实抽取与可纠正字段
  → 本地规则、知识快照与引用
  → 严格 DiagnosisRecord 校验
  → 同源 Markdown / PNG / MP3
  → Gradio 结果展示
  → ZIP evidence bundle
```

当前普通演示既包含本地实时处理，也包含固定回放。固定回放来自 [`fixtures/replay/index.json`](fixtures/replay/index.json) 所列的仓库 allowlist 脱敏证据包，用于稳定展示已保存的真实状态和多模态产物；**固定回放不等于实时 Dify 或其他云端调用**。本地规则生成的诊断同样不能证明云端视觉、检索、工作流或 TTS 已可用。

## 架构分工

| 层 | 当前职责 |
|---|---|
| 本地 Python | 输入校验、脱敏与确认、事实抽取、本地规则/知识引用、证据落盘和 ZIP 打包 |
| Pydantic | 严格验证 `DiagnosisRecord`、结果状态和 manifest，拒绝静默类型转换与额外字段 |
| Pillow / 本地 TTS | 从同一诊断记录确定性生成 PNG；按可用后端生成并验证 MP3 |
| Gradio | 提供输入、隐私确认、学生诊断摘要、多模态结果、技术细节和下载入口 |
| Dify（可选增强） | 预留云端视觉、知识检索、工作流和 TTS 接入；当前能力矩阵尚未实测 |

Git 仓库是可提交事实源。云端配置不能替代仓库中的知识源、提示词、Schema、回放样例、测试和运行证据。

## 关键目录

| 路径 | 内容 |
|---|---|
| [`src/debugmate/`](src/debugmate/) | 本地诊断、隐私、知识、结果生成与 UI 代码 |
| [`src/debugmate/ui/serve.py`](src/debugmate/ui/serve.py) | 本地 Gradio 演示入口 |
| [`knowledge/`](knowledge/) | 官方知识源清单、本地快照、构建与评测资产 |
| [`fixtures/replay/`](fixtures/replay/) | allowlist 固定回放索引与脱敏证据包 |
| [`platform/dify/`](platform/dify/) | Dify 能力矩阵和可重建平台资产 |
| [`tests/`](tests/) | 契约、隐私、结果和 UI/Edge 自动测试 |
| [`evidence/`](evidence/) | 经校验的本地运行与课程证据 |
| [`.planning/`](.planning/) | 项目需求、路线图、阶段记录和当前状态 |
| [`docs/course/README.md`](docs/course/README.md) | 课程运行与提交说明 |

## 快速运行

项目要求 CPython 3.13。新环境可在仓库根目录创建自己的 `.venv`；下列步骤不依赖任何个人目录或既有 worktree 环境。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m debugmate.ui.serve
```

打开命令输出中的本地地址即可使用。2026-08-08 的验证记录来自当时已核验的 Python 3.13 环境；它说明该次验证条件，不代表每位读者本机已经存在同一路径或同一虚拟环境。

## 测试

普通 UI 合同测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/ui/test_app.py
```

显式 Microsoft Edge 浏览器套件：

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m browser tests/ui/test_browser.py
```

Edge 套件会启动真实浏览器，耗时明显长于普通测试；其中依赖专用 QA server 或特定根环境的案例会以 `environment-gated` skip 明确记录，而不是伪装为通过。

## 能力探针

在仓库根目录可分别运行固定 fixture 探针与真实云端探针；两个命令都必须提供 `--output`：

```powershell
.\.venv\Scripts\python.exe -m debugmate.cli fixture-probe --output .artifacts\phase1-probe
.\.venv\Scripts\python.exe -m debugmate.cli cloud-probe --output .artifacts\phase1-probe
```

`fixture-probe` 不需要云凭据，只验证固定输入下的探针合同与 evidence bundle 生成。它退出 0 时，C01–C07 七项云能力仍全部是 `not-tested`；这不能证明 Dify 认证、文件上传、视觉、知识检索、工作流、DSL 导入导出或云端 TTS 已通过。

`cloud-probe` 仅在用户自行配置所需环境变量（例如 `DIFY_API_KEY`）后发起真实云调用。本仓库当前没有已成功执行该命令的声明。其退出码 0/1/2 分别表示探针完成、探针合同/传输/结果验证失败、因凭据等前置条件受阻；退出 0 也不表示七项能力全部通过，当前实现只会把有真实证据的 C01、C02、C05 标为 `pass`，其他能力仍可为 `not-tested`。

两个命令输出的 JSON 都包含 `backend`、`bundle_path` 和 `status_counts`：`bundle_path` 指向可审计证据包，`status_counts` 汇总该次逐能力状态。最终结论必须以 bundle 内每项状态、证据路径和 SHA-256 为准：

- `pass`：仅表示该项具体能力有真实执行证据支撑，并且应有证据路径与 SHA-256。
- `fail`：该项已经尝试，但合同、传输或结果验证失败。
- `blocked`：凭据、账号、配额或其他前置条件阻止了真实测试。
- `not-tested`：该项本次没有真实执行，不能从本地、fixture 或其他能力的成功推断为通过。

[`scripts/run_phase1_probe.ps1`](scripts/run_phase1_probe.ps1) 是包装入口：它先运行 fixture 探针，仅在凭据存在时运行 cloud 探针，然后执行离线测试与 Ruff。包装脚本成功同样不能替代 bundle 内逐能力证据；当前能力矩阵仍是 C01–C07 全部 `not-tested`。

## 固定回放与真值标签

固定回放用于稳定复现完成、长内容、部分失败和降级等已保存结果，便于课堂讲解与回归检查。它只读取 [`fixtures/replay/index.json`](fixtures/replay/index.json) allowlist 中的脱敏证据目录，不接受浏览器任意文件路径。

- `live`：本地输入经过校验、脱敏、确认后由当前本地流水线处理。
- `replay`：加载仓库中已存在且经过 allowlist/manifest 校验的结果，不是一次新的推理。
- `fallback`：主后端不可用时使用已记录的本地降级后端；页面必须显示最终后端与原因。
- `not-tested`：能力尚未执行真实验证，不能从本地成功或 fixture 成功推断为已通过。

因此，回放不是实时云端结果，本地规则也不是 Dify 诊断结果。

## 安全边界

- 敏感配置只通过环境变量名（例如 `DIFY_API_KEY`）或未赋值的 `.env.example` 约定说明，不在文档、日志、证据包或提交材料中保存秘密值。
- 输入在离开本机前进行文本和截图脱敏，并由用户确认；输出、PNG 元数据、音频讲稿和导出内容还会再次扫描。
- 日志、截图、代码和知识文档都按不可信数据处理，不能覆盖系统策略或触发外部动作。
- 页面仅展示修复与验证命令，不自动执行 Shell、PowerShell、包安装或模型生成的操作。
- 固定回放只能从服务端 allowlist 与经过校验的 manifest 发布，不允许客户端指定任意本地路径。

## 当前验证

以下是 **2026-08-08** 已保存验证记录的摘要，不是本次 README 更新重新运行后的永久保证：

- [`tests/ui/test_app.py`](tests/ui/test_app.py)：`34 passed`。
- [`tests/ui/test_browser.py`](tests/ui/test_browser.py) 显式 Edge 套件：`39 passed`、`7 environment-gated skipped`、`0 failed`。
- [学生诊断 UI quick verifier](.planning/quick/260721-uf9-debugmate/260721-uf9-VERIFICATION.md)：`5/5 must-haves` verified。

上述记录验证当前本地学生诊断 UI、严格记录派生展示、隐私确认、真实 Edge 几何/键盘/缩放和下载边界。完整 Edge 套件约需 14 分钟，本次文档真值同步不把未复跑写成新的测试结果。

## 当前限制

- [`platform/dify/capability-matrix.json`](platform/dify/capability-matrix.json) 中 C01–C07 七项全部仍为 `not-tested`。Dify 认证、文件上传、云端视觉、知识检索、结构化工作流、DSL 导入导出和云端 TTS 均不得写成已完成或已验收。
- 当前本地规则与知识快照覆盖课程选取的 Python/AI 高频场景，不代表覆盖全部框架、版本和故障。
- Local SAPI 生成的中文复盘已有“可解码、非静音”等机器证据，但仍需在实体播放设备上进行一次人耳听感检查；机器检查不能替代主观听验。
- V0.1 面向单用户 Windows 本地课程演示，不包含公网部署、多人账号、生产监控、SLA 或并发压测。
- 系统提供诊断建议和验证命令，不保证修复成功，也不自动执行修复。

## 后续工作顺序

1. 先持续保持本地课程演示、证据、README 与项目状态一致。
2. 按实际演示需要实测 Dify C01–C07，并只依据真实运行证据更新能力矩阵。
3. 安排 `physical-device` 上的 Local SAPI 中文复盘人耳听验。
4. 最后才统一刷新 PPTX、视频、字幕和最终截图，避免在 UI 与事实口径仍变化时反复改写交付物。

本次 README/STATE 真值同步不处理或刷新 PPTX、视频、字幕、最终截图及其他课程交付物。
