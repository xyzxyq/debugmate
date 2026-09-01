---
id: 260901-dk0
status: verified
completed: 2026-09-01
---

# Remotion 视频重制完成记录

## 结果

DebugMate V0.1 课程介绍视频已使用 Remotion 4.0.506 重制完成。视频由 8 个逐帧动画场景组成，保留项目真实事实边界，使用真实项目截图和确定性图形展示隐私脱敏、知识检索、结构化诊断、多模态产物与降级路径。

## 交付规格

- 输出：`deliverables/DebugMate-V0.1-demo.mp4`
- 分辨率：1920×1080，30 fps，H.264 High
- 音频：AAC LC，48 kHz，双声道，中文 Edge TTS `zh-CN-XiaoxiaoNeural` 旁白 + 低音量原创环境音
- 时长：约 366.267 秒
- 字幕：45 条，Remotion `captions.json` 与 SRT 均由同一组 VTT 时间轴生成并归一化
- 证据：`deliverables/video-manifest.json` 记录视频、字幕、音频后端和真实性边界

## 实现文件

- `video/remotion/`：Remotion 工程、Composition、场景组件、字幕和媒体资源
- `scripts/build-remotion-video.py`：旁白、VTT、字幕、场景时长、环境音和素材构建
- `scripts/render-remotion-video.py`：Remotion 视觉渲染、音频安全混音、FFprobe 验收和 manifest 生成
- `docs/course/README.md`、`README.md`：更新视频构建方式和交付说明
- `deliverables/DebugMate-V0.1-source.zip`：重新打包，包含 367 个可重建/运行所需的源码与交付文件；包 SHA-256 为 `53e1312381b60b8b3760474bce8955c98d68edfa887cd99bf23ecc624618b43f`

## 验证

- TypeScript `tsc --noEmit`：通过
- Remotion compositions：通过，`DebugMateV01` / `DebugMateV01Visual` 均为 10988 帧
- 单帧与关键场景预览：通过；修复 `Sequence` 重复扣帧导致的后续场景空白问题
- Ruff、Python 编译、`git diff --check`：通过
- 离线契约/隐私测试：127 passed，1 deselected
- MP4 完整解码：通过；视频 1920×1080，音频 AAC，音频均值 -22.4 dB，未静音、未削波
- 字幕时间轴：44 个可解析 SRT 区块 + 1 个末尾标准区块，最后结束时间 365.268 秒，未超出视频时长
- 源码包：ZIP 完整性、manifest 哈希、解压编译和 `debugmate` 导入 smoke test 均通过

## 备注

Remotion 视觉 Composition 在当前环境会产生静音音轨，因此渲染脚本会检测音轨均值，并在静音时只进行一次外部安全混音；最终交付不包含重复旁白。Dify live、local fallback 和 fixed replay 仍在视频中明确区分。

Implementation commit: `e9395d7`
