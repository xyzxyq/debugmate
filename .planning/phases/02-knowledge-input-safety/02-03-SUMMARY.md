---
phase: 02-knowledge-input-safety
plan: 03
subsystem: knowledge
tags: [official-sources, html-extraction, reproducible-build, dify-sync, retrieval-audit]
requires:
  - phase: 02-knowledge-input-safety
    plan: 01
    provides: privacy scan, evidence gate and prompt-injection marking
  - phase: 02-knowledge-input-safety
    plan: 02
    provides: screenshot validation, OCR redaction and approval boundary
provides:
  - strict 17-source official registry across seven product families
  - allowlisted fetch and deterministic structured note build
  - coverage, retrieval trace and honest offline hit-rate evidence
  - sealed Dify sync plan with 800/120 chunk configuration and readback contract
  - fail-closed binary evidence boundary for Phase 2
affects: [phase-3-workflow, phase-4-results-ui, phase-5-evaluation]
tech-stack:
  added: [beautifulsoup4 4.15.0, jsonschema 4.26.0]
  patterns: [content-addressed-build, exact-host-fetch, external-build-trust-anchor, zero-http-dry-run]
key-files:
  created:
    - knowledge/sources.json
    - knowledge/eval_queries.json
    - src/debugmate/knowledge/fetcher.py
    - src/debugmate/knowledge/extractor.py
    - src/debugmate/knowledge/build.py
    - src/debugmate/knowledge/sync.py
    - src/debugmate/knowledge/retrieval.py
    - scripts/build_knowledge.ps1
  modified:
    - knowledge/manifest.schema.json
    - src/debugmate/evidence.py
    - src/debugmate/cli.py
key-decisions:
  - "Official HTML is never committed as a page snapshot; only attributed structured notes and hashes are retained."
  - "Unverified LLM summaries are excluded from authoritative knowledge notes until an entailment verifier exists."
  - "Dify execution validates and snapshots the complete sealed plan before the first HTTP request."
  - "Phase 2 refuses MP3 and unknown binary evidence; audio publication is deferred to the Phase 4 trusted TTS chain."
patterns-established:
  - "Offline retrieval requires out-of-band expected build identity, so a build directory cannot self-authorize rewritten content."
  - "Cloud and online operations remain opt-in; the default wrapper is fixture-based and credential-free."
requirements-completed: [SAFE-02, SAFE-03, KNOW-01, KNOW-02, KNOW-03, KNOW-04, KNOW-05]
duration: 17h13m
completed: 2026-07-12
---

# Phase 2 Plan 03 Summary

**17 个精选官方来源已形成可重建、可审计、默认离线且安全失败的知识管线。**

## Performance

- **Duration:** 17h 13m（包含多轮独立对抗审查与在线源漂移修复）
- **Started:** 2026-07-11T14:32:01+08:00
- **Completed:** 2026-07-12T07:44:56+08:00
- **Tasks:** 5
- **Files modified:** 31

## Accomplishments

- 严格登记 17 个官方来源，覆盖 Python、pip、PyTorch、CUDA、Hugging Face、Ultralytics 和 Windows 七个产品族。
- 抓取只允许 HTTPS 与精确主机；跨域/站内重定向、超限响应、错误内容类型和结构漂移均安全失败。
- 从标题锚点确定性摘录短段落，构建内容寻址 Markdown；不提交完整网页，不允许未经蕴含验证的大模型摘要进入权威知识库。
- 输出七类覆盖率、固定查询检索 trace、命中率与盲区；离线运行明确标记 `backend=offline_fixture`，不冒充 Dify 云检索。
- Dify 同步默认 dry-run、零 HTTP；真实执行前验证密钥、删除确认、路径、哈希、完整文件快照、来源元数据、800/120 分块和回读一致性。
- 补强 evidence 边界：PNG 仅经解码/去元数据/重编码后发布；未知二进制和 MP3 在 Phase 2 全部拒绝，音频留给 Phase 4 的可信生成链。

## Task Commits

1. **官方来源严格登记表** — `94e7f42`, `bb9b559`
2. **安全抓取与结构化摘录** — `cf81535`, `d90a5df`
3. **确定性知识笔记构建** — `23b2c3a`, `6203b77`, `573e825`
4. **覆盖率与 Dify 同步预演** — `fd97c78`, `2d24dc1`
5. **检索追踪与命中率评测** — `8544273`, `f8fca8b`, `3a7c1df`
6. **阶段级安全与完整性加固** — `c0b2735`, `e4bcd94`, `c12f704`, `3e2020b`, `8e493a1`, `9d1a09e`, `479ad52`

## Verification

- 全仓离线：`279 passed, 19 deselected`
- 一键离线知识流程：`91 passed, 18 deselected`，构建 `ready/syncable`，Dify `executed=false`
- 一键在线知识流程：17/17 官方来源构建成功，17 个结构化笔记，Dify dry-run `operation_count=17`
- Ruff：通过；`pip check`：无损坏依赖；`git diff --check`：通过
- 最终独立对抗复审：`REVIEW CLEAN`

## Deviations from Plan

- PyTorch、CUDA 与 Ultralytics 的原登记 URL 已按实时直接地址修正，仍保持精确官方主机，不通过放宽重定向规则规避漂移。
- 可选 LLM 摘要被完全排除在同步知识笔记之外；在引入蕴含验证器前只保留确定性摘录。
- 增加带外构建身份参数，防止攻击者修改笔记后同时重算目录内所有无密钥哈希来自我授权。
- 原计划中的音频 evidence 写入被收紧为 Phase 2 禁止；因为仅把文本和任意 MP3 同时传入不能证明语义派生关系。

## External Gates

- 未执行真实 Dify 数据集写入和远端回读：需要账号、数据集 ID 与 API 密钥；当前仅通过严格契约和 MockTransport 验证。
- 未生成或发布 MP3：可信 TTS、音频有效性和同一诊断派生证明属于 Phase 4。

## Next Phase Readiness

- Phase 3 可直接复用脱敏输入、官方知识构建、检索 trace、引用锚点、Dify 同步契约和 evidence 安全门禁。
- 在线源、Dify 和未来 TTS 的真实运行结果必须继续与离线 fixture/模拟证据分开标记。

---
*Phase: 02-knowledge-input-safety*
*Completed: 2026-07-12*
