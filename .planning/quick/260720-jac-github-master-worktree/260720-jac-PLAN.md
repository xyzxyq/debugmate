---
id: 260720-jac-github-master-worktree
phase: quick-260720-jac-github-master-worktree
plan: 01
type: quick
title: 安全快进同步 GitHub 更新到 master 与功能 worktree
wave: 1
depends_on: []
autonomous: true
files_modified:
  - .git/refs/heads/master
  - .git/refs/heads/codex/phase-1-foundation-platform-gate
requirements:
  - GIT-SYNC-01
must_haves:
  truths:
    - "本地 master 仅通过 fast-forward 到达 origin/master 的 f031c6b，不创建合并提交、不改写历史。"
    - "功能分支仅在其旧尖端为更新后 master 的祖先时 fast-forward 到同一提交，且 979 个未跟踪运行产物在同步前后逐项不变。"
    - "两个本地分支最终指向同一已测试提交；origin/master 经实时查询也指向该提交，且两个 worktree 均无 tracked/staged 改动。"
  artifacts:
    - path: ".git/refs/heads/master"
      provides: "与 GitHub origin/master 一致的本地主分支引用"
    - path: ".git/refs/heads/codex/phase-1-foundation-platform-gate"
      provides: "快进到同一远端最新提交的功能 worktree 分支引用"
  key_links:
    - from: "master"
      to: "origin/master"
      via: "git fetch 后 git merge --ff-only 与 git ls-remote OID 校验"
      pattern: "refs/heads/master"
    - from: "codex/phase-1-foundation-platform-gate"
      to: "master"
      via: "祖先检查后 git merge --ff-only master"
      pattern: "refs/heads/codex/phase-1-foundation-platform-gate"
---

<objective>
将 GitHub `origin/master` 的两个最新 UI 提交安全同步到本地 `master` 和 `codex/phase-1-foundation-platform-gate` 功能 worktree，并证明分支、测试与本地运行产物均保持预期状态。

Purpose: 让两个本地工作入口使用相同的最新 UI 代码，同时严格避免合并提交、历史改写或对功能 worktree 中 979 个本地生成文件的任何触碰。
Output: 指向同一已验证提交的两个本地分支、与 `origin/master` 一致的 master，以及未跟踪运行产物前后不变的审计证据。
</objective>

<context>
@AGENTS.md
@.planning/STATE.md
@.planning/quick/260720-d6u-codex-phase-1-foundation-platform-gate-m/260720-d6u-SUMMARY.md
@pyproject.toml
@src/debugmate/results/font.py
@src/debugmate/ui/app.py
@tests/results/test_contracts.py
@tests/ui/test_app.py
@tests/ui/test_browser.py
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md

Planning evidence captured on 2026-07-20 after fetch:
- Main worktree is `X:/PROJECT/校外实训`, on `master` at `6d5442e`; it is clean except for this new untracked quick-task directory. `origin/master...master` is `2 0`, so local master is strictly behind and has no unique commit.
- Remote commits are `0144efc style(ui): add macOS student-friendly workbench` and merge commit `f031c6b merge: macOS student-friendly UI`. Their tracked diff is limited to `src/debugmate/results/font.py`, `src/debugmate/ui/app.py`, `tests/results/test_contracts.py`, `tests/ui/test_app.py`, and `tests/ui/test_browser.py`.
- Feature worktree is `.worktrees/phase-1-foundation-platform-gate`, on `codex/phase-1-foundation-platform-gate` at `ce0aa84`; its local/remote feature divergence is `0 0`, it has no tracked or staged changes, and it retains exactly 979 untracked generated files.
- This task synchronizes remote changes into local refs only. Do not push or otherwise mutate `origin/codex/phase-1-foundation-platform-gate` unless separately authorized.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Freeze safety evidence and fast-forward master</name>
  <files>.git/refs/heads/master</files>
  <action>From the repository root, fetch `origin` with pruning and revalidate the repository root, origin URL, worktree mapping, current branches, and both worktree statuses. Permit in the main worktree only the untracked `.planning/quick/260720-jac-github-master-worktree/` workflow files; if any other tracked, staged, or untracked entry exists, stop and report it rather than stashing, deleting, staging, or overwriting it. In the feature worktree require zero tracked/staged changes. Capture its complete `git ls-files --others --exclude-standard` output, require exactly 979 entries and require every path to remain under `.debugmate-runtime/` or `--help/`; save only an in-memory sorted list plus SHA-256 digest for the final comparison, never alter those paths. Reconfirm `git rev-list --left-right --count origin/master...master` is `2 0`, `git merge-base --is-ancestor master origin/master` succeeds, and `origin/master` resolves to `f031c6b`; if any precondition changed, stop instead of choosing another integration strategy. On `master`, run `git merge --ff-only origin/master`. Do not use pull, rebase, a merge commit, reset, checkout-overwrite, clean, stash, add, commit, or any force option.</action>
  <verify>
    <automated>$root = (git rev-parse --show-toplevel).Trim(); if ($root -replace '\\','/' -ne 'X:/PROJECT/校外实训') { throw "Unexpected root: $root" }; if ((git branch --show-current).Trim() -ne 'master') { throw 'Expected master' }; $local = (git rev-parse master).Trim(); $tracking = (git rev-parse origin/master).Trim(); if ($local -ne $tracking) { throw "master does not equal origin/master: $local / $tracking" }; $counts = ((git rev-list --left-right --count origin/master...master).Trim() -split '\s+'); if ([int]$counts[0] -ne 0 -or [int]$counts[1] -ne 0) { throw "master divergence: $($counts -join '/')" }; git diff --check</automated>
  </verify>
  <done>`master` is fast-forwarded from `6d5442e` to fetched `origin/master` without a new commit or rewritten history; the feature worktree's tracked state is clean and its 979-file baseline is captured unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Run focused UI regression checks and fast-forward the feature worktree</name>
  <files>.git/refs/heads/codex/phase-1-foundation-platform-gate</files>
  <action>Use the existing `.worktrees/phase-1-foundation-platform-gate/.venv/Scripts/python.exe`, but bind `PYTHONPATH` first to the main worktree `src`, and run the three test files changed by the incoming commits: `tests/results/test_contracts.py`, `tests/ui/test_app.py`, and `tests/ui/test_browser.py`. Run Ruff on the two changed production files and those three test files. Only after these checks pass, prove the feature tip is an ancestor of the updated master with `git merge-base --is-ancestor codex/phase-1-foundation-platform-gate master`; then from the feature worktree execute `git merge --ff-only master`. This must move only the feature branch ref and tracked checkout. Do not stage, clean, stash, delete, rename, open for writing, or otherwise touch any untracked generated path, and do not push the feature branch. Rebind `PYTHONPATH` to the feature worktree `src` and rerun the same focused pytest and Ruff checks from that checkout so path-specific import or worktree problems are detected.</action>
  <verify>
    <automated>$repo = (git rev-parse --show-toplevel).Trim(); $featurePath = Join-Path $repo '.worktrees\phase-1-foundation-platform-gate'; $python = Join-Path $featurePath '.venv\Scripts\python.exe'; if ((git rev-parse master).Trim() -ne (git -C $featurePath rev-parse HEAD).Trim()) { throw 'Feature worktree did not fast-forward to master' }; if (@(git -C $featurePath status --porcelain=v1 --untracked-files=no).Count) { throw 'Feature tracked/staged changes exist' }; $env:PYTHONPATH = (Join-Path $featurePath 'src'); & $python -m pytest -q (Join-Path $featurePath 'tests\results\test_contracts.py') (Join-Path $featurePath 'tests\ui\test_app.py') (Join-Path $featurePath 'tests\ui\test_browser.py'); if ($LASTEXITCODE) { throw 'Focused UI pytest failed in feature worktree' }; & $python -m ruff check (Join-Path $featurePath 'src\debugmate\results\font.py') (Join-Path $featurePath 'src\debugmate\ui\app.py') (Join-Path $featurePath 'tests\results\test_contracts.py') (Join-Path $featurePath 'tests\ui\test_app.py') (Join-Path $featurePath 'tests\ui\test_browser.py'); if ($LASTEXITCODE) { throw 'Focused Ruff failed in feature worktree' }</automated>
  </verify>
  <done>The incoming UI changes pass focused pytest and Ruff checks from both checkout contexts, and the feature branch fast-forwards to exactly the updated master without altering or publishing untracked runtime outputs.</done>
</task>

<task type="auto">
  <name>Task 3: Prove ref equality and byte-for-byte preservation of untracked paths</name>
  <files>.git/refs/heads/master, .git/refs/heads/codex/phase-1-foundation-platform-gate</files>
  <action>Independently query GitHub with `git ls-remote --heads origin refs/heads/master` and require its OID to equal both local `master` and the feature worktree `HEAD`. Fetch `origin/master` once more and require `origin/master...master` to be `0 0`; also prove both incoming commits `0144efc` and `f031c6b` are ancestors of both local refs. Confirm both worktrees have zero tracked/staged changes, allowing only this quick workflow's untracked directory in the main worktree. Re-enumerate the feature worktree's untracked files, require the count to remain exactly 979, require the same two-directory allowlist, and require the sorted path-list SHA-256 digest to equal the baseline captured before either fast-forward. If the executor can afford a content-level invariant, also compare a pre/post manifest of relative path, length, and SHA-256 for all 979 files; any mismatch is failure and must be reported without attempting restoration or cleanup. Record the remote/local OIDs, test results, ahead/behind result, and untracked count/digest in the SUMMARY. Do not claim `origin/codex/phase-1-foundation-platform-gate` was updated: it is intentionally outside this pull-only task.</action>
  <verify>
    <automated>$repo = (git rev-parse --show-toplevel).Trim(); $featurePath = Join-Path $repo '.worktrees\phase-1-foundation-platform-gate'; $master = (git rev-parse master).Trim(); $feature = (git -C $featurePath rev-parse HEAD).Trim(); $line = git ls-remote --heads origin refs/heads/master; if (-not $line) { throw 'origin/master missing' }; $remote = ($line -split '\s+')[0]; if ($master -ne $remote -or $feature -ne $remote) { throw "Ref mismatch: master=$master feature=$feature remote=$remote" }; git fetch origin master; $counts = ((git rev-list --left-right --count origin/master...master).Trim() -split '\s+'); if ([int]$counts[0] -ne 0 -or [int]$counts[1] -ne 0) { throw "master divergence: $($counts -join '/')" }; foreach ($oid in @('0144efc','f031c6b')) { git merge-base --is-ancestor $oid master; if ($LASTEXITCODE) { throw "$oid absent from master" }; git merge-base --is-ancestor $oid codex/phase-1-foundation-platform-gate; if ($LASTEXITCODE) { throw "$oid absent from feature" } }; if (@(git status --porcelain=v1 --untracked-files=no).Count) { throw 'Main tracked/staged changes exist' }; if (@(git -C $featurePath status --porcelain=v1 --untracked-files=no).Count) { throw 'Feature tracked/staged changes exist' }; $items = @(git -C $featurePath ls-files --others --exclude-standard | Sort-Object); if ($items.Count -ne 979) { throw "Expected 979 untracked files, found $($items.Count)" }; $invalid = @($items | Where-Object { $_ -notmatch '^(\.debugmate-runtime|--help)/' }); if ($invalid.Count) { throw "Unexpected untracked paths: $($invalid -join '; ')" }; git status --short --branch; git -C $featurePath status --short --branch --untracked-files=no</automated>
  </verify>
  <done>Fresh remote evidence shows `origin/master`, local `master`, and local feature HEAD at the same OID with master divergence `0/0`; both incoming commits are reachable; tracked states are clean; all 979 allowlisted untracked paths and their baseline digest remain unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GitHub origin → local refs | Remote state may move between fetch and update; only observed ancestor-safe history may be accepted. |
| Git refs/index → feature runtime directories | Branch checkout must not stage, clean, overwrite, or delete 979 untracked generated files. |
| Updated UI code → local runtime | A ref can synchronize successfully while the incoming UI behavior is broken, so targeted tests must gate completion. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q-JAC-01 | Tampering | `master` and feature refs | mitigate | Fetch, verify exact ahead/behind and ancestry, and permit only `git merge --ff-only`; stop on any changed precondition. |
| T-Q-JAC-02 | Tampering | feature untracked outputs | mitigate | Capture pre/post path digest (and content manifest when feasible), enforce count 979 and directory allowlist, and prohibit add/clean/stash/delete. |
| T-Q-JAC-03 | Repudiation | synchronization result | mitigate | Record full OIDs, `ls-remote` result, ancestry checks, test commands, and untracked digest in SUMMARY. |
| T-Q-JAC-04 | Denial of service | incoming UI changes | mitigate | Run the three changed test files plus focused Ruff from both checkout contexts before accepting synchronization. |
</threat_model>

<verification>
Completion requires all of the following at the same time: the main and feature local refs exactly equal a fresh `ls-remote` result for `origin/master`; `origin/master...master` is `0 0`; both incoming commits are ancestors of both local refs; focused pytest and Ruff pass in both checkout contexts; both worktrees have no tracked/staged changes; and the feature worktree still exposes exactly the same 979 allowlisted untracked paths with the same baseline digest.
</verification>

<success_criteria>
- `master` reaches `f031c6b` solely by fast-forward and exactly matches `origin/master`.
- `codex/phase-1-foundation-platform-gate` reaches the same commit solely by fast-forward, without pushing its remote branch.
- The five changed UI/font/test files pass focused pytest and Ruff checks from both worktree contexts.
- No merge commit, rebase, reset, force operation, stash, staging, cleanup, deletion, or overwrite is used.
- The feature worktree retains all 979 original generated files unchanged and untracked under only `.debugmate-runtime/` and `--help/`.
</success_criteria>

<output>
After execution, create `.planning/quick/260720-jac-github-master-worktree/260720-jac-SUMMARY.md` and update `.planning/STATE.md` through the quick workflow. The summary must include the final full/short OID, fresh remote-ref evidence, both local branch refs, focused pytest/Ruff results, the 979-file path digest (and content-manifest comparison if collected), and the explicit note that `origin/codex/phase-1-foundation-platform-gate` was not mutated.
</output>
