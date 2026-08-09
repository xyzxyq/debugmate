# Phase 8: Dify Unified Live Chain - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Connect the Phase 7 approved, redacted real-input snapshot to the published Dify workflow, strictly validate the same-run extraction/retrieval/diagnosis response locally, and feed the verified outcome into the existing Markdown, PNG, MP3, ZIP and Gradio result pipeline. This phase proves one current synthetic-but-real end-to-end Dify case. Representative-case/V1–V4 evaluation remains Phase 9; final screenshots, PPTX, subtitles and video remain Phase 10.

</domain>

<decisions>
## Implementation Decisions

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

### Agent discretion
- Exact class/module names for the run envelope, durable receipt and safe error taxonomy.
- Whether the receipt is an append-only JSON record or another repository-consistent atomic local format.
- Exact bounded limits for trace entries, response bytes and safe error detail, provided tests prove fail-closed behavior.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product and phase truth
- `.planning/PROJECT.md` — privacy, cost, reproducibility, multimodal and media-last constraints.
- `.planning/REQUIREMENTS.md` — KNOW-03/04, DIAG-02, MULTI-03, UX-01 and EVID-01 acceptance.
- `.planning/ROADMAP.md` — Phase 8 boundary and success criteria.
- `.planning/phases/07-real-input-privacy-ui/07-CONTEXT.md` — approval, revision, local-only and replay decisions inherited by Phase 8.
- `.planning/phases/07-real-input-privacy-ui/07-VERIFICATION.md` — verified Phase 7 baseline and exact integration boundary.

### Dify and knowledge contracts
- `platform/dify/app.dsl.yml` — current published workflow variables and node graph.
- `platform/dify/README.md` — capability/evidence truth and retrieval-proof rules.
- `platform/dify/capability-matrix.json` — isolated C01–C07 capability baseline.
- `contracts/diagnosis-record-v1.1.schema.json` — strict cloud/local diagnosis contract.
- `knowledge/sources.json` — canonical 17-source registry.
- `src/debugmate/knowledge/sync.py` — sealed sync/readback/delete-safety contract.

### Local pipeline
- `src/debugmate/gateway.py` — approved-input cloud boundary.
- `src/debugmate/adapters/dify.py` — upload/workflow adapter and retry behavior to correct.
- `src/debugmate/diagnosis/workflow.py` — strict outcome validation and identity rules.
- `src/debugmate/diagnosis/generation.py` — one-repair budget and privacy/command validation.
- `src/debugmate/results/service.py` — verified outcome publication and multimodal result composition.
- `src/debugmate/results/contracts.py` — result/backend/state truth contracts.
- `src/debugmate/ui/app.py` and `src/debugmate/ui/serve.py` — Phase 7 approval/UI construction seam.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 7 preview store and `ApprovedRedactedInput`: revision-bound one-time network authorization.
- `CloudGateway` and Dify adapter: thin current cloud seam requiring DSL-aligned image and envelope updates.
- Diagnosis validators and generation repair budget: local final authority for provider output.
- Result service/outcome store/composer: already verified Markdown/PNG/MP3/ZIP pipeline.
- Knowledge sync planner/readback: deterministic 17-source rebuild and deletion guard.
- Existing live evidence validators and C03/C04/C06/C07 bundles: safe fingerprint and atomic evidence patterns.

### Established Patterns
- Server-only secrets and approval material; value-free, SHA-bound evidence.
- One authoritative run identity and immutable terminal publication.
- Typed failure and honest partial output; no silent success or unknown-as-zero usage.
- Live network tests are explicit markers and never part of default offline execution.

### Integration Points
- `build_demo()` consumes the approved preview token and calls the selected service.
- `serve.py` chooses configured Dify or explicit local fallback at construction without network I/O.
- The Dify backend returns a validated envelope to the same `DiagnosticResultService` used by replay/local paths.
- Final view state and ZIP manifest carry verified backend/run/knowledge identities.

</code_context>

<specifics>
## Specific Ideas

- The UI should say “Dify 工作流运行中” rather than expose speculative per-node progress.
- A cloud attempt that may have reached Dify but timed out is `uncertain`; it is never auto-retried.
- `not_reported` is the only truthful cost/token value when the API omits usage.

</specifics>

<deferred>
## Deferred Ideas

- Phase 9: current 3–5 representative cases, privacy/degradation matrix and V1–V4 same-case prompt comparison.
- Phase 10: final course screenshots, PPTX, narration script, SRT, MP4, manifests and final human flip/listen QA.

</deferred>

---

*Phase: 08-dify-unified-live-chain*
*Context gathered: 2026-08-10*
