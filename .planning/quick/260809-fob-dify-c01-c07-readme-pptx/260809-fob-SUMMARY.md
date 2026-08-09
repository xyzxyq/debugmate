---
phase: quick-260809-fob-dify-c01-c07-readme-pptx
plan: 01
subsystem: evidence
tags: [dify, capability-matrix, sha256, ffprobe, pytest]
requires:
  - phase: phase-1-foundation-platform-gate
    provides: Dify cloud probe、证据 bundle 校验器与 live TTS gate
provides:
  - 版本化且可复算的 C01/C02/C05 cloud-probe 证据
  - 重新执行并经 FFprobe 验证的 C07 Dify MP3 证据
  - pass 状态必须绑定已跟踪文件与实算 SHA-256 的回归门禁
  - 与能力矩阵一致的两份 README 和项目状态口径
affects: [dify, course-evidence, readme, state]
tech-stack:
  added: []
  patterns: [versioned-live-evidence, pass-to-tracked-file-sha256]
key-files:
  created:
    - evidence/dify-live/README.md
    - evidence/dify-live/2026-08-09/tts/dify-recap.mp3
    - evidence/dify-live/2026-08-09/tts/tts-evidence.json
  modified:
    - .gitignore
    - platform/dify/capability-matrix.json
    - tests/test_probe_cli.py
    - platform/dify/README.md
    - README.md
    - .planning/STATE.md
key-decisions:
  - "C01/C02/C05/C07 只有在版本化证据文件已跟踪且 SHA-256 可复算时标记 pass。"
  - "C03/C04/C06 缺少各自独立版本化执行证据，因此保持 not-tested。"
patterns-established:
  - "Capability pass gate: repository-relative regular file + not ignored + git tracked + matching lowercase SHA-256."
requirements-completed: []
duration: 10min
completed: 2026-08-09
---

# Quick 260809-fob: Dify C01-C07 Evidence Truth Summary

**真实 cloud-probe 与 Dify TTS 产物已进入 Git 事实源，C01/C02/C05/C07 由已跟踪文件和实算 SHA-256 支撑，未独立取证的 C03/C04/C06 保持 `not-tested`。**

## Performance

- **Duration:** 10 min
- **Started:** 2026-08-09T03:31:48Z
- **Completed:** 2026-08-09T03:41:31Z
- **Tasks:** 3
- **Files modified:** 15（不含本 SUMMARY）

## Accomplishments

- 将 2026-08-08 live cloud-probe 六个 JSON 原样复制到 `evidence/dify-live/`，复制前后均通过 `verify-bundle`，逐文件 SHA-256 一致。
- 重新执行正式 Dify TTS gate，保存 46.2 秒、单声道、739200 字节的 MP3，并用 FFprobe 与元数据哈希双重绑定。
- 增强能力矩阵测试，拒绝绝对/越界/目录/缺失/ignored/未跟踪/哈希不匹配的任何 `pass` 证据。
- 同步根 README、Dify README 与 STATE；课程 PPTX、视频、字幕和截图保持未修改。

## Final C01-C07 Status

| Capability | Status | Versioned evidence | SHA-256 / reason |
|---|---|---|---|
| C01 | `pass` | `evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/dify-upload.json` | `608ebdbd5990f3e09f6cafd1682ff25441057768e1c59506e611531831b3cab1` |
| C02 | `pass` | 与 C01 相同的真实上传响应 | `608ebdbd5990f3e09f6cafd1682ff25441057768e1c59506e611531831b3cab1` |
| C03 | `not-tested` | — | 缺少真实截图视觉抽取的独立版本化执行证据 |
| C04 | `not-tested` | — | 缺少 retrieval chunk 与来源元数据的独立版本化证据 |
| C05 | `pass` | `evidence/dify-live/2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/diagnosis.json` | `75b2d9a8c2b555418173410592222e8d504fcc7530779ccbae652770658d0d26` |
| C06 | `not-tested` | — | DSL 和历史观察不能替代导出、重导入、复跑的版本化执行记录 |
| C07 | `pass` | `evidence/dify-live/2026-08-09/tts/dify-recap.mp3` | `a7d7821743b4364e1278b650b80e3d869ce2d06621a0745a4eb5fd45bca02328` |

## Verification Results

- Historical and versioned cloud bundle: `verify-bundle` returned `{"issues": [], "ok": true}`; exact status counts were 3 `pass`, 4 `not-tested`.
- Fresh real C07 gate: `tests/results/test_tts_live.py::test_live_dify_tts_gate` with explicit `cloud and tts` marker — `1 passed in 5.86s`.
- FFprobe: codec `mp3`, channels `1`, duration `46.2s`, size `739200` bytes.
- Capability/documentation focused tests: `2 passed`.
- Full `tests/test_probe_cli.py`: `20 passed in 1.54s`.
- Ruff: `All checks passed!` for `tests/test_probe_cli.py`.
- Secret/personal-path scan: no credential values, authorization secrets, recap text, or personal absolute path found.
- Scoped diff and frozen deliverable checks: passed; no PPTX, MP4, SRT, final screenshot, ROADMAP, REQUIREMENTS, PROJECT, DSL, or product code changes.

## Task Commits

1. **Task 1: 固化并复验真实 cloud-probe 与 Dify TTS 证据** — `25cdf49`
2. **Task 2 RED: 新增 pass→tracked file→SHA-256 回归门禁** — `0e3edc8`
3. **Task 2 GREEN: 更新 C01-C07 能力矩阵** — `ad2724f`
4. **Task 3: 同步 Dify README 与根 README** — `1b452c0`

`.planning/STATE.md` 按计划已更新但未包含在 Task 3 提交中；根 quick orchestrator 将与 PLAN/SUMMARY 一起提交编排文档。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 显式选择 cloud/tts marker 才实际执行 live gate**

- **Found during:** Task 1
- **Issue:** 按节点名运行时受仓库默认 pytest marker 过滤，结果为 `1 deselected`，没有网络调用或产物。
- **Fix:** 在同一专用 `--basetemp` 下显式添加 `-m "cloud and tts"`；这是唯一一次真实 Dify 调用。
- **Verification:** `1 passed in 5.86s`，且仅生成一个 `dify.mp3`。
- **Committed in:** `25cdf49`

**2. [Rule 1 - Bug] 修复新增测试的一处 Ruff 长行**

- **Found during:** Task 2 GREEN
- **Issue:** 集合推导断言为 104 字符，触发 E501。
- **Fix:** 提取 `passing_ids` 局部变量并保持断言语义不变。
- **Verification:** 两项 focused tests 通过，Ruff 全通过。
- **Committed in:** `ad2724f`

---

**Total deviations:** 2 auto-fixed（1 blocking，1 formatting bug）
**Impact on plan:** 两项均为完成既定门禁所需的局部修正，没有扩大文件或产品范围。

## Issues Encountered

- `git check-ignore -v` 会打印命中的反向放行规则；实际 ignored 状态使用不带 `-v` 的退出码确认，live evidence 返回 1（未忽略）。

## Known Stubs

None. 能力矩阵中 C03/C04/C06 的 `null` 证据字段是 `not-tested` 状态的明确合同要求，不是 UI 或数据源占位。

## Authentication Gates

None. 所需 Dify 配置已从进程环境读取，未打印或保存值；真实 C07 gate 正常通过。

## Decisions Made

- 保留 C03/C04/C06 为 `not-tested`，因为 DSL 节点、输出字段与历史文字均不能替代独立可复算执行证据。
- C01 与 C02 共享同一真实上传响应；C05 指向严格校验后的诊断 JSON；C07 指向 FFprobe 验证后的 MP3。

## Next Phase Readiness

- 仓库已具备可审计的 C01/C02/C05/C07 证据链和自动回归门禁。
- 若课程演示需要扩大 Dify 声明范围，下一步只能分别补齐 C03、C04、C06 的真实版本化证据。
- 课程交付物仍冻结，本 quick 未刷新 PPTX、视频、字幕或最终截图。

---
*Quick: 260809-fob*
*Completed: 2026-08-09*

## Self-Check: PASSED

- All declared evidence, matrix, README, test, STATE, and SUMMARY files exist.
- Task commits `25cdf49`, `0e3edc8`, `ad2724f`, and `1b452c0` exist.
- Final aggregate verification passed; orchestration artifacts remain intentionally uncommitted for the root executor.
