# Phase 3: 可追溯诊断工作流 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-12
**Phase:** 03-可追溯诊断工作流
**Mode:** `--auto`（用户已授权始终选择推荐方案）
**Areas discussed:** 抽取纠错、信息充分性、路由证据、结构化生成安全

---

## 抽取事实与纠错重跑

| Option | Description | Selected |
|---|---|---|
| 结构化事实草稿 + correction overlay | 每字段保存来源/置信度/定位，用户修改形成新 revision，保留审计链 | ✓ |
| 直接修改模型输入文本 | 简单，但无法区分 OCR/VLM 原候选与用户纠正 | |
| 由大模型自动修正 OCR | 人工少，但会把未验证推断伪装成事实 | |

**Auto choice:** 结构化事实草稿 + correction overlay。
**Rationale:** 最符合 DIAG-06、可回放和课程证据要求，并可复用 Phase 2 的预览/审批哈希模式。

---

## 信息充分性与有限追问

| Option | Description | Selected |
|---|---|---|
| 类别充分性矩阵，最多三问 | 可测试、可解释，问题只针对会改变结论的缺失字段 | ✓ |
| LLM 自由追问 | 灵活但难以保证数量、去重和价值 | |
| 不追问直接诊断 | 最快，但容易编造确定性根因 | |

**Auto choice:** 类别充分性矩阵，最多三问。
**Rationale:** 满足 INP-03，并允许证据不足时安全结束。

---

## 路由、证据与不确定性

| Option | Description | Selected |
|---|---|---|
| 规则优先 + 受限模型补充 + unknown | 高频报错稳定、低置信度不强行分类 | ✓ |
| 全部交给 LLM 分类 | 实现短但不稳定、难以复现 | |
| 纯关键词路由 | 可复现但对复合报错和截图抽取容错不足 | |

**Auto choice:** 规则优先 + 受限模型补充 + unknown。
**Rationale:** 同时兼顾可复现性与复杂案例，并使置信度和冲突可见。

| Option | Description | Selected |
|---|---|---|
| v1 minor 契约升级，显式 fact/citation support links | 根因与事实、知识锚点形成机器可验关系 | ✓ |
| 保持字符串列表隐式对应 | 兼容性高，但无法可靠验证引用支撑 | |
| 只在报告文本中写引用 | 展示容易，机器验证和多模态一致性弱 | |

**Auto choice:** v1 minor 契约升级，显式 support links。
**Rationale:** DIAG-03 需要结构级证据绑定，Phase 4 也需要稳定单一事实源。

---

## 结构化生成与安全失败

| Option | Description | Selected |
|---|---|---|
| 云端候选 + 本地裁决 + 一次受控修复 | 保留平台效率，同时让 Schema、引用和安全由本地确定 | ✓ |
| 接受 Dify 最终 JSON | 工程少，但模型/平台漂移会直接污染 evidence | |
| 完全本地无模型 | 最可控，但不符合多模态智能体目标且诊断能力受限 | |

**Auto choice:** 云端候选 + 本地裁决 + 一次受控修复。
**Rationale:** 延续现有窄适配器和严格 Pydantic 边界；第二次失败必须显式终止。

| Option | Description | Selected |
|---|---|---|
| 命令只作为结构化数据展示 | 标注平台、影响、预期和回退，永不执行 | ✓ |
| 允许安全命令一键运行 | 用户体验更快，但超出 v1 安全边界 | |
| 不输出命令 | 最安全但降低诊断可执行性 | |

**Auto choice:** 命令只作为结构化数据展示。
**Rationale:** 满足 SAFE-04，并保留学生实际排障所需的可操作步骤。

---

## the agent's Discretion

- 稳定 ID 编码、阈值常量、规则表组织和 CLI 名称。
- 受控修复位于适配器还是领域服务，只要重试次数和隐私边界可测试。

## Deferred Ideas

- 最终字段编辑 UI 和统一结果页 — Phase 4。
- 自动运行修复命令 — v1 不实现。
- 提示词多版本定量比较 — Phase 5。
