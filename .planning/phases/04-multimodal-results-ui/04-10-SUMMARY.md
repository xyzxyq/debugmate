---
phase: 04-multimodal-results-ui
plan: 10
status: completed
completed: 2026-07-17
---

# Plan 04-10 Summary — truth-state browser harness and recovery

## Outcome

Plan 04-10 closes the deterministic real-browser coverage for VQ-02, VQ-03,
VQ-06, VQ-07, VQ-08, VQ-09 and VQ-10. It does not publish the formal visual
ledger or complete Phase 4; those remain Plan 04-11 and Plan 04-12 work.

The QA harness is available only in the runner-owned `qa_serve` process. It
uses enum-only scenarios, a 256-bit loopback request-header capability, an
ordered seven-stage rendezvous and server-built verified result variants.
Ordinary startup has no QA route or QA import. Missing, wrong, non-loopback or
malformed QA requests fail before workflow, result or download side effects.

Partial TTS and PNG failures retain only the verified artifacts that actually
exist. A single scoped retry uses strict server-held case/result identity and
the service-declared failed stage; browser input cannot choose a stage or
filesystem path. Safe source failure exposes the seven approved fields but no
report, citation, media, artifact, download, traceback or absolute path.
Fallback output records `sapi`, the fallback flag and a non-empty reason.

VQ-10 now proves one-field correction does not run on edit or first
confirmation. Two stable windows observe unchanged server run/result counts.
Only explicit “创建新运行” creates one new run and one new result. The new ZIP
has a different result ID and a source-run identity consistent with the page;
the previous replay result remains recoverable.

## Download and session truth boundary

Review uncovered two production defects that button-only tests had hidden:

1. Gradio `launch()` rebuilds its ASGI app, so the private content route could
   disappear and return 404. `ensure_content_endpoint()` now idempotently
   remounts the route after launch in both ordinary and QA startup.
2. A same-name replacement ZIP could retain stale `FileData`. Main result
   callbacks now only clear download surfaces. A server-session resync is the
   sole publisher: it revalidates a strict completed/partial `ResultViewState`,
   resolves the verified bundle and issues a fresh loopback token.

The resync registry is bounded and thread-safe. A 128-bit opaque lease is
issued during a real replay/diagnosis event and kept in `gr.State`; it never
enters config, DOM, URL, logs, screenshots or evidence. Lease tampering,
cross-session use, stale source-run binding, eviction and invalid state all
fail closed. QA audit data contains only session SHA-256 prefixes and safe
state facts behind the private capability gate.

Real downloads are no longer inferred from CTA copy. Edge clicks the native
DownloadButton, verifies the suggested filename, HTTP MIME and
Content-Disposition, compares the browser file SHA-256 with a second GET,
opens the ZIP, enforces the exact manifest/checksum artifact allowlist and
verifies every member digest.

## Verification

- Focused VQ-10 real Edge: `1 passed, 34 deselected in 106.88s`.
- VQ-02 + VQ-10 synchronization rerun: `2 passed, 33 deselected in 130.80s`.
- Final default Edge matrix: `5 passed, 30 deselected in 316.51s`.
- Non-browser UI suite: `97 passed, 35 deselected in 135.66s`.
- Focused app/capability suite: `55 passed, 1 warning`.
- Ruff check and format check for all seven changed implementation/test files:
  passed.
- PowerShell runner syntax: passed.
- `git diff --check`: passed.
- Final process audit: no `debugmate.ui.qa_serve` or `debugmate.ui.serve`
  process remained.

The only test warning is the existing upstream Starlette TestClient/httpx
deprecation warning.

## Commits

- `051eaa8` — isolated truth-state QA scenarios.
- `4952aa0` — hardened rendezvous and fixture provenance.
- `12e33f9` — verifiable partial/fallback result variants.
- `38c9184` / `76e6272` — RED/GREEN scoped partial retry.
- `c543450` — real Edge truth-state and correction matrix.
- `4fbda84` — closed independent specification and security review gaps.

Independent specification re-review and quality/security re-review both
returned `APPROVED`; the quality review reported no P0–P3 findings.

## Remaining work

Plan 04-11 must exercise long-content, responsive and accessibility VQs,
publish the complete 15-row visual ledger through the atomic generation
contract, and validate browser downloads across the full matrix. Plan 04-12
must run the clean tested-commit gate and independent Phase 4 verification.
Human listening remains `human_needed` and is not closed by this plan.
