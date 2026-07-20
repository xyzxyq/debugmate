---
phase: 01-foundation-platform-gate
plan: 02
status: complete
requirements_completed: [EVID-01, EVID-02]
completed_at: 2026-07-10
---

# Plan 01-02 Summary: 安全设置与原子证据链

## Outcome

DebugMate 现在可以把一次运行发布为与 `case_id` 绑定、可重算 SHA-256、可发现篡改且不会把半成品伪装成成功结果的 evidence bundle。

## Delivered

- UTF-8/排序键/紧凑分隔符的 canonical JSON 与 SHA-256 工具。
- 相对 POSIX 路径、`..`、绝对路径和符号链接逃逸防护。
- `SecretStr` 云端设置、安全摘要和只返回字段路径的密钥泄漏检测器。
- 严格 `ArtifactEntry`、`CapabilityEvidence`、`RunManifest` 与状态合同。
- `.tmp-<case_id>` 写入、`manifest.json` 最后写入、目录原子发布。
- 失败 manifest、产物复算、漏列文件/缺失文件/篡改/case 目录不一致检查。
- 运行 evidence 默认忽略，仅跟踪 `evidence/.gitkeep`。

## TDD evidence

- Hash/settings RED: `No module named 'debugmate.hashing'`.
- Evidence RED: `No module named 'debugmate.evidence'`.
- GREEN: `44 passed`; Ruff: `All checks passed!`.
- 独立运行时篡改复核：原始 bundle 验证通过，单字节修改后验证失败。

## Commits

- `1a7b556 feat(01-02): add hashing and safe settings`
- `066cac5 feat(01-02): add atomic evidence bundles`

## Review note

两次独立审查代理均在无结果状态下超时并被中止；控制器针对提交重新运行了测试、Ruff、敏感序列化检查和真实单字节篡改检查。代理超时未被记录为审查通过证据。

## Next dependency

Plan 01-03 可直接将 fixture/Dify 七能力探针结果写入同一 bundle，并要求每个 `pass` 都带 evidence path 与 SHA-256。
