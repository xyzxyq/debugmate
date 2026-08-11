---
phase: 08
slug: dify-unified-live-chain
status: audited
nyquist_compliant: true
wave_0_complete: true
executed_scope: "08-01..08-06"
automated_scope_status: green
live_acceptance_status: blocked
created: 2026-08-10
audited: 2026-08-11
---

# Phase 08 — Validation Strategy

> 验证经一次性批准后，真实 Dify 工作流、17 源知识库、严格本地校验和现有多模态结果链能形成可追溯、可失败、不可静默降级的统一闭环。

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest 9.1.1 + Playwright 1.61.0（Microsoft Edge） |
| Config file | `pyproject.toml` |
| Executed-scope run A | `.\.venv\Scripts\python.exe -m pytest tests/diagnosis/test_command_safety.py tests/platform/test_dify_live_evidence.py tests/test_probe_cli.py tests/cloud/test_run_envelope.py tests/cloud/test_receipts.py tests/knowledge/test_coverage_sync.py tests/knowledge/test_dify_readback.py tests/cloud/test_settings.py tests/cloud/test_dify_adapter.py tests/cloud/test_gateway.py tests/privacy/test_approval_gateway.py tests/platform/test_dify_dsl.py -q` |
| Executed-scope run B | `.\.venv\Scripts\python.exe -m pytest tests/diagnosis/test_workflow_e2e.py tests/diagnosis/test_workflow_evidence.py tests/results/test_contracts.py tests/results/test_backend_provenance.py tests/results/test_publisher.py tests/results/test_loader.py tests/results/test_service.py tests/results/test_media.py tests/results/test_tts_chain.py tests/cloud/test_live_workflow.py tests/diagnosis/test_evidence_binding.py tests/diagnosis/test_generation.py tests/results/test_security_abuse.py tests/ui/test_dify_live.py tests/ui/test_app.py tests/ui/test_view_state.py tests/ui/test_real_input.py tests/results/test_result_e2e.py -q` |
| Full offline suite | `.\.venv\Scripts\python.exe -m pytest -q`，随后 `.\.venv\Scripts\python.exe -m ruff check src tests` |
| Phase gate | 显式 cloud marker 零跳过 + Phase 08 Edge runner 零跳过 + FFprobe/ZIP/evidence/security validators 全绿 |

## Sampling Rate

- 每个任务提交后：运行直接受影响测试、`tests/diagnosis/test_command_safety.py` 与 scoped Ruff。
- 每个 wave 完成后：运行默认离线全量 pytest、全量 Ruff、冻结媒体检查。
- 最终验收前：运行知识库 readback、真实 Dify smoke、真实 Edge 端到端、证据与秘密扫描。
- 云端测试必须显式 marker；默认测试不得因缺少网络、额度或密钥而变成隐式调用。

## Requirement Verification Map

| Req ID | Observable behavior | Test layers | Automated gate | Wave 0 gap |
|---|---|---|---|---|
| KNOW-03 | 17 个 Git 知识源完成封闭同步、索引等待、元数据/配置/数量回读；意外删除失败关闭 | unit + cloud integration | `pytest tests/knowledge/test_coverage_sync.py tests/knowledge/test_dify_readback.py -q` | 新建 readback fixtures/tests |
| KNOW-04 | 诊断与直接知识检索 trace 来自同一次 workflow run，并绑定 source/build | contract + cloud | `pytest tests/cloud/test_run_envelope.py tests/diagnosis/test_evidence_binding.py -q` | 新建 envelope contract |
| DIAG-02 | 严格 1.1.0 诊断；最多一次修复；隐私或危险命令问题不可修复并终止 | unit + cloud | `pytest tests/diagnosis/test_generation.py tests/cloud/test_live_workflow.py -q` | 新建 live workflow fixtures |
| MULTI-03 | 已验证云端诊断进入现有 Markdown/PNG/MP3/ZIP 结果链 | integration + Edge | `pytest tests/results/test_media.py tests/results/test_tts_chain.py -q` + Phase 08 Edge gate | 新建真实云端 QA |
| UX-01 | 单页明确展示 `dify`、`local_fallback` 或 `replay`，且失败不暴露伪制品 | UI + browser | `pytest tests/ui/test_dify_live.py -q` + Phase 08 Edge gate | 新建 backend truth fixtures |
| EVID-01 | receipt、run fingerprint、usage 和制品哈希可复核；无 secret/raw remote ID/provider body | adversarial + E2E | `pytest tests/cloud/test_receipts.py tests/cloud/test_live_workflow.py tests/results/test_security_abuse.py -q` | 新建 receipt/live tests |

## Per-Task Verification Map — Executed Scope

| Task ID | Requirement | Type | Behavioral test file(s) | Automated command | Status |
|---|---|---|---|---|---|
| 08-01-01 | DIAG-02, EVID-01 | integration | `tests/platform/test_dify_live_evidence.py`, `tests/test_probe_cli.py`, `tests/diagnosis/test_command_safety.py` | `.\.venv\Scripts\python.exe -m pytest tests/diagnosis/test_command_safety.py tests/platform/test_dify_live_evidence.py tests/test_probe_cli.py -q` | green |
| 08-01-02 | DIAG-02, EVID-01 | unit + integration | `tests/cloud/test_run_envelope.py`, `tests/cloud/test_receipts.py` | `.\.venv\Scripts\python.exe -m pytest tests/cloud/test_run_envelope.py tests/cloud/test_receipts.py -q` | green |
| 08-02-01 | KNOW-03 | integration | `tests/knowledge/test_coverage_sync.py`, `tests/knowledge/test_dify_readback.py` | `.\.venv\Scripts\python.exe -m pytest tests/knowledge/test_coverage_sync.py tests/knowledge/test_dify_readback.py -q` | green (offline/fake transport) |
| 08-02-02 | KNOW-03 | smoke + integration | `tests/knowledge/test_coverage_sync.py`, `tests/knowledge/test_dify_readback.py` | `.\.venv\Scripts\python.exe -m pytest tests/knowledge -q` | green (offline gate) |
| 08-03-01 | KNOW-04, DIAG-02, EVID-01 | unit + integration | `tests/cloud/test_settings.py`, `tests/cloud/test_dify_adapter.py` | `.\.venv\Scripts\python.exe -m pytest tests/cloud/test_settings.py tests/cloud/test_dify_adapter.py -q` | green |
| 08-03-02 | KNOW-04, DIAG-02, EVID-01 | integration | `tests/cloud/test_gateway.py`, `tests/privacy/test_approval_gateway.py` | `.\.venv\Scripts\python.exe -m pytest tests/cloud/test_gateway.py tests/privacy/test_approval_gateway.py -q` | green |
| 08-03-03 | KNOW-04, DIAG-02, EVID-01 | contract | `tests/platform/test_dify_dsl.py`, `tests/cloud/test_run_envelope.py` | `.\.venv\Scripts\python.exe -m pytest tests/platform/test_dify_dsl.py tests/cloud/test_run_envelope.py -q` | green |
| 08-04-01 | UX-01, EVID-01 | integration | `tests/diagnosis/test_workflow_e2e.py`, `tests/diagnosis/test_workflow_evidence.py`, `tests/results/test_contracts.py`, `tests/results/test_backend_provenance.py` | `.\.venv\Scripts\python.exe -m pytest tests/diagnosis/test_workflow_e2e.py tests/diagnosis/test_workflow_evidence.py tests/results/test_contracts.py tests/results/test_backend_provenance.py -q` | green |
| 08-04-02 | UX-01, EVID-01 | integration | `tests/results/test_backend_provenance.py`, `tests/results/test_publisher.py`, `tests/results/test_loader.py`, `tests/results/test_service.py`, `tests/results/test_media.py`, `tests/results/test_tts_chain.py` | `.\.venv\Scripts\python.exe -m pytest tests/results/test_backend_provenance.py tests/results/test_publisher.py tests/results/test_loader.py tests/results/test_service.py tests/results/test_media.py tests/results/test_tts_chain.py -q` | green |
| 08-05-01 | KNOW-04, DIAG-02, EVID-01 | integration | `tests/cloud/test_live_workflow.py`, `tests/cloud/test_receipts.py`, `tests/diagnosis/test_evidence_binding.py` | `.\.venv\Scripts\python.exe -m pytest tests/cloud/test_live_workflow.py tests/cloud/test_receipts.py tests/diagnosis/test_evidence_binding.py -q` | green (fake provider) |
| 08-05-02 | KNOW-04, DIAG-02, EVID-01 | integration | `tests/diagnosis/test_generation.py`, `tests/cloud/test_live_workflow.py`, `tests/results/test_service.py`, `tests/results/test_security_abuse.py` | `.\.venv\Scripts\python.exe -m pytest tests/diagnosis/test_generation.py tests/cloud/test_live_workflow.py tests/results/test_service.py tests/results/test_security_abuse.py -q` | green |
| 08-06-01 | MULTI-03, UX-01 | UI integration | `tests/ui/test_dify_live.py`, `tests/ui/test_app.py` | `.\.venv\Scripts\python.exe -m pytest tests/ui/test_dify_live.py tests/ui/test_app.py -q` | green |
| 08-06-02 | MULTI-03, UX-01 | UI integration | `tests/ui/test_dify_live.py`, `tests/ui/test_view_state.py`, `tests/ui/test_real_input.py`, `tests/ui/test_app.py` | `.\.venv\Scripts\python.exe -m pytest tests/ui/test_dify_live.py tests/ui/test_view_state.py tests/ui/test_real_input.py tests/ui/test_app.py -q` | green |
| 08-06-03 | MULTI-03, UX-01 | end-to-end integration | `tests/results/test_result_e2e.py`, `tests/results/test_tts_chain.py`, `tests/ui/test_dify_live.py` | `.\.venv\Scripts\python.exe -m pytest tests/results/test_result_e2e.py tests/results/test_tts_chain.py tests/ui/test_dify_live.py -q` | green |

## Wave 0 Requirements

- [x] 移除 `src/debugmate/dify_live_evidence.py` 的进程能力；由外部 QA 注入严格 tracked inventory，使 command-safety 全绿。
- [x] 建立严格 run envelope、usage、attempt、receipt 模型和对抗 fixtures。
- [x] 建立知识 API 分页、索引状态、metadata/config/count readback fixtures。
- [x] 扩展 outcome/manifest/view fixtures，冻结 backend provenance 迁移合同。
- [x] 建立显式 Phase 08 cloud 与 Edge runner/evidence namespace。

以上表示测试基础设施已建立，不表示 08-07 的真实 cloud/Edge runner 已执行或通过。

## Threat References

| Ref | STRIDE | Threat | Required control |
|---|---|---|---|
| T-08-ORIGIN | Spoofing / Information disclosure | 恶意 base URL 或 redirect 转发 bearer key | 只允许精确 HTTPS origin；拒绝 userinfo/query/fragment/redirect；测试 origin 单独注入 |
| T-08-DUPLICATE | Tampering / DoS | 超时、双击或重启造成重复付费 workflow | 一次性 consume、持久 receipt、仅连接前失败可重试、歧义超时进入 `uncertain` |
| T-08-UPLOAD | Tampering | 批准后图片被替换或 MIME 混淆 | root confinement、重算 SHA、不可变 bytes、解码/格式校验、上传 MIME 一致 |
| T-08-INJECTION | Tampering / Elevation | 日志、代码、截图或知识文本注入提示/命令 | 所有输入只作数据；无工具执行；本地 schema/fact/evidence/command 严格校验 |
| T-08-CITATION | Tampering | 模型伪造引用或复制旧检索内容 | 只信 Knowledge Retrieval 节点直接投影，并与同一 run/source/build 指纹绑定 |
| T-08-LEAK | Information disclosure | key、provider body、远端 ID 或原始输入进入 UI/证据/ZIP | allowlist 投影、指纹化 ID、安全错误、证据与 DOM secret scan |
| T-08-SIZE | DoS | 超大/递归 JSON 或 trace | 解析前 raw byte cap；深度、条目和字符串长度上限；`extra='forbid'` |
| T-08-RACE | Tampering | 旧请求完成后覆盖新结果 | Phase 7 session/revision lease + per-case lock + receipt identity；仅当前 lease 可发布 |
| T-08-COMMAND | Elevation | 模型命令被误执行 | 命令保持惰性文本；危险命令 validator；仓库 command-safety 门禁 |
| T-08-KNOWLEDGE | Tampering / DoS | 同步过程删除非预期远端知识 | 完整 preflight inventory、sealed plan、显式删除确认、同步后精确 readback |

## Real-Service Checkpoints

| Checkpoint | Blocking point | Required evidence |
|---|---|---|
| App input shape | adapter/DSL 完成后 | Get App Parameters + 一张已提交脱敏图的上传与 singular `image_input` 实跑 |
| Retrieval shape | DSL/knowledge 完成后 | Knowledge Retrieval `result` 的真实 keys、source/build 绑定和同 run fingerprint |
| Dataset authority | 17 源同步前 | `DIFY_DATASET_API_KEY` 已配置但不读取/输出值；当前 dataset binding 可回读 |
| DSL portability | 发布验收前 | 当前应用导出、独立导入/重导出结构比较及新应用实跑 |
| Usage truth | 最终真实 run | provider 返回则记录 allowlisted usage；缺失则显式 `not_reported` |

缺少知识库专用 Key 时，离线实现与普通 `local_fallback` 可以继续，但 KNOW-03 和 Phase 08 最终真实验收不得标记通过。

## Manual-Only Verification

| Behavior | Why manual | Instruction |
|---|---|---|
| 仅在 Dify Cloud 要求重新登录、验证码、控制台发布/导入且 API 无法完成时暂停 | 这些动作需要用户账号权限，不能从仓库推断或绕过 | 明确指出页面、按钮、预期结果和回传截图；其余命令与验证由 Codex 执行 |
| 08-07 真实知识库同步与 readback | 当前缺少 `DIFY_DATASET_API_KEY`、`DIFY_DATASET_ID`，且 app-ready gate 未满足；离线 fake transport 不能证明真实 17 源云端状态 | 配置专用 dataset key/id 后执行显式 cloud marker，确认分页、索引、metadata/config/count 精确回读且零跳过 |
| 08-07 真实 Dify + Microsoft Edge 统一链验收 | 需要已发布 app、真实账号/额度、浏览器会话与同一次 run 的服务端证据 | 在 Phase 08 Edge runner 中提交脱敏文本/截图，核对 `dify` backend、同 run retrieval/diagnosis、Markdown/PNG/MP3/ZIP、receipt/usage/hash 与 DOM/ZIP secret scan；任何跳过均不算通过 |

## Validation Sign-Off

- [x] 六个 Phase 08 requirements 均有自动化验收路径
- [x] 所有计划任务必须带 focused verify，且每个 wave 有离线回归
- [x] Wave 0 覆盖当前缺失合同和 command-safety 红灯
- [x] 云端调用被隔离为显式 marker，默认测试无隐式网络
- [x] 威胁模型覆盖 origin、重复调用、TOCTOU、注入、泄漏、DoS 和知识同步
- [x] 媒体、课程截图、PPTX、MP4、SRT 在 Phase 08 全程冻结

**Approval:** approved 2026-08-10

## Validation Audit 2026-08-11

| Metric | Count |
|---|---:|
| Executed tasks audited (08-01..08-06) | 14 |
| Covered | 14 |
| Partial | 0 |
| Missing | 0 |
| New test files required | 0 |
| Gaps found | 0 |
| Resolved by new tests | 0 |
| Escalated implementation bugs | 0 |
| Pending live acceptance plans | 1 (08-07) |

Current execution evidence:

- Run A: **202 passed, 1 deselected** in 7.03s.
- Run B: **350 passed, 1 warning** in 110.34s.
- The deselection is an explicit live/cloud marker. The warning is the existing Starlette/httpx dependency deprecation warning.
- `nyquist_compliant: true` applies only to the executed 08-01..08-06 implementation scope. `live_acceptance_status: blocked` remains authoritative for 08-07; no cloud, Edge, dataset, TTS, or provider acceptance is inferred from offline tests.
