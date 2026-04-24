# Feature 1a — Architect Review Fixes

> Reviewed by: architect agent | Date: 2026-04-24
> Fixes applied: 2026-04-24 | All F01–F07 resolved ✅

---

## Overall Assessment

**PASS WITH MINOR ISSUES** — Implementation is structurally sound. All critical contracts (BaseLoader, ChunkMetadata schema, domain-agnostic metadata, config isolation, structlog) are correctly applied. No critical findings. Seven targeted fixes required before Phase 1 gate.

---

## Findings

| ID | Severity | File | Assigned To | Status |
|----|----------|------|-------------|--------|
| F01 | MAJOR | `src/ingestion/loaders/local_loader.py:85,127` | data-engineer | ✅ Resolved |
| F02 | MINOR | `src/ingestion/loaders/local_loader.py:33` | data-engineer | ✅ Resolved |
| F03 | MINOR | `src/ingestion/vector_store.py:20` | data-engineer | ✅ Resolved |
| F04 | MINOR | `src/ingestion/pipeline.py:171` | data-engineer | ✅ Resolved |
| F05 | MINOR | `src/config.py:19,29` | backend-developer | ✅ Resolved |
| F06 | MINOR | `src/ingestion/pipeline.py:119-145` | data-engineer | ✅ Resolved |
| F07 | MINOR | `tests/unit/test_ingestion_pipeline.py` | test-manager | ✅ Resolved |
| F08 | OBSERVATION | `src/config.py:54` | backend-developer | Awareness only |
| F09 | OBSERVATION | `src/ingestion/vector_store.py:54-59` | data-engineer | Backlog (Phase 2) |

---

## Detailed Findings

### F01 — Blocking I/O on the async event loop [MAJOR]
**File:** `src/ingestion/loaders/local_loader.py` (lines 85, 127)
**Issue:** `_load_pdf` calls `pypdf.PdfReader(...)` and `_load_txt` calls `file_path.read_text(...)` as synchronous blocking calls inside `async def load()`. These block the event loop thread under load.
**Rule violated:** CLAUDE.md — "All I/O operations are `async` — file reads included."
**Fix:** Wrap `_load_pdf` and `_load_txt` dispatches with `asyncio.to_thread(...)`. The helper methods themselves can remain synchronous; the dispatch from `load()` must be async.
**Assigned to:** data-engineer

---

### F02 — `Settings` injected into `LocalFileLoader` but never used [MINOR]
**File:** `src/ingestion/loaders/local_loader.py` (line 33–35)
**Issue:** `__init__` accepts and stores `settings: Settings` as `self._settings` but no method reads it. Orphaned code that will mislead future loader implementors.
**Rule violated:** CLAUDE.md §8 — "Do not write code that is not yet called or tested — it will rot and mislead."
**Fix:** Remove `settings` parameter and `self._settings`. Update any test that passes settings to `LocalFileLoader`.
**Assigned to:** data-engineer

---

### F03 — `_VECTOR_SIZE = 3072` hardcoded in `vector_store.py` [MINOR]
**File:** `src/ingestion/vector_store.py` (line 20)
**Issue:** Hardcoded to `text-embedding-3-large` dims. If embedding deployment changes, the Qdrant collection schema silently mismatches.
**Rule violated:** CLAUDE.md — "No hardcoded values. All configuration lives in `src/config.py`."
**Fix:** Add `embedding_vector_size: int = 3072` to `Settings`. Read `settings.embedding_vector_size` in `QdrantVectorStore`. Update `.env.example`.
**Assigned to:** data-engineer

---

### F04 — `print()` in pipeline `__main__` block [MINOR]
**File:** `src/ingestion/pipeline.py` (line 171)
**Issue:** `print(result.model_dump_json(indent=2))` violates the structlog-only rule. The `# noqa: T201` suppressor papers over a real violation.
**Rule violated:** CLAUDE.md — "Never use `print()` or `logging.info()` directly."
**Fix:** Replace with `logger.info("pipeline_result", **result.model_dump())`. Remove the `# noqa` suppressor.
**Assigned to:** data-engineer

---

### F05 — API keys stored as plain `str` instead of `SecretStr` [MINOR]
**File:** `src/config.py` (lines 19, 29); downstream: `src/ingestion/embedder.py`
**Issue:** `azure_openai_api_key: str` and `api_key: str` expose secrets in stack traces, `model_dump()` calls, and any structured log that serialises settings. The `# type: ignore[arg-type]` in `embedder.py:26` exists because `AzureOpenAIEmbeddings` expects `SecretStr` — the ignore is papering over this mismatch.
**Rule violated:** CLAUDE.md — defence-in-depth for secret handling; will spread to auth middleware when `api_key` is compared in request handlers.
**Fix:** Change both fields to `SecretStr` (from `pydantic`). Remove `# type: ignore[arg-type]` in `embedder.py`. Update call sites to use `.get_secret_value()`.
**Assigned to:** backend-developer

---

### F06 — Upsert failure leaves BM25 index in inconsistent state [MINOR]
**File:** `src/ingestion/pipeline.py` (lines 119–145)
**Issue:** When `QdrantVectorStore.upsert` raises (caught and added to `errors`), the pipeline continues and persists the BM25 index. Result: BM25 has hits with no corresponding dense vectors in Qdrant — hybrid retrieval will be broken silently.
**Rule violated:** CLAUDE.md data-consistency principle; "Never silently swallow exceptions."
**Fix:** After the upsert stage, if `errors` is non-empty, log a warning and return `PipelineResult` early — do not build or save the BM25 index.
**Assigned to:** data-engineer

---

### F07 — Pipeline tests missing upsert-failure and BM25-failure paths [MINOR]
**File:** `tests/unit/test_ingestion_pipeline.py`
**Issue:** Error path coverage misses: (a) upsert raising `IngestionError`, (b) `BM25Store.save()` raising `OSError`. These are the paths that exercise F06's fix.
**Rule violated:** CLAUDE.md §3 — "Every task has at least one corresponding test."
**Fix:** Add `test_upsert_failure_adds_error_and_skips_bm25` and `test_bm25_save_failure_adds_error`.
**Assigned to:** test-manager

---

### F08 — `type: ignore[call-arg]` on `get_settings()` [OBSERVATION]
**File:** `src/config.py` (line 54)
**Issue:** Suppressor is correct for pydantic-settings pattern but broad. No action required. If a pydantic-settings mypy plugin becomes available, migrate to remove it.
**Assigned to:** backend-developer (awareness only)

---

### F09 — HNSW tuning constants not config-driven [OBSERVATION — Backlog]
**File:** `src/ingestion/vector_store.py` (lines 54–59)
**Issue:** `m=16`, `ef_construct=100`, `indexing_threshold=10_000` are hardcoded. Performance-tuning only — not a correctness issue.
**Fix:** Defer to Phase 2. Record as backlog.
**Assigned to:** data-engineer (Phase 2 backlog)

---

## Gate Recommendation

**CLEAR TO PROCEED to Feature 1b**, with conditions:

- **F01** must be resolved before Feature 1b integration tests are written — event-loop stalls will cause intermittent failures.
- **F05** must be resolved before the API layer (`/api/v1/ingest`) is wired — the `type: ignore` in `embedder.py` will spread to the auth middleware.
- **F06 + F07** should be resolved together in one commit before the Phase 1 MVP gate.
- **F02, F03, F04** can be batched into a single cleanup commit alongside F06/F07.

---

## Resolution Log

| ID | Resolved By | Date | Notes |
|----|-------------|------|-------|
| F01 | data-engineer | 2026-04-24 | `asyncio.to_thread()` wraps `_load_pdf` and `_load_txt` dispatch in `load()` |
| F02 | data-engineer | 2026-04-24 | Removed `settings` param and `self._settings`; updated tests and `pipeline.py` instantiation |
| F03 | data-engineer | 2026-04-24 | Added `embedding_vector_size: int = 3072` to `Settings`; removed `_VECTOR_SIZE` constant; updated `.env.example` |
| F04 | data-engineer | 2026-04-24 | Replaced `print()` + `# noqa` with `logger.info("pipeline_complete", **result.model_dump())` |
| F05 | backend-developer | 2026-04-24 | `azure_openai_api_key` and `api_key` changed to `SecretStr`; `# type: ignore` removed from `embedder.py`; auth middleware uses `.get_secret_value()` |
| F06 | data-engineer | 2026-04-24 | Upsert failure now triggers early return via `upsert_failed` flag before BM25 stage |
| F07 | test-manager | 2026-04-24 | Added `test_upsert_failure_adds_error_and_skips_bm25` and `test_bm25_save_failure_adds_error`; BM25 stage also hardened with try/except |

**Final gate result:** 91 tests passed · mypy strict 0 errors · ruff 0 warnings
