# Phase 2 — Architect Review Fixes

> Created: 2026-04-28 | Source: Architect review of Phase 1+2 implementation
> Rule: development-process.md §9 — all Critical/High fixes must clear before Phase 3 starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On | Assigned To |
|----|----------|--------|----------|---------|------------|-------------|
| F01 | High | ⏳ Pending | Lifespan | `DenseRetriever` owns a private `AsyncQdrantClient` — second connection pool alongside `app.state.qdrant_client` | — | backend-developer |
| F02 | High | ⏳ Pending | Lifespan | `QdrantVectorStore` creates `AsyncQdrantClient` per pipeline run — not injected from lifespan | — | backend-developer |
| F03 | High | ⏳ Pending | Async | `BM25Store.save()` and `load()` call blocking `pickle.dump`/`pickle.load` inside async contexts without `asyncio.to_thread()` | — | backend-developer |
| F04 | High | ⏳ Pending | Secrets | `langsmith_api_key` typed as `str` instead of `SecretStr` | — | backend-developer |
| F05 | High | ⏳ Pending | Schema | `Citation` defined in `src/schemas/generation.py` — violates ADR-008; API types must live in `src/api/schemas/` | — | backend-developer |
| F06 | High | ⏳ Pending | Lifespan | `builder.py` instantiates two `AzureChatOpenAI` clients inside `build_graph()` — not stored on `app.state`, not injectable via `deps.py` | — | backend-developer |
| F07 | High | ⏳ Pending | Lifespan | `GenerationChain.__init__` instantiates `AzureChatOpenAI` directly — bypasses lifespan singleton / deps.py pattern | F06 | backend-developer |
| F08 | Major | ⏳ Pending | Config | `edges.py` calls `get_settings()` directly — bypasses FastAPI DI, requires `get_settings.cache_clear()` in tests | — | backend-developer |
| F09 | Major | ⏳ Pending | Security | `cors_origins` defaults to `["*"]` — wildcard CORS in default config | — | backend-developer |
| F10 | Major | ⏳ Pending | Testing | No error-path tests in `test_api_ingest.py`, `test_api_query.py`, `test_retrieval_hybrid.py`, `test_retrieval_reranker.py` | — | tester |
| F11 | Major | ⏳ Pending | Graph | `initial_state` sent to `compiled_graph.astream()` omits 14 of 19 `AgentState` fields — relies on LangGraph implicit defaults | — | backend-developer |
| F12 | Major | ⏳ Pending | Graph | `retrieved_docs` accumulates across all retries via `operator.add` — generator context window grows unbounded on repeated critic failures | — | backend-developer |
| F13 | Major | ⏳ Pending | Contract | Retriever node emits no `agent_step` SSE event — docstring promises one event per intermediate node | — | backend-developer |
| F14 | Minor | ⏳ Pending | Graph | `retry_count` semantics overloaded — grader and critic share the same budget counter; grader retry loop is dead code with `graph_max_retries=1` | — | backend-developer |
| F15 | Minor | ⏳ Pending | Code | `_RouterOutput.reasoning`, `_CriticOutput.reasoning`, and `_CriticOutput.unsupported_claims` are defined but never read after the LLM call — orphaned model fields | — | backend-developer |
| F16 | Advisory | ⏳ Pending | ADR | No ADR covers CRAG retry orchestration details: which node increments `retry_count`, shared grader/critic budget, `retrieved_docs` accumulation behaviour | — | architect |
| F17 | Advisory | ⏳ Pending | Ops | SQLite checkpointer file grows indefinitely per session — no cleanup on shutdown, risk of disk exhaustion in containers | — | backend-developer |
| F18 | Advisory | ⏳ Pending | Robustness | `_build_agent_step_event` hardcodes node name strings — renames in `builder.py` would break SSE routing silently | — | backend-developer |

---

## Detailed Fix Specifications

### F01 — DenseRetriever dual Qdrant connection pool (High)

**File:** `backend/src/retrieval/dense.py:24`
**Issue:** `DenseRetriever.__init__` constructs its own `AsyncQdrantClient`. The lifespan already creates `app.state.qdrant_client`. Two separate connection pools run against the same Qdrant instance — connection churn, inconsistent pool sizing, separate shutdown paths.
**Fix:** Remove the private client from `DenseRetriever`. Accept `AsyncQdrantClient` as a constructor argument and inject the lifespan singleton. Add a `QdrantClientDep` injection point through `HybridRetriever` → `DenseRetriever`. Remove `DenseRetriever.close()` (caller owns the client).
**Rule:** architecture-rules.md § Lifespan Singleton — No Per-Request Client Creation.

---

### F02 — QdrantVectorStore creates per-run Qdrant client (High)

**File:** `backend/src/ingestion/vector_store.py:33` / `backend/src/ingestion/pipeline.py:73`
**Issue:** `QdrantVectorStore(settings)` at pipeline.py:73 constructs a new `AsyncQdrantClient` on every `run_pipeline` call. Each background ingest task opens a new connection, never sharing the lifespan-managed `app.state.qdrant_client`.
**Fix:** Accept `AsyncQdrantClient` as a constructor argument in `QdrantVectorStore`. Thread the lifespan client through `run_pipeline()`'s signature and the ingest route.
**Rule:** architecture-rules.md § Lifespan Singleton — No Per-Request Client Creation.

---

### F03 — BM25Store blocking I/O in async contexts (High)

**File:** `backend/src/ingestion/bm25_store.py:59` (`pickle.dump`), `bm25_store.py:75` (`pickle.load`); called from `backend/src/api/main.py:59` (lifespan) and `backend/src/ingestion/pipeline.py:161` (`run_pipeline` async function).
**Issue:** `BM25Store.save()` and `load()` perform synchronous blocking file I/O and pickle serialisation directly on the async event loop. Under load this stalls all concurrent requests.
**Fix:** Wrap both calls at their call sites with `asyncio.to_thread(bm25_store.save)` and `asyncio.to_thread(bm25_store.load)`. Alternatively, add async wrappers `async def asave()` / `async def aload()` to `BM25Store`.
**Rule:** python-rules.md § Blocking I/O in async functions; anti-patterns.md — `pickle.load`/`pickle.dump` without `asyncio.to_thread`.

---

### F04 — `langsmith_api_key` typed as `str` not `SecretStr` (High)

**File:** `backend/src/config.py:52`
**Issue:** `langsmith_api_key: str = ""` leaks the LangSmith API key in `Settings.model_dump()` output (e.g. in debug logging or health endpoints), violating the SecretStr boundary rule.
**Fix:** Change to `langsmith_api_key: SecretStr = SecretStr("")`. Update the LangSmith SDK initialization site to call `.get_secret_value()`.
**Rule:** python-rules.md § Secrets — SecretStr boundary rule; anti-patterns.md — Type a secret field as `str` in Settings.

---

### F05 — `Citation` defined outside `src/api/schemas/` (High)

**File:** `backend/src/schemas/generation.py:10`
**Issue:** `Citation` appears in the `POST /api/v1/query` and `/query/agentic` API responses. ADR-008 requires that all types surfacing in an API response are canonical in `src/api/schemas/`. The current location (`src/schemas/generation.py`) is an intermediate module not sanctioned by ADR-008.
**Fix:** Move `Citation` (and `GenerationResult`) to `backend/src/api/schemas/__init__.py` (or a new `backend/src/api/schemas/generation.py`). Update all import sites: `graph/state.py`, `graph/nodes/generator.py`, `generation/chain.py`. Remove `backend/src/schemas/generation.py` once empty.
**Rule:** architecture-rules.md § Schema Ownership — Single Definition Rule; ADR-008.

---

### F06 — `build_graph()` creates LLM clients not on `app.state` (High)

**File:** `backend/src/graph/builder.py:51–62`
**Issue:** Two `AzureChatOpenAI` instances (`llm`, `llm_4o`) are created inside `build_graph()` and captured in closures. They are not stored on `app.state` and are not injectable through `deps.py`. Tests that need to swap the LLM must reconstruct the entire graph.
**Fix:** Accept `llm` and `llm_4o` as parameters of `build_graph()`. Create them in `main.py` lifespan, store on `app.state`, expose via `Dep` aliases in `deps.py`. This also enables independent LLM mocking in tests.
**Rule:** architecture-rules.md § Lifespan Singleton; anti-patterns.md — Create a new client inside a route handler or health endpoint.

---

### F07 — `GenerationChain` creates `AzureChatOpenAI` in `__init__` (High)

**File:** `backend/src/generation/chain.py:116`
**Issue:** `GenerationChain.__init__` instantiates `AzureChatOpenAI` directly. Although `GenerationChain` itself is a lifespan singleton, the LLM client it owns is invisible to `deps.py` and cannot be injected or replaced independently.
**Fix:** Accept `llm: AzureChatOpenAI` as a constructor argument. Create the client in lifespan alongside F06's fix, store on `app.state.llm_chat`, and inject into `GenerationChain`.
**Rule:** architecture-rules.md § Lifespan Singleton; anti-patterns.md.
**Depends On:** F06 (same lifespan LLM creation block).

---

### F08 — `edges.py` calls `get_settings()` directly (Major)

**File:** `backend/src/graph/edges.py:21`, `edges.py:32`
**Issue:** Both edge functions call `get_settings()` directly rather than receiving settings as a parameter. This forces tests to call `get_settings.cache_clear()` to override threshold values, and couples pure routing functions to the settings singleton.
**Fix:** Thread `settings: Settings` as an argument into `route_after_grader(state, settings)` and `route_after_critic(state, settings)`. Pass it from the `builder.py` closures that already receive `settings`.
**Rule:** anti-patterns.md — No hardcoded values; python-rules.md § No Hardcoded Values.

---

### F09 — CORS wildcard default (Major)

**File:** `backend/src/config.py:31`
**Issue:** `cors_origins: list[str] = ["*"]` allows any origin by default. A misconfigured or bare deployment with no `.env` override is fully CORS-open.
**Fix:** Change default to `cors_origins: list[str] = []` and update `.env.example` to document the required value. The FastAPI `CORSMiddleware` with an empty list blocks cross-origin requests until explicitly configured.
**Rule:** Security best practice; anti-patterns.md — Put secrets in source code (equivalent misconfiguration risk).

---

### F10 — Missing error-path tests in key modules (Major)

**Files:**
- `backend/tests/unit/test_api_ingest.py` — 0 `pytest.raises` / `side_effect` calls; no test for pipeline failure propagation
- `backend/tests/unit/test_api_query.py` — 0 error-path tests; `GenerationError` path not tested via SSE
- `backend/tests/unit/test_retrieval_hybrid.py` — 0 error-path tests; embedding failure path not covered
- `backend/tests/unit/test_retrieval_reranker.py` — 0 error-path tests; cross-encoder failure not tested

**Issue:** development-process.md §3 requires at least one error-path test per external call. These modules call Azure OpenAI and Qdrant without any tested failure path.
**Fix:** Add at minimum: (1) patch `run_pipeline` to raise `IngestionError`, assert 500 propagation in ingest test; (2) patch `astream_generate` to raise `GenerationError`, assert SSE `done` still emitted; (3) patch `Embedder.embed_query` to raise `EmbeddingError` in hybrid test; (4) patch cross-encoder `predict` to raise in reranker test.
**Rule:** development-process.md §3 — Test First, Then Code; §7 DoD gate.

---

### F11 — Incomplete initial state for `compiled_graph.astream()` (Major)

**File:** `backend/src/api/routes/query_agentic.py:94–100`
**Issue:** `initial_state` initialises only 5 of 19 `AgentState` fields (`session_id`, `query`, `filters`, `k`, `retry_count`). The remaining 14 fields are absent. LangGraph infers `None` / `[]` defaults, but this is implicit and untested. Fields like `graded_docs`, `all_below_threshold`, `web_fallback_used`, `messages`, and `steps_taken` are read by downstream nodes before they are written.
**Fix:** Declare explicit defaults for all non-reducer fields in `initial_state` (e.g. `graded_docs: []`, `web_fallback_used: False`, `messages: []`, `steps_taken: []`). This makes the contract explicit and eliminates reliance on LangGraph's implicit TypedDict initialisation.
**Rule:** architecture-rules.md § AgentState is the Single Source of Truth.

---

### F12 — `retrieved_docs` unbounded accumulation across retries (Major)

**File:** `backend/src/graph/state.py:46` / `backend/src/graph/nodes/grader.py:56`
**Issue:** `retrieved_docs: Annotated[list[Document], operator.add]` appends on every node update. Each retriever retry appends a new batch without deduplication. The grader re-grades all accumulated docs on every retry, and the generator receives the full accumulated set as context. With high `graph_max_retries` or large `k`, this blows up LLM context.
**Fix:** Either (a) cap `retrieved_docs` to the most-recent retrieval batch by replacing it each time (remove `operator.add`, use plain replacement), tracking history separately if needed; or (b) deduplicate by `chunk_id` inside `grader_node` before scoring. Document the chosen semantics in an ADR (see F16).
**Rule:** architecture-rules.md § AgentState is the Single Source of Truth; python-rules.md — No Hardcoded Values (context budget).

---

### F13 — Retriever node emits no SSE `agent_step` event (Major)

**File:** `backend/src/api/routes/query_agentic.py:142–150`
**Issue:** The `_stream()` function handles `"retriever"` nodes by silently updating `_context_texts` but never yields an `agent_step` event. The route docstring states "one `agent_step` event per intermediate node." The retriever fires on every retry but produces no client-visible signal.
**Fix:** Add `retriever` to `AgentStepEvent.node` literal, add a `RetrieverStepPayload` (doc_count, strategy, duration_ms) to `src/api/schemas/agentic.py`, and yield an event in the retriever branch of `_stream()`. Update the SSE contract in ADR-004.
**Rule:** architecture-rules.md § Streaming — SSE for Query Responses; ADR-004.

---

### F14 — `retry_count` semantics overloaded; grader retry is dead code (Minor)

**File:** `backend/src/graph/edges.py:22`, `edges.py:38`
**Issue:** Both `route_after_grader` and `route_after_critic` check `state["retry_count"] < settings.graph_max_retries`. The grader increments the counter every call. With the default `graph_max_retries=1`, `retry_count` reaches 1 after the first grader pass, so `route_after_grader` never routes back to the retriever — the grader retry branch is effectively dead.
**Fix:** Use separate counters `grader_retry_count` and `critic_retry_count` in `AgentState`, each with its own max. Alternatively, document the shared-budget design decision in ADR (see F16) and rename the field to `total_retry_count` to signal intent.
**Rule:** architecture-rules.md § AgentState is the Single Source of Truth (field semantics must be clear).

---

### F15 — Orphaned Pydantic model fields (Minor)

**Files:** `backend/src/graph/nodes/router.py:18` (`_RouterOutput.reasoning`), `backend/src/graph/nodes/critic.py:32–33` (`_CriticOutput.reasoning`, `_CriticOutput.unsupported_claims`)
**Issue:** These fields are populated by the LLM structured-output call but are never read or stored after the call returns. Comments say "LangSmith trace only" but LangSmith tracing is not wired in these nodes — the data is silently discarded.
**Fix:** If LangSmith tracing is not implemented, remove the fields from the Pydantic models to avoid misleading future readers. If tracing is planned, add a tracking issue and an ADR entry.
**Rule:** development-process.md §8 — No Orphaned Code; anti-patterns.md — Store `__init__` parameters that no method ever reads.

---

### F16 — No ADR for CRAG retry orchestration (Advisory)

**Files:** `backend/src/graph/edges.py`, `backend/src/graph/nodes/grader.py`, `backend/src/graph/state.py`
**Issue:** Phase 2 introduced a non-trivial design: shared `retry_count` budget across grader and critic, `operator.add` on `retrieved_docs` across retries, and the decision that the grader (not the edge) increments the counter. None of these choices are covered by an existing ADR.
**Fix:** Write ADR-011 covering: (a) retry counter ownership and scope, (b) `retrieved_docs` accumulation vs. replacement semantics, (c) grader/critic retry budget sharing.
**Rule:** architecture-rules.md § Architecture Decision Records.

---

### F17 — SQLite checkpointer file grows without cleanup (Advisory)

**File:** `backend/src/graph/builder.py:110–115` / `backend/src/api/main.py` lifespan
**Issue:** The `AsyncSqliteSaver` writes a session checkpoint per thread_id. In a containerised environment with ephemeral deployments, old session data accumulates on disk indefinitely. No retention policy or cleanup hook exists.
**Fix:** Add a configurable `sqlite_checkpointer_ttl_days` setting (default 7). On lifespan startup, run a `DELETE FROM checkpoints WHERE ... < now - TTL` query before opening the graph. Document in ADR-004 amendment.
**Rule:** python-rules.md § No Hardcoded Values (operational configuration belongs in Settings).

---

### F18 — Hardcoded node name strings in SSE routing (Advisory)

**File:** `backend/src/api/routes/query_agentic.py:113`, `query_agentic.py:42–72`
**Issue:** The string literals `"router"`, `"grader"`, `"critic"` are used both as LangGraph node names (in `builder.py`) and as SSE dispatch keys (in `query_agentic.py`). A rename in one place silently breaks the other.
**Fix:** Extract node name constants to a shared `src/graph/node_names.py` module (or as class-level constants on a `NodeNames` dataclass) and import them in both `builder.py` and `query_agentic.py`.
**Rule:** anti-patterns.md — No hardcoded values.

---

## Priority Grep Check Results (clean)

The following checks produced zero matches — no action required:

| Check | Result |
|-------|--------|
| P1 — Duplicate class names | ✅ No duplicates |
| P3 — SecretStr boundary (`api_key=settings.X` without `get_secret_value()`) | ✅ No violations |
| P4 — Deprecated LangChain symbols (RetrievalQA, LLMChain, etc.) | ✅ No violations |
| P6 — `print()` in source files | ✅ None found |
| P10 — Relative imports (`from . import`) | ✅ None found |
| P11 — Wildcard imports (`from X import *`) | ✅ None found |
| P12 — Raw `logging.*` calls | ✅ None found |

---

## Clearance Order

**Batch 1 — Parallel (no dependencies):**
F03 (BM25 async), F04 (langsmith SecretStr), F08 (edges settings), F09 (CORS default), F10 (error-path tests), F11 (initial state), F14 (retry counter), F15 (orphaned fields), F16 (ADR-011), F17 (SQLite TTL), F18 (node name constants)

**Batch 2 — After Batch 1:**
F06 (LLM clients in lifespan) — prerequisite for F07 and F13

**Batch 3 — After F06:**
F07 (GenerationChain injection), F13 (retriever SSE event)

**Batch 4 — After Batch 3:**
F01 (DenseRetriever inject client), F02 (QdrantVectorStore inject client) — both require the lifespan restructuring from F06

**Batch 5 — After F01/F02:**
F05 (Citation move to api/schemas) — safe to do after all import sites are stable
F12 (retrieved_docs accumulation) — requires ADR-011 decision from F16

---

## Verification Checklist

- [ ] F01 — `grep -rn "AsyncQdrantClient(" backend/src/retrieval/ --include="*.py"` → zero matches
- [ ] F02 — `grep -rn "AsyncQdrantClient(" backend/src/ingestion/ --include="*.py"` → zero matches
- [ ] F03 — `grep -rn "pickle\.load\|pickle\.dump" backend/src/ --include="*.py" | grep -v "asyncio.to_thread"` → zero matches
- [ ] F04 — `grep -n "langsmith_api_key" backend/src/config.py` → shows `SecretStr`
- [ ] F05 — `grep -rn "from src.schemas.generation" backend/src/ --include="*.py"` → zero matches
- [ ] F06 — `grep -n "AzureChatOpenAI(" backend/src/graph/builder.py` → zero matches
- [ ] F07 — `grep -n "AzureChatOpenAI(" backend/src/generation/chain.py` → zero matches
- [ ] F08 — `grep -n "get_settings()" backend/src/graph/edges.py` → zero matches
- [ ] F09 — `grep -n 'cors_origins' backend/src/config.py` → default is `[]`
- [ ] F10 — `grep -c "pytest.raises\|side_effect" backend/tests/unit/test_api_ingest.py test_api_query.py test_retrieval_hybrid.py test_retrieval_reranker.py` → all ≥ 1
- [ ] F11 — `query_agentic.py initial_state` includes all 19 AgentState fields
- [ ] F12 — `retrieved_docs` reducer or deduplication strategy documented and implemented
- [ ] F13 — `grep -n "retriever" backend/src/api/routes/query_agentic.py` → yields SSE event
- [ ] F14 — separate `grader_retry_count` / `critic_retry_count` OR ADR documents shared budget
- [ ] F15 — `_RouterOutput.reasoning`, `_CriticOutput.reasoning`/`unsupported_claims` removed or wired to tracing
- [ ] F16 — `docs/adr/011-*.md` exists and is Accepted
- [ ] F17 — `sqlite_checkpointer_ttl_days` in Settings; cleanup runs on startup
- [ ] F18 — node name strings imported from shared constants module
