# Task 4 implementation report

## Outcome

Implemented the single-owner local-live Edge runner and produced the only
formal evidence requested by Task 4: VQ-01 at 1366 x 768. VQ-02 through VQ-15
remain open.

## RED / GREEN

- RED: the focused structural command failed `2 failed, 20 deselected` because
  the new runner and ledger did not exist.
- GREEN: the same command passed `2 passed, 20 deselected in 0.28s` after the
  implementation and formal browser run.
- Real Edge: runner passed `1 passed in 29.16s`, then stopped only its captured
  child and proved port `57117` closed.

## Runner ownership and evidence write boundary

- Literal `127.0.0.1`, IPv4 `TcpListener` reservation, one hidden captured
  Python child, strict `/config`, and a single VQ-01 node ID.
- Both environment variables are restored in nested cleanup; the process
  object, PID and start ticks are checked before termination.
- No fixture path, public URL, external-owner takeover, shell redirection, or
  broad process termination is used.
- The browser performs preview, waits for approval enablement, clicks approval,
  waits for completed/live, checks report/download/provenance/overflow, and
  cross-checks the unique fresh result manifest before writing the screenshot
  and exact-allowlist ledger.

## Visual inspection

The original-resolution image shows readable Chinese, `✓ 已完成`, live mode,
all three workbench headings, the report and citation/download tabs, enabled
download CTA, and `local-rule-v1（本地规则，无云端调用）`. The viewport is
1366 x 768 and browser body metrics are 1366/1366 with no horizontal overflow.

## Verification

- Formal screenshot SHA-256:
  `35d9aa50a4ff9df0ea99ffca3cc771d4be238547d3f717ab51dd14dcbaf2c155`.
- Ledger file SHA-256:
  `825431440c8a6fa325829d7d9dfd0e0eac40f7e80104990815000ff7920c18c7`.
- Fresh-ID and poisoned-network focus: `2 passed, 6 deselected in 34.12s`.
- Preview/approval tamper focus: `4 passed, 12 deselected, 1 warning in 5.15s`.
- Full pytest: `769 passed, 49 deselected, 1 warning in 189.41s`.
- Ruff, pip check and diff check: exit `0`.
- Product secret scan: exit `1`, expected clean/no-match result.
- TTS marker: `3 passed, 2 skipped in 9.35s`; SAPI machine record passes,
  human listening remains `human_needed`.

## Files and self-review

- `scripts/run-phase4-local-live-qa.ps1`
- `tests/ui/test_browser.py`
- `evidence/ui/phase4/VQ-01-live-local.png`
- `evidence/ui/phase4/local-live-vq01.json`
- `.planning/phases/04-multimodal-results-ui/04-09-SUMMARY.md`
- `.superpowers/sdd/task-4-report.md`

Self-review found no raw identity or secret in the ledger, no fixture use in
the live path, no ownership ambiguity, and no claim beyond VQ-01. The visible
source-run string in the UI is an automatically generated fictitious runtime
identity; only its SHA-256 is retained in the machine ledger.

## Concerns

- The existing Starlette TestClient/httpx deprecation warning remains.
- Dify and edge-TTS external gates remain open and unchanged.
- Human listening is still required before course recording.

## Review-fix report (2026-07-16)

### Outcome and TDD

Resolved both Important review findings without changing product live semantics.
The review-fix RED command reported `3 failed, 1 passed, 20 deselected in 2.81s`:
the runner lacked `DEBUGMATE_UI_LEDGER_PATH` and evidence-pair transaction helpers,
and the browser test lacked a strict source-manifest backend loader. The focused
GREEN command reported `4 passed, 20 deselected in 1.21s`.

The controlled failure test dot-sources only the runner helpers, uses a pytest
temporary directory, starts or stops no process, and proves byte-for-byte
restoration of the old PNG/JSON pair plus complete staging/backup cleanup.

### Transactional publication boundary

The runner now moves any old formal PNG/ledger into unique same-directory
backups before server startup. Edge receives unique staging paths through both
`DEBUGMATE_UI_SCREENSHOT_PATH` and `DEBUGMATE_UI_LEDGER_PATH`. It never writes
the formal pair directly. Before promotion, the runner validates the PNG
signature, exact JSON allowlist and semantics, strict UTC-Z timestamp, and
screenshot hash. Same-volume moves promote the pair; any pytest, validation,
promotion, or cleanup failure removes new/staged files and restores the old
pair. Backups are deleted only after captured PID/port cleanup succeeds.

Three hardening failures demonstrated real rollback: a browser-local variable
error, an over-strict optional lineage assertion, and a PowerShell UTC format
error. Each run restored the prior formal hashes, left no staging files, stopped
only its captured process, and proved ports `51022`, `50263`, and `53129` closed.
The prior review-fix runner passed `1 passed in 38.60s`, proved port `57328` closed, and left
zero staging/backup files and zero `debugmate.ui.serve` processes.

### Observed backend and ledger strictness

The fresh result manifest supplies case ID, source run ID, and result ID. The
browser test uses case/source-run to locate
`.debugmate-runtime/evidence/<case>/<source_run>/manifest.json`, parses it with
strict `RunManifest`, and checks source `case_id`/`run_id` against the fresh
result manifest and DOM. The observed backend must be exactly `local-rule-v1`
and that observed value is written to the ledger; UI copy is not the source.
The ledger test recomputes the formal PNG SHA-256, strictly parses a UTC `Z`
timestamp, and records overflow directly from
`scrollWidth > clientWidth` after asserting it is false.

### Formal evidence and verification

- Screenshot SHA-256 at that review stage: `ac1a0af845a6c292f1fa304755d76968f56604b0a1c2fac8d88a21680b706d84`.
- Ledger SHA-256 at that review stage: `00fe952e1f06736fa9b83f61dbbef1457ea53ffa5b5aa3682713a3987a96f861`.
- Source backend, case hash, source-run hash, and screenshot hash all match the ledger.
- Original-resolution viewer confirms completed/live state, three workbench
  headings, citation/download tab, enabled download CTA, visible
  `local-rule-v1` provenance, and no horizontal crop.
- Fresh identity and poisoned-network focus: `2 passed, 6 deselected in 44.74s`.
- Preview/approval tamper focus: `4 passed, 12 deselected, 1 warning in 6.96s`.
- Full pytest: `769 passed, 51 deselected, 1 warning in 229.18s`.
- Ruff, pip check, and diff check: exit `0`; secret scan: expected clean exit `1`.
- TTS marker: `3 passed, 2 skipped in 12.90s`; machine checks pass and human
listening remains exactly `human_needed`.

### Truth boundary and remaining concerns

This publishes only local non-network VQ-01. VQ-02 through VQ-15 remain open;
Phase 4 is not complete. The 04-07 Dify/edge-TTS external outcomes remain
unchanged. Dify credentials are absent, network TTS was not approved, the
existing Starlette/httpx deprecation warning remains, and a human still must
listen before course recording.

## Re-review per-file transaction fix (2026-07-16)

The next review found that rollback state was still pair-wide. Deterministic
fault injection first produced RED `6 failed, 24 deselected`: the runner had no
per-operation injection boundary or per-file state. GREEN was
`6 passed, 24 deselected in 6.93s`; the final combined transaction/ledger/source
focus passed `10 passed, 20 deselected in 8.59s`.

Each screenshot/ledger member now records `HadOriginal`, `BackedUp`,
`Promoted`, and `BackupCleaned`. Restore removes only a member actually
promoted and restores only a member actually backed up. The matrix proves:

- screenshot backup failure before any backup leaves both old formal bytes untouched;
- ledger backup failure after screenshot backup restores both original files;
- first/second promotion failures restore both old files without residue;
- first/second backup-cleanup failures keep the complete validated new formal
  pair, return an explicit cleanup error, and retain recognizable residue;
- the next-start reconcile validates the formal PNG/ledger first and then
  idempotently clears that residue.

The mandatory final real run passed `1 passed in 36.99s`, closed captured port
`54855`, and left zero staging/backup files and zero server processes. Its
current unique formal hashes are:

- PNG: `875813f5cdd332dc99ff1a017c389c47f31638a8f6514b4b97631a27e42976aa`;
- ledger: `8a50fd7adba23408b24ecdf0fb3ba31a745994ef7b0080b6944f1299132ed8e0`.

The original `35d9aa50...` / `82543144...` pair and intermediate
`8637e619...` / `9993c4b9...` pair are explicitly superseded. The later
`ac1a0af8...` / `00fe952e...` review pair is also superseded only because the
required final real runner generated a fresh identity-bound screenshot and
ledger. The two full hashes immediately above are the only current formal
evidence hashes.

Final verification on the re-review code reported:

- combined focused fault/source/ledger matrix: `10 passed, 20 deselected in 8.59s`;
- full pytest: `769 passed, 57 deselected, 1 warning in 222.78s`;
- Ruff, pip check, and diff check: exit `0`;
- product secret scan: expected clean exit `1`;
- TTS marker: `3 passed, 2 skipped in 12.89s`, with human listening still
  exactly `human_needed`.

Truth boundaries remain unchanged: only VQ-01 is closed, VQ-02 through VQ-15
remain open, Dify and network TTS gates remain external, and human listening is
still `human_needed`.
