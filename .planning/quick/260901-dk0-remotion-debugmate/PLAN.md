# Quick Task: Remotion 重制 DebugMate 课程视频

## 目标

用 Remotion 重制 DebugMate V0.1 课程介绍视频，保持真实项目事实口径，改善镜头层次、动画节奏、界面/证据展示和音频清晰度，并交付可播放、带音频和字幕的新 MP4。

## 实施范围

- 复用当前课程讲解稿、PPT SVG/PNG、真实 UI/证据素材和项目视觉规范。
- 新建 `video/remotion/` 工程，使用 React/Remotion 组织多场景时间线。
- 使用同一份中文讲解稿生成清晰旁白，加入轻量、可控的背景音乐/音频层；不使用会遮挡旁白的音效。
- 生成与旁白时间一致的 Remotion 字幕，并保留 SRT/manifest。
- 交付 `deliverables/DebugMate-V0.1-demo.mp4`，必要时同步更新字幕和视频 manifest。

## 事实边界

- 真实 Dify live、local fallback、固定回放必须明确区分。
- 不生成或伪造运行截图、指标和云端成功证据。
- 新视频中的所有工程界面素材来自仓库中的真实/已审计截图或现有项目素材。

## 验收

- Remotion composition 可被 Studio 打开并由 CLI 渲染。
- MP4 包含 H.264 视频和 AAC 音频，音频可解码、非静音、无明显削波，旁白可听清。
- 字幕时间轴连续、不越界，与旁白镜头顺序一致。
- 视频时长、分辨率、帧率和 SHA-256 写入 manifest。
- 运行现有视频/材料相关测试和 `git diff --check`。
- 更新源码包，使新的 Remotion 工程、音频源/脚本和交付物可复现。
