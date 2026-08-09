---
phase: 07-real-input-privacy-ui
verified: 2026-08-09T20:24:33Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
requirements:
  INP-01: satisfied
  INP-02: satisfied
  SAFE-01: satisfied
  UX-01: satisfied
evidence_run_id: p7qa_45b179b0439b471da0c3d50735496916
---

# Phase 7: 真实输入与隐私预览接线 Verification Report

**Phase Goal:** 用户可在普通 Gradio 页面提交报错文本、代码、环境或截图，在任何云调用前查看并确认真实脱敏预览；live/replay 均保持本地、真实、可回放且不越过 Phase 08–10 边界。
**Verified:** 2026-08-09T20:24:33Z
**Status:** passed
**Re-verification:** No — initial goal-backward verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | 普通页面恰好提供报错文本、单张截图、代码、环境四个真实输入；报错文本与截图至少一项，代码/环境不能单独提交。 | ✓ VERIFIED | `src/debugmate/ui/app.py` 定义稳定的四个输入 ID；live config/primary-input tests passed in the 125-test focused run. Screenshot is one `gr.File`, `filepath`, PNG/JPG/JPEG only. |
| 2 | 截图在 OCR 前经过 cache-root、symlink/reparse、真实字节、10 MiB 和 20 MP 边界检查；原始上传在成功、失效和 OCR 失败后删除。 | ✓ VERIFIED | `_require_cached_upload()` validates confinement before bytes/OCR; `_delete_cached_upload()` is called in `finally`. Success, invalidation and OCR-failure deletion regressions passed. |
| 3 | 生产 RapidOCR 生成确定性遮挡；value-free 截图审计进入 `preview_hash`，无 OCR 文本、框、路径或匹配值泄露。 | ✓ VERIFIED | `ScreenshotPreviewAudit` is strict/frozen and included in the canonical hash payload. Sensitive, zero-finding, workspace-independent hash and failure-cleanup tests passed. Production OCR smoke: 1 passed, 0 skipped/failures/errors. |
| 4 | 浏览器批准能力绑定 session、单调 revision、TTL 和一次性 token；consume 在同一锁内比较并 pop，陈旧/复制/篡改/重复 token 失败关闭。 | ✓ VERIFIED | `LocalPreviewStore` implements revision CAS and atomic consume. Independent test covers change→approve, approve→change, slow N→change, N→N+1, duplicate approve, cross-session, expiry/tamper and replay invalidation; focused suite passed. |
| 5 | 已批准截图在二次 OCR 前重新 root-confine、SHA-256 复验和图像校验，并继续输出可纠正的六个抽取字段。 | ✓ VERIFIED | `ProductionExtractionProvider._verified_screenshot` wiring and `test_approved_screenshot_rehashes_before_ocr_and_keeps_six_fields` passed. The same `RapidOcrBackend` instance/root is injected into preview and extraction. |
| 6 | 普通 live 与 replay 在构造期均只构造本地规则、RapidOCR 和 SAPI；不 import/construct Dify、Edge TTS、HTTPX 或 outbound socket adapter。 | ✓ VERIFIED | `src/debugmate/ui/serve.py` has no Dify/Edge/httpx imports; constructor-poison live/replay test passed. Dify remains explicitly deferred to Phase 08. |
| 7 | mode、privacy 和 result 是正交状态；编辑会使预览 stale，批准不等于诊断完成，replay 不读取/覆盖 live 输入且先撤销 live authority。 | ✓ VERIFIED | `PrivacyPreviewState` has the exact eight states and pure precedence rendering. Exhaustive state, replay-first invalidation, previous-result and aria-live deduplication tests passed. |
| 8 | 单页保留脱敏输入、六字段、诊断/引用、报告、PNG、音频、纠错、重试和下载，并提供响应式、键盘、AA、灰度和 200% zoom 可用性。 | ✓ VERIFIED | Stable Phase 04 IDs remain wired. Final UI review is 24/24. Real Edge JUnit: 10 passed, 0 skipped/failures/errors, including 1024/768/375, keyboard, effective contrast and true DPR-2 zoom. Direct inspection of retained idle/ready/replay/zoom captures found no clipping or contradictory mode copy. |
| 9 | 最终 Edge evidence 是同一 current run 的精确 9 对 value-free JSON/PNG，语义、时间、身份及截图 SHA-256 全部一致。 | ✓ VERIFIED | `evidence/ui/phase7` contains exactly 9 JSON + 9 PNG for `p7qa_45b179b0439b471da0c3d50735496916`. `Assert-Phase7EvidenceSet` passed the exact allowlist, semantic map, PNG header/hash and time-window checks. Retained JUnit files under `.debugmate-runtime/phase7-qa/<run>/` prove OCR 1/1 and Edge 10/10 with zero skips. |
| 10 | 审查、安全、回归和冻结范围门禁均满足；Phase 04/08–10、PPTX、MP4、SRT 和课程截图未被 Phase 07 修改。 | ✓ VERIFIED | Code review is clean; security register closes 16/16 threats. Security/scope gate matched 14/14 frozen targets and scanned 37 files with 0 findings. Focused regression: 125 passed; Ruff: passed. No frozen media/future-phase diff exists. |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/debugmate/privacy/models.py` | Strict value-free screenshot audit | ✓ VERIFIED | Exists, substantive, validated and consumed by preview hashing. |
| `src/debugmate/privacy/text_redactor.py` | Text/image redaction and preview-hash binding | ✓ VERIFIED | Real audit counts and redacted screenshot hash flow into the strict preview. |
| `src/debugmate/ui/local_live.py` | Revision/session/TTL/one-time server authority | ✓ VERIFIED | Bounded store, deterministic eviction, lock-atomic publication/consumption and replay invalidation. |
| `src/debugmate/ui/presentation.py` | Orthogonal privacy/result/mode truth | ✓ VERIFIED | Exact states, precedence, permissions and deduplicated accessible announcements. |
| `src/debugmate/ui/app.py` | Four-field Gradio form, privacy preview and existing result page | ✓ VERIFIED | All stable input/preview/result IDs are wired; browser receives only redacted presentation and opaque capabilities. |
| `src/debugmate/ui/serve.py` | Shared production OCR and construction-time local-only graph | ✓ VERIFIED | One RapidOCR instance/root; local rules and SAPI only in ordinary assembly. |
| `scripts/run-phase7-real-input-qa.ps1` | Zero-skip Edge/OCR runner and atomic evidence promotion | ✓ VERIFIED | JUnit rejection, owned loopback process, exact inventory and rollback logic are substantive and tested. |
| `scripts/verify-phase7-security-scope.ps1` | Secret/path and frozen-scope gate | ✓ VERIFIED | Current clean execution passed; injected failure coverage is retained. |
| `evidence/ui/phase7/*` | Exact current value-free Edge evidence | ✓ VERIFIED | 18 formal files, exact 9-pair inventory, one run ID, all PNG hashes verified. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| Four Gradio inputs | `InputEnvelope` | `prepare_local_preview` | ✓ WIRED | Local primary-input gate, deterministic environment parsing and confined screenshot validation precede preview work. |
| `build_preview` | `PreviewBundle.preview_hash` | canonical payload with `screenshot_audit` | ✓ WIRED | Image audit facts are signed without image values/paths. |
| Input `.change()` events | `LocalPreviewStore` | shared `debugmate-case` queue + `invalidate_and_increment` | ✓ WIRED | Every input edit removes server/browser authority and disables confirmation. |
| Confirm button | Existing diagnosis service | `consume_current` → `approve_preview` → `diagnose_events(approved)` | ✓ WIRED | Only one current server-owned preview can enter diagnosis. |
| Approved screenshot | Six-field extraction | root confinement + rehash + validation + shared OCR | ✓ WIRED | No browser-provided approved path or payload is accepted. |
| Replay action | Fixed fixture result service | invalidate live token before allowlisted fixture lookup | ✓ WIRED | Replay is separately labeled and does not use live form values. |
| Edge tests | Formal evidence | owned loopback app + atomic staging/promotion | ✓ WIRED | Current JUnit and ledgers share the final run identity. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| Privacy preview | redacted error/code/environment/screenshot/audit | Four native inputs → strict local redaction/RapidOCR | Yes; real values are redacted and screenshot bytes are deterministically rewritten | ✓ FLOWING |
| Extraction disclosure | exception/traceback/package/version/device/path candidates | Approved redacted input → shared production extraction provider | Yes; second OCR read is hash/root verified | ✓ FLOWING |
| Local live result | verified result state/report/card/audio/download | Approved input → local workflow → existing result composer | Yes; focused and Edge flows exercise real local services | ✓ FLOWING |
| Replay result | fixed allowlisted fixture/result identity | Repository replay fixtures | Yes; explicitly replay-labeled with hashed identities | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Privacy/UI/adversarial regression | `pytest` on preview, real-input, local-live, app, view-state and extraction modules | 125 passed | ✓ PASS |
| Production RapidOCR | `pytest -q -m ocr tests/privacy/test_rapidocr_smoke.py` | 1 passed | ✓ PASS |
| Retained final JUnit truth | `Assert-JUnitZeroIssues` on final run OCR/Edge XML | OCR 1, Edge 10; zero skipped/failures/errors | ✓ PASS |
| Exact evidence semantics/hashes | `Assert-Phase7EvidenceSet` for final run | Exact 9 pairs validated | ✓ PASS |
| Frozen scope and secret/path scan | `verify-phase7-security-scope.ps1` | 14 targets matched; 37 files, 0 findings | ✓ PASS |
| Static quality | `ruff check src tests` | All checks passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|---|---|---|---|---|
| INP-01 | 07-01 through 07-05 | Four real inputs; text or screenshot required | ✓ SATISFIED | Exact components and primary-input gate are wired and tested. |
| INP-02 | 07-01 through 07-05 | Screenshot extracts and echoes six diagnostic fields | ✓ SATISFIED | Production OCR smoke, shared-backend identity and six-field rehash integration pass. |
| SAFE-01 | 07-01 through 07-05 | Redact before any input leaves local machine and retain audit | ✓ SATISFIED | Phase 07 constructs no cloud path; text/image audit is strict, hash-bound and user-visible. |
| UX-01 | 07-01 through 07-05 | One page shows redacted input, fields, citations, report, PNG and audio | ✓ SATISFIED | Existing result surfaces remain wired; real Edge replay/live privacy states and stable IDs pass. |

No additional orphaned Phase 07 requirement IDs were found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---:|---|---|---|
| `src/debugmate/ui/app.py` | 1365 | `return {}` | ℹ️ Info | Correct empty optional environment parse; it does not flow as a stub and real input populates it. |
| `src/debugmate/ui/app.py` | 1542–1565 | `placeholder=` | ℹ️ Info | Native input guidance, not placeholder implementation. |
| `src/debugmate/dify_live_evidence.py` | import | Pre-existing `subprocess` rejected by repository command-safety test | ⚠️ Warning (out of Phase 07) | Isolated command-safety run is 39 passed, 1 failed. The file is byte-unchanged from the Phase 07 baseline and is not imported or constructed by Phase 07 live/replay, so it does not invalidate this phase goal. It remains separately actionable debt. |
| GSD static verifier | — | Glob and multiline-regex false negatives | ℹ️ Info | The helper does not expand `evidence/ui/phase7/*.png|*.json` and misses several multiline/path patterns. Manual exact inventory, source, runtime, semantic and hash checks above supersede those syntactic misses. |

No blocker anti-pattern, stub, orphaned artifact, raw-value evidence field, or unapproved network construction was found in Phase 07 code.

### Human Verification Required

None. The approved validation strategy explicitly makes Phase 07 keyboard, zoom, responsive layout, OCR, privacy and evidence checks automated; current real Edge and production OCR gates ran with zero skips.

### Gaps Summary

No Phase 07 goal gaps remain. Dify live workflow construction is intentionally and explicitly Phase 08 work, not a deferred Phase 07 failure. The unrelated pre-existing command-safety failure should remain visible in repository-wide QA, but it has no execution or import path into Phase 07 and therefore does not block this goal.

---

_Verified: 2026-08-09T20:24:33Z_
_Verifier: Codex (gsd-verifier)_
