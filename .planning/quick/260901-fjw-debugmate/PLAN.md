# DebugMate 简单公网演示部署计划

## 目标

在不改变 DebugMate 核心诊断契约的前提下，让当前 Windows 本机版可以通过临时公网地址进行低并发课程演示。

## 范围

1. 增加可选的公网内容 origin 配置，修复远程浏览器下载报告、PNG、MP3 和 ZIP 时仍指向 `127.0.0.1` 的问题。
2. 保持应用进程仅监听 `127.0.0.1`，由 `cloudflared` Quick Tunnel 提供公网入口。
3. 启动本地 Gradio 服务并验证首页、健康访问、固定回放和产物下载路径。
4. 不把 DIFY_API_KEY 写入代码、日志或公网页面；保留 Dify live、local fallback、fixed replay 的明确边界。
5. 记录启动命令、临时公网地址、进程状态、验证结果和停止方式；不宣称长期生产可用。

## 安全边界

- Quick Tunnel 地址为临时地址，进程停止或隧道退出后即失效。
- 当前项目没有账号体系和公网限流，仅适合本人或少量演示访问。
- Dify API Key 只由本地服务端读取；远程用户只能通过 UI 触发服务端调用。
- 上传文件仍受现有 10 MB 限制，运行产物留在本机 `.debugmate-runtime`。

## 验收

- Python 服务启动成功并仅绑定 `127.0.0.1`。
- Cloudflare Tunnel 获得 `https://*.trycloudflare.com` 地址。
- 远程 origin 配置通过严格校验，不接受任意 Host 注入。
- 首页可访问，固定回放可用，下载链接使用公网 origin。
- 本地离线契约测试、UI 基础测试、`git diff --check` 通过。
- 关闭服务和隧道后不残留敏感进程或密钥输出。
