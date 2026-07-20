---
quick_id: 260720-ksx
phase: quick-260720-ksx-phase-4-ui-debugmate-windows
plan: 01
type: quick
wave: 1
depends_on: []
autonomous: true
description: 基于 Phase 4 UI 审计优化 DebugMate 学生友好前端并完成 Windows 浏览器验证
mode: quick-full
date: 2026-07-20
files_modified:
  - .planning/phases/04-multimodal-results-ui/04-UI-SPEC.md
  - src/debugmate/ui/presentation.py
  - src/debugmate/ui/app.py
  - tests/ui/test_app.py
  - tests/ui/test_view_state.py
  - tests/ui/test_browser.py
  - output/playwright/after-student-idle-desktop.png
  - output/playwright/after-student-completed-desktop.png
  - output/playwright/after-student-completed-mobile.png
must_haves:
  truths:
    - "学生进入页面后只看到清晰的 1. 生成脱敏预览 → 2. 确认并开始诊断主流程；回放、纠错、重试和技术详情只在其适用状态下渐进披露。"
    - "问题概览由两条显式的纯呈现链路组成：ResultViewState 决定状态、语义颜色与恢复权限，严格验证后的 DiagnosisRecord 决定完成态原因与行动；空闲为中性入门提示，部分/失败保留七字段恢复指导。"
    - "空闲、运行、完成、部分和失败分别使用中性、蓝、绿、琥珀和红色语义，并同时保留图标与文字；页面减少阴影、嵌套卡片和无意义装饰。"
    - "桌面端优先展示结论与下一步，移动端按主操作→状态概览→核心结果→次要技术信息阅读，长内容和 200% 缩放均无 body 级横向滚动。"
    - "诊断逻辑、安全边界、证据身份/下载能力合同、部分与失败真实性、键盘语义及现有公共 elem_id 保持不变。"
  artifacts:
    - path: .planning/phases/04-multimodal-results-ui/04-UI-SPEC.md
      provides: "经审计批准的学生友好标题、编号主流程、渐进披露、状态化 tabs 与响应式结果优先设计合同"
    - path: src/debugmate/ui/presentation.py
      provides: "分别由严格结果状态和已验证诊断记录派生的 typed/pure 呈现合同"
    - path: src/debugmate/ui/app.py
      provides: "编号主流程、渐进披露、状态化样式与桌面/移动端结果优先布局"
    - path: tests/ui/test_app.py
      provides: "状态文案、组件身份、披露条件、回调与安全合同回归"
    - path: tests/ui/test_view_state.py
      provides: "ResultViewState 与严格 DiagnosisRecord 两条纯呈现映射的状态矩阵测试"
    - path: tests/ui/test_browser.py
      provides: "真实 Windows Edge 的桌面/移动端布局、键盘、状态、截图与交互验收"
    - path: output/playwright/after-student-completed-mobile.png
      provides: "改版后 375×812 或等效窄屏的真实完成态证据"
  key_links:
    - from: src/debugmate/ui/presentation.py
      to: src/debugmate/ui/app.py
      via: "ComponentViewModel/render_view_state 只映射 ResultViewState；VerifiedDiagnosisPresentation/render_verified_diagnosis 只映射已严格解析的 DiagnosisRecord，apply_payload 显式组合两者"
      pattern: "render_view_state\(state\)|render_verified_diagnosis\(diagnosis\)"
    - from: .planning/phases/04-multimodal-results-ui/04-UI-SPEC.md
      to: src/debugmate/ui/app.py
      via: "学生友好产品标题、编号 CTA、渐进披露、状态语义颜色、tabs 锁定和移动端结果优先合同"
      pattern: "DebugMate 学习诊断助手|1\. 生成脱敏预览|tabs_enabled"
    - from: src/debugmate/ui/app.py
      to: debugmate.results.service.ResultApplicationService
      via: "保留现有 UiCallbacks、ResultViewState、能力 URL 与 session-owned 下载重验证链路"
      pattern: "download_surface|publish_session_state|resolve_download"
    - from: tests/ui/test_browser.py
      to: src/debugmate/ui/app.py
      via: "Playwright 使用 msedge 运行真实预览→审批→完成、回放、部分/失败、键盘与响应式检查"
      pattern: "launch\(channel=\"msedge\""
---

# Quick Task 260720-ksx Plan

<objective>
把 Phase 4 审计指出的“视觉换肤但流程仍复杂”收敛为学生一眼可懂、状态真实、结果优先的诊断工作台，同时完整保留已经通过验证的证据、安全、无障碍和恢复合同。

Purpose: 初学者无需理解 backend、fixture、run ID 或所有恢复入口，就能沿唯一主路径完成诊断，并先看到“发生了什么、为什么、下一步做什么”。
Output: 状态化纯呈现模型、重排后的 Gradio UI、更新后的单元/浏览器测试，以及 Windows Edge 桌面与移动端真实截图。
</objective>

<context>
@AGENTS.md
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md
@.planning/STATE.md
@.planning/phases/04-multimodal-results-ui/04-UI-REVIEW.md
@.planning/phases/04-multimodal-results-ui/04-UI-SPEC.md
@src/debugmate/ui/presentation.py
@src/debugmate/ui/app.py
@tests/ui/test_app.py
@tests/ui/test_browser.py
@output/playwright/before-desktop.png
@output/playwright/before-mobile.png
@output/playwright/before-completed-desktop-2.png

Locked implementation boundaries:
- 面向学生与初学者，清晰、可读、好看和唯一明显下一步优先于装饰性 macOS 忠实度；不新增营销 hero、AI 插图、渐变玻璃或第三方组件。
- 不改变 `DiagnosisRecord`、`ResultViewState`、结果 manifest、能力 URL、下载重验证、session/lease、回放 allowlist、纠错创建新运行和单并发队列语义。
- 保留当前公共组件 ID，包括 `diagnostic-status`、`accessible-status`、`result-metadata`、`workbench-grid`、`local-preview`、`local-approve`、`replay-action`、`fact-table`、`diagnostic-commands`、`failure-details`、`partial-retry`、`diagnostic-report`、`diagnostic-card`、`diagnostic-audio`、`audio-metadata`、`recap-text`、`citation-table`、`download-metadata`、`download-result`。
- 技术信息是渐进披露而非删除：完整 run/case/result/fixture 身份、事实/证据 ID、后端、命令、安全元数据仍可查看和复制，且 replay/fallback/partial/failed 的真实性不得隐藏。
- 真实截图只能由当前代码在 Windows Edge 中运行生成；不得用生成图片或静态拼图替代浏览器证据。
- 根工作区没有 `.venv`。所有 Python 验证先检查 `X:\PROJECT\校外实训\.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe` 存在且报告 Python 3.13.x，再设置 `$env:PYTHONPATH=(Resolve-Path '.\src').Path` 绑定根工作区源码。解释器缺失时停止并报告，不默认安装或创建环境；只有证明现有环境确实不可恢复且得到额外授权后才可安装。
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 以纯状态合同驱动学生概览、语义颜色与披露条件</name>
  <files>src/debugmate/ui/presentation.py, tests/ui/test_app.py, tests/ui/test_view_state.py</files>
  <behavior>
    - 空闲态返回中性色调和“两步开始”提示，不出现依赖安装、失败或已完成建议。
    - 运行态返回蓝色调、真实 `current_stage` 标签和禁止重复提交提示，不编造百分比。
    - 完成态允许展示从已验证诊断派生的根因/下一步；部分和失败态保留七个恢复字段、缺失产物、retry scope 与安全错误码。
    - replay 与 outcome、fallback 与 outcome 保持正交；颜色之外始终有现有图标和文字标签。
  </behavior>
  <action>先在 `tests/ui/test_app.py` 增加/调整覆盖 idle、running、completed、partial、failed、replay、fallback 的呈现合同测试并确认 RED。保持 `ComponentViewModel` 与 `render_view_state(state: ResultViewState)` 的职责只限于状态：集中提供有限枚举式 `state_tone`、状态概览/恢复文案、secondary disclosure 可见性和 `tabs_enabled`，不向它传入诊断详情，也不让 Gradio 回调通过“文件是否存在”或 DOM 状态猜测 outcome。另在 `presentation.py` 定义不可变的 typed `VerifiedDiagnosisPresentation` 以及纯函数 `render_verified_diagnosis(diagnosis: DiagnosisRecord)`，只从已经严格验证的诊断记录选择类别、置信度、最高可信根因候选和第一个安全检查/修复行动；不得硬编码 ModuleNotFoundError 建议。为该函数先写确定输入→输出与空候选/空行动边界测试；输入类型错误必须 fail closed。保留现有状态 badge、七字段失败详情、下载标签、audio/fallback 元数据和 `tabs_enabled` 语义，不能降低 partial/failed 的真实性。验证前必须执行声明的 worktree Python preflight 和根 `PYTHONPATH` 绑定，缺失即停止，不安装。</action>
  <verify>
    <automated>$python='X:\PROJECT\校外实训\.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe'; if (-not (Test-Path -LiteralPath $python)) { throw 'Verified worktree Python is missing; do not install automatically' }; & $python --version; if ($LASTEXITCODE) { throw 'Python preflight failed' }; $env:PYTHONPATH=(Resolve-Path '.\src').Path; & $python -m pytest -q tests\ui\test_app.py tests\ui\test_view_state.py -k "view or diagnosis or idle or running or completed or partial or failed or replay or fallback"; if ($LASTEXITCODE) { throw 'presentation tests failed' }; & $python -m ruff check src\debugmate\ui\presentation.py tests\ui\test_app.py tests\ui\test_view_state.py; if ($LASTEXITCODE) { throw 'Ruff failed' }</automated>
  </verify>
  <done>所有结果状态都通过纯函数产生可测试、非误导的学生概览和披露合同；空闲态不再像诊断结论，部分/失败的七字段恢复事实没有丢失。</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 重排唯一主流程、渐进披露与结果优先响应式界面</name>
  <files>.planning/phases/04-multimodal-results-ui/04-UI-SPEC.md, src/debugmate/ui/app.py, tests/ui/test_app.py, tests/ui/test_browser.py</files>
  <behavior>
    - 首屏明确显示 `1. 生成脱敏预览` 与 `2. 确认并开始诊断`，第二步在一次性预览 token 生成前禁用，审批消费后仍保持原安全链路。
    - 回放位于默认关闭且键盘可操作的“查看示例” disclosure；纠错只在 verified completed/partial 结果后显示；retry 只在 verified partial 可重试状态显示，失败态仍显示恢复说明但不伪造可执行权限。
    - 原始身份、后端、事实/证据 ID、完整命令和下载元数据进入明确命名的技术详情 disclosure，核心类别、原因、置信度、下一步和报告优先展示。
    - idle/running 时结果 tabs 明确锁定且不能通过鼠标或键盘进入；completed/partial 时由 `ComponentViewModel.tabs_enabled` 原子启用，failed 继续锁定。
    - 1366 宽桌面保留清楚的工作区关系；1024 与 768/375 宽按主流程→状态概览→核心结果→技术详情排序，无 body 横向滚动且不产生嵌套滚动陷阱。
  </behavior>
  <action>先更新 `.planning/phases/04-multimodal-results-ui/04-UI-SPEC.md`，将审计后批准的合同明确写入：产品标题为 `DebugMate 学习诊断助手`，主 CTA 为 `1. 生成脱敏预览` → `2. 确认并开始诊断`，回放/纠错/retry/技术元数据采用状态化渐进披露，颜色为 neutral/blue/green/amber/red，移动端先核心结果后技术详情；同步修正旧“六字段始终可见”、旧 CTA 和仍把 tabs_enabled 视为未接线的冲突描述，保留 D4 安全/证据/原生组件约束。再把结构测试和 Playwright 断言改为该合同并确认 RED，同时继续断言全部既有公共 `elem_id`、组件类型、回调输出身份与安全边界。重组 `build_app()` 的 Gradio `Group`/`Accordion`/`Tabs` 与 `apply_payload()`：`UiCallbacks._details()` 在 `DiagnosisRecord.model_validate_json(..., strict=True)` 成功后调用 Task 1 的 `render_verified_diagnosis()`，将 typed 结果放入 `CallbackPayload`；`apply_payload()` 显式组合 `payload.view` 的状态/权限与 verified diagnosis 的原因/行动，解析失败继续 fail closed。主按钮采用编号文案；idle 只显示中性两步说明；running 显示真实阶段；completed 展示已验证原因、置信度和第一步行动；partial/failed 显示琥珀/红色恢复卡和七字段详情。为 `gr.Tabs` 保存引用并设定稳定 `elem_id="result-tabs"`，初始 `interactive=False`；把 tabs 加入原子输出更新，严格以 `payload.view.tabs_enabled` 控制交互，确保 idle/running/failed 锁定而 completed/partial 启用，并用配置测试和真实鼠标/键盘浏览器测试验证，不能只靠 CSS 假禁用。回放改为默认关闭“查看示例”，技术 backend/fixture/run/case/result、事实表、引用、命令与下载元数据收进明确 disclosure；纠错仅在完成/部分显示，retry 使用 `visible` 与 `interactive` 双重控制且仅 partial 可见。不能删掉原始值、改成截断数据源、把 replay 说成实时成功，或修改能力 URL/manifest 校验。CSS 统一到 4px 间距体系（8/12/16/24）、8px 圆角、1px 边框、最多一层轻阴影；状态色不得静态绑定列。保留 40px 触控目标、2px focus outline、aria-live、原生控件键盘语义、AA 对比度和长 ID 局部换行/滚动。更新旧“macOS 外观”和固定三列几何测试为行为/信息优先级断言，不得放宽下载身份、路径、无 raw traceback/secret、回放真值、partial/failure 或键盘断言。验证使用声明的 worktree Python与根 `PYTHONPATH`，不自动安装。</action>
  <verify>
    <automated>$python='X:\PROJECT\校外实训\.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe'; if (-not (Test-Path -LiteralPath $python)) { throw 'Verified worktree Python is missing; do not install automatically' }; & $python --version; if ($LASTEXITCODE) { throw 'Python preflight failed' }; $env:PYTHONPATH=(Resolve-Path '.\src').Path; & $python -m pytest -q tests\ui\test_app.py tests\ui\test_view_state.py tests\ui\test_callbacks.py; if ($LASTEXITCODE) { throw 'UI contract tests failed' }; & $python -m pytest -q -m browser tests\ui\test_browser.py -k "student or learning or result_tabs or vq_03 or vq_04 or vq_05 or vq_06 or vq_07 or vq_08 or vq_09 or vq_10 or vq_11 or vq_12 or vq_13 or vq_14 or vq_15 or gap_01"; if ($LASTEXITCODE) { throw 'Focused Edge tests failed' }; & $python -m ruff check src\debugmate\ui\app.py src\debugmate\ui\presentation.py tests\ui\test_app.py tests\ui\test_browser.py; if ($LASTEXITCODE) { throw 'Ruff failed' }; git diff --check -- .planning\phases\04-multimodal-results-ui\04-UI-SPEC.md src\debugmate\ui\app.py src\debugmate\ui\presentation.py tests\ui\test_app.py tests\ui\test_browser.py; if ($LASTEXITCODE) { throw 'diff check failed' }</automated>
  </verify>
  <done>页面只有一个醒目的编号主路径；所有次要/专家功能按状态披露；颜色、层级和响应式顺序匹配真实状态，且现有 ID、证据、安全、键盘及恢复合同继续通过。</done>
</task>

<task type="auto">
  <name>Task 3: 在 Windows Edge 中完成桌面、移动端真实截图与交互验收</name>
  <files>tests/ui/test_browser.py, output/playwright/after-student-idle-desktop.png, output/playwright/after-student-completed-desktop.png, output/playwright/after-student-completed-mobile.png</files>
  <action>使用已验证的 worktree Python（先做存在性/版本 preflight，再将 `PYTHONPATH` 绑定根 `src`）、本地 loopback server 和 Playwright `chromium.launch(channel="msedge")` 跑真实浏览器；解释器缺失时停止，不自动安装，不复用旧截图作为通过证据。至少捕获并人工检查：1366×768 idle（中性两步主流程、无伪诊断红卡且 result tabs 锁定）、1366×768 completed（先见原因/下一步与核心结果且 tabs 已启用）、375×812 或设备等效窄屏 completed（主流程→概览→结果→技术详情、标题不尴尬断行），落盘到声明的 `after-student-*.png`。浏览器交互必须真实执行预览→批准→running→完成，分别验证 idle/running tabs 无法由鼠标或键盘激活、完成后 tabs 可操作、按钮从 disabled 到 enabled、aria-live 公告、下载、折叠/展开“查看示例”和技术详情；另验证 partial tabs 启用且 retry 可见，failed tabs 锁定且无不可信结果。再用键盘完成 replay 与 tabs/accordion 导航，并覆盖 200% zoom、长 ID/命令、1024/768 断点。断言每个视口无 body 级横向滚动、无文字/控件重叠、核心 CTA 至少 40px、正常文本对比度 ≥4.5:1、状态不仅依赖颜色。不得把截图加入课程证据或重建 PPT/视频；本 quick task 只验证 UI，课程材料同步需另行授权。</action>
  <verify>
    <automated>$python='X:\PROJECT\校外实训\.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe'; if (-not (Test-Path -LiteralPath $python)) { throw 'Verified worktree Python is missing; do not install automatically' }; & $python --version; if ($LASTEXITCODE) { throw 'Python preflight failed' }; $env:PYTHONPATH=(Resolve-Path '.\src').Path; $env:DEBUGMATE_CAPTURE_UI_REVIEW='1'; & $python -m pytest -q -m browser tests\ui\test_browser.py -k "student or result_tabs or vq_01 or vq_03 or vq_06 or vq_08 or vq_11 or vq_12 or vq_13 or vq_15 or long_content or local_approval"; if ($LASTEXITCODE) { throw 'Playwright Edge verification failed' }; foreach ($p in @('output\playwright\after-student-idle-desktop.png','output\playwright\after-student-completed-desktop.png','output\playwright\after-student-completed-mobile.png')) { if (-not (Test-Path -LiteralPath $p) -or (Get-Item -LiteralPath $p).Length -lt 10000) { throw "Missing real screenshot: $p" } }; & $python -m pytest -q tests\ui\test_app.py tests\ui\test_browser.py; if ($LASTEXITCODE) { throw 'Full UI pytest failed' }; & $python -m ruff check src\debugmate\ui\app.py src\debugmate\ui\presentation.py tests\ui\test_app.py tests\ui\test_browser.py; if ($LASTEXITCODE) { throw 'Ruff failed' }; git diff --check; if ($LASTEXITCODE) { throw 'diff check failed' }</automated>
  </verify>
  <done>Windows Edge 的 idle/completed 桌面与 completed 移动端截图真实存在且经视觉检查；主流程、披露、状态、键盘、partial/failed、zoom、长内容和下载交互均通过自动化。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Result state/diagnosis → presentation | 只有严格验证的 `ResultViewState` 与 `DiagnosisRecord` 可决定状态、原因、建议和恢复信息。 |
| Browser controls → service callbacks | 预览 token、fixture allowlist、纠错 draft、retry identities 均跨越不可信浏览器边界。 |
| Server result → browser media/download | 原生组件只能接收 loopback capability URL 和重新校验后的 manifest 成员，不能接收用户路径。 |
| Runtime UI → screenshot evidence | 截图必须来自当前 Windows Edge 实际运行，不得伪造、回放旧图或泄露敏感值。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q-KSX-01 | Spoofing | replay/completed presentation | mitigate | 保留 replay badge、fixture/source identity 和“离线回放”文案；不把回放描述为实时诊断成功。 |
| T-Q-KSX-02 | Tampering | preview/correction/retry callbacks | mitigate | 不改变一次性 token、单字段 draft、显式确认、新运行身份与 server-owned retry ID；测试非法/重复/跨 session 输入 fail closed。 |
| T-Q-KSX-03 | Information disclosure | technical details and screenshots | mitigate | 技术详情仅展示已验证脱敏值；不渲染绝对路径、raw traceback/provider body、secret 或 session capability；截图使用虚构脱敏案例。 |
| T-Q-KSX-04 | Elevation of privilege | command/download surfaces | mitigate | 命令保持只读原生 Markdown；无 shell/安装回调；下载继续由 session state 重验证并签发 loopback capability URL。 |
| T-Q-KSX-05 | Repudiation | partial/failure/fallback UI | mitigate | 保留安全错误码、七字段恢复、缺失产物、重试范围、backend/fallback 原因和 icon+text 状态，不用颜色或成功文案掩盖降级。 |
| T-Q-KSX-06 | Denial of service | duplicate diagnosis/retry actions | mitigate | running 时禁用 preview/approve/replay/correction/retry，保持 `concurrency_id="debugmate-case"` 与一次触发语义。 |
</threat_model>

<verification>
执行验收必须同时满足：已验证的 worktree Python 存在并以根工作区 `src` 作为 `PYTHONPATH`，该环境下 pytest 与 Ruff 全部通过；真实 Playwright Edge 完成 desktop/mobile 截图和交互；idle/running/failed tabs 锁定、completed/partial tabs 启用；现有 public `elem_id`、manifest/能力 URL/下载身份、回放、纠错、partial/failed/fallback、键盘与 aria-live 断言没有被删除或放宽；UI-SPEC 与实现一致；三张新截图经人工目视确认不存在错误状态色、首屏多主操作竞争、文字裁切或 body 横向滚动。
</verification>

<success_criteria>
- Idle 首屏呈现中性的编号 1→2 主流程，不显示通用依赖修复结论、空闲绿色成功色或静态红色告警卡。
- 完成后概览以已验证诊断的原因、置信度和首个可执行建议为主；partial/failed 则以真实七字段恢复信息为主。
- 回放、纠错、retry、raw IDs/metadata、事实/证据表和完整命令均保留，但只在明确命名的次要 disclosure 或适用状态中出现。
- 桌面和移动端都先到达结果要点；1366、1024、768、375/等效窄屏与 200% zoom 无 body 横向滚动或不可达核心操作。
- 所有既有组件 ID、结果/证据/下载/安全合同、键盘与 accessibility 语义通过回归。
- `ComponentViewModel` 只消费 `ResultViewState`，完成态诊断内容通过独立 typed/pure `VerifiedDiagnosisPresentation` 从严格 `DiagnosisRecord` 派生并在 `apply_payload()` 显式组合；不存在职责混淆或硬编码案例结论。
- UI-SPEC 已更新为学生友好标题、编号 CTA、渐进披露、状态化 tabs 和移动端结果优先的当前合同。
- `tabs_enabled` 已接入真实 Gradio Tabs 交互状态：idle/running/failed 锁定，completed/partial 启用，并有配置及 Edge 鼠标/键盘断言。
- Windows Edge 真实生成并检查三张 `after-student-*.png`，pytest、Ruff 和 `git diff --check` 通过。
</success_criteria>

<output>
执行后创建 `.planning/quick/260720-ksx-phase-4-ui-debugmate-windows/260720-ksx-SUMMARY.md`，并按 quick workflow 更新 `.planning/STATE.md`。SUMMARY 需记录 pytest/Ruff 命令与结果、Edge/Playwright 版本、三个 viewport、三张截图 SHA-256、交互场景、保留的公共 ID/安全合同，以及任何未解决的主观视觉风险。
</output>
