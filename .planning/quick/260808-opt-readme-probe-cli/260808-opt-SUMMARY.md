---
phase: quick-260808-opt-readme-probe-cli
plan: 01
subsystem: documentation
tags: [readme, probe-cli, evidence, truth-boundary]
requires:
  - phase: 01-foundation-platform-gate
    provides: fixture and cloud capability probe CLI contracts
provides:
  - copyable fixture-probe and cloud-probe commands with required output paths
  - evidence-backed pass, fail, blocked, and not-tested semantics
  - explicit separation between fixture success and Dify cloud capability evidence
affects: [project-onboarding, cloud-validation, capability-evidence]
tech-stack:
  added: []
  patterns: [evidence-backed capability status, repository-relative PowerShell commands]
key-files:
  created:
    - .planning/quick/260808-opt-readme-probe-cli/260808-opt-SUMMARY.md
  modified:
    - README.md
key-decisions:
  - "Treat fixture-probe exit 0 only as successful fixture and evidence-bundle execution; C01-C07 remain not-tested."
  - "Interpret cloud-probe per capability and bundle evidence, never as seven capabilities passing from exit 0 alone."
requirements-completed: []
duration: 5min
completed: 2026-08-08
---

# Quick Task 260808-opt: README Probe CLI Summary

**The root README now exposes the real fixture/cloud probe commands and defines capability outcomes without claiming any Dify cloud success.**

## Accomplishments

- Added repository-relative PowerShell commands for `fixture-probe` and `cloud-probe`, including each command's required `--output` argument.
- Documented CLI JSON fields `backend`, `bundle_path`, and `status_counts` and made the generated bundle's evidence paths and SHA-256 values the audit source.
- Defined `pass`, `fail`, `blocked`, and `not-tested`, plus cloud-probe exit codes 0/1/2.
- Made explicit that fixture-probe exit 0 leaves C01-C07 as seven `not-tested` capabilities and that this repository has no claimed successful cloud-probe run.
- Documented `scripts/run_phase1_probe.ps1` as the conditional wrapper while preserving the same evidence boundary.

## Task Commit

1. **Task 1: Complete README probe commands and auditable status semantics** — `2dc5a83` (`docs`)

The PLAN and this SUMMARY remain uncommitted for the parent quick-workflow documentation commit, as requested.

## Files Created/Modified

- `README.md` — probe commands, result fields, status definitions, exit semantics, and Dify truth boundary.
- `.planning/quick/260808-opt-readme-probe-cli/260808-opt-SUMMARY.md` — bounded execution and verification record.

## Verification

- `tests/test_probe_cli.py::test_reconstruction_docs_and_examples_are_truthful_and_secret_free`: `1 passed`.
- Required README tokens and parser-shaped command checks passed for both probe subcommands, `--output`, all four statuses, and `status_counts`.
- Fixture C01-C07 truth and cloud exit-code 0/1/2 explanation checks passed.
- Secret assignment, Bearer value, and personal Windows absolute-path scans passed.
- Documented `src/debugmate/cli.py` and `scripts/run_phase1_probe.ps1` targets exist.
- `git diff --check` passed for README and the quick documentation directory.
- Only `README.md` was staged in task commit `2dc5a83`; no product code, test, ROADMAP, REQUIREMENTS, STATE, PPTX, video, subtitle, or screenshot was modified by this task.

## Decisions Made

- Used capability-level evidence as the only basis for `pass`; neither an overall exit code nor another capability's success is sufficient.
- Mentioned only an environment-variable name and repository-relative paths, with no credential value or personal installation path.
- Preserved the current matrix truth: all seven Dify capabilities remain `not-tested`.

## Deviations from Plan

None in implementation. The initial scope-check command reported the parent-created untracked PLAN directory and the review agent's `.planning/phases/04-multimodal-results-ui/04-REVIEW.md`; both were expected shared-workspace paths, were not touched, and were excluded from this task's staged files.

## Known Stubs

None. `not-tested` is an intentional capability status, not a placeholder.

## Threat Flags

None. This documentation-only change adds no endpoint, authentication path, file-access behavior, schema change, or trust boundary.

## Self-Check: PASSED

- README, PLAN, and SUMMARY exist.
- README task commit `2dc5a83` exists and contains only `README.md`.
- The targeted documentation contract and bounded README checks passed.
- PLAN/SUMMARY remain for the parent documentation commit; STATE, ROADMAP, REQUIREMENTS, source, tests, and course deliverables are unchanged by this task.

---
*Quick task: 260808-opt-readme-probe-cli*
*Completed: 2026-08-08*
