# Phase 10 Plan 01 Summary: Final Course Package Refresh

## Outcome

课程材料已依据当前 Phase 8/9 事实口径重新生成：

- `deliverables/DebugMate-V0.1.pptx`
- `deliverables/DebugMate-V0.1-demo.mp4`
- `deliverables/DebugMate-V0.1-subtitles.srt`
- `deliverables/asset-manifest.json`
- `deliverables/video-manifest.json`

生成脚本使用仓库中的当前课程文案和真实 UI 截图；材料明确区分 Dify live、local fallback 和固定 replay。视频使用确定性本地 Windows SAPI/FFmpeg 管线，未将本地音频标记为 Dify TTS。

## Verification

- PPTX 可解压，包含 13 页，无 TODO/TBD/Lorem ipsum/占位文本。
- MP4 为 1920x1080 H.264/AAC，时长约 355 秒。
- SRT 时间轴连续且未超过视频时长。
- PPT、视频、字幕 manifest 哈希一致。
- Phase 8 MP3 仍可由 FFprobe 解析，约 59 秒。
- `python-pptx==1.0.2` 已加入 `pyproject.toml`，保证课程材料可从项目依赖重建。

## Limitation

Dify 浏览器端真实调用曾出现 `ambiguous_timeout` 和旧契约响应；该限制在讲解稿、视频脚本、Phase 8 证据和 Phase 9 账本中均保留，演示时按页面实际状态选择实时 Dify、local fallback 或 replay。
