# Phase 3: 可追溯诊断工作流 - Research

**Researched:** 2026-07-12  
**Mode:** ecosystem / implementation  
**Scope:** `INP-02`、`INP-03`、`SAFE-04`、`DIAG-01`～`DIAG-06`  
**Planning question:** 为了把 Phase 3 规划好，我们还需要知道什么？

## Executive Summary

Phase 3 不应被规划成“一次 Dify 调用返回最终 JSON”，而应规划成一个由本地 Python 裁决的、可停顿和可重跑的领域工作流：

```text
ApprovedRedactedInput
  -> candidate extraction (text/OCR/VLM)
  -> local normalization + privacy rescan
  -> CaseFacts revision
  -> deterministic sufficiency assessment
  -> deterministic-first routing
  -> validated RetrievalTrace
  -> candidate diagnosis generation
  -> local semantic + schema + safety validation
  -> at most one controlled repair
  -> DiagnosisRecord v1.x or explicit typed failure
```

当前代码已经有可靠的 Phase 2 边界：`ApprovedRedactedInput`、带 bbox/score 的 `OcrToken`、只含摘要的 `RetrievalTrace`、可信 knowledge build ID、严格 Pydantic 模型、fixture/Dify 适配器和 fail-closed evidence bundle。Phase 3 的主要工作不是换库，而是补齐四类领域合同：

1. `ExtractionRecord` / `CaseFacts` / `CorrectionOverlay`，使每个关键字段有稳定 ID、来源、定位、置信度和修订历史；
2. `SufficiencyAssessment` / `RoutingDecision`，使最多三问、一次补充、`unknown` 和 `insufficient_information` 都是确定性状态；
3. `DiagnosisRecord 1.1.0`（仍属 v1 major）的显式 `fact_id + evidence_id` 支持链接，替代当前基于相似文字的暗示性关联；
4. `DiagnosisRunOutcome` 与原始候选端口，使本地编排器而不是 Dify adapter 负责首次校验、一次受控修复和最终发布裁决。

**建议拆成 4 个计划：** 先迁移合同；再做抽取/纠错；再做充分性/路由/检索绑定；最后做生成、一次修复、evidence、CLI 与端到端回放。云端实测保持独立 marker 和外部门禁，不阻塞默认离线验收。

## Standard Stack

不引入新的运行时框架。沿用当前已锁定的栈：

| Concern | Use | Why |
|---|---|---|
| 严格领域合同 | Pydantic `2.13.4`，`ConfigDict(strict=True, extra="forbid")`，after validators | 当前项目已形成模式；支持字段、跨字段和判别联合约束 |
| 外部 JSON 再验证 | `model_validate_json(..., strict=True)`；公共边界先 dump/revalidate | 阻止隐式类型转换、`model_copy` 和多余字段绕过 |
| Schema 快照 | `model_json_schema()` + 提交的 JSON Schema + SHA-256 | Git 中的合同是事实源，Dify UI 只是副本 |
| OCR | 既有 `OcrBackend` / `OcrToken`；RapidOCR 只作本地候选源 | 已提供 bbox 与 score，足以支持来源定位和置信度 |
| 云调用 | 既有 HTTPX Dify adapter，但改为返回不可信候选 envelope | 适配器只处理 transport/platform shape，不做领域裁决 |
| 检索 | 既有 `RetrievalTrace`、可信 build identity、summary-only hit | 可直接生成稳定 `evidence_id` 并校验 locator/source/build |
| Evidence | 既有 `EvidenceBundle` 原子写入、输出复扫、失败 bundle | 复用已有 fail-closed 发布边界，不另造日志系统 |
| 离线测试 | pytest + fixture backend + versioned JSON fixtures | 默认 279 项测试已经完全离线，可延续相同模式 |

Pydantic 官方说明默认会进行类型转换，严格模式才会拒绝错误类型；JSON 输入在少数标准类型上仍可能比 Python 输入宽松。因此模型级 strict 之外，关键数值/ID 继续使用严格字段，并在公共边界显式 `strict=True`。复杂完整性约束使用 after model validators；不要用会提前终止内部校验的 plain validators。参考：[Pydantic strict mode](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/)、[Pydantic validators](https://pydantic.dev/docs/validation/latest/concepts/validators/)。

Dify 官方 LLM 节点支持 JSON Schema 结构化输出，但也明确说明：非原生 JSON 模型只是把 Schema 放入提示词，结果可能变化。因此 Dify structured output 是提高首轮通过率的生成约束，不是本地合同校验的替代品。参考：[Dify LLM structured outputs](https://docs.dify.ai/en/cloud/use-dify/nodes/llm#structured-outputs)。

## Architecture Patterns

### Pattern 1: 候选、事实、推断、发布记录四层分离

必须保持四个不同信任等级：

- **Candidate:** OCR/VLM/LLM 原始候选，只能停留在内存或私有调试边界，不可直接进入 evidence。
- **Fact draft:** 经过本地规范化、类型检查、定位检查和隐私复扫的候选事实。
- **CaseFacts revision:** 用户确认/纠错后的不可变事实快照，带 `revision` 与 `facts_sha256`。
- **DiagnosisRecord:** 只读取已确认事实、已验证 retrieval anchors 和本地规则；是 Phase 4 唯一允许消费的结果。

推荐领域模型（名称可在规划时微调，但语义不可合并）：

```text
SourceKind = text | ocr | vlm | user
FactField = exception_type | traceback_key_line | package | version | device | path
FactCandidate(candidate_id, field_id, value, source_kind, confidence, locator)
ExtractionRecord(case_id, extraction_id, candidates, source_hashes)
CorrectionOverlay(case_id, base_revision, field_id, old_value_sha256, replacement, reason)
CaseFact(fact_id, field_id, value, provenance[], confidence, status)
CaseFacts(case_id, revision, facts_sha256, facts[], applied_corrections[])
```

`locator` 应为判别联合：文本使用字段名 + 字符跨度/行号；OCR/VLM 使用经过验证图片的 SHA-256 + 四点 bbox；用户 correction 使用 overlay/revision 定位。路径内容已经脱敏，locator 不得保留原始未脱敏文本。

稳定 ID 应由规范化后的非敏感内容和来源定位作 canonical JSON hash 派生，而不是数组下标。纠错后同一 `case_id` 不变，但新建 revision、facts hash、run ID 和 diagnosis；旧记录不可原地改写。

### Pattern 2: 充分性是有限状态机，不是自由追问

建立按六类错误维护的确定性矩阵：每个类别声明 `required`、`high_value`、`optional` 字段以及问题模板。矩阵输入只读 `CaseFacts` 与已问字段集合，输出：

```text
ready
needs_information (questions <= 3, followup_round = 0)
insufficient_information (followup_round >= 1 or no safe high-value question)
```

排序键固定为：能否改变类别路由 > 能否改变根因排序 > 能否改变安全检查 > 字段稳定 ID。每个问题必须包含 `question_id`、目标 `field_id`、预期格式、为什么需要；去重依据是字段 ID 而非自然语言文本。最多允许一轮补充，同一缺失字段不得重复询问。

不要让 `insufficient_information` 伪装成一个低质量 `DiagnosisRecord`。使用判别联合 `DiagnosisRunOutcome`：

- `completed` -> `DiagnosisRecord`
- `needs_information` -> questions + known facts
- `insufficient_information` -> known facts + missing fields + safe checks
- `generation_failed` -> safe error code + completed stages + retry scope

这样 Phase 4 能展示部分结果，Phase 5 也能独立计算信息不足成功率。

### Pattern 3: 确定性优先的六类路由

路由必须是有解释的纯函数：

1. 对标准异常名、Traceback 关键短语、包/设备字段运行有版本号的规则集；
2. 每条规则产生 `rule_id`、category、matched fact IDs、score；
3. 单一强规则可确定类别；冲突、无命中或低于阈值时返回 `unknown`；
4. 模型只可提供候选类别和理由，不能覆盖本地冲突/阈值规则；
5. `RoutingDecision` 保存规则版本、候选分数、命中 fact IDs 和最终理由。

首版不要追求复杂分类器。六类课程错误都有高信号异常/短语，规则表更易形成可复现 fixture。`unknown` 是正确的安全结果，不是覆盖率失败。

### Pattern 4: RetrievalTrace 转换为显式 evidence anchors

当前 `RetrievalTrace` 已校验：`case_id`、query hash、knowledge build ID、source ID、HTTPS URL、locator 和 summary。Phase 3 应增加一个纯转换/验证层，生成稳定 `EvidenceAnchor`：

```text
evidence_id = sha256(knowledge_build_id, chunk_id, source_id, locator)
EvidenceAnchor(evidence_id, chunk_id, content_summary, source_id, source_url,
               locator, relevance_score, knowledge_build_id)
SupportLink(fact_ids[1..], evidence_ids[1..], support_type)
```

每个 `RootCauseCandidate` 必须有稳定 `candidate_id`、至少一个 fact ID，以及：

- 若声明为 `grounded`，至少一个已验证 evidence ID；
- 若没有引用支持，只能是 `inference`，并带 `applicability`、`counterevidence_or_limits`；
- support link 指向的 ID 必须存在且 case/build 一致；
- 引用只保存命中摘要，不保存完整 raw chunk。

当前 `DiagnosisRecord 1.0.0` 的 `observed_facts: list[str]`、`supporting_facts: list[str]` 与独立 `citations` 不能表达这种关系，必须先迁移合同。

### Pattern 5: 同一 major 内的显式合同迁移

建议将 `schema_version` 从 `1.0.0` 升到 `1.1.0`，仍称 `DiagnosisRecord v1`。不要悄悄改变 `1.0.0` Schema。迁移计划至少包括：

1. 保留 `DiagnosisRecordV100` loader 和冻结的旧 schema/hash；
2. 新增 `DiagnosisRecord` 1.1.0 或明确命名 `DiagnosisRecordV110`；
3. 实现单向纯函数 `migrate_v100_to_v110()`，旧字符串事实生成稳定 fact IDs；旧 citation 生成 anchor IDs；无法证明绑定的旧根因必须标为 inference，而不是猜测 support link；
4. Schema 文件同时存在或在 `contracts/migrations/` 记录版本；
5. 所有 fixture 显式更新版本，增加迁移 golden test、幂等测试、旧 Schema 拒绝新字段测试；
6. Phase 4 只接受当前 1.1.0，不在渲染层兼容多个版本。

新增字段至少应覆盖：事实 ID、evidence ID、support links、根因类型（grounded/inference）、适用条件、反证/局限。现有 `CommandStep` 已覆盖平台、影响、预期结果和回退，可保留但增加非空约束、确定性顺序和安全规则校验。

### Pattern 6: 适配器返回候选，本地 generator 裁决

当前 `DifyBackend.run_workflow()` 在 adapter 内直接解析为 `DiagnosisRecord`，第一次失败就抛 `DifyContractError`，因此无法：

- 生成只含错误路径的修复请求；
- 区分 transport failure、JSON parse failure、Schema failure 和语义/引用 failure；
- 保证恰好最多一次修复；
- 防止原始模型响应进入 evidence。

Phase 3 应把端口收窄为不可信候选 envelope，例如：

```text
CandidateRunResult(run_id, backend, candidate_payload)
GenerationRequest(case_facts, routing, retrieval_anchors, schema_version, attempt)
```

adapter 只负责上传、调用、提取公开 output 字段和安全错误分类。领域 `DiagnosisGenerator` 负责：

1. 首次候选严格验证；
2. 运行跨字段语义、引用、case ID、command safety 和输出隐私验证；
3. 收集 bounded validation issues（JSON pointer、错误码，不含原始响应/敏感值）；
4. 仅在可修复合同错误时发起一次 repair，repair 输入只含 Schema 版本、错误路径/代码和脱敏候选；
5. 第二次失败返回 `generation_failed`，绝不拼接自由文本或部分伪对象。

transport 的一次网络重试与 DIAG-05 的一次结构修复是两个不同预算，必须分别计数。不要让 Dify 节点自身无限 retry；计划中固定 `generation_attempts <= 2`。

### Pattern 7: 一个本地 orchestrator 管理可停顿工作流

新增领域服务（例如 `DiagnosisWorkflow`），由它依次调用 extractor、sufficiency policy、router、retriever、generator 和 evidence writer。`CloudGateway` 继续只接受 `ApprovedRedactedInput`，但不应承载分类/充分性/引用绑定逻辑。

建议工作流阶段名固定并进入 outcome/evidence：

```text
input_approved -> extracted -> facts_confirmed -> sufficiency_checked
-> routed -> retrieved -> generated -> validated -> published
```

纠错重跑从 `facts_confirmed` 创建新 revision 后重新执行 sufficiency 之后的阶段；若 correction 改变候选事实，则 extraction 原记录保留。所有 expensive/cloud 阶段使用 facts hash + route rules version + knowledge build ID + schema version 构造幂等键。

## Security Threat Model

### Assets and trust boundaries

| Asset | Threat | Required control |
|---|---|---|
| 已脱敏文本/截图 | 隐藏/间接提示注入 | 候选数据与指令分离；外部内容不能选择工具、Schema 或工作流状态 |
| OCR/VLM 候选 | 伪字段、越界 bbox、低置信误读 | 本地类型/locator 校验、图像 hash 绑定、隐私复扫、用户 correction |
| Retrieval summary | 污染知识诱导命令或结论 | 只接受可信 build ID 和已发布 locator；summary 仍视为不可信数据 |
| 模型诊断 JSON | 多余字段、类型转换、伪引用、命令注入 | strict Pydantic + `extra=forbid` + support-link 完整性 + command policy |
| 修复循环 | 无限重试、费用放大、候选泄漏 | 最多一次 repair；错误信息 bounded；原始 body 不写日志/evidence |
| 命令建议 | 自动执行、破坏性操作、平台错配 | 系统无 execution port；CommandStep 只作数据；平台/影响/预期/回退必填 |
| 纠错 overlay | 并发覆盖、篡改历史、注入敏感值 | base revision/hash 乐观锁；新 revision；replacement 再脱敏/校验 |

OWASP 明确指出 RAG 和微调不能消除 prompt injection，并建议隔离不可信内容、确定性验证输出、最小权限和高风险动作人工批准；对多模态还要考虑图像内隐藏指令。[OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)。本阶段最有效的控制不是“再写一句忽略恶意指令”，而是模型没有任何执行工具、本地状态机不接受自然语言改变路由/重试预算、所有输出都经过合同与安全策略。

OWASP 对 improper output handling 和 excessive agency 的建议也支持当前边界：LLM 输出必须在下游消费前验证，授权不能委托给模型。[OWASP LLM05:2025](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/)、[OWASP LLM06:2025](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)。

### Required adversarial fixtures

- OCR 文本中出现 “ignore previous instructions / execute command”；不得改变字段集合、路由规则或触发工具。
- retrieval summary 中出现伪 system instruction；只作为引用数据，不能提升置信度或产生未绑定命令。
- model 输出伪造 source ID/locator/build ID；本地拒绝且一次 repair 后仍不可信。
- command 中出现链式删除、下载执行、shell substitution、未标平台或空 rollback；拒绝整个 diagnosis，不做局部发布。
- correction overlay 含邮箱/token/绝对私人路径；在新 revision 创建前被输出扫描阻断。
- repair 返回新增未声明字段、字符串 confidence 或不同 case ID；第二次失败形成 typed failure bundle。

## Don't Hand-Roll

- 不自建向量数据库、embedding/reranker；使用已完成的 knowledge build + `RetrievalTrace`。
- 不自建 JSON parser/schema engine；用 Pydantic 和已安装的 `jsonschema` 做合同与快照交叉验证。
- 不用正则解析任意 JSON 或从 Markdown code fence 猜测最终对象；候选必须是 JSON value，最多做一次明确的外层 fence/字符串解包规范化，且规范化行为有测试。
- 不把充分性、路由或安全规则塞进 prompt；它们是版本化 Python 数据/纯函数。
- 不让 Dify adapter 保存业务规则或直接发布 `DiagnosisRecord`。
- 不设计 Gradio 字段编辑器、报告、PNG、MP3；Phase 3 只提供 JSON/CLI/API 纠错与重跑边界。
- 不执行任何诊断命令，不引入 subprocess/shell execution port。
- 不保存完整 raw chunk、原始模型 body、模型 reasoning 或敏感 validation input 到 evidence。

## Common Pitfalls

### 1. 只扩展 Schema，不增加跨引用验证

`additionalProperties: false` 只能拒绝未知字段，不能证明 support link 指向存在的 fact/evidence。必须用 model-level validators 验证 ID 唯一性、引用存在性、case/build 一致性、grounded/inference 规则。JSON Schema 默认允许额外字段，必须继续显式禁用。[JSON Schema additional properties](https://tour.json-schema.org/content/03-Objects/02-Additional-Properties)。

### 2. 在 adapter 里捕获所有异常

当前 Dify adapter 的宽泛 `except Exception` 会把 JSON、Schema 和代码 bug 都折叠成同一种 contract error。规划时应只捕获预期的 JSON/Pydantic/key errors，领域验证错误由 generator 结构化保存；程序错误不得伪装成模型失败。

### 3. 把 OCR confidence 当事实 confidence

OCR score 只表示识别置信度，不等于异常分类或根因置信度。分别保存 extraction、routing、diagnosis confidence；不要用一个百分比覆盖三层。

### 4. 字符串相等充当证据绑定

当前 `supporting_facts: list[str]` 容易因纠错、标点、翻译漂移而失效。所有绑定使用稳定 ID，展示文本只是派生视图。

### 5. 信息不足仍强行生成 DiagnosisRecord

这会让“未知”和“信息不足”混淆，并诱发根因编造。工作流必须在 generation 前停下，返回 typed outcome。

### 6. 重跑覆盖原证据

纠错后必须新 run/new facts hash/new diagnosis ID 或 diagnosis hash；同 case 保留 revision lineage。不能原地改写 evidence bundle。

### 7. 将平台 structured output 视为保证

Dify 本身说明非原生 JSON 模型的结构化结果可能变化。即使平台显示成功，本地仍执行同一验证和一次 repair 预算。

### 8. 默认离线 fixture 冒充真实 VLM/Dify

fixture run 必须标 `backend=fixture/offline_fixture`；cloud/ocr tests 保持 marker 隔离。真实 Dify 的模型、知识引用映射和结构化稳定性是 external gate，不得由 MockTransport 结论替代。

## Code Examples

以下是规划级伪代码，展示边界而不是实现细节：

```python
class DiagnosisRunOutcome(StrictRecord):
    # Prefer a discriminated union of completed / needs_information /
    # insufficient_information / generation_failed concrete models.
    status: Literal[...]


def generate_with_one_repair(request, backend):
    first = backend.generate_candidate(request)
    first_result = validate_candidate(first, request)
    if first_result.ok:
        return first_result.record
    if not first_result.repairable:
        return generation_failed(first_result.safe_issues)

    repair = backend.generate_candidate(
        request.for_repair(first_result.safe_issues, first.safe_payload)
    )
    second_result = validate_candidate(repair, request)
    return second_result.record if second_result.ok else generation_failed(
        second_result.safe_issues
    )
```

```python
@model_validator(mode="after")
def validate_support_graph(self):
    fact_ids = {fact.fact_id for fact in self.observed_facts}
    evidence_ids = {item.evidence_id for item in self.evidence}
    for candidate in self.root_cause_candidates:
        # require unique IDs, existing targets, and evidence for grounded claims
        ...
    return self
```

```python
def assess_sufficiency(facts, asked_field_ids, followup_round):
    missing = matrix.for_route(facts.route_hint).missing(facts)
    ranked = deterministic_rank(missing)
    if not ranked:
        return Ready(...)
    if followup_round == 0:
        return NeedsInformation(questions=templates.for_fields(ranked[:3]))
    return InsufficientInformation(missing_field_ids=ranked, safe_checks=[...])
```

## Nyquist Validation Architecture

验证应与实现任务同计划交付，不把所有测试推到 Phase 5。每项产品行为至少有一个低层合同测试和一个跨边界测试；关键风险在相邻层重复验证，以便定位故障。

### Validation layers

| Layer | Test target | Key assertions |
|---|---|---|
| L1 Contract | Pydantic + JSON Schema | strict types、extra forbid、非空字段、ID 唯一、support graph、version const |
| L2 Pure policy | normalization/sufficiency/router/safety | deterministic ordering、<=3 questions、one round、six categories + unknown、deny unsafe commands |
| L3 Port contract | fixture and Dify MockTransport | same candidate envelope、safe error classes、no response body leakage、upload hash binding |
| L4 Workflow integration | `ApprovedRedactedInput` -> outcome | stage transitions、retrieval build binding、one repair、correction revision/new run |
| L5 Evidence | EvidenceBundle | summary-only、privacy rescan、typed failure、atomicity、manifest hashes/backend labels |
| L6 External smoke | real OCR/Dify, marker-isolated | screenshot extraction quality、model structured output、real citation mapping、run ID |

### Requirement-to-test map

| Requirement | Minimum automated proof |
|---|---|
| INP-02 | text + OCR tokens -> six field types with source/bbox/confidence; low-confidence/malformed locator rejected |
| INP-03 | per-category matrices; 0/1/3/4 missing fields; no duplicate question; second round -> insufficient |
| SAFE-04 | every check/fix/verify command has five required fields; execution capability absent; malicious command fixtures rejected |
| DIAG-01 | one fixture per six category + ambiguous/conflict/no-hit -> unknown; route explains fact/rule IDs |
| DIAG-02 | completed workflow validates against Pydantic and committed JSON Schema; schema hash snapshot matches |
| DIAG-03 | missing/dangling/wrong-build support links rejected; unsupported candidate forced to inference |
| DIAG-04 | root causes/checks/fixes/verification/missing/confidence/limits/environment all required and semantically non-empty |
| DIAG-05 | valid first attempt = 1 call; invalid then valid = 2; invalid twice = typed failure; transport retries counted separately |
| DIAG-06 | correction preserves original candidate, increments revision, changes facts hash/run ID, reroutes/retrieves/regenerates |

### Fixture matrix

至少提交以下固定案例：

- `module_not_found` -> dependency/environment（主 demo）
- `path_permission_windows`
- `python_runtime_traceback`
- `tensor_shape_dtype`
- `cuda_oom`
- `model_loading`
- `unknown_conflicting_signals`
- `insufficient_then_answered`
- `insufficient_after_one_round`
- `ocr_misread_corrected`
- `citation_missing_or_forged`
- `schema_invalid_then_repaired`
- `schema_invalid_twice`
- `prompt_injection_in_screenshot`
- `unsafe_command_candidate`

每个 fixture 的输入、事实、route、retrieval trace、候选输出和期望 outcome 分开保存，避免把同一完整 golden JSON 同时当输入和答案。六类异常可复用 Phase 2 `knowledge/eval_queries.json` 的类别与 anchor，但诊断 fixture 应拥有独立 case IDs，防止评测资产与实现 fixture 耦合。

### Verification commands expected by plans

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not cloud and not ocr"
.\.venv\Scripts\python.exe -m pytest -q tests\diagnosis
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m jsonschema -i <fixture> contracts\diagnosis-record-v1.1.schema.json
git diff --check
```

真实 OCR 与 Dify smoke 必须分别使用 `-m ocr`、`-m cloud`，报告 backend、知识 build ID、prompt/schema version 和外部门禁；无凭据时默认套件仍须完全通过。

## Proposed Plan Decomposition

### Plan 03-01 — Contract migration and trace graph

- 新增 extraction/facts/correction/sufficiency/routing/outcome contracts。
- 将 DiagnosisRecord 1.0.0 迁移到 1.1.0，加入 stable IDs、evidence anchors、support links、grounded/inference semantics。
- 更新 committed schemas、hash snapshots、migration fixtures 和 contract tests。
- 先完成这一计划，后续计划才能基于稳定 API 工作。

### Plan 03-02 — Extraction, normalization and correction replay

- 从已脱敏 text + `OcrToken` 提取候选；VLM 为可选 backend candidate source。
- 本地规范化、隐私复扫、locator/bbox 校验，生成 `CaseFacts`。
- 实现 correction overlay、revision lineage、facts hash 和 JSON/CLI correction/replay seam。
- 不实现 Phase 4 可视化编辑器。

### Plan 03-03 — Sufficiency, deterministic routing and evidence binding

- 六类充分性矩阵、问题模板、最多三问/一轮状态机。
- 版本化规则 router，覆盖六类 + unknown/conflict。
- 复用可信 `RetrievalTrace`，构造/校验 evidence anchors 和 support graph 输入。
- 信息不足必须在 generation 前结束。

### Plan 03-04 — Candidate generation, one repair and end-to-end evidence

- 重构 backend port 为 raw candidate envelope，fixture/Dify 同合同。
- 本地 generator 完成 strict + semantic + citation + privacy + command safety validation。
- 实现最多一次 repair 与 typed failure；区分 transport retry。
- 写入原子 evidence、CLI/API 入口、完整 fixture replay 和 marker-isolated cloud smoke。

## Open Questions / External Gates

这些问题不应阻塞离线规划，但必须在 Phase 3 验证报告中如实标注：

1. 当前 Dify 账号所选模型是否原生支持 JSON Schema，还是仅 prompt-assisted structured output？
2. Dify workflow 实际输出能否稳定回传知识命中 chunk/source/locator，如何映射到 Phase 2 `RetrievalTrace`？
3. 真实 VLM 对 10 张终端截图的字段准确率和 bbox/来源能力如何？若只返回文本，则 bbox 以本地 OCR 为准，VLM 只作候选补充。
4. Dify 自身 node retry 设置是否能固定为 0/1 并从运行 metadata 观察？否则本地 “一次 repair” 计数可能与平台隐藏重试混淆。
5. 当前 Dify dataset 写入/回读仍是凭据门禁；真实 cloud evidence 不得由 offline retrieval 或 MockTransport 代替。

## Confidence Assessment

| Finding | Confidence | Basis |
|---|---|---|
| 本地 orchestrator 必须拥有最终裁决 | HIGH | 项目既有架构、Phase 2 trust boundary、OWASP output validation |
| DiagnosisRecord 需要 1.1.0 trace graph migration | HIGH | 当前 Schema 无法表达 DIAG-03；可由合同测试直接证明 |
| 充分性/路由应为确定性矩阵和规则 | HIGH | 已锁定六类范围、一次追问边界和短周期约束 |
| 适配器应返回候选而非最终 DiagnosisRecord | HIGH | 当前 adapter 无法实现一次 repair 与错误分类 |
| Dify structured output 可提高首轮通过率 | MEDIUM-HIGH | 官方支持，但可靠性依赖具体模型 |
| Dify 能提供满足本项目的 citation mapping | MEDIUM | 官方支持 RAG 来源，但账号、工作流和返回字段需现场验证 |
| VLM 可稳定提供所有字段及定位 | MEDIUM-LOW | 依赖具体模型；本地 OCR + 用户 correction 必须是可靠主边界 |

## Sources

- [Pydantic strict mode](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/) — 默认转换与 strict validation 的边界。
- [Pydantic validators](https://pydantic.dev/docs/validation/latest/concepts/validators/) — field/model validators 与 plain validator 风险。
- [Dify LLM node](https://docs.dify.ai/en/cloud/use-dify/nodes/llm) — structured outputs、JSON Schema、vision 和 retry；非原生 JSON 模型结果可能变化。
- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — RAG 不能消除注入；隔离、输出验证、最小权限和人工批准。
- [OWASP LLM05:2025 Improper Output Handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/) — 模型输出进入下游前必须校验与清理。
- [OWASP LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) — 功能、权限和自治最小化；授权由下游代码执行。
- [JSON Schema additional properties](https://tour.json-schema.org/content/03-Objects/02-Additional-Properties) — 显式拒绝未声明字段。

---

*Research complete. Ready for `/gsd-plan-phase 3`.*
