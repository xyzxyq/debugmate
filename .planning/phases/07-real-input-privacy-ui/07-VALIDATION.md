---
phase: 07
slug: real-input-privacy-ui
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-09
---

# Phase 07 — Validation Strategy

> 真实输入、截图 OCR、隐私预览与一次性批准的分层反馈合同。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + Playwright 1.61.0（Microsoft Edge） |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest -q --disable-warnings --maxfail=1 tests\privacy tests\ui\test_real_input.py tests\ui\test_local_live.py tests\ui\test_app.py` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest`，随后 `.\.venv\Scripts\python.exe -m ruff check src tests` |
| **Estimated runtime** | quick ≤ 120 秒；offline full ≤ 900 秒；Edge gate ≤ 1200 秒 |

---

## Sampling Rate

- **After every task commit:** 运行该任务涉及的新测试文件、直接受影响的隐私/UI 测试和 scoped Ruff。
- **After every plan wave:** 运行默认离线全量 pytest 与全量 Ruff。
- **Before `/gsd-verify-work`:** 离线全量、显式 OCR smoke、Phase 07 Edge gate、秘密/路径扫描和冻结媒体检查全部通过。
- **Max feedback latency:** 单个任务的自动化反馈不超过 120 秒；长时 Edge 分组逐组保留最终计数。

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-W0-01 | planner assigns | 0 | INP-01, INP-02 | T-07-ENV | 固定 Python 3.13 环境可导入 Gradio/RapidOCR/Pydantic/Playwright 且 `pip check` 通过 | environment | `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"; .\.venv\Scripts\python.exe -m pip check` | ❌ W0 | ⬜ pending |
| 07-W0-02 | planner assigns | 0 | INP-01, SAFE-01 | T-07-RACE | 建立四输入、revision、token、OCR 和 local-only 的 RED 合同 | unit/callback | `.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_real_input.py tests\ui\test_local_live.py` | ❌ W0 | ⬜ pending |
| 07-PRIVACY | planner assigns | 1 | SAFE-01 | T-07-PATH, T-07-OCR | 截图审计进入 preview hash；失败不留 PNG/token/path | privacy | `.\.venv\Scripts\python.exe -m pytest -q tests\privacy` | ⚠️ extend existing | ⬜ pending |
| 07-STORE | planner assigns | 1 | INP-01, SAFE-01 | T-07-RACE, T-07-SESSION | session+revision+TTL+one-time 原子 compare-and-consume | unit/race | `.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_real_input.py tests\ui\test_local_live.py -k "revision or token or race or replay"` | ❌ W0 | ⬜ pending |
| 07-ASSEMBLY | planner assigns | 2 | INP-02, SAFE-01 | T-07-CLOUD | ordinary live/replay 构造期零 Dify/Edge/httpx/socket，生产 RapidOCR 共享 | integration | `.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis\test_extraction_providers.py tests\ui\test_real_input.py -k "ocr or local_only or construction"` | ⚠️ extend/new | ⬜ pending |
| 07-UI | planner assigns | 2 | INP-01, UX-01 | T-07-DOM | 四字段、三轴状态、稳定 ID、无 raw/token/path DOM 泄露 | structural/browser | `.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py tests\ui\test_view_state.py tests\ui\test_real_input.py` | ⚠️ extend/new | ⬜ pending |
| 07-EDGE | planner assigns | 3 | INP-01, INP-02, SAFE-01, UX-01 | T-07-A11Y, T-07-DOM | Edge 覆盖 idle/ready/stale/OCR/replay/响应式/键盘/200% 且工程截图不覆盖课程媒体 | browser | `.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py -k "phase7 or p7_"` | ❌ W0 namespace | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Threat References

| Ref | Threat | Required control |
|-----|--------|------------------|
| T-07-RACE | 输入变更、慢预览、重复批准的顺序竞态 | 单调 revision、共享 `debugmate-case` lane、锁内 publish/consume 比较 |
| T-07-SESSION | token 复制、过期、篡改或跨会话使用 | session+revision+TTL 绑定且一次性 pop |
| T-07-PATH | 任意路径、symlink 或脱敏输出路径注入 | upload root 约束、生成输出名、root confinement 与 SHA-256 复验 |
| T-07-OCR | OCR 失败泄露异常/路径或静默降级 | 固定 `ocr_unavailable`、无 token/PNG/批准、移除截图后才可恢复 |
| T-07-CLOUD | Phase 07 live/replay 构造网络适配器 | 构造期 poison Dify/Edge/httpx/socket，零调用、零实例 |
| T-07-DOM | raw input、秘密、token、签名、路径进入 DOM/config/storage | 仅 redacted presentation + 独立只读 capability URL |
| T-07-A11Y | 状态仅靠颜色、键盘/缩放不可达 | AA 深色文本 token、可见文字、原生控件、真实 Edge 门禁 |

---

## Wave 0 Requirements

- [ ] 修复 `.venv`：安装 `.[dev]`、校验 Python 3.13.5、依赖版本与 `pip check`。
- [ ] 新建 `tests/ui/test_real_input.py`，先固定四字段、主输入拒绝、revision/token/race/local-only 合同。
- [ ] 扩展 `tests/privacy/test_preview_integration.py`，固定截图审计、preview hash 与零 findings 文案。
- [ ] 为 `tests/ui/test_browser.py` 添加 Phase 07 selector/marker/evidence namespace，不覆盖 Phase 04 或课程最终截图。
- [ ] 为 ordinary `serve.py` 添加生产 RapidOCR 构造与 live/replay 零网络源代码/运行时门禁。

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 无 | — | Phase 07 的界面、OCR、竞态、无障碍和隐私边界均须自动化；工程截图只作为可复查证据，不替代断言 | — |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency targets are explicit
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-09
