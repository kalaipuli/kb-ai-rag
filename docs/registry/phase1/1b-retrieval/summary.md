# Phase 1b — Hybrid Retrieval Pipeline — Retrospective Summary

> Date: 2026-04-24 | Phase: 1b | Feature: retrieval | Gate Status: Passed

---

## Feature Summary

Phase 1b delivers the complete hybrid retrieval pipeline for the kb-ai-rag platform, implementing the four-stage query path specified in ADR-003: dense Qdrant cosine search, BM25 sparse keyword search, Reciprocal Rank Fusion of both result sets, and a CPU-based cross-encoder re-ranker. The pipeline is exposed through a single `HybridRetriever.retrieve(query, k, filters)` coroutine that encapsulates the full embed → search → fuse → rerank flow, producing a ranked `list[RetrievalResult]` ready for Phase 1c's generation chain. This feature is architecturally critical because retrieval quality directly determines RAGAS faithfulness and context precision — the primary MVP gate metrics. By combining dense (semantic) and sparse (lexical) signals and re-ranking with a cross-encoder, the system can recall both paraphrase queries and exact-match technical lookups such as error codes and model names, which pure dense retrieval consistently misses.

---

## Architecture

| Item | Detail |
|------|--------|
| Pattern | Synchronous BM25 search + async Qdrant dense search fused via pure RRF function, then re-ranked by CPU cross-encoder |
| Components | `src/retrieval/models.py`, `src/retrieval/dense.py`, `src/retrieval/sparse.py`, `src/retrieval/hybrid.py`, `src/retrieval/reranker.py`, `src/retrieval/retriever.py`, `src/retrieval/__init__.py` |
| AgentState changes | None — retrieval is a library used by Phase 2 agent nodes, not directly wired into AgentState yet |
| ADRs governing this feature | ADR-003: Hybrid Retrieval with RRF Fusion (Dense + BM25) |
| Cross-cutting contracts changed | `ChunkMetadata` payload in Qdrant extended with `"text": chunk.text` (outside TypedDict); `Embedder` gained public `embed_query()` method; `schemas.py` gained `QueryRequest`, `CitationItem`, `QueryResponse` |

---

## Design

| Item | Detail |
|------|--------|
| Key files | `backend/src/retrieval/retriever.py`, `backend/src/retrieval/hybrid.py`, `backend/src/retrieval/dense.py`, `backend/src/retrieval/sparse.py`, `backend/src/retrieval/reranker.py`, `backend/src/ingestion/vector_store.py`, `backend/src/ingestion/embedder.py`, `backend/src/api/schemas.py` |
| Libraries / versions | `qdrant-client^1.11` (already pinned), `rank-bm25^0.2` (already pinned), `sentence-transformers^3.3` (already pinned) — no new dependencies introduced |
| Settings fields added | `retrieval_top_k=10` (`RETRIEVAL_TOP_K`), `reranker_top_k=5` (`RERANKER_TOP_K`), `reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2"` (`RERANKER_MODEL`), `rrf_k=60` (`RRF_K`), `cors_origins=["*"]` (`CORS_ORIGINS`) |
| Tasks driving this design | T01–T11 from [tasks.md](tasks.md) |
| Findings that shaped the design | F01 (chunk text payload gap), F02 (public embed_query method), F03 (error guard in retrieve), F04 (strict chunk_id lookup), F05 (API schemas before Phase 1c) from [fixes.md](fixes.md) |

**Key design decisions:**

- **`text` stored as parallel Qdrant payload key** (not in `ChunkMetadata` TypedDict): adding to the TypedDict would require updating every metadata construction site in tests; a parallel key `"text": chunk.text` alongside `dict(chunk.metadata)` preserves the TypedDict contract while making full text available to the dense retriever and re-ranker.
- **`SparseRetriever` is synchronous**: BM25 scoring (`rank-bm25`) is pure CPU computation with no I/O; wrapping it in `asyncio.run_in_executor` would add complexity with no benefit for Phase 1.
- **`CrossEncoderReranker` loaded eagerly at init**: model weights (~85MB) are loaded once when `HybridRetriever` is constructed, not on first query, to avoid cold-start latency on the first real request.
- **RRF `k=60` is the ADR-specified constant** — no tuning parameter exposed in Phase 1; the constant is config-driven via `Settings.rrf_k` for future tuning without code changes.
- **`QueryRequest`/`QueryResponse` schemas defined in Phase 1b** (F05): the API contract must be stable before Phase 1c chain implementation begins, per CLAUDE.md schema-before-implementation rule.

---

## Phase Gate Evidence

| Command | Result |
|---------|--------|
| `poetry run ruff check .` | ✅ zero warnings |
| `poetry run ruff format . --check` | ✅ clean |
| `poetry run mypy src/` | ✅ zero errors, 28 source files |
| `poetry run pytest tests/unit -q` | ✅ 131 passed in 3.62s |
| `npm run tsc -- --noEmit` | N/A — no frontend changes in this phase |

See gate criteria: [tasks.md](tasks.md)

---

## Open Questions / Deferred Decisions

- **BM25 → Qdrant sparse vectors (SPLADE) migration** — ADR-003 explicitly defers this to Phase 3; the in-memory BM25 index will be replaced with Qdrant native sparse vectors when the `AzureSearchRetriever` and `BaseRetriever` ABC are introduced.
- **Cross-encoder GPU inference** — CPU inference is ~100–200ms per query, acceptable for P95 < 8s locally; if load testing shows P95 breach, `sentence-transformers` can switch to GPU via `device="cuda"` — deferred to Phase 6 production hardening.
- **`HuggingFace` model download in CI** — the `ms-marco-MiniLM-L-6-v2` model (~85MB) is downloaded on first run; CI may need `TRANSFORMERS_OFFLINE=1` with a cached model layer in the Docker build — deferred to Phase 7 (CI/CD).
- **CORS origins restriction** — `CORS_ORIGINS=*` is the default; must be restricted to the Next.js frontend URL in production — deferred to Phase 6 security hardening.
- **`text` field not indexed in Qdrant** — full chunk text is stored as a payload key but not indexed for keyword filtering; this is intentional (BM25 handles keyword search), but if Qdrant full-text payload search is desired in Phase 3, the field will need a payload index — deferred to Phase 3.

---

## What Went Well

- **All required dependencies (`qdrant-client`, `rank-bm25`, `sentence-transformers`) were already pinned in `pyproject.toml`** from Phase 0 scaffolding, so Phase 1b required zero new package additions and no `poetry lock` churn.
- **The `BM25Store` data model from Phase 1a** (storing `ChunkedDocument` objects parallel to the BM25 corpus rows) made `SparseRetriever` trivial to implement — chunk metadata and full text were directly available without any secondary lookup.
- **The architect review caught the critical `text` payload gap (F01) before any Phase 1c generation code was written**, preventing a scenario where the entire generation and RAGAS evaluation pipeline would have been silently operating on 80-character title fragments.

---

## What Could Be Improved

- **The initial `HybridRetriever` accessed `_embedder._embeddings` directly (F02)**: the `Embedder` class should have exposed `embed_query()` as a public method from the start — the omission was caught only in the architect review, not during implementation, suggesting the implementation spec should have included the query-path interface alongside the ingest-path interface.
- **The RRF test suite initially lacked exact score-accumulation assertions (F07) and tested the wrong empty-list shape (F09)**: the test plan specified "deterministic input → verified expected output" but the initial tests only asserted rank order — a more precise test spec (with expected float values) would have caught formula regressions earlier.
- **The `chunk_id` silent fallback to `point.id` (F04) and the missing error guard around the embed call (F03)** were both defensive-programming gaps that only surfaced in the architect review; a pre-implementation checklist item for "what happens when each external call fails?" would catch these during task planning rather than after.
