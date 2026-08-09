---
phase: 08
slug: dify-unified-live-chain
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-10
---

# Phase 08 — Validation Strategy

> 验证经一次性批准后，真实 Dify 工作流、17 源知识库、严格本地校验和现有多模态结果链能形成可追溯、可失败、不可静默降级的统一闭环。

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest 9.1.1 + Playwright 1.61.0（Microsoft Edge） |
| Config file | `pyproject.toml` |
| Quick run | `.\.venv\Scripts\python.exe -m pytest tests\cloud tests\knowledge\test_dify_readback.py tests\results\test_backend_provenance.py tests\ui\test_dify_live.py -q` |
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

## Wave 0 Requirements

- [ ] 移除 `src/debugmate/dify_live_evidence.py` 的进程能力；由外部 QA 注入严格 tracked inventory，使 command-safety 全绿。
- [ ] 建立严格 run envelope、usage、attempt、receipt 模型和对抗 fixtures。
- [ ] 建立知识 API 分页、索引状态、metadata/config/count readback fixtures。
- [ ] 扩展 outcome/manifest/view fixtures，冻结 backend provenance 迁移合同。
- [ ] 建立显式 Phase 08 cloud 与 Edge runner/evidence namespace。

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

## Validation Sign-Off

- [x] 六个 Phase 08 requirements 均有自动化验收路径
- [x] 所有计划任务必须带 focused verify，且每个 wave 有离线回归
- [x] Wave 0 覆盖当前缺失合同和 command-safety 红灯
- [x] 云端调用被隔离为显式 marker，默认测试无隐式网络
- [x] 威胁模型覆盖 origin、重复调用、TOCTOU、注入、泄漏、DoS 和知识同步
- [x] 媒体、课程截图、PPTX、MP4、SRT 在 Phase 08 全程冻结

**Approval:** approved 2026-08-10
