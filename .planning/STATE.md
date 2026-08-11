---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: milestone
status: Phase 08 live acceptance awaiting user configuration
last_updated: "2026-08-11T18:00:00+08:00"
progress:
  total_phases: 10
  completed_phases: 7
  total_plans: 39
  completed_plans: 37
  percent: 70
---

# Project State

## Current Position

Phase: 08 (dify-unified-live-chain) — 08-01 至 08-06 COMPLETE，08-07 BLOCKED
Plan: 6 of 7；Phase 09 已提前完成 09-01 与 09-02，09-03 依赖 08-07
DebugMate V0.1 已完成 Phase 1–7。Phase 8 的离线合同、知识同步、Dify 适配、后端 provenance、实时编排、受控修复和 UI/service 接线已完成；唯一未执行项是 08-07 的真实 Dify Knowledge readback、当前应用同次 run、Edge 与 TTS 最终证据晋升。

GSD 文件记账：现场共有 39 份阶段 PLAN 和 37 份对应 SUMMARY；未完成的两份是 `08-07` 与依赖它的 `09-03`。阶段完成度仍为 7/10（70%），不得在真实云端验收前把 Phase 8 或 Phase 9 标为 complete。

Phase 9 的离线 Wave 1–2 已完成：四案例严格合同、V1–V4 同案例绑定、当前证据收集器、Phase 10 来源清单和冻结媒体门禁均已版本化；正式 ledger 原子晋升留给 09-03。

## Current Verification Baseline

以下记录区分既有能力证据、当前离线实现与尚未执行的最终真实云验收：

- 普通 UI 合同：`tests/ui/test_app.py` — 34 passed。
- 显式 Microsoft Edge 套件：39 passed、7 environment-gated skipped、0 failed。
- quick verifier：6/6 must-haves verified。
- 默认离线回归：845 passed、73 deselected、0 failed（1 个既有依赖弃用警告）。
- Phase 4 review fixes：102 passed，Ruff passed；3 个 Warning 已全部关闭。
- 2026-08-08 cloud bundle 已在版本化路径通过 `verify-bundle` 且零问题：C01、C02、C05 为 `pass`，C03、C04、C06、C07 为 `not-tested`。
- C07 已于 2026-08-09 重新通过正式 Dify live TTS gate；版本化 MP3 经 FFprobe 验证为单声道 MP3，并与 `tts-evidence.json` 的 SHA-256 一致。
- 2026-08-09 独立 live capture 证明 C03/C04 为 `pass`：C03 绑定 target-free request manifest、真实 PNG 上传与 exact VLM extraction；C04 绑定 console run 的 direct Knowledge Retrieval node output、chunk/source URL/locator/score。
- 当前可复算能力矩阵为 C01–C07 全部 `pass`。C06 绑定 distinct source/independent app 指纹、byte-exact re-export、相同规范化结构 SHA-256、空 differences，以及 authoritative reconstructed-app rerun 的安全 allowlist；总记录与三个内层产物均通过 Git tracked/not ignored 和精确哈希门禁。
- Phase 8 08-01～08-06 默认离线回归最新为 1107 passed、58 deselected、0 failed；计划级聚焦门禁与 Ruff 全绿。
- Phase 8 标准代码审查 iteration 2 为 clean；4 个 Warning 已全部原子修复。安全审计关闭 25/25 条登记威胁，OPEN 0；Nyquist 审计确认 14/14 executed tasks 均有直接自动化覆盖。
- Phase 9 09-01/09-02 共 47 个 evaluation 聚焦测试通过；所有 Phase 10 媒体路径仍由冻结门禁保护，尚未刷新。

## Remaining UAT Debt

Phase 4 的实体设备 Local SAPI 中文听验已由用户确认通过。当前唯一需要用户操作的验收前置条件是：配置 `DIFY_DATASET_API_KEY`、`DIFY_DATASET_ID` 与 `DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED=1`，并完全重启 Codex 使新用户环境变量进入当前进程。

## Course Deliverables Boundary

仓库中已有 PPTX、视频、字幕和截图，但它们属于历史课程材料，不表示已随 2026-08-08 的最新 UI 与事实口径刷新：

- `deliverables/DebugMate-V0.1.pptx` — 历史版本，待最后统一刷新。
- `deliverables/DebugMate-V0.1-demo.mp4` — 历史版本，待最后统一刷新。
- `deliverables/DebugMate-V0.1-subtitles.srt` — 历史版本，待最后统一刷新。
- `evidence/course-v0.1/` 与其他截图 — 现有证据目录；最终截图待最后统一刷新。

Phase 8 与 Phase 9 当前工作不修改 PPTX、视频、字幕或最终截图；这些文件只在 Phase 10 最后统一刷新。

## Next Order

1. 用户完成三个 Dify 环境变量配置并重启 Codex。
2. 执行 08-07：真实 17-source readback、当前 DSL/app 同次 run、严格 DiagnosisRecord、Edge/TTS/ZIP 与证据原子晋升；随后完成 Phase 8 最终验证。
3. 执行 09-03：用 08-07 当前证据生成四案例正式 ledger，并完成 Phase 9 审查、验证与收尾。
4. Phase 10 最后统一更新 PPTX、视频、字幕和最终截图，完成 freshness/claim/hash 与人工翻页/听验 QA。

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
| 260808-kmd | Add a versioned Dify-uploadable ModuleNotFoundError knowledge note | 2026-08-08 | this commit | Verified | [debugmate-module-not-found.md](../knowledge/notes/debugmate-module-not-found.md) |
| 260808-dsl | Version the Dify workflow DSL after a successful six-node re-import check | 2026-08-08 | this commit | Verified | [app.dsl.yml](../platform/dify/app.dsl.yml) |
| 260808-tts | Enable and live-verify the published Dify workflow text-to-speech API feature | 2026-08-09 | this commit | Verified | [app.dsl.yml](../platform/dify/app.dsl.yml) |
| 260809-fob | Version Dify C01-C07 evidence and synchronize matrix, README, and state truth | 2026-08-09 | ad2724f | Verified | [260809-fob-dify-c01-c07-readme-pptx](./quick/260809-fob-dify-c01-c07-readme-pptx/) |
| 260809-ghz | Version independent Dify C03/C04 evidence and preserve the accurate C06 blocker | 2026-08-09 | e3b9ed9 | Verified | [260809-ghz-dify-c03-c04-c06-dsl-readme-state-pptx](./quick/260809-ghz-dify-c03-c04-c06-dsl-readme-state-pptx/) |
| 260809-icj | Promote C06 through independent DSL roundtrip and authoritative rerun evidence | 2026-08-09 | task commits | Verified | [260809-icj-c06-pass-pptx](./quick/260809-icj-c06-pass-pptx/) |
