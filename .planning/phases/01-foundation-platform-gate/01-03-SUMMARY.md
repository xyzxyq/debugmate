---
phase: 01-foundation-platform-gate
plan: 03
status: complete
requirements_completed: [EVID-01, EVID-02]
completed_at: 2026-07-10
external_setup_remaining: true
---

# Plan 01-03 Summary: Dify 适配层与七能力探针

## Outcome

仓库现在具有可离线测试的 Dify HTTP 适配层、fixture/cloud 分离的七能力探针、Windows 一键脚本、确定性契约 Schema 与平台重建文档。没有 Dify 凭据时会明确记录 `blocked`/`not-tested`，不会把 fixture 成功冒充云端通过。

## Delivered

- 集中 Authorization 构造的 Dify adapter；401/403/429 不重试，连接/超时最多重试一次。
- Workflow 响应严格通过 `DiagnosisRecord`；TTS 字节必须符合 MP3 文件头。
- `fixture-probe`、`cloud-probe`、`verify-bundle`、`export-schema` CLI。
- C01–C07 固定矩阵，`pass` 必须同时具有相对 evidence path 与 SHA-256。
- PowerShell 脚本使用 `$PSScriptRoot`、`-LiteralPath`，无密钥时不发起云请求。
- Dify 设置顺序、4 小时闸门、不得充值、真实 DSL 重导入证据要求。
- 独立的 `DiagnosisRecord` Schema 与知识来源 manifest Schema。

## TDD and debugging evidence

- Dify adapter RED：缺少 `debugmate.adapters.dify`。
- Probe/CLI RED：缺少 `debugmate.cli`。
- 文档/Schema RED：目标文件不存在。
- 失败云探针回归：先复现 failed manifest 缺少 error 字段，再修复为可验证失败 bundle。
- Windows 中文路径回归：定位 PowerShell 对原始 Unicode stdout 的代码页破坏，改为 ASCII JSON 转义后真实 round-trip 验证通过。

## Verification

- `63 passed`，Ruff 全部通过。
- 无 Dify 密钥时 `run_phase1_probe.ps1` 退出 0，7 项为 `not-tested`。
- 最终 fixture bundle：`verify-bundle` 返回 `{"issues": [], "ok": true}`。
- tracked product secret scan clean；`Bearer` 构造只存在于 `DifyBackend._headers()`。
- Schema 连续导出 SHA-256 一致。

## Commits

- `4300531 feat(01-03): add safe Dify adapter`
- `6efbb69 feat(01-03): add capability probe CLI`
- `ab73795 docs(01-03): add Dify reconstruction assets`
- `3c8fb71 fix(01-03): publish failed probe evidence`
- `16d6eae fix(01-03): escape CLI paths for PowerShell`
- `a49f71d fix(01-03): bind capability passes to artifacts`

## External limitation

当前线程没有用户 Dify 登录态或密钥，因此 C01–C07 的真实云端证据仍待 `01-USER-SETUP.md` 所列步骤完成。该限制不影响离线工程合同，但 Phase 1 云能力闸门不能标记为全量通过。
