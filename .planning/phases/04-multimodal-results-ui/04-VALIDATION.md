---
phase: 04
slug: multimodal-results-ui
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-13
---

# Phase 04 — Validation Strategy

> 三模态产物与统一结果页在执行期间的 Nyquist 反馈采样合同。`nyquist_compliant: true` 表示所有计划行为已有自动或明确人工采样覆盖；Wave 0 依赖仍须先完成，不能据此声称产品已经通过验证。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest `9.1.1` + Ruff `0.15.21`; Pydantic strict contracts; Pillow/ffprobe artifact probes |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.ruff]`) |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest -q --disable-warnings --maxfail=1 tests\results tests\ui` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest` then `.\.venv\Scripts\python.exe -m ruff check src tests` |
| **Local media command** | `.\.venv\Scripts\python.exe -m pytest -m tts` |
| **External TTS commands** | `.\.venv\Scripts\python.exe -m pytest -m "cloud and tts"`; `.\.venv\Scripts\python.exe -m pytest -m "network and tts"` |
| **Browser command** | `.\.venv\Scripts\python.exe -m pytest -m browser` plus UI-SPEC `VQ-01..VQ-15` screenshot checklist |
| **Estimated runtime** | targeted quick ≤20s; full offline suite ≤90s; local SAPI ≤120s; external/browser variable |

The current default pytest expression is `not cloud and not ocr`. Wave 0 must extend it to also exclude `network`, `browser`, and real-local `tts` markers while keeping fake TTS/media unit tests unmarked and therefore blocking by default.

---

## Sampling Rate

- **After every task commit:** Run the row-specific focused command below; if the row creates the named test file, run it immediately after the first red test exists and again after implementation.
- **After every plan wave:** Run the full offline pytest suite and Ruff. For Wave 04-04 and 04-07 also run the real local `tts` marker on this Windows machine.
- **Before `/gsd-verify-work`:** Full offline suite, Ruff, schema round-trip, secret scan, result verifier, deterministic ZIP repeat build, local SAPI/ffprobe smoke, Gradio app smoke, and browser visual matrix must be green.
- **External gate policy:** Dify and edge-tts tests are explicit gates. Missing credentials/network may clean-skip during development, but the course-demo readiness record must name each still-open gate; it may not report a skipped gate as passed.
- **Max feedback latency:** 20 seconds for focused unit tests; no three consecutive implementation tasks may defer feedback to a later plan.
- **File evidence rule:** Artifact tests reopen bytes from disk and rerun the public verifier; renderer return values alone are not proof.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | MULTI-04 | T4-01, T4-14 | Strict result contracts reject extra fields, unknown versions, forged status and identity drift. | contract | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_contracts.py` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | MULTI-04 | T4-01 | Loader accepts only completed, revalidated outcome plus verified matching source bundle. | integration | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_loader.py` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | UX-04 | T4-12, T4-14 | Loader failures expose fixed safe code/stage only and publish nothing. | abuse/integration | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_loader.py -k "failure or tamper or version"` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | MULTI-01 | T4-04 | Presentation projection has deterministic order and preserves stable fact/evidence/candidate IDs. | unit | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_presentation.py` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | MULTI-01 | T4-04, T4-12 | Markdown has fixed sections, escapes content, preserves English technical text/commands, and blocks secret/injection output without echo. | unit/golden | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_report.py` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | MULTI-01, UX-01 | T4-04 | Every rendered citation maps to verified evidence; unsupported URLs or invented support are rejected. | integration | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_report.py -k citation` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 3 | MULTI-02 | T4-05 | Font resolver is confined/hashed; 1600px layout is deterministic and all measured boxes remain in bounds. | unit/artifact | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_card.py -k "font or layout or deterministic"` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 3 | MULTI-02 | T4-05 | Saved PNG is reopened as single-frame metadata-free PNG with approved mode/size. | artifact | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_card.py -k "png or metadata or frame"` | ❌ W0 | ⬜ pending |
| 04-03-03 | 03 | 3 | MULTI-05, UX-04 | T4-05 | Oversize/long content yields typed `png_layout_failed`, no clipped/placeholder card, and preserves other candidate modalities. | boundary | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_card.py -k "oversize or partial"` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 4 | MULTI-03 | T4-06 | Recap has fixed six-part structure, derives from the same presentation model, and passes privacy scan. | unit | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_recap.py` | ❌ W0 | ⬜ pending |
| 04-04-02 | 04 | 4 | MULTI-03 | T4-07 | Media probe rejects bad header, decode failure, non-audio/multi-audio streams, and duration outside inclusive 30–60s. | artifact | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_media.py` | ❌ W0 | ⬜ pending |
| 04-04-03 | 04 | 4 | MULTI-03, MULTI-05 | T4-06, T4-07, T4-12 | Fake adapters prove Dify→edge→SAPI, one rate retry, all-failed partial, bounded response and value-free attempts. | unit/integration | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_tts_chain.py` | ❌ W0 | ⬜ pending |
| 04-04-04 | 04 | 4 | MULTI-05 | T4-08 | SAPI/FFmpeg adapter uses fixed executable and `shell=False`; real Chinese MP3 is mono, decodable and 30–60s. | local smoke | `.\.venv\Scripts\python.exe -m pytest -q -m tts tests\results\test_tts_live.py` | ❌ W0 | ⬜ pending |
| 04-04-05 | 04 | 4 | MULTI-03, MULTI-05 | T4-06, T4-07 | Dify and edge adapters match current live service contracts without making default suite network-dependent. | external smoke | `.\.venv\Scripts\python.exe -m pytest -q -m "(cloud or network) and tts" tests\results\test_tts_live.py` | ❌ W0 | ⬜ pending |
| 04-05-01 | 05 | 5 | MULTI-04 | T4-01, T4-11, T4-14 | Consistency gate compares every artifact identity; mismatch/duplicate/interruption creates no success-looking final directory. | integration | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_publisher.py -k "identity or atomic or duplicate"` | ❌ W0 | ⬜ pending |
| 04-05-02 | 05 | 5 | UX-02 | T4-02, T4-03, T4-09, T4-13 | Full/partial member allowlists, confinement, size limits and checksum verification reject traversal, symlink, extra/missing/tampered files. | abuse/artifact | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_publisher.py -k "path or zip or tamper or partial"` | ❌ W0 | ⬜ pending |
| 04-05-03 | 05 | 5 | UX-02 | T4-03, T4-13 | Fixed ZipInfo order/time/attrs/compression creates byte-identical ZIP; CRC and unpacked manifest/hash verify. | determinism | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_publisher.py -k deterministic` | ❌ W0 | ⬜ pending |
| 04-05-04 | 05 | 5 | MULTI-04, UX-02 | T4-02, T4-09 | Download resolution rereads manifest and file hash immediately before returning an allowlisted path. | TOCTOU | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_publisher.py -k download` | ❌ W0 | ⬜ pending |
| 04-06-01 | 06 | 6 | UX-01, UX-04 | T4-12 | Pure visibility matrix covers idle/running/completed/partial/failed plus orthogonal replay/fallback; no state is inferred from file absence. | unit | `.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_view_state.py` | ❌ W0 | ⬜ pending |
| 04-06-02 | 06 | 6 | UX-03 | T4-10, T4-14 | Replay loads only indexed verified fixture and labels replay in state, manifest and download metadata. | integration | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_service.py -k replay` | ❌ W0 | ⬜ pending |
| 04-06-03 | 06 | 6 | UX-04 | T4-11 | Per-case idempotency prevents duplicate work; correction needs confirmation and creates a distinct immutable run/result. | service E2E | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_service.py -k "idempotent or correction or retry"` | ❌ W0 | ⬜ pending |
| 04-06-04 | 06 | 6 | UX-01, UX-02 | T4-04, T4-08, T4-09, T4-12 | Gradio app builds offline with native components/private callbacks, no raw HTML, shell/terminal action or user path input. | structural UI | `.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_app.py` | ❌ W0 | ⬜ pending |
| 04-06-05 | 06 | 6 | UX-01, UX-04 | T4-09, T4-12 | Component values/labels/actions exactly follow verified state, and tampered download after render fails safely. | UI integration | `.\.venv\Scripts\python.exe -m pytest -q tests\ui\test_callbacks.py` | ❌ W0 | ⬜ pending |
| 04-07-01 | 07 | 7 | MULTI-01..05, UX-01..04 | T4-01..T4-14 | Fixed completed/PNG-partial/TTS-partial/failed/replay cases traverse source verification through on-disk result revalidation. | offline E2E | `.\.venv\Scripts\python.exe -m pytest -q tests\results\test_result_e2e.py` | ❌ W0 | ⬜ pending |
| 04-07-02 | 07 | 7 | MULTI-01..05, UX-01..04 | T4-01..T4-14 | Full regression, static checks, secret scan, schema/result/ZIP gates remain green. | regression | `.\.venv\Scripts\python.exe -m pytest` then `.\.venv\Scripts\python.exe -m ruff check src tests` | ✅ infra | ⬜ pending |
| 04-07-03 | 07 | 7 | UX-01, UX-03, UX-04 | T4-09, T4-10, T4-12 | Real browser renders VQ-01..15 without overflow/crop, preserves keyboard/focus/status/replay/fallback truth. | browser/manual+automation | `.\.venv\Scripts\python.exe -m pytest -m browser` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Threat Coverage Audit

All `T4-01..T4-14` appear in the map. In particular, the less visible threats are sampled as follows: T4-02/03/09/13 in publisher and download abuse tests; T4-06/07/08 in TTS/media adapters; T4-10 in replay E2E; T4-11 in atomic/idempotent tests; T4-12 in safe failure/log/UI assertions; T4-14 in loader/replay/restore version tests.

---

## Wave 0 Requirements

- [ ] Pin runtime dependencies in `pyproject.toml`: `gradio==6.20.0`, `edge-tts==7.2.8`; install into `.venv` and record import/version smoke. Do not install a second web framework.
- [ ] Add pytest markers: `tts` (real local SAPI/FFmpeg), `network` (edge), `browser` (real browser); retain `cloud`; default expression excludes all external/slow gates while keeping fake adapter/media tests in the default suite.
- [ ] Create `tests/results/` and `tests/ui/` packages plus the test modules named in the map before their production behavior is implemented.
- [ ] Add shared fixture builders in `tests/results/conftest.py`: strict completed Phase 3 outcome/source evidence, long safe diagnosis, tampered manifests, result-state matrix, fake TTS attempts.
- [ ] Commit one verified allowlisted `ModuleNotFoundError` replay index entry whose source bundle passes the current Phase 3 verifier; display label is not a path.
- [ ] Provide deterministic media fixtures or a test-only generator for 29.9s/30s/45s/60s/60.1s mono MP3, corrupt header, non-MP3, multi-audio stream and tagged payload. Generated fixtures must be real ffprobe-decodable media, not header-only bytes.
- [ ] Add Dify/edge fake transport fixtures for success, timeout, wrong content type, oversized response and safe HTTP errors.
- [ ] Add a committed/approved Chinese font asset if license permits. If not, record the Windows font allowlist and make byte-golden PNG tests conditional on the exact recorded font SHA-256; layout/metadata tests remain mandatory everywhere.
- [ ] Add a browser harness and screenshot output location for UI-SPEC `VQ-01..VQ-15`; browser evidence must use verified redacted fixture/replay state.
- [ ] Add deterministic result/ZIP verifier CLI or callable test helper so Phase 5 can reuse the gate rather than parse manifests independently.

Wave 0 is incomplete because Gradio/edge-tts and all Phase 4 test modules/fixtures are currently absent. Existing pytest/Ruff and Phase 3 outcome/evidence fixtures are reusable foundations, not sufficient coverage by themselves.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| UI-SPEC visual matrix `VQ-01..VQ-15` | UX-01, UX-03, UX-04 | Static/component tests cannot prove real layout, keyboard focus, 200% zoom, grayscale semantics or native audio controls. | Launch loopback Gradio app with verified replay fixtures; capture 1366×768, 1024×768 and 768×1024; run every UI-SPEC row; inspect body horizontal scroll, overlap/crop, focus order, audio/download and replay/fallback labels. |
| Dify TTS live contract | MULTI-03, MULTI-05 | Requires account key, configured provider, quota and current remote API behavior. | With explicit credential environment, run cloud+tts marker; verify real `audio/mpeg`, safe failure handling, ffprobe duration/stream and manifest backend; redact evidence. Do not expose key or response body. |
| edge-tts live fallback | MULTI-03, MULTI-05 | Third-party online service can change independently and requires network. | Run network+tts marker with approved Chinese voice; force Dify failure; verify edge output, fallback reason, MP3 probe and no sensitive log values. |
| Windows SAPI voice quality/readability | MULTI-03, MULTI-05 | Automated probes prove format/duration, not intelligibility or technical-term pronunciation. | Generate fixed Chinese recap through `Microsoft Huihui Desktop`; listen once for clipping/silence/garbling and record voice/rate/hash/duration. Technical names may sound imperfect but content must remain understandable. |
| Course-demo truth labels | UX-03, UX-04 | Wording can be contextually misleading even when state values are technically correct. | Compare live and replay screens plus downloaded manifests; confirm replay never claims current cloud success and partial never appears complete/deliverable. |

External/manual checks supplement, but do not replace, offline branch coverage: every fallback transition and failure state is already sampled automatically with fakes.

---

## Final Phase Gate

Phase 04 may be marked verified only when:

1. all default offline tests and Ruff pass;
2. strict schemas round-trip and `git diff --check`/secret scan are clean;
3. full and partial result bundles pass public verifier after disk reread;
4. deterministic ZIP repeat builds match byte-for-byte;
5. local SAPI→FFmpeg→ffprobe smoke passes on this Windows target;
6. Gradio app builds offline and browser `VQ-01..15` is evidenced;
7. any unexecuted Dify/edge external gate is explicitly recorded as open and not represented as success; before final course recording, the chosen live/fallback audio path must have one real successful run;
8. requirement traceability proves `MULTI-01..05` and `UX-01..04` individually rather than relying only on one broad E2E test;
9. threat audit proves `T4-01..T4-14` closed or names an exact unresolved threat; unresolved high-risk threats block completion.

---

## Validation Sign-Off

- [x] All planned tasks have an automated verification or explicit Wave 0 dependency.
- [x] Sampling continuity: no three consecutive tasks lack automated verification.
- [x] Wave 0 enumerates every currently missing test/dependency/fixture reference.
- [x] No watch-mode flags appear in commands.
- [x] Focused feedback target is under 20 seconds; slow/external gates are isolated.
- [x] All nine Phase 4 requirements have direct sampling coverage.
- [x] All fourteen Phase 4 threat references have direct sampling coverage.
- [x] Manual-only checks have exact procedures and do not substitute for branch automation.
- [x] `nyquist_compliant: true` is justified for the planned strategy.

**Approval:** ready for plan review 2026-07-13; execution sign-off pending Wave 0 and implementation.
