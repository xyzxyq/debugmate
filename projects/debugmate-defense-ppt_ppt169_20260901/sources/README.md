# DebugMate V0.1 课程提交说明

## 项目定位

DebugMate 是面向人工智能专业学习场景的多模态报错诊断与复盘智能体。用户提供报错文本、截图、代码和环境信息，系统先在本机脱敏并等待确认，再生成带知识引用的结构化诊断，最后从同一个诊断对象派生文字报告、PNG 诊断卡和 MP3 语音复盘。

V0.1 是 Windows 本机课程演示版，不是公网部署或生产服务。

## 课程要求对应

- 专属知识库：`knowledge/sources.json` 收录 17 个 Python、pip、PyTorch、CUDA、Hugging Face、Ultralytics 和 Windows 官方来源。
- 完整工作流：输入校验 -> 文本/截图脱敏 -> 用户预览确认 -> 事实抽取与纠错 -> 分类与知识检索 -> 结构化诊断 -> 报告/PNG/MP3 -> ZIP 下载。
- 多模态成果：文字、图像、语音均由同一 `DiagnosisRecord` 派生。
- 提示词优化：`prompts/v1-baseline.md` 至 `prompts/v4-course-release.md`。
- 真实成果：`evidence/course-v0.1/` 保存当前代码真实 Edge 截图和哈希清单。
- 当前验收口径：Dify 知识库 readback 与严格 `DifyRunEnvelope` 已通过，Edge 结果包因真实 Dify 超时/契约波动采用明确标注的 `local_fallback`；不得把 fallback 媒体称为 Dify 生成。
- 评测账本：`evidence/evaluation/phase9/` 和 `docs/course/current-evaluation.md`，保留 4 个案例、V1–V4 绑定及阻塞原因。

## 主要工具

| 工具 | 功能定位 |
|---|---|
| Dify Cloud（已验收检索契约） | 视觉模型、知识检索、LLM 工作流；受 provider、额度和网络影响 |
| Python + Pydantic | 本地工作流、严格 Schema、结果一致性与证据生成 |
| RapidOCR + Pillow | 截图文字候选与上传前像素脱敏；确定性绘制 PNG |
| Gradio | 统一输入、隐私确认、诊断结果和下载页面 |
| Windows SAPI + FFmpeg | 免费本地语音降级与 MP3 检查 |
| pytest + Playwright Edge | 自动验证状态、键盘、缩放、长内容和下载 |

## 演示运行

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -m debugmate.ui.serve
```

打开命令输出中的本地地址。正常演示可选择固定回放；若实时 Dify 不可用，页面明确显示“本地降级”，不会伪装成云端实时调用。

## 建议演示顺序

1. 展示输入区和“生成本地脱敏预览”。
2. 说明上传前必须由用户确认脱敏结果。
3. 加载 `ModuleNotFoundError` 完成案例。
4. 依次展示事实与引用、文字报告、诊断卡、语音复盘和 ZIP 下载。
5. 展示一次语音或诊断卡部分失败，说明安全降级和最小重试。
6. 切换长内容案例，展开命令说明，强调命令只供查看。

## 提交材料

- PPT：`deliverables/DebugMate-V0.1.pptx`
- 最终讲解视频：`deliverables/DebugMate-V0.1-demo.mp4`（约 5 分 59 秒）
- 字幕：`deliverables/DebugMate-V0.1-subtitles.srt`
- 演示讲解稿：`docs/course/video-script.md`
- PPT 结构：`docs/course/presentation-outline.md`
- 案例说明：`docs/course/v0.1-demo-cases.md`
- 提示词对比：`docs/course/prompt-iteration.md`
- 真实截图与清单：`evidence/course-v0.1/`
- 视频生成脚本与视觉规范：`scripts/build-course-video.py`、`video/DESIGN.md`

## 已知限制

- 当前只有少量代表性案例，不代表覆盖全部 Python/AI 故障。
- Dify 检索和 envelope 已有真实证据，但浏览器端工作流曾出现 `ambiguous_timeout`/结构波动；本次最终媒体包使用明确标记的本地 fallback。
- 本地 SAPI MP3 在正式录屏前仍需人工试听一次。
- 系统不会自动执行修复命令，建议由用户审阅后自行运行。
