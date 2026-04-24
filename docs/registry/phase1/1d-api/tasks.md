# Phase 1d — API Task Registry

> Status: ✅ Complete (+ architect fixes resolved 2026-04-24) | Phase: 1d | Started: 2026-04-24 | Completed: 2026-04-24
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-24 | See [fixes.md](fixes.md) for the 17-item architect review fix log

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | T1-1: Fix pytest-asyncio strict mode (pyproject.toml + async test files) | backend-developer | — |
| T02 | ✅ Done | T1-2 + T1-4: Unwrap SecretStr + replace `_aget_relevant_documents` in chain.py | backend-developer | — | ⚠️ DoD note: `AzureChatOpenAI` accepts `SecretStr` natively; `.get_secret_value()` would cause a mypy type error — DoD item wording was incorrect. Verified clean. See F01 in fixes.md. |
| T03 | ✅ Done | T1-3: Bump qdrant-client to ^1.12, migrate client.search → query_points in dense.py | backend-developer | — |
| T04 | ✅ Done | T2-5: Audit and remove unused langchain-community / langchain shim deps | backend-developer | — |
| T05 | ✅ Done | Add IngestRequest, IngestAcceptedResponse, CollectionsResponse schemas to api/schemas.py | backend-developer | — | ⚠️ DoD gap resolved 2026-04-24: unit tests for all 4 schemas added in test_api_schemas.py (F10 in fixes.md). |
| T06 | ✅ Done | Add `astream_generate` SSE streaming method to GenerationChain | backend-developer | T02 |
| T07 | ✅ Done | Refactor main.py lifespan: initialize singletons, store in app.state, create Annotated deps | backend-developer | T02, T03 | ⚠️ DoD gap resolved 2026-04-24: health.py migrated from `Depends(get_settings) # noqa: B008` to `SettingsDep` (F07 in fixes.md). |
| T08 | ✅ Done | Implement POST /api/v1/ingest route (BackgroundTasks, 202 Accepted) | backend-developer | T05, T07 |
| T09 | ✅ Done | Implement POST /api/v1/query SSE route (StreamingResponse, token/citations/done) | backend-developer | T05, T06, T07 |
| T10 | ✅ Done | Implement GET /api/v1/collections route | backend-developer | T05, T07 |
| T11 | ✅ Done | Register ingest, query, collections routers in main.py | backend-developer | T08, T09, T10 |
| T12 | ✅ Done | Write unit tests for all Phase 1d endpoints and new chain method | tester | T08, T09, T10 |
| T13 | ✅ Done | Run ruff + mypy + pytest — zero warnings, zero errors, all tests passing | backend-developer | T12 |
| T14 | ✅ Done | Update DASHBOARD.md with Phase 1d status | project-manager | T13 |

---

## Ordered Execution Plan

### Batch 1 — Parallel (independent fixes)
- **T01** — pytest-asyncio strict mode fix
- **T02** — SecretStr unwrap + public retriever method
- **T03** — qdrant-client bump + query_points migration
- **T04** — langchain-community audit / removal
- **T05** — New API schemas

### Batch 2 — After T02, T03
- **T06** — GenerationChain.astream_generate (depends on T02 — uses public method)
- **T07** — main.py lifespan refactor + Annotated dependency functions

### Batch 3 — After T05, T06, T07
- **T08** — POST /api/v1/ingest
- **T09** — POST /api/v1/query (SSE)
- **T10** — GET /api/v1/collections

### Batch 4 — After T08, T09, T10
- **T11** — Register all new routers

### Batch 5 — After T11
- **T12** — Unit tests
- **T13** — CI checks (ruff + mypy + pytest)

### Batch 6 — After T13
- **T14** — DASHBOARD.md update

---

## Definition of Done Per Task

Each task must satisfy the global Definition of Done (CLAUDE.md §7) plus:

### T01 — pytest-asyncio strict mode
- [ ] `asyncio_mode = "strict"` in pyproject.toml
- [ ] `asyncio_default_fixture_loop_scope = "function"` added
- [ ] All async test files have `pytestmark = pytest.mark.asyncio` at module level
- [ ] Full test suite passes (`pytest -q`)

### T02 — SecretStr + public retriever method
- [ ] `api_key=settings.azure_openai_api_key.get_secret_value()` in chain.py
- [ ] `_aget_relevant_documents` call site in GenerationChain replaced with `aget_relevant_documents(query)`
- [ ] `run_manager=AsyncCallbackManagerForRetrieverRun.get_noop_manager()` call removed
- [ ] Existing chain tests still pass

### T03 — qdrant-client bump
- [ ] `qdrant-client = "^1.12"` in pyproject.toml
- [ ] `client.search(...)` replaced with `client.query_points(...)` in dense.py
- [ ] `# type: ignore` comment updated if mypy error code changed
- [ ] Retrieval tests still pass

### T04 — Unused dependency audit
- [ ] `grep -r "from langchain_community"` returns no results in `backend/src/`
- [ ] `grep -r "^from langchain "` returns no results in `backend/src/`
- [ ] If unused: `langchain-community` removed from pyproject.toml
- [ ] If unused: `langchain` (shim) removed from pyproject.toml

### T05 — New API schemas
- [ ] `IngestRequest` schema added (optional `data_dir: str | None`)
- [ ] `IngestAcceptedResponse` schema added (`status: str`, `message: str`)
- [ ] `CollectionInfo` schema added (`name: str`, `document_count: int`, `vector_count: int`)
- [ ] `CollectionsResponse` schema added (`collections: list[CollectionInfo]`)
- [ ] All schemas exported in `__all__`

### T06 — GenerationChain.astream_generate
- [ ] Method signature: `async def astream_generate(self, query, k, filters) -> AsyncGenerator[str, None]`
- [ ] Retrieves docs, builds context, builds citations + confidence before streaming
- [ ] Yields `data: {"type": "token", "content": "..."}\n\n` events per token
- [ ] Yields `data: {"type": "citations", "citations": [...], "confidence": 0.xx}\n\n`
- [ ] Yields `data: {"type": "done"}\n\n`
- [ ] Raises GenerationError on failure
- [ ] Unit test covers happy path + error path

### T07 — main.py lifespan refactor
- [ ] Lifespan initializes: `BM25Store`, `Embedder`, `HybridRetriever`, `GenerationChain`, `AsyncQdrantClient`
- [ ] All singletons stored on `app.state`
- [ ] `get_generation_chain`, `get_qdrant_client` dependency functions created
- [ ] `GenerationChainDep`, `QdrantClientDep`, `SettingsDep` Annotated type aliases created
- [ ] `HybridRetriever.close()` called on shutdown (yield teardown)
- [ ] `AsyncQdrantClient.close()` called on shutdown
- [ ] No `lru_cache + Depends` on non-hashable types
- [ ] Existing health tests still pass

### T08 — POST /api/v1/ingest
- [ ] Route returns `202 Accepted` immediately
- [ ] `BackgroundTasks.add_task(run_pipeline, ...)` called with correct args
- [ ] Accepts optional `data_dir` override in body; falls back to `settings.data_dir`
- [ ] Uses `SettingsDep` (Annotated pattern)
- [ ] Unit test: 202 returned, background task queued

### T09 — POST /api/v1/query (SSE)
- [ ] Returns `StreamingResponse` with `media_type="text/event-stream"`
- [ ] SSE events: `token`, `citations`, `done` (three types only)
- [ ] Uses `GenerationChainDep` (Annotated pattern)
- [ ] Uses `astream_generate` from GenerationChain
- [ ] Unit test: SSE events parsed correctly, citations present in stream

### T10 — GET /api/v1/collections
- [ ] Returns `CollectionsResponse` with list of all Qdrant collections
- [ ] Each entry includes `name`, `document_count`, `vector_count`
- [ ] Uses `QdrantClientDep` (Annotated pattern)
- [ ] Handles Qdrant unavailability gracefully (returns empty list or 503)
- [ ] Unit test: collections listed correctly with mocked Qdrant client

### T11 — Router registration
- [ ] All three new routers included in main.py with `/api/v1` prefix
- [ ] OpenAPI docs reflect all endpoints at `/docs`
- [ ] No duplicate prefix (routes use relative paths, prefix set at `include_router`)

### T12 — Unit tests
- [ ] Tests for T06, T08, T09, T10 all written and passing
- [ ] No real network calls (all external deps mocked)
- [ ] Tests are in `tests/unit/` following existing naming conventions

### T13 — CI checks
- [ ] `ruff check backend/src/ backend/tests/` — zero warnings
- [ ] `mypy backend/src/` — zero errors
- [ ] `pytest backend/tests/unit/ -q` — all tests pass (≥ 142 existing + new)

### T14 — DASHBOARD update
- [ ] DASHBOARD.md shows 1d tasks as ✅ Done
- [ ] "Currently In Progress" section updated to 1e

---

## Phase Gate Criteria

Applies at Phase 1 completion (after 1d + 1e + 1f):

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | Ingest 30+ local files end-to-end | No errors, all chunks in Qdrant |
| G02 | POST /query P95 latency | < 8 seconds locally |
| G03 | RAGAS faithfulness | ≥ 0.70 |
| G04 | API key auth | Unauthenticated requests blocked (401) |
| G05 | docker compose up | Full stack running in < 90s |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| qdrant-client 1.12 `query_points` signature differs from `search` | Medium | Medium | Read 1.12 changelog before migrating; run retrieval tests after bump |
| SSE streaming + TestClient compatibility | Medium | Low | Use `httpx.AsyncClient` for SSE tests; `TestClient` buffers by default |
| langchain shim removal breaks transitive import | Low | High | Run full test suite after removal; revert if any import fails |
