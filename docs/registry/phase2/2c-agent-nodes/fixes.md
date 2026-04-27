# Phase 2c — Architect Review Fixes

> Created: 2026-04-27 | Source: Architect review of Phase 2c implementation
> Rule: development-process.md §9 — all Critical and High fixes must clear before Phase 2d starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On | Assigned To |
|----|----------|--------|----------|---------|------------|-------------|
| F01 | High | ✅ | Async hygiene | `grader_chain.batch()` blocks event loop inside `async def` | — | backend-developer |
| F02 | Major | ✅ | Type safety | `state.get("retry_count", 0)` on required TypedDict field causes mypy strict error | — | backend-developer |
| F03 | Major | ✅ | DI / config isolation | `get_settings()` called inside `retriever_node` body instead of injected via closure | F04 | backend-developer |
| F04 | Major | ✅ | Lifespan singleton | `TavilyClient` instantiated per-call inside `retriever_node` | — | backend-developer |
| F05 | Minor | ✅ | Code style | Deferred `from tavily import TavilyClient` inside function body | F04 | backend-developer |
| F06 | Minor | ✅ | Interface consistency | `router_node` `llm` parameter is positional; all other nodes use keyword-only `*` | — | backend-developer |
| F07 | Advisory | ✅ | ADR coverage | No ADR for Tavily web-search integration decision | — | architect |
| F08 | Minor | ✅ | Type safety | `state.get("critic_score")` in `edges.py` bypasses TypedDict subscript typing | — | backend-developer |
| F09 | Minor | ✅ | Test coverage | `test_graph_integration.py` has zero error-path tests | — | tester |

---

## Detailed Fix Specifications

### F01 — grader_chain.batch() blocks event loop (High)

**File:** `backend/src/graph/nodes/grader.py:74`
**Issue:** `grader_chain.batch(messages_batch)` is a synchronous LangChain call executed inside `async def grader_node`. LangChain's `Runnable.batch()` has no async variant — it runs on the calling thread, blocking the asyncio event loop for the full duration of the batch LLM call. Under load this stalls all concurrent graph executions sharing the same worker process. Phase 2d will expose the graph via a FastAPI SSE route; any event-loop block will cause dropped heartbeats and client-visible latency spikes.
**Fix:** Replace the direct `grader_chain.batch(messages_batch)` call with `await asyncio.to_thread(grader_chain.batch, messages_batch)`. Add `import asyncio` at the top of the file (it is not currently imported). The return type annotation and `# type: ignore` comment remain unchanged.
**Rule:** anti-patterns.md — "Call sync file I/O or CPU-bound libs inside `async def` → wrap with `asyncio.to_thread()`"; architecture-rules.md — "Async I/O: All network and disk I/O is async. No blocking calls on the event loop."

---

### F02 — state.get("retry_count", 0) mypy strict error (Major)

**File:** `backend/src/graph/nodes/grader.py:107`
**Issue:** `retry_count` is declared as `retry_count: int` (required, non-optional) in `AgentState`. Calling `.get("retry_count", 0)` on a `TypedDict` returns `int | None` under `mypy --strict` because `.get()` is the `dict` method and TypedDict does not narrow its return type for required keys. The subsequent `+ 1` then produces `error: Unsupported left operand type for + ("int | None")`. This will block the `mypy --strict` gate that Phase 2d depends on.
**Fix:** Replace `state.get("retry_count", 0) + 1` with `state["retry_count"] + 1`. Subscript access on a required TypedDict field is correctly typed as `int` by mypy. No default is needed because LangGraph always initialises the full state before a node is called.
**Rule:** python-rules.md — "annotate everything; `mypy --strict` must pass"; CLAUDE.md Always-Apply Rules — "`mypy --strict` / `tsc --noEmit` passes — zero errors".

---

### F03 — get_settings() called inside retriever_node body (Major)

**File:** `backend/src/graph/nodes/retriever.py:112`
**Issue:** `settings = get_settings()` is called at runtime inside the node function body on every web-strategy invocation. This breaks the dependency injection pattern: nodes must receive all their dependencies via builder-injected closures, not by pulling from a global config cache at call time. It also creates an implicit coupling between the node and the config module that is invisible from the builder and cannot be overridden in tests without mocking `get_settings` globally.
**Fix:** Remove the `get_settings()` call from the node body. Add a `tavily_api_key: str` keyword-only parameter to `retriever_node` (alongside the existing `retriever` parameter). In `builder.py`, extract the key once: `tavily_key = settings.tavily_api_key.get_secret_value()` and pass it through the `_retriever_node` closure: `return await retriever_node(state, retriever=retriever, tavily_api_key=tavily_key)`. Remove the `from src.config import get_settings` import from `retriever.py` if it is no longer used after this change.
**Rule:** architecture-rules.md — "Config isolation: No hardcoded values. All config via `pydantic-settings` and `.env`"; anti-patterns.md — "Do not create a new client inside a route handler … use lifespan singleton via `Dep` alias" (generalised to: do not pull config inside a node — inject it).

---

### F04 — TavilyClient instantiated per-call inside retriever_node (Major)

**File:** `backend/src/graph/nodes/retriever.py:118`
**Issue:** `client = TavilyClient(api_key=api_key)` is executed on every web-strategy retrieval call, creating a new HTTP client object with each graph invocation. The Lifespan Singleton rule states that shared external clients must be initialised once. A per-call `TavilyClient` construction wastes connection-pool setup overhead, makes it impossible to inject a mock client in tests without patching the import, and is inconsistent with how `AsyncQdrantClient` and `AzureChatOpenAI` are managed.
**Fix:** Pass `tavily_client` as a keyword-only dependency to `retriever_node` (type `Any | None = None`, or introduce a `TavilyClientProtocol` if strict typing is desired). In `builder.py`, after the F03 fix is applied, construct the client once: `from tavily import TavilyClient; tavily_client = TavilyClient(api_key=tavily_key)` and capture it in the `_retriever_node` closure. For the `retriever is None` guard pattern already in the node, add a parallel `tavily_client is None` guard for the web branch.
**Rule:** architecture-rules.md — "Lifespan Singleton — No Per-Request Client Creation"; anti-patterns.md — "Do not create a new client inside a route handler … use lifespan singleton via `Dep` alias".

---

### F05 — Deferred import inside retriever_node function body (Minor)

**File:** `backend/src/graph/nodes/retriever.py:114`
**Issue:** `from tavily import TavilyClient` is placed inside the function body as a deferred import. Module-level imports are the project standard. Deferred imports obscure the module's dependency surface, complicate static analysis, and can hide `ImportError` until the code path is exercised at runtime.
**Fix:** After F04 is resolved (the import moves to `builder.py`), this deferred import in `retriever.py` is eliminated entirely. If for any reason `TavilyClient` must be referenced in `retriever.py` (e.g., for a `TavilyClientProtocol`), place the import at the top of the file under a `TYPE_CHECKING` guard or as a plain module-level import.
**Rule:** python-rules.md — module-level imports; anti-patterns.md — no hidden/deferred imports.

---

### F06 — router_node llm parameter is positional, not keyword-only (Minor)

**File:** `backend/src/graph/nodes/router.py:50`
**Issue:** `async def router_node(state: AgentState, llm: AzureChatOpenAI)` takes `llm` as a positional parameter. Every other node uses `(state: AgentState, *, llm: AzureChatOpenAI)` with a bare `*` to enforce keyword-only. This inconsistency means `router_node` can be called as `router_node(state, some_llm)` without a keyword, masking accidental argument transposition. It also makes the public API of `router_node` differ visually from the other four nodes, increasing cognitive load for anyone writing a new node.
**Fix:** Change the signature to `async def router_node(state: AgentState, *, llm: AzureChatOpenAI) -> dict[str, Any]:`. The existing builder call `router_node(state, llm=llm)` already passes `llm` by keyword and requires no change.
**Rule:** python-rules.md — consistent function signatures; architecture-rules.md — interface consistency across agent nodes.

---

### F07 — No ADR for Tavily web-search integration (Advisory)

**File:** `docs/adr/` (new file required)
**Issue:** Tavily is the first third-party SaaS dependency introduced in Phase 2c that is not Azure. It carries its own cost model, API key lifecycle, rate limits, data-privacy considerations (queries leave the Azure trust boundary), and fallback policy decisions (when to invoke web search vs. returning a low-confidence answer from local docs). None of these trade-offs are recorded. Phase 2d will expose the web fallback path through the public API, at which point the absence of a documented policy becomes an operational risk.
**Fix:** Write `docs/adr/010-tavily-web-fallback.md` covering: context (need for web fallback when local retrieval fails), decision (Tavily over alternatives such as Bing Search API, SerpAPI, or no web fallback), alternatives considered, consequences (data leaves Azure boundary, requires `TAVILY_API_KEY`, fallback only triggers on `retrieval_strategy == "web"`).
**Rule:** architecture-rules.md — "Every significant architectural choice gets an ADR in `docs/adr/`. When to write one: choosing between two viable options, accepting a trade-off."

---

### F08 — state.get("critic_score") in edges.py (Minor)

**File:** `backend/src/graph/edges.py:36`
**Issue:** `critic_score = state.get("critic_score") or 0.0` uses the `dict.get()` method on a TypedDict. Under `mypy --strict`, `TypedDict` instances do not guarantee that `.get()` narrows the return type of optional fields correctly — mypy may emit `error: TypedDict "AgentState" has no key "critic_score" with .get()` depending on the mypy version, or silently return `float | None | None`. The `or 0.0` pattern is also semantically incorrect for the value `0.0` itself: `0.0 or 0.0` evaluates to `0.0` (correct), but `0.001 or 0.0` evaluates to `0.001` (also correct) — however the intent to default `None` to `0.0` is clearer with an explicit `None` check.
**Fix:** Replace with `critic_score: float = state["critic_score"] if state["critic_score"] is not None else 0.0`. `critic_score` is typed `float | None` in AgentState so subscript access returns `float | None`, and the explicit `None` guard narrows it to `float` for mypy.
**Rule:** python-rules.md — "annotate everything; `mypy --strict` must pass"; prefer explicit `None` checks over falsy `or` patterns on numeric types.

---

### F09 — test_graph_integration.py has zero error-path tests (Minor)

**File:** `backend/tests/unit/graph/test_graph_integration.py`
**Issue:** The integration smoke tests cover four routing paths (happy path, CRAG re-route, Self-RAG re-route, max-retry guard) but include zero error-path scenarios. The DoD rule requires at least one error-path test per external call. The graph makes Azure OpenAI calls in every node; an LLM failure mid-graph (e.g., during the Generator node) should be tested to confirm the graph terminates gracefully and does not raise an unhandled exception into the Phase 2d API route handler.
**Fix:** Add at least one test function that patches the LLM mock to raise an exception mid-graph (e.g., `side_effect=Exception("Azure throttled")` on the Generator's `ainvoke`) and asserts that: (a) `graph.ainvoke()` does not propagate the exception, (b) the returned state contains a non-empty `answer` field with the error fallback string, and (c) `steps_taken` contains a `"generator:error:…"` entry.
**Rule:** CLAUDE.md Always-Apply Rules — "Unit test written and passing (including at least one error-path test per external call)"; development-process.md §7 Definition of Done.

---

## Clearance Order

**Batch 1 — Parallel (no inter-dependencies):**
- F01: grader async fix
- F02: grader TypedDict subscript fix
- F06: router keyword-only signature fix
- F08: edges.py TypedDict subscript fix

**Batch 2 — Sequential (F04 before F05, F03 after F04):**
- F04: construct TavilyClient in builder and inject via closure
- F03: remove `get_settings()` from node body (requires F04's closure pattern to be in place first)
- F05: remove deferred import (resolved as a side-effect of F03/F04; verify no residual import remains)

**Batch 3 — Independent, can run in parallel with Batch 2:**
- F07: write ADR-010

**Batch 4 — After all implementation fixes are green:**
- F09: add error-path integration test (depends on node error-fallback behaviour confirmed stable)

---

## Verification Checklist

- [ ] F01: `poetry run pytest backend/tests/unit/graph/test_grader.py` passes; `asyncio.to_thread` present in grader.py; `poetry run mypy --strict backend/src/graph/nodes/grader.py` zero errors
- [ ] F02: `poetry run mypy --strict backend/src/graph/nodes/grader.py` zero errors; `state["retry_count"]` subscript in grader.py:107
- [ ] F03: `grep -n "get_settings" backend/src/graph/nodes/retriever.py` returns no output; `tavily_api_key` parameter present in `retriever_node` signature
- [ ] F04: `grep -n "TavilyClient(api_key" backend/src/graph/nodes/retriever.py` returns no output; `TavilyClient` construction present in `builder.py`
- [ ] F05: `grep -n "from tavily" backend/src/graph/nodes/retriever.py` returns no output
- [ ] F06: `grep -n "def router_node" backend/src/graph/nodes/router.py` shows `*, llm` in signature
- [ ] F07: `ls docs/adr/010-tavily-web-fallback.md` exists and has Status: Accepted
- [ ] F08: `poetry run mypy --strict backend/src/graph/edges.py` zero errors; `state["critic_score"]` subscript with explicit `None` check in edges.py:36
- [ ] F09: `poetry run pytest backend/tests/unit/graph/test_graph_integration.py` passes; `grep -n "side_effect=Exception\|raises\|error" backend/tests/unit/graph/test_graph_integration.py` returns at least one match
- [ ] Full suite: `poetry run pytest backend/tests/unit/graph/ -q` all green; `poetry run mypy --strict backend/src/graph/` zero errors; `poetry run ruff check backend/src/graph/` zero warnings
