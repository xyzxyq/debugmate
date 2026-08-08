---
quick_id: 260808-opt
phase: quick-260808-opt-readme-probe-cli
plan: 01
type: quick
wave: 1
depends_on: []
autonomous: true
description: 修复根 README 的 probe 命令与能力状态说明，使文档重新满足真实 CLI 合同和测试
mode: quick
date: 2026-08-08
files_modified:
  - README.md
must_haves:
  truths:
    - "读者可从根 README 直接复制 fixture-probe 与 cloud-probe 的真实 PowerShell 命令，并理解两者都要求 --output。"
    - "README 准确定义 pass、fail、blocked、not-tested，并明确 fixture-probe 成功不等于任何 Dify 云能力通过。"
    - "README 不宣称 cloud-probe 已成功，不包含秘密值、个人绝对路径或不存在的命令入口。"
  artifacts:
    - path: README.md
      provides: "与 debugmate.cli 和能力探针测试一致的 probe 运行及状态判读说明"
    - path: .planning/quick/260808-opt-readme-probe-cli/260808-opt-SUMMARY.md
      provides: "执行后记录 README 修复和验证结果的 quick 摘要"
  key_links:
    - from: README.md
      to: src/debugmate/cli.py
      via: "文档命令使用已注册的 fixture-probe/cloud-probe 子命令及必填 --output 参数"
      pattern: "debugmate\\.cli (fixture-probe|cloud-probe) --output"
    - from: README.md
      to: tests/test_probe_cli.py
      via: "文档同时包含两个子命令和 pass/fail/blocked/not-tested 四个状态词"
      pattern: "fixture-probe|cloud-probe|not-tested"
---

# Quick Task 260808-opt Plan

<objective>
修正根 README 的能力探针入口与状态解释，使公开文档重新符合现有 CLI、探针退出码和证据真实性合同。

Purpose: 当前 README 缺少 `fixture-probe`、`cloud-probe` 以及完整状态语义，导致真实文档契约测试失败，也可能让读者把 fixture 成功误解为云能力已验证。
Output: 更新后的 `README.md`，以及执行完成后生成的 quick `260808-opt-SUMMARY.md`；不修改项目状态、路线图、需求、产品代码、测试或课程交付物。
</objective>

<context>
@AGENTS.md
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md
@.planning/STATE.md
@README.md
@tests/test_probe_cli.py
@src/debugmate/cli.py
@src/debugmate/probe.py
@scripts/run_phase1_probe.ps1

Locked boundaries:
- 只修改 `README.md`；执行后按 quick workflow 创建本目录的 `260808-opt-SUMMARY.md`。不得修改 `.planning/STATE.md`、`.planning/ROADMAP.md`、`.planning/REQUIREMENTS.md`、产品代码、测试、PPTX、视频、字幕、截图或其他课程交付物。
- 以 `debugmate.cli` 的真实合同为准：`fixture-probe` 与 `cloud-probe` 都要求 `--output`；CLI 输出包含 `backend`、`bundle_path` 和 `status_counts`。
- `fixture-probe` 返回 0 只表示固定 fixture 探针及证据包生成成功；其 C01-C07 状态仍全部为 `not-tested`，不得据此宣称 Dify 认证、上传、视觉、检索、工作流、DSL 或 TTS 通过。
- `cloud-probe` 未配置凭据时返回 2 并记录 `blocked`，探针合同/传输失败时返回 1 并记录 `fail`，真实执行成功时返回 0；即使返回 0，当前实现也只会为有证据的 C01、C02、C05 标 `pass`，其余能力仍可为 `not-tested`。文档不得声称本仓库已取得任何 cloud-probe 成功结果。
- 环境配置只允许提到环境变量名，不写示例密钥值；命令使用仓库相对路径，不写个人 Windows 绝对路径。
</context>

<tasks>

<task type="auto">
  <name>Task 1: 补齐 README probe 命令与可审计状态语义</name>
  <files>README.md</files>
  <action>在根 README 的测试/验证说明附近新增一个紧凑的“能力探针”小节。给出可从仓库根目录运行的两条真实 PowerShell 命令：`.\.venv\Scripts\python.exe -m debugmate.cli fixture-probe --output .artifacts\phase1-probe` 与 `.\.venv\Scripts\python.exe -m debugmate.cli cloud-probe --output .artifacts\phase1-probe`；说明前者无需云凭据，后者仅在用户自行配置所需环境变量后才会发起真实云调用，并可补充 `scripts/run_phase1_probe.ps1` 是顺序运行 fixture、按凭据条件运行 cloud、再执行离线测试与 Ruff 的包装入口。解释 CLI JSON 中 `bundle_path`/`status_counts` 的用途，并逐一定义能力级状态：`pass` 仅表示该具体能力已由真实执行证据支撑，且应有证据路径和 SHA-256；`fail` 表示已尝试但合同、传输或结果验证失败；`blocked` 表示凭据、账号、配额或其他前置条件阻止实测；`not-tested` 表示该能力本次没有被真实执行，不能从本地或其他能力成功推断通过。明确写出 fixture 命令即使退出 0，C01-C07 仍是七项 `not-tested`；cloud 命令的退出码 0/1/2 分别对应完成/失败/受阻，但退出 0 也不代表七项全部通过，应以生成 bundle 内逐项状态和证据为准。延续 README 当前事实：能力矩阵仍全部 `not-tested`，不得加入任何云端成功、已验收或已完成声称。不要改写现有项目定位、UI 能力、验证计数、后续顺序或交付物边界；不要加入密钥值、个人路径、不可移植环境路径或要求充值的步骤。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; & $python -m pytest -q tests\test_probe_cli.py::test_reconstruction_docs_and_examples_are_truthful_and_secret_free; if($LASTEXITCODE){ throw 'Targeted probe documentation contract failed' }; $readme=Get-Content -LiteralPath 'README.md' -Raw -Encoding UTF8; foreach($token in @('fixture-probe','cloud-probe','pass','fail','blocked','not-tested','--output','status_counts')){ if($readme -notmatch [regex]::Escape($token)){ throw "README missing probe contract token: $token" } }; if($readme -notmatch 'debugmate\.cli fixture-probe --output' -or $readme -notmatch 'debugmate\.cli cloud-probe --output'){ throw 'README probe commands do not match the CLI parser' }; if($readme -notmatch '(?s)fixture-probe.+(C01.+C07|7|七).+not-tested' -or $readme -notmatch '(?s)cloud-probe.+(0/1/2|0.+1.+2)'){ throw 'README does not explain truthful fixture/cloud outcomes' }; if($readme -match '(?i)(api[_ -]?key|token|secret|password)\s*[:=]\s*[\x22\x27]?[A-Za-z0-9_\-]{8,}' -or $readme -match '(?i)Bearer\s+[A-Za-z0-9._\-]+' -or $readme -match '[A-Z]:\\Users\\'){ throw 'README may contain a secret value or personal absolute path' }; foreach($path in @('src\debugmate\cli.py','scripts\run_phase1_probe.ps1','.artifacts')){ if($path -ne '.artifacts' -and -not (Test-Path -LiteralPath $path -PathType Leaf)){ throw "Documented target missing: $path" } }; git diff --check -- README.md .planning\quick\260808-opt-readme-probe-cli; if($LASTEXITCODE){ throw 'Markdown diff check failed' }; $allowed=@('README.md','.planning/quick/260808-opt-readme-probe-cli/260808-opt-PLAN.md','.planning/quick/260808-opt-readme-probe-cli/260808-opt-SUMMARY.md'); $changed=@(git status --short | ForEach-Object { $_.Substring(3).Replace('\','/') }); $unexpected=@($changed | Where-Object { $_ -notin $allowed }); if($unexpected){ throw "Out-of-scope changes detected: $($unexpected -join ', ')" }</automated>
  </verify>
  <done>README 提供可复制的 fixture/cloud probe 命令和真实退出码/状态解释；目标测试、秘密与个人路径扫描、diff 及修改范围检查全部通过，且没有新增云端成功声称。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| fixture 结果 → 云能力声明 | 本地 fixture 只验证探针和证据包管线，不能证明任何 Dify 能力。 |
| cloud 探针状态 → README 结论 | 只有逐能力真实证据可支撑 `pass`；退出码或其他能力成功不能替代证据。 |
| 文档命令 → 读者环境 | 可复制命令不得泄露秘密、绑定个人路径或暗示缺少凭据时已经实测。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q-OPT-01 | Spoofing | README probe 结果说明 | mitigate | 明确 fixture 七项均 `not-tested`，cloud 逐能力以 evidence path/SHA-256 判定，不把退出 0 等同全通过。 |
| T-Q-OPT-02 | Repudiation | 四种能力状态 | mitigate | 在 README 固定定义 `pass`、`fail`、`blocked`、`not-tested` 及 cloud 退出码 0/1/2。 |
| T-Q-OPT-03 | Information disclosure | 命令与环境配置 | mitigate | 只写环境变量名和仓库相对路径；自动扫描秘密赋值、Bearer 值及个人 Windows 路径。 |
</threat_model>

<verification>
先运行定向 pytest，确认 `test_reconstruction_docs_and_examples_are_truthful_and_secret_free` 通过；再执行 README 合同、秘密/个人路径、文档目标、`git diff --check` 和修改范围检查。人工通读新增小节，确认它不与“当前能力矩阵 C01-C07 全部 not-tested”冲突，也不将 fixture、脚本包装器或 cloud-probe 退出 0 描述为七项云能力已验收。
</verification>

<success_criteria>
- 根 README 同时包含 `fixture-probe` 与 `cloud-probe` 的真实 `debugmate.cli ... --output` 命令。
- README 明确定义 `pass`、`fail`、`blocked`、`not-tested`，并解释 cloud 退出码 0/1/2。
- README 明确 fixture 退出 0 时 C01-C07 仍全部 `not-tested`，cloud 也必须逐能力看证据，未宣称任何云端成功。
- 定向文档契约测试和秘密、个人路径、命令目标、diff、范围检查通过。
- 修改范围仅为 `README.md` 和本 quick 目录内 PLAN/SUMMARY；STATE、ROADMAP、REQUIREMENTS、代码、测试及课程交付物无变化。
</success_criteria>

<output>
执行后创建 `.planning/quick/260808-opt-readme-probe-cli/260808-opt-SUMMARY.md`，记录新增命令/状态语义、定向测试结果、秘密/路径扫描和最终修改范围。不得更新 STATE、ROADMAP 或 REQUIREMENTS。
</output>
