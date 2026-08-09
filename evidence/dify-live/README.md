# Dify 现场证据

本目录只保存已经通过本地合同校验、媒体检查和秘密扫描的真实 Dify 运行证据。临时探测输出仍位于被 Git 忽略的 `.artifacts/`，不能作为可提交事实源。

## 当前证据

- `2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/`：从已验证的 live cloud-probe 原样复制；仅证明 C01、C02、C05 为 `pass`。其中 `probe-results.json` 明确保留 C03、C04、C06、C07 为 `not-tested`。
- `2026-08-09/tts/`：通过正式 Dify `text-to-audio` live gate 生成的 MP3 及其无秘密媒体元数据；证明 C07 为 `pass`。

C03 仍需要真实截图视觉抽取证据，C04 仍需要真实 retrieval chunk/来源元数据，C06 仍需要导出、重导入并复跑的版本化记录。DSL 中存在节点、输出字段存在或历史文字记录都不能替代这些独立证据。

## 复验

```powershell
$python = (Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path
$env:PYTHONPATH = (Resolve-Path -LiteralPath 'src').Path
$bundle = (Resolve-Path -LiteralPath 'evidence\dify-live\2026-08-08\cloud-probe\case_d2c4d21672c14d9bad7f7fe95ee86653').Path
& $python -m debugmate.cli verify-bundle $bundle
ffprobe -v error -show_entries stream=codec_name,channels -show_entries format=duration,size -of json 'evidence\dify-live\2026-08-09\tts\dify-recap.mp3'
Get-FileHash -Algorithm SHA256 -LiteralPath 'evidence\dify-live\2026-08-09\tts\dify-recap.mp3'
```

重新运行 live TTS gate 时只从环境变量读取 Dify 配置；不得把凭据、Authorization header、完整响应体或复盘原文写入本目录。
