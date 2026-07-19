# Prompt 版本目录

V0.1 已保存四个可审查版本，用于课程展示提示词从自然语言诊断到结构化、多模态一致性约束的优化过程：

- V1：最小诊断结构与禁止执行命令边界，见 `prompts/v1-baseline.md`。
- V2：增加知识引用与缺失信息表达，见 `prompts/v2-citations.md`。
- V3：增加结构化输出与不确定性校准，见 `prompts/v3-reliability.md`。
- V4：增加课程表达、TTS 长度和多模态一致性约束，见 `prompts/v4-course-release.md`。

真实性说明：固定案例的运行 manifest 记录当前基线为 `diagnosis-v1`；V2–V4 是基于已发现问题形成的可直接配置版本，尚未伪造云端批量评测结果。课程展示应区分“已运行基线”和“设计迭代”。
