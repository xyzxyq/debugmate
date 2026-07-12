---
phase: 03-traceable-diagnosis-workflow
status: issues_found
depth: deep
reviewed_at: 2026-07-12
files_reviewed: 41
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
---

# Phase 3 Software Quality Review

## Result

Phase 3 is not clean. The full offline test suite and Ruff pass, and the main happy-path workflow is deterministic, but three correctness/traceability gaps remain at public boundaries.

## Findings

### WARNING 1 — Approved `environment` content is never extracted or source-bound

**Files:** `src/debugmate/diagnosis/providers.py:103-109`, `src/debugmate/diagnosis/providers.py:173-178`

`ProductionExtractionProvider.extract()` hashes only `error_text`, `code`, and the optional screenshot. `_text_candidates()` likewise iterates only `error_text` and `code`. The approved input's `environment` field is ignored even though version/device/package facts are commonly supplied there and Phase 3's sufficiency matrices explicitly depend on those fields.

Consequences:

- a complete approved submission can incorrectly stop at `needs_information` or `insufficient_information`;
- changes to environment data do not change `ExtractionRecord.source_hashes`, `extraction_id`, facts, or run identity;
- the diagnosis can be generated without audit evidence that the submitted environment was considered.

**Action:** include `environment` in both `source_hashes` and `_text_candidates()` using `TextLocator(input_field="environment", ...)`. Add an end-to-end test where the only `Version:`/`Device:` evidence is in `environment`, plus a test proving an environment-only change changes extraction/facts/run identity.

### WARNING 2 — Evidence publication trusts caller-supplied run identity and stage history

**Files:** `src/debugmate/evidence.py:467-501`, `src/debugmate/evidence.py:549-617`, `src/debugmate/diagnosis/workflow.py:65-87`, `src/debugmate/diagnosis/workflow.py:107-120`

`publish_diagnosis_evidence()` strictly reconstructs `DiagnosisRunOutcome`, but `_validate_diagnosis_lineage()` never recomputes `_identities()` and never validates `idempotency_key`, `run_id`, or the legal `completed_stages` sequence for the declared status. It also writes module constants for prompt/schema versions rather than checking the outcome fields. A syntactically valid imported `DiagnosisRunOutcome` can therefore select an arbitrary valid-looking run directory, claim impossible stages (for example `published` on a blocked outcome), or carry version metadata that is silently replaced in the manifest.

This weakens the evidence bundle's core claim that directory identity and node history are derived from the immutable workflow state. The JSON/CLI publication boundary makes this more than an internal-only concern.

**Action:** move identity derivation and stage-transition validation into a shared public validator. Before `EvidenceBundle.begin_run`, recompute and constant-time compare `run_id` and `idempotency_key`; validate status-specific field presence and the exact allowed stage prefix; require outcome schema/prompt/workflow versions to match the publisher contract (or explicitly migrate them). Add tamper tests for each field.

### WARNING 3 — `CaseFact` accepts non-canonical stable IDs and inconsistent provenance

**Files:** `src/debugmate/diagnosis/extraction.py:186-220`, `src/debugmate/diagnosis/extraction.py:237-256`, `src/debugmate/diagnosis/correction.py:61-127`

`CaseFacts` verifies only that its aggregate hash matches the serialized payload and that fact IDs are sorted/unique. `CaseFact` does not verify `fact_id == fact_id_for(field_id, normalized value)`, does not normalize/reject unsafe values at reconstruction, and does not validate provenance IDs/source ordering. A caller can construct a self-consistent hash over a forged fact ID; correction and rerun then accept that ID as the stable target, while downstream support links and evidence use it as authoritative.

This contradicts the Phase 3 stable-ID contract and means strict Pydantic reconstruction is not equivalent to semantic validation.

**Action:** add a `CaseFact` validator for canonical normalized value and fact ID, validate/deduplicate/sort provenance candidate IDs and source kinds, and privacy-scan values at the public `CaseFacts` reconstruction boundary. If legacy/imported facts require exceptions, use a distinct migrated model rather than weakening the current fact contract. Add JSON-boundary tests with a recomputed `facts_sha256` over a forged ID/value.

### INFO 1 — Corrected reruns report extraction as newly completed

**File:** `src/debugmate/diagnosis/workflow.py:313-322`

`rerun()` does not invoke extraction, but starts its stage list with `input_approved`, `extracted`, and `facts_confirmed`, and reuses the original `ExtractionRecord`. This is understandable as lineage, but the manifest's `node_states` labels every entry `completed`, so consumers cannot distinguish “reused from prior revision” from “executed in this run.”

**Action:** represent reused stages explicitly (`reused`/`inherited`) or start reruns at `facts_corrected` and retain the source run/extraction ID as lineage metadata.

## Clean Evidence

- `python -m pytest -q -m "not cloud and not ocr"`: **429 passed, 22 deselected**.
- `python -m ruff check src tests`: **passed**.
- Contract generation performs schema, privacy, semantic fact/evidence set, category, and knowledge-build checks with at most one repair.
- Sufficiency is bounded to one follow-up round and at most three deterministic questions.
- Correction uses optimistic locking and preserves immutable revision/facts hashes.
- Evidence publication is atomic, allowlisted, privacy-scanned, hash-manifested, and rejects Phase 4 audio artifacts.

## Test Gaps to Close

1. Environment-only extraction and environment-change identity tests.
2. Imported outcome tampering tests for run/idempotency IDs, versions, stages, and status-specific fields.
3. Self-consistent forged `CaseFact` ID/value/provenance tests at JSON and rerun boundaries.
4. Manifest semantics for inherited correction-rerun stages.
