---
phase: 03
slug: traceable-diagnosis-workflow
status: verified
threats_open: 0
asvs_level: 1
created: 2026-07-12
---

# Phase 03 — Security

> Phase 3 threat-model verification. This audit verifies only the threats declared in plans 03-01 through 03-06 and their summary flags.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Approval to workflow | A signed, fresh approval and root-confined screenshot binding must verify before any stage or provider call. | Redacted input, HMAC proof, path and SHA-256 |
| OCR/VLM to facts | External extraction output remains candidate data until strict provenance, locator, normalization and privacy checks pass. | Candidate fields, confidence, bbox and image SHA-256 |
| Facts to policy | Deterministic sufficiency and routing policy controls questions, uncertainty and category selection. | Immutable fact revision and stable fact IDs |
| Retrieval to diagnosis | Only a validated trusted build/source/locator trace can become an evidence anchor or support link. | Summary-only retrieval trace and stable evidence IDs |
| Model to local authority | Candidate JSON is untrusted; local schema, semantic, privacy and command validation controls publication with one repair maximum. | Bounded candidate payload and safe issue codes |
| Outcome to evidence | Only allowlisted summaries from a strictly revalidated outcome may be atomically published to an immutable run directory. | Facts/routing/retrieval/diagnosis summaries and manifest hashes |
| Correction to rerun | A correction must match the exact case, revision, facts hash, fact ID, field and old-value hash. | Correction overlay and immutable next revision |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T3-01 | Tampering / Spoofing | Diagnosis contract and support graph | mitigate | Strict frozen Pydantic models, `extra=forbid`, stable-ID uniqueness and cross-reference validation; Schema snapshot/hash tests reject coercion, extras, dangling IDs and unsupported grounded claims. Evidence: `contracts.py`; `test_contract_v11.py`. | closed |
| T3-02 | Elevation of privilege | Command recommendations | mitigate | Command steps are inert structured data; chaining, substitution, destructive/download-execute constructs are rejected, and an AST guard proves the product source has no shell/subprocess execution capability. Evidence: `contracts.py`; `test_command_safety.py`. | closed |
| T3-03 | Tampering / Information disclosure | OCR/VLM extraction and correction | mitigate | Field enum allowlist, strict source/locator contracts, bbox/image dimensions and screenshot hash binding, local normalization/privacy rescan, candidate-only VLM port, and optimistic-lock corrections. Prompt-like OCR/VLM values remain inert and unsafe promotion fails closed. Evidence: `extraction.py`, `providers.py`, `correction.py`; extraction/correction tests. | closed |
| T3-04 | Denial of service / Integrity | Sufficiency state machine | mitigate | Versioned deterministic matrices cap questions at three, deduplicate by field, permit one follow-up round, and stop with typed `insufficient_information` before retrieval/generation. Evidence: `sufficiency.py`, `workflow.py`; `test_sufficiency.py`, `test_workflow_e2e.py`. | closed |
| T3-05 | Tampering | Deterministic router | mitigate | Pure local rules, thresholds, explicit conflict handling and `unknown` fallback prevent prompt-like facts or low-score model suggestions from overriding policy. Evidence: `routing.py`; `test_router.py`. | closed |
| T3-06 | Spoofing / Tampering | Retrieval evidence binding | mitigate | Strict RetrievalTrace revalidation binds exact case, trusted build, source URL and locator before deterministic evidence-ID creation; support links require known fact/evidence IDs and grounded claims require exact support. Raw chunks/provider bodies are excluded. Evidence: `evidence_binding.py`; `test_evidence_binding.py`. | closed |
| T3-07 | Tampering / Information disclosure | Candidate generation and repair | mitigate | Local JSON/schema/semantic/privacy/command validation is authoritative; failures expose bounded code/pointer pairs only; unsafe command/privacy failures are not repaired; repair budget is exactly one and second failure is typed. Adapter tests prove undocumented response bodies are not exposed. Evidence: `generation.py`, candidate adapters; `test_generation_repair.py`. | closed |
| T3-08 | Spoofing / Replay | Approval-gated workflow and rerun | mitigate | HMAC comparison, 30-minute freshness, configured key, root-confined path and live screenshot rehash run before `input_approved` and before all providers. Forged/stale/wrong/missing key, unsafe/missing/changed screenshot all produce zero extraction/retrieval/generation calls. Reruns derive new revision/facts hash/idempotency/run identities. Evidence: `approval.py`, `workflow.py`; `test_workflow_e2e.py`, `test_approval_gateway.py`. | closed |
| T3-09 | Information disclosure / Tampering | Evidence publisher | mitigate | Strict outcome/lineage revalidation, artifact allowlist, summary-only serialization, privacy rescan, temporary sibling publication, immutable run-specific directories, final manifest artifact hashes and verifier tamper detection. Failure aborts remove temporary state; duplicate runs cannot overwrite; corrected runs preserve both bundles. Evidence: `evidence.py`; `test_workflow_evidence.py`, `test_evidence.py`. | closed |

*Status: open · closed*  
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Verification Evidence

- Focused adversarial suite: `159 passed` across contract, command safety, extraction/correction, routing/sufficiency, evidence binding, repair, approval workflow and evidence publication tests.
- Full offline suite: `429 passed, 22 deselected` using `pytest -m "not cloud and not ocr"`.
- Static quality gate: Ruff passed for Phase 3 source/tests; `git diff --check` reported no Phase 3 patch error (only the pre-existing `.planning/config.json` line-ending warning).
- Source capability search found no product `subprocess`, `os.system`, `Popen`, `shell=True`, `eval`, `exec`, `Start-Process`, or `Invoke-Expression` execution path; the only `run` match is the domain retrieval function and CLI call.
- Six executed summaries contain no unresolved threat flag; `03-01-SUMMARY.md` explicitly reports no unresolved issue and the remaining summaries add no open security disposition.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-12 | 9 | 9 | 0 | gsd-security-auditor |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-12
