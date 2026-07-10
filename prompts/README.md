# Prompt 版本目录

Phase 1 不伪造“生产提示词”。后续阶段将把每次优化保存为独立文件，并在 evidence manifest 中记录实际版本：

- V1：最小诊断结构与禁止执行命令边界，计划位置 `prompts/v1-baseline.md`。
- V2：增加知识引用与缺失信息表达，计划位置 `prompts/v2-citations.md`。
- V3：增加结构化输出修复与不确定性校准，计划位置 `prompts/v3-reliability.md`。
- V4：根据评测集定稿，计划位置 `prompts/v4-course-release.md`。

只有文件真实存在并被一次运行 manifest 引用后，该版本才算已使用。
