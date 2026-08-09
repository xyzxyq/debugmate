---
phase: 07
slug: real-input-privacy-ui
status: verified
threats_open: 0
asvs_level: 1
block_on: open
created: 2026-08-10
verified: 2026-08-10
---

# Phase 07 — Security

> Threat-model verification for the real-input privacy workbench. Enforcement uses the project default ASVS level 1 and the requested fail-on-any-open-threat policy.

## Trust Boundaries

| Boundary | Security property verified |
|---|---|
| Local environment → test claims | Exact Python/package versions, dependency consistency, collected contracts, and zero-skip release gates prevent false completion. |
| OCR/redaction → preview | Only strict value-free aggregate screenshot facts enter the signable preview hash. |
| Browser token → server authority | An opaque random token is bound to one session, revision, TTL, and one atomic consume. |
| Concurrent callbacks → session authority | Edit, preview, approve, and replay share server revision checks and a serialized callback lane. |
| Upload → OCR | Cache confinement, link/reparse rejection, real-byte format, size, and pixel limits run before OCR. |
| Approved screenshot → extraction | The server-owned relative artifact is root-confined, rehashed, and image-validated before the second OCR read. |
| Service construction → external adapters | Ordinary live and replay composition constructs production RapidOCR and local SAPI only. |
| Server presentation → browser DOM | Browser surfaces receive redacted values and bounded loopback capabilities, not raw values, filesystem paths, signatures, or strict approval objects. |
| Edge capture → repository evidence | Exact value-free ledgers bind each PNG by SHA-256 and promote only as a complete atomic inventory. |
| Phase 07 changes → frozen project scope | Baseline ancestry and exact hashes protect historical evidence, deliverables, media, and later-phase planning. |

## Threat Register

| Threat ID | Category | Severity | Component | Disposition | Mitigation and evidence | Status |
|---|---|---:|---|---|---|---|
| T-07-ENV | Repudiation | high | Pinned environment and validation output | mitigate | Live audit confirmed Python 3.13, all exact pinned versions, and `pip check` with no broken requirements; `scripts/run-phase7-real-input-qa.ps1:20-38` rejects zero-test, failed, errored, or skipped JUnit runs. | closed |
| T-07-TEST-GAP | Tampering | high | Phase 07 contract tests | mitigate | The four frozen contract sentinels are present at `tests/ui/test_real_input.py:101`, `:113`, `:237`, and `:364`; the current focused audit passed 66 tests with no collection failure. | closed |
| T-07-EVIDENCE | Information Disclosure / Tampering / Repudiation | high | Browser evidence ledger and PNG inventory | mitigate | Exact ledger allowlist, scenario semantics, UTC interval, PNG header/hash, and atomic transaction checks are enforced at `scripts/run-phase7-real-input-qa.ps1:41-143` and `:145-204`; the current nine-ledger/nine-PNG inventory passed `Assert-Phase7EvidenceSet`. | closed |
| T-07-RACE | Tampering / Elevation of Privilege | high | `LocalPreviewStore` and queued callbacks | mitigate | Revision CAS and atomic consume are implemented at `src/debugmate/ui/local_live.py:138-205`; all authority callbacks use `concurrency_id="debugmate-case"` at `src/debugmate/ui/app.py:2199-2360`; adversarial orders are covered at `tests/ui/test_real_input.py:128-234`. | closed |
| T-07-SESSION | Spoofing | high | Preview token | mitigate | Random 32-byte URL-safe tokens bind session, revision, and expiry at `src/debugmate/ui/local_live.py:149-175`; session/revision/TTL compare-and-pop occurs at `:186-205`; copied, tampered, expired, and reused tokens are rejected at `tests/ui/test_real_input.py:189-223`. | closed |
| T-07-OCR-AUDIT | Repudiation / Information Disclosure | high | `PreviewBundle` | mitigate | Strict frozen screenshot audit is defined at `src/debugmate/privacy/models.py:137-174`, required by `PreviewBundle` at `:188`, and included before preview hashing at `src/debugmate/privacy/text_redactor.py:249-274`; value/path-free and hash-binding tests are at `tests/privacy/test_preview_integration.py:78-133`. | closed |
| T-07-STORE-DOS | Denial of Service | medium | Bounded preview authority store | mitigate | Positive capacity validation, deterministic session/token eviction, expiry purge, and per-session token removal are implemented at `src/debugmate/ui/local_live.py:39-92`, `:165-177`, and `:207-214`. | closed |
| T-07-CLOUD | Information Disclosure / Repudiation | high | Local service assembly | mitigate | Ordinary composition instantiates one production `RapidOcrBackend` at `src/debugmate/ui/serve.py:190` and a SAPI-only `local_only=True` chain at `:111-115`; constructor poisoning and source-absence checks are at `tests/ui/test_real_input.py:237-286`. | closed |
| T-07-OCR | Information Disclosure | high | RapidOCR failure handling | mitigate | OCR failure raises the safe `OcrUnavailable` path and leaves no preview/stale redacted PNG, proven at `tests/privacy/test_preview_integration.py:229-253`; the UI maps it to fixed safe copy without exception/path data in `src/debugmate/ui/app.py:1984-2009`. | closed |
| T-07-PATH | Tampering / Elevation of Privilege | high | Approved screenshot extraction | mitigate | `_verified_screenshot` performs trusted-root resolution, existence/type check, SHA-256 comparison, and image validation before OCR at `src/debugmate/diagnosis/providers.py:155-179`; shared backend/root identity is verified at `tests/ui/test_real_input.py:291-314`. | closed |
| T-07-IMAGE-DOS | Denial of Service | high | Screenshot OCR | mitigate | Real bytes are capped at 10 MiB and decoded pixels at 20 MP by `src/debugmate/privacy/image_models.py:15-16` and `:34-62`; the upload callback invokes validation only after confinement at `src/debugmate/ui/app.py:1380-1421`, and launch also caps uploads at `src/debugmate/ui/serve.py:275`. | closed |
| T-07-DOM | Information Disclosure | high | Gradio DOM/config/storage | mitigate | Redacted screenshot bytes are exposed only through a bounded loopback capability at `src/debugmate/ui/app.py:532-568` and `:1919-1952`; real-Edge browser/config/storage sentinel checks and value-free evidence capture are implemented at `tests/ui/test_browser.py:675-735` and `:1273-1324`. | closed |
| T-07-UPLOAD | Tampering / Denial of Service | high | `screenshot-input` | mitigate | The single-file UI contract is fixed at `src/debugmate/ui/app.py:1533-1540`; lexical/root confinement, symlink/reparse rejection, strict resolution, regular-file check, and validation are at `:1380-1421`; focused upload regressions passed in the current audit. | closed |
| T-07-REPLAY | Spoofing / Repudiation | high | Replay/live isolation | mitigate | Replay invalidates the live server authority before fixture/service access at `src/debugmate/ui/app.py:1899-1905`, then clears browser preview authority in the same serialized stream at `:2190-2200`; real Edge verifies literal independent replay behavior at `tests/ui/test_browser.py:1397-1422`. | closed |
| T-07-A11Y | Denial of Service | medium | Keyboard, zoom, contrast, and responsive UI | mitigate | Effective ancestor-opacity contrast is measured at `tests/ui/test_browser.py:748-793`; real Edge keyboard and 200% zoom gates are at `:1499-1557`, with responsive no-overflow scenarios at `:1447-1484`. | closed |
| T-07-SCOPE | Tampering | high | Frozen Phase 04/08–10/media scope | mitigate | `scripts/verify-phase7-security-scope.ps1:120-137` invokes the exact frozen hash gate, verifies baseline ancestry, derives changed files, and scans reviewable/evidence files; the live audit confirmed all 14 frozen targets and zero findings across 37 files. | closed |

## Summary Threat Flags

No Phase 07 summary contains a `## Threat Flags` section. No unregistered threat flags were identified.

## Accepted Risks Log

No accepted risks. All 16 registered threats use the `mitigate` disposition; none are accepted or transferred.

## Security Audit Trail

| Audit Date | Verification | Result |
|---|---|---|
| 2026-08-10 | Python 3.13 and exact package-version assertions; `python -m pip check` | passed; no broken requirements |
| 2026-08-10 | Focused privacy, race, evidence, runner, and security tests | 66 passed, 88 deselected |
| 2026-08-10 | Focused store/upload/extraction/local-only regressions | 4 passed, 57 deselected |
| 2026-08-10 | `scripts/verify-phase7-security-scope.ps1` | passed; 14 frozen targets matched, 37 files scanned, 0 findings |
| 2026-08-10 | Current formal `evidence/ui/phase7` inventory | passed; exactly 9 JSON + 9 PNG, one QA run, exact ledger/PNG contract |

## Sign-Off

- [x] All 16 threats classified and verified by disposition.
- [x] No accepted or transferred risks require documentation.
- [x] No unregistered summary threat flags exist.
- [x] `threats_open: 0` confirmed under block-on-any-open enforcement.
- [x] `status: verified` set in frontmatter.

**Approval:** verified 2026-08-10
