# Phase 2 Official Knowledge Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible curated-official-source pipeline that fetches approved pages, produces deterministic structured diagnostic notes, audits coverage, and prepares a deletion-safe Dify synchronization bundle.

**Architecture:** A strict source registry drives an allowlisted HTTP fetcher. BeautifulSoup extracts configured heading ranges into normalized sections; a deterministic note renderer is the default, while an optional summarizer port may provide grounded Chinese paraphrases. Immutable build directories record every source/document hash and retrieval configuration.

**Tech Stack:** HTTPX 0.28.1, BeautifulSoup 4.15.0, Pydantic 2.13.4, standard-library HTML/JSON/hash tools, pytest.

## Global Constraints

- Only the exact official domains and URLs in `knowledge/sources.json` are fetched; redirects outside the source domain fail.
- Save structured notes and short source anchors, never full-page snapshots.
- A note cannot publish without source ID, heading locator, source SHA-256 and license/terms note.
- LLM output is optional and never authoritative; deterministic generation must remain available offline.
- Dify synchronization defaults to dry-run and never deletes/overwrites without explicit confirmation.

---

### Task 1: Source Registry and Curated Official Set

**Files:**
- Modify: `pyproject.toml`
- Create: `src/debugmate/knowledge/__init__.py`
- Create: `src/debugmate/knowledge/models.py`
- Create: `knowledge/sources.json`
- Modify: `knowledge/manifest.schema.json`
- Test: `tests/knowledge/test_source_registry.py`

**Interfaces:**
- Produces: `KnowledgeSource`, `SourceRegistry`, `load_registry(path)`.

- [ ] **Step 1: Write failing strict-registry tests**

```python
def test_registry_covers_exact_product_families():
    registry = load_registry(Path("knowledge/sources.json"))
    assert {x.product for x in registry.sources} == {
        "python", "pip", "pytorch", "cuda", "huggingface", "ultralytics", "windows"
    }
    assert all(2 <= count <= 4 for count in Counter(x.product for x in registry.sources).values())
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_source_registry.py`.

- [ ] **Step 3: Implement strict models and pin BeautifulSoup**

Add `beautifulsoup4==4.15.0`. `KnowledgeSource` fields are `source_id`, `title`, `url`, `product`, `version_scope`, `platform`, `allowed_domain`, `heading_patterns`, `error_categories`, `license_or_terms_note`, `selection_reason`. Reject duplicate IDs/URLs, non-HTTPS URLs, domains not equal to URL host, missing categories and extra fields.

- [ ] **Step 4: Populate the exact first registry**

Use these verified official URLs:

```text
python-errors        https://docs.python.org/3/tutorial/errors.html
python-venv          https://docs.python.org/3/library/venv.html
python-import        https://docs.python.org/3/reference/import.html
pip-resolution       https://pip.pypa.io/en/stable/topics/dependency-resolution/
pip-user-guide       https://pip.pypa.io/en/stable/user_guide/
pytorch-cuda         https://docs.pytorch.org/docs/stable/notes/cuda.html
pytorch-serialization https://docs.pytorch.org/docs/stable/notes/serialization.html
pytorch-tensor-view  https://docs.pytorch.org/docs/stable/generated/torch.Tensor.view.html
cuda-compatibility   https://docs.nvidia.com/deploy/cuda-compatibility/
cuda-windows-install https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/
hf-installation      https://huggingface.co/docs/transformers/en/installation
hf-cache             https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache
ultralytics-install  https://docs.ultralytics.com/quickstart/
ultralytics-predict  https://docs.ultralytics.com/modes/predict/
windows-env          https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables?view=powershell-7.5
windows-policy       https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-7.5
windows-path-format  https://learn.microsoft.com/en-us/dotnet/standard/io/file-path-formats
```

Run registry tests and schema validation; expected 17 sources, 2–3 per family.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml src/debugmate/knowledge knowledge/sources.json knowledge/manifest.schema.json tests/knowledge/test_source_registry.py
git commit -m "feat(02-03): define curated official source registry"
```

### Task 2: Allowlisted Fetcher and HTML Section Extraction

**Files:**
- Create: `src/debugmate/knowledge/fetcher.py`
- Create: `src/debugmate/knowledge/extractor.py`
- Create: `tests/fixtures/knowledge/python-errors.html`
- Test: `tests/knowledge/test_fetch_extract.py`

**Interfaces:**
- Produces: `FetchedSource`, `fetch_source(source, client)`, `extract_sections(source, html)`.

- [ ] **Step 1: Write failing transport/extraction tests**

```python
def test_cross_domain_redirect_is_rejected(mock_transport, source):
    mock_transport.redirect(source.url, "https://example.com/copied")
    with pytest.raises(SourceDomainViolation): fetch_source(source, mock_transport.client)

def test_selected_headings_and_code_are_normalized(fixture_html, source):
    sections = extract_sections(source, fixture_html)
    assert sections[0].heading == "Exceptions"
    assert "Traceback" in sections[0].text
    assert sections[0].source_locator.startswith("#")
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_fetch_extract.py`.

- [ ] **Step 3: Implement safe fetch**

Use injected `httpx.Client(follow_redirects=False)`, 20-second timeout, two attempts only for connect/timeout, maximum response 2 MiB, content type `text/html`, HTTPS and exact host checks. Record final URL, status, ETag, Last-Modified, fetched UTC and raw SHA-256; do not persist full HTML outside the temporary build directory.

- [ ] **Step 4: Implement deterministic extraction**

BeautifulSoup removes `nav`, `footer`, `script`, `style`, sidebars and copy buttons. Match configured heading regexes; collect content until the next same/higher heading; normalize whitespace, preserve fenced code, limit each section to 8,000 characters and deduplicate by canonical text SHA-256. Empty matches raise `SourceStructureChanged`.

- [ ] **Step 5: Commit**

```powershell
git add src/debugmate/knowledge/fetcher.py src/debugmate/knowledge/extractor.py tests/fixtures/knowledge tests/knowledge/test_fetch_extract.py
git commit -m "feat(02-03): fetch and extract official sections"
```

### Task 3: Structured Note Builder and Reproducible Build

**Files:**
- Create: `src/debugmate/knowledge/note_builder.py`
- Create: `src/debugmate/knowledge/build.py`
- Create: `knowledge/notes/.gitkeep`
- Test: `tests/knowledge/test_note_build.py`

**Interfaces:**
- Produces: `DiagnosticNote`, `NoteSummarizer` protocol, `build_knowledge(registry, output_root, client, summarizer=None)`.

- [ ] **Step 1: Write failing golden-build tests**

```python
def test_repeated_fixture_build_is_byte_identical(tmp_path, fixture_client):
    first = build_knowledge(registry, tmp_path / "one", fixture_client)
    second = build_knowledge(registry, tmp_path / "two", fixture_client)
    assert first.content_hash == second.content_hash

def test_note_has_source_anchors_and_no_full_page(note):
    assert note.source_id and note.source_sha256 and note.locators
    assert len(note.markdown.encode()) < 32_000
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_note_build.py`.

- [ ] **Step 3: Implement deterministic renderer**

Render UTF-8 Markdown with fixed frontmatter and sections: symptoms/categories, diagnostic facts, checks, version/platform limits, source anchors, short extracted snippets. The default summarizer paraphrases using deterministic templates and never invents commands. An injected `NoteSummarizer` may return Chinese bullets only when every bullet includes a locator; invalid output falls back to templates.

- [ ] **Step 4: Implement immutable build manifest**

Build ID is SHA-256 of registry version, source hashes, extractor version and chunk settings. Write under `knowledge/build/<build_id>/` via temporary directory then atomic replace. Manifest records every note hash, source hash, document count, categories, chunk size `800`, overlap `120`, generator version and failures. A partial build is status `failed` and is not syncable.

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_note_build.py`.

- [ ] **Step 5: Commit**

```powershell
git add src/debugmate/knowledge/note_builder.py src/debugmate/knowledge/build.py knowledge/notes/.gitkeep tests/knowledge/test_note_build.py
git commit -m "feat(02-03): build structured knowledge notes"
```

### Task 4: Coverage Report, Dify Dry-run Bundle, and CLI

**Files:**
- Create: `src/debugmate/knowledge/coverage.py`
- Create: `src/debugmate/knowledge/sync.py`
- Modify: `src/debugmate/cli.py`
- Create: `scripts/build_knowledge.ps1`
- Test: `tests/knowledge/test_coverage_sync.py`

**Interfaces:**
- Produces: `coverage_report(build)`, `create_sync_plan(build, remote_manifest)`, CLI `knowledge-build`, `knowledge-coverage`, `knowledge-sync --dry-run`.

- [ ] **Step 1: Write failing coverage/safety tests**

```python
def test_coverage_reports_all_categories_and_blind_spots(build):
    report = coverage_report(build)
    assert set(report.categories) == set(ErrorCategory)
    assert report.blind_spots == sorted(report.blind_spots)

def test_sync_never_deletes_without_confirmation(build):
    plan = create_sync_plan(build, remote_manifest_with_extra_doc)
    assert plan.deletes
    with pytest.raises(SyncConfirmationRequired): execute_sync(plan, confirm_delete=False)
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_coverage_sync.py`.

- [ ] **Step 3: Implement coverage and sync plan**

Coverage reports per category: source count, note count, locator count, last fetched UTC, current build hash and blind spots. Sync plan compares `source_id` and content SHA-256 and emits `create`, `update`, `unchanged`, `delete`; default dry-run performs no HTTP calls. Real execution remains cloud-marked and requires Dify dataset key plus explicit delete confirmation.

- [ ] **Step 4: Add CLI and PowerShell wrapper**

`build_knowledge.ps1` uses `$PSScriptRoot`, `-LiteralPath`, local `.venv`, UTF-8, runs registry validation, build, coverage, offline tests and Ruff. Online fetch is opt-in `-Online`; default uses fixtures. CLI outputs ASCII-safe JSON paths as established in Phase 1.

Run: `.\scripts\build_knowledge.ps1`  
Expected: fixture build, coverage and dry-run sync plan succeed without credentials or network.

- [ ] **Step 5: Commit and final verification**

```powershell
git add src/debugmate/knowledge/coverage.py src/debugmate/knowledge/sync.py src/debugmate/cli.py scripts/build_knowledge.ps1 tests/knowledge/test_coverage_sync.py
git commit -m "feat(02-03): report coverage and prepare Dify sync"
.\.venv\Scripts\python.exe -m pytest -q -m "not cloud and not ocr"
.\.venv\Scripts\python.exe -m ruff check .
```

### Task 5: Retrieval Trace and Category Hit-rate Evaluation

**Files:**
- Create: `src/debugmate/knowledge/retrieval.py`
- Create: `knowledge/eval_queries.json`
- Modify: `src/debugmate/knowledge/coverage.py`
- Modify: `src/debugmate/evidence.py`
- Test: `tests/knowledge/test_retrieval_trace.py`

**Interfaces:**
- Produces: `RetrievalHit`, `RetrievalTrace`, `validate_retrieval_trace`, `evaluate_retrieval_cases`.

- [ ] **Step 1: Write failing trace and hit-rate tests**

```python
def test_retrieval_hit_keeps_auditable_source_fields():
    hit = RetrievalHit(chunk_id="python-errors#exceptions-0", content_summary="Traceback anatomy",
                       source_id="python-errors", source_url="https://docs.python.org/3/tutorial/errors.html",
                       locator="#exceptions", relevance_score=0.91)
    assert hit.relevance_score == 0.91

def test_category_hit_rate_and_blind_spot_are_reported():
    result = evaluate_retrieval_cases(cases, traces)
    assert result.by_category["dependency_environment"].hit_rate == 1.0
    assert "cuda_memory" in result.blind_spots
```

- [ ] **Step 2: Verify RED**

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_retrieval_trace.py`  
Expected: import fails for `debugmate.knowledge.retrieval`.

- [ ] **Step 3: Implement strict retrieval contracts and evidence export**

`RetrievalHit` requires `chunk_id`, `content_summary` capped at 500 characters, `source_id`, HTTPS `source_url`, non-empty `locator`, and strict `relevance_score` in `0..1`. `RetrievalTrace` binds `case_id`, query hash, knowledge build ID, retrieved UTC and ordered hits. `validate_retrieval_trace` rejects duplicate chunk IDs, source IDs absent from the build manifest, mismatched URLs and unsorted relevance scores. Add `EvidenceBundle.write_json("retrieval.json", trace.model_dump(mode="json"))`; no full raw chunk is stored in evidence.

- [ ] **Step 4: Implement fixed query evaluation**

`knowledge/eval_queries.json` contains at least one fictional query for each `ErrorCategory`, with expected source IDs and locators. `evaluate_retrieval_cases` computes per-category case count, top-k hit count, hit rate, uncovered expected sources, blind spots and last source-update time. Extend `knowledge-coverage` CLI to include this result when trace fixtures are provided.

Run: `.\.venv\Scripts\python.exe -m pytest -q tests/knowledge/test_retrieval_trace.py tests/knowledge/test_coverage_sync.py`  
Expected: trace validation, evidence serialization, category hit rates and deterministic blind-spot ordering pass.

- [ ] **Step 5: Commit and phase verification**

```powershell
git add src/debugmate/knowledge/retrieval.py src/debugmate/knowledge/coverage.py src/debugmate/evidence.py knowledge/eval_queries.json tests/knowledge/test_retrieval_trace.py
git commit -m "feat(02-03): trace retrieval and evaluate knowledge hit rate"
.\.venv\Scripts\python.exe -m pytest -q -m "not cloud and not ocr"
.\.venv\Scripts\python.exe -m ruff check .
```
