---
phase: 01-foundation-platform-gate
plan: 01
status: complete
requirements_completed: [INP-04, EVID-02]
completed_at: 2026-07-10
---

# Plan 01-01 Summary: 工程骨架、诊断契约与离线后端

## Outcome

建立了可安装的 Python 3.13 `src` 工程，冻结 `DiagnosisRecord v1`，并提供明确标记为 fixture 的可复现离线诊断后端。fixture 不能生成云端能力通过结果，也不执行任何修复命令。

## Delivered

- Python 3.13 项目、锁定依赖、Ruff/pytest 配置与安全忽略规则。
- 严格 Pydantic v2 诊断契约、`case_<uuid4 hex>`、生成式 JSON Schema 与确定性 Schema SHA-256。
- 平台无关 `DiagnosisBackend` Protocol 和结果类型。
- 虚构 `ModuleNotFoundError` 输入/诊断 fixture；仅替换调用方 `case_id` 后重新通过契约验证。
- C01–C07 fixture 能力状态全部为 `not-tested`，TTS 明确不可用。

## TDD evidence

- Contract RED: `ModuleNotFoundError: No module named 'debugmate.contracts'`.
- Fixture RED: `ModuleNotFoundError: No module named 'debugmate.adapters.base'`.
- GREEN: `27 passed`; Ruff: `All checks passed!`.

## Commits

- `deecfcc chore(01-01): scaffold Python project`
- `a874d4f feat(01-01): define diagnosis contract`
- `0f97807 feat(01-01): add deterministic fixture backend`

## Deviations

实现代理连续两次在无文件、无提交、无报告状态下超时，按 GSD runtime fallback 改为顺序内联执行。Task 1 独立审查通过；Task 2/3 的审查代理超时后，由控制器针对提交区间重新执行规格与运行时门检，未把代理超时计为通过证据。

## Verification

```text
27 passed in 0.12s
All checks passed!
fixture-runtime-ok fixture:module_not_found
No sensitive source/fixture patterns.
```

## Next dependency

Plan 01-02 可基于 `DiagnosisRecord` 与 `case_id` 构建原子、可重算哈希的 evidence bundle。
