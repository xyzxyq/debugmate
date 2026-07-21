---
id: 260721-tdz-github-master
phase: quick-260721-tdz-github-master
plan: 01
type: quick
title: 记录远端核对并安全发布本地 master
wave: 1
depends_on: []
autonomous: true
files_modified:
  - .planning/quick/260721-tdz-github-master/260721-tdz-PLAN.md
  - .planning/quick/260721-tdz-github-master/260721-tdz-SUMMARY.md
  - .planning/STATE.md
  - .git/refs/heads/master
  - .git/refs/remotes/origin/master
requirements:
  - 将已核验仅本地领先的 master 连同本次 GSD 同步记录以非强制方式发布到 origin/master，并用实时远端引用与差异计数证明同步完成
must_haves:
  truths:
    - "执行前重新获取 origin 后，GitHub master 仍没有本机缺失的提交；若门禁事实变化，任务停止而不自行 merge、rebase 或覆盖历史。"
    - "现有 5 个本机提交保持原样，本次只追加 GSD quick 文档提交，不修改产品源码、ROADMAP.md，也不 amend、squash 或 force push。"
    - "最终 git ls-remote 返回的 refs/heads/master OID 等于本地 HEAD，fetch 后 HEAD...origin/master 的双向差异计数为 0 0。"
  artifacts:
    - path: ".planning/quick/260721-tdz-github-master/260721-tdz-PLAN.md"
      provides: "本次安全同步的可执行计划与范围边界"
    - path: ".planning/quick/260721-tdz-github-master/260721-tdz-SUMMARY.md"
      provides: "初始远端核对、首次推送 OID 与验证结果的版本化同步记录"
    - path: ".planning/STATE.md"
      provides: "Quick Tasks Completed 表与 last activity 的任务记录"
  key_links:
    - from: "local master"
      to: "origin/master"
      via: "git fetch、祖先/差异门禁、显式非强制 git push"
      pattern: "HEAD:refs/heads/master"
    - from: ".planning/quick/260721-tdz-github-master/260721-tdz-SUMMARY.md"
      to: "GitHub refs/heads/master"
      via: "记录 git ls-remote OID 与 rev-list 差异计数"
      pattern: "0 0"
---

<objective>
把已确认仅存在于本机的 5 个提交连同本次 GSD quick 同步记录安全发布到 GitHub `origin/master`，并留下可审计的远端验证证据。

Purpose: 让 GitHub 包含当前完整的本地提交历史与同步记账，同时严格避免误合并、历史改写、产品改动或把 push 的退出信息误当成远端完成证据。
Output: 已更新并提交的 quick PLAN/SUMMARY 与 STATE 记录、保留全部既有提交的远端 `master`，以及 `git ls-remote` 和双向差异计数均通过的最终证据。
</objective>

<context>
@AGENTS.md
@.planning/STATE.md
@.planning/quick/260720-cmj-github/260720-cmj-SUMMARY.md
@.planning/quick/260720-jac-github-master-worktree/260720-jac-SUMMARY.md
@C:/Users/20795/Documents/codex 第一次进化/docs/CODEX_EXPERIENCE_PROFILE.md

Planning evidence captured after the orchestrator's mandatory `git fetch origin --prune` gate on 2026-07-21:
- Repository root is `X:/PROJECT/校外实训`; active branch is `master`; origin is `https://github.com/xyzxyq/debugmate.git`; the worktree was clean before this plan was created.
- Local HEAD is `41362891ed75634224fc1f4d2f5a144ae0de9580`; fetched `origin/master` is `f031c6b4c78d6d16e046b34f9b0addac240fdfd0`.
- `HEAD..origin/master` is empty; `origin/master..HEAD` contains exactly 5 local commits; `git rev-list --left-right --count HEAD...origin/master` is `5 0`.
- Therefore the permitted integration is an ordinary fast-forward push from local `master`; no merge or rebase is required. Execution must fetch and revalidate this gate immediately before publishing because the remote can move after planning.
- The plan file itself is the only expected worktree change introduced by planning. No product source or `ROADMAP.md` belongs to this quick task.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Revalidate the publish gate and prepare GSD records</name>
  <files>.planning/quick/260721-tdz-github-master/260721-tdz-SUMMARY.md, .planning/STATE.md</files>
  <action>From `X:/PROJECT/校外实训`, confirm the repository root, current branch `master`, upstream, and exact origin URL, then run `git fetch origin --prune`. Require `origin/master` to remain an ancestor of `HEAD`, require `HEAD..origin/master` to be empty, and require the right-hand (remote-only) count from `git rev-list --left-right --count HEAD...origin/master` to be zero. The local-only count may increase from 5 only through this quick task's later documentation commits; before any task commit it must still be exactly 5. Query `git ls-remote --heads origin refs/heads/master` as an independent race check and require that OID to equal the freshly fetched `origin/master`. If any remote-only commit appears, the remote OID changes during the checks, the branch/URL is unexpected, or any worktree entry exists outside this quick plan, stop and report the evidence; do not merge, rebase, reset, stash, clean, checkout-overwrite, or push. Create `260721-tdz-SUMMARY.md` with the initial local/remote full OIDs, the five preserved local commits, branch/URL, gate commands, the exact documentation-only scope, and a note that its definitive verification section will be filled only after the first push succeeds. Update `.planning/STATE.md` last activity and append quick task `260721-tdz` using the table's existing columns, initially marking the record `Recorded` and using `this task` for the commit field until the first push OID exists. Do not change any other STATE content and do not modify `ROADMAP.md` or product files.</action>
  <verify>
    <automated>$root = (git rev-parse --show-toplevel).Trim() -replace '\\','/'; if ($root -ne 'X:/PROJECT/校外实训') { throw "Unexpected root: $root" }; if ((git branch --show-current).Trim() -ne 'master') { throw 'Expected master' }; if ((git remote get-url origin).Trim() -ne 'https://github.com/xyzxyq/debugmate.git') { throw 'Unexpected origin URL' }; git merge-base --is-ancestor origin/master HEAD; if ($LASTEXITCODE) { throw 'origin/master is not an ancestor of HEAD' }; $counts = ((git rev-list --left-right --count HEAD...origin/master).Trim() -split '\s+'); if ([int]$counts[0] -ne 5 -or [int]$counts[1] -ne 0) { throw "Expected pre-commit divergence 5/0, found $($counts -join '/')" }; if (-not (Test-Path -LiteralPath '.planning\quick\260721-tdz-github-master\260721-tdz-SUMMARY.md')) { throw 'SUMMARY missing' }; $unexpected = @(git status --porcelain=v1 --untracked-files=all | Where-Object { $_ -notmatch '^\?\? \.planning/quick/260721-tdz-github-master/' -and $_ -notmatch '^ M \.planning/STATE\.md$' }); if ($unexpected.Count) { throw "Unexpected worktree entries: $($unexpected -join '; ')" }; git diff --check</automated>
  </verify>
  <done>The live remote still has no commit missing locally; the five existing local commits are untouched; SUMMARY and the narrowly edited STATE record contain the baseline evidence; only the three authorized quick-document paths are pending publication.</done>
</task>

<task type="auto">
  <name>Task 2: Commit the quick records, push master, and capture first-push evidence</name>
  <files>.planning/quick/260721-tdz-github-master/260721-tdz-PLAN.md, .planning/quick/260721-tdz-github-master/260721-tdz-SUMMARY.md, .planning/STATE.md, .git/refs/heads/master, .git/refs/remotes/origin/master</files>
  <action>Review `git diff -- .planning/STATE.md` and both quick documents, confirm again that no product file or `ROADMAP.md` changed, and stage exactly the PLAN, SUMMARY, and STATE paths with `git add -- <three explicit paths>`; never use `git add -A`, `git add .`, or a wildcard. Run `git diff --cached --check`, inspect the cached name list, and require it to equal those three paths before creating one new Conventional Commit for the GSD synchronization record. Do not amend, squash, rebase, or otherwise rewrite any of the five existing local commits. Immediately fetch again and require the fetched/remote-only side is still zero and `origin/master` is still an ancestor of the new HEAD; then push explicitly with `git push origin HEAD:refs/heads/master`, without any force option. If push times out, first inspect active `git`, `git send-pack`, and `git pack-objects` processes and query `git ls-remote`; do not blindly repeat a still-running push. After the push completes, independently query `git ls-remote --heads origin refs/heads/master`, require it to equal this first documentation commit, fetch `origin master`, and require `git rev-list --left-right --count HEAD...origin/master` to be `0 0`. Only after those checks pass, update SUMMARY with the pushed full/short OID, `ls-remote` result, `0 0` count, preserved five-commit range, and non-force method; change the STATE row status to `Verified` and its commit column to that first pushed short OID. These two verification-record edits intentionally remain for the next additive commit so the evidence never relies on amending a published commit.</action>
  <verify>
    <automated>$firstPush = (git rev-parse HEAD).Trim(); $line = git ls-remote --heads origin refs/heads/master; if (-not $line) { throw 'origin/master missing from ls-remote' }; $remote = ($line -split '\s+')[0]; if ($remote -ne $firstPush) { throw "First push mismatch: local=$firstPush remote=$remote" }; git fetch origin master; $counts = ((git rev-list --left-right --count HEAD...origin/master).Trim() -split '\s+'); if ([int]$counts[0] -ne 0 -or [int]$counts[1] -ne 0) { throw "First push divergence: $($counts -join '/')" }; $changed = @(git status --porcelain=v1 --untracked-files=all); $invalid = @($changed | Where-Object { $_ -notmatch '^ M \.planning/(STATE\.md|quick/260721-tdz-github-master/260721-tdz-SUMMARY\.md)$' }); if ($invalid.Count) { throw "Unexpected post-push changes: $($invalid -join '; ')" }; git diff --check</automated>
  </verify>
  <done>The untouched five-commit local history plus the initial GSD record commit is published by ordinary push and proven remote-equal; SUMMARY and STATE now contain the observed first-push OID and verification, ready for a separate non-rewriting evidence commit.</done>
</task>

<task type="auto">
  <name>Task 3: Publish the verification record and prove final remote equality</name>
  <files>.planning/quick/260721-tdz-github-master/260721-tdz-SUMMARY.md, .planning/STATE.md, .git/refs/heads/master, .git/refs/remotes/origin/master</files>
  <action>Review the remaining SUMMARY and STATE diff, require that it only replaces the provisional quick-task status/commit entry and adds the actual first-push evidence, then explicitly stage only those two paths. Run cached diff/name checks and create a second additive Conventional Commit whose sole purpose is to version the remote-verification record. Do not amend the already-pushed documentation commit, rewrite the prior five commits, or compress the two documentation commits. Fetch once more, stop if a new remote-only commit appears, and push `HEAD:refs/heads/master` without force. Finally, use a fresh `git ls-remote --heads origin refs/heads/master` and require its full OID to equal local HEAD; fetch `origin master` and require `git rev-list --left-right --count HEAD...origin/master` to return `0 0`. Require `git status --porcelain=v1 --untracked-files=all` to be empty and prove the original local commit `41362891ed75634224fc1f4d2f5a144ae0de9580` plus all five pre-existing local-only commits remain ancestors of final HEAD. Return the final full/short OID and both remote checks as execution evidence; the final commit cannot truthfully contain its own hash, so its OID belongs in the executor result rather than another self-referential file edit.</action>
  <verify>
    <automated>$local = (git rev-parse HEAD).Trim(); $line = git ls-remote --heads origin refs/heads/master; if (-not $line) { throw 'origin/master missing from final ls-remote' }; $remote = ($line -split '\s+')[0]; if ($remote -ne $local) { throw "Final remote mismatch: local=$local remote=$remote" }; git fetch origin master; $counts = ((git rev-list --left-right --count HEAD...origin/master).Trim() -split '\s+'); if ([int]$counts[0] -ne 0 -or [int]$counts[1] -ne 0) { throw "Final divergence: $($counts -join '/')" }; git merge-base --is-ancestor 41362891ed75634224fc1f4d2f5a144ae0de9580 HEAD; if ($LASTEXITCODE) { throw 'Original local tip is no longer an ancestor' }; $pending = @(git status --porcelain=v1 --untracked-files=all); if ($pending.Count) { throw "Final worktree is not clean: $($pending -join '; ')" }; git diff --check; git log --oneline --decorate -7</automated>
  </verify>
  <done>Final local HEAD and GitHub refs/heads/master are identical, fetched divergence is 0/0, the worktree is clean, all five pre-existing commits remain intact, and both GSD record commits are additive and published.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GitHub `origin/master` → local decision | The remote may move after the completed planning gate; a fresh fetch and `ls-remote` must agree before each push. |
| Worktree/index → published history | Unrelated or product files could be accidentally staged unless the three/two documentation paths are explicitly allowlisted. |
| Local Git process → GitHub | A timeout or successful CLI exit does not alone prove the remote ref changed; remote OID and divergence must be checked independently. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-Q-TDZ-01 | Tampering | `origin/master` history | mitigate | Re-fetch before each push, require remote-only count zero and origin/master ancestry, prohibit force/rebase/amend/squash, and stop on a changed gate. |
| T-Q-TDZ-02 | Information Disclosure | staged documentation | mitigate | Stage only explicit GSD paths, inspect cached names/diff, and never print credentials or modify product/runtime evidence. |
| T-Q-TDZ-03 | Repudiation | push completion | mitigate | Record the first pushed OID in SUMMARY/STATE and verify each push with fresh `git ls-remote` plus fetched `0 0` divergence. |
| T-Q-TDZ-04 | Denial of Service | repeated push after timeout | mitigate | Inspect active Git processes and remote ref before any retry so an in-flight pack/upload is not duplicated. |
</threat_model>

<verification>
Completion requires all of the following simultaneously: no product source or `ROADMAP.md` changed; only PLAN, SUMMARY, and the narrow STATE record were committed; the original five local-only commits remain reachable and unmodified; neither documentation commit was amended/squashed; no force operation was used; final `git ls-remote --heads origin refs/heads/master` equals local HEAD; a subsequent fetch yields `HEAD...origin/master` count `0 0`; and the worktree is clean.
</verification>

<success_criteria>
- The completed preflight fact (`HEAD..origin/master` empty and local ahead by five) is preserved as the initial synchronization record and revalidated before mutation.
- The five existing local commits are published intact, followed only by two focused GSD documentation commits needed to avoid self-referential verification metadata.
- `.planning/quick/260721-tdz-github-master/260721-tdz-PLAN.md`, its SUMMARY, and the matching STATE row are committed; no product file or ROADMAP entry changes.
- GitHub `origin/master` and local `master` end at the same final OID, independently proven by `git ls-remote` and fetched `0 0` divergence.
- No merge, rebase, amend, squash, reset, stash, clean, force push, blanket staging, or deletion is used.
</success_criteria>

<output>
Complete `.planning/quick/260721-tdz-github-master/260721-tdz-SUMMARY.md` and the quick-task row in `.planning/STATE.md` as specified. Return the final full/short GitHub-matching OID, the final `git ls-remote` OID, the `0 0` difference count, and confirmation that only the authorized GSD documentation files were added or changed.
</output>
