---
phase: 04-multimodal-results-ui
plan: 11
subsystem: ui
tags: [gradio, playwright, msedge, accessibility, verified-downloads, course-evidence]

requires:
  - phase: 04-multimodal-results-ui
    plan: 10
    provides: truth-state QA scenarios, server-held download resync, and real-browser ZIP verification
  - phase: quick-260721-uf9-debugmate
    provides: current student-first two-region UI and full Edge regression evidence
provides:
  - focused current-code acceptance for accessibility, long content, 200% zoom, and same-run ZIP identity
  - hash-checked three-case course engineering evidence set without refreshing final showcase assets
  - explicit V0.1 limits for physical-device listening and untested cloud capabilities
affects: [04-12-course-acceptance, course-materials, final-showcase]

tech-stack:
  added: []
  patterns: [proportionate-current-code-regression, evidence-manifest-hash-check, historical-evidence-truth-labeling]

key-files:
  created:
    - .planning/phases/04-multimodal-results-ui/04-11-SUMMARY.md
  modified: []

key-decisions:
  - "Use fresh focused current-code tests plus the existing independent VQ-14 pass instead of repeating the 14-minute full Edge suite."
  - "Preserve PPTX, video, subtitles, and final showcase screenshots for the explicitly deferred final refresh."
  - "Treat Local SAPI listening as physical-device acceptance and Dify C01-C07 as not-tested, not as completed cloud evidence."

patterns-established:
  - "Course closure may cite committed real engineering screenshots when their source commit and hash manifest remain explicit."
  - "A reused worktree virtual environment must set PYTHONPATH to the current repository src tree."

requirements-completed: [MULTI-01, MULTI-02, MULTI-03, MULTI-04, MULTI-05, UX-01, UX-02, UX-03, UX-04]

duration: 9min
completed: 2026-08-08
---

# Phase 04 Plan 11: V0.1 界面与下载闭环收尾 Summary

**当前学生诊断界面通过 64 项 UI 合同测试和 4 个真实 Edge 代表场景，同次运行 ZIP 身份链与三例课程工程证据均完成校验。**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-08T09:23:53Z
- **Completed:** 2026-08-08T09:32:23Z
- **Tasks:** 4/4
- **Files modified:** 1（仅本 SUMMARY）

## Accomplishments

- 新鲜运行 `test_app.py`、`test_view_state.py`、`test_callbacks.py`，共 **64 passed**；受控状态播报、稳定焦点、只读表格与下载 resync 合同保持通过。
- 新鲜运行 4 个真实 Microsoft Edge 场景，**4 passed, 42 deselected**：VQ-13 键盘/播报、VQ-15 200% 缩放、长内容/高图卡，以及正向同次运行 ZIP 下载。
- 正向下载测试实际点击 `debugmate-result.zip`，校验文件名、响应头、ZIP manifest/checksum allowlist、逐成员 SHA-256，并把 manifest `source_run_id` 与页面可见值绑定。
- 复核 `evidence/course-v0.1/manifest.json` 与 3 张真实工程 QA 截图；完成态、TTS 部分完成、诊断卡部分完成的大小和 SHA-256 均与清单一致。
- 未刷新 PPTX、视频、字幕或最终展示截图；仅引用已存在、来源清楚的真实 Edge/工程 QA 证据。

## Task Commits and Provenance

本计划没有新增产品实现；验收对象来自已提交实现：

1. **无障碍、长内容与当前学生 UI** — `0490535`（当前 UI/Edge 回归）
2. **受控 truth-state 与下载身份边界** — `4fbda84`（04-10 最终修复）
3. **课程小型工程证据集** — `57613c9`（真实 QA 截图与 manifest 来源提交）
4. **04-11 计划收尾记录** — 本 SUMMARY 的原子 docs 提交（以 `git log` 为准）

## Verification

### Fresh current-code checks

```text
PYTHONPATH=<current repo>/src
<verified worktree python> -m pytest -q tests/ui/test_app.py tests/ui/test_view_state.py tests/ui/test_callbacks.py
64 passed, 1 warning in 21.93s

<verified worktree python> -m pytest -q -m browser tests/ui/test_browser.py -k "vq_13 or vq_15 or v01_download or long_content"
4 passed, 42 deselected in 261.03s

git diff --check
silent, exit 0
```

唯一 warning 是既有的 Starlette TestClient/httpx 弃用警告，不影响产品行为。

### VQ-14 and full-suite evidence

- `.planning/phases/04-multimodal-results-ui/04-VERIFICATION.md` 已记录专用 truth-state runner 的 **VQ-14: 1 passed**。
- 2026-08-08 最新显式全量 Edge 记录为 **39 passed, 7 skipped, 0 failed**；6 个 skip 需要独立 QA server，1 个 skip 说明根 `.venv` 按设计不存在。
- 本轮没有重复约 14 分钟全量 Edge 套件；新鲜的 4 个代表场景覆盖了本计划其余浏览器合同。

### Course evidence integrity

| Case | File | Bytes | SHA-256 |
|---|---|---:|---|
| 完成态：报告、引用与结果包 | `screenshots/01-completed-overview.png` | 178634 | `2c826b40123418f95eab0cd7a7d0075cd306666973007d80a0ac04b85249b49d` |
| 语音失败的部分完成态 | `screenshots/02-tts-partial.png` | 246866 | `ba24d724188073f9f03e30f2017188c12cc3c9cd2d8ff1def4a427e8c76297de` |
| 诊断卡失败的部分完成态 | `screenshots/03-card-partial.png` | 256247 | `801cc5765744eee1aad63508a282dabc767f4b0939a114b840715fab169ba75e` |

清单另将长报告/长命令作为非截图案例绑定到真实 Edge 测试。本轮对该证据目录执行 TODO/FIXME/placeholder、本机用户名、常见 API key 和 private-key header 扫描，结果无命中。

## Files Created/Modified

- `.planning/phases/04-multimodal-results-ui/04-11-SUMMARY.md` — 记录当前代码的代表性验收、证据完整性和课程 V0.1 限制。

## Decisions Made

- 使用当前代码的定向回归，而不做无收益的完整 Edge 重跑；这同时保留了下载、键盘、缩放和长内容四条高价值路径。
- 专用 VQ-14 runner 硬编码根 `.venv`，而当前仓库有意只保留已核验工作树 venv；没有为一次复跑修改 runner 合同，采用独立验收文件中的通过证据并透明记录环境门控。
- 课程证据集是 2026-07-19 的真实工程 QA 证据，当前学生 UI 则由 2026-08-08 的三张现有 Edge 截图和 39/7 全量回归记录支撑；两者不混称为本轮新生成的“最终截图”。

## Deviations from Plan

None — no product or test code changes were required. The verification environment used the already approved worktree Python with explicit current-repository `PYTHONPATH` because root `.venv` is intentionally absent.

## Issues Encountered

- 首次单测收集从工作树 editable install 导入旧源码，报缺少 `render_verified_diagnosis`；显式设置 `PYTHONPATH` 为当前仓库 `src` 后，同一命令通过 64 项。这是环境选择问题，不是代码缺陷。
- 临时根 `.venv` junction 方案被工具安全策略拒绝，且未产生文件改动；根据已知环境门控与现有 VQ-14 通过记录，没有改 runner 或产品文件。

## Known Stubs

None. 本计划没有新增或修改产品实现；当前 UI quick verification 已确认匹配到的 `placeholder` 仅为 CSS selector/表单提示，不是空数据源。

## Threat Flags

None. 本计划仅新增执行摘要，没有增加 endpoint、认证路径、文件访问模式或 schema 信任边界。

## Physical-Device / Manual Acceptance Remaining

- **Local SAPI 中文语音人耳听验：仍需 physical-device。** 自动探针已经证明 MP3 可解码、非静音、时长与格式有效，但技术术语发音、可懂度和听感仍需在实际播放设备上听一次。
- **Dify C01-C07：仍为 `not-tested`。** 缺少账号/凭据时不得把本地规则或固定回放描述成云端成功。
- PPTX、视频、字幕和最终展示截图继续留到所有工程验收完成后的最后统一刷新。

## Next Phase Readiness

- 04-12 可直接做小型代表性验收与课程交接，无需重做完整 15 行视觉发布矩阵。
- 本地课程演示闭环具备输入/回放、隐私确认、诊断、文字/PNG/MP3 和验证后 ZIP 下载证据。
- 已知限制已单独列出，不应升级为生产就绪或云端已验证结论。

## Self-Check: PASSED

- `04-11-PLAN.md`、`04-VERIFICATION.md`、课程证据 manifest、3 张课程 QA 截图及当前完成态 Edge 截图均存在。
- 实现/证据提交 `0490535`、`4fbda84`、`57613c9` 均存在于 Git 历史。
- 三张课程截图的当前字节数和 SHA-256 与 manifest 完全匹配。
- 新鲜 UI 单测、定向 Edge、敏感/占位符扫描与 `git diff --check` 均通过。
- 未创建或刷新 PPTX、视频、字幕和最终展示截图。

---
*Phase: 04-multimodal-results-ui*
*Completed: 2026-08-08*
