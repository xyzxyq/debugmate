---
phase: 03-traceable-diagnosis-workflow
status: issues_found
depth: deep
reviewed_at: 2026-07-12
files_reviewed: 41
original_findings:
  closed: 2
  partially_closed: 2
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
---

# Phase 3 Software Quality Re-review

## Result

Phase 3 is still not clean after the first fix iteration. The canonical `CaseFact`
checks and ordinary correction-stage presentation are materially improved, and the
full offline suite remains green. However, the environment extraction fix does not
handle the project's established key/value environment shape, and the shared outcome
validator still permits forged correction lineage and top-level revision/hash state.

## Findings

### WARNING 1 — Structured environment keys are discarded before extraction

**Files:** `src/debugmate/diagnosis/providers.py:111-114`,
`src/debugmate/diagnosis/providers.py:180-189`

The source hash correctly binds the complete environment mapping, but
`_text_candidates()` concatenates only mapping values. This discards the semantic keys
that identify otherwise bare values. Existing Phase 2 inputs use shapes such as
`{"PYTHON": "3.13.5"}` and `{"python": "3.13"}`; the analogous
`{"PYTHON": "3.13.5", "DEVICE": "cpu"}` produces no candidates at all. The new
tests avoid the defect by putting `Version:` and `Device:` labels inside a single
`runtime` value, which is not the established input contract.

Consequences:

- approved structured environment data remains unavailable to sufficiency and routing;
- a common environment-only submission is source-hashed but yields no version/device
  facts, so it can still stop as information-poor;
- the original environment finding is only partially closed despite the passing
  environment tests.

**Reproduction:** invoking `ProductionExtractionProvider.extract()` with
`environment={"PYTHON": "3.13.5", "DEVICE": "cpu"}` returned `candidates=[]` while
the environment source hash was present.

**Action:** serialize each environment entry into a deterministic key-aware extraction
view (for example `PYTHON: 3.13.5` and `DEVICE: cpu`) and preserve locators that identify
the corresponding mapping entry. Map the supported environment keys explicitly to the
six fields rather than relying only on labels embedded inside values. Add regression
tests using the Phase 2 `PYTHON`/`python` shape and a separate `DEVICE` key.

### WARNING 2 — Shared outcome validation still accepts forged revision and correction lineage

**Files:** `src/debugmate/diagnosis/workflow.py:168-194`,
`src/debugmate/diagnosis/workflow.py:421-433`,
`src/debugmate/evidence.py:475-478`, `src/debugmate/evidence.py:589-620`

`validate_diagnosis_outcome()` recomputes run identities from the nested `facts`, but it
does not require top-level `revision`/`facts_sha256` to equal that nested immutable
revision. Those checks remain private to evidence publication. Consequently,
`DiagnosisWorkflow.rerun()` accepts a previous outcome whose top-level revision and
facts hash were forged, because rerun calls only the incomplete shared validator.

The same validator treats any syntactically valid `source_run_id` plus the three fixed
inherited stages as valid correction lineage. It does not require a corrected revision,
an applied correction, a distinct source run, or consistency with extraction/fact
history. Evidence publication therefore accepts and records a revision-0, zero-
correction outcome as `facts_corrected`, with an arbitrary source run ID.

**Reproductions:** both were confirmed against the fixed tree:

1. `validate_diagnosis_outcome()` accepted copies with `revision=999` and with an
   all-`f` top-level `facts_sha256`; `rerun()` then accepted the combined forged outcome.
2. A normal completed revision-0 outcome modified to declare inherited stages,
   `facts_corrected`, and `source_run_id=run_ffff...` was successfully published; its
   manifest reported `facts_corrected=completed` despite zero applied corrections.

**Action:** make the shared validator the single complete semantic boundary: compare
top-level revision/hash to `outcome.facts`, validate extraction/fact provenance where
present, and require inherited correction lineage to have `revision >= 1`, at least one
canonical correction, a distinct source run ID, and an allowed correction-stage path.
If arbitrary imported lineage must be supported, require a separately verified source
manifest rather than accepting an unbound run-shaped string. Add direct validator,
rerun, and publication tamper tests for all of these cases.

## Original Finding Closure

1. **Environment binding:** partially closed — full mapping is hashed, but established
   structured key/value inputs are not extracted.
2. **Publication identity and stage history:** partially closed — run/idempotency and
   version checks exist, but the shared validator and correction lineage remain
   bypassable as described above.
3. **Canonical `CaseFact`:** closed — normalized values, stable IDs, privacy scanning,
   and deterministic provenance ordering are enforced at reconstruction.
4. **Inherited rerun stages:** presentation is improved, but semantic lineage validation
   remains part of Warning 2.

## Verification Evidence

- `python -m pytest -q -m "not cloud and not ocr"`: **442 passed, 22 deselected**.
- `python -m ruff check src tests`: **passed**.
- `python -m pip check`: **passed**.
- `git diff --check`: **passed** apart from the pre-existing line-ending notice for
  `.planning/config.json`.

## Required Tests Before Clean Status

1. Key-aware environment extraction for existing `PYTHON`/`python` and `DEVICE` maps.
2. Direct shared-validator and rerun rejection of top-level revision/facts-hash tampering.
3. Publication rejection of revision-0/no-correction inherited lineage, self-source
   lineage, and arbitrary unverified source-run lineage.
