# Stack Research

**Domain:** 面向 AI 专业学习场景的多模态 RAG 报错诊断智能体（Windows 本地展示 + 云端编排）  
**Researched:** 2026-07-10  
**Overall confidence:** HIGH（Dify/Python 主链路）；MEDIUM（Coze Cloud 的长期可迁移性与免费额度）

## Executive Decision

采用 **Dify Cloud + 本地 Python 薄客户端**，而不是纯 Coze、纯 Dify 页面或从零实现 RAG。

- **Dify Cloud** 只负责：知识库索引、检索、视觉模型调用、工作流编排，以及输出统一的 `DiagnosisResult` JSON。
- **本地 Python** 负责：输入脱敏、调用 Dify API、Pydantic 严格校验、运行证据落盘、Markdown 报告、确定性 PNG 诊断卡、MP3 复盘和 Gradio 统一结果页。
- **Git 仓库** 是唯一可提交事实源：知识源 Markdown、来源清单、提示词 V1-V4、Dify DSL、JSON Schema、测试样例、每次运行的脱敏输入与输出均版本化；Dify 中的数据是可重建副本。

这个分工的人工成本最低且满足课程证据要求：不重写 RAG/工作流，不依赖云平台页面作为唯一证据，也不让文本、PNG、MP3 三条生成链互相漂移。

```text
Gradio 输入 -> 本地脱敏 -> Dify 文件/Workflow API
                              |
                              v
                  Vision + 分类 + Knowledge Retrieval
                              |
                              v
                    DiagnosisResult JSON
                              |
             Pydantic 严格校验/失败重试一次
                 /            |             \
        Markdown/JSON     Pillow PNG      TTS MP3
                 \            |             /
                    Gradio 统一结果页 + evidence/run_id/
```

## Recommended Stack

### Core Technologies

| Technology | Version / contract | Purpose | Why Recommended |
|------------|--------------------|---------|-----------------|
| Dify Cloud | 托管版本，不在代码中硬编码版本；保留 `.dify.yml` DSL | Workflow、知识库 RAG、视觉 LLM、运行日志、API 发布 | 官方文档明确支持 Workflow/Chatflow、文件与图像输入、知识检索结果中的内容与元数据、API 和 Webapp；Sandbox 可在无信用卡情况下试用。比自建向量库和编排器少大量人工工作。 |
| CPython | `3.13.x`（本机已核验 `3.13.5`） | 本地胶水层、脱敏、验证、制品生成、评测 | 与本机现状一致；`venv` 是官方隔离方式。不要为此项目额外维护 Conda 或 WSL 环境。 |
| Gradio | `6.20.0` | Windows 浏览器中的统一输入/结果页 | 原生提供 Image、Audio、File/DownloadButton，能在一个页面展示原截图、报告、PNG、MP3 与下载文件；比 React 前端节省数天工作。 |
| Pydantic | `2.13.4` | `DiagnosisResult` 单一事实源、严格验证、JSON Schema 导出 | 可将模型输出、PNG、MP3 和评测绑定到同一结构；使用 `ConfigDict(strict=True, extra='forbid')` 阻止静默类型转换和多余字段。 |
| HTTPX | `0.28.1` | 调用 Dify 文件、Workflow、TTS API | 同步/异步接口清晰，超时和错误处理比手写 `urllib` 更适合测试；密钥仅从环境变量读取。 |
| Pillow | `12.3.0` | 从结构化诊断确定性绘制 PNG 诊断卡/流程图 | 纯 Python、Windows `cp313` wheel 已核验；无需 Graphviz、Node/Chromium 或图像生成 API，输出可测试且不会凭空改写证据。 |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| RapidOCR | `3.9.1` | 截图本地 OCR，返回文字与坐标框 | 在上传云端前识别用户名、路径、邮箱、Token 等候选敏感区域；与正则规则结合后用 Pillow 遮挡。首次运行会下载/加载 OCR 资源，应提前缓存。 |
| ONNX Runtime CPU | `1.27.0` | RapidOCR 本地推理后端 | 使用 CPU 版本即可；OCR 不值得占用 RTX 4050 显存，也避免 CUDA/PyTorch 依赖冲突。 |
| python-dotenv | `1.2.2` | 本地开发时加载 `.env` | 只加载 `DIFY_API_KEY`、`DIFY_DATASET_API_KEY`、`DIFY_BASE_URL` 等；`.env` 必须被 Git 忽略，提交 `.env.example`。 |
| Dify Text-to-Audio API | Cloud contract，返回 `audio/mpeg` | 将同一诊断对象的短摘要转成 MP3 | **主 TTS 路径**。官方 API 明确返回音频流；具体声音取决于应用配置的 TTS provider。若免费额度或 provider 不可用，再启用本地降级。 |
| edge-tts | `7.2.8` | 无额外付费密钥的 MP3 降级路径 | 只作为课程演示 fallback；它不是 Microsoft 官方 SDK，必须记录 `tts_backend=edge_tts`，不要将其当长期生产依赖。 |
| FFmpeg | `8.1`（本机已核验） | 音频规范化、时长探测、必要时转 MP3 | 对所有 MP3 运行 `ffprobe` 证明确实可播放；仅在 TTS 返回非 MP3 时转码。 |
| pytest | `9.1.1` | 单元测试、契约测试、golden cases | 覆盖脱敏、Schema、Dify 响应适配、PNG/MP3 文件头、评测计分；云端测试用 marker 隔离。 |
| Ruff | `0.15.21` | 格式化和静态检查 | 一个工具替代 Black + isort + Flake8，减少配置与依赖。 |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Git | 版本化知识源、提示词、DSL、评测与证据 | 每次平台配置变更后立即导出 Dify DSL；不得只留平台截图。 |
| Dify DSL export/import | 工作流可移植备份 | 将导出的 YAML 放入 `platform/dify/`；DSL 不等于知识库内容，知识源和同步 manifest 必须独立保存。 |
| Dify API logs + local `run_id` | 双重运行证据 | 本地保存请求摘要、脱敏输入 SHA-256、模型/提示词版本、命中 chunk 元数据、输出 JSON、PNG、MP3 和错误；云日志只是补充。 |
| JSON Schema | 云端输出与本地模型契约 | 由 Pydantic 生成并提交；提示词中要求只返回符合 Schema 的 JSON，本地验证失败只自动修复/重试一次。 |
| PowerShell scripts | Windows 一键运行与验收 | 使用 `-LiteralPath`、UTF-8、绝对路径；脚本调用 `.venv\Scripts\python.exe`，不依赖激活状态。 |

## Installation

MVP 不安装 Dify/Coze 服务端，也不需要 Docker。使用本机 Python 3.13 虚拟环境：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install `
  gradio==6.20.0 pydantic==2.13.4 httpx==0.28.1 `
  pillow==12.3.0 rapidocr==3.9.1 onnxruntime==1.27.0 `
  python-dotenv==1.2.2 edge-tts==7.2.8
.\.venv\Scripts\python.exe -m pip install --group dev `
  pytest==9.1.1 ruff==0.15.21
```

如果项目元数据尚未采用 dependency groups，可先使用：

```powershell
.\.venv\Scripts\python.exe -m pip install pytest==9.1.1 ruff==0.15.21
```

建议在 `pyproject.toml` 中锁定上述 direct dependencies，并生成一份解析后的锁文件；不要提交 `.venv`。

## Platform Comparison

| Dimension | Dify Cloud | Coze Cloud / 扣子 | Full Python fallback |
|----------|------------|-------------------|----------------------|
| 初次搭建人工量 | 低 | **最低**（单平台节点多） | 高 |
| 文本 + 图像输入 | 官方 Workflow 文件类型与 vision 模型支持明确 | 官方 SDK 有 image/file mixed input 与 workflow image 示例 | 取决于所选模型 API，需自己处理上传 |
| RAG 与来源元数据 | **强**：Knowledge Retrieval 输出 chunk 内容、标题、元数据，可做 metadata filter | 有 Dataset/Knowledge API，但云端文档与迁移证据不如 Dify 清晰 | 最可控，但分块、embedding、rerank、引用都要自己实现 |
| 结构化输出约束 | 中：Prompt/变量输出，本地 Pydantic 可补强 | 中：可输出 JSON，但仍需本地验证 | **强**：完全自控 |
| PNG/MP3 | 通过本地 Pillow + Dify TTS，确定性且可验收 | 原生语音/图像能力方便，但图像生成不适合充当诊断证据 | Pillow/TTS 自己实现 |
| 导出/可复现 | **强**：官方 DSL 迁移 + 开源服务端；知识仍需独立同步 | **中-低**：API 可调用 workflow/dataset/TTS，但未找到等价、稳定、完整的云端 Workflow-as-code 导出承诺 | **最强**：全在 Git |
| Windows、无 Docker | Cloud + Python 均适配 | Cloud 适配；不要自建 Coze Studio | 适配，但依赖管理工作最多 |
| 课程“工程量可见” | **最佳平衡** | 容易被看成平台拼装 | 工程量大但短周期风险高 |
| 免费额度风险 | Sandbox：200 message credits、5 apps、50 docs、50MB、10 knowledge req/min、5000 API req/month；额度耗尽需自备 key | 额度、模型和节点可用性会随地区/账号变化 | 模型 API 仍可能收费；本地 6GB GPU 不适合大视觉模型 |

**Recommendation:** 以 Dify Cloud 为正式编排平台。Coze 仅在“中国区访问/模型额度显著优于 Dify，且能在一天内通过 DSL/知识/日志导出验收”时替换；否则不要在两套平台同时维护同一工作流。

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Dify Cloud + local Python | Coze Cloud + `cozepy==0.20.0` | 需要最快做出全云 demo，国内网络/账号可用性优先于可迁移性；官方 SDK 已覆盖 workflow、image chat、dataset、file upload、audio/speech。仍应保留本地 Schema、提示词、知识源和证据。 |
| Dify Cloud RAG | Python direct RAG | Dify 无法访问/额度不可接受，或评分明确要求自研检索。此时先用小规模可审计检索，再决定 embedding/vector DB；不要直接引入大型框架。 |
| Gradio 6 | Streamlit | 最终页面更偏报告仪表板且不需要多文件/音频交互时。当前项目的 Image/Audio/Download 组合更适合 Gradio。 |
| Pillow 诊断卡 | Mermaid/Graphviz | 老师明确要求标准流程图而非诊断信息卡，且允许安装 Node/Chromium 或 Graphviz 时；否则 Windows 安装和中文字体渲染成本不划算。 |
| Dify TTS | `edge-tts` | Dify TTS provider 或额度在演示前不可用。必须在结果元数据中标记降级后端，并用 FFprobe 验证 MP3。 |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| 本地自建 Dify 或 Coze Studio | 官方部署主路径依赖 Docker/多服务；本机明确无 Docker，安装与运维会吞噬课程时间。 | Dify Cloud；Git 中保留 DSL 和知识资产。 |
| 同时实现 Coze 与 Dify 两套正式流程 | 双倍手工节点配置、双倍回归测试，提示词和知识版本容易漂移。 | 只保留一个正式平台，另一个仅做有时间盒的可行性试验。 |
| LangChain/LlamaIndex 作为 MVP 核心 | 当前 Dify 已负责 RAG/Workflow，再叠一层框架没有价值；版本变化、抽象和调试面会增加。 | `httpx + pydantic` 的薄适配层。 |
| Chroma/Milvus/Elasticsearch/FAISS 本地向量栈 | 小型课程知识库不需要额外数据库；Windows/Python 3.13/无 Docker 会带来 wheel、索引和持久化问题。 | Dify Knowledge；云端失效后再实现小型直接检索。 |
| 让图像生成模型绘制“诊断证据图” | 文字错写、步骤漂移、不可做像素级 golden test，还可能被误认为伪造证据。 | 从已验证 `DiagnosisResult` 用 Pillow 绘制确定性 PNG。 |
| Mermaid CLI / Playwright 截图作为默认 PNG 管线 | 需要 Node、Chromium 和字体配置，Windows 中文路径下故障面大。 | Pillow；确需图结构时再增加 Graphviz。 |
| PyTorch/CUDA OCR 或本地视觉大模型 | RTX 4050 6GB 不适合稳定承载视觉 LLM；还会与课程中要诊断的 PyTorch/CUDA 环境相互污染。 | RapidOCR + ONNX Runtime CPU；视觉理解走云模型。 |
| 只保留 Dify/Coze 页面截图 | 截图不能重建知识库、Prompt、Workflow 或同一次运行输出。 | DSL + Git 资产 + `evidence/<run_id>/manifest.json`。 |
| 将 API key 写入 DSL、日志、PPT、示例 JSON | 会直接违反项目隐私要求，且平台导出文件可能携带敏感配置。 | 环境变量、`.env.example`、日志键名 allowlist、提交前 secret scan。 |
| `edge-tts` 作为唯一 TTS | 非 Microsoft 官方 SDK，依赖未公开服务行为，可能无通知失效。 | Dify 官方 TTS API 为主；edge-tts 只降级。 |

## Stack Patterns by Variant

**正式课程版本（推荐）：**
- Dify Cloud：Start -> 文件/图像 -> Vision LLM 抽取 -> 分类 -> Knowledge Retrieval -> 诊断 LLM -> JSON 输出。
- Python：脱敏 -> API 调用 -> Pydantic 验证 -> Markdown/PNG/MP3 -> Gradio -> evidence bundle。
- 每个诊断生成固定目录：`input.redacted.*`, `diagnosis.json`, `report.md`, `card.png`, `recap.mp3`, `retrieval.json`, `manifest.json`。

**如果 Dify Cloud 在 4 小时内无法完成账户、模型、知识库和 API smoke test：**
- 用 Coze Cloud 完成工作流和模型调用；Python 继续负责脱敏、Schema、制品与证据。
- 通过 `cozepy==0.20.0` 调用 workflow/dataset/files/audio，禁止把业务逻辑散落到不可导出的聊天配置里。

**如果两个云平台都不可用：**
- 保留 Gradio/Pydantic/Pillow/RapidOCR 主体。
- 视觉与诊断改为任一已批准的 OpenAI-compatible API；知识检索先用本地文档关键词/BM25，并明确这是 fallback，不在首版引入向量数据库。
- 所有付费 API 在实现前单独确认；不得默认充值。

**如果 TTS 不可用：**
- 降级顺序：Dify TTS -> edge-tts -> Windows SAPI WAV + FFmpeg MP3。
- UI 中显示后端和降级原因；只要 MP3 来自同一个 `recap_text`，仍保持多模态一致性。

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python `3.13.5` | Gradio `6.20.0`, FastAPI dependency chain, Pydantic `2.13.4`, Pillow `12.3.0`, RapidOCR `3.9.1`, Ruff `0.15.21` | 2026-07-10 在本机用 `pip --dry-run`/wheel metadata 核验；Pillow、pydantic-core、OpenCV 等有 `cp313-win_amd64` wheel。 |
| Gradio `6.20.0` | Python `>=3.10` dependency set | 使用 Gradio 6 API：音频/图片下载按钮改为 `buttons=[...]`，不要照抄 5.x 的 `show_download_button`。 |
| Pydantic `2.13.4` | `pydantic-core 2.46.4` | 使用 V2 的 `model_validate_json()`、`model_json_schema()` 和 `ConfigDict`，不要使用 V1 `parse_raw`/inner `Config` 新代码。 |
| RapidOCR `3.9.1` | ONNX Runtime `1.27.0`, OpenCV `4.x`, NumPy `<3` | CPU 即可；首次模型准备和中英文混合 OCR 必须提前做 smoke test。 |
| Dify Cloud Workflow | Dify Application API | Cloud 不做语义版本锁定；通过 DSL、契约测试和适配器隔离变化。API key 只放服务端/本地进程。 |
| Dify TTS API | 已在 Dify app 配置的 TTS provider | 响应是 `audio/mpeg`/audio stream；声音列表和可用性依 provider，不要在代码里假设固定 voice。 |
| `edge-tts 7.2.8` | Python 3.13, network access | 仅 fallback，网络或上游协议变化会导致失败。 |

## Implementation Guardrails

1. `DiagnosisResult` 必须至少包含：`schema_version`, `run_id`, `error_category`, `root_cause_candidates`, `evidence[]`, `retrieved_sources[]`, `checks[]`, `fix_steps[]`, `verification_commands[]`, `confidence`, `limitations[]`, `recap_text`。
2. `evidence[]` 分 `observed`、`retrieved_fact`、`inference` 三类；任何根因候选必须引用其 evidence/source id。
3. PNG 和 MP3 不再调用 LLM重写内容：PNG 从字段渲染，MP3 只朗读 `recap_text`。
4. Dify 返回 JSON 失败时最多“JSON 修复提示 + 重试一次”；仍失败就输出明确错误，不用正则拼出一个看似成功的诊断。
5. 上传前执行：EXIF 清除、OCR、敏感正则匹配、区域遮挡、用户预览；原始截图只在本地临时目录短期保留。
6. 每条知识文档保存 `source_url`, `title`, `product`, `version_scope`, `retrieved_at`, `sha256`, `license_or_terms_note`；Dify metadata 同步这些字段。
7. 评测默认不依赖实时云结果：保留已脱敏的 golden response fixtures；live tests 单独标记，避免额度耗尽导致 CI 全红。

## Confidence and Open Checks

| Decision | Confidence | Remaining live check before implementation |
|----------|------------|-------------------------------------------|
| Dify Cloud 作为正式 RAG/Workflow | HIGH | 登录后用 1 张截图 + 1 个 MD 文档完成 API smoke test，并实际导出/重导入一次 DSL。 |
| 本地 Gradio/Pydantic/Pillow | HIGH | Python 3.13 依赖已解析；实现阶段验证中文字体和长文本分页/换行。 |
| RapidOCR 本地脱敏 | MEDIUM-HIGH | 用 10 张真实终端截图测用户名、Windows 路径、邮箱和 Token 的召回率；漏检时强制用户确认预览。 |
| Dify TTS 为主 | MEDIUM | 取决于账号中实际可配置的 TTS provider/额度；先调用 `/text-to-audio` 保存一个可播放 MP3。 |
| Coze 作为替代平台 | MEDIUM | 官方 SDK 能力明确，但云端账号/地区/额度和完整工作流导出能力必须现场验证；未通过则不进入正式架构。 |

## Sources

Official/primary sources consulted on 2026-07-10:

- [Dify Cloud pricing](https://dify.ai/pricing/dify-cloud) — Sandbox 额度、Workflow/API/Webapp、知识库和日志限制。
- [Dify 30-minute quick start](https://docs.dify.ai/en/guides/application-orchestrate/creating-an-application) — Workflow 的文本、文档、图像文件输入及 vision 处理。
- [Dify Knowledge Retrieval node](https://docs.dify.ai/en/use-dify/nodes/knowledge-retrieval) — 检索结果数组、chunk 内容/标题/元数据、metadata filter 与 vision context。
- [Dify Text-to-Audio API](https://docs.dify.ai/api-reference/tts/convert-text-to-audio) — TTS 请求与音频响应契约。
- [Dify Tool Return](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/tool) — workflow tool 的 text/files/json 与 image/file blob 输出。
- [Dify official repository](https://github.com/langgenius/dify) and [official releases](https://github.com/langgenius/dify/releases) — 开源/自托管边界与当前 release evidence；自托管仍以 Docker Compose 为标准运维路径。
- [Dify official DSL portability announcement](https://github.com/langgenius/dify/discussions/3163) — 应用通过 DSL 迁入迁出。
- [Coze Python SDK](https://github.com/coze-dev/coze-py) — workflow、image chat、dataset、file upload、audio/speech API 覆盖及 Python 要求。
- [Coze Studio API reference](https://github.com/coze-dev/coze-studio/wiki/6.-API-Reference) — workflow run 和多模态消息输入契约。
- [Coze Studio basic component configuration](https://github.com/coze-dev/coze-studio/wiki/5.-Basic-component-configuration) — 自建版上传/知识库所需的外部组件，支持“不在无 Docker Windows 上自建”的结论。
- [Python 3.13 `venv`](https://docs.python.org/3.13/library/venv.html) — Windows 虚拟环境隔离方式。
- [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/) — 未来若增加独立 API 层时的 `UploadFile` 路径；MVP 不要求 FastAPI。
- [Gradio Image](https://www.gradio.app/docs/gradio/image), [Audio](https://www.gradio.app/docs/gradio/audio), [DownloadButton](https://www.gradio.app/docs/gradio/downloadbutton), [Gradio 6 migration guide](https://www.gradio.app/guides/gradio-6-migration-guide) — 多模态展示与 6.x API。
- [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/) and [JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) — 严格结构验证与 schema 生成。
- [Pillow documentation](https://pillow.readthedocs.io/en/stable/) — 确定性图片绘制与保存。
- PyPI package metadata / local `pip index` and `pip --dry-run` — 2026-07-10 核验本文 Python 包版本及 Windows CPython 3.13 wheel 可解析性。

---
*Stack research for: DebugMate multimodal RAG debugging/learning agent*  
*Researched: 2026-07-10*
