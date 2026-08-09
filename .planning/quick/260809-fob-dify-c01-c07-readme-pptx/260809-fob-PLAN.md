---
quick_id: 260809-fob
phase: quick-260809-fob-dify-c01-c07-readme-pptx
plan: 01
type: quick
wave: 1
depends_on: []
autonomous: true
description: 固化 Dify C01-C07 真实证据并同步能力矩阵、README 与项目状态，不触碰课程交付物
mode: quick-full
date: 2026-08-09
files_modified:
  - .gitignore
  - evidence/dify-live/README.md
  - evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/diagnosis.json
  - evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/dify-upload.json
  - evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/input.redacted.json
  - evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/manifest.json
  - evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/probe-results.json
  - evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/recap.json
  - evidence/dify-live/2026-08-09/tts/dify-recap.mp3
  - evidence/dify-live/2026-08-09/tts/tts-evidence.json
  - platform/dify/capability-matrix.json
  - tests/test_probe_cli.py
  - platform/dify/README.md
  - README.md
  - .planning/STATE.md
must_haves:
  truths:
    - "能力矩阵中每个 pass 都指向仓库内可提交、无秘密、可复算 SHA-256 的真实 Dify 执行证据；任何未满足该门禁的能力保持 not-tested 或准确的受限状态。"
    - "C01、C02、C05 的结论来自 2026-08-08 已通过 verify-bundle 的 live cloud-probe；C03、C04、C06 不因 DSL 节点存在、输出字段存在或历史文字记录而被推断为 pass。"
    - "C07 只有在现有 cloud+tts gate 真实重跑成功、MP3 经 ffprobe 验证并版本化后才为 pass；否则保留 not-tested/准确状态且不伪造制品。"
    - "根 README、Dify README 与 STATE 对 C01-C07 的逐项口径和证据路径一致，同时继续声明本地规则、fixture 与固定回放不能替代云端实测。"
    - "PPTX、视频、字幕和最终截图保持逐字节不变，且仓库中不新增 API key、Bearer 值或个人绝对路径。"
    - "所有 pass 引用的 evidence_path 不受 ignore 规则遮蔽，并已进入 Git tracked files，而不是仅存在于本机工作树。"
  artifacts:
    - path: evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/manifest.json
      provides: "C01/C02/C05 live cloud-probe 的版本化原子 bundle 清单"
    - path: .gitignore
      provides: "仅放行 evidence/dify-live/** 的窄范围版本化规则，其他 evidence 临时产物继续忽略"
    - path: evidence/dify-live/2026-08-09/tts/tts-evidence.json
      provides: "C07 真实 Dify TTS 请求与 MP3 媒体校验的无秘密元数据"
    - path: platform/dify/capability-matrix.json
      provides: "C01-C07 的证据路径、SHA-256 与逐项真实状态"
    - path: tests/test_probe_cli.py
      provides: "pass 状态必须绑定存在文件和匹配 SHA-256 的自动回归门禁"
    - path: README.md
      provides: "面向复现者的当前 Dify 能力与本地/云端边界说明"
    - path: .planning/STATE.md
      provides: "与版本化证据一致的项目状态和 quick task 记录"
  key_links:
    - from: platform/dify/capability-matrix.json
      to: evidence/dify-live/
      via: "每个 pass 项的 evidence_path 指向真实文件，sha256 等于该文件的实际 SHA-256"
      pattern: "evidence/dify-live/.+sha256"
    - from: tests/test_probe_cli.py
      to: platform/dify/capability-matrix.json
      via: "测试解析矩阵、解析仓库相对证据路径并复算文件哈希"
      pattern: "capability-matrix|sha256"
    - from: README.md
      to: platform/dify/capability-matrix.json
      via: "文档逐项复述矩阵状态并链接版本化 live evidence 根目录"
      pattern: "C01|C02|C03|C04|C05|C06|C07"
---

# Quick Task 260809-fob Plan

<objective>
把已完成的 Dify 现场验证从忽略目录和临时测试输出固化为可提交、可复算、无秘密的证据，并让能力矩阵、两份 README 与项目 STATE 使用同一套逐能力事实口径。

Purpose: 当前 `.artifacts/dify-cloud-probe-live2` 已真实证明 C01/C02/C05，live TTS gate 已具备真实 C07 重跑能力，但版本化矩阵仍全为 `not-tested`，README 仍声称没有成功 cloud-probe，STATE 又包含更靠前的现场结论。必须先建立可审计证据链，再更新公开口径，避免高估 C03/C04/C06 或把临时目录当事实源。
Output: 版本化 Dify live evidence、经过文件存在性与哈希约束的 C01-C07 能力矩阵、同步后的 `platform/dify/README.md`、根 `README.md`、`.planning/STATE.md`，以及执行后生成的 quick SUMMARY。
</objective>

<context>
@AGENTS.md
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
@.planning/STATE.md
@platform/dify/capability-matrix.json
@platform/dify/README.md
@platform/dify/app.dsl.yml
@README.md
@src/debugmate/evidence.py
@src/debugmate/probe.py
@tests/test_probe_cli.py
@tests/results/test_tts_live.py
@.planning/debug/resolved/cloud-probe-c05-semantic-mismatch.md
@.planning/debug/resolved/live-dify-tts-evidence-serialization.md

Locked evidence conclusions and boundaries:
- 已保存的 live bundle `.artifacts/dify-cloud-probe-live2/case_d2c4d21672c14d9bad7f7fe95ee86653` 经既有 `verify-bundle` 记录为 zero issues；其 `probe-results.json` 只证明 C01/C02/C05 为 `pass`，C03/C04/C06/C07 为 `not-tested`。复制到版本化目录后必须再次执行 `verify-bundle`，不得编辑 bundle 内 JSON 来改变历史结果。
- C03 需要真实截图视觉抽取证据；C04 需要真实 retrieval chunk/来源元数据证据；C06 需要真实导出→重导入→复跑的版本化执行记录。`app.dsl.yml` 中存在 vision/retrieval 节点、DSL 已提交或 STATE 中记录过人工现场观察，均不能单独满足 `pass` 门禁。本任务没有对应可复算文件时，三项保持 `not-tested`。
- C07 必须通过 `tests/results/test_tts_live.py::test_live_dify_tts_gate` 对正式 Dify `/text-to-audio` 路径重新执行；只有测试非 skip 且通过、保存的 MP3 通过 `ffprobe`、元数据不含 recap 原文或秘密值、版本化文件 SHA-256 可复算时才标 `pass`。若环境/额度阻止重跑，不请求用户手工操作、不充值、不沿用口头结论，保留 `not-tested` 或记录准确受阻状态。
- C01 与 C02 可以共享同一真实 `dify-upload.json` 证据文件；C05 必须指向严格验证后保存的 `diagnosis.json`；C07 指向版本化 MP3，并由同目录 `tts-evidence.json` 记录后端、媒体类型、codec、channels、bytes、duration、SHA-256、测试命令和 UTC 时间，不保存原始 recap 文本、API key、Authorization header 或完整 HTTP body。
- 只允许修改 frontmatter `files_modified` 所列文件和执行后本 quick 目录的 SUMMARY。保留所有无关工作区变化；不得修改 `.planning/PROJECT.md`、`.planning/REQUIREMENTS.md`、`.planning/ROADMAP.md`、产品代码、DSL、PPTX、视频、字幕、已有/最终截图或其他课程交付物。
- `.gitignore` 当前以 `evidence/*` 忽略整个证据根目录；必须只追加 `!evidence/dify-live/` 与 `!evidence/dify-live/**`（或语义完全等价且不扩大的规则）来放行本任务证据。不得放行 `evidence/` 下其他历史、课程截图或临时目录。
</context>

<tasks>

<task type="auto">
  <name>Task 1: 固化并复验真实 cloud-probe 与 Dify TTS 证据</name>
  <files>.gitignore, evidence/dify-live/README.md, evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/diagnosis.json, evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/dify-upload.json, evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/input.redacted.json, evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/manifest.json, evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/probe-results.json, evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/recap.json, evidence/dify-live/2026-08-09/tts/dify-recap.mp3, evidence/dify-live/2026-08-09/tts/tts-evidence.json</files>
  <action>先在 `.gitignore` 的 `evidence/*` 后添加窄范围反向规则 `!evidence/dify-live/` 与 `!evidence/dify-live/**`，只允许本任务 live evidence 被 Git 发现；不得放行整个 `evidence/`、课程截图或其他历史证据。用 `git check-ignore -v`/`git status --short --untracked-files=all` 确认新路径不再 ignored 且会出现在可提交集合。然后用既有 `debugmate.cli verify-bundle` 验证忽略目录中的 live2 bundle；只有结果 `ok: true` 且逐项恰为 C01/C02/C05 `pass`、C03/C04/C06/C07 `not-tested` 时，才把该 case 目录的六个 JSON 文件原样复制到 `evidence/dify-live/2026-08-08/cloud-probe/`，复制后再次执行同一 bundle 验证并逐文件核对原/目标 SHA-256 一致。随后以专用 `.artifacts/dify-tts-capture` 作为 pytest `--basetemp` 运行现有 `test_live_dify_tts_gate`；确认不是 skip、真实测试通过后，从该测试唯一生成的 `dify.mp3` 固化为 `evidence/dify-live/2026-08-09/tts/dify-recap.mp3`。用项目 `probe_mp3` 或 `ffprobe` 复验其 codec、单声道、时长、字节数与 SHA-256，并创建确定性、UTF-8 的 `tts-evidence.json`，只记录无秘密的媒体元数据、`backend=dify`、`content_type=audio/mpeg`、正式 live gate 名称/命令、UTC 执行时间和 MP3 相对路径/哈希；不得写 recap 原文、请求头、环境变量值、用户目录或 raw audio 的 JSON 编码。创建 `evidence/dify-live/README.md`，简要列出证据来源、复验命令和明确状态边界。若 live TTS 门禁 skip/失败，不创建伪造 MP3/metadata，后续 C07 保持 `not-tested` 或按真实阻塞状态记录；不要通过人工截图或口头确认补洞。Task 1 的原子提交必须包含 `.gitignore` 和全部已生成 `evidence/dify-live/**` 文件，使 Task 2 可用 `git ls-files` 证明它们已 tracked。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; $bundle=(Resolve-Path -LiteralPath 'evidence\dify-live\2026-08-08\cloud-probe\case_d2c4d21672c14d9bad7f7fe95ee86653').Path; & $python -m debugmate.cli verify-bundle $bundle; if($LASTEXITCODE){ throw 'Versioned live cloud bundle verification failed' }; $report=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $bundle 'probe-results.json') | ConvertFrom-Json; $states=@{}; foreach($item in $report.capabilities){ $states[$item.capability_id]=$item.status }; foreach($id in @('C01','C02','C05')){ if($states[$id] -ne 'pass'){ throw "$id must be pass in the preserved historical probe" } }; foreach($id in @('C03','C04','C06','C07')){ if($states[$id] -ne 'not-tested'){ throw "$id was overstated in the historical probe" } }; $tts='evidence\dify-live\2026-08-09\tts\dify-recap.mp3'; $meta='evidence\dify-live\2026-08-09\tts\tts-evidence.json'; if((Test-Path -LiteralPath $tts) -xor (Test-Path -LiteralPath $meta)){ throw 'C07 evidence is incomplete' }; if(Test-Path -LiteralPath $tts){ & ffprobe -v error -show_entries stream=codec_name,channels -show_entries format=duration,size -of json $tts | Out-Null; if($LASTEXITCODE){ throw 'Versioned Dify MP3 failed ffprobe' }; $m=Get-Content -Raw -Encoding UTF8 -LiteralPath $meta | ConvertFrom-Json; $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $tts).Hash.ToLowerInvariant(); if($m.sha256 -ne $actual -or $m.backend -ne 'dify' -or $m.content_type -ne 'audio/mpeg'){ throw 'C07 metadata does not bind the verified MP3' } }; $ignored=@(git check-ignore -- 'evidence/dify-live/README.md' 'evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/manifest.json' 2>$null); if($ignored){ throw "Live evidence is still ignored: $($ignored -join ', ')" }; $visible=@(git status --short --untracked-files=all -- 'evidence/dify-live'); $tracked=@(git ls-files -- 'evidence/dify-live'); if(-not $visible -and -not $tracked){ throw 'Live evidence is neither tracked nor visible as versionable files' }; rg -n -i '(Bearer\s+[A-Za-z0-9._-]+|api[_ -]?key\s*[:=]\s*["''][^"'']+|token\s*[:=]\s*["''][^"'']+|[A-Z]:\\Users\\)' evidence/dify-live; if($LASTEXITCODE -eq 0){ throw 'Versioned Dify evidence may contain a secret or personal path' } elseif($LASTEXITCODE -ne 1){ throw 'Evidence secret scan failed to run' }</automated>
  </verify>
  <done>C01/C02/C05 的 live bundle 在版本化路径再次通过零问题验证且哈希未改变；C07 若门禁成功则拥有经 ffprobe 与 metadata SHA 双重绑定的版本化 MP3，否则没有伪造制品；全部证据无秘密、无个人路径并附可复现说明。</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 用证据文件和实算哈希更新 C01-C07 能力矩阵</name>
  <files>platform/dify/capability-matrix.json, tests/test_probe_cli.py</files>
  <behavior>
    - "任何 capability status=pass 时，evidence_path 必须是仓库内存在的普通文件，sha256 必须等于文件实算 SHA-256。"
    - "C01/C02/C05 绑定 Task 1 固化的 live cloud bundle 文件并为 pass。"
    - "C03/C04/C06 保持 not-tested 且 evidence_path/sha256 为 null，不从 DSL 或 C05 输出推断执行。"
    - "C07 仅在 Task 1 固化且验证真实 MP3 后为 pass；否则保持准确的非 pass 状态与空证据引用。"
  </behavior>
  <action>先扩展 `test_capability_matrix_has_exact_ids_and_no_unproven_pass`：除保持 C01-C07 精确顺序外，对每个 `pass` 使用安全的仓库相对路径解析，拒绝绝对路径、`..`、目录和缺失文件，用 `git check-ignore` 证明路径未被忽略、用 `git ls-files --error-unmatch` 证明路径已经 tracked，并用 Python `hashlib.sha256` 复算内容，要求与矩阵小写十六进制哈希完全相同；对 `not-tested` 要求 `evidence_path` 与 `sha256` 都为 null。先运行测试观察旧矩阵不满足新证据期望，再更新 `capability-matrix.json`：C01/C02 指向版本化 `dify-upload.json`，C05 指向版本化 `diagnosis.json`，三项使用实际文件哈希；C03/C04/C06 维持 `not-tested`。C07 只有 Task 1 的 MP3 与 metadata 门禁全部通过时才指向版本化 MP3 并填实际哈希，否则维持准确的非 pass 状态。不得把 `app.dsl.yml`、debug markdown、STATE 文本或 fixture 文件用作能力通过证据，也不得手填未复算的摘要。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; & $python -m pytest -q tests\test_probe_cli.py::test_capability_matrix_has_exact_ids_and_no_unproven_pass tests\test_probe_cli.py::test_reconstruction_docs_and_examples_are_truthful_and_secret_free; if($LASTEXITCODE){ throw 'Capability evidence and documentation contracts failed' }; $matrix=Get-Content -Raw -Encoding UTF8 -LiteralPath 'platform\dify\capability-matrix.json' | ConvertFrom-Json; if(($matrix.capabilities.capability_id -join ',') -ne 'C01,C02,C03,C04,C05,C06,C07'){ throw 'Capability IDs/order changed' }; foreach($item in $matrix.capabilities){ if($item.status -eq 'pass'){ if(-not $item.evidence_path -or -not $item.sha256){ throw "$($item.capability_id) lacks pass evidence" }; $ignored=@(git check-ignore -- $item.evidence_path 2>$null); if($ignored){ throw "$($item.capability_id) evidence is ignored" }; git ls-files --error-unmatch -- $item.evidence_path 2>$null | Out-Null; if($LASTEXITCODE){ throw "$($item.capability_id) evidence is not tracked" }; $p=(Resolve-Path -LiteralPath $item.evidence_path).Path; $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant(); if($actual -ne $item.sha256){ throw "$($item.capability_id) hash mismatch" } } elseif($item.status -eq 'not-tested' -and ($null -ne $item.evidence_path -or $null -ne $item.sha256)){ throw "$($item.capability_id) has evidence attached to not-tested" } }; foreach($id in @('C03','C04','C06')){ $entry=$matrix.capabilities | Where-Object capability_id -eq $id; if($entry.status -ne 'not-tested'){ throw "$id cannot pass without independently versioned evidence" } }</automated>
  </verify>
  <done>矩阵的每个 pass 都由自动测试证明其证据文件存在且 SHA-256 匹配；C01/C02/C05 如实通过，C03/C04/C06 保持 not-tested，C07 只随真实版本化 TTS 证据通过。</done>
</task>

<task type="auto">
  <name>Task 3: 同步 Dify README、根 README 与 STATE 的证据口径</name>
  <files>platform/dify/README.md, README.md, .planning/STATE.md</files>
  <action>以最终 `capability-matrix.json` 为唯一逐项状态源同步三份文档。`platform/dify/README.md` 删除“真实 DSL 仍是占位”的过时说法，明确 `app.dsl.yml` 是已版本化的真实导出、`.example` 才是结构样例；新增版本化 live evidence 目录、cloud bundle/MP3 复验命令和当前逐项状态表，并说明 C03/C04/C06 为何仍不能从节点配置、知识引用字段或历史重导入观察推断通过。根 `README.md` 将“Dify 当前尚未实测”“没有成功 cloud-probe”“矩阵七项全 not-tested”等过时句子替换为最终矩阵事实：C01/C02/C05 已由版本化 cloud bundle 支撑，C07 仅在 Task 1 成功时写为已由版本化 live MP3 支撑，其他项保持准确状态；保留 fixture 成功不证明云能力、cloud-probe 退出 0 不等于七项全通过、本地规则/回放不等于实时 Dify、V0.1 非生产系统等边界。`.planning/STATE.md` 更新 `last_updated`、`last_activity`、当前验证基线、Next Order 和 Quick Tasks Completed，明确区分“曾现场观察”与“当前可复算能力矩阵”：没有版本化执行证据的 C03/C04/C06 不写成 pass，并删除已完成 Local SAPI 人耳听验仍待安排的过时后续项。三处只链接仓库相对路径和环境变量名，不写密钥值、个人路径或无法复现的绝对结论；保留课程交付物冻结段落，绝不修改 PPTX、MP4、SRT 或任何截图。</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; & $python -m pytest -q tests\test_probe_cli.py; if($LASTEXITCODE){ throw 'Probe and documentation suite failed' }; & $python -m ruff check tests\test_probe_cli.py; if($LASTEXITCODE){ throw 'Ruff failed' }; $matrix=Get-Content -Raw -Encoding UTF8 -LiteralPath 'platform\dify\capability-matrix.json' | ConvertFrom-Json; $root=Get-Content -Raw -Encoding UTF8 -LiteralPath 'README.md'; $dify=Get-Content -Raw -Encoding UTF8 -LiteralPath 'platform\dify\README.md'; $state=Get-Content -Raw -Encoding UTF8 -LiteralPath '.planning\STATE.md'; foreach($id in @('C01','C02','C03','C04','C05','C06','C07')){ if($root -notmatch $id -or $dify -notmatch $id){ throw "$id missing from synchronized documentation" } }; foreach($text in @($root,$dify,$state)){ if($text -match '(?i)(Bearer\s+[A-Za-z0-9._-]+|api[_ -]?key\s*[:=]\s*["''][^"'']+|token\s*[:=]\s*["''][^"'']+|[A-Z]:\\Users\\)'){ throw 'Documentation contains a secret value or personal path' } }; if($root -match '当前能力矩阵仍是 C01.C07 全部.*not-tested' -or $root -match '本仓库当前没有已成功执行该命令的声明'){ throw 'Root README retains superseded Dify truth' }; git diff --check -- evidence/dify-live platform/dify/capability-matrix.json platform/dify/README.md README.md .planning/STATE.md tests/test_probe_cli.py .planning/quick/260809-fob-dify-c01-c07-readme-pptx; if($LASTEXITCODE){ throw 'Scoped diff check failed' }; $forbidden=@('deliverables/DebugMate-V0.1.pptx','deliverables/DebugMate-V0.1-demo.mp4','deliverables/DebugMate-V0.1-subtitles.srt'); $changed=@(git status --short | ForEach-Object { $_.Substring(3).Replace('\','/') }); foreach($path in $forbidden){ if($path -in $changed){ throw "Forbidden course deliverable changed: $path" } }; if($changed | Where-Object { $_ -match '\.(pptx|mp4|srt)$' -or $_ -match '(^|/)(screenshots?|final-screenshots?)(/|$)' }){ throw 'PPTX/video/subtitle/screenshot scope was touched' }</automated>
  </verify>
  <done>两份 README 与 STATE 完整匹配最终矩阵和版本化证据，过时的全 not-tested/无 cloud success/待 Local SAPI 听验口径已移除；测试、Ruff、秘密扫描、diff 和交付物冻结检查全部通过。</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ignored `.artifacts` → versioned evidence | 临时目录内容只有通过现有 bundle 校验、逐文件哈希比对和秘密扫描后才能进入 Git 事实源。 |
| Dify API/TTS → capability pass | 网络调用成功、HTTP 200 或 pytest 退出 0 本身不足；还必须有对应能力的版本化文件、媒体/合同验证和可复算 SHA-256。 |
| DSL/历史文字 → C03/C04/C06 status | 配置存在和人工观察不能替代该能力的独立、版本化执行证据。 |
| capability matrix → README/STATE | 文档只能复述矩阵和证据，不得用更宽泛措辞升级能力状态。 |
| evidence/docs → course deliverables | 本 quick 只稳定事实源；PPTX、视频、字幕和最终截图继续冻结。 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q-FOB-01 | Spoofing | C01-C07 状态 | mitigate | 仅当 evidence_path 存在且实际 SHA-256 匹配时允许 `pass`；C03/C04/C06 明确保留 `not-tested`。 |
| T-Q-FOB-02 | Tampering | live bundle / MP3 | mitigate | 历史 bundle 原样复制并前后验哈希；版本化副本运行 `verify-bundle`；MP3 运行 ffprobe 并与 metadata 哈希绑定。 |
| T-Q-FOB-03 | Repudiation | 现场测试结论 | mitigate | 保存 UTC 时间、测试命令、backend、媒体属性、run/case 元数据和版本化路径，README 指向同一证据。 |
| T-Q-FOB-04 | Information disclosure | 上传记录、TTS metadata、文档 | mitigate | 不保存 API key/header/recap 原文/个人路径，对 evidence、README、STATE 执行秘密模式扫描。 |
| T-Q-FOB-05 | Denial of service | 云端额度/网络 | accept | 只进行一次必要 live TTS 重跑；失败时保留准确状态，不重试刷额度、不充值、不阻塞本地 V0.1。 |
| T-Q-FOB-06 | Elevation of privilege | 课程材料范围 | mitigate | 修改范围检查禁止 PPTX、MP4、SRT 和截图路径，且不调用任何交付物生成器。 |
</threat_model>

<verification>
按顺序完成三层门禁：先复验并版本化 cloud/TTS 原始证据；再通过测试强制矩阵的 pass→文件→SHA-256 链路；最后运行完整 probe 文档测试、Ruff、秘密/个人路径扫描、`git diff --check` 与课程交付物冻结检查。最终人工只需审阅 Git diff，不需要登录平台或执行任何手工验证动作。
</verification>

<success_criteria>
- `evidence/dify-live/` 保存 secret-free、可复算的真实 Dify 证据；历史 cloud bundle 在版本化位置通过 `verify-bundle`。
- C01/C02/C05 为 evidence-backed pass；C03/C04/C06 保持 `not-tested`；C07 仅在真实 live gate、ffprobe 与版本化哈希全部成功时为 pass。
- `.gitignore` 仅放行 `evidence/dify-live/**`；自动测试会拒绝 ignored、未被 `git ls-files` 跟踪、缺失、越界、目录或 SHA-256 不匹配的任何 `pass` 证据。
- `platform/dify/README.md`、根 `README.md` 和 `.planning/STATE.md` 与矩阵逐项一致，不再保留全 not-tested、无成功 cloud-probe 或 Local SAPI 听验未完成等过时口径。
- 全部证据和文档不含秘密值、Bearer header、recap 原文或个人绝对路径。
- PPTX、视频、字幕、最终截图、ROADMAP、REQUIREMENTS、PROJECT、DSL 和产品代码均未修改。
</success_criteria>

<output>
执行完成后创建 `.planning/quick/260809-fob-dify-c01-c07-readme-pptx/260809-fob-SUMMARY.md`，逐项记录 C01-C07 最终状态、对应版本化证据路径与 SHA-256、cloud bundle/ffprobe/pytest/Ruff/秘密扫描结果，以及未通过能力保持非 pass 的具体理由。SUMMARY 不得声称本任务刷新了 PPTX、视频、字幕或最终截图。
</output>
