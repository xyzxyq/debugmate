# Phase 1 External Setup: Dify Cloud

本机离线实现与 fixture 验证已经完成；以下步骤需要用户自己的 Dify Cloud 登录态，因此当前没有伪造为已完成。

## 必要配置

1. 按 `platform/dify/README.md` 创建最小 Workflow 与知识库。
2. 在本机进程环境中提供：

   - `DIFY_API_KEY`：应用 API Access 中的密钥。
   - `DIFY_DATASET_API_KEY`：仅在知识库管理 API 需要时提供。
   - `DIFY_BASE_URL`：默认 `https://api.dify.ai/v1`。
   - `DIFY_USER`：默认 `debugmate-local`。

3. 不要把任何密钥写入 `.env.example`、DSL、截图、PPT 或 evidence。真实 `.env` 已被 Git 忽略。
4. 不得充值或购买额度；如免费能力不足，记录 `blocked` 并停止。

## 真实探针

```powershell
.\.venv\Scripts\python.exe -m debugmate.cli cloud-probe --output .artifacts\phase1-cloud
```

或设置密钥后运行：

```powershell
.\scripts\run_phase1_probe.ps1
```

## 人工能力证据

- C03 视觉抽取、C04 知识检索和 C06 DSL 重导入没有独立证据时必须保持 `not-tested`。
- C06 需要真实 DSL 文件、重导入结果和固定 fixture 复跑证据。
- C07 需要真实 MP3；后续还须用 FFprobe 验证时长。
- 在线配置总时长最多 4 小时。
