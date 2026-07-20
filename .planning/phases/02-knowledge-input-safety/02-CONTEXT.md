# Phase 2: 知识库与输入安全 - Context

**Gathered:** 2026-07-10  
**Status:** Approved for planning and execution

<domain>
## Phase Boundary

本阶段建立两条底座：精选官方知识源自动化，以及本地输入/输出安全。诊断推理、字段纠错 UI、PNG/MP3 和 Gradio 属于后续阶段。
</domain>

<decisions>
## Locked Decisions

- **D2-01:** 知识库采用精选官方源自动化，每个产品家族 2–4 个页面，不做无边界爬取。
- **D2-02:** 仓库保存结构化中文诊断摘录、来源锚点和哈希，不保存完整网页快照。
- **D2-03:** 文本、代码、环境和截图自动脱敏；用户确认预览后才允许进入云端。
- **D2-04:** 云端公开入口只接受 `ApprovedRedactedInput`，类型合同阻止绕过确认。
- **D2-05:** OCR 使用 RapidOCR + ONNX Runtime CPU；测试默认使用虚构截图和 fake OCR。
- **D2-06:** 所有日志、代码、截图 OCR 和知识正文视为不可信数据，不能覆盖系统策略或触发动作。
- **D2-07:** 首版知识笔记仅包含确定性摘录事实；在具备独立蕴含验证器前，可选 LLM 文本不得进入 Markdown、manifest 或 Dify 同步内容。
- **D2-08:** 真实来源抓取、OCR 模型准备和 Dify 同步使用独立 marker；默认测试完全离线。
</decisions>

<canonical_refs>
- `docs/superpowers/specs/2026-07-10-phase2-knowledge-input-safety-design.md`
- `docs/superpowers/plans/2026-07-10-phase2-text-redaction-approval.md`
- `docs/superpowers/plans/2026-07-10-phase2-image-redaction.md`
- `docs/superpowers/plans/2026-07-10-phase2-official-knowledge.md`
- `.planning/REQUIREMENTS.md` Phase 2 requirements
</canonical_refs>
