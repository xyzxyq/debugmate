# Architecture Research

**Domain:** 面向 Python/AI 工程学习场景的多模态 RAG 报错诊断智能体  
**Researched:** 2026-07-10  
**Confidence:** MEDIUM（合同优先的混合架构为 HIGH；扣子当前细粒度节点、导出与日志能力需登录后现场验证）

## Executive Recommendation

采用“**平台无关的本地工程核心 + 可替换的云端智能体适配器**”，而不是把全部逻辑锁死在扣子画布中：

- 本地核心拥有输入规范化/脱敏、统一数据契约、结果校验、PNG/MP3 渲染、运行证据、评测和课程交付自动化。
- 云端平台只提供需要模型的能力：VLM 截图理解、LLM 路由/诊断、平台知识库检索，以及可交互演示。
- `DiagnosisRecord` 是文本、PNG、MP3和结果页唯一允许读取的事实源；渲染器不得各自重新调用 LLM。
- 扣子是首选交互平台，但必须先通过能力闸门；Dify Cloud 是有官方 API 依据的云端降级方案；若两者受登录、额度或导出限制，则启用 Python Web/CLI + 本地检索/TTS 降级。
- 真实用户输入优先从本地入口进入并在上传云端前脱敏。扣子原生聊天入口只使用已脱敏或合成的课程案例，避免把真实 Token、邮箱和个人路径先上传后再处理。

这套边界能同时满足“快速完成课程演示”和“仓库内可复现”两个目标。平台中心式单体虽然搭建最快，但无法可靠证明提示词版本、检索片段、节点执行和三种输出来自同一次诊断；全本地实现控制力最高，却会在短周期内增加模型接入、前端和部署工作量。

## Standard Architecture

### System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 入口层                                                               │
│  本地 Web/CLI（真实输入）        扣子/Dify 原生 UI（脱敏演示案例）    │
└───────────────────────┬──────────────────────────────┬───────────────┘
                        │                              │
┌───────────────────────▼──────────────────────────────▼───────────────┐
│ 本地可信边界                                                         │
│ Input Gateway → Normalize → Secret/PII Scan → Screenshot Masking     │
│             → EvidenceBundle + 原始文件哈希（原图不进入 Git）        │
└───────────────────────┬──────────────────────────────────────────────┘
                        │ 已脱敏文本/图像
┌───────────────────────▼──────────────────────────────────────────────┐
│ 模型编排边界（Provider Adapter）                                     │
│ VLM Extractor → Router → Retriever → Diagnosis Generator             │
│                  ↑          ↑                                       │
│                  │   Coze KB / Dify KB / Local FTS                   │
└───────────────────────┬──────────────────────────────────────────────┘
                        │ DiagnosisRecord JSON
┌───────────────────────▼──────────────────────────────────────────────┐
│ 本地确定性产物层                                                     │
│ Schema Validator → Text Renderer → PNG Renderer → TTS/MP3 Renderer   │
│                         └──────→ Unified Result Page                 │
└───────────────────────┬──────────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────────┐
│ 可复现与交付层                                                       │
│ Run Manifest / Provenance / Eval / Prompt Compare / PPT-Video Build  │
└──────────────────────────────────────────────────────────────────────┘
```

### Trust Boundaries

1. **原始输入区：** 原截图、原日志可能含敏感信息，只能暂存在 `runs/<run_id>/private/`，该目录必须被 Git 忽略；浏览器关闭或清理命令可删除。
2. **脱敏证据区：** 云端模型、运行日志、结果页、评测和课程材料只能读取 `EvidenceBundle` 及遮罩后的图像。
3. **知识区：** 只有带来源清单、官方 URL、抓取/更新时间和内容哈希的条目可以被同步到平台知识库。
4. **生成区：** LLM 输出是不可信数据，必须通过 JSON Schema/Pydantic 校验；其中的命令只作为字符串展示，首版绝不执行。
5. **交付区：** 只允许从已批准的运行清单复制产物；禁止把生成图片当作平台运行截图或评测证据。

### Component Responsibilities

| Component | Owns | Input → Output | Failure behavior |
|---|---|---|---|
| Input Gateway | 文件类型、大小、编码和 run ID | 用户输入 → `RawSubmission` | 拒绝未知/超限文件，不启动模型调用 |
| Normalizer | 换行、代码块、环境字段、文件清单、哈希 | `RawSubmission` → normalized draft | 保留原意，不“修正”报错文本 |
| Redaction Engine | Token/邮箱/用户名/绝对路径扫描与稳定占位符 | draft → `SanitizedSubmission` + `RedactionReport` | 命中高风险未能遮罩时 fail closed |
| Screenshot Masker | 本地 OCR/人工框选接口、图像遮罩 | 原图 → 脱敏图 + bbox 清单 | 无可用本地 OCR 时要求预脱敏；不得把原图发云端后再补救 |
| VLM Extractor | Traceback、错误行、包/版本、设备信息 | 脱敏图 → `VisualEvidence` | 低置信字段标记 uncertain，不覆盖用户文本 |
| Evidence Merger | 文本与视觉证据去重、冲突保存 | 多证据 → `EvidenceBundle` | 冲突项并列并请求补充，不擅自选边 |
| Router | 六类首版诊断域和检索过滤器 | evidence → `RouteDecision` | 允许 `unknown`/多标签，避免强制误分类 |
| Retriever Port | 查询构造、top-k、过滤和引用 ID | query/route → `RetrievedChunk[]` | 零命中返回空列表，禁止伪造来源 |
| Diagnosis Generator | 基于证据和检索生成严格 JSON | context → candidate `DiagnosisRecord` | 一次结构修复后仍失败则输出结构化错误，不转为自由文本 |
| Schema/Policy Validator | 字段、引用完整性、命令安全、事实/推断分离 | candidate → validated record | 引用不存在、泄密或危险命令未标注时拒绝发布 |
| Text Renderer | 人类可读中文诊断报告 | record → Markdown/HTML | 纯模板渲染，不调用 LLM |
| PNG Renderer | 动态诊断卡/流程图 | record → PNG | MVP 用 Pillow 确定性布局；可选 Mermaid 不能成为唯一实现 |
| TTS Renderer | 由记录生成短语音脚本并合成 | record → MP3 | 云 TTS 失败后走 Windows SAPI/WAV + FFmpeg；记录实际 provider |
| Result Composer | 统一结果页和下载清单 | artifacts → static HTML/package | 某模态失败时显示真实失败状态，不放伪占位成品 |
| Provenance Store | 提示词、模型、检索、哈希、耗时、状态 | stage events → `run_manifest.json` | 写入凭证前再次脱敏；API Key 永不落盘 |
| Evaluation Runner | 案例执行、规则评分、人工复核队列 | eval case × prompt/provider → JSONL/CSV/HTML | 可重复运行，平台失败与诊断失败分别计数 |
| Deliverable Builder | PPT/讲稿/字幕/视频的源文件追踪 | approved runs → deliverables | 只消费清单列出的真实产物和截图 |

## Core Contracts

### Single Source of Truth: `DiagnosisRecord`

建议以版本化 JSON Schema 定义，下列字段是跨平台最小合同：

```json
{
  "schema_version": "1.0.0",
  "run_id": "dm_20260710_001",
  "status": "complete|insufficient_evidence|partial|failed",
  "input_summary": {
    "sanitized": true,
    "modalities": ["text", "image"],
    "artifact_refs": ["input/screenshot.redacted.png"]
  },
  "classification": {
    "primary": "cuda_memory",
    "secondary": ["tensor_shape"],
    "rationale_evidence_ids": ["ev_01"]
  },
  "evidence": [
    {"id": "ev_01", "kind": "observed", "content": "...", "source": "user_text"}
  ],
  "root_cause_candidates": [
    {
      "id": "cause_01",
      "statement": "...",
      "basis": "inference",
      "supporting_evidence_ids": ["ev_01"],
      "knowledge_chunk_ids": ["kb_pytorch_oom_03"]
    }
  ],
  "checks": [{"order": 1, "instruction": "...", "command": "...", "risk": "read_only"}],
  "fixes": [{"order": 1, "instruction": "...", "conditions": ["..."]}],
  "verification": [{"instruction": "...", "command": "...", "expected_signal": "..."}],
  "missing_information": ["..."],
  "confidence": {"level": "low|medium|high", "rationale": "..."},
  "limitations": ["..."],
  "citations": [
    {"chunk_id": "kb_pytorch_oom_03", "source_url": "https://...", "title": "...", "retrieved_at": "..."}
  ],
  "render_plan": {"diagram_nodes": ["..."], "speech_sections": ["summary", "checks", "verification"]}
}
```

强制不变量：

- `observed` 只能来自用户文本、截图提取或环境字段；模型推断必须标为 `inference`。
- 每个事实性根因陈述必须同时指向输入证据或知识片段；无支持时进入 `missing_information`。
- `status=complete` 需要至少一个根因候选、一个检查步骤、一个验证步骤和一个有效引用。
- 三个渲染器只读同一个已校验 JSON；输出文件把 `run_id`、`schema_version` 和 JSON 哈希写入元数据/清单。
- 语音脚本可压缩内容，但不能引入 JSON 中不存在的原因或步骤。

### Other Contracts

- `EvidenceBundle`: 规范化文本、脱敏图像引用、VLM 字段、冲突、缺失字段、每项证据来源与置信标记。
- `RetrievedChunk`: 稳定 chunk ID、正文、标题、官方 URL、产品/版本、更新时间、检索得分、检索器名称。
- `ProviderRunResult`: provider、模型/工作流版本、request/run ID、开始结束时间、原始响应哈希、结构化 payload、错误分类。
- `ArtifactManifest`: 相对路径、MIME、SHA-256、生成器版本、源 `DiagnosisRecord` 哈希、是否允许进入课程交付。

## Recommended Project Structure

```text
.
├── pyproject.toml
├── .env.example                  # 只列变量名，不含密钥
├── src/debugmate/
│   ├── domain/                   # JSON/Pydantic 合同与状态机
│   │   ├── diagnosis.py
│   │   ├── evidence.py
│   │   └── provenance.py
│   ├── pipeline/                 # 平台无关用例编排
│   │   ├── normalize.py
│   │   ├── redact.py
│   │   ├── merge_evidence.py
│   │   ├── route.py
│   │   ├── diagnose.py
│   │   └── orchestrator.py
│   ├── ports/                    # VLM/LLM/RAG/TTS/Store 接口
│   ├── adapters/
│   │   ├── coze/                 # 扣子输入输出映射；能力闸门通过后启用
│   │   ├── dify/                 # 文件、工作流、知识库、TTS API
│   │   └── local/                # OCR、SQLite FTS、SAPI/FFmpeg、fixture
│   ├── renderers/                # markdown/html、Pillow PNG、MP3
│   ├── result_page/              # 静态模板与资源
│   ├── evaluation/               # runner、scorers、prompt comparator
│   └── cli.py
├── schemas/                      # 版本化 JSON Schema；跨平台源文件
├── prompts/
│   ├── v1/ ... v4/              # system、extract、route、diagnose + CHANGELOG
│   └── shared/                   # 注入防护与输出合同
├── knowledge/
│   ├── sources/                  # 可核验原文或允许保存的摘录
│   ├── manifests/                # URL、产品、版本、更新时间、许可证、哈希
│   ├── chunks/                   # 可重建 JSONL，不手工编辑
│   └── snapshots/                # 平台同步/检索配置摘要，不含密钥
├── platform/
│   ├── coze/                     # 画布说明、变量映射、真实配置截图清单
│   └── dify/                     # DSL/API 映射与降级说明
├── eval/
│   ├── cases/                    # 正确/不足/易混淆/隐私安全案例
│   ├── expected/                 # 允许集合与禁止项，不强绑唯一措辞
│   └── results/                  # 机器可读评分；大响应可忽略后归档
├── scripts/
│   ├── build_knowledge.py
│   ├── run_eval.py
│   ├── capture_run.py
│   ├── build_deliverables.py
│   └── verify_release.py
├── tests/                        # unit/contract/integration/e2e/fixtures
├── runs/                         # 本地运行区，默认 Git ignore
├── evidence/approved/            # 经脱敏、清单批准的课程证据
├── deliverables/
│   ├── sources/                  # PPT、讲稿、字幕、视频工程源文件
│   └── dist/                     # 可重建最终文件
└── docs/                         # 架构、操作手册、局限、演示脚本
```

### Structure Rationale

- **按稳定边界而非按平台分层：** `domain`、`pipeline`、`renderers` 和 `evaluation` 不依赖扣子/Dify；平台变化只影响 `adapters`。
- **资产与运行结果分离：** 提示词、知识源、评测案例可进 Git；原始运行区默认不进 Git；只有脱敏并签入清单的证据进入 `evidence/approved`。
- **源文件与生成物分离：** `knowledge/chunks`、`deliverables/dist` 都能由脚本重建，避免最终文件成为唯一来源。
- **不引入容器前提：** 所有入口提供 PowerShell 命令；MVP 依赖 Python venv 与现有 FFmpeg，不要求 Docker、Redis、Celery 或外部数据库。

## Architectural Patterns

### 1. Ports and Adapters for Platform Fallback

Pipeline 只依赖接口，provider 负责字段映射和能力差异：

```python
class DiagnosisProvider(Protocol):
    def extract_visual(self, image_ref: str) -> VisualEvidence: ...
    def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]: ...
    def generate(self, context: DiagnosisContext) -> ProviderRunResult: ...
```

优点是评测可对同一案例比较扣子、Dify 与本地 fixture；代价是首版要维护少量映射代码。不要抽象成通用“万能 Agent SDK”，只覆盖 DebugMate 用到的三个方法。

### 2. Stage State Machine + Idempotent Artifacts

单次运行状态：

```text
RECEIVED → SANITIZED → EXTRACTED → RETRIEVED → DIAGNOSED
         → VALIDATED → RENDERED → PACKAGED
                    ↘ INSUFFICIENT_EVIDENCE / PARTIAL / FAILED
```

每个阶段把结果写到独立文件并更新 manifest；重跑只覆盖同阶段的临时文件，成功后原子替换。这样云端超时、TTS失败或 PNG 生成失败时，不必重新消耗全部模型额度。

### 3. Evidence-First RAG

知识库不是“把网页丢进平台”即可。源清单先在本地生成稳定 chunk ID 和元数据，再同步到云端。检索查询由错误签名、包名、版本、平台和路由类别组成；诊断只接收 top-k 片段及其 ID。对于首版小型知识库，本地 SQLite FTS/BM25 是可复现的降级项，向量检索是可选增强，不应阻塞 MVP。

### 4. Deterministic Multimodal Rendering

PNG 使用模板和布局规则将根因、证据、检查链与验证信号绘制为诊断卡；MP3 的朗读文本由模板从相同记录压缩而来。确定性渲染比让图像模型“画流程图”更适合课程证据：可测试、无错字概率低、能证明三种模态一致。

## Data Flow

### Main Request Flow

```text
用户文本/截图/代码/环境
  → 建立 run_id 与原始文件哈希
  → 本地规范化 + 文本脱敏 + 截图遮罩
  → VLM 只读取脱敏截图，产出字段化视觉证据
  → 合并文本/视觉证据，显式保存冲突与缺失
  → 路由类别 + 构造检索查询
  → 检索知识片段并冻结本次命中快照
  → LLM 生成 DiagnosisRecord JSON
  → Schema、引用、泄密、命令风险校验
  → 同一 JSON 并行渲染 Markdown/HTML、PNG、MP3
  → 生成结果页、下载包、run manifest
  → 经人工批准后复制到 evidence/approved
```

### Knowledge Flow

```text
官方 URL 清单
  → 下载/摘录 + 元数据/许可证/时间/哈希
  → 清理与按语义标题切块
  → 生成稳定 chunk_id 和 JSONL
  → 质量检查（空段、重复、过期、URL 可达性）
  → 同步 Coze/Dify KB 或建立 Local FTS
  → 固定查询 smoke test
  → 保存同步摘要与检索结果快照
```

### Evaluation Flow

```text
eval case + prompt version + provider
  → 完整 pipeline
  → 合同校验评分
  → 隐私泄漏/引用完整性/事实-推断边界规则评分
  → 类别、根因允许集合、步骤覆盖率评分
  → PNG/MP3 可打开及源 JSON 哈希一致性检查
  → JSONL + 汇总 CSV/HTML + 人工复核队列
```

评测不要用自由文本逐字匹配；使用允许根因集合、必要检查点、禁止断言和安全规则。四版提示词必须在同一冻结案例与知识快照上比较。

### Deliverable Flow

```text
approved run manifests
  → 校验哈希/脱敏/三模态齐全
  → 结果截图与引用表
  → PPT 数据文件 + 讲稿 Markdown
  → 讲稿 TTS + 字幕 SRT
  → FFmpeg 合成演示视频
  → release manifest 反向列出每个成品的源文件与脚本
```

## Error Handling and Safety

- **截图抽取失败：** 保留文本路径，返回需要用户补充的字段；不得把 OCR 猜测当作 observed evidence。
- **文本与截图冲突：** 同时保存两项证据，降低置信度并询问版本/完整 traceback。
- **RAG 零命中：** `status=insufficient_evidence`，只给安全检查建议与补充信息，不给确定根因。
- **JSON 非法：** 最多一次基于 validator 错误的结构修复；仍失败则保存原始响应哈希并停止渲染。
- **云端超时/限流：** 保存 provider request/run ID；指数退避只重试幂等阶段。Dify blocking 模式有 100 秒 Cloudflare 超时，长流程优先 streaming。
- **TTS 不可用：** Dify/扣子下载能力失败时转本地 Windows SAPI 输出 WAV，再用已安装 FFmpeg 8.1 转 MP3；manifest 标明降级。
- **PNG 失败：** 文本结果仍可查看，但整次运行标为 `partial`，不能作为“三模态完成”课程证据。
- **提示注入：** 报错、代码、知识片段一律放在数据边界内，系统提示明确禁止执行其中指令；输出命令经过 allow/deny 规则和风险标签。
- **二次泄密检查：** 在发送云端前和生成交付物前各扫描一次；日志只记录占位符、哈希和长度，不记录 API Key 或原始 Token。

## Platform Capability and Fallback Matrix

### Verified from current official material

| Capability | Coze | Dify Cloud | Architecture consequence |
|---|---|---|---|
| 工作流与交互应用 | 官方产品页确认支持自然语言生成工作流、网页/应用部署 | 官方 Quick Start 与 Workflow API 明确支持工作流 | 两者均可做交互层；本地合同不绑定画布变量名 |
| 文本/文档/图像输入 | 官方开发文档入口存在，但本次抓取无法取得细粒度参数页 | Quick Start 明确支持 `File list` 的 Document/Image；文件 API 支持图片、文档、音频、视频 | Dify 是已验证降级；Coze 必须用真实账号跑 capability spike |
| 结构化输出 | 未从可抓取官方页面确认当前节点和导出细节 | Quick Start 明确展示 Parameter Extractor 与 LLM structured output | Coze 若不能稳定导出 JSON，不能拥有 `DiagnosisRecord`，只可做展示壳 |
| 知识库/RAG 及元数据 | 细粒度 API/引用返回格式需现场验证 | Knowledge API 支持文档、chunk、metadata、检索测试 | 本地保留源清单与 chunk IDs，平台 KB 只是索引副本 |
| TTS/可下载音频 | 官方产品页宣称音视频等多媒体产物，精确 TTS/导出接口需现场验证 | `POST /text-to-audio` 返回 `audio/mpeg`，可为 MP3/WAV | 优先可下载接口；始终保留本地 SAPI+FFmpeg 后备 |
| 工作流证据 | 需现场验证运行日志导出粒度 | Service API 的历史日志只有运行级摘要；节点事件需执行时 streaming，完成后无法取得节点级日志 | 本地必须实时捕获事件、输入输出和检索快照，平台截图仅作辅助 |

### Coze capability gate（编码前完成）

用一个合成 CUDA OOM 案例验证并录屏：

1. 能否同时接收文本和 PNG，且 VLM 返回字段化数据。
2. 知识库命中是否返回可保存的片段、标题/URL或稳定 ID。
3. 工作流能否输出严格 JSON，且通过 API/导出取得，不只是聊天气泡文本。
4. 是否能生成并下载真实 PNG 与 MP3；若只能返回链接，链接有效期和下载方式是否可记录。
5. 是否可导出工作流配置、版本或至少保存节点变量/提示词清单。
6. 免费额度是否足够跑最小评测集；任何付费项在启用前单独确认。

判定规则：1–3 任一失败，直接将 Dify 设为云端主适配器；4 失败仅把该模态移到本地渲染；5 失败则平台只作演示镜像；6 失败使用本地 fixture 完成工程链，并等待额度后补真实云端证据。

### Fallback Ladder

```text
Coze full workflow
  ├─ 缺 TTS/PNG 导出 → Coze VLM/RAG/LLM + local renderers
  ├─ 缺 JSON/引用/日志 → Dify Cloud workflow + local evidence runner
  └─ 登录/额度不可用 → Python CLI/Web + Local FTS + configured model API
                           └─ 模型 API 也不可用 → frozen fixtures 仅开发/测试，
                              不宣称完整智能体已在线运行
```

## Build Order

按“每一步都有可验收产物”建设，避免先画完整云端工作流再发现无法导出：

1. **能力闸门与合同 fixture：** 完成 Coze 六项 spike；同时冻结 `DiagnosisRecord v1`、一个合成输入和一个合法结果 fixture。验收：fixture 可通过 schema 校验。
2. **本地隐私入口：** 实现输入校验、规范化、文本脱敏、截图遮罩接口与双重泄密扫描。验收：隐私案例不会进入 cloud payload 或日志。
3. **三模态确定性闭环：** 先用 fixture 生成 Markdown/HTML、PNG、MP3、结果页和 manifest。验收：三文件可打开且指向同一 JSON SHA-256。这一步最早证明多模态课程合规。
4. **知识资产与本地检索：** 建官方源清单、chunk pipeline、稳定 ID 和 Local FTS smoke tests。验收：固定查询命中预期来源且能重建索引。
5. **云端模型适配器：** 按闸门结果先实现 Coze 或 Dify 的文件上传、VLM、检索/诊断和运行事件捕获。验收：真实合成案例返回可校验 `DiagnosisRecord`。
6. **端到端编排与降级：** 串联状态机、失败恢复、provider fallback 和统一结果页。验收：文本-only、图文、零命中、TTS失败四条路径状态正确。
7. **评测与提示词 V1–V4：** 建四类案例、规则评分、提示词对照和引用/隐私评分。验收：同一冻结快照可一键重跑并生成 JSONL/CSV/HTML。
8. **课程证据与交付自动化：** 从 approved manifests 生成截图清单、PPT 数据、讲稿、SRT、MP3和视频。验收：release manifest 能追溯每个成品到源文件、run ID 和脚本。
9. **最终平台镜像与演示演练：** 将已验证提示词/知识快照同步到选定平台，录制真实运行。验收：演示案例现场运行成功；录像与仓库 manifest 一致。

前三步不依赖云端登录，可立即开始；第 4 步与第 5 步可以在合同冻结后并行，但不得让平台字段反向污染领域 schema。

## Testing Strategy

| Layer | Tests | Required evidence |
|---|---|---|
| Unit | 正则脱敏、路径占位、路由规则、文本/PNG/speech 模板 | pytest 输出 |
| Contract | JSON Schema、provider payload 映射、引用 ID 完整性 | fixture + schema report |
| Integration | Coze/Dify sandbox、KB 检索、TTS、超时/限流 | 脱敏响应、run ID、时间戳 |
| E2E | 图文输入到结果包；零命中；隐私；provider fallback | `run_manifest.json` + 三模态哈希 |
| Visual/audio | PNG 尺寸/文字溢出；MP3 MIME/时长/可解码 | Pillow/FFprobe 检查 + 人工抽检 |
| Coursework release | 无占位符、无密钥、来源 URL 可追溯、PPT/视频引用真实 run | `verify_release` 报告 |

评测结果必须区分：模型诊断质量、平台/网络失败、渲染失败和证据采集失败，不能把平台不可用算成错误根因。

## Scaling Considerations

| Scale | Architecture adjustment |
|---|---|
| 课程单人/数十次运行 | 单 Python 进程、文件制 run store、SQLite FTS、同步渲染足够；这是目标形态 |
| 小班级/数百并发前 | 将运行元数据迁至 SQLite/PostgreSQL、对象存储产物、后台作业队列；仍保持相同合同 |
| 公开服务/上千并发 | 再考虑异步 worker、限流、租户隔离、病毒扫描、保留策略和独立观测系统；不属于首版 |

最先出现的瓶颈通常是云模型/TTS 额度和单次延迟，不是本地 CPU。先缓存知识快照、对同一输入使用 content hash 去重、让三个渲染器并行；不要提前引入微服务或 Kubernetes。

## Anti-Patterns

### Platform-as-Database

**错误：** 提示词、知识文档、结果和运行历史只存在于扣子/Dify。  
**后果：** 无法版本对比、迁移、复评或证明课程工作量。  
**替代：** 仓库资产为源，平台是可重建镜像；每次运行落本地 manifest。

### Three Independent Generators

**错误：** 文本、流程图和语音分别提示 LLM 生成。  
**后果：** 三种模态会产生互相矛盾的根因和步骤。  
**替代：** 先校验一次 `DiagnosisRecord`，再确定性渲染。

### Upload Then Redact

**错误：** 先把原截图上传云端，让 VLM 找到 Token 后再遮罩。  
**后果：** 敏感内容已经越过信任边界。  
**替代：** 本地预扫描/遮罩；平台原生入口只接收合成或预脱敏案例。

### Screenshot-Only Evidence

**错误：** 用平台截图证明整个流程。  
**后果：** 截图不能验证真实输入、检索片段、提示词版本和产物关联。  
**替代：** 截图 + run manifest + 结构化 JSON + 哈希 + streaming 事件/响应摘要共同构成证据。

### LLM-Drawn Technical Diagram as Proof

**错误：** 用图像生成模型绘制“诊断流程图”，并把它当运行结果。  
**后果：** 文字易错且无法验证与诊断一致。  
**替代：** 由 schema 字段确定性绘图；生成式图片仅可作明确标注的装饰，不计核心证据。

### Premature Full Local Platform

**错误：** 首版自建账号、队列、向量库、对象存储和复杂前端。  
**后果：** 工期被基础设施吞噬。  
**替代：** CLI/静态结果页 + 云端交互平台；只有能力闸门失败才启用最小 Python Web。

## Sources

- [Coze 官方产品概览](https://www.coze.cn/overview) — 当前产品页确认工作流、Web/App 部署与多媒体产物方向；细粒度 API/节点能力仍需账号内验证。
- [Coze 官方开发文档入口](https://www.coze.cn/open/docs/developer_guides/coze_api_overview) — 本次研究环境可打开入口，但动态页面未返回可引用的参数正文，因此未据此宣称具体 API 能力。
- [Dify 30-Minute Quick Start](https://docs.dify.ai/en/quick-start) — Workflow、文本/文档/图像输入、Parameter Extractor、IF/ELSE 与 structured output。
- [Dify Run Workflow API](https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow) — 已发布工作流、文件变量、blocking/streaming、run ID 与 100 秒 blocking 超时。
- [Dify Upload File API](https://docs.dify.ai/en/api-reference/files/upload-file) — 图像、文档、音频、视频多模态文件上传。
- [Dify Convert Text to Audio API](https://docs.dify.ai/en/api-reference/audio/convert-text-to-audio) — TTS 及 `audio/mpeg`、MP3/WAV 响应。
- [Dify List Workflow Logs API](https://docs.dify.ai/en/api-reference/workflow-runs/list-workflow-logs) — 历史 API 仅运行级摘要，节点事件需执行时 streaming，完成后无节点级 Service API 日志。
- [Dify Knowledge Base API](https://docs.dify.ai/en/api-reference/knowledge-bases/update-knowledge-base) — 知识库检索配置、metadata、文档模式与 multimodal 标记。
- [Dify Test Retrieval API](https://docs.dify.ai/en/api-reference/knowledge-bases/retrieve-chunks-from-a-knowledge-base-test-retrieval) — 基于 query 的知识片段检索测试。

---
*Architecture research for: DebugMate multimodal RAG debugging and learning agent*  
*Researched: 2026-07-10*
