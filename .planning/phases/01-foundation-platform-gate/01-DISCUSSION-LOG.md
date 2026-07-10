# Phase 1: 工程骨架与平台能力闸门 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-10
**Phase:** 01-工程骨架与平台能力闸门
**Mode:** Auto — recommended defaults selected under the user's low-manual-work preference
**Areas discussed:** 平台能力闸门、诊断合同、证据目录、仓库边界

---

## 平台能力闸门

| Option | Description | Selected |
|--------|-------------|----------|
| Dify主路径 + 4小时闸门 | 最强的DSL、RAG元数据和API可追溯性；失败后按预设路径降级 | ✓ |
| Coze主路径 | 初次人工配置较少，但完整导出和可重建证据较弱 | |
| 纯Python主路径 | 最可控，但会增加RAG和模型编排工作量 | |

**Auto choice:** Dify主路径 + 4小时闸门。

## 诊断合同

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic严格Schema先行 | 云端和本地共享契约，阻止静默字段漂移 | ✓ |
| 自由JSON + 后处理 | 上手快，但多模态和评测容易各说各话 | |
| 纯文本首版 | 无法稳定派生证据和多模态产物 | |

**Auto choice:** Pydantic严格Schema先行；`case_<uuid4 hex>` 作为案例标识。

## 证据目录

| Option | Description | Selected |
|--------|-------------|----------|
| 每案例自包含目录 | 便于回放、打包、哈希和课程证据追溯 | ✓ |
| 单个全局日志文件 | 简单但难以关联多种产物和失败状态 | |
| 只依赖Dify日志 | 不可移植，平台变化后无法重建 | |

**Auto choice:** `evidence/<case_id>/` 自包含目录，原子落盘并保存manifest。

## 仓库边界

| Option | Description | Selected |
|--------|-------------|----------|
| src布局 + 窄平台端口 | 可测试、可替换，不制造通用框架 | ✓ |
| 平台逻辑直接写进UI | 初期少文件，但后续无法降级和测试 | |
| 通用多Agent SDK | 范围过大，与课程目标无关 | |

**Auto choice:** `src/debugmate/` + 窄平台适配器；Git为唯一事实源。

## the agent's Discretion

- 测试与静态检查的具体配置。
- 探针报告的终端展示样式。
- 原子写入辅助函数的模块组织。

## Deferred Ideas

- 知识库、完整诊断、多模态界面和课程交付分别保留在既定后续阶段。
