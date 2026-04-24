# Phase 1b — Architect Review Fixes

> Reviewed: 2026-04-24 | Reviewer: architect agent
> Scope: Phase 1a (ingestion) + Phase 1b (retrieval) integrity against goal, ADRs, and CLAUDE.md
> **Phase 1c cannot start until Critical + High issues are resolved.**

---

## Issue Tracker

| ID | Severity | Status | Title | Agent | File |
|----|----------|--------|-------|-------|------|
| F01 | 🔴 Critical | ✅ Resolved | Full chunk text never stored in Qdrant — dense retriever returns 80-char title fragments | backend-developer | `src/ingestion/vector_store.py`, `src/retrieval/dense.py` |
| F02 | 🟠 High | ✅ Resolved | `HybridRetriever` accesses private `_embeddings` attribute + uses wrong embed method | backend-developer | `src/retrieval/retriever.py`, `src/ingestion/embedder.py` |
| F03 | 🟠 High | ✅ Resolved | No error handling around Azure embedding call in `retrieve()` | backend-developer | `src/retrieval/retriever.py` |
| F04 | 🟠 High | ✅ Resolved | `chunk_id` fallback to `point.id` in `DenseRetriever` creates silent payload contract breach | backend-developer | `src/retrieval/dense.py` (line 77) |
| F05 | 🟠 High | ✅ Resolved | `QueryRequest` / `QueryResponse` schemas absent — required before Phase 1c chain implementation | backend-developer | `src/api/schemas.py` |
| F06 | 🟡 Medium | ✅ Resolved | `conftest.py` missing `bm25_index_path` and `embedding_vector_size` explicit values | tester | `tests/conftest.py` |
| F07 | 🟡 Medium | ✅ Resolved | RRF test lacks exact score-accumulation assertion for chunk appearing in both lists | tester | `tests/unit/test_retrieval_hybrid.py` |
| F08 | 🟡 Medium | ✅ Resolved | No end-to-end test for `retrieve()` when both dense and sparse return empty | tester | `tests/unit/test_retrieval_retriever.py` |
| F09 | 🟡 Medium | ✅ Resolved | RRF empty test covers `[]` outer list, not `[[], []]` (actual call-site shape) | tester | `tests/unit/test_retrieval_hybrid.py` |
| F10 | 🟡 Medium | ✅ Resolved | `CrossEncoderReranker.rerank()` empty-input guard is untested | tester | `tests/unit/test_retrieval_reranker.py` |
| F11 | 🔵 Low | ✅ Resolved | `DenseRetriever` error test uses only `RuntimeError` — missing `__cause__` chain assertion | tester | `tests/unit/test_retrieval_dense.py` |
| F12 | 🔵 Low | ✅ Resolved | `CORS allow_origins=["*"]` hardcoded — must be config-driven | backend-developer | `src/api/main.py` |
| F13 | 🔵 Low | ✅ Resolved | Two conflicting test settings conventions (`Settings` vs `MagicMock`) across test files | tester | `tests/conftest.py`, retrieval test files |

---

## Detailed Fixes

---

### F01 — Full chunk text never stored in Qdrant
**Severity**: 🔴 Critical — blocks Phase 1c
**Agent**: backend-developer

**Root cause**: `QdrantVectorStore.upsert()` stores `dict(chunk.metadata)` as the Qdrant payload. `ChunkMetadata` contains `title` (first 80 chars of text) but NOT the full chunk text. `DenseRetriever` therefore sets `RetrievalResult.text = payload.get("title", "")` — an 80-character fragment. The cross-encoder re-ranker and Phase 1c generator both operate on this truncated text.

**Fix**:
1. In `src/ingestion/vector_store.py`, change the payload construction to include the full text:
   ```python
   payload = {**dict(chunk.metadata), "text": chunk.text}
   ```
2. In `src/retrieval/dense.py`, read text from the expanded payload:
   ```python
   text=str(payload.get("text", payload.get("title", ""))),
   ```
3. Add a unit test asserting `"text"` key is present in the upserted payload (in `test_ingestion_vector_store.py`).

**Why not add `text` to `ChunkMetadata`**: `ChunkMetadata` is a Qdrant payload contract TypedDict. Adding `text` to it would make `text` a required field in every metadata construction site across all tests — too broad a change. A parallel key in the payload (outside the TypedDict) is the correct approach.

---

### F02 — Private `_embeddings` access + wrong embed method
**Severity**: 🟠 High
**Agent**: backend-developer

**Root cause**: `retriever.py:58` calls `self._embedder._embeddings.aembed_documents([query])`. This accesses the private `_embeddings` attribute of `Embedder` and uses the batch-documents method instead of the semantically correct `aembed_query()`.

**Fix**:
1. Add to `src/ingestion/embedder.py`:
   ```python
   async def embed_query(self, query: str) -> list[float]:
       """Embed a single query string for retrieval."""
       try:
           return await self._embeddings.aembed_query(query)
       except Exception as exc:
           logger.error("query_embedding_failed", error=str(exc))
           raise EmbeddingError(f"Azure OpenAI query embedding failed: {exc}") from exc
   ```
2. In `src/retrieval/retriever.py`, replace line 58:
   ```python
   query_vector = await self._embedder.embed_query(query)
   ```
3. Update `test_retrieval_retriever.py` embedder mock to mock `embed_query` instead of `_embeddings.aembed_documents`.

---

### F03 — No error handling around embed call in `retrieve()`
**Severity**: 🟠 High
**Agent**: backend-developer

**Root cause**: After applying F02, `embed_query()` will raise `EmbeddingError` on Azure failure. `retrieve()` must catch this and re-raise as `RetrievalError` so the API layer returns a structured 503, not an unhandled 500.

**Fix** (in `src/retrieval/retriever.py`, wrap the embed call):
```python
from src.exceptions import EmbeddingError, RetrievalError

try:
    query_vector = await self._embedder.embed_query(query)
except EmbeddingError as exc:
    raise RetrievalError(f"Query embedding failed: {exc}") from exc
```

---

### F04 — `chunk_id` fallback to `point.id` is a maintenance hazard
**Severity**: 🟠 High
**Agent**: backend-developer

**Root cause**: `dense.py:77` uses `payload.get("chunk_id", point.id)`. The fallback to `point.id` silently masks a missing payload key, which could cause RRF deduplication to use the Qdrant internal ID instead of the canonical `chunk_id`, producing phantom duplicates in fused results.

**Fix** (in `src/retrieval/dense.py`, line 77):
```python
# Before
chunk_id=str(payload.get("chunk_id", point.id)),

# After
chunk_id=str(payload["chunk_id"]),
```
Wrap inside the `try/except` block already surrounding the Qdrant call, so a `KeyError` on missing `chunk_id` becomes a `RetrievalError`.

---

### F05 — API schemas absent for Phase 1c
**Severity**: 🟠 High
**Agent**: backend-developer

**Root cause**: `schemas.py` only contains `HealthResponse` and `ErrorResponse`. Phase 1c `RetrievalQA` chain must produce output conforming to a stable schema or Phase 1d will face breaking changes.

**Fix** (add to `src/api/schemas.py`):
```python
class QueryRequest(BaseModel):
    query: str
    filters: dict[str, str] | None = None
    k: int | None = None

class CitationItem(BaseModel):
    chunk_id: str
    filename: str
    source_path: str
    page_number: int

class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[CitationItem]
    confidence: float
```
Add unit tests asserting schema instantiation and serialisation.

---

### F06 — `conftest.py` missing explicit retrieval + path settings
**Severity**: 🟡 Medium
**Agent**: tester

**Fix**: Add to `_make_test_settings()` in `tests/conftest.py`:
```python
bm25_index_path="/tmp/test-bm25.pkl",
embedding_vector_size=3072,
retrieval_top_k=10,
reranker_top_k=5,
reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
rrf_k=60,
```
(Note: `retrieval_top_k`, `reranker_top_k`, `reranker_model`, `rrf_k` may already have been added by the 1b implementation — verify and fill the gap for `bm25_index_path` and `embedding_vector_size`.)

---

### F07 — RRF missing exact score assertion for chunk in both lists
**Severity**: 🟡 Medium
**Agent**: tester

**Fix**: Add to `test_retrieval_hybrid.py`:
```python
def test_rrf_chunk_in_both_lists_accumulates_score_correctly(self) -> None:
    shared = _make_result("shared", score=0.0)
    list1 = [shared]           # rank 0 in list1: score += 1/(60+0+1) = 1/61
    list2 = [shared]           # rank 0 in list2: score += 1/(60+0+1) = 1/61
    results = reciprocal_rank_fusion([list1, list2], k=60)
    assert len(results) == 1
    assert results[0].chunk_id == "shared"
    assert results[0].score == pytest.approx(2.0 / 61, rel=1e-6)
```

---

### F08 — No `retrieve()` test for both-empty path
**Severity**: 🟡 Medium
**Agent**: tester

**Fix**: Add to `TestHybridRetriever` in `test_retrieval_retriever.py`:
```python
def test_retrieve_returns_empty_when_no_results_found(self) -> None:
    # mock dense and sparse both returning []
    # assert retrieve() returns [] without raising
```

---

### F09 — RRF empty test covers wrong shape
**Severity**: 🟡 Medium
**Agent**: tester

**Fix**: Add alongside the existing empty test:
```python
def test_rrf_two_empty_inner_lists_returns_empty(self) -> None:
    assert reciprocal_rank_fusion([[], []], k=60) == []
```

---

### F10 — Reranker empty-input guard untested
**Severity**: 🟡 Medium
**Agent**: tester

**Fix**: Add to `TestCrossEncoderReranker`:
```python
def test_rerank_empty_results_returns_empty(self) -> None:
    with patch("src.retrieval.reranker.CrossEncoder"):
        reranker = CrossEncoderReranker("test-model")
        assert reranker.rerank("query", [], top_k=5) == []
```

---

### F11 — Dense error test missing `__cause__` assertion
**Severity**: 🔵 Low
**Agent**: tester

**Fix**: In `test_retrieval_dense.py`, add to the error test:
```python
assert exc_info.value.__cause__ is not None
```
Optionally add a second parameterised case with `ConnectionError`.

---

### F12 — CORS origins hardcoded to `["*"]`
**Severity**: 🔵 Low
**Agent**: backend-developer

**Fix**:
1. Add `cors_origins: list[str] = ["*"]` to `Settings` in `config.py`.
2. Add `CORS_ORIGINS=*` to `.env.example`.
3. Replace `allow_origins=["*"]` in `main.py` with `allow_origins=settings.cors_origins`.

---

### F13 — Two conflicting test settings conventions
**Severity**: 🔵 Low
**Agent**: tester

**Fix**: Document the convention in `tests/conftest.py` with a comment:
- **Integration-adjacent tests** (routes, middleware): use `mock_settings` fixture → real `Settings` object
- **Pure-unit retrieval tests**: local `_make_settings()` returning `MagicMock` is acceptable to avoid `Settings` validation overhead

No code change required — add a comment block to `conftest.py` stating this convention so Phase 1c test authors know which pattern to follow.

---

## Resolution Order

```
Phase 1c PRE-REQUISITES (must merge before any 1c code):
  F01 → (same PR) F02 → F03 → F04
  F05 (separate PR: API schemas)

Phase 1c PARALLEL (fix alongside 1c work, before Phase 2 gate):
  F06, F07, F08, F09, F10

Phase 2 PRE-REQUISITES (before Phase 2 gate):
  F11, F12, F13
```
