# Phase 2 Validation Strategy

## Test layers

1. Contracts: strict input/privacy/source/retrieval models and no secret-bearing fields.
2. Text privacy: token/password/email/path/private-host redaction, overlap resolution and stable hashes.
3. Approval: HMAC binding, expiry, mutation invalidation and zero backend calls on rejection.
4. Image privacy: byte-format limits, fake-OCR pixel redaction, deterministic PNG and OCR failure block.
5. Knowledge: registry/schema, safe fetch, deterministic extraction/note build, coverage and sync dry-run.
6. Security: prompt injection marking, export rescan, raw-value absence from repr/log/evidence.
7. Optional live: `ocr`, `knowledge_online`, `cloud` markers remain outside the default suite.

## Default gate

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not cloud and not ocr and not knowledge_online"
.\.venv\Scripts\python.exe -m ruff check .
git diff --check
```

## Phase evidence

- Privacy tests use only generated fictional secrets and screenshots.
- Knowledge tests use local HTML fixtures; online results save URL/status/hash without full-page snapshots.
- Any cloud call observed before approval is a Critical failure.
- Any matched secret value appearing in exception, repr, audit, manifest or tracked file is a Critical failure.
