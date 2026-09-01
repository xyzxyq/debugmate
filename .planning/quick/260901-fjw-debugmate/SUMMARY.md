---
id: 260901-fjw
status: verified
completed: 2026-09-01
---

# DebugMate 临时公网演示部署记录

## 部署结果

DebugMate 已在当前 Windows 主机启动，并通过 Cloudflare Quick Tunnel 发布为临时 HTTPS 公网演示地址。应用进程仍只监听 `127.0.0.1`，公网隧道转发到本地 Gradio 服务，适合低并发课程展示。

## 本轮改动

- `src/debugmate/ui/app.py`：允许由显式配置提供 HTTPS 公网 content origin，同时保留回环请求校验和严格 origin 校验。
- `src/debugmate/ui/serve.py`：读取 `DEBUGMATE_PUBLIC_ORIGIN`，让报告、PNG、MP3 和 ZIP 下载链接指向公网入口。
- `scripts/start-public-demo.ps1`：自动启动 Quick Tunnel、本地服务、健康检查并保存临时进程状态。
- `scripts/stop-public-demo.ps1`：按状态文件精确停止本地服务和隧道。
- `.gitignore`、`README.md`、`docs/course/README.md`：记录公网演示边界和停止方式。

## 现场验证

- `cloudflared.exe` 已发现并启动成功。
- 本地 UI `http://127.0.0.1:7860/`：HTTP 200。
- Quick Tunnel HTTPS 地址：HTTP 200。
- 应用运行时继续使用服务端环境变量读取 `DIFY_API_KEY`，未写入脚本、日志或公网响应。
- 当前仍是无账号、低并发、临时地址；Dify live、local fallback、fixed replay 状态继续由页面真实标识。

## 运维

- 启动：`powershell -ExecutionPolicy Bypass -File scripts/start-public-demo.ps1`
- 停止：`powershell -ExecutionPolicy Bypass -File scripts/stop-public-demo.ps1`
- 访问地址会在每次 Quick Tunnel 启动时随机变化，不承诺永久域名、SLA 或生产可用性。

Implementation commit: `6e1ce25`
