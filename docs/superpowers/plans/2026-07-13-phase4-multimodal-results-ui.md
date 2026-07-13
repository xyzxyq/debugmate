# Phase 4 Multimodal Results and Gradio Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a verified Phase 4 pipeline that derives one Chinese Markdown report, deterministic PNG card, real 30–60 second Chinese MP3, immutable result bundle and honest Gradio 6 result page from the same completed Phase 3 diagnosis.

**Architecture:** A strict outcome store/source loader revalidates the complete redacted Phase 3 outcome and immutable source bundle. `prepare_generation_context()` resolves/verifies the approved font and returns one frozen `PreparedGenerationContext` containing its matching `generation_profile` and `resolved_font`; `build_presentation(source, context)` creates the only frozen `PresentationModel`. Renderers, consistency and atomic result publication precede a service-only Gradio boundary where UI supplies approved input/IDs but never constructs an outcome.

**Tech Stack:** CPython 3.13, Pydantic 2.13.4, Pillow 12.3.0, HTTPX 0.28.1, Gradio 6.20.0, edge-tts 7.2.8, Playwright 1.61.0 with explicit Microsoft Edge channel, Windows SAPI, FFmpeg/ffprobe 8.1, pytest 9.1.1 and Ruff 0.15.21.

## Global Constraints

- Normal generation accepts only `status=completed` `DiagnosisRunOutcome` values that pass strict round-trip, `validate_diagnosis_outcome()` and on-disk Phase 3 `verify_bundle()`.
- Phase 3 `evidence/<case_id>/<run_id>/` is immutable; Phase 4 publishes only under independent `results/<case_id>/<result_id>/` directories.
- Preserve the existing Phase 3 `AudioEvidenceNotReady` fail-closed boundary; never add MP3/report/card files to `EvidenceBundle`.
- Report, PNG and recap derive only from one frozen `PresentationModel`; no renderer calls an LLM or invents a fact, citation, cause or command.
- Before projection, create exactly one frozen `PreparedGenerationContext(generation_profile, resolved_font)` through the preparation function. Presentation and card receive this complete indivisible context; card reads its font internally and never resolves, splits or recombines identity.
- PNG uses Pillow only, fixed width 1600 px, approved hashed Chinese font, measure-before-paint layout, pixels-only sanitation and disk reopen verification.
- TTS order is exactly Dify → edge-tts → Windows SAPI WAV + FFmpeg MP3; every candidate must be mono, decodable, tag-free and inclusive 30–60 seconds by ffprobe. Any nonempty ID3/format/stream tag rejects.
- SAPI uses fixed `scripts/sapi-synthesize.ps1`; recap is passed only through a controlled UTF-8 file to fixed `-File` argv. `-Command`, recap text argv and dynamic script source are prohibited.
- Each TTS backend permits at most one deterministic rate retry for duration failure; all-backend failure yields explicit partial state with no empty/placeholder MP3.
- Every modality shares case ID, source run ID, canonical diagnosis SHA-256, Schema 1.1.0 and generation version; any mismatch blocks publication.
- Full/partial ZIPs use fixed POSIX member allowlists, order, timestamps, modes and compression settings; repeat builds must be byte-identical.
- UI/download callbacks accept strict IDs/models, never a user filesystem path; every returned file is freshly verified against manifest and hash.
- Replay is allowlisted and must be marked in view state, result manifest and download metadata; replay must never claim a current cloud success.
- Commit a deterministic generated full redacted replay source bundle plus strict full outcome record; current `verify_bundle()` and regeneration identity checks are blocking.
- Live and replay write complete strict redacted outcomes into server-side `DiagnosisOutcomeStore` by run ID; refresh/correction reread and revalidate that record. UI never accepts or constructs `DiagnosisRunOutcome`.
- Commands are display-only inert data. No shell, terminal, auto-install or “运行命令” control is permitted.
- Default pytest remains fully offline and excludes `cloud`, `ocr`, `network`, `browser` and real-local `tts`; fake media/adapters remain blocking default tests.
- Real local SAPI and browser VQ-01..VQ-15 are blocking final Phase 4 gates. Dify/edge gates remain explicit pass/fail/clean-skip external records; no paid API is authorized.
- Browser QA uses project `.venv` Playwright 1.61.0 with explicit `channel="msedge"`, bounded health/action timeouts and guaranteed browser/server cleanup; no global Python 3.10/runtime.
- Execution writes summaries, execution log, media and visual QA only; a fresh independent GSD verifier alone creates the later phase verdict/report.
- All public failures expose fixed safe code/stage/retry information only; no provider body, stack trace, secret, absolute path or temp name enters manifest/UI/course evidence.
- Strict TDD is mandatory: record focused RED before production edits, make the minimum full-fidelity GREEN change, rerun focused/full gates and create selective atomic commits.

---

## File Responsibility Map

| File | Single responsibility |
|---|---|
| `src/debugmate/results/contracts.py` | Strict frozen PreparedGenerationContext/result identities, manifests, states and audio-attempt contracts. |
| `src/debugmate/results/font.py` | Prepare one internally matching generation profile + confined verified resolved font before projection. |
| `src/debugmate/results/loader.py` | Revalidate completed outcome and immutable source bundle; compute canonical diagnosis identity. |
| `src/debugmate/results/outcome_store.py` | Atomically persist/read/revalidate complete redacted outcomes by run ID. |
| `src/debugmate/results/presentation.py` | One deterministic diagnosis-to-display projection shared by all renderers. |
| `src/debugmate/results/report.py` | Fixed safe Markdown and verified canonical citation export. |
| `src/debugmate/results/card.py` | Verify profile-bound passed font, measured layout, Pillow paint and PNG disk verification. |
| `src/debugmate/results/recap.py` | Six-part deterministic privacy-scanned Chinese recap transcript. |
| `src/debugmate/results/media.py` | Bounded MP3 signature/ffprobe validation. |
| `src/debugmate/results/tts/base.py` | Narrow TTS port and shared request/candidate/rate types. |
| `src/debugmate/results/tts/dify.py` | Bounded HTTPX Dify TTS adapter. |
| `src/debugmate/results/tts/edge.py` | Fixed-voice/rate edge-tts network adapter. |
| `src/debugmate/results/tts/sapi.py` | Safe local SAPI WAV generation and FFmpeg MP3 normalization. |
| `scripts/sapi-synthesize.ps1` | Fixed file-to-file SAPI COM script with strict path/voice/rate parameters. |
| `src/debugmate/results/audio.py` | Ordered fallback, one duration retry and partial audio outcome. |
| `src/debugmate/results/consistency.py` | Cross-modal identity/privacy/citation/media gate. |
| `src/debugmate/results/publisher.py` | Atomic immutable result directory and deterministic ZIP creation. |
| `src/debugmate/results/verifier.py` | Public disk revalidation and strict member-ID download resolution. |
| `src/debugmate/results/service.py` | Approved-input diagnose/compose, replay, outcome-backed restore/correction, retry/download facade and idempotency. |
| `src/debugmate/ui/presentation.py` | Pure strict state-to-component value/visibility/action mapping. |
| `src/debugmate/ui/app.py` | Native Gradio 6 three-region workbench, private callbacks and responsive CSS. |
| `src/debugmate/ui/serve.py` | Runnable loopback server for `python -m debugmate.ui.serve --host 127.0.0.1 --port N`; `/config` readiness. |
| `tests/results/` | Contract, renderer, media, fallback, publisher, service, E2E and threat proofs. |
| `tests/ui/` | Pure state, structure, callback and real-browser VQ proofs. |
| `fixtures/replay/index.json` | Repository allowlist pointing through controlled relative paths to committed full outcome/source records. |
| `scripts/generate-replay-fixture.py` | Deterministically regenerate and verify the committed redacted replay outcome/source bundle. |
| `evidence/ui/phase4/` | Hashed real-browser screenshots and VQ-01..VQ-15 evidence ledger. |

## Frozen Interfaces

```python
def load_verified_outcome(
    outcome: DiagnosisRunOutcome, *, evidence_root: Path
) -> LoadedDiagnosisSource: ...

class DiagnosisOutcomeStore:
    def write(self, outcome: DiagnosisRunOutcome) -> StoredOutcomeIdentity: ...
    def read(self, run_id: str) -> DiagnosisRunOutcome: ...

def prepare_generation_context() -> PreparedGenerationContext: ...
def build_presentation(
    source: LoadedDiagnosisSource, context: PreparedGenerationContext
) -> PresentationModel: ...
def render_report(presentation: PresentationModel) -> RenderedReport: ...
def render_citations(presentation: PresentationModel) -> RenderedCitations: ...
def render_card(
    presentation: PresentationModel, context: PreparedGenerationContext, *, target: Path
) -> RenderedCard | CardRenderFailure: ...
def compose_recap(presentation: PresentationModel) -> SafeRecapText: ...
def probe_mp3(path: Path, *, timeout_seconds: float, max_bytes: int) -> MediaProbe: ...

class TtsAdapter(Protocol):
    def synthesize(
        self,
        text: SafeRecapText,
        target: Path,
        request_identity: TtsRequestIdentity,
        rate_profile: RateProfile,
    ) -> AudioCandidate: ...

class TtsFallbackChain:
    def synthesize(self, recap: SafeRecapText, target_dir: Path) -> AudioResult: ...

def validate_result_candidates(
    source: LoadedDiagnosisSource,
    presentation: PresentationModel,
    report: RenderedReport,
    citations: RenderedCitations,
    card_result: RenderedCard | CardRenderFailure,
    recap: SafeRecapText,
    audio_result: AudioResult,
) -> ValidatedResultCandidates: ...

def publish_result_bundle(
    candidates: ValidatedResultCandidates, *, results_root: Path
) -> PublishedResult: ...
def verify_result_bundle(path: Path) -> ResultVerification: ...
def resolve_verified_download(
    results_root: Path, case_id: str, result_id: str, member_id: str
) -> Path: ...

class ResultApplicationService:
    def diagnose_and_compose(
        self, approved: ApprovedRedactedInput | str
    ) -> ResultViewState: ...
    def load_replay(self, fixture_id: str) -> ResultViewState: ...
    def restore_result(self, case_id: str, result_id: str) -> ResultViewState: ...
    def correct_and_compose(
        self, previous_run_id: str, draft: CorrectionDraft, *, confirmed: bool
    ) -> ResultViewState: ...
    def retry_stage(self, case_id: str, result_id: str, scope: RetryScope) -> ResultViewState: ...
    def resolve_download(self, case_id: str, result_id: str, member_id: str) -> Path: ...

def render_view_state(state: ResultViewState) -> ComponentViewModel: ...
def build_app(service: ResultApplicationService) -> gr.Blocks: ...
```

`load_replay` has one frozen meaning: verify indexed strict outcome and Phase 3 source bundle, import full outcome into `DiagnosisOutcomeStore`, compose/publish a new `replay=true` Phase 4 result, freshly run the public result verifier, then return view state. It never restores a prebuilt Phase 4 result.

The acyclic hash graph is exact: `result-manifest.json` hashes/lists business payload only and excludes itself, checksums, ZIP and publication; `checksums.sha256` covers every ZIP member except itself and may include the manifest; outside-only `publication.json` alone stores final ZIP SHA-256 plus result identity.

## Task Sequence

### Task 1: Dependencies, contracts, source loader and Wave 0

**Files:** `pyproject.toml`, `src/debugmate/results/{__init__,contracts,font,loader,outcome_store}.py`, `tests/results/{__init__,conftest,test_contracts,test_loader}.py`, `fixtures/replay/index.json`, `fixtures/replay/module-not-found/**`, `scripts/generate-replay-fixture.py`

**Interfaces:** Produces one `PreparedGenerationContext` containing matching GenerationProfile/ResolvedFont, plus result contracts, DiagnosisOutcomeStore and LoadedDiagnosisSource.

- [ ] Write RED dependency/marker/strict-contract/loader forgery tests described in [04-01-PLAN.md](../../../.planning/phases/04-multimodal-results-ui/04-01-PLAN.md).
- [ ] Run `\.\.venv\Scripts\python.exe -m pytest -q tests\results\test_contracts.py tests\results\test_loader.py` and confirm failures name missing result contracts/loader behavior.
- [ ] Pin dependencies, generate/verify replay, and implement `prepare_generation_context()` so no caller can mix separately prepared profile/font values.
- [ ] Run the same tests GREEN, then `\.\.venv\Scripts\python.exe -m pip check` and Ruff.
- [ ] Commit each RED/GREEN unit selectively with the messages specified by 04-01.

### Task 2: Presentation, report and citations

**Files:** `src/debugmate/results/{presentation,report}.py`, `tests/results/{test_presentation,test_report}.py`, `tests/results/golden/module-not-found-report.md`

**Interfaces:** Consumes `LoadedDiagnosisSource` plus one PreparedGenerationContext; produces identity-bound presentation/report/citations.

- [ ] Write RED ordering, stable-ID, Markdown injection, command-fence and citation-forgery tests from [04-02-PLAN.md](../../../.planning/phases/04-multimodal-results-ui/04-02-PLAN.md).
- [ ] Run `\.\.venv\Scripts\python.exe -m pytest -q tests\results\test_presentation.py tests\results\test_report.py` and retain the expected RED evidence.
- [ ] Implement `build_presentation(source, context)` and reject missing/mismatched/separately passed profile/font objects.
- [ ] Review and commit the deterministic golden report, then rerun the focused suite and Ruff GREEN.
- [ ] Commit presentation, report and citation review units separately.

### Task 3: Deterministic Pillow card

**Files:** `src/debugmate/results/card.py`, `tests/results/test_card.py`, `tests/results/golden/card-layout.json`

**Interfaces:** Consumes the profile-bound PresentationModel and complete indivisible `PreparedGenerationContext`; verifies profile/font/identity equality and never resolves or recombines identity.

- [ ] Write RED font-confinement/hash, wrap/layout, metadata/frame and oversize/partial tests from [04-03-PLAN.md](../../../.planning/phases/04-multimodal-results-ui/04-03-PLAN.md).
- [ ] Run `\.\.venv\Scripts\python.exe -m pytest -q tests\results\test_card.py` and confirm renderer behavior is absent.
- [ ] Call `render_card(presentation, context, target=...)`; strict-revalidate the complete context and exact embedded profile/font identity, then layout/paint without fallback lookup or context splitting.
- [ ] Repeat render with identical input/font and compare PNG/layout hashes; reopen all output bytes.
- [ ] Run focused tests and Ruff GREEN, then commit each layout/render/failure unit.

### Task 4: Recap, real media and TTS fallback

**Files:** `src/debugmate/results/{recap,media,audio}.py`, `src/debugmate/results/tts/{__init__,base,dify,edge,sapi}.py`, `scripts/sapi-synthesize.ps1`, `tests/results/{test_recap,test_media,test_tts_chain,test_tts_live}.py`

**Interfaces:** Consumes `PresentationModel`; produces `SafeRecapText` and verified `AudioResult` with attempts/backend/reason/probe.

- [ ] Write RED six-part recap, real ffprobe boundary, adapter fallback/rate retry and all-failed tests from [04-04-PLAN.md](../../../.planning/phases/04-multimodal-results-ui/04-04-PLAN.md).
- [ ] Run `\.\.venv\Scripts\python.exe -m pytest -q tests\results\test_recap.py tests\results\test_media.py tests\results\test_tts_chain.py` and retain RED evidence.
- [ ] Implement narrow adapters and fallback with tag-free media policy; SAPI uses controlled UTF-8 input file plus fixed `-File` script argv and FFmpeg metadata stripping; keep Phase 3 audio rejection unchanged.
- [ ] Run the focused suite GREEN, then run real local `\.\.venv\Scripts\python.exe -m pytest -q -m tts tests\results\test_tts_live.py`.
- [ ] Run external `-m "(cloud or network) and tts"` separately and record pass/skip/open exactly; commit adapter/orchestrator/local-smoke units.

### Task 5: Consistency, immutable ResultBundle and deterministic ZIP

**Files:** `src/debugmate/results/{consistency,publisher,verifier}.py`, `src/debugmate/cli.py`, `tests/results/{test_consistency,test_publisher}.py`

**Interfaces:** Consumes only typed renderer results; produces `PublishedResult`, full/partial verified bundles and member-ID downloads.

- [ ] Write RED identity drift, privacy/media mutation, path/symlink, atomicity, ZIP-slip/bomb/determinism and TOCTOU download tests from [04-05-PLAN.md](../../../.planning/phases/04-multimodal-results-ui/04-05-PLAN.md).
- [ ] Run `\.\.venv\Scripts\python.exe -m pytest -q tests\results\test_consistency.py tests\results\test_publisher.py` and capture RED.
- [ ] Implement gate, independent atomic result publisher, the exact manifest→checksums→outside-publication acyclic graph, explicit ZipInfo construction and public verifier; add RED tests for each forbidden cycle edge.
- [ ] Build full/partial ZIPs twice in separate roots and require byte equality; mutate each artifact and require verification/download failure.
- [ ] Run focused tests and Ruff GREEN; commit gate, publisher/ZIP and download resolver units separately.

### Task 6: Service, replay/correction and Gradio workbench

**Files:** `src/debugmate/results/service.py`, `src/debugmate/ui/{__init__,presentation,app,serve}.py`, `tests/results/test_service.py`, `tests/ui/{__init__,test_view_state,test_app,test_callbacks}.py`

**Interfaces:** `ResultApplicationService.diagnose_and_compose` is the only live entry and accepts approved redacted input, never an outcome. Full live/replay outcomes persist in `DiagnosisOutcomeStore`; refresh/correction load by run ID. `render_view_state` is pure and `build_app` uses native Gradio 6 components.

- [ ] Write RED state matrix, approved-input diagnose-and-compose, full outcome-store, compose→refresh→correct, replay→correct, tampered-record, structural UI and callback TOCTOU tests from [04-06-PLAN.md](../../../.planning/phases/04-multimodal-results-ui/04-06-PLAN.md).
- [ ] Run `\.\.venv\Scripts\python.exe -m pytest -q tests\results\test_service.py tests\ui` and retain RED.
- [ ] Implement service-owned live flow and frozen replay flow: verify indexed outcome/source → store full outcome → compose/publish new replay=true result → fresh result verification → state.
- [ ] Implement exact runnable server `python -m debugmate.ui.serve --host 127.0.0.1 --port N`; readiness is HTTP 200 JSON at `/config` containing `version` and `components`.
- [ ] Exercise draft→summary→explicit confirmation→new run/result and tamper-after-render download failure.
- [ ] Run service/UI tests and Ruff GREEN; commit mapping, service and app/callback review units separately.

### Task 7: Offline E2E, security, real SAPI, browser VQ and independent-verifier handoff

**Files:** `tests/results/{test_result_e2e,test_security_abuse}.py`, `tests/ui/test_browser.py`, `scripts/run-phase4-browser-qa.ps1`, `evidence/ui/phase4/*`, `evidence/media/phase4/local-sapi.json`, `.planning/phases/04-multimodal-results-ui/{04-07-EXECUTION-LOG,04-07-GAPS}.md`

**Interfaces:** Exercises every public boundary from Phase 3 source through result verifier, UI and download; produces final Phase 4 evidence.

- [ ] Write RED five-state E2E and one executable public-boundary test for each T4-01..T4-14 from [04-07-PLAN.md](../../../.planning/phases/04-multimodal-results-ui/04-07-PLAN.md).
- [ ] Run focused E2E/security without production/CSS edits; any failure creates `04-07-GAPS.md` and routes to a later explicit gap plan.
- [ ] Run full offline pytest, Ruff, pip, diff, Schema/canonical-contract, secret, result-verifier and repeat-ZIP gates.
- [ ] Run fresh real local SAPI and record safe backend/voice/rate/duration/hash plus listening check; record Dify/edge gates truthfully.
- [ ] Launch the exact serve module using reserved loopback port, poll `/config` for 30s, capture PID, use Playwright/msedge and always clean browser/process/port in finally; VQ failure creates a gap and never authorizes CSS repair here.
- [ ] Complete `04-07-EXECUTION-LOG.md` and media/visual evidence, rerun every blocking gate, then hand off verdict/report creation to a fresh independent GSD verifier.

## Exact Final Gate Commands

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m pip check
git diff --check
.\.venv\Scripts\python.exe -m pytest -q -m tts tests\results\test_tts_live.py
.\.venv\Scripts\python.exe -m pytest -q -m "(cloud or network) and tts" tests\results\test_tts_live.py
.\.venv\Scripts\python.exe -m pytest -q -m browser tests\ui\test_browser.py
.\scripts\run-phase4-browser-qa.ps1
git grep -n -I -E "SECRET_SENTINEL_DO_NOT_LOG|sk-[A-Za-z0-9_-]{8,}|BEGIN( [A-Z0-9]+)* PRIVATE KEY|20795" -- src contracts fixtures knowledge prompts platform scripts README.md pyproject.toml
```

For the final `git grep`, exit code 1 means clean/no matches; 0 is blocking and any other code is an execution error. External Dify/edge clean skips remain open external gates; they do not weaken offline, real-local SAPI or browser acceptance.

## Execution Handoff

Implement with `superpowers:subagent-driven-development`: dispatch one fresh implementer per XML task in `04-01-PLAN.md` through `04-07-PLAN.md`, require a specification review and code-quality review after each task, and do not let adjacent tasks share unreviewed edits. Use selective staging and the exact focused RED/GREEN commands in each GSD plan. After all seven waves, run `superpowers:verification-before-completion`, request an independent Phase 4 code/security review, and only then allow the GSD phase verifier to mark the phase passed.

Execution agents must stop at summaries/logs/media/visual evidence. A fresh independent gsd-verifier then reads current code/evidence and creates the separate phase verdict/report.
