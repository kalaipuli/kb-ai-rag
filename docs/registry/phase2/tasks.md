# Phase 2 — Pre-Phase-3 Cleanup Task Registry

> Status: ✅ Complete | Phase: 2 (cleanup) | Estimated Days: 4–6
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-05-02
>
> **Purpose:** Clear all findings from the Phase 1+2 architect review (F01–F18, plus additional PHASE_1_2_REVIEW items) before Phase 3 (Azure Connectors) begins. Per development-process.md §9: all High and Major findings must be Done; Minor findings must be Done or formally deferred; Advisory findings may be Deferred with a documented DASHBOARD.md entry.
>
> **Source:** `docs/registry/phase2/architect-fixes.md` (F01–F18) + `PHASE_1_2_REVIEW.md` (additional items)

---

## Task Overview

| ID  | Status     | Task                                                                           | Agent              | Depends On       |
|-----|------------|--------------------------------------------------------------------------------|--------------------|------------------|
| T01 | ✅ Done    | Write ADR-015: CRAG retry budget design decisions                              | architect          | —                |
| T02 | ✅ Done    | Fix BM25Store blocking I/O — wrap pickle.dump/load with asyncio.to_thread      | backend-developer  | —                |
| T03 | ✅ Done    | Fix langsmith_api_key — retype as SecretStr                                    | backend-developer  | —                |
| T04 | ✅ Done    | Fix edges.py settings access — thread Settings as parameter                    | backend-developer  | —                |
| T05 | ✅ Done    | Fix CORS default — change cors_origins default from ["*"] to []                | backend-developer  | —                |
| T06 | ✅ Done    | Add error-path tests in test_api_ingest, test_api_query, test_retrieval_*      | tester             | —                |
| T07 | ✅ Done    | Fix initial_state — declare all 19 AgentState fields explicitly                | backend-developer  | —                |
| T08 | ✅ Done    | Fix retry_count overload — shared budget with graph_max_retries=2              | backend-developer  | T01              |
| T09 | ✅ Done    | Remove orphaned Pydantic fields from _RouterOutput and _CriticOutput           | backend-developer  | —                |
| T10 | ✅ Done    | Add SQLite checkpointer TTL cleanup on startup                                 | backend-developer  | —                |
| T11 | ✅ Done    | Extract node name constants to src/graph/node_names.py                         | backend-developer  | —                |
| T12 | ✅ Done    | Add aiosqlite monkey-patch version guard in builder.py                         | backend-developer  | —                |
| T13 | ✅ Done    | Lift AzureChatOpenAI clients into lifespan (build_graph injection)             | backend-developer  | T01–T12          |
| T14 | ✅ Done    | Inject AzureChatOpenAI into GenerationChain constructor                        | backend-developer  | T13              |
| T15 | ✅ Done    | Add retriever SSE agent_step event + RetrieverStepPayload schema               | backend-developer  | T13              |
| T16 | ✅ Done    | Inject lifespan Qdrant client into DenseRetriever and QdrantVectorStore        | backend-developer  | T14, T15         |
| T17 | ✅ Done    | Move Citation to src/api/schemas/ and fix retrieved_docs accumulation          | backend-developer  | T16              |
| T18 | ✅ Done    | Fix crypto.randomUUID() fallback for non-HTTPS contexts in useAgentStream.ts   | frontend-developer | —                |
| T19 | ✅ Done    | Verify ragas is isolated to [tool.poetry.group.eval.dependencies]              | backend-developer  | —                |
| T20 | ⚠️ Deferred | Migrate query_agentic_endpoint to real streaming via astream_events           | backend-developer  | Phase 5 scope    |
| T21 | ⚠️ Deferred | Add Playwright E2E tests for parallel SSE streaming                           | tester             | Phase 5 scope    |

---

## Ordered Execution Plan

Tasks in the same batch are independent and can run concurrently. Batch N+1 starts only after all non-deferred tasks in Batch N are Done.

### Batch 1 — Parallel (no inter-task dependencies)

- **T01** — Write ADR-011 (architect): covers retry counter ownership, retrieved_docs semantics, grader/critic budget; must exist before T08 and T17 can finalise their implementations
- **T02** — BM25Store async I/O (backend-developer): wrap both pickle.dump and pickle.load call sites with asyncio.to_thread
- **T03** — langsmith_api_key SecretStr (backend-developer): retype field in config.py, update SDK init call
- **T04** — edges.py settings parameter (backend-developer): replace get_settings() calls with a Settings parameter threaded from builder.py
- **T05** — CORS default (backend-developer): change default to [] in config.py, update .env.example
- **T06** — Error-path tests (tester): add error-path coverage to all four identified test files
- **T07** — initial_state completeness (backend-developer): declare all 19 AgentState fields with explicit defaults in query_agentic.py
- **T08** — retry_count semantics (backend-developer): depends on T01 ADR decision; implement separate counters or rename field per ADR-011
- **T09** — Orphaned Pydantic fields (backend-developer): remove _RouterOutput.reasoning, _CriticOutput.reasoning, _CriticOutput.unsupported_claims
- **T10** — SQLite TTL (backend-developer): add sqlite_checkpointer_ttl_days setting; run DELETE on startup
- **T11** — Node name constants (backend-developer): create src/graph/node_names.py; update builder.py and query_agentic.py imports
- **T12** — Aiosqlite monkey-patch guard (backend-developer): add version check and pyproject.toml comment in builder.py
- **T18** — UUID fallback (frontend-developer): add Math.random fallback in useAgentStream.ts for non-HTTPS contexts
- **T19** — ragas group isolation (backend-developer): confirm ragas appears only in [tool.poetry.group.eval.dependencies]

Note: T08 has a soft dependency on T01 (the ADR decision dictates which implementation path to take). T08 must not be started until T01 is Accepted.

### Batch 2 — After Batch 1 complete

- **T13** — Lift AzureChatOpenAI into lifespan (backend-developer): refactor build_graph() to accept llm parameters; create clients in main.py lifespan; store on app.state; expose via deps.py Dep aliases

### Batch 3 — After T13 complete

- **T14** — GenerationChain injection (backend-developer): refactor GenerationChain.__init__ to accept llm as constructor argument; wire from lifespan
- **T15** — Retriever SSE event (backend-developer): add RetrieverStepPayload schema to src/api/schemas/agentic.py; add retriever to AgentStepEvent.node literal; yield agent_step event in query_agentic.py retriever branch

### Batch 4 — After T14 and T15 complete

- **T16** — Qdrant client injection (backend-developer): remove private AsyncQdrantClient from DenseRetriever; accept client as constructor argument; thread lifespan singleton through HybridRetriever and QdrantVectorStore; remove DenseRetriever.close()

### Batch 5 — After T16 complete

- **T17** — Citation relocation and retrieved_docs fix (backend-developer): move Citation and GenerationResult to src/api/schemas/; update all import sites; remove src/schemas/generation.py; implement retrieved_docs replacement or deduplication strategy per ADR-011

---

## Definition of Done Per Task

Each task must satisfy its specific criteria below **and** pass all global DoD commands from CLAUDE.md §7 before being marked Done.

Global DoD commands (run for every task):
```
poetry run ruff check backend/src/ backend/tests/
poetry run mypy backend/src/ --strict
poetry run pytest backend/tests/unit/ -q --tb=short
```
Frontend tasks additionally run:
```
npm run tsc --noEmit
npm run lint
```

---

### T01 — ADR-011: CRAG Retry Orchestration

**Agent:** architect
**Fixes:** F16
**File to create:** `docs/adr/011-crag-retry-orchestration.md`

The ADR must cover all three open design questions:

| Question | Decision required |
|----------|------------------|
| Retry counter ownership | Which node increments retry_count; which graph entity reads it for routing |
| retrieved_docs accumulation | Replace-on-retry vs. append-with-deduplication; what the generator receives as context |
| grader/critic budget sharing | Whether grader and critic share one counter or have separate budgets; what the default values mean |

**Acceptance criteria:**
- [ ] `docs/adr/011-crag-retry-orchestration.md` exists with Status: Accepted
- [ ] ADR uses the standard template (Status / Context / Decision / Alternatives Considered / Consequences)
- [ ] All three questions above have an explicit Decision entry
- [ ] T08 implementation path is unambiguous from reading the ADR
- [ ] T17 retrieved_docs fix strategy is unambiguous from reading the ADR

---

### T02 — BM25Store Async I/O

**Agent:** backend-developer
**Fixes:** F03
**Files:** `backend/src/ingestion/bm25_store.py`, `backend/src/api/main.py`, `backend/src/ingestion/pipeline.py`

**Fix approach:** Either add `async def asave()` / `async def aload()` methods to `BM25Store` wrapping the synchronous calls with `asyncio.to_thread()`, or wrap the existing call sites in `asyncio.to_thread()`. The chosen approach must be applied consistently at all call sites.

**Verification grep:**
```
grep -rn "pickle\.load\|pickle\.dump" backend/src/ --include="*.py" | grep -v "asyncio.to_thread"
```
Must return zero matches.

**Acceptance criteria:**
- [ ] All pickle.dump and pickle.load calls inside async contexts are wrapped with asyncio.to_thread()
- [ ] Verification grep returns zero matches
- [ ] poetry run mypy backend/src/ --strict — zero errors
- [ ] poetry run pytest backend/tests/unit/ -q — all green

---

### T03 — langsmith_api_key SecretStr

**Agent:** backend-developer
**Fixes:** F04
**File:** `backend/src/config.py`

**Fix:** Change `langsmith_api_key: str = ""` to `langsmith_api_key: SecretStr = SecretStr("")`. Locate the LangSmith SDK initialization site and update it to call `.get_secret_value()` when passing the key to the SDK.

**Verification grep:**
```
grep -n "langsmith_api_key" backend/src/config.py
```
Must show `SecretStr`.

**Acceptance criteria:**
- [ ] Field typed as `SecretStr` in config.py
- [ ] All SDK call sites unwrap with `.get_secret_value()`
- [ ] No bare `langsmith_api_key` string passed to any SDK constructor
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T04 — edges.py Settings Parameter

**Agent:** backend-developer
**Fixes:** F08
**File:** `backend/src/graph/edges.py`, `backend/src/graph/builder.py`

**Fix:** Change `route_after_grader` and `route_after_critic` signatures to accept `settings: Settings` as a parameter. Pass `settings` from the closures in `builder.py` that already hold the settings reference. Tests must not call `get_settings.cache_clear()`.

**Verification grep:**
```
grep -n "get_settings()" backend/src/graph/edges.py
```
Must return zero matches.

**Acceptance criteria:**
- [ ] Both edge functions receive Settings as a parameter
- [ ] No get_settings() call in edges.py
- [ ] builder.py closures pass settings explicitly
- [ ] Existing tests do not require get_settings.cache_clear()
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T05 — CORS Default Hardening

**Agent:** backend-developer
**Fixes:** F09
**Files:** `backend/src/config.py`, `.env.example`

**Fix:** Change `cors_origins: list[str] = ["*"]` to `cors_origins: list[str] = []`. Update `.env.example` to include `CORS_ORIGINS=http://localhost:3000` with a comment explaining it must be set explicitly in each environment.

**Verification grep:**
```
grep -n "cors_origins" backend/src/config.py
```
Default value must be `[]`.

**Acceptance criteria:**
- [ ] Default CORS origins is an empty list in config.py
- [ ] .env.example documents CORS_ORIGINS with a required-value comment
- [ ] Application still starts correctly with the default (no cross-origin requests permitted)
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T06 — Error-Path Test Coverage

**Agent:** tester
**Fixes:** F10
**Files:**
- `backend/tests/unit/test_api_ingest.py`
- `backend/tests/unit/test_api_query.py`
- `backend/tests/unit/test_retrieval_hybrid.py`
- `backend/tests/unit/test_retrieval_reranker.py`

**Required error-path additions (minimum one per file):**

| File | Error to test | Assertion |
|------|--------------|-----------|
| test_api_ingest.py | Patch run_pipeline to raise IngestionError | HTTP 500 returned; error propagates correctly |
| test_api_query.py | Patch astream_generate to raise GenerationError | SSE done event still emitted; stream does not hang |
| test_retrieval_hybrid.py | Patch Embedder.embed_query to raise EmbeddingError | Exception propagates; no partial state written |
| test_retrieval_reranker.py | Patch cross-encoder predict to raise RuntimeError | Exception propagates; reranker does not swallow it |

**Verification grep:**
```
grep -c "pytest.raises\|side_effect" backend/tests/unit/test_api_ingest.py backend/tests/unit/test_api_query.py backend/tests/unit/test_retrieval_hybrid.py backend/tests/unit/test_retrieval_reranker.py
```
Every file must show count ≥ 1.

**Acceptance criteria:**
- [ ] Each of the four test files contains at least one error-path test using pytest.raises or side_effect
- [ ] Verification grep shows all counts ≥ 1
- [ ] poetry run pytest backend/tests/unit/ -q — all green
- [ ] No existing passing tests broken

---

### T07 — Complete initial_state Declaration

**Agent:** backend-developer
**Fixes:** F11
**File:** `backend/src/api/routes/query_agentic.py`

**Fix:** Extend the `initial_state` dict to explicitly declare all 19 `AgentState` fields. Non-input fields must be initialised to their zero values (`[]`, `False`, `None`, `0` as appropriate for the field type). This eliminates reliance on LangGraph's implicit TypedDict initialisation.

Fields to add (current omissions — verify against `backend/src/graph/state.py`):
`retrieved_docs`, `graded_docs`, `all_below_threshold`, `web_fallback_used`, `answer`, `citations`, `confidence`, `messages`, `steps_taken`, `grader_context`, `critic_context`, and any remaining unset fields.

**Acceptance criteria:**
- [ ] initial_state contains an explicit entry for every field in AgentState
- [ ] Zero-value types are correct for each field's annotation (list not None for list fields)
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T08 — retry_count Semantics Fix

**Agent:** backend-developer
**Fixes:** F14
**Files:** `backend/src/graph/state.py`, `backend/src/graph/edges.py`, `backend/src/graph/nodes/grader.py`
**Depends on:** T01 (ADR-011 must be Accepted first)

**Fix:** Implement the approach documented in ADR-011. If the decision is separate counters: add `grader_retry_count: int` and `critic_retry_count: int` to AgentState; update both edge functions and the incrementing node. If the decision is shared budget with renamed field: rename `retry_count` to `total_retry_count` throughout and document the semantics. Either way, the grader retry branch must not be dead code with the default configuration.

**Acceptance criteria:**
- [ ] Implementation matches ADR-011 decision exactly
- [ ] Grader retry branch is reachable with the default graph_max_retries value
- [ ] AgentState field semantics are unambiguous from field names alone
- [ ] poetry run mypy backend/src/ --strict — zero errors
- [ ] poetry run pytest backend/tests/unit/ -q — all green

---

### T09 — Remove Orphaned Pydantic Fields

**Agent:** backend-developer
**Fixes:** F15
**Files:** `backend/src/graph/nodes/router.py`, `backend/src/graph/nodes/critic.py`

**Fix:** Remove `_RouterOutput.reasoning`, `_CriticOutput.reasoning`, and `_CriticOutput.unsupported_claims` from their respective Pydantic models. If LangSmith tracing is planned for a future phase, create a tracking comment in the relevant node file and add it to the Phase 5 backlog — do not leave the fields defined without a consumer.

**Verification grep:**
```
grep -n "reasoning\|unsupported_claims" backend/src/graph/nodes/router.py backend/src/graph/nodes/critic.py
```
Must return zero matches (or only comments referencing a tracking issue).

**Acceptance criteria:**
- [ ] Orphaned fields removed from both model classes
- [ ] Verification grep returns zero matches in model field definitions
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T10 — SQLite Checkpointer TTL Cleanup

**Agent:** backend-developer
**Fixes:** F17
**Files:** `backend/src/config.py`, `backend/src/graph/builder.py`, `backend/src/api/main.py`, `.env.example`

**Fix:** Add `sqlite_checkpointer_ttl_days: int = 7` to Settings. On lifespan startup, before opening the graph, run a DELETE query against the checkpoints table to remove rows older than TTL. The query must execute asynchronously (use the async SQLite connection).

**Acceptance criteria:**
- [ ] `sqlite_checkpointer_ttl_days` field exists in Settings with default 7
- [ ] Startup cleanup runs before graph is opened; uses async SQLite connection
- [ ] .env.example documents SQLITE_CHECKPOINTER_TTL_DAYS
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T11 — Node Name Constants Module

**Agent:** backend-developer
**Fixes:** F18
**Files:** `backend/src/graph/node_names.py` (new), `backend/src/graph/builder.py`, `backend/src/api/routes/query_agentic.py`

**Fix:** Create `backend/src/graph/node_names.py` exporting string constants (or a dataclass/NamedTuple) for every LangGraph node name: `ROUTER`, `RETRIEVER`, `GRADER`, `GENERATOR`, `CRITIC`. Replace all string literals for node names in `builder.py` and `query_agentic.py` with imports from this module.

**Verification grep:**
```
grep -n '"router"\|"retriever"\|"grader"\|"generator"\|"critic"' backend/src/graph/builder.py backend/src/api/routes/query_agentic.py
```
Must return zero matches (string literals gone; only the constants module defines them).

**Acceptance criteria:**
- [ ] node_names.py created and exports all node name constants
- [ ] builder.py and query_agentic.py import from node_names.py
- [ ] Verification grep returns zero matches
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T12 — Aiosqlite Monkey-Patch Version Guard

**Agent:** backend-developer
**Source:** PHASE_1_2_REVIEW.md Module 3 finding
**File:** `backend/src/graph/builder.py`, `pyproject.toml`

**Fix:** Locate the `conn.is_alive` monkey-patch in builder.py. Add a version check guard:
```python
import langgraph_checkpoint_sqlite
assert langgraph_checkpoint_sqlite.__version__ < "2.0.12", (
    "Remove conn.is_alive monkey-patch: fixed in langgraph-checkpoint-sqlite>=2.0.12"
)
```
Add a comment in pyproject.toml next to the `langgraph-checkpoint-sqlite` pin explaining the monkey-patch removal trigger version.

**Acceptance criteria:**
- [ ] Version check guard present in builder.py before the monkey-patch
- [ ] pyproject.toml comment documents removal trigger version
- [ ] Guard raises AssertionError if library is updated past the fixed version
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T13 — Lift AzureChatOpenAI Clients into Lifespan

**Agent:** backend-developer
**Fixes:** F06
**Files:** `backend/src/graph/builder.py`, `backend/src/api/main.py`, `backend/src/api/deps.py`
**Depends on:** T01–T12 complete (all Batch 1 tasks)

This is the central lifespan restructuring that unblocks T14, T15, T16. Do not start until all Batch 1 tasks are Done.

**Fix:** Refactor `build_graph()` to accept `llm: AzureChatOpenAI` and `llm_4o: AzureChatOpenAI` (or the relevant client names) as parameters instead of constructing them internally. In `main.py` lifespan: create both clients once, store as `app.state.llm_chat` and `app.state.llm_4o`, pass to `build_graph()`. Expose via `Dep` aliases in `deps.py`.

**Verification grep:**
```
grep -n "AzureChatOpenAI(" backend/src/graph/builder.py
```
Must return zero matches.

**Acceptance criteria:**
- [ ] build_graph() accepts LLM clients as parameters
- [ ] Both clients created exactly once in main.py lifespan
- [ ] app.state stores both clients
- [ ] deps.py exposes LLM Dep aliases
- [ ] Verification grep returns zero matches in builder.py
- [ ] Tests can inject mock LLM without rebuilding the graph
- [ ] poetry run mypy backend/src/ --strict — zero errors
- [ ] poetry run pytest backend/tests/unit/ -q — all green

---

### T14 — GenerationChain LLM Injection

**Agent:** backend-developer
**Fixes:** F07
**File:** `backend/src/generation/chain.py`
**Depends on:** T13

**Fix:** Refactor `GenerationChain.__init__` to accept `llm: AzureChatOpenAI` as a constructor argument. Remove the internal `AzureChatOpenAI(...)` instantiation. Wire the injection point from the lifespan client created in T13.

**Verification grep:**
```
grep -n "AzureChatOpenAI(" backend/src/generation/chain.py
```
Must return zero matches.

**Acceptance criteria:**
- [ ] GenerationChain.__init__ accepts llm as a parameter
- [ ] No AzureChatOpenAI instantiation in chain.py
- [ ] Verification grep returns zero matches
- [ ] poetry run mypy backend/src/ --strict — zero errors

---

### T15 — Retriever SSE agent_step Event

**Agent:** backend-developer
**Fixes:** F13
**Files:** `backend/src/api/schemas/agentic.py`, `backend/src/api/routes/query_agentic.py`
**Depends on:** T13 (node name constants from T11 must also be in place)

**Fix:** Add `RetrieverStepPayload` to `src/api/schemas/agentic.py` with fields: `doc_count: int`, `strategy: str`, `duration_ms: int`. Extend `AgentStepEvent.node` literal to include `"retriever"`. In the `_stream()` function of `query_agentic.py`, add a retriever branch that yields an `agent_step` event using `NodeNames.RETRIEVER`.

**New schema contract:**

| Field | Type | Notes |
|-------|------|-------|
| `doc_count` | `int` | Number of documents returned by retriever |
| `strategy` | `str` | Retrieval strategy used (dense/hybrid/web) |
| `duration_ms` | `int` | Node execution time in milliseconds |

**Acceptance criteria:**
- [ ] RetrieverStepPayload defined in agentic.py with correct field types
- [ ] AgentStepEvent.node literal includes "retriever"
- [ ] query_agentic.py retriever branch yields agent_step event
- [ ] poetry run mypy backend/src/ --strict — zero errors
- [ ] poetry run pytest backend/tests/unit/ -q — all green

---

### T16 — Qdrant Client Injection (DenseRetriever + QdrantVectorStore)

**Agent:** backend-developer
**Fixes:** F01, F02
**Files:** `backend/src/retrieval/dense.py`, `backend/src/retrieval/hybrid.py`, `backend/src/ingestion/vector_store.py`, `backend/src/ingestion/pipeline.py`, `backend/src/api/routes/ingest.py`
**Depends on:** T14, T15

**Fix (F01):** Remove the private `AsyncQdrantClient` from `DenseRetriever.__init__`. Accept `client: AsyncQdrantClient` as a constructor argument. Thread the lifespan client through `HybridRetriever` → `DenseRetriever`. Remove `DenseRetriever.close()` (caller owns the client lifetime).

**Fix (F02):** Accept `client: AsyncQdrantClient` as a constructor argument in `QdrantVectorStore`. Update `run_pipeline()` signature to accept the client. Thread the lifespan `app.state.qdrant_client` through the ingest route into `run_pipeline()`.

**Verification greps:**
```
grep -rn "AsyncQdrantClient(" backend/src/retrieval/ --include="*.py"
grep -rn "AsyncQdrantClient(" backend/src/ingestion/ --include="*.py"
```
Both must return zero matches.

**Acceptance criteria:**
- [ ] DenseRetriever accepts AsyncQdrantClient as constructor argument
- [ ] DenseRetriever.close() removed
- [ ] QdrantVectorStore accepts AsyncQdrantClient as constructor argument
- [ ] run_pipeline() receives the lifespan client, not creates a new one
- [ ] Both verification greps return zero matches
- [ ] poetry run mypy backend/src/ --strict — zero errors
- [ ] poetry run pytest backend/tests/unit/ -q — all green

---

### T17 — Citation Relocation and retrieved_docs Fix

**Agent:** backend-developer
**Fixes:** F05, F12
**Files:** `backend/src/schemas/generation.py` (delete), `backend/src/api/schemas/__init__.py` or `backend/src/api/schemas/generation.py` (new), `backend/src/graph/state.py`, `backend/src/graph/nodes/generator.py`, `backend/src/generation/chain.py`
**Depends on:** T16 (import sites must be stable), T01 (ADR-011 dictates retrieved_docs strategy)

**Fix (F05):** Move `Citation` and `GenerationResult` to `backend/src/api/schemas/` (either into `__init__.py` or a new `generation.py` sub-module). Update all import sites. Delete `backend/src/schemas/generation.py` once empty.

**Fix (F12):** Implement the retrieved_docs strategy documented in ADR-011. Either: (a) change `Annotated[list[Document], operator.add]` to plain replacement semantics and reset the list each retry, or (b) keep operator.add but deduplicate by `chunk_id` inside `grader_node` before scoring. The generator must receive only the current retry's deduplicated context, not the full accumulated list.

**Verification greps:**
```
grep -rn "from src.schemas.generation" backend/src/ --include="*.py"
grep -rn "from backend.src.schemas.generation" backend/src/ --include="*.py"
```
Both must return zero matches.

**Acceptance criteria:**
- [ ] Citation and GenerationResult live in src/api/schemas/
- [ ] src/schemas/generation.py deleted
- [ ] All import sites updated
- [ ] Both verification greps return zero matches
- [ ] retrieved_docs accumulation strategy matches ADR-011 decision
- [ ] Generator receives bounded context on each retry
- [ ] poetry run mypy backend/src/ --strict — zero errors
- [ ] poetry run pytest backend/tests/unit/ -q — all green

---

### T18 — crypto.randomUUID() Non-HTTPS Fallback

**Agent:** frontend-developer
**Source:** PHASE_1_2_REVIEW.md Module 5 finding
**File:** `frontend/src/hooks/useAgentStream.ts`

**Fix:** `crypto.randomUUID()` is only available in secure contexts (HTTPS or localhost). Add a fallback for non-HTTPS environments:
```typescript
const generateUUID = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
};
```
Replace the bare `crypto.randomUUID()` call with `generateUUID()`.

**Acceptance criteria:**
- [ ] generateUUID() helper defined and used for session ID generation
- [ ] No bare crypto.randomUUID() call in the hook
- [ ] npm run tsc --noEmit — zero errors (no `any` types introduced)
- [ ] npm run lint — zero warnings

---

### T19 — ragas Eval Group Isolation

**Agent:** backend-developer
**Source:** PHASE_1_2_REVIEW.md Section 3 finding
**File:** `pyproject.toml`

**Fix:** Verify that `ragas` appears only under `[tool.poetry.group.eval.dependencies]` and not under `[tool.poetry.dependencies]` or `[tool.poetry.group.dev.dependencies]`. If misplaced, move it to the eval group. Run `poetry install --without eval` and confirm the install succeeds without ragas.

**Verification grep:**
```
grep -n "ragas" pyproject.toml
```
Must show ragas only under the eval group section.

**Acceptance criteria:**
- [ ] ragas is exclusively in [tool.poetry.group.eval.dependencies]
- [ ] poetry install --without eval succeeds without installing ragas
- [ ] Verification grep confirms placement

---

### T20 — Real Streaming via astream_events (Deferred)

**Status:** ⚠️ Deferred to Phase 5 (Observability)
**Source:** PHASE_1_2_REVIEW.md Module 4 finding
**Reason:** The current pseudo-streaming (splitting completed answer string) meets the Phase 2 gate. True token-level TTFT requires migrating to `astream_events` or a LangChain async callback, which intersects with the Phase 5 observability work. A DASHBOARD.md entry will track this.

---

### T21 — Playwright E2E Tests (Deferred)

**Status:** ⚠️ Deferred to Phase 5 (Observability)
**Source:** PHASE_1_2_REVIEW.md Section 4 finding
**Reason:** Playwright E2E test infrastructure setup is Phase 5 scope per PROJECT_PLAN.md. The parallel SSE streaming scenarios will be covered there alongside full observability validation.

---

## Phase Gate Criteria

All of the following must be true before Phase 3 (Azure Connectors) begins:

| Gate | Check | Pass Condition | Status |
|------|-------|----------------|--------|
| G01 | ADR-015 exists | `docs/adr/015-crag-retry-budget.md` present and Status: Accepted | ✅ |
| G02 | BM25 async I/O | `grep -rn "pickle\.load\|pickle\.dump" backend/src/ --include="*.py" \| grep -v asyncio.to_thread` returns zero | ✅ |
| G03 | SecretStr boundary | `grep -n "langsmith_api_key" backend/src/config.py` shows SecretStr | ✅ |
| G04 | CORS default | `grep -n "cors_origins" backend/src/config.py` default is `[]` | ✅ |
| G05 | No direct settings in edges | `grep -n "get_settings()" backend/src/graph/edges.py` returns zero | ✅ |
| G06 | Error-path coverage | `grep -c "pytest.raises\|side_effect"` in all four test files returns ≥ 1 each | ✅ |
| G07 | initial_state completeness | All 19 AgentState fields explicitly declared in query_agentic.py initial_state | ✅ |
| G08 | retry_count semantics | Grader retry branch reachable with default graph_max_retries=2; field names unambiguous | ✅ |
| G09 | No orphaned model fields | No _RouterOutput.reasoning or _CriticOutput orphaned fields in model definitions | ✅ |
| G10 | SQLite TTL | sqlite_checkpointer_ttl_days in Settings; startup cleanup executes | ✅ |
| G11 | Node name constants | `grep -n '"router"\|"retriever"\|"grader"\|"generator"\|"critic"' builder.py query_agentic.py` returns zero literal strings | ✅ |
| G12 | LLM lifespan singleton | `grep -n "AzureChatOpenAI(" backend/src/graph/builder.py backend/src/generation/chain.py` returns zero | ✅ |
| G13 | Qdrant lifespan singleton | `grep -rn "AsyncQdrantClient(" backend/src/retrieval/ backend/src/ingestion/ --include="*.py"` returns zero | ✅ |
| G14 | Citation schema location | `grep -rn "from src.schemas.generation" backend/src/ --include="*.py"` returns zero | ✅ |
| G15 | retrieved_docs bounded | retrieved_docs uses plain replacement semantics (no operator.add); generator context bounded per retry | ✅ |
| G16 | Retriever SSE event | Retriever node yields agent_step event; RetrieverStepPayload schema exists | ✅ |
| G17 | UUID fallback | No bare crypto.randomUUID() in useAgentStream.ts | ✅ |
| G18 | ragas isolation | ragas only in [tool.poetry.group.eval.dependencies] | ✅ |
| G19 | mypy clean | `poetry run mypy backend/src/ --strict` — zero errors | ✅ |
| G20 | ruff clean | `poetry run ruff check backend/src/ backend/tests/` — zero warnings | ✅ |
| G21 | pytest green | `poetry run pytest backend/tests/unit/ -q --tb=short` — all passing (349 passed) | ✅ |
| G22 | tsc clean | `npm run tsc --noEmit` (from frontend/) — zero errors | ✅ |
| G23 | Deferred items documented | T20 and T21 deferred to Phase 5 with justification in tasks.md | ✅ |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| ADR-011 decision on retrieved_docs forces a test rewrite in batch 5 | Medium | Medium | Write ADR-011 (T01) before starting T08 or T17; align tests with ADR decision |
| Lifespan restructuring (T13) breaks existing integration tests that mock build_graph() | Medium | High | Run full test suite before marking T13 Done; fix any mocking sites before proceeding to T14/T15 |
| Injecting Qdrant client through HybridRetriever (T16) requires interface changes across multiple files | Medium | Medium | Audit all HybridRetriever construction sites before starting T16; create a single injection point |
| Moving Citation to api/schemas/ (T17) causes circular import with graph/state.py or generation/chain.py | Medium | Medium | Use TYPE_CHECKING guard or restructure imports; confirm with mypy before merging |
| T08 retry_count refactor invalidates existing AgentState-dependent tests | Low | High | Run test suite after T08; update any test that asserts on retry_count field name |
| crypto.randomUUID() fallback introduces UUIDs with reduced entropy | Low | Low | Fallback is for dev/test only; production always uses HTTPS where crypto.randomUUID() is available |
| SQLite TTL cleanup query (T10) targets wrong schema if langgraph-checkpoint-sqlite changes table structure | Low | Medium | Pin langgraph-checkpoint-sqlite version; test TTL cleanup in unit tests with an in-memory SQLite DB |
| Deferred items (T20, T21) accumulate if Phase 5 scope is not finalized | Low | Low | Ensure DASHBOARD.md entries reference the Phase 5 tracking item explicitly |
