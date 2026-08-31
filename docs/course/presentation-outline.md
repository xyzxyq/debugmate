# DebugMate V0.1 答辩展示大纲

本版本由 `superpowers:brainstorming` 完成叙事设计，再由 `ppt-master` 按 16:9、15 页、浅色技术简报视觉系统制作。预计答辩时长 8–10 分钟；核心案例贯穿全篇，所有“真实结果”均来自仓库证据，封面概念图仅作视觉引导。

## 叙事主线

真实报错 → 学习痛点 → V0.1 边界 → 完整路径 → 技术路线与架构 → 知识库与隐私 → Prompt 演进 → 真实运行结果 → 同源多模态 → 失败诚实性 → 自动评测 → 演示收束。

## 页面结构

1. **封面｜从报错到复盘：DebugMate**：项目身份、课程、版本与“有依据 / 可执行 / 说明不确定性”三项价值。右侧为无文字概念图，不承担事实证据。
2. **真实案例｜从一个真实报错开始**：脱敏后的 `ModuleNotFoundError`、Windows、Python 3.13.5 与导入代码；提出“下一步该相信什么”的问题。
3. **问题定义｜普通问答为什么不够**：证据缺失、环境不确定、结果难沉淀三类痛点，收束到“把排错变成学习闭环”。
4. **产品边界｜V0.1 做什么，也不做什么**：左侧展示本地浏览器、17 源知识库、隐私确认、三模态产物与代表性案例；右侧明确公网部署、SLA、稳定云端浏览器链路和自动修复延期。
5. **系统全貌｜一次诊断的完整路径**：Input → Privacy Gate → Extraction → Retrieval → DiagnosisRecord → Media/UI 六节点流水线。
6. **技术路线｜云端增强，本地闭环**：Dify Cloud 负责视觉 / RAG / LLM 编排；本地 Python 负责脱敏、Pydantic、Pillow、TTS fallback 与 Gradio；Git 作为可复现事实源。
7. **系统架构｜DiagnosisRecord 是单一事实源**：中央结构化对象连接输入、证据、根因、检查、验证与 limitations，并派生报告、PNG、MP3、ZIP。
8. **知识库｜17 个官方来源**：Python、pip/venv、PyTorch、CUDA、Hugging Face、Ultralytics、Windows/PowerShell 七类主题；展示 `knowledge_build_id`、来源和哈希绑定。
9. **安全边界｜隐私闸门：先确认，再上传**：本机校验 → OCR/正则发现 → 脱敏预览 → 用户确认；覆盖 Token、邮箱、用户名、绝对路径、图片敏感像素和导出物。
10. **工程迭代｜V1–V4：从能回答到可派生**：基础诊断 → 引用约束 → 结构可靠 → 课程定稿；强调证据、结构和多模态派生的一致性。
11. **真实证据｜一次完整诊断的真实结果**：使用真实 Edge 工作台截图，标注脱敏输入、证据与产物区域，并明确当前运行属于 live、fallback 或 replay。
12. **同源产物｜三种输出，共享一个身份**：`case_id + source_run_id + diagnosis_hash + schema_version` 贯穿报告、诊断卡、语音和 ZIP。
13. **可靠性｜失败也要诚实**：展示真实 TTS / PNG 部分失败；只重试失败产物，保留失败证据，不把 local fallback 冒充 cloud success。
14. **评测｜评测与自动验证**：4 个代表性案例、V1–V4 同输入、1177 项离线回归、113 项隐私测试、1 项云端合同测试；Phase 9 blockers 继续保留并可追溯。
15. **收束｜把“修好一次”变成“理解一次”**：报错 → 隐私确认 → 官方知识 → 结构化诊断 → 报告 / PNG / MP3 / ZIP；现场演示顺序与真实限制一并给出。

## 视觉与素材规则

- 视觉系统：暖纸面 `#F7F5EF`、深石墨 `#14212B`、青绿 `#0F9D8A`、橙色 `#F0784A`；固定章节标记与证据脊线。
- 技术图优先使用原生 SVG/PPT 元素，保证可编辑、可放大、可复核。
- 真实运行截图来自 `evidence/course-v0.1/` 与 `evidence/dify-live/phase8/`，保持原图比例，不裁切关键状态。
- 封面 `cover-concept.png` 是 imagegen 生成的无文字概念图，不能作为运行证据。
- 生成入口：`scripts/author_defense_ppt_svg.py`；ppt-master 工程：`projects/debugmate-defense-ppt_ppt169_20260901/`。
