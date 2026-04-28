# Phase 1a — Ingestion Pipeline — Retrospective Summary

> Date: 2026-04-24 | Phase: 1a | Feature: ingestion | Gate Status: Passed

---

## Feature Summary

Feature 1a delivered the complete document ingestion pipeline for the kb-ai-rag platform — the first production-ready subsystem of Phase 1's Core MVP goal. The pipeline ingests local PDF and TXT files, splits them into configurable chunks, embeds each chunk asynchronously via Azure OpenAI `text-embedding-3-large`, persists vectors with full metadata to a Qdrant collection, and simultaneously builds a BM25 keyword index that is pickled to disk. This work establishes the foundational data layer that all downstream retrieval, generation, and agent features depend on: nothing in Phase 1b through 1f can proceed without chunks in Qdrant and a live BM25 index. A formal architect review was conducted after initial implementation and seven findings (one MAJOR, five MINOR, two OBSERVATIONS) were identified and resolved in a second pass before merging to `main`.

---

## Architecture

| Item | Detail |
|------|--------|
| Pattern | `BaseLoader` ABC → concrete `LocalFileLoader`; orchestrated by `run_pipeline` coroutine |
| Components | `models.py`, `loaders/base.py`, `loaders/local_loader.py`, `splitter.py`, `embedder.py`, `vector_store.py`, `bm25_store.py`, `pipeline.py` — all under `backend/src/ingestion/` |
| AgentState changes | None — AgentState not introduced until Phase 2 |
| ADRs governing this feature | ADR-003 (hybrid retrieval — domain-agnostic `ChunkMetadata`, no `domain` field); ADR-001 (Qdrant as vector store) |
| Cross-cutting contracts changed | `Settings` gained `embedding_vector_size: int`, `embedding_batch_size: int`, `bm25_index_path: str`; `api_key` and `azure_openai_api_key` promoted from `str` to `pydantic.SecretStr` |

---

## Design

| Item | Detail |
|------|--------|
| Key files | `backend/src/ingestion/models.py`, `backend/src/ingestion/loaders/local_loader.py`, `backend/src/ingestion/embedder.py`, `backend/src/ingestion/vector_store.py`, `backend/src/ingestion/bm25_store.py`, `backend/src/ingestion/pipeline.py`, `backend/src/config.py` |
| Libraries / versions | `pypdf ^5.1`, `langchain ^0.3`, `langchain-openai ^0.2`, `qdrant-client ^1.11`, `rank-bm25 ^0.2` (all pre-declared in `pyproject.toml` from Phase 0) |
| Settings fields added | `embedding_vector_size=3072`, `embedding_batch_size=100`, `bm25_index_path=/app/data/bm25_index.pkl` — all in `.env.example` |
| Tasks driving this design | T01–T10 from [tasks.md](tasks.md) |
| Findings that shaped the design | F01 (asyncio.to_thread for blocking I/O), F03 (vector size to Settings), F05 (SecretStr), F06 (upsert-failure consistency guard) from [fixes.md](fixes.md) |

---

## Phase Gate Evidence

| Command | Result |
|---------|--------|
| `poetry run ruff check .` | ✅ zero warnings |
| `poetry run ruff format .` | ✅ 38 files unchanged |
| `poetry run mypy src/` | ✅ zero errors — 21 source files |
| `poetry run pytest tests/unit -q` | ✅ 91 passed (52 ingestion + 39 prior Phase 0 tests) |
| `npm run tsc -- --noEmit` | N/A — frontend not in scope for 1a |

See gate criteria: [tasks.md](tasks.md)

---

## Open Questions / Deferred Decisions

- HNSW tuning constants (`m=16`, `ef_construct=100`, `indexing_threshold=10_000`) are hardcoded in `vector_store.py` — deferred to Phase 2 (F09, backlog)
- Integration test for `run_pipeline` end-to-end (real Qdrant + real files) requires `docker compose up` and is not yet automated — deferred to Phase 1 MVP gate
- `get_settings()` uses `# type: ignore[call-arg]` due to missing pydantic-settings mypy plugin; migrate if plugin becomes available — deferred indefinitely (F08, awareness)
- Azure OpenAI calls in `Embedder` are mocked in all unit tests; real embedding quality is unverified until the Phase 1f RAGAS evaluation

---

## What Went Well

- The data-engineer agent correctly applied the async-first constraint from CLAUDE.md without prompting — all Qdrant and embedding calls were `async` from the start, requiring only the file I/O fix (F01) to complete async coverage.
- The architect review caught a real data-consistency bug (F06): upsert failure would have left BM25 populated with hits having no corresponding Qdrant vectors, which would have caused silent hybrid retrieval failures discovered only in Phase 1b integration testing.
- Delegating F05 (SecretStr) and F07 (missing tests) to separate agents in parallel and having them complete in the correct dependency order (F06 fix landed before F07 tests were written) showed the parallel-agent coordination pattern working cleanly.

---

## What Could Be Improved

- The initial implementation passed `settings: Settings` to `LocalFileLoader.__init__` without using it anywhere (F02) — a YAGNI violation that the architect caught; the agent should have applied the no-orphaned-code rule from CLAUDE.md before submitting.
- `_VECTOR_SIZE = 3072` was hardcoded as a module-level constant (F03) despite CLAUDE.md explicitly prohibiting hardcoded values; the no-hardcoded-values rule should be applied as a checklist item by the implementing agent before review.
- The test-manager agent (F07) needed to also add a `try/except` block to the BM25 stage in `pipeline.py` before the new tests could pass, which constituted an unplanned implementation change during the test phase — the pipeline's BM25 error handling should have been specified in T08's Definition of Done.
