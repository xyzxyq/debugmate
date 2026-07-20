---
phase: 02-knowledge-input-safety
plan: 01
subsystem: privacy
tags: [pydantic, redaction, hmac, prompt-injection, evidence]
requires:
  - phase: 01-foundation-platform-gate
    provides: strict case contracts, backend port, atomic evidence bundles
provides:
  - strict input, candidate, preview and approval contracts
  - deterministic text redaction with value-free audit records
  - HMAC approval-only cloud gateway
  - prompt-injection marking and export rescan
affects: [02-02-image-redaction, 02-03-official-knowledge, phase-3-workflow]
tech-stack:
  added: []
  patterns: [value-free findings, canonical hash binding, approval-only cloud boundary]
key-files:
  created:
    - src/debugmate/privacy/models.py
    - src/debugmate/privacy/text_redactor.py
    - src/debugmate/privacy/approval.py
    - src/debugmate/privacy/output_scan.py
    - src/debugmate/gateway.py
  modified:
    - src/debugmate/settings.py
    - src/debugmate/evidence.py
key-decisions:
  - "Approval signatures bind the redacted payload, approval ID and timestamp in addition to case and preview hashes."
  - "Evidence JSON is scanned before writing and manifests are scanned again before publication."
patterns-established:
  - "Sensitive findings store spans, rule metadata and SHA-256 only, never matched values."
  - "Only ApprovedRedactedInput may cross CloudGateway."
requirements-completed: []
duration: 40min
completed: 2026-07-10
---

# Phase 2 Plan 01 Summary

**确定性文本脱敏、确认签名、云端类型门禁与导出二次扫描组成了可审计的本地隐私边界。**

## Performance

- **Duration:** 40 min
- **Started:** 2026-07-10T14:30:11Z
- **Completed:** 2026-07-10T15:10:42Z
- **Tasks:** 4
- **Files modified:** 15

## Accomplishments

- 输入至少包含报错文本或截图，候选、预览和确认对象均使用严格 Pydantic 合同。
- 九类文本规则覆盖密钥、密码、Token、邮箱、用户路径、私有主机、用户名和高熵值，多字段结果保持确定性哈希。
- HMAC 确认有效期为 30 分钟；篡改、错密钥、错案例和过期输入均在零后端调用时被拒绝。
- 中英文提示注入与导出秘密在写入 evidence 前被标记，异常只报告 JSON 路径和规则 ID。

## Task Commits

1. **输入与隐私合同** — `7502721`
2. **确定性文本脱敏** — `872cf60`
3. **HMAC 确认与云端门禁** — `e707682`
4. **提示注入与导出二次扫描** — `b82431c`

## Verification

- `python -m pytest -q` — 115 passed
- `python -m ruff check src tests` — passed
- `git diff --check` — passed

## Deviations from Plan

- 修复 `InputEnvelope` 默认 repr 泄漏原始输入。
- 扩展环境变量前缀识别，覆盖 `OPENAI_API_KEY`、`DB_PASSWORD` 等真实键名。
- 签名额外绑定脱敏字段、确认 ID 和时间，阻止独立篡改或续期。
- evidence 写入门禁暴露了旧 fixture 中未真正脱敏的虚构绝对路径，已替换为 `[REDACTED:WINDOWS_PATH]`。
- 元数据豁免改为格式感知，防止借 `case_id`/`sha256`/`run_id` 字段名绕过扫描。

## Issues Encountered

- 四个实现代理和四个审查代理均在时限内未产生可验收结果；控制器按既定超时降级规则接管，并保留 RED/GREEN 与审查记录。

## User Setup Required

None - this plan is fully offline. `DEBUGMATE_APPROVAL_KEY` is optional; missing时生成仅存在于进程内的随机密钥。

## Next Phase Readiness

- `02-02` 可复用同一候选、预览、确认和网关合同加入 OCR/像素级截图遮挡。
- INP-01、SAFE-01～SAFE-03 暂不标记完成，待 `02-02` 验证截图链路后统一关闭。

---
*Phase: 02-knowledge-input-safety*
*Completed: 2026-07-10*
