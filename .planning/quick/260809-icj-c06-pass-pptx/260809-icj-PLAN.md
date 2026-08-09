---
quick_id: 260809-icj
phase: quick-260809-icj-c06-pass-pptx
plan: 01
type: quick
wave: 1
depends_on: []
autonomous: true
description: "将独立 Dify 应用的重导出、结构等价与真实复跑证据版本化，并把 C06 从 blocked 提升为 pass；课程媒体继续冻结"
mode: quick-full
date: 2026-08-09
requirements: []
files_modified:
  - src/debugmate/dify_live_evidence.py
  - tests/platform/test_dify_live_evidence.py
  - tests/platform/test_dify_dsl.py
  - evidence/dify-live/2026-08-09/c06/reexport.dsl.yml
  - evidence/dify-live/2026-08-09/c06/reconstructed-output.json
  - evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
  - evidence/dify-live/README.md
  - platform/dify/capability-matrix.json
  - platform/dify/README.md
  - README.md
  - .planning/STATE.md
  - .planning/quick/260809-icj-c06-pass-pptx/260809-icj-SUMMARY.md
must_haves:
  truths:
    - "C06 pass 由一个与原应用 ID 不同的独立 Dify 应用支撑；仓库只保存两个 ID 的 SHA-256 指纹，不保存原始 ID、cookie、CSRF、Authorization、HAR 或个人路径。"
    - "下载的重导出 DSL 作为只读输入复制进仓库证据目录；源 DSL 与重导出 DSL 均有原始 SHA-256，规范化结构 SHA-256 相等且 differences 为空。"
    - "独立应用从 2026-08-09 13:21:46 至 13:22:04 Asia/Shanghai 的 fresh CDP/SSE SUCCESS 复跑被记录为安全 allowlist：workflow run 指纹精确为 94a89d3fe4e77fa0a1255e39dbfd565f184076a12d6248c93fd314f09cb3531f、18.515 秒、6019 tokens、6 steps、category=dependency_environment、DiagnosisRecord 1.1.0 校验成功，并包含知识片段 python-exceptions:module-not-found-error 与 Python 官方来源 URL。"
    - "C06 记录精确绑定源 DSL、重导出 DSL 和 reconstructed-output.json 的 SHA-256；任一内层产物替换、应用指纹相同、结构差异或无有效复跑都会使 candidate/publication 验证失败。"
    - "只有 C06 证据先被原子提交、成为 Git tracked 且 not ignored 后，能力矩阵才将 C06 从 blocked 提升为 pass 并写入新证据记录的实算 SHA-256。"
    - "C01-C05/C07 的状态、evidence_path 和 SHA-256 逐字保持现有基线；README、Dify README、live evidence README 与 STATE 同步为七项 pass。"
    - "PPTX、MP4、SRT、视频、字幕、最终截图、deliverables、产品 UI、ROADMAP、REQUIREMENTS、PROJECT 和 platform/dify/app.dsl.yml 在整个 quick 中保持不变。"
  artifacts:
    - path: src/debugmate/dify_live_evidence.py
      provides: "严格 C06 记录、复跑 allowlist、三项内层 SHA、独立应用与 publication tracking 校验"
    - path: evidence/dify-live/2026-08-09/c06/reexport.dsl.yml
      provides: "从 X:/Download 只读重导出文件选择性复制的版本化 DSL"
    - path: evidence/dify-live/2026-08-09/c06/reconstructed-output.json
      provides: "真实独立应用复跑的脱敏 allowlist 证据"
    - path: evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
      provides: "C06 独立导入、重导出、结构比较、复跑及精确 SHA 绑定的总记录"
    - path: tests/platform/test_dify_dsl.py
      provides: "C06 pass、独立应用、结构语义、复跑和内层篡改回归门槛"
    - path: tests/platform/test_dify_live_evidence.py
      provides: "七项矩阵、Git tracked/not ignored、精确 SHA 与文档口径回归"
    - path: platform/dify/capability-matrix.json
      provides: "C01-C07 全部 pass 的机器可读事实源"
    - path: .planning/STATE.md
      provides: "C06 已完成独立 roundtrip/rerun 的当前事实和媒体冻结边界"
  key_links:
    - from: evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
      to: platform/dify/app.dsl.yml
      via: "source_dsl + source_sha256 + source_normalized_sha256"
      pattern: "source_dsl|source_sha256|source_normalized_sha256"
    - from: evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
      to: evidence/dify-live/2026-08-09/c06/reexport.dsl.yml
      via: "reexport_dsl + reexport_sha256 + reexport_normalized_sha256 + empty differences"
      pattern: "reexport_dsl|reexport_sha256|reexport_normalized_sha256|differences"
    - from: evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
      to: evidence/dify-live/2026-08-09/c06/reconstructed-output.json
      via: "reconstructed_output + reconstructed_output_sha256 + independent app/run fingerprints"
      pattern: "reconstructed_output|reconstructed_output_sha256|independent_app_id_sha256"
    - from: platform/dify/capability-matrix.json
      to: evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
      via: "C06 pass evidence_path 与总记录实算 SHA-256，并由 published validator 强制 Git tracking"
      pattern: "C06|evidence_path|sha256|pass"
---

# Quick Task 260809-icj Plan

<objective>
把已经由用户在独立 Dify 应用中完成的 DSL 导入、重导出、结构等价检查与真实复跑转化为可复算、可发布且不泄露会话信息的 C06 证据链，并在证据先提交且 publication gate 通过后将能力矩阵提升为全 pass。

Purpose: 当前 C06 仍指向准确的 blocked 记录，但现场事实已发生变化：`platform/dify/app.dsl.yml` 已被导入到独立应用 `DebugMate C06 Roundtrip Verify 20260809`，下载目录已有该应用的重导出 YAML，且独立应用在 13:22:04 完成了含有效 DiagnosisRecord 与知识来源的 fresh CDP/SSE 复跑。本计划只固化这些已发生事实，不重新操作 Dify，也不刷新最终媒体。

Output: 强化后的 C06 validator/tests、三个精确 SHA 绑定的版本化 C06 证据文件、C06=pass 的能力矩阵与一致文档/STATE、原子提交和冻结范围复核记录。
</objective>

<context>
@AGENTS.md
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/quick/260809-ghz-dify-c03-c04-c06-dsl-readme-state-pptx/260809-ghz-PLAN.md
@.planning/quick/260809-ghz-dify-c03-c04-c06-dsl-readme-state-pptx/260809-ghz-VERIFICATION.md
@src/debugmate/dify_live_evidence.py
@tests/platform/test_dify_live_evidence.py
@tests/platform/test_dify_dsl.py
@evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json
@platform/dify/capability-matrix.json
@platform/dify/app.dsl.yml

Live facts and locked boundaries:
- Source application ID is `6fe994e7-2eac-4814-936b-10d2266712eb`; imported application ID is `2ed0d18e-bc5f-4a6a-9abf-4c603df1bf5a`. Use these values only in memory to calculate fingerprints. The expected fingerprints are respectively `eb29da988ef9fc10db49d44b1fef4b9fba524e1f27d99f1f59f86360bddd1cf2` and `2d73ad412fbc255347c37ca530c3c3970654144eb27ae74183c1f7390b639402`; raw IDs must not be written to versioned evidence or docs.
- The re-exported DSL is the read-only input `X:/Download/DebugMate C06 Roundtrip Verify 20260809.yml`. Its observed raw SHA-256 is `b6eb183d89000c0f4bb92c69a9afb749f77f18f0d76eb63890984830f18d2ea5`. Never edit, move, rename, delete, or stage the download file; copy bytes into the repository evidence path and verify source/destination hashes match.
- The frozen source DSL raw SHA-256 observed during planning is `806532d42c82aa76e83d786e5badb66ed73797be9ccd52c4ef0b6787e3097289`. Existing `compare_dsl_files` produced matching normalized SHA-256 `d5e7983383c6fc94836efe81b89d6b6f7f2b294cff548ccb3536d0f41e64a12a` and an empty differences list for the source/download pair. Execution must recompute these values; do not hardcode success if bytes changed.
- The authoritative fresh CDP/SSE run started at 2026-08-09 13:21:46 Asia/Shanghai and completed at 13:22:04 with status `SUCCESS`, duration `18.515s`, `6019` tokens and `6` steps. Its workflow run SHA-256 fingerprint is locked to `94a89d3fe4e77fa0a1255e39dbfd565f184076a12d6248c93fd314f09cb3531f`; the raw run ID must never be persisted. Its complete DiagnosisRecord schema is `1.1.0`, category is `dependency_environment`, knowledge chunk is `python-exceptions:module-not-found-error`, and source URL is `https://docs.python.org/3/library/exceptions.html`. Only these safe allowlisted facts and SHA-256 fingerprints may be persisted; do not save raw SSE, console responses or screenshots.
- Existing C01/C02/C03/C04/C05/C07 matrix tuples are locked exactly as found in `platform/dify/capability-matrix.json`. C06 may become pass only through this quick's published record.
- Before capturing the baseline, inspect `git status --porcelain=v1 --untracked-files=all`. The only permitted pre-existing dirt is the orchestrator-owned untracked/modified `.planning/quick/260809-icj-c06-pass-pptx/260809-icj-PLAN.md`; abort for every other path. Record both this allowed exception and `git rev-parse HEAD` in ignored `.artifacts/quick-260809-icj/`. The final scope audit must apply the same allowlist/frozen rules to the union of `baseline..HEAD`, staged, unstaged and non-ignored untracked paths. Do not assume shell variables survive across tasks.
- Use `.worktrees/phase-1-foundation-platform-gate/.venv/Scripts/python.exe` with current-repository `src` in `PYTHONPATH`; the root `.venv` is dependency-incomplete and must not be repaired or installed into during this quick.
- Do not modify or regenerate any PPTX, MP4, SRT, video, subtitle, final screenshot, `deliverables/**`, `src/debugmate/ui/**`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, or `platform/dify/app.dsl.yml`.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Strengthen the exact C06 roundtrip and rerun contract</name>
  <files>src/debugmate/dify_live_evidence.py, tests/platform/test_dify_dsl.py, tests/platform/test_dify_live_evidence.py</files>
  <behavior>
    - "A C06 pass requires source_app_id_sha256 and independent_app_id_sha256 to be valid, distinct SHA-256 values."
    - "A C06 pass binds source DSL, re-export DSL, and reconstructed-output.json by independently recomputed raw SHA-256 values; same-schema byte replacement of any inner artifact is rejected."
    - "The rerun file uses a strict extra=forbid allowlist and requires workflow_run_id_sha256 to equal the locked fresh-run fingerprint 94a89d3fe4e77fa0a1255e39dbfd565f184076a12d6248c93fd314f09cb3531f, plus SUCCESS, exact UTC start/completion timestamps, 18.515-second duration, 6019 tokens, 6 steps, diagnosis_valid=true, DiagnosisRecord 1.1.0, category=dependency_environment, the knowledge chunk ID, and HTTPS source URL."
    - "Source/re-export normalized hashes must match recomputation and each other, while differences must be empty; changing model, vision, retrieval, topology, start variables, or end output remains a failure."
    - "Published C06 pass requires the total record and all referenced inner artifacts to be Git tracked and not ignored; candidate validation does not require tracking before the evidence commit."
  </behavior>
  <action>At task start, create ignored `.artifacts/quick-260809-icj/`. Capture `git status --porcelain=v1 --untracked-files=all`, normalize its paths, and abort unless every pre-existing entry is exactly `.planning/quick/260809-icj-c06-pass-pptx/260809-icj-PLAN.md`; write that allowed orchestrator exception to `preflight-status.txt`, then save non-empty `git rev-parse HEAD` to `baseline.txt`. Write RED tests before production changes. Extend `C06Record` with `source_app_id_sha256` and `reconstructed_output_sha256`; define a strict reconstructed-run model limited to safe fields: evidence schema version, UTC start/completion, status, duration, token/step counts, workflow run fingerprint, `diagnosis_valid`, `diagnosis_schema_version`, diagnosis category, knowledge chunk ID and source URL. Validate both app fingerprints as SHA-256 and reject equality; recompute and compare the reconstructed-output hash before parsing it; require workflow run fingerprint exactly `94a89d3fe4e77fa0a1255e39dbfd565f184076a12d6248c93fd314f09cb3531f`, status SUCCESS, the exact second-run timestamps/metrics, DiagnosisRecord 1.1.0, `dependency_environment`, and non-empty retriever/source facts. Keep raw app IDs, raw run IDs, SSE and console payloads out of models and error output. Extend `validate_published_tree` regressions so C06's source DSL, re-export DSL, rerun JSON and total record must all be tracked/not ignored. Add mutation tests for wrong run fingerprint, same-schema rerun replacement, mismatched app identity, missing/extra allowlist fields, invalid status/metrics/diagnosis schema/category/source URL, and existing critical DSL changes. Preserve non-pass C06 compatibility so historical blocked records still parse until replaced. Run RED, implement GREEN, then Ruff. Selectively stage only the three listed files and create atomic commit `test(quick-260809-icj): strengthen C06 publication evidence` (production validator and its tests form one inseparable contract change).</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; & $python -m pytest -q tests\platform\test_dify_dsl.py tests\platform\test_dify_live_evidence.py -k 'c06 or dsl'; if($LASTEXITCODE){ throw 'C06 contract tests failed' }; & $python -m ruff check src\debugmate\dify_live_evidence.py tests\platform\test_dify_dsl.py tests\platform\test_dify_live_evidence.py; if($LASTEXITCODE){ throw 'Ruff failed' }; $baseline=Get-Content -Raw -LiteralPath '.artifacts\quick-260809-icj\baseline.txt'; if([string]::IsNullOrWhiteSpace($baseline)){ throw 'Missing execution baseline' }; git show --name-only --format= HEAD | Where-Object { $_ } | ForEach-Object { if($_ -notin @('src/debugmate/dify_live_evidence.py','tests/platform/test_dify_dsl.py','tests/platform/test_dify_live_evidence.py')){ throw "Task 1 commit escaped scope: $_" } }</automated>
  </verify>
  <done>The validator cannot accept a same-app reconstruction, unbound or replaced rerun output, structurally changed DSL, incomplete DiagnosisRecord proof, untracked publication artifact, secret-bearing field, or raw platform identifier; the focused contract is committed atomically.</done>
</task>

<task type="auto">
  <name>Task 2: Version the re-export and safe real-rerun evidence before promotion</name>
  <files>evidence/dify-live/2026-08-09/c06/reexport.dsl.yml, evidence/dify-live/2026-08-09/c06/reconstructed-output.json, evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json</files>
  <action>Treat `X:/Download/DebugMate C06 Roundtrip Verify 20260809.yml` as immutable input: verify it still exists and its raw SHA is the observed `b6eb...2ea5`, then copy its exact bytes to `evidence/dify-live/2026-08-09/c06/reexport.dsl.yml` without modifying the download. Build `reconstructed-output.json` only from the authoritative fresh CDP/SSE run: `started_at_utc=2026-08-09T05:21:46Z`, `completed_at_utc=2026-08-09T05:22:04Z`, status `SUCCESS`, duration `18.515`, token count `6019`, step count `6`, `workflow_run_id_sha256=94a89d3fe4e77fa0a1255e39dbfd565f184076a12d6248c93fd314f09cb3531f`, `diagnosis_valid=true`, `diagnosis_schema_version=1.1.0`, category `dependency_environment`, knowledge chunk `python-exceptions:module-not-found-error`, and `https://docs.python.org/3/library/exceptions.html`. Do not recalculate a different fingerprint, persist the raw run ID, or copy the full diagnosis/SSE/console response. Replace the historical blocked record with a pass record containing the two known distinct app fingerprints, source DSL repository path and raw SHA, copied re-export path and raw SHA, both recomputed normalized hashes, empty differences, reconstructed-output path and its recomputed SHA, UTC attempt/completion facts, `import_channel=dify_console`, and `reason_code=null`. Run `compare_dsl_files` and `validate-candidate` against the repository; scan all three files for secrets, raw app IDs, raw run IDs, session material, download/personal absolute paths and Authorization data. Selectively stage only the three C06 evidence files, verify the downloaded input remains outside Git and unchanged, then create atomic commit `evidence(quick-260809-icj): publish C06 roundtrip rerun proof`. Do not update the capability matrix or prose before this evidence commit exists.</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; $download='X:\Download\DebugMate C06 Roundtrip Verify 20260809.yml'; if((Get-FileHash -Algorithm SHA256 -LiteralPath $download).Hash.ToLowerInvariant() -ne 'b6eb183d89000c0f4bb92c69a9afb749f77f18f0d76eb63890984830f18d2ea5'){ throw 'Read-only downloaded DSL changed' }; if((Get-FileHash -Algorithm SHA256 -LiteralPath $download).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath 'evidence\dify-live\2026-08-09\c06\reexport.dsl.yml').Hash){ throw 'Versioned re-export is not byte-identical to download' }; & $python -m debugmate.dify_live_evidence validate-candidate --repository-root . --evidence-root evidence\dify-live\2026-08-09; if($LASTEXITCODE){ throw 'Candidate evidence validation failed' }; & $python -m pytest -q tests\platform\test_dify_dsl.py -k 'c06 or dsl'; if($LASTEXITCODE){ throw 'C06 evidence tests failed' }; $unsafe=rg -n -i '(2ed0d18e-bc5f-4a6a-9abf-4c603df1bf5a|6fe994e7-2eac-4814-936b-10d2266712eb|Bearer\s+|authorization\s*[:=]|api[_ -]?key|csrf|session[_ -]?token|cookie\s*[:=]|[A-Z]:\\(?:Users|Download)\\)' evidence\dify-live\2026-08-09\c06; if($LASTEXITCODE -eq 0){ throw "Unsafe C06 evidence: $unsafe" } elseif($LASTEXITCODE -ne 1){ throw 'Secret scan failed to run' }; if(-not (git ls-files --error-unmatch -- 'evidence/dify-live/2026-08-09/c06/reexport.dsl.yml' 'evidence/dify-live/2026-08-09/c06/reconstructed-output.json' 'evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json')){ throw 'C06 evidence commit missing' }</automated>
  </verify>
  <done>The downloaded DSL remains byte-identical and read-only; the repository contains a secret-free, exact-SHA-bound C06 pass record plus re-export and real-rerun allowlist, all three are committed before any matrix promotion.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Promote C06 only through publication validation and synchronize truth</name>
  <files>tests/platform/test_dify_live_evidence.py, platform/dify/capability-matrix.json, platform/dify/README.md, README.md, evidence/dify-live/README.md, .planning/STATE.md, .planning/quick/260809-icj-c06-pass-pptx/260809-icj-SUMMARY.md</files>
  <behavior>
    - "validate-published returns C03=pass, C04=pass and C06=pass only after every referenced artifact is tracked, not ignored and exact-hash matched."
    - "C01-C05/C07 retain their exact pre-quick status/path/hash tuples, while C06 alone changes to pass and points at the new total record SHA."
    - "All four truth documents report C01-C07 pass and describe C06 as independent import, re-export, normalized structural equality, and reconstructed-app rerun—not merely configuration presence."
    - "The execution-baseline diff contains only plan-declared source/tests/C06 evidence/matrix/docs/STATE/SUMMARY paths and no frozen course media, UI, planning source, or source DSL."
  </behavior>
  <action>Before changing the matrix, run `validate-published` and require exactly `{C03: pass, C04: pass, C06: pass}`; this proves Task 2's C06 files are tracked/not ignored and their hashes still match. Update the matrix regression test's C06 tuple from blocked to pass using the new total record's repository path and freshly computed SHA; retain all six other tuples byte-for-byte. Add assertions that published C06 validates the three inner hashes and that all seven matrix entries point to existing, tracked, not-ignored, exact-hash files. Update `platform/dify/capability-matrix.json` only after the test is RED for the old blocked tuple. Synchronize the root README, Dify README, live evidence README and STATE to say C01-C07 pass; include C06's independent roundtrip/rerun basis, exact evidence path, and no claim that course media was refreshed. In STATE, update current verification baseline/next order/quick-task ledger while retaining milestone completion and explicitly preserving the frozen PPTX/video/subtitle/final-screenshot boundary. Run the complete focused suite, Ruff, candidate/published validators, secret scan and matrix hash/tracking audit. Selectively stage exactly `tests/platform/test_dify_live_evidence.py`, `platform/dify/capability-matrix.json`, `platform/dify/README.md`, `README.md`, `evidence/dify-live/README.md`, and `.planning/STATE.md`, then create atomic commit `docs(quick-260809-icj): promote C06 to evidence-backed pass`. Do not include PLAN, SUMMARY or VERIFICATION in this third task commit. The execute workflow may make at most one subsequent orchestration documentation commit; its changed paths must be a non-empty subset of `.planning/quick/260809-icj-c06-pass-pptx/260809-icj-PLAN.md`, `.planning/quick/260809-icj-c06-pass-pptx/260809-icj-SUMMARY.md`, `.planning/quick/260809-icj-c06-pass-pptx/260809-icj-VERIFICATION.md`, and `.planning/STATE.md`, and no other post-task commit is allowed. That final docs step creates/updates SUMMARY with raw/normalized hashes, authoritative second-run safe facts, test results, the three atomic commit IDs, exact baseline commit and four-source scope audit; it must not include raw app/run IDs or personal/download paths.</action>
  <verify>
    <automated>$ErrorActionPreference='Stop'; $python=(Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path; $env:PYTHONPATH=(Resolve-Path -LiteralPath 'src').Path; & $python -m debugmate.dify_live_evidence validate-published --repository-root . --evidence-root evidence\dify-live\2026-08-09; if($LASTEXITCODE){ throw 'Publication validation failed' }; & $python -m pytest -q tests\test_probe_cli.py tests\platform\test_dify_live_evidence.py tests\platform\test_dify_dsl.py; if($LASTEXITCODE){ throw 'Capability/evidence/DSL tests failed' }; & $python -m ruff check src\debugmate\dify_live_evidence.py tests\test_probe_cli.py tests\platform\test_dify_live_evidence.py tests\platform\test_dify_dsl.py; if($LASTEXITCODE){ throw 'Ruff failed' }; git diff --check; if($LASTEXITCODE){ throw 'Diff check failed' }; $baseline=(Get-Content -Raw -LiteralPath '.artifacts\quick-260809-icj\baseline.txt').Trim(); if([string]::IsNullOrWhiteSpace($baseline)){ throw 'Missing baseline commit' }; function Get-CommitPaths([string]$hash){ @((git diff-tree --no-commit-id --name-only -r $hash) | ForEach-Object { $_.Replace('\','/') } | Sort-Object -Unique) }; function Assert-ExactPaths([string]$hash,[string[]]$expected){ $actual=@(Get-CommitPaths $hash); $missing=@($expected | Where-Object { $_ -notin $actual }); $extra=@($actual | Where-Object { $_ -notin $expected }); if($missing -or $extra){ throw "Commit $hash path partition mismatch; missing=$($missing -join ','); extra=$($extra -join ',')" } }; $commits=@(git rev-list --reverse "$baseline..HEAD"); if($commits.Count -lt 3 -or $commits.Count -gt 4){ throw "Expected three task commits and at most one final orchestration docs commit, got $($commits.Count)" }; $subjects=@($commits | ForEach-Object { git show -s --format=%s $_ }); $expectedSubjects=@('test(quick-260809-icj): strengthen C06 publication evidence','evidence(quick-260809-icj): publish C06 roundtrip rerun proof','docs(quick-260809-icj): promote C06 to evidence-backed pass'); for($i=0;$i -lt 3;$i++){ if($subjects[$i] -ne $expectedSubjects[$i]){ throw "Commit order/subject mismatch at index $i: $($subjects[$i])" } }; Assert-ExactPaths $commits[0] @('src/debugmate/dify_live_evidence.py','tests/platform/test_dify_dsl.py','tests/platform/test_dify_live_evidence.py'); Assert-ExactPaths $commits[1] @('evidence/dify-live/2026-08-09/c06/reexport.dsl.yml','evidence/dify-live/2026-08-09/c06/reconstructed-output.json','evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json'); Assert-ExactPaths $commits[2] @('tests/platform/test_dify_live_evidence.py','platform/dify/capability-matrix.json','platform/dify/README.md','README.md','evidence/dify-live/README.md','.planning/STATE.md'); $orchestrationDocs=@('.planning/quick/260809-icj-c06-pass-pptx/260809-icj-PLAN.md','.planning/quick/260809-icj-c06-pass-pptx/260809-icj-SUMMARY.md','.planning/quick/260809-icj-c06-pass-pptx/260809-icj-VERIFICATION.md','.planning/STATE.md'); if($commits.Count -eq 4){ if($subjects[3] -notmatch '^docs\('){ throw 'Final allowance is restricted to one orchestration docs commit' }; $fourth=@(Get-CommitPaths $commits[3]); if(-not $fourth -or @($fourth | Where-Object { $_ -notin $orchestrationDocs })){ throw 'Final orchestration commit escaped PLAN/SUMMARY/VERIFICATION/STATE allowance' } }; $allowed=@('src/debugmate/dify_live_evidence.py','tests/platform/test_dify_dsl.py','tests/platform/test_dify_live_evidence.py','evidence/dify-live/2026-08-09/c06/reexport.dsl.yml','evidence/dify-live/2026-08-09/c06/reconstructed-output.json','evidence/dify-live/2026-08-09/c06/dsl-roundtrip-evidence.json','evidence/dify-live/README.md','platform/dify/capability-matrix.json','platform/dify/README.md','README.md','.planning/STATE.md','.planning/quick/260809-icj-c06-pass-pptx/260809-icj-PLAN.md','.planning/quick/260809-icj-c06-pass-pptx/260809-icj-SUMMARY.md','.planning/quick/260809-icj-c06-pass-pptx/260809-icj-VERIFICATION.md'); $committed=@(git diff --name-only "$baseline..HEAD"); $staged=@(git diff --cached --name-only); $unstaged=@(git diff --name-only); $untracked=@(git ls-files --others --exclude-standard); $worktree=@($staged+$unstaged+$untracked | ForEach-Object { $_.Replace('\','/') } | Sort-Object -Unique); $dirtyEscape=@($worktree | Where-Object { $_ -notin $orchestrationDocs }); if($dirtyEscape){ throw "Uncommitted path is not an orchestration doc: $($dirtyEscape -join ', ')" }; $allChanged=@($committed+$staged+$unstaged+$untracked | ForEach-Object { $_.Replace('\','/') } | Sort-Object -Unique); $escaped=@($allChanged | Where-Object { $_ -notin $allowed }); if($escaped){ throw "Committed/staged/unstaged/untracked scope escaped: $($escaped -join ', ')" }; $frozen=@($allChanged | Where-Object { $_ -match '\.(pptx|mp4|srt)$' -or $_ -match '(^|/)(screenshots?|final-screenshots?|deliverables)(/|$)' -or $_ -match '^src/debugmate/ui/' -or $_ -in @('.planning/PROJECT.md','.planning/REQUIREMENTS.md','.planning/ROADMAP.md','platform/dify/app.dsl.yml') }); if($frozen){ throw "Frozen scope changed: $($frozen -join ', ')" }</automated>
  </verify>
  <done>C06 is publication-validated pass; C01-C05/C07 are unchanged; matrix/docs/STATE/SUMMARY agree; all evidence is tracked and exact-SHA-bound; atomic commits exist; the baseline diff proves every frozen media/planning/UI/source-DSL path remained untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Download directory → repository evidence | The exported YAML is external read-only input; accept it only after exact hash verification and copy bytes without modifying the source. |
| Dify console run → reconstructed-output.json | Console/session data is untrusted and secret-bearing; persist only strict allowlisted facts and SHA-256 fingerprints. |
| Evidence inner artifacts → C06 total record | Re-export and rerun files can be replaced while remaining structurally valid; bind each by recomputed SHA-256. |
| C06 total record → capability matrix | A candidate record is insufficient for publication; require Git tracked/not ignored artifacts and exact hashes before pass promotion. |
| Execution commits → frozen course deliverables | This quick is evidence-only; compare all committed paths against the captured execution baseline and a strict allowlist. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q-ICJ-01 | Spoofing | Independent Dify application | mitigate | Store source/imported application SHA-256 fingerprints, require both valid and unequal, and reject raw IDs in evidence. |
| T-Q-ICJ-02 | Tampering | Re-export/rerun artifacts | mitigate | Recompute source DSL, re-export DSL and rerun JSON hashes; regression-test same-schema byte replacement. |
| T-Q-ICJ-03 | Repudiation | Real reconstructed-app run | mitigate | Record normalized UTC completion, run fingerprint, DiagnosisRecord 1.1.0 validity, chunk/source facts and atomic commit IDs. |
| T-Q-ICJ-04 | Information disclosure | Console/download capture | mitigate | Strict extra-forbid allowlist; no raw IDs, response payload, cookie, CSRF, header, HAR, secret or absolute path; scan before commit. |
| T-Q-ICJ-05 | Denial of service | Missing real run identity | accept | If the actual run ID cannot be fingerprinted, stop promotion and leave C06 blocked; do not rerun indefinitely or fabricate an identifier. |
| T-Q-ICJ-06 | Elevation of privilege | Media/planning/product scope | mitigate | Three selective atomic commits plus execution-baseline allowlist and explicit frozen-path rejection. |
</threat_model>

<verification>
Use RED/GREEN tests to close the missing reconstructed-output hash and independent-app distinction, publish the three evidence files in a dedicated commit, then require publication validation before matrix promotion. Finish with focused pytest/Ruff, two-level validators, exact hash/tracking audit, secret/raw-ID scan, clean-tree check, and an execution-baseline path diff that rejects every frozen deliverable/UI/planning/source-DSL path.
</verification>

<success_criteria>
- `reexport.dsl.yml` is byte-identical to the immutable downloaded export, while the download remains outside Git and unchanged.
- Source and re-export raw SHA values are stored and recomputable; both normalized SHA values recompute to the same value and `differences` is empty.
- `reconstructed-output.json` contains only safe allowlisted proof of the authoritative 13:21:46–13:22:04 SUCCESS independent-app CDP/SSE run, exact locked run fingerprint `94a89d3fe4e77fa0a1255e39dbfd565f184076a12d6248c93fd314f09cb3531f`, 18.515-second duration, 6019 tokens, 6 steps, DiagnosisRecord 1.1.0 validity, `dependency_environment`, the named knowledge chunk and official Python source; its exact SHA is bound by the C06 record.
- The C06 record proves distinct source/imported application fingerprints, exact inner artifacts, structural equivalence and valid rerun; mutation and missing-field tests fail closed.
- C06 evidence is committed and passes `validate-published` before the capability matrix changes to pass.
- C01-C05/C07 retain their exact current tuples; all seven capabilities are pass and every matrix target is tracked, not ignored and exact-hash matched.
- Root/Dify/live-evidence READMEs and STATE agree with the matrix and explicitly state that course media was not refreshed.
- Ordered atomic commits have the exact three locked subjects and exact task path partitions; at most one later `docs(...)` orchestration commit may touch only PLAN/SUMMARY/VERIFICATION/STATE. The union of baseline-to-HEAD commits, staged changes, unstaged changes and non-ignored untracked paths contains only declared/orchestration files and no PPTX/MP4/SRT/screenshots/deliverables/UI/ROADMAP/REQUIREMENTS/PROJECT/source DSL changes.
</success_criteria>

<output>
After completion, create `.planning/quick/260809-icj-c06-pass-pptx/260809-icj-SUMMARY.md` containing the observable C06 proof, repository-relative artifact paths and SHA-256 values, normalized comparison result, safe rerun facts, validation commands/results, atomic commit IDs, captured baseline commit, frozen-scope diff result, and an explicit statement that PPTX/video/subtitles/final screenshots were not touched.
</output>
