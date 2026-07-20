---
id: 260720-cmj-github
phase: quick-260720-cmj-github
plan: 01
type: quick
title: 安全同步当前有效改动到已配置的 GitHub 远端
wave: 1
depends_on: []
autonomous: true
files_modified:
  - .git/index
  - .git/refs/heads/master
requirements:
  - 当前仓库中适合版本化的本地改动与提交安全同步到 origin/master，且远端分支经独立查询验证已更新
must_haves:
  truths:
    - "只有经审查、适合版本化且属于当前仓库的有效改动会进入提交；密钥、环境文件、缓存和超大文件不会被误提交。"
    - "同步前已获取 origin 的最新状态；远端领先或分叉时先安全协调历史，整个流程不使用任何 force push。"
    - "同步完成后，本地 HEAD 与 GitHub 上 refs/heads/master 的对象 ID 完全一致，且不存在遗漏的有效本地改动。"
  artifacts:
    - path: ".git/refs/heads/master"
      provides: "包含本次有效改动的本地 master 提交指针"
    - path: ".git/index"
      provides: "仅含明确选择文件的暂存状态"
  key_links:
    - from: "local HEAD"
      to: "origin/master"
      via: "git fetch、非强制 git push 与 git ls-remote 校验"
      pattern: "refs/heads/master"
---

<objective>
将当前本地仓库中适合版本化的有效改动安全同步到已配置的 GitHub `origin/master`，并用远端引用证明同步结果。

Purpose: 在完整保留用户改动的前提下，让 GitHub 远端成为当前可提交仓库状态的可靠副本，避免误提交敏感/生成文件、覆盖远端历史或因 push 超时而误判结果。
Output: 一个范围明确的本地提交（仅在确有未提交有效改动时创建）、已同步的 `origin/master`，以及本地/远端提交 OID 一致性证据。
</objective>

<context>
@AGENTS.md
@.planning/STATE.md
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md

Planning facts verified on 2026-07-20: repository root is `X:/PROJECT/校外实训`; active branch is `master`; `master` tracks `origin/master`; both fetch and push URLs are `https://github.com/xyzxyq/debugmate.git`; the worktree was clean when this plan was authored. Execution must re-check live state because this plan and workflow bookkeeping may add changes after planning.
</context>

<tasks>

<task type="auto">
  <name>Task 1: 审计实时仓库状态并建立明确提交清单</name>
  <files>.git/index</files>
  <action>在仓库根目录运行 `git rev-parse --show-toplevel`、`git branch --show-current`、`git remote -v`、`git status --short --branch --untracked-files=all` 和 `git diff --check`，确认仍位于预期仓库、分支仍为 `master`、`origin` 仍指向 `xyzxyq/debugmate`。分别用 `git diff --name-only HEAD`、`git diff --cached --name-only` 与 `git ls-files --others --exclude-standard` 建立候选文件清单，逐个查看 diff 或内容用途并确定哪些是本次需要版本化的有效改动。检查候选中是否存在 `.env`、凭据/token、私钥、编辑器/缓存目录、虚拟环境、临时日志、运行时隐私证据或接近 GitHub 100 MiB 限制的大文件；这些内容不得进入提交，也不得在日志中打印秘密值。保留全部用户改动，不删除、不回滚、不覆盖；若某文件是否应发布无法由仓库规则和内容用途确定，则停止并报告具体路径。仅使用 `git add -- <逐个明确路径>` 暂存批准文件，禁止 `git add -A`、`git add .` 和通配式全量暂存；随后审阅 `git diff --cached --stat` 与 `git diff --cached`。如果没有未提交的有效改动，不创建空提交，直接保留现有提交历史进入远端协调。</action>
  <verify>
    <automated>$root = (git rev-parse --show-toplevel).Trim(); if ($root -replace '\\','/' -ne 'X:/PROJECT/校外实训') { throw "Unexpected repository root: $root" }; if ((git branch --show-current).Trim() -ne 'master') { throw 'Expected master branch' }; if ((git remote get-url origin).Trim() -ne 'https://github.com/xyzxyq/debugmate.git') { throw 'Unexpected origin URL' }; git diff --check; git diff --cached --check; git status --short --branch --untracked-files=all</automated>
  </verify>
  <done>候选改动均已逐项分类；只有明确适合发布的文件被选择性暂存，所有其他用户文件保持原样，且没有密钥、缓存、隐私证据或超大文件进入暂存区。</done>
</task>

<task type="auto">
  <name>Task 2: 获取远端最新历史并非强制同步 master</name>
  <files>.git/refs/heads/master</files>
  <action>先执行 `git fetch origin --prune`，确认 `refs/remotes/origin/master` 可解析，再处理本地提交与远端历史。若暂存区有有效改动，先再次检查 `git diff --cached`，用准确概括这些改动的单一 Conventional Commit 消息创建原子提交；若暂存区为空则不得创建空提交。用 `git rev-list --left-right --count origin/master...HEAD` 判断 ahead/behind：仅远端领先且本地无新增提交时执行 `git merge --ff-only origin/master`；本地存在未推送提交且远端也领先/发生分叉时，对未推送本地提交执行 `git rebase origin/master`。只在变更互不冲突且能保持语义时继续；如遇冲突，保留现场并停止报告，不得丢弃任何一侧改动。协调后重新运行快速、与本次改动相关的自动检查及 `git diff --check HEAD^ HEAD`（没有新提交时运行 `git diff --check`），再执行显式非强制推送 `git push origin HEAD:refs/heads/master`。禁止 `--force`、`--force-with-lease`、删除远端引用、hard reset 或覆盖式 checkout。若 push 超时，先检查活动 Git 进程并查询远端 ref，不得立即重复推送。</action>
  <verify>
    <automated>git fetch origin --prune; $counts = (git rev-list --left-right --count origin/master...HEAD).Trim() -split '\s+'; if ([int]$counts[0] -gt 0) { throw "Local branch remains behind origin/master: $($counts -join '/')" }; git diff --check; git log -1 --oneline --decorate</automated>
  </verify>
  <done>所有有效改动已包含在本地 `master` 历史中；远端最新提交已在同步前获取并安全协调；非强制 push 成功或经远端 ref 证明先前超时的 push 实际已完成。</done>
</task>

<task type="auto">
  <name>Task 3: 独立验证 GitHub 远端引用与本地状态</name>
  <files>.git/refs/heads/master</files>
  <action>不要仅依赖 `git push` 的退出信息。读取本地 `git rev-parse HEAD`，并用 `git ls-remote --heads origin refs/heads/master` 直接查询 GitHub；要求远端返回且 OID 与本地完全一致。再执行 `git fetch origin master`，要求 `git rev-list --left-right --count origin/master...HEAD` 为 `0 0`，并检查 `git status --short --branch --untracked-files=all`。工作树应无未提交的有效改动；被 Git 正确忽略的本地秘密不需要显示或上传。若仍有未跟踪/修改文件，则同步验收失败并报告路径；不得为了得到干净状态而删除、回滚或误提交它们。记录远端 URL、分支名和匹配的短 SHA 作为同步证据，但不记录任何认证信息。</action>
  <verify>
    <automated>$local = (git rev-parse HEAD).Trim(); $line = git ls-remote --heads origin refs/heads/master; if (-not $line) { throw 'origin/master was not returned by git ls-remote' }; $remote = ($line -split '\s+')[0]; if ($local -ne $remote) { throw "Remote mismatch: local=$local remote=$remote" }; git fetch origin master; $counts = (git rev-list --left-right --count origin/master...HEAD).Trim() -split '\s+'; if ([int]$counts[0] -ne 0 -or [int]$counts[1] -ne 0) { throw "Branch divergence remains: $($counts -join '/')" }; $pending = git status --porcelain=v1 --untracked-files=all; if ($pending) { throw "Unsynchronized worktree entries remain: $($pending -join '; ')" }; git status --short --branch</automated>
  </verify>
  <done>`git ls-remote` 返回的 GitHub `refs/heads/master` OID 等于本地 `HEAD`，fetch 后 ahead/behind 为 `0/0`，且不存在遗漏的有效工作树改动。</done>
</task>

</tasks>

<verification>
依次完成三项任务的自动化验证。最终必须同时满足：`origin` URL 与预期一致；未使用任何 force push；`git ls-remote --heads origin refs/heads/master` 的 OID 等于 `git rev-parse HEAD`；`origin/master...HEAD` 的 ahead/behind 为 `0 0`；`git status --porcelain=v1 --untracked-files=all` 无未解释条目。
</verification>

<success_criteria>
- 所有适合版本化的当前本地改动均已选择性提交，且用户改动没有被删除、回滚或覆盖。
- 同步前已 fetch 远端；远端变化通过 fast-forward 或对未推送提交的安全 rebase 协调，没有使用 force push。
- GitHub `origin/master` 与本地 `master` 指向同一提交，并由 `git ls-remote` 和 ahead/behind 双重验证。
- 没有秘密、环境文件、缓存、隐私证据或超大文件被误提交；没有有效本地改动被遗漏。
</success_criteria>

<output>
完成后，在 `.planning/quick/260720-cmj-github/` 创建执行摘要，并按 quick-workflow 约定更新 `.planning/STATE.md` 的 Quick Tasks Completed 记录。摘要必须包含本地/远端匹配的短 SHA、实际推送分支、提交的文件清单，以及任何明确保留在本地的排除项（仅写路径/类别，不写秘密内容）。
</output>
