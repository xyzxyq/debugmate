---
quick_id: 260808-nrg
phase: quick-260808-nrg-readme-ui
plan: 01
type: quick
wave: 1
depends_on: []
autonomous: true
description: 修正根目录 README 和项目状态说明，使其与当前本地课程版、最新 UI、验证结果和后续优先级一致
mode: quick
date: 2026-08-08
files_modified:
  - README.md
  - .planning/STATE.md
must_haves:
  truths:
    - "课程项目读者从根 README 能准确理解 DebugMate V0.1 的定位、当前本地演示能力、真实工作流、架构目录、运行测试方法、安全边界、验证证据和明确限制。"
    - "README 明确区分实时本地处理、固定离线回放与尚未验证的 Dify 云端能力，不把本地规则、回放、云端视觉或云端 TTS 写成已完成的实时云端结果。"
    - "STATE 同时保持路线图 6/6 阶段完成，并显式记录 22/24（92%）GSD 计划/摘要文件统计差异、04-11/04-12 缺 SUMMARY 的范围收束原因和唯一 physical-device UAT 债务。"
    - "后续顺序明确以本地课程演示与事实一致性为先，Dify C01-C07 仍为 not-tested，PPTX、视频、字幕和最终截图只在最后统一刷新；本任务不修改这些交付物。"
    - "README 中的仓库路径、PowerShell 命令和 Markdown 本地链接均可在当前工作区验证，且文档不含秘密值、个人绝对路径、过时 Phase 1 当前态或生产就绪宣称。"
  artifacts:
    - path: README.md
      provides: "面向课程读者的 DebugMate V0.1 中文项目入口与可复现运行说明"
    - path: .planning/STATE.md
      provides: "区分功能完成、GSD 记账差异、UAT 债务和后续优先级的当前项目状态"
    - path: .planning/quick/260808-nrg-readme-ui/260808-nrg-SUMMARY.md
      provides: "执行后记录文档修正范围与验证结果的 quick 流程摘要"
  key_links:
    - from: README.md
      to: src/debugmate/ui/serve.py
      via: "快速运行命令使用 python -m debugmate.ui.serve，并说明固定回放是本地 allowlisted evidence 回放"
      pattern: "debugmate\\.ui\\.serve"
    - from: README.md
      to: platform/dify/capability-matrix.json
      via: "当前限制引用 C01-C07 全部 not-tested 的事实口径"
      pattern: "C01.*C07|not-tested"
    - from: .planning/STATE.md
      to: .planning/ROADMAP.md
      via: "STATE 保持路线图 6/6 阶段完成语义，同时单列 GSD 22/24 文件统计差异"
      pattern: "6/6|22/24|92%"
---

# Quick Task 260808-nrg Plan

<objective>
将根目录 README 和项目状态改为与当前 DebugMate V0.1 本地课程演示版、最新学生诊断 UI、已完成验证和剩余边界一致的单一事实口径。

Purpose: 消除根 README 仍停留在 Phase 1、STATE 将功能完成和 GSD 文件记账混为一谈的问题，让读者能按真实路径运行、验证并理解回放/云端边界。
Output: 更新后的 `README.md`、`.planning/STATE.md`，以及执行完成后生成的 quick `SUMMARY.md`；不触碰代码、测试、路线图、需求或课程交付物。
</objective>

<context>
@AGENTS.md
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md
@README.md
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/quick/260721-uf9-debugmate/260721-uf9-SUMMARY.md
@.planning/quick/260721-uf9-debugmate/260721-uf9-VERIFICATION.md
@docs/course/README.md
@pyproject.toml
@platform/dify/capability-matrix.json
@.planning/phases/04-multimodal-results-ui/04-UAT.md

Locked boundaries:
- 只修改 `README.md` 与 `.planning/STATE.md`；执行后按 quick workflow 创建本目录的 `260808-nrg-SUMMARY.md`。不得修改 `.planning/ROADMAP.md`、`.planning/REQUIREMENTS.md`、任何源码/测试、PPTX、视频、字幕、截图或其他交付物。
- 以当前 `HEAD 33dd25c`、`master` 与 `origin/master` 同步且任务开始前工作区洁净为执行基线；仓库可能出现他人并行改动，只处理本计划文件，绝不回滚或覆盖无关变化。
- 路线图 6/6 阶段完成是功能范围结论；GSD 22/24（92%）是计划/摘要文件统计，缺口仅为 Phase 4 的 `04-11-SUMMARY.md`、`04-12-SUMMARY.md`，属于 V0.1 范围收束后的记账差异，不得写成核心功能未完成。
- 最新验证基线为：`tests/ui/test_app.py` 34 passed；显式 Edge 浏览器套件 39 passed、7 environment-gated skipped、0 failed；quick verifier 5/5 must-haves。只把这些写成有日期/来源的当前记录，不承诺未来复跑仍保持固定计数。
- `platform/dify/capability-matrix.json` 中 C01-C07 全部为 `not-tested`。不得宣称 Dify、云端视觉理解、云端检索或云端 TTS 已完成、已验收或已用于当前回放结果。
- 唯一显式 UAT 债务是 Local SAPI 中文复盘的人耳听感检查，`blocked_by: physical-device`；机器证据只证明 MP3 可解码、非静音等客观属性，不替代主观听验。
- 用户锁定顺序：PPTX、视频、字幕、最终截图等统一放到最后处理。本任务不得刷新或改写任何最终材料。
</context>

<tasks>

<task type="auto">
  <name>Task 1: 将根 README 重写为真实的 V0.1 本地课程演示入口</name>
  <files>README.md</files>
  <action>用中文重构 `README.md`，面向首次看到仓库的课程老师、同学和复现实验者，按自然阅读顺序完整覆盖：项目定位；当前 V0.1 本地演示能力；从输入校验/本地脱敏/显式确认到事实抽取、规则/知识引用、严格 `DiagnosisRecord`、同源 Markdown/PNG/MP3、Gradio 展示与 ZIP evidence 的真实工作流；本地 Python/Pydantic/Pillow/Gradio 与可选 Dify 层的架构分工；关键目录；Python 3.13 环境创建、`pip install -e ".[dev]"`、`python -m debugmate.ui.serve` 的快速运行；普通 UI 与显式 Edge 测试命令；固定回放的用途和真值标签；安全边界；2026-08-08 的 34 passed、39 passed/7 environment-gated skipped/0 failed、5/5 must-haves 验证记录；当前限制；后续工作顺序。快速运行必须允许新环境使用根 `.venv`，同时可注明当前验证记录来自已核验 Python 3.13 环境，不能把本机 worktree 虚拟环境路径写成所有读者都必须存在的公共安装步骤。明确说明固定回放来自仓库 allowlist 的脱敏证据包，本地规则/回放不等于实时 Dify 调用；Dify C01-C07 均为 `not-tested`，云端视觉、检索、工作流与 TTS 是待实测增强；V0.1 不是公网部署、生产系统或自动修复工具。路径只使用仓库相对路径，秘密只写环境变量名或 `.env.example` 概念，不写任何值、个人目录或本机绝对路径。后续顺序先保持本地演示/证据与文档一致，再按需完成云端能力实测与人耳听验，最后统一刷新 PPTX、视频、字幕和最终截图；不得暗示本任务会更新交付物。删除所有把 Phase 1 或未来 Phase 2/4 当作当前状态的过时文案，但保留能力探针的历史/高级入口时必须清楚标注其与当前本地演示的关系。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $readme=Get-Content -LiteralPath 'README.md' -Raw -Encoding UTF8; $required=@('项目定位','V0.1','真实工作流','快速运行','测试','固定回放','安全边界','当前验证','当前限制','后续'); foreach($item in $required){ if($readme -notmatch [regex]::Escape($item)){ throw "README missing required section/content: $item" } }; if($readme -match '(?m)^## Phase 1\s*$|Phase 2 才会|Phase 4 才会'){ throw 'README still describes an obsolete phase as current' }; if($readme -notmatch 'not-tested' -or $readme -notmatch '34 passed' -or $readme -notmatch '39 passed' -or $readme -notmatch '7.+skipped' -or $readme -notmatch '5/5'){ throw 'README verification/cloud boundary is incomplete' }; if($readme -notmatch '固定回放.+(不等于|不是).+(Dify|云端)|回放.+(不等于|不是).+(实时|云端)'){ throw 'Replay truth boundary is missing' }; if($readme -match '(?i)(api[_ -]?key|token|secret|password)\s*[:=]\s*[\x22\x27]?[A-Za-z0-9_\-]{8,}' -or $readme -match '[A-Z]:\\Users\\'){ throw 'README may contain a secret value or personal absolute path' }; $paths=@('src\debugmate\ui\serve.py','platform\dify\capability-matrix.json','fixtures\replay\index.json','docs\course\README.md','tests\ui\test_app.py','tests\ui\test_browser.py'); foreach($path in $paths){ if(-not (Test-Path -LiteralPath $path -PathType Leaf)){ throw "README target missing: $path" } }; if($readme -notmatch 'debugmate\.ui\.serve' -or $readme -notmatch 'pytest.+tests[\\/]ui[\\/]test_app\.py' -or $readme -notmatch 'pytest.+-m browser.+tests[\\/]ui[\\/]test_browser\.py'){ throw 'README run/test commands do not match verified entry points' }</automated>
  </verify>
  <done>根 README 不再停留在 Phase 1；课程读者可准确理解、运行和测试当前本地 V0.1，并能明确区分本地 live、固定回放、规则结果和未实测云端能力。</done>
</task>

<task type="auto">
  <name>Task 2: 统一 STATE 状态口径并执行文档边界验收</name>
  <files>.planning/STATE.md</files>
  <action>更新 `.planning/STATE.md` frontmatter 与正文，使状态按两个维度表达：路线图功能范围保持 `status: complete`、6/6 phases complete；GSD 计划/摘要文件统计单列为 22/24（92%），并明确缺少 `04-11-SUMMARY.md`、`04-12-SUMMARY.md` 是 V0.1 范围收束/记账差异，不是核心功能缺口。不要继续用无法解释的 `26/26 plans completed` 作为唯一进度口径；frontmatter 中如保留 `total_plans/completed_plans/percent`，应与 24/22/92 一致，同时正文必须紧邻解释 6/6 完成语义。将当前位置、last activity/stopped_at 更新为 README/STATE 真值同步；记录最新普通 UI、显式 Edge 和 5/5 must-have 验证；记录 C01-C07 全部 `not-tested`；把 UAT 仅保留为 Local SAPI recap 的 `physical-device` 人耳听感债务。现有 PPTX、视频、字幕和截图即使文件存在，也不得描述为已随最新 UI 刷新；若保留清单，标记为历史/待最后统一刷新。新增本 quick task 的 `Quick Tasks Completed` 行，状态和 commit 使用执行阶段真实值（提交前可写 `this commit`），链接指向 `./quick/260808-nrg-readme-ui/`。明确后续顺序：先维护本地课程演示与事实证据一致；再按需实测 Dify C01-C07；安排 physical-device 人耳听验；最后才更新 PPTX、视频、字幕和最终截图。随后执行限定范围验收：验证 README 中相对 Markdown 链接和关键代码路径存在；扫描 README/STATE 的秘密值、个人绝对路径和过时 Phase 1 当前态；核对 Dify 矩阵仍是 7 个 `not-tested`；核对 Git diff 只包含 `README.md`、`.planning/STATE.md` 与本 quick 目录内 PLAN/SUMMARY，且 ROADMAP、REQUIREMENTS、代码、测试及交付物没有变化。不得为了让链接通过而创建、移动或修改范围外文件。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $state=Get-Content -LiteralPath '.planning\STATE.md' -Raw -Encoding UTF8; foreach($token in @('6/6','22/24','92%','04-11-SUMMARY.md','04-12-SUMMARY.md','not-tested','physical-device','260808-nrg','PPTX','视频','字幕','最终截图')){ if($state -notmatch [regex]::Escape($token)){ throw "STATE missing required status token: $token" } }; if($state -notmatch '(?s)6/6.+(完成|complete)' -or $state -notmatch '(?s)22/24.+(记账|统计|SUMMARY|摘要)'){ throw 'STATE does not distinguish phase completion from GSD file statistics' }; $matrix=Get-Content -LiteralPath 'platform\dify\capability-matrix.json' -Raw -Encoding UTF8 | ConvertFrom-Json; if($matrix.capabilities.Count -ne 7 -or @($matrix.capabilities | Where-Object status -ne 'not-tested').Count -ne 0){ throw 'Dify capability truth changed; do not claim cloud completion' }; foreach($doc in @('README.md','.planning\STATE.md')){ $text=Get-Content -LiteralPath $doc -Raw -Encoding UTF8; if($text -match '(?i)(api[_ -]?key|token|secret|password)\s*[:=]\s*[\x22\x27]?[A-Za-z0-9_\-]{8,}' -or $text -match '[A-Z]:\\Users\\'){ throw "Potential secret or personal path in $doc" }; foreach($match in [regex]::Matches($text,'\[[^\]]+\]\((?!https?://|#|mailto:)([^)]+)\)')){ $target=$match.Groups[1].Value.Split('#')[0].Trim('<','>'); if($target -and -not (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $doc) $target))){ throw "Broken local Markdown link in ${doc}: $target" } } }; $allowed=@('README.md','.planning/STATE.md','.planning/quick/260808-nrg-readme-ui/260808-nrg-PLAN.md','.planning/quick/260808-nrg-readme-ui/260808-nrg-SUMMARY.md'); $changed=@(git status --short | ForEach-Object { $_.Substring(3).Replace('\','/') }); $unexpected=@($changed | Where-Object { $_ -notin $allowed }); if($unexpected){ throw "Out-of-scope changes detected: $($unexpected -join ', ')" }; git diff --check -- README.md .planning/STATE.md .planning/quick/260808-nrg-readme-ui; if($LASTEXITCODE){ throw 'Markdown diff check failed' }</automated>
  </verify>
  <done>STATE 清楚区分 6/6 功能完成与 22/24 GSD 记录统计，记录唯一听验债务和真实后续顺序；两份文档的路径、链接、秘密扫描、Dify 边界和修改范围全部通过自动验收。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| 历史规划/验证记录 → 当前文档 | 旧 Phase、UAT 和交付物记录可能过期，只有当前指定事实源可支撑 README/STATE 的现在时结论。 |
| 本地回放/规则 → 云端能力声明 | 仓库回放与本地规则可验证，但不能越界证明 Dify、云视觉、云检索或云 TTS。 |
| 文档示例 → 读者本机 | 路径、命令、链接与环境变量示例会被读者执行或复制，必须相对、存在且不含秘密值。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q-NRG-01 | Spoofing | README 云端/回放状态 | mitigate | 明确标注固定回放、本地规则与 C01-C07 `not-tested`，禁止把回放包装为实时云端成功。 |
| T-Q-NRG-02 | Tampering | STATE 完成度口径 | mitigate | 同时记录 6/6 功能完成和 22/24 文件统计，并点名两份缺失 SUMMARY 及范围收束原因。 |
| T-Q-NRG-03 | Information disclosure | README/STATE 命令与路径 | mitigate | 只写相对路径和环境变量名；自动扫描秘密赋值模式及个人 Windows 绝对路径。 |
| T-Q-NRG-04 | Repudiation | 验证结果陈述 | mitigate | 每项计数绑定 2026-08-08 的 SUMMARY/VERIFICATION 记录，跳过项标注 environment-gated，UAT 人耳听验保留 blocked_by physical-device。 |
| T-Q-NRG-05 | Elevation of privilege | 文档运行示例 | accept | 文档仅包含创建虚拟环境、安装项目、启动本地 UI 和运行测试；项目仍不自动执行模型生成的修复命令。 |
</threat_model>

<verification>
完成前执行 Task 1 与 Task 2 的自动检查，并人工通读 README/STATE 一次，确认中文叙述面向课程读者、章节顺序自然、没有将历史材料或云端能力写成当前已验收成果。`git diff --check` 必须通过；`git status --short` 只允许 `README.md`、`.planning/STATE.md` 与 `.planning/quick/260808-nrg-readme-ui/` 下的 PLAN/SUMMARY。确认 `.planning/ROADMAP.md`、`.planning/REQUIREMENTS.md`、`src/`、`tests/`、`deliverables/`、字幕、视频与截图均无 diff。README 的本地链接和关键命令目标必须真实存在，但本任务是文档真值同步，不重复运行约 14 分钟的完整 Edge 套件；应引用已验证的 2026-08-08 记录，不把未复跑写成新测试结果。
</verification>

<success_criteria>
- 根 README 已从 Phase 1 说明升级为完整、中文、可运行的 DebugMate V0.1 本地课程版入口。
- README 覆盖定位、能力、工作流、架构/目录、快速运行、测试、固定回放、安全、验证、限制与后续顺序。
- README/STATE 都清楚说明本地规则与固定回放不是 Dify 实时结果，C01-C07 全部仍为 `not-tested`。
- STATE 保持路线图 6/6 阶段完成，同时诚实记录 22/24（92%）GSD 文件统计和两份 Phase 4 SUMMARY 缺失原因。
- 唯一 UAT 债务 `Local SAPI recap human listening quality` 以 `blocked_by: physical-device` 保留，不被机器媒体检查冒充完成。
- PPTX、视频、字幕与最终截图被明确排在最后统一刷新，本任务未修改任何交付物或范围外文件。
</success_criteria>

<output>
执行后创建 `.planning/quick/260808-nrg-readme-ui/260808-nrg-SUMMARY.md`，记录 README/STATE 修正内容、路径/命令/链接/秘密/过时文案检查结果、最终 Git 修改范围和任何未能自动验证的事项。按 quick workflow 更新 STATE 的 Quick Tasks Completed 行；不更新 ROADMAP 或 REQUIREMENTS。
</output>
