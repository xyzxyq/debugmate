---
gsd_state_version: 1.0
milestone: v0.1
milestone_name: course-demo
status: complete
stopped_at: Phase 4 closure plans recorded and README probe contract restored
last_updated: "2026-08-08T09:52:00Z"
last_activity: 2026-08-08 -- Completed quick task 260808-opt README probe CLI truth repair
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 24
  completed_plans: 24
  percent: 100
---

# Project State

## Current Position

DebugMate V0.1 的路线图功能范围为 `status: complete`：6/6 phases complete，当前本地 Windows 课程演示闭环已经形成。

GSD 文件记账现已与路线图一致：现场共有 24 份阶段 PLAN 和 24 份对应 SUMMARY，即 24/24（100%）。Phase 4 的 `04-11-SUMMARY.md` 与 `04-12-SUMMARY.md` 已补齐；不得再使用旧的 22/24 或无法解释的 “26/26 plans completed” 口径。

当前位置：Phase 4 收尾计划已形成可审计记录，根 README 已补回真实 `fixture-probe` / `cloud-probe` 合同；正在关闭阶段代码审查与最终验证门禁。

## Current Verification Baseline

以下是 2026-08-08 已保存记录，不是本次文档任务重新运行后的固定承诺：

- 普通 UI 合同：`tests/ui/test_app.py` — 34 passed。
- 显式 Microsoft Edge 套件：39 passed、7 environment-gated skipped、0 failed。
- quick verifier：5/5 must-haves verified。
- Dify 能力矩阵：C01–C07 共 7 项全部为 `not-tested`；本地规则和固定回放不能作为云端视觉、检索、工作流或 TTS 的通过证据。

## Remaining UAT Debt

唯一显式 UAT 债务是 **Local SAPI recap human listening quality**：`blocked_by: physical-device`。

机器证据能够证明现有 MP3 可解码、非静音等客观属性，但不能替代人在实体播放设备上对中文可懂度、截断、乱码和明显发音问题的主观听验。

## Course Deliverables Boundary

仓库中已有 PPTX、视频、字幕和截图，但它们属于历史课程材料，不表示已随 2026-08-08 的最新 UI 与事实口径刷新：

- `deliverables/DebugMate-V0.1.pptx` — 历史版本，待最后统一刷新。
- `deliverables/DebugMate-V0.1-demo.mp4` — 历史版本，待最后统一刷新。
- `deliverables/DebugMate-V0.1-subtitles.srt` — 历史版本，待最后统一刷新。
- `evidence/course-v0.1/` 与其他截图 — 现有证据目录；最终截图待最后统一刷新。

本 quick task 不修改 PPTX、视频、字幕、最终截图或任何其他交付物。

## Next Order

1. 先维护本地课程演示、事实证据、README 与 STATE 的一致性。
2. 再按演示需要真实执行 Dify C01–C07；在能力矩阵仍为 `not-tested` 时不得宣称云端完成。
3. 安排 `physical-device` 上的 Local SAPI 中文复盘人耳听验。
4. 最后才统一更新 PPTX、视频、字幕和最终截图。

## Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260719-r5a | Refresh final dark workbench Edge evidence, PPT and video | 2026-07-19 | this commit | Historical | [260719-r5a-debugmate-gradio](./quick/260719-r5a-debugmate-gradio/) |
| 260719-gy7 | Create and synchronize private DebugMate GitHub repository | 2026-07-19 | Pending | Recorded | [260719-gy7-github-debugmate](./quick/260719-gy7-github-debugmate/) |
| 260719-h5z | Author and publish DebugMate README | 2026-07-19 | Pending | Recorded | [260719-h5z-debugmate-readme](./quick/260719-h5z-debugmate-readme/) |
| 260720-cmj | Synchronize local repository with GitHub and verify remote ref | 2026-07-20 | 76a431d | Verified | [260720-cmj-github](./quick/260720-cmj-github/) |
| 260720-d6u | Merge and publish complete Phase 1 project | 2026-07-20 | 4b304b5 | Verified | [260720-d6u-codex-phase-1-foundation-platform-gate-m](./quick/260720-d6u-codex-phase-1-foundation-platform-gate-m/) |
| 260720-jac | Synchronize GitHub updates into local worktrees | 2026-07-20 | f031c6b | Verified | [260720-jac-github-master-worktree](./quick/260720-jac-github-master-worktree/) |
| 260720-ksx | Optimize the student-friendly diagnosis UI | 2026-07-20 | 97cf1c4 | Verified | [260720-ksx-phase-4-ui-debugmate-windows](./quick/260720-ksx-phase-4-ui-debugmate-windows/) |
| 260721-tdz | Record remote verification and safely publish local master | 2026-07-21 | 5ecc77f | Verified | [260721-tdz-github-master](./quick/260721-tdz-github-master/) |
| 260721-uf9 | Redesign DebugMate as a student-first two-region diagnosis guide | 2026-08-08 | 0490535 | Verified | [260721-uf9-debugmate](./quick/260721-uf9-debugmate/) |
| 260808-nrg | Synchronize README and STATE with the current local course-demo truth | 2026-08-08 | 82a8d82 | Verified | [260808-nrg-readme-ui](./quick/260808-nrg-readme-ui/) |
| 260808-opt | Restore truthful README probe CLI commands and capability states | 2026-08-08 | 2dc5a83 | Verified | [260808-opt-readme-probe-cli](./quick/260808-opt-readme-probe-cli/) |
