# Phase 08: Dify Unified Live Chain - Research

**Researched:** 2026-08-10  
**Domain:** Dify Workflow Application API, knowledge synchronization, strict local validation, durable live-run integration  
**Confidence:** HIGH for repository architecture and documented API contracts; MEDIUM-HIGH for the exact current published-app output shape until the required live smoke is run. `[VERIFIED: repository inspection]` `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]`

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Execution mode and consent
- **D8-01:** Ordinary live mode constructs Dify only when the complete environment configuration is valid. Missing configuration constructs the existing local chain and labels it `local_fallback`; replay remains explicit, allowlisted and offline. There is no student-facing backend or API-key selector.
- **D8-02:** Application construction performs no network probe. The first outbound request may occur only after the current revision-bound preview authority is atomically consumed. The confirmation copy states that the redacted payload will be sent to configured Dify and may consume quota.
- **D8-03:** Once a configured Dify attempt starts, authentication, quota, transport, timeout or contract failure remains a typed cloud failure. It never silently becomes a local success. A local attempt requires a fresh preview and confirmation.

### Published workflow contract
- **D8-04:** The versioned `platform/dify/app.dsl.yml` contract is authoritative. Approved screenshots are re-hashed, uploaded with verified image MIME and supplied as `image_input={type:image, transfer_method:local_file, upload_file_id:...}`; text-only runs omit `image_input`. `file_id` stays metadata-only.
- **D8-05:** Dify returns one bounded same-run envelope: strict diagnosis candidate, sanitized VLM facts, bounded direct Knowledge Retrieval trace, safe node/run fingerprint and usage when actually reported. Diagnosis citations alone do not prove retrieval.
- **D8-06:** KNOW-03 closes only after all 17 registered Git sources are rebuilt, safely synchronized to the configured dataset, and read back with document count, source/content hashes, metadata and retrieval configuration. Unexpected remote deletes fail closed.
- **D8-07:** Any DSL/trace/contract change requires a fresh export whose hash, dataset binding, prompt/schema version and sanitized outputs are versioned. Historical C01–C07 evidence remains capability evidence, not product-chain evidence.

### Local validation and result integration
- **D8-08:** Provider output is untrusted until local strict validation proves DiagnosisRecord 1.1.0, case ID, facts/evidence graph, knowledge-build identity, command safety and privacy. Only a valid same-run envelope becomes a `DiagnosisRunOutcome` and enters the existing evidence publisher, outcome store and result composer.
- **D8-09:** JSON/semantic repair has exactly one additional Dify call. Repair input contains only safe issue codes/pointers plus the redacted candidate. Privacy-unsafe or unsafe-command failures are terminal and never repairable.
- **D8-10:** A workflow POST is never automatically replayed after an ambiguous read timeout. At most one retry is allowed only for a proven pre-dispatch connection failure. Upload attempts, workflow attempts and contract repair are distinct evidence events.
- **D8-11:** Add a durable server-side receipt keyed by approval identity and preview hash with `started/succeeded/uncertain/failed`. Existing one-time consume, serial queue, per-case lock, immutable outcome store and verified cache remain authoritative. Stale UI sessions cannot overwrite newer runs.
- **D8-12:** There is no cosmetic cloud cancellation. Inputs, replay and duplicate actions are disabled during the blocking run; closing the page does not claim to cancel Dify.

### UI, failures, privacy and cost truth
- **D8-13:** `ResultMode` remains `live|replay`. A separate strict backend field flows through outcome, manifest and self-contained view state with values including `dify`, `local_fallback` and `replay`; presentation never infers it from filenames or artifact presence.
- **D8-14:** Progress is coarse and truthful: local preview, optional upload, Dify running, local validation, then existing result stages. Do not invent percentages or claim vision/retrieval node completion before validating the returned trace.
- **D8-15:** Typed safe failures distinguish configuration, authentication, quota, pre-dispatch transport, ambiguous timeout, upload, workflow envelope, diagnosis validation, repair exhaustion, knowledge readback and local result composition. Invalid cloud diagnosis exposes no report/PNG/MP3/ZIP. Valid diagnosis with later media failure keeps existing partial-result semantics.
- **D8-16:** API keys, dataset keys, approval signatures/tokens, raw provider bodies and raw remote identifiers never enter UI, logs, evidence or ZIP. `DIFY_BASE_URL` is HTTPS and origin-constrained outside explicit tests; upload uses an application-owned immutable byte snapshot; response bodies are bounded before JSON parsing.

### Evidence and acceptance
- **D8-17:** Publish one current synthetic-but-real redacted end-to-end case binding request/redaction/upload fingerprints, Dify run fingerprint, DSL/prompt/schema/knowledge hashes, validated extraction/retrieval trace, strict diagnosis, local result identities, Markdown, PNG, MP3 and ZIP hashes. No raw input or approval material is versioned.
- **D8-18:** Usage/cost is recorded only when Dify reports it; otherwise use `not_reported`, never numeric zero. Failed runs produce an atomic safe failure record; successful raw responses are not published before all local checks pass.
- **D8-19:** Acceptance layers are mock/adversarial contract tests, offline service/UI/result regression, explicit cloud-marked service smoke, then one zero-skip real Edge Dify-live path with media and ZIP verification. Existing Phase 7 and C01–C07 evidence is reused rather than regenerated.
- **D8-20:** Resolve the pre-existing `dify_live_evidence.py` command-safety red test before declaring Phase 8 green.

### Claude's Discretion
- Exact class/module names for the run envelope, durable receipt and safe error taxonomy.
- Whether the receipt is an append-only JSON record or another repository-consistent atomic local format.
- Exact bounded limits for trace entries, response bytes and safe error detail, provided tests prove fail-closed behavior.

### Deferred Ideas (OUT OF SCOPE)
- Phase 9: current 3–5 representative cases, privacy/degradation matrix and V1–V4 same-case prompt comparison.
- Phase 10: final course screenshots, PPTX, narration script, SRT, MP4, manifests and final human flip/listen QA.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| KNOW-03 | Rebuild the Dify knowledge base from local sources and verify count, metadata and retrieval configuration. `[VERIFIED: .planning/REQUIREMENTS.md]` | Use the existing sealed sync plan, asynchronous indexing-status polling, official metadata endpoints, paginated document readback, dataset-detail readback, and exact 17-source comparison. `[VERIFIED: src/debugmate/knowledge/sync.py; knowledge/sources.json]` `[CITED: https://docs.dify.ai/en/api-reference/documents/get-document-indexing-status]` |
| KNOW-04 | Retain hit chunk identity, bounded content summary, source metadata, score and citation position. `[VERIFIED: .planning/REQUIREMENTS.md]` | Export a sanitized projection of the Knowledge Retrieval node's direct `result` variable in the workflow envelope and bind it locally to the current run/build. `[CITED: https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval]` |
| DIAG-02 | Generate a DiagnosisRecord v1 object from structured input and retrieval. `[VERIFIED: .planning/REQUIREMENTS.md]` | Keep Dify as candidate producer and reuse strict `DiagnosisRecord`/`DiagnosisGenerator` local authority, including one controlled repair. `[VERIFIED: contracts/diagnosis-record-v1.1.schema.json; src/debugmate/diagnosis/generation.py]` |
| MULTI-03 | Generate a playable/downloadable Chinese MP3 from the same diagnosis. `[VERIFIED: .planning/REQUIREMENTS.md]` | Do not alter the Phase 4 media pipeline; feed only a verified `DiagnosisRunOutcome` into the existing result composer and retain its partial-media semantics. `[VERIFIED: src/debugmate/results/service.py; tests/results/test_media.py; tests/results/test_tts_chain.py]` |
| UX-01 | Present redacted input, extracted fields, evidence, report, PNG and audio on one Gradio page. `[VERIFIED: .planning/REQUIREMENTS.md]` | Extend the existing view state with explicit execution backend and coarse live stages; preserve stable Phase 4/7 result surfaces. `[VERIFIED: src/debugmate/ui/app.py; .planning/phases/07-real-input-privacy-ui/07-VERIFICATION.md]` |
| EVID-01 | Save redacted input hash, workflow/prompt/knowledge/model identity, run/node state, latency, reported usage/cost and artifact hashes. `[VERIFIED: .planning/REQUIREMENTS.md]` | Publish a sanitized accepted-envelope projection plus atomic attempt/receipt records; never publish raw Dify bodies or raw remote identifiers. `[VERIFIED: 08-CONTEXT.md D8-16 through D8-18]` |
</phase_requirements>

## Summary

Phase 08 should add a separate `DifyLiveWorkflow` orchestration path that conforms to the existing `DiagnosisWorkflow.run(ApprovedRedactedInput) -> DiagnosisRunOutcome` seam, while leaving the Phase 4 publisher/composer and Phase 7 preview/approval mechanisms intact. The Dify path starts only after `LocalPreviewStore.consume_current()` and approval signing; it records a durable receipt before the first outbound byte, uploads an immutable verified image snapshot when present, runs one blocking published workflow, validates a bounded same-run envelope locally, and only then calls the existing evidence/outcome/result pipeline. `[VERIFIED: src/debugmate/ui/app.py:2128-2144; src/debugmate/results/service.py:345-410; 08-CONTEXT.md D8-02/D8-08/D8-11]`

The current DSL is not yet a Phase 08 product-chain contract: it exposes only `outputs.diagnosis`, while the current direct retrieval evidence was captured separately from a console log and even carries a different workflow-run fingerprint than the retained C03 run. Historical C03/C04 remains valid capability evidence, but it cannot prove a same-run Phase 08 chain. The fresh DSL must expose a bounded, sanitized projection of the Knowledge Retrieval node's documented `result` array and extraction facts as explicit End outputs; the adapter then binds these outputs to the blocking response's `workflow_run_id` and reported usage. `[VERIFIED: platform/dify/app.dsl.yml:645-654; evidence/dify-live/2026-08-09/c03-c04/retriever-resource.json; evidence/dify-live/2026-08-09/c03-c04/workflow-output.json]` `[CITED: https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval]`

KNOW-03 also requires more than the current `execute_sync()` implementation. Dify document creation/update is asynchronously indexed and returns a batch ID; source metadata should be written through the documented metadata-field/batch-update API, then the dataset, all paginated documents and their metadata must be read back and matched to the sealed 17-source build. Unexpected deletes remain a pre-execution failure unless separately confirmed. `[VERIFIED: src/debugmate/knowledge/sync.py:634-701; knowledge/sources.json contains 17 records]` `[CITED: https://docs.dify.ai/en/api-reference/documents/create-document-by-text]` `[CITED: https://docs.dify.ai/en/api-reference/metadata/update-document-metadata-in-batch]`

**Primary recommendation:** implement Phase 08 as five bounded layers—configuration/receipt, Dify HTTP adapter, knowledge sync/readback, Dify envelope workflow/local validation, and unchanged result composition—then close with one zero-skip real Edge/Dify evidence run. `[VERIFIED: 08-CONTEXT.md D8-01 through D8-20]`

## Project Constraints

- Treat `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` and `.planning/STATE.md` as current truth; this research changes no implementation or STATE. `[VERIFIED: project AGENTS.md]`
- Preserve the planning/implementation boundary and do not refresh frozen Phase 9/10 media. `[VERIFIED: project AGENTS.md; 08-CONTEXT.md Deferred Ideas]`
- Keep secrets server-side, version reproducible source/prompt/DSL/evidence assets, use true runs rather than generated screenshots, and require confirmation before paid APIs or subscriptions. `[VERIFIED: .planning/PROJECT.md constraints]`
- No repository-local `.claude/skills/` or `.agents/skills/` project skill was present during research. `[VERIFIED: filesystem inspection 2026-08-10]`
- No repository `CLAUDE.md` was present, so there are no additional `CLAUDE.md` directives to copy. `[VERIFIED: filesystem inspection 2026-08-10]`

## Standard Stack

### Core

| Component | Version / contract | Purpose | Prescriptive use |
|---|---|---|---|
| CPython | 3.13.5 installed; project requires `>=3.13,<3.14`. `[VERIFIED: local environment; pyproject.toml]` | Runtime and durable local authority. | Keep all approval, validation, receipts and evidence local. `[VERIFIED: .planning/PROJECT.md]` |
| HTTPX | 0.28.1 pinned and installed. `[VERIFIED: pyproject.toml; importlib.metadata]` | Application/Knowledge API transport. | Retain one narrow adapter, explicit connect/read/write/pool timeouts, no redirects, bounded streaming reads, and retry only `ConnectError`/`ConnectTimeout` before dispatch. `[CITED: https://www.python-httpx.org/exceptions/]` `[CITED: https://www.python-httpx.org/advanced/transports/]` |
| Pydantic | 2.13.4 pinned and installed. `[VERIFIED: pyproject.toml; importlib.metadata]` | Strict envelopes, settings, receipts, safe failures and manifest contracts. | Continue `strict=True`, `extra='forbid'`, frozen boundary models and canonical hashes. `[VERIFIED: repository model patterns]` |
| Dify Workflow Application API | Published-workflow contract; cloud version not hard-coded. `[VERIFIED: platform/dify/app.dsl.yml; .planning/PROJECT.md]` | Image upload and one blocking workflow run. | Use documented `/files/upload` and `/workflows/run`; do not depend on console-only node logs or raw provider bodies. `[CITED: https://docs.dify.ai/en/api-reference/files/upload-file]` `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]` |
| Dify Knowledge API | Dataset key, configured dataset and official document/metadata endpoints. `[VERIFIED: src/debugmate/settings.py; 08-CONTEXT.md D8-06]` | Synchronize/read back 17 source documents. | Wait for indexing batches, then verify dataset detail, document pages and metadata values. `[CITED: https://docs.dify.ai/en/api-reference/documents/get-document-indexing-status]` `[CITED: https://docs.dify.ai/en/api-reference/knowledge-bases/get-knowledge-base]` |

### Supporting

| Component | Version / contract | Purpose | When to use |
|---|---|---|---|
| Gradio | 6.20.0 pinned and installed. `[VERIFIED: pyproject.toml; importlib.metadata]` | Existing single-page UI and serial queue. | Preserve `concurrency_limit=1`, stale-session leases, stable component IDs and coarse truthful stages. `[VERIFIED: src/debugmate/ui/app.py]` |
| Pillow | 12.3.0 pinned. `[VERIFIED: pyproject.toml]` | Existing deterministic card plus screenshot byte verification. | Verify approved snapshot format from immutable bytes before upload; do not infer MIME from extension. `[VERIFIED: 08-CONTEXT.md D8-04/D8-16]` |
| pytest | 9.1.1 installed. `[VERIFIED: pyproject.toml; importlib.metadata]` | Mock/adversarial/offline/cloud-marked gates. | Default suite remains network-free; live calls require explicit `cloud` marker and zero-skip runner. `[VERIFIED: pyproject.toml; 08-CONTEXT.md D8-19]` |
| FFmpeg/FFprobe | 8.1 available locally. `[VERIFIED: local environment 2026-08-10]` | Existing MP3 verification. | Reuse unchanged for final real chain verification. `[VERIFIED: platform/dify/README.md; tests/results]` |

**Installation:** no new runtime dependency is required. Use the repository's pinned environment. `[VERIFIED: pyproject.toml; recommended architecture uses only existing dependencies]`

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
```

### Alternatives Considered

| Instead of | Could use | Why it is not the Phase 08 plan |
|---|---|---|
| Blocking Workflow API | Streaming SSE | Streaming enables documented stop/recovery events, but D8-12 deliberately freezes blocking behavior and forbids cosmetic cancellation. `[VERIFIED: 08-CONTEXT.md D8-12]` `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/stop-workflow-task]` |
| Explicit End-output retrieval trace | Workflow logs or diagnosis citations | Logs are not part of the blocking response contract, and citations do not prove direct retrieval. `[VERIFIED: 08-CONTEXT.md D8-05; platform/dify/README.md]` `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]` |
| Existing thin Python integration | New SDK/orchestration framework | The current stack already has strict adapters/contracts; adding another framework would expand failure and version surfaces without closing a requirement. `[VERIFIED: src/debugmate/adapters/dify.py; .planning/PROJECT.md stack constraints]` |

## Architecture Patterns

### Recommended Project Structure and File Boundaries

```text
src/debugmate/
├── settings.py                    # complete no-I/O Dify config + HTTPS origin validation
├── adapters/
│   ├── base.py                    # bounded result protocol extensions only
│   └── dify.py                    # application HTTP, upload bytes, response cap, typed errors
├── cloud/
│   ├── envelope.py                # strict DifyRunEnvelope / usage / trace models
│   ├── receipts.py                # atomic durable receipt transitions
│   └── workflow.py                # Approved input -> gateway -> local validation -> outcome
├── gateway.py                     # approval recheck, immutable image snapshot, exact DSL inputs
├── knowledge/
│   └── sync.py                    # indexing wait, metadata write, pagination/readback adapter
├── diagnosis/
│   ├── generation.py              # reuse one-repair and terminal unsafe rules
│   └── workflow.py                # preserve DiagnosisRunOutcome invariants
├── results/
│   ├── contracts.py               # explicit execution_backend, not ResultMode overloading
│   ├── publisher.py               # backend/attempt identity in manifest
│   └── service.py                 # receipt + existing per-case/cache/store/composer boundary
└── ui/
    ├── serve.py                   # no-I/O configured-Dify vs local_fallback construction
    └── app.py                     # consent copy, disabled actions, coarse truthful progress

platform/dify/app.dsl.yml          # exported published same-run envelope workflow
tests/cloud/                       # adapter/envelope/receipt/adversarial tests
tests/knowledge/                   # official API readback and delete safety
scripts/run-phase8-live-qa.ps1     # explicit cloud+Edge zero-skip orchestration
evidence/dify-live/phase8/         # only sanitized accepted/failure evidence
```

The exact `cloud/` module names are discretionary; the responsibility split is mandatory to keep HTTP concerns, provider-envelope parsing, receipt durability and diagnosis semantics independently testable. `[VERIFIED: 08-CONTEXT.md Agent discretion and D8-08/D8-11/D8-16]`

### Pattern 1: Construct Without I/O, Dispatch Only After Atomic Consent

**What:** `serve.py` parses a complete strict configuration and constructs either `DifyLiveWorkflow` with `execution_backend='dify'` or the existing local graph with `execution_backend='local_fallback'`. Constructors perform no network operations. The UI atomically consumes the current preview token, creates the signed approval, then invokes the service. `[VERIFIED: 08-CONTEXT.md D8-01/D8-02; src/debugmate/ui/app.py:2128-2144]`

**When to use:** every ordinary `live` run. Replay retains its separate allowlisted offline route. `[VERIFIED: 08-CONTEXT.md D8-01/D8-13]`

**Required construction inputs:** validated HTTPS base origin, app key presence, stable Dify user, current exported DSL hash, configured dataset identity fingerprint, and a locally verified knowledge readback attestation for the expected build. Missing any item selects local fallback before UI launch; it does not produce a cloud configuration error after confirmation. `[VERIFIED: 08-CONTEXT.md D8-01/D8-06/D8-07/D8-16]`

### Pattern 2: Durable Receipt Before Outbound Side Effect

**What:** under the existing per-case lock, compute `receipt_id = sha256(canonical({approval_id, preview_hash}))`, but persist only the receipt hash, case ID, preview hash, backend, safe status/timestamps and sanitized attempt fingerprints. Atomically transition `started -> succeeded|uncertain|failed`; never store approval ID/signature/token. `[VERIFIED: 08-CONTEXT.md D8-11/D8-16]`

**Recommended representation:** one strict JSON file per receipt, written to a temporary sibling, flushed, and atomically replaced; transitions are guarded by an in-process lock and validated against an explicit state machine. This matches repository atomic immutable-store patterns while avoiding JSONL truncation recovery. `[VERIFIED: src/debugmate/results/outcome_store.py and repository atomic publisher patterns]`

**State meaning:**

| State | Meaning | Permitted next state |
|---|---|---|
| `started` | Authority consumed and an attempt is about to dispatch or is in progress. `[VERIFIED: D8-11]` | `succeeded`, `uncertain`, `failed` |
| `succeeded` | Strict outcome and result identity are stored. `[VERIFIED: D8-11]` | terminal |
| `uncertain` | Workflow/upload may have reached Dify but no authoritative response was obtained. `[VERIFIED: D8-10/D8-11]` | terminal; fresh preview required |
| `failed` | Definitive safe typed failure. `[VERIFIED: D8-15]` | terminal; fresh preview required |

### Pattern 3: Immutable Upload Snapshot and Exact Workflow Input Shape

**What:** after approval verification, resolve the redacted file under its trusted root, verify the approved hash, read the bounded bytes once, verify image decoding/format, map format to MIME (`PNG -> image/png`, `JPEG -> image/jpeg`), and upload the same immutable bytes. Validate Dify's 201 response ID/name/size/MIME without retaining raw ID. `[VERIFIED: src/debugmate/gateway.py current rehash boundary; 08-CONTEXT.md D8-04/D8-16]` `[CITED: https://docs.dify.ai/en/api-reference/files/upload-file]`

**Dify input:** preserve the locked exported single-file contract exactly:

```python
# Source: 08-CONTEXT.md D8-04 and platform/dify/app.dsl.yml (type: file)
inputs["image_input"] = {
    "type": "image",
    "transfer_method": "local_file",
    "upload_file_id": upload_id,
}
```

Text-only runs omit `image_input`; they do not send `null`, `{}`, or a fabricated file. The same `user` value must be used for upload and workflow because Dify scopes uploaded files to the uploading end user. `[VERIFIED: 08-CONTEXT.md D8-04]` `[CITED: https://docs.dify.ai/en/api-reference/files/upload-file]`

**Live compatibility check:** current generic Dify documentation describes file-type variables as arrays, while the authoritative exported DebugMate DSL declares `image_input` as a singular `type: file`, and the retained 2026-08-09 live capture successfully used the singular object. Execution must re-run one current app-parameter/upload/workflow smoke against the published export and fail closed on any shape drift; do not silently switch shapes. `[VERIFIED: platform/dify/app.dsl.yml:229-235; src/debugmate/dify_live_evidence.py:726-735; historical C03 pass]` `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]`

### Pattern 4: Explicit Same-Run Envelope, Not Undocumented Logs

**What:** modify the Dify workflow graph so the End node returns a single object (recommended variable `run_envelope`) containing:

```json
{
  "envelope_version": "1.0.0",
  "case_id": "case_...",
  "diagnosis": {},
  "extraction_facts": [],
  "retrieval_trace": {"knowledge_build_id": "...", "hits": []},
  "contract": {
    "schema_version": "1.1.0",
    "prompt_version": "...",
    "knowledge_build_id": "...",
    "dsl_semantic_sha256": "..."
  }
}
```

The DSL should sanitize the Knowledge Retrieval node's direct `result` through a deterministic Code node before the diagnosis LLM/End node: allow only at most 4 hits; bound strings; project chunk/segment ID, source ID/title/HTTPS URL, locator, score and short summary; reject duplicate/missing identities. Dify documents `result` as an array containing content, metadata, title and related attributes. `[CITED: https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval]` `[VERIFIED: platform/dify/app.dsl.yml currently top_k=4]`

The adapter reads the blocking response, verifies `data.status == 'succeeded'`, extracts only the named envelope, hashes (does not expose) `workflow_run_id`, and adds reported `elapsed_time`, `total_tokens`, `total_steps`, created/finished timestamps. A provider node-run ID is optional because it is not in the documented blocking response; the stable retrieval-node fingerprint should be derived from the exported DSL semantic contract unless a safe provider node ID is actually returned. `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]` `[VERIFIED: 08-CONTEXT.md D8-05/D8-18]`

### Pattern 5: Local Publication Authority and Repair Lineage

**What:** validate the provider envelope before constructing `DiagnosisRunOutcome`:

1. Strictly parse bounded envelope and `DiagnosisRecord 1.1.0`. `[VERIFIED: contracts/diagnosis-record-v1.1.schema.json]`
2. Require envelope/diagnosis/approval case IDs to match. `[VERIFIED: src/debugmate/diagnosis/generation.py]`
3. Convert sanitized extraction facts into the existing strict fact model and run deterministic local routing. `[VERIFIED: src/debugmate/diagnosis/routing.py; D8-08]`
4. Bind direct retrieval hits to the sealed local source/build manifest; reject unknown source URL/locator/build or duplicate hits. `[VERIFIED: src/debugmate/diagnosis/evidence_binding.py; tests/diagnosis/test_evidence_binding.py]`
5. Reuse `DiagnosisGenerator` semantic equality, command safety and privacy checks. `[VERIFIED: src/debugmate/diagnosis/generation.py]`
6. On a repairable failure, issue exactly one `contract_repair` workflow call containing only safe issue codes/pointers and the redacted candidate. Retain the primary run's extraction/retrieval provenance and record the repair run as a distinct attempt; repair cannot introduce a new fact/evidence set. `[VERIFIED: 08-CONTEXT.md D8-09; src/debugmate/diagnosis/generation.py]`
7. Privacy/unsafe-command failures are terminal after one provider call and expose no diagnosis artifact. `[VERIFIED: tests/diagnosis/test_generation.py; D8-09/D8-15]`

### Pattern 6: Safe HTTP Semantics and Ambiguity Classification

**What:** split endpoint methods rather than applying the current generic two-attempt loop to every exception. HTTPX distinguishes connect, read, write and pool failures; only `ConnectError`/`ConnectTimeout` are proven connection-establishment failures suitable for the one retry allowed by D8-10. `ReadTimeout`, `ReadError`, `WriteTimeout`, `WriteError`, `RemoteProtocolError`, response truncation and client cancellation after dispatch are `uncertain` for workflow POST. `[CITED: https://www.python-httpx.org/exceptions/]` `[VERIFIED: 08-CONTEXT.md D8-10]`

**Prescriptive caps:** use connect 10 s, write 30 s, read 95 s (below Dify Cloud's documented 100 s blocking limit), pool 5 s; cap the complete workflow response at 512 KiB before JSON decoding; keep the existing diagnosis candidate cap at 256 KiB serialized bytes; allow at most 4 retrieval hits, 2,000 characters per summary and 128 characters of safe error detail. These choices are local safety limits and must be contract-tested. `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]` `[VERIFIED: src/debugmate/adapters/base.py candidate limit; 08-CONTEXT.md Agent discretion]`

Use `client.stream()` and count raw bytes before calling `json.loads`; reject oversized `Content-Length` early and stop reading when the accumulated cap is exceeded. Do not follow redirects. `[CITED: https://www.python-httpx.org/api/]` `[VERIFIED: 08-CONTEXT.md D8-16]`

### Pattern 7: Knowledge Sync as a Verified Transaction-Like Workflow

**What:** extend, do not replace, the sealed `create_sync_plan()` / deletion confirmation design. The execution sequence is:

1. Rebuild all 17 registered sources into an immutable local knowledge build and validate the build path/manifest/note hashes. `[VERIFIED: knowledge/sources.json; src/debugmate/knowledge/build.py]`
2. Fetch the full remote document inventory with pagination before planning. Reject duplicate source IDs/document IDs and any unrecognized remote document as an unexpected delete candidate; require separate explicit delete confirmation. `[VERIFIED: src/debugmate/knowledge/sync.py]` `[CITED: https://docs.dify.ai/en/api-reference/documents/list-documents]`
3. Create/update text via official endpoints and record each returned document ID and batch ID only in runtime state. `[CITED: https://docs.dify.ai/en/api-reference/documents/create-document-by-text]`
4. Poll every batch until `completed` or `error`, with bounded deadline/backoff; do not read back while indexing. `[CITED: https://docs.dify.ai/en/api-reference/documents/get-document-indexing-status]`
5. Ensure required string metadata fields exist, then write `source_id`, `content_sha256`, `source_sha256`, source URL/product/version/platform/retrieved timestamp and build ID through the official batch metadata endpoint. `[CITED: https://docs.dify.ai/en/api-reference/metadata/create-metadata-field]` `[CITED: https://docs.dify.ai/en/api-reference/metadata/update-document-metadata-in-batch]`
6. Read dataset detail to verify document count, indexing technique, embedding availability and retrieval settings; paginate all documents and verify exact 17 source/hash/metadata records; optionally list chunks only to prove nonempty completed indexing, not to re-hash transformed chunk text. `[CITED: https://docs.dify.ai/en/api-reference/knowledge-bases/get-knowledge-base]` `[CITED: https://docs.dify.ai/en/api-reference/chunks/list-chunks]`
7. Produce a sanitized local readback attestation containing dataset fingerprint, build ID, config, document fingerprints and API response hashes—not raw dataset/document IDs. `[VERIFIED: 08-CONTEXT.md D8-06/D8-16]`

The current `_dify_document_payload()` places `doc_metadata` directly in create/update payloads, but current official create-by-text documentation does not list that field. Move metadata writes to the documented metadata API and verify live readback. `[VERIFIED: src/debugmate/knowledge/sync.py:572-603]` `[CITED: https://docs.dify.ai/en/api-reference/documents/create-document-by-text]`

### Pattern 8: Explicit Backend Orthogonal to Result Mode

Keep `ResultMode` exactly `live|replay`. Add `execution_backend: Literal['dify','local_fallback','replay']` (name discretionary) to `DiagnosisRunOutcome`, loaded source manifest, `ResultManifest`, `ResultViewState` and terminal/running failure states. Audio's existing `backend` remains independent. `[VERIFIED: 08-CONTEXT.md D8-13; src/debugmate/results/contracts.py]`

Do not infer backend from `DiagnosisRunOutcome.backend == 'local-rule-v1'`, filenames, audio backend or artifact presence. Update manifest version only if repository compatibility tests require it; otherwise add a required field and migrate every fixture/golden/parser together in one task. `[VERIFIED: src/debugmate/results/loader.py currently branches on outcome.backend; D8-13]`

### Anti-Patterns to Avoid

- **Generic automatic retry:** current `_request()` retries all `TimeoutException`, including ambiguous read/write timeouts. Split retry policy by endpoint and exception class. `[VERIFIED: src/debugmate/adapters/dify.py:56-71; D8-10]`
- **Console-log retrieval proof:** current C04 resource is a separate console-log artifact with a different run fingerprint. Use direct End output for the product chain. `[VERIFIED: evidence/dify-live/2026-08-09/c03-c04]`
- **Raw response persistence:** never log or publish `response.text`, raw outputs, headers or error messages. Parse into an allowlisted bounded model first. `[VERIFIED: D8-16/D8-18]`
- **Local fallback after cloud failure:** once receipt status is `started`, every failure is a cloud failure; a fallback attempt requires a new preview and consent. `[VERIFIED: D8-03]`
- **Backend inferred from media:** Dify diagnosis with SAPI audio fallback is still execution backend `dify`. `[VERIFIED: D8-13; existing TTS fallback contracts]`
- **Success on sync POST:** indexing is asynchronous; wait for batch completion and exact readback. `[CITED: https://docs.dify.ai/en/api-reference/documents/get-document-indexing-status]`
- **Fake cancellation:** stop endpoint is documented only for streaming mode; the frozen blocking UI must disable actions and make no cancellation claim. `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/stop-workflow-task]` `[VERIFIED: D8-12]`

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Diagnosis/schema parsing | Loose dictionaries or best-effort coercion. | Existing Pydantic `DiagnosisRecord`, envelope and semantic validators. `[VERIFIED: repository contracts]` | Existing strict invariants already cover case/fact/evidence/command/privacy relationships. `[VERIFIED: tests/diagnosis]` |
| Retry middleware | Generic decorator retrying POST/timeouts/5xx. | Endpoint-specific HTTPX exception classification plus receipt state. `[CITED: https://www.python-httpx.org/exceptions/]` `[VERIFIED: D8-10/D8-11]` | A retry can duplicate a paid workflow after ambiguous dispatch. `[VERIFIED: D8-10]` |
| Node-log scraper | Dify console HTML/API reverse engineering. | DSL End output of the documented retrieval `result`. `[CITED: https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval]` | Console shape is not the Application API blocking contract. `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]` |
| Vector database or RAG | Local Chroma/FAISS/LangChain path. | Configured Dify dataset plus verified readback. `[VERIFIED: project stack decision]` | Out of Phase 08 and duplicates the locked platform role. `[VERIFIED: .planning/PROJECT.md]` |
| Crypto/secrets | Custom encryption or secrets in manifests. | Existing HMAC approval and SHA-256 fingerprints; environment-held keys. `[VERIFIED: src/debugmate/privacy/approval.py; src/debugmate/settings.py]` | Only non-secret fingerprints belong in evidence. `[VERIFIED: D8-16]` |
| Media pipeline | New Markdown/PNG/TTS/ZIP path. | Existing Phase 4 result service/composer/publisher. `[VERIFIED: src/debugmate/results/service.py]` | Phase 08 must preserve verified partial-result and identity semantics. `[VERIFIED: Phase 4 tests; D8-15]` |
| Git state inspection inside product code | `subprocess`, shell execution or a relaxed command-safety allowlist. | A commandless validator consuming a precomputed, hash-bound tracked-file inventory produced by external QA tooling. `[VERIFIED: failing command-safety test; D8-20]` | Product source has a repository-wide no-process-capability security invariant. `[VERIFIED: tests/diagnosis/test_command_safety.py]` |

**Key insight:** Phase 08 complexity lies in authority, provenance and failure ambiguity, not in generating JSON or media. Reuse existing strict contracts and make Dify outputs smaller and more explicit. `[VERIFIED: repository architecture and D8 decisions]`

## Common Pitfalls

### Pitfall 1: Treating `workflow_run_id`, `task_id` and local `run_id` as interchangeable

**What goes wrong:** raw provider IDs leak or local result identity no longer binds to the accepted diagnosis. `[VERIFIED: D8-16/D8-17]`  
**Avoid:** fingerprint provider IDs, retain `task_id` only transiently, and derive the existing local `run_...` identity from case/facts/routing/diagnosis/build according to current workflow invariants. `[VERIFIED: src/debugmate/diagnosis/workflow.py]`  
**Warning sign:** a manifest contains UUID-looking provider IDs or UI displays a Dify ID. `[VERIFIED: D8-16]`

### Pitfall 2: Reading response JSON before enforcing the cap

**What goes wrong:** an oversized provider body is allocated and parsed before local validation. `[VERIFIED: D8-16 threat]`  
**Avoid:** stream/count bytes first, then decode once under the cap. `[CITED: https://www.python-httpx.org/api/]`  
**Warning sign:** any adapter path calls `response.json()` directly on an unbounded response. `[VERIFIED: current src/debugmate/adapters/dify.py does this]`

### Pitfall 3: Retrying a blocking workflow after `ReadTimeout`

**What goes wrong:** the first workflow may have completed and consumed quota, then a second workflow is created. `[VERIFIED: D8-10]`  
**Avoid:** mark receipt `uncertain`; permit one retry only for `ConnectError`/`ConnectTimeout`. `[CITED: https://www.python-httpx.org/exceptions/]`  
**Warning sign:** `except httpx.TimeoutException` wraps a two-attempt loop. `[VERIFIED: current adapter]`

### Pitfall 4: Assuming blocking mode can be cancelled

**What goes wrong:** UI promises cancellation that the selected API mode cannot provide. `[VERIFIED: D8-12]`  
**Avoid:** disable interactions and state only that the blocking run is in progress. `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/stop-workflow-task]`  
**Warning sign:** a Stop button calls `/workflows/tasks/{task_id}/stop` for blocking mode. `[CITED: same source]`

### Pitfall 5: Proving retrieval with citations copied by the model

**What goes wrong:** a plausible diagnosis can fabricate or copy citations without a current retrieval hit. `[VERIFIED: D8-05; platform/dify/README.md]`  
**Avoid:** export and validate a sanitized projection of `knowledge-retrieval.result`. `[CITED: https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval]`  
**Warning sign:** the accepted envelope contains diagnosis evidence but no direct trace field. `[VERIFIED: D8-05]`

### Pitfall 6: Mixing primary-run and repair-run provenance

**What goes wrong:** repaired diagnosis appears to have generated a new retrieval trace that was never retrieved. `[VERIFIED: D8-09 provenance constraint]`  
**Avoid:** primary attempt owns extraction/retrieval; repair attempt is a bounded candidate transformation and must reproduce the same fact/evidence/build sets. Record both fingerprints. `[VERIFIED: existing semantic equality checks; D8-09]`  
**Warning sign:** repair inputs contain raw remote trace/body or repaired evidence IDs differ. `[VERIFIED: D8-09/D8-16]`

### Pitfall 7: Trusting create/update response as a complete knowledge sync

**What goes wrong:** documents remain indexing/error, metadata is absent, count differs, or retrieval settings drift. `[CITED: https://docs.dify.ai/en/api-reference/documents/get-document-indexing-status]`  
**Avoid:** poll batches, update metadata through its own endpoint, then exact readback. `[CITED: https://docs.dify.ai/en/api-reference/metadata/update-document-metadata-in-batch]`  
**Warning sign:** `readback_verified=True` is accepted from a caller-supplied manifest without live GETs. `[VERIFIED: current execute_sync accepts caller-supplied readback]`

### Pitfall 8: Breaking Phase 4/7 contracts while adding backend truth

**What goes wrong:** replay fixtures, partial TTS results, downloads, stale-session protection or stable UI IDs regress. `[VERIFIED: Phase 4/7 verification contracts]`  
**Avoid:** add one orthogonal execution-backend field end-to-end and keep mode/audio semantics unchanged. `[VERIFIED: D8-13]`  
**Warning sign:** code derives cloud/local from audio backend, filename, mode or artifact presence. `[VERIFIED: D8-13]`

### Pitfall 9: Fixing the command-safety red test by broadening an allowlist

**What goes wrong:** product code gains general process execution capability near untrusted diagnostic commands. `[VERIFIED: tests/diagnosis/test_command_safety.py threat model]`  
**Avoid:** remove `subprocess` from `src/debugmate/dify_live_evidence.py`; move Git inventory acquisition to an external QA script and pass a strict inventory to the pure validator. `[VERIFIED: current 60 passed/1 failed focused run; D8-20]`  
**Warning sign:** `dify_live_evidence.py` remains in `audited_process_modules` or the test allowlist expands. `[VERIFIED: failing test behavior]`

## Code Examples

### Bounded Blocking Response Read

```python
# Sources: HTTPX streaming API and D8-16.
MAX_DIFY_RESPONSE_BYTES = 512 * 1024

with client.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
    classify_status_without_body_leak(response)
    declared = response.headers.get("content-length")
    if declared is not None and int(declared) > MAX_DIFY_RESPONSE_BYTES:
        raise DifyEnvelopeError("workflow_response_too_large")
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        size += len(chunk)
        if size > MAX_DIFY_RESPONSE_BYTES:
            raise DifyEnvelopeError("workflow_response_too_large")
        chunks.append(chunk)
payload = json.loads(b"".join(chunks))
```

`[CITED: https://www.python-httpx.org/api/]` `[VERIFIED: 08-CONTEXT.md D8-16]`

### Retry/Uncertain Classification

```python
# Source: HTTPX exception hierarchy plus locked D8-10 behavior.
try:
    return dispatch_once()
except (httpx.ConnectError, httpx.ConnectTimeout):
    if connection_retry_available:
        return dispatch_once()
    raise CloudFailure("pre_dispatch_transport") from None
except (
    httpx.ReadTimeout,
    httpx.ReadError,
    httpx.WriteTimeout,
    httpx.WriteError,
    httpx.RemoteProtocolError,
):
    receipt_store.mark_uncertain(receipt_id, "ambiguous_workflow_transport")
    raise CloudFailure("ambiguous_timeout") from None
```

`[CITED: https://www.python-httpx.org/exceptions/]` `[VERIFIED: 08-CONTEXT.md D8-10]`

### Strict Reported-or-Not-Reported Usage

```python
# Source: Dify blocking response fields and D8-18.
usage = DifyUsage(
    total_tokens=data["total_tokens"] if "total_tokens" in data else "not_reported",
    total_steps=data["total_steps"] if "total_steps" in data else "not_reported",
    elapsed_time=data["elapsed_time"] if "elapsed_time" in data else "not_reported",
    total_price="not_reported",  # blocking Workflow docs do not promise this field
)
```

`[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]` `[VERIFIED: D8-18]`

### Metadata Write After Indexing

```python
# Source: Dify document metadata batch-update API.
operation = {
    "document_id": runtime_document_id,
    "metadata_list": [
        {"id": field_ids["source_id"], "name": "source_id", "value": source.source_id},
        {
            "id": field_ids["content_sha256"],
            "name": "content_sha256",
            "value": source.content_sha256,
        },
        {
            "id": field_ids["knowledge_build_id"],
            "name": "knowledge_build_id",
            "value": plan.build_id,
        },
    ],
    "partial_update": False,
}
client.post(
    f"datasets/{dataset_id}/documents/metadata",
    json={"operation_data": [operation]},
    headers=knowledge_headers,
)
```

`[CITED: https://docs.dify.ai/en/api-reference/metadata/update-document-metadata-in-batch]`

## Test and Evidence Strategy

### Wave 0: Close Existing Red Debt First

The focused command/evidence run on 2026-08-10 produced `60 passed, 1 failed`; the only failure is `test_command_handling_sources_have_no_shell_execution_capability`, caused by `src/debugmate/dify_live_evidence.py: import subprocess`. `[VERIFIED: local pytest run 2026-08-10]`

Required fix boundary:

- Make `dify_live_evidence.py` a pure commandless validator/capture model. `[VERIFIED: D8-20 and command-safety invariant]`
- Move Git tracked/ignored inventory acquisition to `scripts/` or the PowerShell QA orchestrator, producing a strict sorted relative-path + SHA-256 inventory. `[VERIFIED: repository QA script pattern]`
- Pass that inventory into `validate_published_tree()` and verify it is hash-bound to the candidate evidence set. `[VERIFIED: existing exact-inventory evidence patterns]`
- Do not add `dify_live_evidence.py` to the audited subprocess allowlist. `[VERIFIED: security intent of tests/diagnosis/test_command_safety.py]`

Quick gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/diagnosis/test_command_safety.py tests/platform/test_dify_live_evidence.py -q
```

### Mock and Adversarial Contract Tests

Add tests covering: no network during construction; incomplete config selects `local_fallback`; origin rejection; redirect rejection; immutable upload bytes/MIME/hash; singular image shape and text omission; same user; response/status/body caps; raw-ID fingerprinting; missing/duplicate/oversized trace; forged source/build; usage `not_reported`; typed 400/401/403/413/415/429/5xx; connect-only retry; ambiguous read/write failure; receipt duplicate/restart transitions; one repair; unsafe/privacy terminal behavior; and no artifact publication on invalid envelope. `[VERIFIED: D8-01 through D8-18]`

Recommended files:

```text
tests/cloud/test_settings.py
tests/cloud/test_dify_adapter.py
tests/cloud/test_run_envelope.py
tests/cloud/test_receipts.py
tests/cloud/test_live_workflow.py
tests/knowledge/test_dify_readback.py
tests/results/test_backend_provenance.py
tests/ui/test_dify_live.py
```

### Offline Regression

Run the default suite plus focused Phase 4/7 seams; default pytest already excludes `cloud`, `network`, `ocr`, `browser` and `tts`. `[VERIFIED: pyproject.toml]`

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/privacy tests/diagnosis tests/results tests/ui -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

### Explicit Cloud Service Smoke

The cloud smoke must require explicit app-ready and knowledge-ready gates, must fail rather than skip inside the Phase 08 QA runner, and must never be part of default pytest. It should use one committed synthetic redacted case and verify current app parameters, optional upload, blocking envelope, direct trace, local diagnosis, backend identity and receipt. `[VERIFIED: D8-19; existing tests/diagnosis/test_dify_diagnosis_cloud.py pattern]`

Recommended direct command during development:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m cloud tests/cloud/test_dify_live_cloud.py
```

### Real Edge End-to-End Gate

Create `scripts/run-phase8-live-qa.ps1` using the Phase 7 owned-loopback/JUnit/atomic-promotion pattern. It must reject any skipped test; run exactly one current approved redacted case; verify UI backend `dify`; inspect Markdown/PNG/MP3/ZIP through supported download surfaces; run FFprobe; re-open and verify the ZIP; and only promote a sanitized evidence bundle after all checks pass. `[VERIFIED: D8-17/D8-19; scripts/run-phase7-real-input-qa.ps1 pattern]`

### Evidence Allowlist

Successful published evidence should include only safe projections: request/redaction/upload hashes, receipt/attempt statuses, workflow and optional node fingerprints, DSL/prompt/schema/build hashes, sanitized extraction facts, bounded direct retrieval trace, accepted diagnosis, result/artifact identities, reported-or-not-reported usage, and exact file SHA-256 values. Failed evidence contains an atomic safe code/stage/receipt status and no provider body. `[VERIFIED: D8-16 through D8-18]`

Raw application/dataset/document/upload/run IDs, API keys, approval IDs/signatures/tokens, provider messages/bodies/headers and unredacted input are forbidden. `[VERIFIED: D8-16/D8-17]`

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 9.1.1. `[VERIFIED: local environment]` |
| Config file | `pyproject.toml`. `[VERIFIED: repository]` |
| Quick run | `.\.venv\Scripts\python.exe -m pytest tests/cloud tests/knowledge/test_dify_readback.py tests/results/test_backend_provenance.py tests/ui/test_dify_live.py -q`. `[VERIFIED: recommended Wave 0 contract]` |
| Full suite | `.\.venv\Scripts\python.exe -m pytest -q`. `[VERIFIED: pyproject default exclusions]` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test type | Automated command | File exists? |
|---|---|---|---|---|
| KNOW-03 | 17-source sealed sync, indexing wait, metadata/config/count readback, delete fail-closed. `[VERIFIED: requirement]` | unit + cloud integration | `pytest tests/knowledge/test_coverage_sync.py tests/knowledge/test_dify_readback.py -q` | Existing sync tests; `test_dify_readback.py` Wave 0 gap. |
| KNOW-04 | Same-run direct retrieval trace with source/build binding. `[VERIFIED: requirement]` | contract + cloud | `pytest tests/cloud/test_run_envelope.py tests/diagnosis/test_evidence_binding.py -q` | Evidence binding exists; envelope test Wave 0 gap. |
| DIAG-02 | Strict 1.1.0 candidate and one repair, unsafe terminal. `[VERIFIED: requirement]` | unit + cloud | `pytest tests/diagnosis/test_generation.py tests/cloud/test_live_workflow.py -q` | Generation exists; live workflow Wave 0 gap. |
| MULTI-03 | Verified cloud diagnosis reaches existing MP3 chain. `[VERIFIED: requirement]` | integration + Edge | `pytest tests/results/test_media.py tests/results/test_tts_chain.py -q` plus Phase 08 QA | Existing offline tests; live QA gap. |
| UX-01 | One page shows backend truth and existing multimodal result. `[VERIFIED: requirement]` | UI + browser | `pytest tests/ui/test_dify_live.py -q` plus Phase 08 Edge QA | Wave 0 gap. |
| EVID-01 | Safe receipt/run/usage/artifact evidence and no secrets/raw IDs. `[VERIFIED: requirement]` | adversarial + E2E | `pytest tests/cloud/test_receipts.py tests/cloud/test_live_workflow.py tests/results/test_security_abuse.py -q` | Receipt/live tests Wave 0 gaps. |

### Sampling Rate

- **Per task commit:** relevant focused module plus command-safety test. `[VERIFIED: D8-20 risk]`
- **Per wave merge:** default offline suite and Ruff. `[VERIFIED: project testing convention]`
- **Phase gate:** default suite green, explicit cloud smoke zero-skip, real Edge Phase 08 path zero-skip, FFprobe/ZIP/evidence validators green. `[VERIFIED: D8-19]`

### Wave 0 Gaps

- [ ] Commandless tracked-file inventory seam for `dify_live_evidence.py`. `[VERIFIED: current failing test]`
- [ ] Strict cloud envelope/usage/attempt/receipt models and fixtures. `[VERIFIED: D8-05/D8-10/D8-11/D8-18]`
- [ ] Knowledge API pagination/indexing/metadata readback fixtures. `[VERIFIED: KNOW-03 gap]`
- [ ] Backend provenance migrations across outcome/manifest/view fixtures. `[VERIFIED: D8-13]`
- [ ] Explicit Phase 08 cloud and Edge zero-skip runners. `[VERIFIED: D8-19]`

## Security Domain

Security enforcement is enabled because `.planning/config.json` does not set it to false. `[VERIFIED: .planning/config.json]`

### Applicable ASVS Categories

| ASVS Category | Applies | Standard control |
|---|---|---|
| V2 Authentication | yes | Server-only app/dataset bearer keys; never UI/evidence. `[VERIFIED: D8-16]` `[CITED: https://docs.dify.ai/en/api-reference/guides/errors]` |
| V3 Session Management | yes | Phase 7 session/revision/TTL/one-time preview authority plus durable receipt. `[VERIFIED: Phase 7 verification; D8-11]` |
| V4 Access Control | yes | Approval-only gateway and stable Dify `user` ownership for upload/workflow. `[VERIFIED: src/debugmate/gateway.py]` `[CITED: https://docs.dify.ai/en/api-reference/files/upload-file]` |
| V5 Input Validation | yes | Strict Pydantic models, HTTPS origin allowlist, MIME/size/hash checks, response cap, trace/source/build allowlists. `[VERIFIED: D8-08/D8-16]` |
| V6 Cryptography | yes | Existing HMAC approval and SHA-256 identity/fingerprints; no custom encryption. `[VERIFIED: src/debugmate/privacy/approval.py; D8-16]` |
| V8 Data Protection | yes | Redacted immutable snapshot only; no secrets/raw provider IDs/bodies in UI/evidence/ZIP. `[VERIFIED: D8-16/D8-17]` |
| V13 API/Web Service | yes | Typed status/code handling, bounded response, no redirects, non-idempotent retry restrictions. `[VERIFIED: D8-10/D8-15/D8-16]` `[CITED: https://docs.dify.ai/en/api-reference/guides/errors]` |

### Threat Model Inputs

| Threat pattern | STRIDE | Required mitigation |
|---|---|---|
| Base URL SSRF / credential forwarding to hostile origin | Spoofing / Information Disclosure | Parse and constrain exact HTTPS origin; prohibit userinfo/query/fragment/redirects; explicit test-only origin injection. `[VERIFIED: D8-16]` |
| Duplicate paid workflow after timeout/double-click/restart | Tampering / Denial of Service | Atomic one-time consume, durable receipt, connect-only retry, `uncertain` terminal state, disabled actions. `[VERIFIED: D8-10 through D8-12]` |
| Approved image TOCTOU or MIME confusion | Tampering | Root-confine, rehash, immutable byte snapshot, decode/format verification, matching upload MIME. `[VERIFIED: D8-04/D8-16]` |
| Prompt injection in code/log/image/knowledge | Tampering / Elevation | Treat all content as data, deterministic sanitizer, no tools/actions, local strict schema/fact/evidence/command checks. `[VERIFIED: .planning/PROJECT.md SAFE constraints; D8-08]` |
| Forged citation/retrieval evidence | Tampering | Direct retrieval result projection plus source URL/locator/build allowlist and same-run fingerprint binding. `[VERIFIED: D8-05/D8-08]` |
| Raw provider body/key/remote ID leakage | Information Disclosure | Allowlisted bounded parsing, fingerprint identifiers, safe typed errors, secret scan of UI/evidence/ZIP. `[VERIFIED: D8-16/D8-17]` |
| Oversized/recursive JSON or trace | Denial of Service | Raw byte cap before parse; strict depth/entry/string limits; `extra='forbid'`. `[VERIFIED: D8-16 and chosen caps]` |
| Stale UI completion overwrites newer result | Tampering | Existing session lease, per-case lock, immutable stores and receipt identity; terminal publication requires current lease. `[VERIFIED: Phase 7 verification; D8-11]` |
| Model-produced shell command reaches execution | Elevation | Keep commands inert, strict unsafe-command validator, repository-wide no-process-capability test. `[VERIFIED: tests/diagnosis/test_command_safety.py; D8-20]` |
| Knowledge sync deletes unexpected remote state | Tampering / Denial of Service | Full preflight inventory, sealed plan, explicit delete confirmation, post-sync exact readback. `[VERIFIED: src/debugmate/knowledge/sync.py; D8-06]` |

## Environment Availability

| Dependency | Required by | Available | Version / state | Fallback |
|---|---|---|---|---|
| CPython | all local work | yes | 3.13.5. `[VERIFIED: local probe]` | none |
| HTTPX/Pydantic/Gradio/pytest | adapter/contracts/UI/tests | yes | 0.28.1 / 2.13.4 / 6.20.0 / 9.1.1. `[VERIFIED: importlib.metadata]` | none |
| FFmpeg/FFprobe | MP3 verification | yes | 8.1. `[VERIFIED: local probe]` | existing TTS partial-result semantics |
| `DIFY_API_KEY` | live application call | configured | value not inspected or reported. `[VERIFIED: value-free environment probe]` | construction selects `local_fallback` only when configuration is incomplete; after dispatch no fallback. `[VERIFIED: D8-01/D8-03]` |
| `DIFY_BASE_URL` | live application call | configured | value not reported. `[VERIFIED: value-free environment probe]` | must pass new strict origin validation. `[VERIFIED: D8-16]` |
| `DIFY_DATASET_API_KEY` | real 17-source sync/readback | missing | not configured. `[VERIFIED: value-free environment probe]` | none for KNOW-03 live closure; execution must obtain/configure it without versioning the value. `[VERIFIED: D8-06/D8-16]` |
| App-ready gate | cloud smoke | not enabled | `DEBUGMATE_DIFY_DIAGNOSIS_APP_CONFIGURED != 1`. `[VERIFIED: value-free environment probe]` | offline tests continue; Phase 08 acceptance remains blocked until explicit live setup. `[VERIFIED: D8-19]` |
| Immutable 17-source knowledge build | KNOW-03 | not currently present in repository output | only one local fallback note/snapshot is present; `knowledge/sources.json` still registers 17. `[VERIFIED: filesystem inspection]` | execution must rebuild all 17 before sync. `[VERIFIED: D8-06]` |

**Missing dependency with no acceptance fallback:** `DIFY_DATASET_API_KEY`, current dataset binding/readback attestation and an enabled app-ready gate are required for the one real Phase 08 acceptance run. `[VERIFIED: environment audit; D8-06/D8-19]`

**Available fallback:** ordinary construction may run the existing local chain labeled `local_fallback` when configuration is incomplete, but that path does not satisfy the Phase 08 real Dify acceptance case or KNOW-03. `[VERIFIED: D8-01/D8-19]`

## State of the Art / Current API Drift

| Repository/current older assumption | Current official contract | Planning impact |
|---|---|---|
| Generic 30 s HTTP timeout and retry of all timeouts. `[VERIFIED: src/debugmate/adapters/dify.py]` | Blocking workflow has a documented 100 s Cloudflare limit; HTTPX distinguishes connect/read/write/pool failures. `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]` `[CITED: https://www.python-httpx.org/exceptions/]` | Use split timeouts and connect-only retry; classify ambiguous response/write failures as `uncertain`. |
| Direct `response.json()` and only `outputs.diagnosis`. `[VERIFIED: current adapter]` | Blocking response documents task/run IDs, status, outputs, elapsed time, tokens and steps. `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]` | Bound bytes first and parse a strict run envelope plus reported usage. |
| C04 console log as direct retrieval evidence. `[VERIFIED: retained evidence]` | Retrieval node exposes documented `result` array to downstream workflow nodes. `[CITED: https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval]` | Export a sanitized projection in the same End output. |
| Create/update payload includes `doc_metadata`; no live GET readback. `[VERIFIED: current sync.py]` | Current docs expose separate metadata field/update APIs and asynchronous batch indexing. `[CITED: https://docs.dify.ai/en/api-reference/metadata/update-document-metadata-in-batch]` `[CITED: https://docs.dify.ai/en/api-reference/documents/get-document-indexing-status]` | Separate text indexing, metadata update and exact readback stages. |
| Product evidence validator shells out to Git. `[VERIFIED: src/debugmate/dify_live_evidence.py]` | Repository command-safety invariant forbids process capability outside the separately audited media boundary. `[VERIFIED: tests/diagnosis/test_command_safety.py]` | Make product validator pure; external QA supplies a strict tracked inventory. |

## Prescriptive Task Boundaries for the Planner

### Task A — Wave 0 safety and strict contracts

**Own:** `src/debugmate/dify_live_evidence.py`, external QA inventory helper/script, command-safety/evidence tests, new envelope/receipt model tests. `[VERIFIED: D8-20 and Wave 0 gaps]`  
**Do not touch:** DSL, media, UI styling. `[VERIFIED: phase boundary]`  
**Exit:** focused 61-test command/evidence set fully green and pure validator consumes strict inventory. `[VERIFIED: current baseline 60/1]`

### Task B — Knowledge rebuild/sync/readback

**Own:** `src/debugmate/knowledge/sync.py`, knowledge CLI/tests, sanitized readback attestation; rebuild 17 sources. `[VERIFIED: D8-06]`  
**Do not touch:** diagnosis/result/UI.  
**Exit:** zero-delete or explicitly confirmed sealed plan, all batches completed, exact 17-document metadata/hash/config readback, no raw IDs in evidence. `[VERIFIED: KNOW-03/D8-06/D8-16]`

### Task C — Dify DSL and adapter

**Own:** `platform/dify/app.dsl.yml`, platform README/DSL tests, `settings.py`, `adapters/base.py`, `adapters/dify.py`, `gateway.py`, cloud adapter tests. `[VERIFIED: integration seams]`  
**Do not touch:** Phase 4 media generators.  
**Exit:** fresh exported DSL with bounded explicit envelope, immutable verified upload, origin/body caps, typed error/usage and connect-only retry. `[VERIFIED: D8-04/D8-05/D8-07/D8-10/D8-16/D8-18]`

### Task D — Live orchestration, receipts and local validation

**Own:** new cloud workflow/receipt modules, minimal `diagnosis/generation.py`/`diagnosis/workflow.py` extensions, `results/service.py`, outcome evidence tests. `[VERIFIED: D8-08/D8-09/D8-11]`  
**Do not touch:** result rendering logic.  
**Exit:** approved input produces either one strict `DiagnosisRunOutcome` or one safe typed cloud failure; duplicate/uncertain/repair paths are adversarially proven. `[VERIFIED: D8-03/D8-08 through D8-11]`

### Task E — Backend truth, construction and UI regression

**Own:** `results/contracts.py`, publisher/loader fixtures, `ui/serve.py`, minimal `ui/app.py` copy/progress/action state, relevant tests. `[VERIFIED: D8-01/D8-13 through D8-15]`  
**Do not touch:** visual redesign or stable media components.  
**Exit:** `live` mode reports `dify` or `local_fallback`, replay reports `replay`, cloud failures never expose artifacts, existing partial media remains valid, Phase 7 stale-session controls pass. `[VERIFIED: D8-13/D8-15]`

### Task F — Current live acceptance evidence

**Own:** explicit cloud test, Phase 08 PowerShell QA runner, sanitized phase8 evidence, platform README/capability references only as needed. `[VERIFIED: D8-17/D8-19]`  
**Do not touch:** Phase 9 representative comparisons or Phase 10 PPTX/MP4/SRT/screenshots. `[VERIFIED: Deferred Ideas]`  
**Exit:** one zero-skip real redacted Edge/Dify chain with strict envelope, 17-source attestation, Markdown/PNG/MP3/ZIP hashes and no secret/raw-ID findings. `[VERIFIED: D8-17/D8-19]`

## Open Questions / Mandatory Live Checks

1. **Does the current published app still accept the singular `image_input` object from the exported `type: file` DSL?**  
   What is known: the locked decision and retained C03 live capture use the singular object; generic current API docs describe file variables as arrays. `[VERIFIED: D8-04; retained C03 evidence]` `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]`  
   Execution check: call Get App Parameters, upload one committed redacted PNG with the stable user, then run the exact exported singular shape once. Fail closed and refresh DSL/tests if the published app rejects it. `[CITED: https://docs.dify.ai/en/api-reference/applications/get-app-parameters]`

2. **What exact keys does the current Knowledge Retrieval `result` provide for this dataset?**  
   What is known: official docs guarantee an array with content, metadata, title and other attributes but do not freeze every nested key. `[CITED: https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval]`  
   Execution check: use one bounded workflow debug/live output, update the sanitizer allowlist to observed keys, export fresh DSL, and retain only the sanitized projection/hash. Never depend on console logs for product acceptance. `[VERIFIED: D8-05/D8-07]`

3. **Which current metadata field IDs and document metadata serialization does the configured dataset return?**  
   What is known: official endpoints support custom fields, batch document updates and list/readback. `[CITED: https://docs.dify.ai/en/api-reference/metadata/create-metadata-field]` `[CITED: https://docs.dify.ai/en/api-reference/metadata/update-document-metadata-in-batch]`  
   Execution check: create/list fields, write one synthetic document's hashes, list/get it, then proceed with the sealed 17-source sync only if roundtrip equality holds. `[VERIFIED: D8-06 fail-closed requirement]`

4. **Does Dify report any cost/price field for the current provider/run?**  
   What is known: current blocking Workflow docs promise total tokens/steps/elapsed time but not price. `[CITED: https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow]`  
   Execution check: accept only documented/allowlisted numeric fields actually present; otherwise store `not_reported`, never `0`. `[VERIFIED: D8-18]`

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| — | None. All implementation claims are tied to locked context, inspected repository behavior or current official documentation; unresolved provider-specific shapes are listed as mandatory live checks rather than assumptions. | — | — |

## Sources

### Primary — Repository (HIGH confidence)

- `08-CONTEXT.md` — all locked decisions, discretion and deferred scope. `[VERIFIED: repository]`
- `platform/dify/app.dsl.yml` and retained C03/C04/C06 evidence — current exported workflow and historical capability shapes. `[VERIFIED: repository]`
- `src/debugmate/adapters/dify.py`, `gateway.py`, `knowledge/sync.py`, diagnosis/result/UI modules and relevant tests — current seams and gaps. `[VERIFIED: repository]`
- `knowledge/sources.json` — canonical 17-source registry. `[VERIFIED: repository]`
- Local focused pytest on 2026-08-10 — 60 passed, 1 command-safety failure. `[VERIFIED: local execution]`

### Primary — Official Documentation (HIGH confidence)

- [Dify Run Workflow](https://docs.dify.ai/en/api-reference/workflow-runs/run-workflow) — blocking request/response, 100 s limit, file references, task/run and usage fields.
- [Dify Upload File](https://docs.dify.ai/en/api-reference/files/upload-file) — multipart upload, user ownership, limits and returned MIME/size/ID.
- [Dify Stop Workflow Task](https://docs.dify.ai/en/api-reference/workflow-runs/stop-workflow-task) — streaming-only cancellation.
- [Dify Errors and Rate Limits](https://docs.dify.ai/en/api-reference/guides/errors) — error envelope/status/code and generic retry guidance.
- [Dify Knowledge Retrieval node](https://docs.dify.ai/en/cloud/use-dify/nodes/knowledge-retrieval) — direct `result` variable and retrieval settings.
- [Dify Create Document by Text](https://docs.dify.ai/en/api-reference/documents/create-document-by-text) and [Indexing Status](https://docs.dify.ai/en/api-reference/documents/get-document-indexing-status) — asynchronous document indexing.
- [Dify Get Knowledge Base](https://docs.dify.ai/en/api-reference/knowledge-bases/get-knowledge-base) and [List Documents](https://docs.dify.ai/en/api-reference/documents/list-documents) — count/config/document readback.
- [Dify Create Metadata Field](https://docs.dify.ai/en/api-reference/metadata/create-metadata-field) and [Batch Update Document Metadata](https://docs.dify.ai/en/api-reference/metadata/update-document-metadata-in-batch) — documented metadata write path.
- [HTTPX Exceptions](https://www.python-httpx.org/exceptions/), [Timeouts](https://www.python-httpx.org/advanced/timeouts/) and [Streaming API](https://www.python-httpx.org/api/) — transport classification and bounded response mechanics.

## Metadata

**Confidence breakdown:**

- Standard stack: **HIGH** — exact installed/pinned versions and official API endpoints were verified. `[VERIFIED: local environment; official docs]`
- Architecture: **HIGH** — follows locked Phase 08 decisions and existing Phase 4/7 seams. `[VERIFIED: repository/context]`
- Dify published-app field shape: **MEDIUM-HIGH** — historical singular image call is proven, but current generic docs and provider-specific retrieval metadata require the listed current live smokes. `[VERIFIED: retained evidence]` `[CITED: official docs]`
- Knowledge synchronization: **HIGH** for required sequence; **MEDIUM-HIGH** until configured-dataset metadata roundtrip is run. `[CITED: official Knowledge API docs]`
- Pitfalls/security: **HIGH** — current red test, code paths and official timeout/cancellation behavior are directly verified. `[VERIFIED: tests/code]` `[CITED: official docs]`

**Research date:** 2026-08-10  
**Valid until:** 2026-08-17 for Dify Application/Knowledge API details; repository architecture remains valid until Phase 08 implementation changes the listed contracts. `[VERIFIED: Dify docs last-modified dates in July 2026; fast-moving cloud API]`
