# Phase 09: Current Evaluation Evidence - Research

**Researched:** 2026-08-10  
**Domain:** 可复算代表案例、同案例提示词证据、课程素材来源账本与隐私/一致性门禁  
**Confidence:** HIGH（仓库结构、现有合同与阶段边界）；MEDIUM（真实 Dify live 可用性，因 Phase 08 Plan 07 尚未完成） `[VERIFIED: repository inspection; .planning/phases/08-dify-unified-live-chain/08-07-PLAN.md]`

## User Constraints

### Locked Decisions

- 3–5 current cases.
- Exact same sanitized case for V1–V4.
- Include live success, insufficient data, long content, privacy, fallback/failure.
- Bind current evidence/citations/three modalities/privacy/limitations.
- Media/PPTX/video/subtitles/final screenshots strictly frozen until Phase 10.
- Phase 9 depends on Phase 8 and must not claim current live pass until 08-07 evidence exists.

### Claude's Discretion

- Exact evaluation directory layout, strict model names, report filenames and deterministic ID derivation.
- How the 3–5-case limit is allocated, provided every locked coverage dimension is explicit.
- Whether a prompt version is represented by a fresh candidate generation or by honest contract verification against the same fixed output, provided provenance never conflates the two.

### Deferred Ideas (OUT OF SCOPE)

- Final screenshots, PPTX, narration, AI voice-over, subtitles, MP4 and final media manifests belong to Phase 10.
- Production-scale statistics, significance tests, cost baselines, exhaustive visual certification and public deployment remain outside V0.1.

## Summary

Phase 09 should be planned as an evidence compilation and verification layer over the current Phase 08/Phase 04 contracts, not as another diagnosis pipeline. The repository already has strict diagnosis evidence, result-manifest, ZIP, privacy-scan, citation-binding and execution-backend contracts; what is missing is one small versioned evaluation registry that references those verified objects and produces current case and prompt-comparison summaries. `[VERIFIED: src/debugmate/evidence.py; src/debugmate/results/contracts.py; src/debugmate/results/verifier.py; src/debugmate/privacy/output_scan.py; src/debugmate/diagnosis/evidence_binding.py]`

The correct minimum set is four evaluation rows: (1) the Phase 08 synthetic-but-real Dify success, also carrying privacy coverage; (2) deterministic insufficient-information; (3) deterministic long-content replay; and (4) the deterministic `local_fallback` partial audio-unavailable terminal row. This covers all locked dimensions without exceeding the 3–5-case V0.1 limit. `[VERIFIED: .planning/ROADMAP.md; tests/fixtures/diagnosis/workflow_cases.json; fixtures/replay/index.json; src/debugmate/results/contracts.py; tests/results/test_result_e2e.py]`

The live row is currently blocked: `.planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md` and `evidence/dify-live/phase8/manifest.json` do not exist, and `DIFY_DATASET_API_KEY` is absent from the current environment. Phase 09 planning and offline Wave 0 work may proceed, but the runner must fail closed rather than emit `live_pass=true`. `[VERIFIED: filesystem inspection 2026-08-10; value-free environment probe 2026-08-10; 08-07-PLAN.md]`

**Primary recommendation:** Build one strict `phase9-evaluation-1.0` source ledger that imports Phase 08 live evidence by hash, regenerates only the three current offline/failure cases, verifies V1–V4 against one immutable sanitized case identity, and emits Phase 10 input manifests without writing any final media. `[VERIFIED: roadmap boundary; existing evidence/result patterns]`

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| EVAL-01 | V0.1 保存 3–5 个可重复运行的代表性案例，覆盖完成、长内容、隐私/安全与平台降级状态。 `[VERIFIED: .planning/REQUIREMENTS.md]` | Use a four-row registry with explicit coverage tags, immutable input hashes, expected/actual status and a deterministic runner. `[VERIFIED: fixtures/replay/index.json; tests/fixtures/diagnosis/workflow_cases.json]` |
| EVAL-03 | 项目保存 V1–V4 提示词、修改目标、固定案例结论和采用/限制说明。 `[VERIFIED: .planning/REQUIREMENTS.md]` | Bind all four prompt file hashes to the same sanitized input/output identity; require each row's safe fixed-case conclusion, accepted diagnosis/result/candidate SHA-256, source-evidence reference, and `generated_live`/`verified_contract`/`rejected`/`blocked` provenance. `[VERIFIED: prompts/README.md; prompts/v1-baseline.md through prompts/v4-course-release.md]` |
| EVAL-05 | 进入 PPT 和视频的案例来自真实运行或明确标注的回放，并通过隐私、文件有效性与一致性代表性检查。 `[VERIFIED: .planning/REQUIREMENTS.md]` | Emit an eligibility ledger with execution backend, run/result hashes, privacy result, artifact validation and exclusion reasons; Phase 10 consumes only eligible rows. `[VERIFIED: src/debugmate/results/contracts.py; src/debugmate/results/verifier.py]` |
| EVID-03 | 项目可以从真实运行证据自动生成提示词对比表、案例卡、工作流图和 PPT 素材清单。 `[VERIFIED: .planning/REQUIREMENTS.md]` | Phase 09 should generate machine-readable prompt/case/workflow/source manifests and Markdown previews; Phase 10 alone renders/finalizes screenshots, PPTX and video assets. `[VERIFIED: .planning/ROADMAP.md Phase 9/10 boundary; scripts/build-course-ppt.py; scripts/build-course-video.py]` |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Treat `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` and `.planning/STATE.md` as source of truth; research does not authorize product implementation. `[VERIFIED: AGENTS.md]`
- All committed evidence and course inputs must be reproducible from repository sources; cloud screenshots are not the sole authority. `[VERIFIED: AGENTS.md project constraints]`
- Real evidence only: generated images may not impersonate runtime, evaluation or platform proof. `[VERIFIED: AGENTS.md project constraints]`
- Inputs and exports are private-by-default, using synthetic identities and redacted paths; secrets must never enter logs, evidence or course outputs. `[VERIFIED: AGENTS.md project constraints]`
- Prefer local/free tooling and obtain separate approval before any paid API or subscription. `[VERIFIED: AGENTS.md project constraints]`
- Windows paths and scripts use PowerShell-native handling, UTF-8 and `-LiteralPath`; the existing virtual environment is the authoritative Python runtime. `[VERIFIED: AGENTS.md; machine experience profile]`
- `CLAUDE.md` is absent and no `.claude/skills/` or `.agents/skills/` project skill directory exists, so there are no additional project-local directives to merge. `[VERIFIED: filesystem inspection 2026-08-10]`

## Current-State Findings

### Hard prerequisite

| Gate | Current state | Planning consequence |
|---|---|---|
| `08-07-SUMMARY.md` | Missing. `[VERIFIED: filesystem inspection]` | Phase 09 cannot treat Plan 08-07 as executed. |
| `evidence/dify-live/phase8/manifest.json` | Missing. `[VERIFIED: filesystem inspection]` | No row may be labelled current Dify live success. |
| `DIFY_DATASET_API_KEY` | Missing; other app configuration names are present without reading their values. `[VERIFIED: value-free environment probe]` | Phase 08 exact 17-source readback/final live acceptance remains blocked. |
| Phase 08 Plans 01–06 | Six summaries exist and report offline contracts/UI/result wiring complete. `[VERIFIED: 08-01-SUMMARY.md through 08-06-SUMMARY.md]` | Wave 0 can safely build evaluation contracts around the current interfaces. |

The Phase 09 runner should accept `--allow-missing-live` only for development/collection and must then produce overall status `blocked`, never `passed`; the phase gate must run without that switch. This is a recommendation derived from the locked no-false-live rule. `[VERIFIED: user constraint; 08-07-PLAN.md]`

### Existing assets to reuse

| Asset | What it already proves | Phase 09 use |
|---|---|---|
| `src/debugmate/evidence.py` | Strict run manifests, atomic evidence bundles, privacy-safe publication and bundle verification. `[VERIFIED: source inspection]` | Verify/import source run identity; do not invent a second run bundle format. |
| `src/debugmate/results/contracts.py` + `verifier.py` | Result identity, explicit execution backend, artifact availability, checksums, MP3/PNG/ZIP verification. `[VERIFIED: source inspection]` | Populate per-case modality validity and consistent hashes. |
| `src/debugmate/diagnosis/evidence_binding.py` | Facts and diagnosis citations bind to known evidence anchors. `[VERIFIED: source inspection]` | Calculate citation status from validated objects, not display text. |
| `src/debugmate/privacy/output_scan.py` | Export safety scan treats untrusted text as data and rejects sensitive content. `[VERIFIED: source inspection]` | Rescan every generated JSON/Markdown source artifact before promotion. |
| `fixtures/replay/module-not-found` and `long-content` | Deterministic verified replay source bundles and current result inputs. `[VERIFIED: fixtures/replay/index.json; scripts/generate-replay-fixture.py; scripts/generate-long-content-fixture.py]` | Regenerate long-content/replay rows under current contracts, with explicit `execution_backend=replay`. |
| `tests/fixtures/diagnosis/workflow_cases.json` | Includes `needs_information`, `insufficient_information` and `generation_failed` deterministic scenarios. `[VERIFIED: fixture inspection]` | Source the insufficient/failure rows without manual data collection. |
| `prompts/v1-baseline.md`–`v4-course-release.md` | Four versioned prompt designs and their stated modification goals. `[VERIFIED: prompt file inspection]` | Hash each file and build constraint/adoption evidence. |
| `docs/course/*`, `evidence/course-v0.1/*`, `deliverables/*` | Historical 2026-07-19 narrative, screenshots and media manifests. `[VERIFIED: manifest inspection]` | Read-only comparison/frozen baseline only; never use as current Phase 09 proof. |

The current ordinary Dify chain is hard-coded to `prompt_version="diagnosis-v1"`, and runtime authority hashes `prompts/v1-baseline.md`; it does not natively execute V2–V4 as separate product runs. `[VERIFIED: src/debugmate/cloud/workflow.py; src/debugmate/ui/serve.py; platform/dify/app.dsl.yml]`

Therefore, the prompt comparison must distinguish actual generation from contract verification. A V2–V4 row may say “verified against the same accepted output and declared constraints,” but must not say “generated by V2/V3/V4” unless an explicit evaluation-only provider run exists and is separately evidenced. `[VERIFIED: prompts/README.md authenticity statement; current runtime binding]`

## Standard Stack

No new runtime dependency is justified. Phase 09 is JSON/Markdown evidence assembly over already pinned project libraries. `[VERIFIED: pyproject.toml; repository architecture]`

### Core

| Library/tool | Version | Purpose | Why standard here |
|---|---:|---|---|
| CPython | 3.13.5 | Evaluation runner, hashing and deterministic JSON. | Matches the project runtime and current `.venv`. `[VERIFIED: local version probe; pyproject.toml]` |
| Pydantic | 2.13.4 | Strict frozen evaluation manifests with `extra='forbid'`. | Existing project-wide contract pattern. `[VERIFIED: pyproject.toml; src/debugmate/* contracts]` |
| pytest | 9.1.1 | Contract, integration and negative security tests. | Existing test framework and marker configuration. `[VERIFIED: local version probe; pyproject.toml]` |
| project result/evidence validators | repository current | Re-open source/result bundles; verify hashes, citations and media. | These are already the local authority for publication. `[VERIFIED: src/debugmate/evidence.py; src/debugmate/results/verifier.py]` |

### Supporting

| Tool | Version | Purpose | When to use |
|---|---:|---|---|
| FFprobe | 8.1 | Confirm referenced MP3 validity/duration. | Required only for rows that claim audio available. `[VERIFIED: local version probe; existing audio verification contract]` |
| Git | 2.50.0.windows.2 | Bind source commit/worktree and verify frozen paths from QA layer. | QA scripts only; product Python must not spawn Git. `[VERIFIED: local version probe; 08-01-SUMMARY.md]` |
| PowerShell | Windows host | Zero-skip runner, exact roots, frozen-scope checks. | Use `-LiteralPath` and value-free environment checks. `[VERIFIED: AGENTS.md; existing Phase 7/8 runner pattern]` |

### Alternatives Considered

| Instead of | Could use | Tradeoff |
|---|---|---|
| Strict JSON ledger + generated Markdown | Spreadsheet/manual table | Manual edits cannot reliably preserve run/result/prompt hashes and are harder to test. `[VERIFIED: project reproducibility constraint]` |
| Importing current Phase 08 live manifest | Re-running Dify once per case/version | Extra quota, non-determinism and accidental product-workflow drift; only do explicit evaluation runs when provenance is required. `[VERIFIED: cost constraint; current prompt binding]` |
| Existing deterministic result validators | Custom media/hash checker | Duplicates already tested ZIP, PNG and MP3 edge cases. `[VERIFIED: src/debugmate/results/verifier.py; tests/results]` |

**Installation:** none. Use the existing `.venv`. `[VERIFIED: pyproject.toml; environment probe]`

## Architecture Patterns

### Recommended Project Structure

```text
evaluation/phase9/
├── cases.json                       # four selected scenarios and expected coverage
└── prompt-criteria.json             # version-specific checks and adoption intent

src/debugmate/evaluation/
├── contracts.py                     # strict Phase9 models
├── collector.py                     # verified run/result import
├── prompt_compare.py                # same-case generation/verification provenance
└── reports.py                       # deterministic JSON + Markdown projections

scripts/
├── run-phase9-evaluation.ps1        # offline first, live prerequisite gate, atomic promotion
└── verify-phase9-scope.ps1           # privacy + hashes + frozen Phase10 paths

evidence/evaluation/phase9/
├── manifest.json                    # whole evaluation identity and status
├── case-results.json                # 3–5 current rows
├── prompt-comparison.json           # V1–V4 same-case results
├── workflow-source.json             # current workflow/DSL/knowledge identities
├── phase10-inputs.json              # eligible source ledger, no rendered media
├── cases/                            # safe per-case projections/references
└── checksums.sha256

docs/course/
├── current-evaluation.md            # generated preview for human review
└── current-prompt-comparison.md      # generated preview; not final PPT/video copy
```

This isolates current Phase 09 evidence from the historical `evidence/course-v0.1/` and from final `deliverables/`. `[VERIFIED: current repository layout; locked Phase 10 boundary]`

### Pattern 1: Reference verified bundles; do not copy raw runs

**What:** A case row stores repository-relative manifest paths plus their exact SHA-256, then re-opens and validates those manifests and all referenced result artifacts before promotion. `[VERIFIED: existing verifier/publisher pattern]`

**When to use:** Every success, replay, fallback and partial row. Typed pre-diagnosis failure rows instead reference the safe receipt/failure manifest and explicitly set all modalities unavailable. `[VERIFIED: 08-CONTEXT D8-15/D8-17; result failure contract]`

**Example:**

```python
# Source: repository recommendation based on ResultManifest/RunManifest contracts
class CaseEvaluation(StrictFrozenModel):
    case_key: str
    coverage: tuple[Literal[
        "live_success", "insufficient_data", "long_content",
        "privacy", "fallback_or_failure"
    ], ...]
    input_sha256: str
    mode: Literal["live", "replay"]
    execution_backend: Literal["dify", "local_fallback", "replay"]
    expected_status: Literal["completed", "partial", "blocked", "failed"]
    actual_status: Literal["completed", "partial", "blocked", "failed"]
    source_manifest: HashBoundPath
    result_manifest: HashBoundPath | None
    citations: CitationEvaluation
    modalities: ModalityEvaluation
    privacy: PrivacyEvaluation
    limitations: tuple[str, ...]
    phase10_eligible: bool
    exclusion_reasons: tuple[str, ...]
```

### Pattern 2: Four-case coverage matrix

| Case key | Source | Required evidence | Notes |
|---|---|---|---|
| `P9-C01-live-private` | Exact accepted Phase 08 Plan 07 case. `[VERIFIED: 08-07-PLAN.md intended artifact]` | Backend `dify`, request/input hash, direct citations, report/PNG/MP3/ZIP hashes, privacy pass, limitations. | Also becomes the single V1–V4 case; blocked until Phase 08 manifest exists. |
| `P9-C02-insufficient` | `insufficient_information` fixture rerun. `[VERIFIED: tests/fixtures/diagnosis/workflow_cases.json]` | Expected/actual blocked status, ≤3 questions, no fabricated diagnosis or media, privacy pass. | A correct non-answer is evidence, not failure. |
| `P9-C03-long-replay` | Regenerated `long-content` replay. `[VERIFIED: fixtures/replay/index.json; generator script]` | Explicit replay provenance, long content markers, verified result identities/artifacts, limitations. | No screenshot capture in Phase 09. |
| `P9-C04-fallback-failure` | Deterministic `local_fallback` partial terminal result with the established audio-stage unavailability contract. `[VERIFIED: src/debugmate/results/contracts.py; tests/results/test_result_e2e.py; 08-06-SUMMARY.md]` | Explicit `execution_backend=local_fallback`, `status=partial`, report/card/recap availability, unavailable audio state, safe recovery scope, and limitations. | This single concrete degradation row demonstrates honest backend and modality truth without a fifth case or a cloud-failure ambiguity. |

Each dimension must be a machine-checked coverage tag; prose alone does not close EVAL-01. `[VERIFIED: requirement structure and reproducibility constraint]`

### Pattern 3: Same-case prompt comparison with provenance

The comparison key must include the exact sanitized input SHA-256, case ID, confirmed-facts hash, retrieval-trace hash, knowledge-build ID, schema hash and prompt file hash. Every V1–V4 row must match the common key before it can enter the table. `[VERIFIED: existing same-run identity/evidence contracts]`

Use this provenance enum:

| Value | Meaning |
|---|---|
| `generated_live` | This row's provider-run source evidence actually used this prompt hash and produced its recorded candidate/accepted diagnosis/result. |
| `verified_contract` | The row binds exactly to the accepted V1 diagnosis/result/candidate and its safe fixed-case conclusion, then checks that output against this version's declared constraints; no claim that the version generated it. |
| `rejected` | A generated candidate existed but strict/schema/privacy/citation/command validation rejected it. |
| `blocked` | Prerequisite/provider evidence was unavailable; no synthetic score or output was substituted. |

The current product chain can truthfully provide `generated_live` only for its bound `diagnosis-v1` prompt unless an evaluation-only run records another prompt hash. `[VERIFIED: src/debugmate/cloud/workflow.py; src/debugmate/ui/serve.py; platform/dify/app.dsl.yml]`

The default low-cost plan is: use Phase 08's accepted live output for V1 generation provenance, then run deterministic constraint verification for V1–V4 against that exact output. If the planner adds real V2–V4 provider calls, they must run through a separate evaluation-only adapter/app and may not mutate or temporarily republish `platform/dify/app.dsl.yml`. `[VERIFIED: prompt authenticity statement; Phase 08 DSL authority/fresh-export rule]`

### Pattern 4: Phase 10 source ledger, not media generation

`phase10-inputs.json` should contain only eligible case/prompt/workflow source paths, hashes, provenance labels, claim-safe summaries and exclusion reasons. It must not contain new screenshots, rendered slides, narration audio, SRT or MP4. `[VERIFIED: locked Phase 10 boundary]`

The old `scripts/build-course-ppt.py` and `scripts/build-course-video.py` hard-code 2026-07-19 paths/text and produce final deliverables, so invoking them in Phase 09 would refresh frozen assets from stale assumptions. `[VERIFIED: script inspection; historical manifests]`

### Pattern 5: Atomic promotion

Build under a sibling staging directory, validate all manifests and outputs, scan privacy, verify frozen paths, then atomically promote to `evidence/evaluation/phase9`. A failed run leaves the prior formal directory untouched. `[VERIFIED: existing evidence/result/Phase 08 runner patterns]`

### Anti-Patterns to Avoid

- **Copy old screenshots into a “current” directory:** the existing course screenshots are dated 2026-07-19 and are historical. `[VERIFIED: evidence/course-v0.1/manifest.json]`
- **Infer backend from filenames or artifact presence:** backend is already an explicit enum. `[VERIFIED: src/debugmate/results/contracts.py; 08-04-SUMMARY.md]`
- **Count missing audio/report as a failure automatically:** insufficient-information and typed pre-diagnosis failure intentionally publish no diagnosis artifacts. `[VERIFIED: diagnosis workflow and Phase 08 failure contracts]`
- **Call V2–V4 “live outputs” after static verification:** the current product workflow binds `diagnosis-v1`. `[VERIFIED: current code/DSL]`
- **Use four different extraction/retrieval runs for prompt comparison:** this changes confounders and violates the exact-same-sanitized-case decision. `[VERIFIED: locked user decision; same-run evidence architecture]`
- **Write prompt scores with zero for unavailable runs:** use `blocked`/`not_reported`, consistent with provider usage truth. `[VERIFIED: 08-CONTEXT D8-18; cloud contracts]`
- **Generate PPTX/video to “test EVID-03”:** Phase 09 tests source manifests only; Phase 10 owns final rendering. `[VERIFIED: roadmap boundary]`

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Diagnosis/run verification | A new loose JSON parser | `RunManifest`, `verify_bundle`, `validate_diagnosis_outcome` | Existing strict identity/evidence rules are already tested. `[VERIFIED: source/tests]` |
| Result/media verification | Ad-hoc file-exists checks | `verify_result_bundle`, manifest/checksum/ZIP/MP3/PNG validators | File presence does not prove validity or same-run identity. `[VERIFIED: results verifier]` |
| Privacy scan | New regex list in the evaluation script | `assert_export_safe` plus existing binary/result checks | Prevents divergent security rules. `[VERIFIED: privacy/output_scan.py; evidence.py]` |
| Citation correctness | Count citation strings in Markdown | Validated diagnosis evidence/support links against source anchors | Display text is not retrieval proof. `[VERIFIED: evidence_binding.py; Phase 08 direct-trace rule]` |
| Prompt provenance | Prompt filename alone | File SHA-256 + declared ID + common case/input/facts/trace hashes | Filenames can remain unchanged while content drifts. `[VERIFIED: repository hash-based identity patterns]` |
| Course rendering | New slide/video generator in Phase 09 | Phase 10 consumes `phase10-inputs.json` and existing builders after refresh | Keeps the media-last boundary enforceable. `[VERIFIED: roadmap]` |

**Key insight:** Phase 09 adds trustworthy indexing and comparison over verified evidence; it should not duplicate the evidence producers it evaluates. `[VERIFIED: repository architecture]`

## Common Pitfalls

### Pitfall 1: Declaring live success before Phase 08 acceptance

**What goes wrong:** An offline mocked Dify test, historical C01–C07 capability evidence or the old cloud probe is promoted as current product-chain success. `[VERIFIED: Phase 08 context distinguishes capability from product evidence]`

**How to avoid:** Require both `08-07-SUMMARY.md` and a hash-valid `evidence/dify-live/phase8/manifest.json`; verify backend `dify`, current DSL/prompt/schema/knowledge identities and all four local outputs. `[VERIFIED: 08-07-PLAN.md]`

**Warning signs:** live row sourced from `evidence/dify-live/2026-08-08`/`2026-08-09`, `capability-matrix.json`, or a test fixture rather than the Phase 08 formal path. `[VERIFIED: current evidence tree]`

### Pitfall 2: Prompt comparison changes more than the prompt

**What goes wrong:** Each version gets a different redaction, facts set, retrieval result or knowledge build, so apparent improvement is not attributable to the prompt. `[VERIFIED: same-case decision and evidence identities]`

**How to avoid:** Freeze one `PromptComparisonInput` from P9-C01 and require exact common hashes in all four rows. `[VERIFIED: recommendation based on locked decision]`

### Pitfall 3: Confusing “verified against” with “generated by”

**What goes wrong:** V2–V4 design documents are represented as executed model variants even though the current product code runs `diagnosis-v1`. `[VERIFIED: prompts/README.md; runtime binding]`

**How to avoid:** Persist a strict provenance enum and display it in both JSON and Markdown tables. `[VERIFIED: recommendation]`

### Pitfall 4: Treating expected absence as modality inconsistency

**What goes wrong:** The insufficient-data or pre-diagnosis failure case is marked invalid because it correctly has no report/PNG/MP3/ZIP. `[VERIFIED: workflow/result failure contracts]`

**How to avoid:** Validate artifact expectations by actual terminal status; completed requires all claimed artifacts, partial requires declared availability, blocked/failed requires no fabricated artifacts. `[VERIFIED: ResultManifest validators]`

### Pitfall 5: Historical course files drift into current evidence

**What goes wrong:** Old screenshots, prompt wording, test counts or media hashes are copied into current tables. `[VERIFIED: historical docs/manifests contain 2026-07-19 claims]`

**How to avoid:** Phase 09 source manifests accept only current evidence roots and prompt hashes; historical directories are a read-only exclusion baseline. `[VERIFIED: roadmap boundary]`

### Pitfall 6: Privacy scans miss binary or nested material

**What goes wrong:** JSON is scanned but PNG metadata, MP3 embedded strings, ZIP members or Markdown still expose a path/key. `[VERIFIED: evidence/result security tests cover multiple formats]`

**How to avoid:** Reuse the full result verifier, binary safety checks, ZIP reopen and export scan recursively before promotion. `[VERIFIED: evidence.py; results/verifier.py]`

### Pitfall 7: EVID-03 ownership ambiguity

**What goes wrong:** The requirements trace table maps EVID-03 to Phase 10, while the Phase 09 roadmap also assigns it; a plan might either do nothing or generate final media early. `[VERIFIED: .planning/REQUIREMENTS.md traceability table; .planning/ROADMAP.md Phase 9]`

**How to avoid:** Define split acceptance: Phase 09 generates current machine-readable case/prompt/workflow/material source manifests; Phase 10 renders and validates final PPT/media. `[VERIFIED: Phase 9/10 goals]`

## Code Examples

### Deterministic evaluation identity

```python
# Source: project canonical JSON + SHA-256 identity pattern
payload = {
    "schema_version": "phase9-evaluation-1.0",
    "source_commit": source_commit,
    "phase8_manifest_sha256": phase8_manifest_sha256,
    "case_registry_sha256": case_registry_sha256,
    "prompt_sha256": prompt_hashes,
    "dsl_semantic_sha256": dsl_semantic_sha256,
    "diagnosis_schema_sha256": diagnosis_schema_sha256,
    "knowledge_build_id": knowledge_build_id,
}
evaluation_id = "eval_" + sha256_bytes(canonical_json_bytes(payload))[:32]
```

### Hard live prerequisite

```python
# Source: locked Phase 08 dependency rule
def require_phase8_live(root: Path) -> tuple[Path, dict[str, object]]:
    summary = root / ".planning/phases/08-dify-unified-live-chain/08-07-SUMMARY.md"
    manifest = root / "evidence/dify-live/phase8/manifest.json"
    if not summary.is_file() or not manifest.is_file():
        raise Phase9Blocked("phase8_live_evidence_missing")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    validate_phase8_manifest(payload, root=root)
    return manifest, payload
```

### Common prompt input gate

```python
# Source: recommendation derived from same-case decision
common = comparisons[0].common_input
for item in comparisons:
    if item.common_input != common:
        raise EvaluationError("prompt_comparison_input_drift")
    if item.prompt_sha256 != sha256_file(root / item.prompt_path):
        raise EvaluationError("prompt_hash_drift")
```

### Honest Phase 10 eligibility

```python
# Source: EVAL-05 and current result contracts
eligible = (
    row.actual_status in {"completed", "partial"}
    and row.privacy.status == "pass"
    and row.source_manifest.verified
    and row.result_manifest is not None
    and row.modalities.claimed_files_valid
    and row.provenance in {"real_live", "explicit_replay", "local_fallback"}
)
```

## State of the Art in This Repository

| Old approach | Current Phase 09 approach | Change point | Impact |
|---|---|---|---|
| Historical 2026-07-19 screenshots/case prose | Hash-bound current case ledger | Phase 09 gap-closure roadmap. `[VERIFIED: roadmap]` | Prevents stale evidence from silently entering final media. |
| V1 run plus V2–V4 design narrative | Same-case prompt hash/provenance/constraint table | Phase 09 success criterion. `[VERIFIED: roadmap; prompts/README.md]` | Makes generation vs verification explicit. |
| `backend="local-rule-v1"` prose | Orthogonal `mode` and `execution_backend` | Phase 08 Plan 04. `[VERIFIED: 08-04-SUMMARY.md]` | Enables truthful Dify/local/replay comparison. |
| File-exists media checks | Strict result manifest, checksums, FFprobe and ZIP reopen | Phase 04/08 contracts. `[VERIFIED: results verifier/tests]` | Phase 09 can reuse verified validity rather than inspect manually. |
| Immediate final PPT/video generation | Source ledger first, final media last | Phase 09/10 split. `[VERIFIED: roadmap]` | Avoids repeated stale rebuilds and frozen-scope violations. |

**Deprecated/outdated for Phase 09:**

- `evidence/course-v0.1/manifest.json` as current evidence authority: it records capture date 2026-07-19 and historical UI. `[VERIFIED: manifest]`
- `docs/course/prompt-iteration.md` as the final comparison result: it explicitly says V2–V4 were design iterations without fabricated cloud batch results. `[VERIFIED: document]`
- `deliverables/asset-manifest.json` and `video-manifest.json` as current output manifests: both are dated 2026-07-19 and must remain frozen until Phase 10. `[VERIFIED: manifests; locked boundary]`

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| — | No unverified factual claims are required for the recommended plan. P9-C04 is fixed as the deterministic `local_fallback` partial terminal state because the existing result contract and fixtures already prove its honest modality availability. | All | None. |

## Open Questions (RESOLVED)

1. **Phase 08 dependency:** Phase 09 formal collection and promotion are hard-gated by the completed `08-07-SUMMARY.md` and the exact, checksum-valid `evidence/dify-live/phase8/manifest.json` bundle. Until both validate, the formal runner emits `blocked`/`phase8_live_evidence_missing`, cannot mark P9-C01 live, and leaves the prior ledger untouched. `[VERIFIED: 08-07-PLAN.md; locked no-false-live decision]`

2. **V2–V4 provenance:** V1 is `generated_live` only when the accepted Phase 08 output binds its exact prompt hash and source-evidence reference. V2–V4 default to `verified_contract`, each bound to that exact accepted V1 diagnosis/result/candidate and its safe fixed-case conclusion. A V2–V4 `generated_live` row is allowed only when its own separately recorded provider-run evidence and exact prompt hash validate; the product DSL remains immutable. `[VERIFIED: prompts/README.md; src/debugmate/cloud/workflow.py; platform/dify/app.dsl.yml]`

3. **P9-C04 degradation choice:** Use the deterministic `local_fallback` partial terminal state with the existing audio-stage unavailability semantics: report/card/recap remain identity-bound and available, audio is explicitly unavailable, and the row records the safe retry scope and limitation. This exercises the existing partial-result validator and makes the fallback evidence precise without implying a Dify failure. `[VERIFIED: src/debugmate/results/contracts.py; tests/results/test_result_e2e.py; 08-06-SUMMARY.md]`

## Environment Availability

| Dependency | Required by | Available | Version/status | Fallback |
|---|---|---|---|---|
| `.venv` CPython | All evaluation commands | ✓ | 3.13.5 `[VERIFIED: local probe]` | — |
| pytest | Validation architecture | ✓ | 9.1.1 `[VERIFIED: local probe]` | — |
| FFprobe | MP3 validation | ✓ | 8.1 `[VERIFIED: local probe]` | Existing result verifier still rejects unverified audio. |
| Git | source/frozen-scope inventory in QA | ✓ | 2.50.0.windows.2 `[VERIFIED: local probe]` | No product-Python fallback; QA only. |
| Dify app configuration names | Phase 08 live evidence | partial | API key/base URL/user present; values were not read. `[VERIFIED: value-free probe]` | Offline evaluation rows can run, but no live-pass claim. |
| `DIFY_DATASET_API_KEY` | Phase 08 exact knowledge acceptance | ✗ | missing `[VERIFIED: value-free probe]` | None for closing Phase 08/Phase 09 live success. |
| Phase 08 formal manifest | P9-C01 and prompt common input | ✗ | missing `[VERIFIED: filesystem inspection]` | Development may emit overall `blocked`; formal pass has no fallback. |

**Missing dependencies with no fallback:** Phase 08 Plan 07 formal evidence, currently also blocked by the absent dataset API key. `[VERIFIED: 08-07-PLAN.md; environment/filesystem inspection]`

**Missing dependencies with fallback:** None for a truthful final Phase 09 pass. Offline Wave 0 development is not a substitute for the live prerequisite. `[VERIFIED: locked decision]`

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 9.1.1 `[VERIFIED: local probe]` |
| Config file | `pyproject.toml` `[VERIFIED: repository]` |
| Quick run command | `.\.venv\Scripts\python.exe -m pytest -q tests/evaluation/test_contracts.py tests/evaluation/test_case_matrix.py tests/evaluation/test_prompt_comparison.py` |
| Full offline command | `.\.venv\Scripts\python.exe -m pytest -q` |
| Formal Phase 09 command | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-phase9-evaluation.ps1` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test type | Automated command | File exists? |
|---|---|---|---|---|
| EVAL-01 | Exactly 3–5 rows, all five locked coverage tags, deterministic rerun and expected/actual status. | unit + integration | `pytest -q tests/evaluation/test_case_matrix.py` | ❌ Wave 0 |
| EVAL-03 | Four prompt hashes, one common sanitized/facts/retrieval identity, explicit provenance/adoption/limitations. | unit + integration | `pytest -q tests/evaluation/test_prompt_comparison.py` | ❌ Wave 0 |
| EVAL-05 | Each eligible row has real-live/explicit-replay/local provenance, privacy pass, valid files and consistent identities. | integration + adversarial | `pytest -q tests/evaluation/test_course_source_manifest.py tests/results/test_security_abuse.py` | ❌ first file Wave 0; security tests exist |
| EVID-03 | Generate case table, prompt table, workflow source and Phase 10 input ledger from evidence only, without frozen-media writes. | integration + scope | `pytest -q tests/evaluation/test_reports.py; powershell -File scripts/verify-phase9-scope.ps1` | ❌ Wave 0 |

### Required adversarial tests

- Missing Phase 08 summary/manifest yields `blocked`, not live success. `[VERIFIED: locked prerequisite]`
- Historical C01–C07 or `course-v0.1` manifest cannot satisfy P9-C01. `[VERIFIED: Phase 08 evidence distinction]`
- Any prompt comparison input/facts/retrieval/prompt hash, accepted diagnosis/result/candidate hash, conclusion, or source-evidence drift fails. `[VERIFIED: exact same-case decision]`
- `verified_contract` cannot serialize as `generated_live`. `[VERIFIED: authenticity boundary]`
- Secret, absolute personal path, approval material, raw remote ID/body or prompt injection in any JSON/Markdown blocks promotion. `[VERIFIED: project/Phase 08 security boundary]`
- Artifact hash/MIME/ZIP/member/audio mismatch makes the row ineligible. `[VERIFIED: existing result verifier]`
- Insufficient-data/typed failure rows reject fabricated report/PNG/MP3/ZIP. `[VERIFIED: failure contracts]`
- Any modification/new file under frozen screenshot/PPTX/MP4/SRT/final-media targets fails the scope gate. `[VERIFIED: locked Phase 10 boundary]`

### Sampling Rate

- **Per task commit:** focused evaluation test file plus `ruff check` on changed Python. 
- **Per wave merge:** all `tests/evaluation`, existing privacy/evidence/result focused suites, then default offline pytest.
- **Formal phase gate:** Phase 08 prerequisite valid, four cases accepted, prompt comparison common key exact, privacy/scope scan clean, checksums exact and PowerShell runner zero-skip.

### Wave 0 Gaps

- [ ] `src/debugmate/evaluation/contracts.py` — strict manifest and provenance models.
- [ ] `tests/evaluation/test_contracts.py` — strict/extra-forbid/path/hash contracts.
- [ ] `tests/evaluation/test_case_matrix.py` — 3–5 range and coverage/status rules.
- [ ] `tests/evaluation/test_prompt_comparison.py` — exact same input and generation-vs-verification truth.
- [ ] `tests/evaluation/test_course_source_manifest.py` — EVAL-05 eligibility.
- [ ] `tests/evaluation/test_reports.py` — deterministic JSON/Markdown projections.
- [ ] `scripts/verify-phase9-scope.ps1` — privacy, secret and frozen Phase 10 paths.
- [ ] `scripts/run-phase9-evaluation.ps1` — offline/live gate and atomic promotion.

No test framework installation is needed. `[VERIFIED: pytest available]`

## Security Domain

Security enforcement is enabled because `.planning/config.json` does not set it to false. `[VERIFIED: config inspection]`

### Applicable ASVS Categories

| ASVS Category | Applies | Standard control |
|---|---|---|
| V2 Authentication | limited | Dify keys remain server environment only; Phase 09 reads only value-free readiness. `[VERIFIED: project architecture]` |
| V3 Session Management | no new surface | Phase 09 is a CLI/evidence workflow; it reuses Phase 08 receipts and does not create browser sessions. `[VERIFIED: recommended architecture]` |
| V4 Access Control | yes | Restrict source paths to allowlisted repository roots and deny historical/frozen paths as current inputs. `[VERIFIED: existing trusted-root pattern]` |
| V5 Input Validation | yes | Strict Pydantic, canonical JSON, bounded strings/lists, safe relative paths, SHA-256 and exact enums. `[VERIFIED: repository standard]` |
| V6 Cryptography | yes | Standard SHA-256/HMAC comparison helpers only; never hand-roll crypto. `[VERIFIED: existing hashing/receipt patterns]` |
| V12 Files and Resources | yes | Root confinement, regular-file/no-link checks, bounded reads, MIME/media validation and atomic promotion. `[VERIFIED: evidence/result patterns]` |
| V14 Configuration | yes | Value-free env readiness, no key values in CLI/UI/evidence, frozen-scope inventory. `[VERIFIED: Phase 08 security decisions]` |

### Trust Boundaries

| Boundary | Risk | Required control |
|---|---|---|
| Phase 08 formal evidence → Phase 09 ledger | Stale/forged/currentness confusion | Exact allowed path, manifest/schema/hash/current contract validation. |
| Prompt files/output → comparison table | Variant or common-input drift | File hashes, common key, strict provenance enum. |
| Result bundles → course eligibility | Corrupt/mismatched media or citations | Reopen using existing validators; no display-text inference. |
| Staging → tracked evaluation evidence | Partial/leaking publication | Privacy scan, checksums, scope gate, atomic promotion. |
| Phase 09 → Phase 10 inputs | Historical or ineligible claim enters final media | Eligibility boolean plus machine-readable exclusion reasons. |

### Known Threat Patterns

| Pattern | STRIDE | Standard mitigation |
|---|---|---|
| Historical evidence relabelled current | Spoofing | Current formal path + source commit + contract/hash identity gate. |
| Prompt output provenance inflated | Spoofing/Repudiation | `generated_live` vs `verified_contract` enum and per-row source hash. |
| Different inputs used across variants | Tampering | One immutable common-input object and equality gate. |
| Secret/path/raw provider data in reports | Information Disclosure | Existing export/binary/ZIP scans; allowlisted safe projections. |
| Oversized output or recursive JSON | Denial of Service | Bounded file/read/list/string limits and strict models. |
| Prompt/log text influences runner behavior | Elevation/Tampering | Treat all prompt/case/provider strings as data; no command execution. |
| Evaluation runner overwrites final media | Tampering | Explicit frozen path inventory and failure on any diff/new file. |
| Partial run replaces last good ledger | Tampering | sibling staging and atomic promotion only after all gates. |

### Privacy boundaries

- The canonical prompt-comparison input is the already sanitized Phase 08 projection; raw input, screenshot bytes, approval token/signature and provider body are not copied into Phase 09. `[VERIFIED: Phase 08 evidence decisions]`
- Store values only when needed for course interpretation; otherwise store SHA-256, stable safe enums, bounded summaries and source-relative paths. `[VERIFIED: existing safe-evidence pattern]`
- Privacy coverage must include both a positive scan result and an adversarial fixture that is rejected without echoing the secret. `[VERIFIED: tests/privacy/test_output_scan.py pattern]`
- Failure reports expose stable code/stage/status only; exception chains and raw provider messages remain excluded. `[VERIFIED: Phase 08 safe failure contract]`

## Sources

### Primary (HIGH confidence)

- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` — scope, requirement wording, phase boundary and current position.
- `.planning/phases/08-dify-unified-live-chain/08-CONTEXT.md`, `08-RESEARCH.md`, `08-VALIDATION.md`, Plans 01–07 and Summaries 01–06 — direct dependency contracts, current implementation and missing final acceptance.
- `src/debugmate/evidence.py`, `src/debugmate/results/*`, `src/debugmate/privacy/output_scan.py`, `src/debugmate/diagnosis/evidence_binding.py` — verification and security patterns.
- `prompts/README.md`, `prompts/v1-baseline.md` through `v4-course-release.md` — prompt lineage and authenticity statement.
- `fixtures/replay/*`, `tests/fixtures/diagnosis/workflow_cases.json`, fixture generators — deterministic case assets.
- `docs/course/*`, `evidence/course-v0.1/manifest.json`, `deliverables/*-manifest.json`, course builders — historical assets and frozen media boundary.

### Secondary (MEDIUM confidence)

- None. This phase is codebase-specific and does not require external ecosystem claims.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — versions and installed tools verified locally.
- Architecture: HIGH — derived from live repository contracts and locked roadmap boundaries.
- Case selection: HIGH — all recommended sources exist except the intentionally gated Phase 08 formal live evidence.
- Prompt execution availability: MEDIUM — current V1 binding is verified, but V2–V4 real provider generation is not implemented and is intentionally not claimed.
- Pitfalls/security: HIGH — tied to existing adversarial tests and Phase 08 decisions.

**Research date:** 2026-08-10  
**Valid until:** 2026-08-17, or immediately invalidated by completion/contract changes in Phase 08 Plan 07.
