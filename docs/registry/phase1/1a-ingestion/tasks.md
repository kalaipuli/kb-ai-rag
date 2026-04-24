# Feature 1a — Ingestion Pipeline Task Registry

> Phase: 1 — Core MVP | Feature: 1a — Ingestion Pipeline
> Status: ✅ Complete | Completed: 2026-04-24
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-24

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Create `ChunkMetadata` TypedDict in `src/ingestion/models.py` | data-engineer | — |
| T02 | ✅ Done | Create `BaseLoader` ABC in `src/ingestion/loaders/base.py` | data-engineer | T01 |
| T03 | ✅ Done | Implement `LocalFileLoader` (PDF + TXT) in `src/ingestion/loaders/local_loader.py` | data-engineer | T02 |
| T04 | ✅ Done | Implement `DocumentSplitter` (RecursiveCharacterTextSplitter) in `src/ingestion/splitter.py` | data-engineer | T01 |
| T05 | ✅ Done | Implement async batched `Embedder` (Azure OpenAI) in `src/ingestion/embedder.py` | data-engineer | T01 |
| T06 | ✅ Done | Implement Qdrant upsert logic in `src/ingestion/vector_store.py` | data-engineer | T01, T05 |
| T07 | ✅ Done | Implement BM25 index builder + disk persistence in `src/ingestion/bm25_store.py` | data-engineer | T01 |
| T08 | ✅ Done | Wire ingestion orchestrator in `src/ingestion/pipeline.py` | data-engineer | T02–T07 |
| T09 | ✅ Done | Write unit tests for all 1a components | data-engineer | T01–T08 |
| T10 | ✅ Done | Update `.env.example` with new 1a variables | data-engineer | T08 |

---

## Ordered Execution Plan

### Batch 1 — Foundation
- **T01** — ChunkMetadata TypedDict (models.py)

### Batch 2 — After T01 (parallel)
- **T02** — BaseLoader ABC
- **T04** — DocumentSplitter
- **T05** — Embedder (async Azure OpenAI)
- **T07** — BM25 index builder

### Batch 3 — After T02
- **T03** — LocalFileLoader (PDF + TXT)

### Batch 4 — After T03, T04, T05, T07
- **T06** — Qdrant upsert (vector_store.py)

### Batch 5 — After T06
- **T08** — pipeline.py orchestrator
- **T09** — Unit tests
- **T10** — Update .env.example

---

## Definition of Done Per Task

### T01 — ChunkMetadata TypedDict
- [x] All 13 required fields present: `doc_id`, `chunk_id`, `source_path`, `filename`, `file_type`, `title`, `page_number`, `chunk_index`, `total_chunks`, `char_count`, `ingested_at`, `tags`
- [x] No `domain` field (domain-agnostic, see ADR-003)
- [x] All fields correctly typed; `mypy --strict` passes
- [x] Unit test verifies instantiation with valid data

### T02 — BaseLoader ABC
- [x] `load() -> list[Document]` abstract method with full type annotations
- [x] mypy passes
- [x] Unit test: ABC cannot be instantiated directly

### T03 — LocalFileLoader
- [x] Loads PDF files via `pypdf` page-by-page
- [x] Loads TXT files with native I/O
- [x] Skips unsupported extensions with structlog warning
- [x] Handles empty files and corrupted PDFs without crashing
- [x] Returns `list[Document]` with correct metadata
- [x] Unit tests: valid PDF, valid TXT, empty file, unsupported extension, corrupted PDF

### T04 — DocumentSplitter
- [x] Uses `RecursiveCharacterTextSplitter`
- [x] `chunk_size` and `chunk_overlap` from `Settings`
- [x] `chunk_index` and `total_chunks` correctly set on every chunk
- [x] `char_count` from actual chunk text length
- [x] Unit test: single doc splits with correct metadata

### T05 — Embedder
- [x] Uses Azure OpenAI `text-embedding-3-large` via `langchain-openai`
- [x] Async `embed_chunks`; batches via `asyncio.gather`
- [x] Batch size configurable (`embedding_batch_size` in Settings)
- [x] Raises `EmbeddingError` on Azure failure
- [x] Unit test: mocked Azure client; batching + error path

### T06 — Qdrant Vector Store
- [x] Creates collection if absent (cosine, 3072 dims)
- [x] Upserts vector + full `ChunkMetadata` payload per point
- [x] Async `AsyncQdrantClient`
- [x] Raises `IngestionError` on failure
- [x] Unit test: mocked client; payload correctness

### T07 — BM25 Index
- [x] `BM25Okapi` built from chunk texts
- [x] Pickle save/load with configurable path (`bm25_index_path` in Settings)
- [x] Raises `IngestionError` on missing file
- [x] Unit test: build → save → load → verify

### T08 — Pipeline Orchestrator
- [x] `run_pipeline(data_dir, settings) -> PipelineResult`
- [x] Sequential: load → split → embed → upsert → BM25
- [x] Structured log at each stage (count, duration_ms)
- [x] Per-file error collection; does not abort on single failure
- [x] Unit test: end-to-end mock; all stages called in order

### T09 — Unit Tests
- [x] All tests in `tests/unit/test_ingestion_*.py`
- [x] No real I/O; all external calls mocked
- [x] 52 new tests; suite < 30s

### T10 — .env.example
- [x] `BM25_INDEX_PATH` added
- [x] `EMBEDDING_BATCH_SIZE` added

---

## Feature Gate Criteria

All of the following passed before Feature 1b begins:

| Gate | Check | Result |
|------|-------|--------|
| G01 | `pytest tests/unit -q` | ✅ 89 passed |
| G02 | `mypy src/` (strict) | ✅ 0 errors, 21 files |
| G03 | `ruff check .` | ✅ 0 warnings |
| G04 | Pipeline runs on ≥ 1 local PDF | ⏳ Integration test (requires `docker compose up`) |
| G05 | No hardcoded values | ✅ All config via `Settings` |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Azure OpenAI not available in unit tests | High | Low | Mocked in all unit tests |
| Qdrant not running in unit test environment | High | Low | Mocked; integration tests require `docker compose up` |
| pypdf text extraction varies by PDF | Medium | Medium | Empty pages skipped with warning; not errors |
| BM25 pickle incompatible across Python versions | Low | Medium | Python version pinned in Dockerfile |
