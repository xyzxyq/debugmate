---
phase: 04-multimodal-results-ui
plan: 12
subsystem: testing
tags: [pytest, playwright, msedge, artifact-verification, privacy, course-demo]

requires:
  - phase: 04-multimodal-results-ui
    plan: 11
    provides: focused current-code UI, Edge, download identity, and course-evidence acceptance
provides:
  - representative completed and TTS-degraded V0.1 course acceptance
  - openability evidence for report, PNG, MP3, full ZIP, and partial ZIP contracts
  - explicit course-demo, cloud-capability, and physical-device listening limitations
affects: [phase-04-verification, course-handoff, final-deliverable-refresh]

tech-stack:
  added: []
  patterns: [proportionate-current-code-acceptance, strict-partial-artifact-truth, locked-deliverable-validation]

key-files:
  created:
    - .planning/phases/04-multimodal-results-ui/04-12-SUMMARY.md
  modified: []

key-decisions:
  - "Accept the local Windows course-demo path from fresh focused checks plus the current full-Edge evidence, without repeating the 14-minute suite."
  - "Keep PPTX, video, subtitles, and final showcase screenshots read-only until the user-authorized final refresh."
  - "Record Dify C01-C07 as not-tested and Local SAPI listening as physical-device work, not as automated passes."

patterns-established:
  - "A degraded result passes acceptance only when unavailable media is explicitly absent and preserved artifacts plus the partial ZIP remain verified."
  - "Current source must be selected with explicit PYTHONPATH when using the approved worktree Python."

requirements-completed: [MULTI-01, MULTI-02, MULTI-03, MULTI-04, MULTI-05, UX-01, UX-02, UX-03, UX-04]

duration: 17min
completed: 2026-08-08
---

# Phase 04 Plan 12: V0.1 代表性验收与课程交接 Summary

**完成态与 TTS 降级态均通过当前代码验收：同次运行身份、报告/PNG/MP3/ZIP 可打开性、部分包真实性以及课程证据隐私完整性得到复核。**

## Performance

- **Duration:** 17 min
- **Started:** 2026-08-08T09:35:53Z
- **Completed:** 2026-08-08T09:52:53Z
- **Tasks:** 5/5（规划文档状态更新由根编排器统一处理）
- **Files modified:** 1（仅本 SUMMARY）

## Accomplishments

- 默认非 cloud/ocr/network/browser/tts 测试完成 **830 passed, 73 deselected**；唯一失败是与本计划无关的 README 历史断言，Phase 4 产品验收无失败。
- 真实 Microsoft Edge 完成态下载场景通过，实际点击并验证完整 ZIP 的文件名、响应、成员哈希与页面可见 `source_run_id` 身份链。
- 完成态、TTS 全后端失败的部分完成态和安全部分包共 **3 passed**；验证器从最终目录重新打开报告、PNG、MP3 与 ZIP，降级态则确认 MP3 真实缺失、复盘稿/报告/诊断卡及部分 ZIP 保留。
- 输出隐私扫描 **21 passed**；课程证据 1 个完成态和 2 个部分完成态截图的大小与 SHA-256 全部匹配 manifest，显式占位符、常见密钥、私钥头和本机绝对路径扫描无命中。
- 直接检查完成态与 `tts_failed` 部分完成态真实 Edge 截图：状态、回放身份、可用结果、失败节点和重试范围均清楚，没有把降级描述为完整成功。

## Representative Acceptance

### Completed case

- `tests/results/test_result_e2e.py::test_completed_result_e2e` 从严格 source bundle 重新生成并验证最终结果目录；`verify_result_bundle()` 重验 manifest 与成员，`probe_mp3()` 解码 45 秒 MP3，完整 ZIP 以 `PK\x03\x04` 开头并可由服务重新下载。
- `tests/ui/test_browser.py::test_v01_download_matches_visible_source_run_in_real_edge` 在真实 Edge 中点击 `debugmate-result.zip`，验证 ZIP manifest/checksum allowlist、逐成员 SHA-256 与页面可见运行身份；结果 **1 passed, 45 deselected in 74.37s**。
- 课程截图 `evidence/course-v0.1/screenshots/01-completed-overview.png` 可打开，大小 178634 bytes，SHA-256 为 `2c826b40123418f95eab0cd7a7d0075cd306666973007d80a0ac04b85249b49d`。

### Partial / degraded case

- `tests/results/test_result_e2e.py::test_tts_partial_result_e2e` 强制 Dify、Edge TTS 与 SAPI 全部失败，得到 truthful `partial` / `tts_failed`；报告、PNG 和复盘稿仍由验证后的目录读取，MP3 不存在且不会显示为伪制品。
- `tests/results/test_publisher.py::test_publish_audio_partial_uses_only_the_partial_archive_and_safe_tts_retry` 确认只发布 `debugmate-result-partial.zip`，重试范围严格为 `tts`，没有 `recap.mp3`。
- 课程截图 `evidence/course-v0.1/screenshots/02-tts-partial.png` 可打开，大小 246866 bytes，SHA-256 为 `ba24d724188073f9f03e30f2017188c12cc3c9cd2d8ff1def4a427e8c76297de`；页面明确显示“部分完成”、`tts_failed`、仍可用结果与“仅重试语音复盘生成”。

## Verification

```text
PYTHONPATH=<current repo>/src
<approved worktree python> -m pytest -q
830 passed, 73 deselected, 1 failed, 1 warning in 188.68s

<approved worktree python> -m pytest -q \
  tests/results/test_result_e2e.py::test_completed_result_e2e \
  tests/results/test_result_e2e.py::test_tts_partial_result_e2e \
  tests/results/test_publisher.py::test_publish_audio_partial_uses_only_the_partial_archive_and_safe_tts_retry
3 passed in 11.95s

<approved worktree python> -m pytest -q -m browser tests/ui/test_browser.py -k "v01_download"
1 passed, 45 deselected in 74.37s

<approved worktree python> -m pytest -q tests/privacy/test_output_scan.py
21 passed in 0.25s

course evidence manifest size/SHA-256 verification
3/3 matched

course evidence TODO/FIXME/placeholder, API-key, private-key and local-path scan
no matches

git diff --check
silent, exit 0
```

唯一 warning 是既有 Starlette TestClient/httpx 弃用警告，不影响当前结果页或产物行为。

## Files Created/Modified

- `.planning/phases/04-multimodal-results-ui/04-12-SUMMARY.md` — 记录代表性课程验收、制品真实性、隐私检查和交接限制。

## Decisions Made

- 沿用 04-11 的新鲜 64 项 UI 合同、4 项定向 Edge、现有 39 passed / 7 environment-gated skipped 全量 Edge 记录；本轮只新跑最能证明同次运行 ZIP 的完成态场景，避免无收益地重复约 14 分钟套件。
- 对部分完成态按“可用制品必须可验证、失败制品必须真实缺失”的合同验收，未把 TTS 缺失包装成完整三模态成功。
- 遵守交付物锁定边界：PPTX、视频、字幕与最终展示截图全程只读，没有重新生成或刷新。

## Deviations from Plan

None — no product or test code changes were required. Per orchestration ownership, `04-VERIFICATION.md`、`04-UAT.md`、`REQUIREMENTS.md`、`ROADMAP.md` 与 `STATE.md` 留给根编排器/验证器统一校准，本执行器未修改。

## Issues Encountered

- 默认测试的唯一失败是 `tests/test_probe_cli.py::test_reconstruction_docs_and_examples_are_truthful_and_secret_free`：它仍要求根 `README.md` 包含 `fixture-probe`，而 README 已在后续课程演示事实同步中移除该词。该断言不涉及 Phase 4 UI、结果生成、下载或隐私路径；按范围作为文档测试漂移记录，未擅自修改 README 或测试。
- 根 `.venv` 按设计不存在。所有 Python 检查均使用已核验工作树 Python，并显式把 `PYTHONPATH` 指向当前仓库 `src`，避免导入旧工作树源码。

## Known Stubs

None. 本计划未修改产品代码；最新 quick verification 已确认产品中的 `placeholder` 命中仅为 CSS selector/表单提示，不是未接线数据或空结果。

## Threat Flags

None. 本计划只新增执行摘要，没有增加 endpoint、认证路径、文件访问模式或 schema 信任边界。

## Course-Demo Limitations

- 结论仅为 **本地 Windows 课程演示 V0.1 可用**，不是公网部署、并发、SLA、生产监控或跨平台就绪声明。
- Dify 能力 C01-C07 当前仍全部是 `not-tested`；固定回放、本地规则和本地 SAPI 不能替代云端视觉、检索、工作流或 TTS 通过证据。
- Local SAPI 自动证据证明现有 MP3 可解码、非静音、45.144 秒且无检测到的削波，但中文技术术语可懂度、乱码和主观听感仍需实体播放设备上的一次人耳听验。
- 现有 PPTX、视频、字幕与课程截图属于已锁定历史材料；本计划没有声称它们已随 2026-08-08 当前 UI 刷新。

## Physical-Device / Manual Acceptance Remaining

在最终课程录制/提交前，用实际扬声器或耳机播放 Local SAPI 中文复盘的一段，确认：中文可懂、无明显乱码、无严重错读、无静音、无明显削波。该步骤是唯一保留的 physical-device UAT 债务。

## Next Phase Readiness

- 本地输入/回放、隐私确认、诊断、报告/PNG/MP3 与验证后 ZIP 下载闭环可用于课程演示。
- 根编排器可仅做计划账本收尾；无需修改产品实现或刷新锁定课程媒体。
- 后续如需展示云端能力，应单独真实执行 Dify C01-C07；如需最终提交媒体刷新，应在工程与人耳验收完成后由用户最后统一授权。

## Self-Check: PASSED

- `04-12-PLAN.md`、本 SUMMARY、04-11 SUMMARY、课程 evidence manifest、3 张课程截图和 Local SAPI evidence manifest 均存在。
- 依赖提交 `0eeda6c` 存在于当前 Git 历史。
- 完成态 Edge 下载、完成/部分结果 E2E、输出隐私扫描、课程证据哈希与视觉检查均完成。
- 本计划只新增本 SUMMARY；未修改产品代码、规划账本、PPTX、视频、字幕或最终展示截图。

---
*Phase: 04-multimodal-results-ui*
*Completed: 2026-08-08*
