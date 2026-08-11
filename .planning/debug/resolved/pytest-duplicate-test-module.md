---
status: resolved
trigger: "Full default offline pytest now fails during collection because Phase 09 added tests/evaluation/test_contracts.py, which collides with existing tests/test_contracts.py under pytest's default import mode."
created: 2026-08-11T18:10:00+08:00
updated: 2026-08-11T18:49:00+08:00
---

## Current Focus

hypothesis: confirmed and fixed — unique standalone basenames restore default pytest collection.
test: all required focused and full offline verification scopes passed.
expecting: complete.
next_action: archived after human verification.

## Symptoms

expected: `.venv\Scripts\python.exe -m pytest -q` collects the full default offline suite and reaches execution with no collection errors.
actual: collection aborts immediately with an import file mismatch.
errors: imported module `test_contracts` has `__file__` `tests/evaluation/test_contracts.py`, not `tests/test_contracts.py`; pytest recommends unique basenames or package/import-mode changes.
reproduction: From repo root, set PYTHONPATH to `<repo>/src` and run `.venv\Scripts\python.exe -m pytest -q`.
started: Began after Phase 09 plan 09-01 added `tests/evaluation/test_contracts.py`; focused `pytest tests/evaluation` passed, but full suite had not yet been run after that addition.

## Eliminated

## Evidence

- timestamp: 2026-08-11T18:14:00+08:00
  checked: pytest configuration and test filenames
  found: `pyproject.toml` defines testpaths/addopts but no import-mode override; the repository contains `tests/test_contracts.py`, `tests/evaluation/test_contracts.py`, and `tests/results/test_contracts.py`.
  implication: under pytest's default prepend import mode, all three non-package files are candidates for the same top-level module name; a unique filename is the narrowest durable remedy.

- timestamp: 2026-08-11T18:14:00+08:00
  checked: debug knowledge base and common bug patterns
  found: no knowledge-base entry overlaps this pytest collection mismatch; the issue matches the Import / Module common-pattern category.
  implication: test the duplicate-module-name hypothesis directly rather than borrowing a previous diagnosis.

- timestamp: 2026-08-11T18:17:00+08:00
  checked: exact command `$env:PYTHONPATH = (Resolve-Path -LiteralPath 'src').Path; .\.venv\Scripts\python.exe -m pytest -q`
  found: collection deterministically aborts with imported module `test_contracts` pointing at `tests/evaluation/test_contracts.py` while pytest attempts to collect `tests/test_contracts.py`; 58 tests were deselected before the collection error.
  implication: the reported failure is reproduced and occurs before test execution; the observed module alias exactly matches the duplicate-basename hypothesis.

- timestamp: 2026-08-11T18:22:00+08:00
  checked: complete contents of all three `test_contracts.py` modules, directory metadata, pytest configuration, and file history
  found: `tests/evaluation/test_contracts.py` and `tests/test_contracts.py` are ordinary test modules in non-package directories; `tests/results/test_contracts.py` is under `tests/results/__init__.py`; pytest has no import-mode override; commit `688e6be` introduced the evaluation file.
  implication: only the evaluation/root pair resolves to the same top-level import name; test bodies have no module-name manipulation, and changing global import semantics is unnecessary.

- timestamp: 2026-08-11T18:26:00+08:00
  checked: focused evaluation subtree, focused root contract module, paired collection, and standalone basename enumeration
  found: evaluation passes 33 tests; root contract passes 14 tests; paired collection fails with the exact mismatch; the only duplicate among non-package test directories is `test_contracts.py` at the root and evaluation paths.
  implication: the basename collision is causally confirmed and isolated; renaming the Phase 09 test module is sufficient.

- timestamp: 2026-08-11T18:29:00+08:00
  checked: implemented diff
  found: the Phase 09 test file now has unique basename `test_evaluation_contracts.py`; `tests/test_pytest_collection.py` asserts that all test modules outside package directories have unique basenames.
  implication: behavior is unchanged inside contract tests, global pytest semantics remain unchanged, and recurrence will produce a direct invariant failure when it does not already stop collection.

- timestamp: 2026-08-11T18:32:00+08:00
  checked: focused post-fix verification with the original `PYTHONPATH`
  found: `pytest -q tests/evaluation` passes 33 tests; `pytest -q tests/test_contracts.py tests/test_pytest_collection.py` passes 15 tests.
  implication: both formerly colliding scopes now collect together with the guard, and Phase 09 contract behavior remains intact.

- timestamp: 2026-08-11T18:36:00+08:00
  checked: first post-fix full-suite attempt
  found: pytest ran beyond the former collection point for 123 seconds, but the command harness timed out and terminated output flushing before pytest returned a result.
  implication: the collection regression is absent, but this attempt is not valid full-suite verification; rerun with a longer command timeout.

- timestamp: 2026-08-11T18:43:00+08:00
  checked: authoritative full default offline suite with the exact original `PYTHONPATH` setup
  found: 1147 passed, 58 deselected, 1 pre-existing Starlette deprecation warning in 266.91 seconds; zero collection errors.
  implication: the original failure is resolved and adjacent offline behavior remains green across the repository.

- timestamp: 2026-08-11T18:46:00+08:00
  checked: lint, diff hygiene, and atomic commit
  found: Ruff and `git diff --check` passed; commit `9a936f5` contains only the Phase 09 test rename and collection guard; the debug report remains untracked and uncommitted.
  implication: the code/test fix is cleanly isolated and ready for human confirmation.

- timestamp: 2026-08-11T18:49:00+08:00
  checked: human verification checkpoint
  found: orchestrator confirmed the fix from focused, full-suite, Ruff, and diff evidence.
  implication: the session is resolved and archived.

## Resolution

root_cause: Phase 09 introduced `tests/evaluation/test_contracts.py` in a non-package directory while `tests/test_contracts.py` already existed. Pytest's default prepend import mode imports both as top-level `test_contracts`, and collection rejects the second path because `sys.modules['test_contracts'].__file__` points to the first.
fix: Rename the Phase 09 module to a unique basename and add a static collection invariant that forbids duplicate basenames among test modules whose parent directory is not a package.
verification: `pytest -q tests/evaluation` => 33 passed; `pytest -q tests/test_contracts.py tests/test_pytest_collection.py` => 15 passed; full `pytest -q` => 1147 passed, 58 deselected, 1 warning.
files_changed: [tests/evaluation/test_evaluation_contracts.py, tests/test_pytest_collection.py]
