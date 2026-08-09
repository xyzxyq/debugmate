# Dify 现场证据

本目录只保存已经通过本地合同校验、媒体检查和秘密扫描的真实 Dify 运行证据。临时探测输出仍位于被 Git 忽略的 `.artifacts/`，不能作为可提交事实源。

## 当前证据

- `2026-08-08/cloud-probe/case_d2c4d21672c14d9bad7f7fe95ee86653/`：从已验证的 live cloud-probe 原样复制；仅证明 C01、C02、C05 为 `pass`。其中 `probe-results.json` 明确保留 C03、C04、C06、C07 为 `not-tested`。
- `2026-08-09/tts/`：通过正式 Dify `text-to-audio` live gate 生成的 MP3 及其无秘密媒体元数据；证明 C07 为 `pass`。
- `2026-08-09/c03-c04/`：固定合成终端 PNG 经正式 `/files/upload` 与 `/workflows/run` 运行；target-free request manifest、Workflow 输出及同一控制台日志的 Knowledge Retrieval 节点 allowlist 分别证明 C03、C04 为 `pass`。
- `2026-08-09/c06/dsl-roundtrip-evidence.json`：记录实际导入尝试。控制台可访问，但浏览器扩展不允许本地文件上传，已认证页面直接调用导入接口又返回 401；未发生独立导入、重导出与复跑，所以 C06 为 `blocked`。

C03 的目标原文只存在于 PNG 像素中；版本化 manifest 枚举全部非图像 Start 输入并绑定 canonical request SHA-256。C04 的主证据是 direct Knowledge Retrieval node execution output，不是最终 diagnosis.evidence。C06 仍需要独立导入、重导出、结构等价比较与重建应用复跑才能升级为 `pass`。

## 复验

```powershell
$python = (Resolve-Path -LiteralPath '.worktrees\phase-1-foundation-platform-gate\.venv\Scripts\python.exe').Path
$env:PYTHONPATH = (Resolve-Path -LiteralPath 'src').Path
$bundle = (Resolve-Path -LiteralPath 'evidence\dify-live\2026-08-08\cloud-probe\case_d2c4d21672c14d9bad7f7fe95ee86653').Path
& $python -m debugmate.cli verify-bundle $bundle
& $python -m debugmate.dify_live_evidence validate-published --repository-root . --evidence-root 'evidence\dify-live\2026-08-09'
ffprobe -v error -show_entries stream=codec_name,channels -show_entries format=duration,size -of json 'evidence\dify-live\2026-08-09\tts\dify-recap.mp3'
Get-FileHash -Algorithm SHA256 -LiteralPath 'evidence\dify-live\2026-08-09\tts\dify-recap.mp3'
```

重新运行 live TTS gate 时只从环境变量读取 Dify 配置；不得把凭据、Authorization header、完整响应体或复盘原文写入本目录。
