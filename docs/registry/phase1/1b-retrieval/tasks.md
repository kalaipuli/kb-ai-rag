# Feature 1b — Hybrid Retrieval Task Registry

> Phase: 1 — Core MVP | Feature: 1b — Hybrid Retrieval
> Status: ✅ Complete | Started: 2026-04-24 | Completed: 2026-04-24
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-24

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Create task registry + update DASHBOARD | project-manager | — |
| T02 | ✅ Done | Add retrieval config fields to `src/config.py` | backend-developer | T01 |
| T03 | ✅ Done | Create `RetrievalResult` model in `src/retrieval/models.py` | backend-developer | T01 |
| T04 | ✅ Done | Implement `DenseRetriever` in `src/retrieval/dense.py` | backend-developer | T03 |
| T05 | ✅ Done | Implement `SparseRetriever` in `src/retrieval/sparse.py` | backend-developer | T03 |
| T06 | ✅ Done | Implement `reciprocal_rank_fusion()` in `src/retrieval/hybrid.py` | backend-developer | T03 |
| T07 | ✅ Done | Implement `CrossEncoderReranker` in `src/retrieval/reranker.py` | backend-developer | T03 |
| T08 | ✅ Done | Implement `HybridRetriever` orchestrator in `src/retrieval/retriever.py` | backend-developer | T04–T07 |
| T09 | ✅ Done | Create `src/retrieval/__init__.py` exporting public API | backend-developer | T08 |
| T10 | ✅ Done | Write unit tests for all 1b components (6 test files) | backend-developer | T03–T09 |
| T11 | ✅ Done | Update `.env.example` + run mypy, ruff, pytest gates | backend-developer | T10 |

---

## Ordered Execution Plan

### Batch 1 — Foundation (parallel)
- **T02** — Add retrieval config fields (`retrieval_top_k`, `reranker_top_k`, `reranker_model`, `rrf_k`)
- **T03** — `RetrievalResult` Pydantic model (canonical output of all searchers)

### Batch 2 — Retrieval components (parallel, after T02 + T03)
- **T04** — `DenseRetriever` — async Qdrant cosine search
- **T05** — `SparseRetriever` — BM25 keyword search over loaded index
- **T06** — `reciprocal_rank_fusion()` — pure function, no I/O, RRF merge
- **T07** — `CrossEncoderReranker` — `sentence_transformers.CrossEncoder` wrapper

### Batch 3 — Orchestrator (after T04–T07)
- **T08** — `HybridRetriever` — embed query → dense+sparse → RRF → rerank

### Batch 4 — Package + tests + gates (after T08)
- **T09** — `src/retrieval/__init__.py`
- **T10** — 6 unit test files
- **T11** — `.env.example`, mypy, ruff, pytest

---

## Module Design

### `src/retrieval/models.py` — RetrievalResult
```python
class RetrievalResult(BaseModel):
    chunk_id: str
    text: str
    metadata: ChunkMetadata
    score: float        # RRF score (pre-rerank) or cross-encoder score (post-rerank)
    rank: int = 0       # 0-based final rank
```

### `src/retrieval/dense.py` — DenseRetriever
- `AsyncQdrantClient` (reuse pattern from `vector_store.py`)
- `async search(query_vector, k, filters) -> list[RetrievalResult]`
- Raises `RetrievalError` on Qdrant failure

### `src/retrieval/sparse.py` — SparseRetriever
- Accepts a loaded `BM25Store` (dependency-injected, not created internally)
- `search(query, k) -> list[RetrievalResult]` — synchronous (BM25 is CPU-only)
- Tokenises query as `query.lower().split()` (matches build-time tokenisation)
- Raises `RetrievalError` when BM25 index is not built

### `src/retrieval/hybrid.py` — RRF
- Pure function: `reciprocal_rank_fusion(result_lists, k=60) -> list[RetrievalResult]`
- Score formula: `score += 1 / (k + rank)` for each list where chunk appears
- Deduplicates by `chunk_id`; merges metadata from first occurrence

### `src/retrieval/reranker.py` — CrossEncoderReranker
- `__init__(model_name: str)` — loads `CrossEncoder` lazily on first call
- `rerank(query, results, top_k) -> list[RetrievalResult]` — synchronous CPU inference
- Updates `score` and `rank` fields on returned results

### `src/retrieval/retriever.py` — HybridRetriever
- `__init__(settings, bm25_store, embedder)` — owns `DenseRetriever` + `SparseRetriever` + `CrossEncoderReranker`
- `async retrieve(query, k=None, filters=None) -> list[RetrievalResult]`
  1. `embedder._embeddings.aembed_query(query)` → query vector
  2. Dense search top `retrieval_top_k`
  3. Sparse search top `retrieval_top_k`
  4. `reciprocal_rank_fusion([dense_results, sparse_results], k=rrf_k)`
  5. `reranker.rerank(query, fused, top_k=reranker_top_k)`
- `async close()` — closes Qdrant client

### Config additions (`src/config.py`)
```python
retrieval_top_k: int = 10          # results from each retriever before fusion
reranker_top_k: int = 5            # final results returned after re-ranking
reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
rrf_k: int = 60                    # RRF constant (larger = less aggressive rank weighting)
```

---

## Unit Test Plan

| File | Tests | Key assertions |
|------|-------|----------------|
| `test_retrieval_models.py` | 3 | Valid creation, score default, required fields |
| `test_retrieval_dense.py` | 4 | Mock Qdrant search → correct results, empty list, RetrievalError on failure, filters passed |
| `test_retrieval_sparse.py` | 5 | Correct top-k ranking, empty query, RetrievalError when index None, score ordering, k limit |
| `test_retrieval_hybrid.py` | 6 | Two lists → correct RRF scores, empty lists, single list, duplicate chunk_id merge, k param, rank ordering |
| `test_retrieval_reranker.py` | 4 | Mocked CrossEncoder, top_k truncation, score updated, rank ordering |
| `test_retrieval_retriever.py` | 5 | Full pipeline mock, k override, filters forwarded, empty results, close propagates |

---

## Definition of Done Per Task

### T02 — Config
- [x] `retrieval_top_k`, `reranker_top_k`, `reranker_model`, `rrf_k` added with correct defaults
- [x] `conftest.py` `_make_test_settings` updated to include new fields

### T03 — RetrievalResult model
- [x] All fields typed; `mypy --strict` passes
- [x] Unit test verifies instantiation

### T04 — DenseRetriever
- [x] `async search(...)` returns `list[RetrievalResult]` sorted by score descending
- [x] Raises `RetrievalError` on Qdrant failure
- [x] Filters optionally passed to Qdrant query
- [x] Unit test: mocked client, payload mapping correct

### T05 — SparseRetriever
- [x] `search(query, k)` returns top-k by BM25 score
- [x] Raises `RetrievalError` when `store.index is None`
- [x] Token lowercasing consistent with BM25 build step
- [x] Unit test: real BM25Store in-memory (no I/O mocking needed)

### T06 — RRF
- [x] Correct score accumulation across multiple result lists
- [x] Deduplication by `chunk_id`
- [x] Output sorted by RRF score descending
- [x] Unit test: deterministic input → verified expected output

### T07 — CrossEncoderReranker
- [x] Synchronous `rerank()` using `CrossEncoder.predict()`
- [x] Returns exactly `min(top_k, len(results))` items
- [x] Updates both `score` and `rank` fields
- [x] Unit test: mocked CrossEncoder

### T08 — HybridRetriever
- [x] Full pipeline: embed → dense → sparse → RRF → rerank
- [x] Structured log at each stage
- [x] `close()` propagates to `DenseRetriever`
- [x] Unit test: all sub-components mocked

### T09 — `__init__.py`
- [x] Exports `HybridRetriever`, `RetrievalResult`

### T10 — Unit tests
- [x] All tests in `tests/unit/test_retrieval_*.py`
- [x] No real I/O; all external calls mocked
- [x] Suite passes in < 30s

### T11 — Quality gates
- [x] `pytest tests/unit -q` — all green
- [x] `mypy src/` — 0 errors
- [x] `ruff check .` — 0 warnings
- [x] `.env.example` updated with new retrieval variables

---

## Feature Gate Criteria

| Gate | Check | Result |
|------|-------|--------|
| G01 | `pytest tests/unit -q` | ✅ 118 passed |
| G02 | `mypy src/` (strict) | ✅ 0 errors, 28 files |
| G03 | `ruff check .` | ✅ 0 warnings |
| G04 | `.env.example` updated | ✅ RETRIEVAL_TOP_K, RERANKER_TOP_K, RERANKER_MODEL, RRF_K |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `sentence-transformers` CrossEncoder slow on CPU first call | Medium | Low | Model loaded once; unit tests mock it |
| HuggingFace model download fails in CI | Low | Medium | Model name in config; CI can set `TRANSFORMERS_OFFLINE=1` with cached model |
| BM25 token mismatch (build vs query) | Low | High | Both use `.lower().split()` — enforced by test |
| Qdrant `ScoredPoint` payload structure changes | Low | Medium | Tested with mocked client; integration test catches real divergence |
