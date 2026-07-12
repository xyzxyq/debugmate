---
phase: 03-traceable-diagnosis-workflow
status: issues_found
depth: deep
reviewed_at: 2026-07-13
reviewed_commits:
  - 42bdbfd
  - ff2487f
files_reviewed: 41
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
---

# Phase 3 Contract and Regression Re-review

## Result

Commits `42bdbfd` and `ff2487f` close the two previously reported public-boundary
bypasses. Workflow outcomes now require their exact extraction record, matching extraction
candidates cannot be relabelled as user-only facts, correction IDs and reasons are
canonical, correction revisions are contiguous, and corrected publication proves each
latest transition against a verified immutable source bundle.

The phase is nevertheless **not clean**. One normal workflow supported by the public domain
model is internally inconsistent: a legitimate user fact created by the bounded follow-up
round can be corrected, but the resulting revision cannot pass the shared outcome validator
or evidence publisher.

## Finding

### WARNING 1 - A legitimate follow-up user fact cannot be corrected and republished

**Files:** `src/debugmate/diagnosis/extraction.py:401-419`,
`src/debugmate/diagnosis/workflow.py:470-485`

`apply_followup_answers()` intentionally creates facts with no extraction candidate,
`provenance_candidate_ids=[]`, and `source_kinds=[user]`. This is the correct representation
for an answer supplied after extraction. `apply_correction()` also accepts such a fact and
creates a valid-looking next revision. However, `validate_facts_against_extraction()` handles
every corrected field by looking up the first correction's old value only in
`extraction.candidates`; when the original fact was a follow-up answer, that lookup is empty
and validation raises `fact correction provenance does not bind its source value`.

The failure occurs after `DiagnosisWorkflow.rerun()` has already returned the new outcome,
so callers receive an object that the public validator and publisher reject. This breaks the
explicit combination of bounded follow-up facts and correction reruns and prevents a normal
revision-1 follow-up / revision-2 correction chain from being serialized and published.

**Confirmed reproduction:** run the committed `insufficient_information` fixture with
`followup_answers={version: "3.13.5"}`. The result is revision 1 and contains a user-only
`version` fact. Correct that fact to `3.13.6` through `DiagnosisWorkflow.rerun()`. The method
returns a revision-2 `needs_information` outcome, but `validate_diagnosis_outcome()` rejects
it with `ValueError: fact correction provenance does not bind its source value`; publication
therefore also cannot succeed.

**Action:** model the initial source of a correction explicitly. For the first correction on
a field, accept either (a) an exact extraction candidate set whose value/fact ID matches the
old correction state, or (b) an existing provenance-free, user-only fact from the verified
source revision. The latter must still be proven through the source bundle during
publication, not inferred merely from an absent candidate. Add an end-to-end round-trip test
covering follow-up revision 1, correction revision 2, JSON model round trips, source bundle
publication, corrected bundle publication, and `verify_bundle()` for both bundles. Also
make `rerun()` validate its newly assembled outcome before returning so future internal
contract mismatches fail at the producing boundary.

## Verified Closures and Invariants

- Every Phase 3 workflow outcome requires an `ExtractionRecord`; removing it is rejected.
- Extracted facts require the complete exact candidate-ID set and exact source-kind set.
- Legitimate uncorrected follow-up facts remain accepted as provenance-free `user` facts.
- `CaseFact` IDs remain canonical over normalized field/value pairs.
- Correction reasons are privacy-scanned and hash-bound; correction IDs are deterministic
  over canonical immutable correction fields.
- Same-field revision 0 -> 1 -> 2 correction chains validate, serialize, publish, and verify.
- Revision gaps, duplicated corrections, altered IDs/reasons/base hashes, and incomplete
  correction prefixes are rejected.
- Corrected publication verifies source manifest identity, correction prefix, source fact,
  resulting fact, unchanged sibling facts, and allowed provenance/source transitions.
- Normal workflow outcomes and correction outcomes survive strict Pydantic JSON round trips.

## Verification Evidence

- Focused extraction/sufficiency/workflow/evidence suite: **81 passed**.
- Full offline suite, `python -m pytest -q -m "not cloud and not ocr"`:
  **462 passed, 22 deselected**.
- `python -m ruff check src tests`: **passed**.
- `python -m pip check`: **passed**.
- `git diff --check`: no implementation error; only pre-existing line-ending warnings for
  `.planning/config.json` and the concurrently updated `03-SECURITY.md`.
- Manual adversarial and normal-path checks used the real public workflow, validator,
  publisher, JSON round trip, and bundle verifier rather than private helper-only assertions.

## Required Test Before Clean Status

1. A user-only follow-up fact can be corrected in the next contiguous revision, strictly
   JSON-round-tripped, published against its verified source bundle, and verified without
   weakening rejection of forged provenance-free OCR/VLM facts.
