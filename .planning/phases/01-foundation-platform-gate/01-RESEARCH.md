# Phase 1 Research: 工程骨架与平台能力闸门

**Researched:** 2026-07-10  
**Scope:** INP-04, EVID-01, EVID-02  
**Confidence:** HIGH（本地Python合同与证据层）；MEDIUM（Dify账号、模型和TTS需执行期现场探针）

## Research Question

如何用最少人工和最小平台耦合建立DebugMate的可测试骨架，使后续文本、PNG、MP3都能围绕同一案例和同一结构化诊断追溯，同时在Dify不可用时仍保留真实可执行的本地证据链？

## Recommended Implementation Pattern

采用四层最小结构：

1. `domain`：Pydantic v2严格模型、`case_id`、版本常量和哈希辅助。
2. `evidence`：每案例自包含目录、临时目录写入、manifest与SHA-256。
3. `adapters`：`fixture`和`dify`实现同一窄端口；fixture先跑通，Dify仅在有环境变量时执行在线探针。
4. `cli`：初始化案例、验证fixture、运行平台探针和输出JSON报告。

首阶段不创建Gradio界面、不抓取正式知识库、不实现完整诊断提示词。这样可以在没有云账号时完成全部离线合同测试，并把云平台真实状态标为`pass/fail/blocked/not-tested`。

## Exact Repository Skeleton

```text
pyproject.toml
.env.example
.gitignore
README.md
src/debugmate/
  __init__.py
  cli.py
  contracts.py
  hashing.py
  evidence.py
  settings.py
  adapters/
    __init__.py
    base.py
    fixture.py
    dify.py
platform/dify/
  README.md
  app.dsl.yml.example
  capability-matrix.json
fixtures/cases/module_not_found/
  input.json
  diagnosis.json
prompts/
  README.md
knowledge/
  manifest.schema.json
scripts/
  run_phase1_probe.ps1
tests/
  test_contracts.py
  test_evidence.py
  test_fixture_adapter.py
  test_probe_cli.py
evidence/.gitkeep
```

## Contract Recommendations

### `case_id`

- 生成格式：`case_<uuid.uuid4().hex>`。
- 正则：`^case_[0-9a-f]{32}$`。
- 不使用时间或用户名，避免信息泄漏和时区差异。

### `DiagnosisRecord v1`

- Pydantic `ConfigDict(strict=True, extra='forbid')`。
- 必需字段：`schema_version`, `case_id`, `category`, `observed_facts`, `root_cause_candidates`, `missing_information`, `checks`, `fixes`, `verification_steps`, `confidence`, `limitations`, `recap_text`, `citations`。
- `schema_version`固定为`1.0.0`。
- `confidence`限制`0.0..1.0`。
- 命令字段首版只存字符串、平台、影响、预期结果和回退说明，不执行。
- JSON Schema由`DiagnosisRecord.model_json_schema()`生成，禁止手写第二份漂移Schema。

### Evidence Manifest

`manifest.json`最少包含：

- `manifest_version`, `case_id`, `status`, `created_at_utc`, `completed_at_utc`
- `backend`, `workflow_version`, `prompt_version`, `schema_version`, `knowledge_version`
- `input_sha256`, `run_id`, `node_states`, `latency_ms`, `token_usage`, `estimated_cost`
- `artifacts[]`: 相对路径、MIME、字节数、SHA-256
- `probe_capabilities`: 七项能力状态和证据文件路径

写入策略：创建同级`.tmp-<case_id>`目录，所有文件写完并校验后使用`Path.replace()`发布为`evidence/<case_id>`；失败也写`status=failed`并保留明确错误，不发布缺少manifest的目录。

## Narrow Platform Port

首版只需要四个方法：

```python
class DiagnosisBackend(Protocol):
    def upload_file(self, path: Path, user: str) -> UploadedFile: ...
    def run_workflow(self, inputs: dict[str, object], user: str) -> WorkflowRun: ...
    def synthesize_audio(self, text: str, user: str) -> bytes: ...
    def capability_probe(self) -> CapabilityProbeResult: ...
```

`FixtureBackend`完全离线读取固定JSON；`DifyBackend`只通过`httpx`访问配置的base URL，API key必须来自环境变量。Phase 1不实现重试风暴：连接类错误最多重试一次，认证/配额/4xx直接记录失败。

## Dify Capability Probe

探针矩阵固定七项：

| ID | Capability | Pass evidence |
|----|------------|---------------|
| C01 | Authentication/API | 返回非401/403的API响应和run/request ID |
| C02 | File upload | 虚构截图上传得到file ID |
| C03 | Vision extraction | 返回截图中的`ModuleNotFoundError`关键文本 |
| C04 | Knowledge retrieval | 返回至少一个chunk及来源元数据 |
| C05 | Structured JSON | 响应通过`DiagnosisRecord.model_validate_json()` |
| C06 | DSL export/import | 仓库保存实际导出DSL并记录重导入结果 |
| C07 | TTS | 保存`audio/mpeg`且FFprobe可读取时长 |

执行期没有账号或密钥时，C01–C07必须是`blocked`或`not-tested`，不能标为失败或通过。在线探针不应打印API key，也不把请求Authorization头写入evidence。

## Threat Model

| Threat | Severity | Structural control |
|--------|----------|--------------------|
| API key进入日志/Git | Critical | 环境变量、日志allowlist、`.env`忽略、提交前secret扫描 |
| 云端自由JSON破坏合同 | High | 严格Pydantic校验，最多一次修复，失败即停止 |
| 半成品证据被当作成功 | High | 临时目录+原子发布，manifest状态与哈希必需 |
| 平台配置成为唯一事实源 | High | DSL、Prompt、fixture、Schema和探针报告落Git |
| fixture被误当真实云结果 | High | `backend=fixture`和UI/报告显式标识 |
| Windows中文路径/编码失败 | Medium | `pathlib`、UTF-8、`-LiteralPath`、ASCII内容fixture |

Phase 1的Critical/High威胁必须在对应计划中有自动测试或明确的在线手工探针，不允许留到后续阶段。

## Validation Architecture

### Test layers

1. **Unit:** case ID、严格Schema、哈希、设置读取。
2. **Contract:** fixture通过Schema；额外字段、错误类型、错case ID必须失败。
3. **Filesystem integration:** 原子evidence发布、失败manifest、产物SHA-256复算。
4. **CLI integration:** `python -m debugmate.cli fixture-probe --output ...`退出0并生成七项本地报告。
5. **Cloud smoke:** 仅当`DIFY_API_KEY`存在时运行；默认pytest套件不得依赖网络。
6. **Security:** Git tracked files不包含密钥样式；CLI输出不回显Authorization或密钥值。

### Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q -m "not cloud"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m debugmate.cli fixture-probe --output .artifacts\phase1-fixture
.\scripts\run_phase1_probe.ps1
git grep -n -I -E "(sk-[A-Za-z0-9_-]{16,}|DIFY_API_KEY=.+)" -- . ':!*.example'
```

### Sampling

- 每个任务提交前运行与该任务对应的测试文件。
- 每个wave结束运行`pytest -q -m "not cloud"`和`ruff check .`。
- Phase完成前重新计算一个evidence目录全部哈希，并在有Dify凭据时运行在线探针。
- 最大本地反馈延迟目标：30秒；在线探针不计入快速循环。

## Planning Implications

建议三个计划：

1. **Plan 01-01 / Wave 1:** Python骨架、严格合同、fixture和基础测试。
2. **Plan 01-02 / Wave 2:** evidence原子落盘、manifest、哈希和安全设置。
3. **Plan 01-03 / Wave 3:** Dify窄适配器、能力探针CLI、PowerShell脚本、平台报告和最终Phase验证。

后一个计划依赖前一个计划，避免两个执行器同时修改`pyproject.toml`、合同或CLI入口。

## Sources

- `.planning/research/STACK.md` — 已核验的Dify/Python主栈、版本和降级顺序。
- `.planning/research/ARCHITECTURE.md` — 单一事实源、端口适配器和证据目录模式。
- `.planning/research/PITFALLS.md` — Schema漂移、平台锁定、密钥泄漏和伪证据风险。
- [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/) — 严格验证。
- [Pydantic JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) — 从模型生成Schema。
- [Dify workflow API](https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow) — 文件变量、blocking/streaming和run ID。
- [Dify file upload API](https://docs.dify.ai/en/api-reference/files/upload-file) — 文件上传合同。
- [Dify TTS API](https://docs.dify.ai/api-reference/tts/convert-text-to-audio) — `audio/mpeg`响应。

---
*Ready for planning: yes*
