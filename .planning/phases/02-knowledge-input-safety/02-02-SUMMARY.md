---
phase: 02-knowledge-input-safety
plan: 02
subsystem: privacy
tags: [pillow, rapidocr, onnxruntime, ocr, image-redaction]
requires:
  - phase: 02-knowledge-input-safety
    plan: 01
    provides: strict preview/approval contracts, text redaction and cloud gate
provides:
  - validated PNG/JPEG screenshot byte boundary
  - lazy local RapidOCR adapter with deterministic token normalization
  - opaque deterministic screenshot redaction with value-free audit
  - portable preview-to-approval-to-upload screenshot chain
affects: [02-03-official-knowledge, phase-3-workflow, phase-4-results-ui]
tech-stack:
  added: [Pillow 12.3.0, RapidOCR 3.9.1, ONNX Runtime CPU 1.27.0]
  patterns: [single-byte-snapshot validation, fail-closed OCR, relative artifact paths]
key-files:
  created:
    - src/debugmate/privacy/ocr.py
    - src/debugmate/privacy/image_models.py
    - src/debugmate/privacy/image_redactor.py
    - src/debugmate/privacy/rapidocr_backend.py
  modified:
    - src/debugmate/privacy/models.py
    - src/debugmate/privacy/text_redactor.py
    - src/debugmate/gateway.py
    - pyproject.toml
key-decisions:
  - "Screenshot validation, Pillow decoding and SHA-256 use one bounded in-memory byte snapshot."
  - "Preview contracts store only portable case-relative screenshot paths; CloudGateway resolves them beneath an explicit local root."
  - "Unusable OCR geometry, OCR failure and stale-output cleanup failure all block preview creation and upload."
patterns-established:
  - "Real OCR is marker-isolated; deterministic tests inject an OcrBackend."
  - "Original screenshot paths and bytes never enter approval payloads or backend uploads."
requirements-completed: [INP-01, SAFE-01]
duration: 6h44m
completed: 2026-07-11
---

# Phase 2 Plan 02 Summary

**本地截图经过真实字节校验、OCR 敏感定位与不可逆像素遮挡后，才能进入预览确认和云端上传。**

## Performance

- **Duration:** 6h 44m（包含代理额度中断与依赖安装等待）
- **Started:** 2026-07-10T23:35:27Z
- **Completed:** 2026-07-11T06:19:23Z
- **Tasks:** 3
- **Files modified:** 14

## Accomplishments

- PNG/JPEG 依据真实字节识别，限制为 10 MiB、20 MP；校验事实与 SHA 来自同一字节快照。
- OCR 敏感框扩展 3 像素并 clamp 后绘制纯黑矩形，输出固定 RGB PNG 且移除元数据。
- RapidOCR 3.9.1 懒加载并归一化四点坐标、文本和分数；异常不回显路径或识别文本。
- Preview 只保存 `case_id/redacted.png` 与 SHA；HMAC 确认后 CloudGateway 只能从显式 root 上传已校验脱敏图。
- 同一截图跨源路径、跨 workspace 产生稳定 source/preview hash；失败重建会清除旧脱敏图。

## Task Commits

1. **图像验证与 OCR 端口** — `bc68e4e`
2. **确定性像素遮挡** — `03dfbf9`
3. **RapidOCR 与预览上传集成** — `18b9c08`

## Verification

- 默认全量：`167 passed, 1 deselected`
- 隐私离线套件：`104 passed, 1 deselected`
- 真实 OCR smoke：`1 passed in 14.51s`
- 依赖现场版本：RapidOCR `3.9.1`、ONNX Runtime `1.27.0`
- Ruff：通过；`pip check`：无损坏依赖；`git diff --check`：通过
- 仓库跟踪 PNG/JPEG 二进制：`0`

## Deviations from Plan

- 保留现有嵌套合同 `preview.redacted.redacted_screenshot_*`，没有增加重复扁平字段。
- 将绝对输出路径改为可移植相对 POSIX 路径，并扩展 CloudGateway root 安全解析。
- 增加入口重验证、旧输出清理、四方向越界 OCR 几何失败关闭和完整预览—确认—上传测试。
- source hash 使用截图内容 SHA 替代本地源路径，实现跨机器路径稳定。

## Issues Encountered

- 整体审查子代理因额度限制失败；主控按同一审查清单执行全量审计，并补跑真实 RapidOCR smoke。
- 首次依赖安装命令超时，但现场确认无残留后分包安装成功；没有将超时误报为失败或成功。

## User Setup Required

None - OCR CPU 依赖已锁定；真实 smoke 通过。默认测试仍排除 `ocr` marker，避免每次回归加载模型。

## Next Phase Readiness

- 文本与截图两条输入路径均已达到上传前自动脱敏、预览确认和失败关闭要求。
- `02-03` 可开始构建精选官方知识源、结构化摘录、覆盖率、检索追踪与 Dify dry-run 同步。

---
*Phase: 02-knowledge-input-safety*
*Completed: 2026-07-11*
