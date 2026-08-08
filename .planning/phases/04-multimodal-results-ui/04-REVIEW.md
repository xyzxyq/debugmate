---
phase: 04-multimodal-results-ui
reviewed: 2026-08-08T09:52:50Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - fixtures/replay/index.json
  - pyproject.toml
  - scripts/generate-replay-fixture.py
  - src/debugmate/results/contracts.py
  - src/debugmate/results/font.py
  - src/debugmate/results/loader.py
  - src/debugmate/results/outcome_store.py
  - src/debugmate/results/presentation.py
  - src/debugmate/results/report.py
  - tests/results/golden/module-not-found-report.md
  - tests/results/test_contracts.py
  - tests/results/test_loader.py
  - tests/results/test_presentation.py
  - tests/results/test_report.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-08-08T09:52:50Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

The Phase 04 result foundation, verified-source loader, immutable presentation projection, and deterministic report renderer are generally well defended and have strong adversarial tests. No critical security vulnerability was found. Three correctness issues remain: regenerating the original replay fixture can silently remove later fixtures from the shared index, multiline report values can still inject Markdown block structure, and the public view-state contract accepts contradictory nonterminal states. One unused validation helper should also be removed or restored to the intended call path.

Focused verification passed with **88 tests** across the four reviewed test modules, and scoped Ruff checks passed. The repository-local `.venv` referenced by historical summaries is absent in this worktree; verification used the existing Phase 1 worktree virtual environment with `PYTHONPATH` explicitly bound to this worktree's `src` directory.

## Warnings

### WR-01: Regenerating the module fixture deletes other replay index entries

**File:** `scripts/generate-replay-fixture.py:64-77`
**Issue:** `generate()` reconstructs `index.json` with exactly one `module-not-found` entry. The committed index now also contains `long-content`, and the later long-content generator deliberately merges its entry with existing fixtures. Running this script with its default destination therefore rewrites the shared allowlist and silently removes `long-content`, breaking the replay selector and its UI tests. `test_replay_fixture_regeneration_is_canonical` compares only the generated module subtree, so it does not detect the destructive index rewrite.

**Fix:** Load and validate an existing index when present, retain entries whose `fixture_id` differs from `module-not-found`, replace only the module entry, and write the merged list deterministically. Extend the regeneration test to seed/copy the committed index and assert that `long-content` remains present, for example:

```python
index_path = root / "index.json"
index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {
    "index_version": "1.0.0",
    "fixtures": [],
}
retained = [
    item for item in index["fixtures"]
    if isinstance(item, dict) and item.get("fixture_id") != FIXTURE_ID
]
index["fixtures"] = [module_entry, *retained]
index_path.write_bytes(canonical_json_bytes(index))
```

### WR-02: Multiline values can escape their report list item and inject Markdown blocks

**File:** `src/debugmate/results/report.py:57-67`
**Issue:** `_safe_text()` escapes headings, links, HTML, and backticks, but leaves physical newlines and Markdown list/thematic-break markers unchanged. A verified value such as `"safe\n- injected item\n---"` is rendered as a second top-level list item followed by a thematic break. This contradicts the fixed-template guarantee and can distort the report structure even though script tags and active URL schemes are blocked. The existing injection tests cover headings, images, HTML, links, and fences, but not newline-prefixed list, ordered-list, or thematic-break constructs.

**Fix:** Normalize CR/LF and ensure untrusted values never introduce a physical Markdown line boundary, or escape every block marker at the start of every continuation line. A compact option is to convert normalized line breaks to a trusted inline break token after escaping:

```python
def _safe_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    escaped = normalized.replace("<", "&lt;").replace(">", "&gt;")
    escaped = escaped.replace("`", "&#96;")
    escaped = re.sub(r"(?i)javascript:", "javascript&#58;", escaped)
    escaped = re.sub(r"(?i)data:", "data&#58;", escaped)
    escaped = _MARKDOWN_ESCAPES.sub(r"\\\1", escaped)
    return escaped.replace("\n", "<br>")
```

Add regression cases for `\n- item`, `\n1. item`, and `\n---`, and assert that they do not create additional block nodes.

### WR-03: `ResultViewState` accepts contradictory idle and running states

**File:** `src/debugmate/results/contracts.py:356-393`
**Issue:** `honest_view_state()` prevents nonterminal states from carrying identity, result ID, or audio, but it does not reject artifact availability, a terminal failure, stale stage history, or a `current_stage` on `IDLE`. As a result, `IDLE` can claim available report/card artifacts and a failure, while `RUNNING` can simultaneously claim completed artifact availability or failure. The UI mapper derives `available_artifacts` from this contract before branching on status, so malformed state can propagate contradictory metadata even when tabs are disabled.

**Fix:** Define the allowed shape for each nonterminal state explicitly and reject terminal-only fields. Also require terminal states to have no `current_stage`:

```python
if self.status is ResultStatus.IDLE and (
    self.availability.any()
    or self.failure is not None
    or self.current_stage is not None
    or self.completed_stages
    or self.inherited_stages
):
    raise ValueError("idle view cannot expose progress or result state")
if self.status is ResultStatus.RUNNING and (
    self.availability.any() or self.failure is not None or not self.current_stage
):
    raise ValueError("running view requires only progress state")
if self.status in {ResultStatus.COMPLETED, ResultStatus.PARTIAL, ResultStatus.FAILED} \
        and self.current_stage is not None:
    raise ValueError("terminal view cannot retain a current stage")
```

Add parameterized contract tests for each rejected combination so stale UI state cannot be reintroduced.

## Info

### IN-01: `_strict_source` is dead validation code

**File:** `src/debugmate/results/presentation.py:151-169`
**Issue:** `_strict_source()` is not called anywhere. `build_presentation()` now obtains its authoritative snapshot through `issued_source_snapshot()`, so the older helper duplicates source identity checks without participating in the security boundary. Keeping two validation implementations invites drift and makes it harder to identify the actual authority path.

**Fix:** Remove `_strict_source()` if the capability registry fully supersedes it, or invoke a single shared identity-validation helper from the loader/capability path so there is only one maintained implementation.

---

_Reviewed: 2026-08-08T09:52:50Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
