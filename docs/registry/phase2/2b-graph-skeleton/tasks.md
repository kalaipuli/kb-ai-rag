# Phase 2b — Graph Skeleton (StateGraph + Builder)

> Status: ✅ Complete | Phase: 2b | Estimated Days: 1
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-27
>
> **Prerequisite:** Phase 2a gate must pass before any task here starts.
> **Goal:** A compilable, runnable graph with stub nodes — no LLM calls yet. Proves the state machine topology, edge logic, and lifespan singleton wiring before agent logic is added.

---

## Context

This phase builds the graph container without filling the nodes with real logic. The result is a graph that can be invoked end-to-end in a unit test using deterministic stub node functions. This validates:
- Module structure under `backend/src/graph/`
- Conditional edge functions (routing logic)
- Graph compilation without runtime errors
- Lifespan singleton injection pattern (`build_graph(settings, retriever)`)
- `app.state.compiled_graph` addition to `main.py`

The stub pattern ensures no orphaned code: every file is imported by something, every function is called by a test.

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Create `backend/src/graph/` module files with stub nodes, edges, and builder | backend-developer | 2a all |
| T02 | ✅ Done | Implement `edges.py` conditional edge functions | backend-developer | T01 |
| T03 | ✅ Done | Implement `builder.py` — compile StateGraph, inject retriever singleton | backend-developer | T01, T02 |
| T04 | ✅ Done | Add `app.state.compiled_graph` to `main.py` lifespan | backend-developer | T03 |
| T05 | ✅ Done | Add `CompiledGraphDep` to `backend/src/api/deps.py` | backend-developer | T04 |
| T06 | ✅ Done | Unit tests: graph compiles, edges route correctly with mock state | backend-developer | T01–T05 |

---

## Ordered Execution Plan

### Batch 1 — No dependencies (after 2a gate)
- **T01** — Create module structure with stub node functions

### Batch 2 — After T01
- **T02** — Conditional edge functions (`route_after_grader`, `route_after_critic`)

### Batch 3 — After T02
- **T03** — Graph builder: wire nodes + edges, compile graph

### Batch 4 — After T03
- **T04** — `main.py` lifespan: add `compiled_graph` to `app.state`
- **T05** — `deps.py`: add `CompiledGraphDep`

### Batch 5 — After T01–T05
- **T06** — Unit tests for full graph skeleton

---

## Module Layout

The `backend/src/graph/` package has the following structure. Each file has exactly one responsibility. No file in `graph/nodes/` may import directly from `retrieval/` — the retriever is injected via the builder closure.

    backend/src/graph/
        __init__.py          — exports: build_graph, AgentState
        state.py             — AgentState TypedDict (created in 2a-T03)
        nodes/
            __init__.py
            router.py        — stub: classifies query type, sets retrieval strategy
            retriever.py     — stub: calls HybridRetriever or Tavily; stub accepts injected retriever
            grader.py        — stub: scores retrieved chunks for relevance
            generator.py     — stub: produces cited answer from graded docs
            critic.py        — stub: scores answer for hallucination risk
        edges.py             — conditional edge functions (pure functions, no LLM, no I/O)
        builder.py           — StateGraph compilation; returns CompiledStateGraph

    backend/tests/unit/graph/
        __init__.py
        test_state.py        — created in 2a-T03
        test_edges.py        — new: tests conditional routing logic
        test_builder.py      — new: tests graph compiles and stub invocation

---

## Definition of Done Per Task

### T01 — Module structure with stub nodes

**What:** Create all files under `backend/src/graph/` as listed in the module layout above. Each of the five node files must contain a single async stub function. Stubs return deterministic hardcoded values — no `raise NotImplementedError`. This ensures tests can run end-to-end without LLM calls.

**Stub node contract:** Each node is an async function that accepts a single `AgentState` parameter and returns a `dict[str, Any]` representing a valid partial `AgentState` update. The return value must satisfy mypy strict. For example, the router stub returns a dict containing `query_type`, `retrieval_strategy`, and a `steps_taken` entry. All five stubs must follow the same pattern.

**Acceptance criteria:**
- [ ] All 5 node files created under `backend/src/graph/nodes/` with stub implementations
- [ ] Each stub returns a valid partial `AgentState` update that passes mypy strict
- [ ] `backend/src/graph/__init__.py` exports `build_graph` and `AgentState`
- [ ] mypy backend/src/ --strict — zero errors on new files

**Conventional commit:** `feat(graph): add graph module skeleton with stub node functions`

---

### T02 — `edges.py` conditional edge functions

**Governed by:** ADR-004 (amended)

**What:** Implement two pure edge functions in `backend/src/graph/edges.py`. These functions are the sole place where routing thresholds are enforced. They have no LLM calls, no I/O, and no side effects — they read `AgentState` and return a routing string.

**`route_after_grader` routing logic:**
- Reads `state.all_below_threshold` and `state.retry_count`
- Returns `"retriever"` (Tavily web fallback path) when all grader scores are below threshold AND `retry_count` is less than `MAX_RETRIES`
- Returns `"generator"` in all other cases (at least one chunk passed, or max retries reached)

**`route_after_critic` routing logic:**
- Reads `state.critic_score` and `state.retry_count`
- Returns `"retriever"` (re-retrieve with refined query) when `critic_score` exceeds `CRITIC_THRESHOLD` AND `retry_count` is less than `MAX_RETRIES`
- Returns `"end"` in all other cases (acceptable quality, or max retries reached)

**Module-level constants (not magic numbers):**

| Constant | Value | Purpose |
|----------|-------|---------|
| `GRADER_THRESHOLD` | `0.5` | Minimum relevance score for a chunk to pass grading |
| `CRITIC_THRESHOLD` | `0.7` | Hallucination risk above which re-retrieval is triggered |
| `MAX_RETRIES` | `1` | Maximum times the graph may loop back through the retriever |

**Acceptance criteria:**
- [ ] `edges.py` implements both functions with correct `Literal` return types
- [ ] Three constants defined at module level
- [ ] mypy backend/src/ --strict — zero errors
- [ ] Unit tests in `test_edges.py` cover all branching paths (see T06)

**Conventional commit:** `feat(graph): implement conditional edge functions for grader and critic routing`

---

### T03 — `builder.py` graph compilation

**Governed by:** ADR-004 (amended)

**What:** Implement `build_graph(settings: Settings, retriever: HybridRetriever) -> CompiledStateGraph` in `backend/src/graph/builder.py`.

**Responsibility:** The builder is the only place where the graph topology is declared. It:
1. Instantiates `SqliteSaver` using `settings.sqlite_checkpointer_path` (import path confirmed by ADR-004 amendment)
2. Instantiates a `StateGraph(AgentState)`
3. Registers all five node functions; the retriever node receives `HybridRetriever` via a closure — the node function itself does not import from `retrieval/`
4. Sets `"router"` as the entry point
5. Wires edges and conditional edges as described in the graph topology below
6. Compiles and returns a `CompiledStateGraph` with the `SqliteSaver` checkpointer

**Graph topology (node → edge → node):**

    router → retriever (unconditional)
    retriever → grader (unconditional)
    grader → [route_after_grader] → generator OR retriever (conditional)
    generator → critic (unconditional)
    critic → [route_after_critic] → END OR retriever (conditional)

The two conditional edges use `route_after_grader` and `route_after_critic` from `edges.py`. The mapping passed to `add_conditional_edges` is: `{"generator": "generator", "retriever": "retriever"}` for grader, and `{"end": END, "retriever": "retriever"}` for critic.

**New `Settings` field required:** `SQLITE_CHECKPOINTER_PATH: str` with default `"data/checkpointer.sqlite"`. Must be added to `src/config.py` and `.env.example`.

**Dependency injection pattern:** `build_graph` receives `Settings` and `HybridRetriever` as parameters and returns a `CompiledStateGraph`. It is called once in the FastAPI lifespan. The compiled graph is stored on `app.state`. No graph-level object is a module global.

**Acceptance criteria:**
- [ ] `builder.py` implemented as described above
- [ ] `SQLITE_CHECKPOINTER_PATH` added to `Settings` with default `"data/checkpointer.sqlite"`
- [ ] `.env.example` updated with `SQLITE_CHECKPOINTER_PATH=data/checkpointer.sqlite`
- [ ] mypy backend/src/ --strict — zero errors
- [ ] `build_graph()` can be called in a unit test with a mock retriever and returns a compiled graph without raising

**Conventional commit:** `feat(graph): implement graph builder with SqliteSaver checkpointer`

---

### T04 — `main.py` lifespan: add compiled graph

**What:** Add two lines to the existing lifespan function in `backend/src/main.py`, immediately after the `HybridRetriever` singleton is constructed. The `build_graph` function is imported from `src.graph.builder`. The compiled graph is stored on `app.state.compiled_graph`.

No other changes to `main.py` are permitted in this task.

**Pre-implementation check (Gate 3 from development-process.md):** Verify existing `app.state` fields and `deps.py` dependency names before editing. Search for `app.state`, `QdrantClientDep`, `SettingsDep`, and `GenerationChainDep` across `deps.py` and `main.py` to confirm current state.

**Acceptance criteria:**
- [ ] `compiled_graph` added to `app.state` in the lifespan function
- [ ] `build_graph` imported at the top of `main.py` from `src.graph.builder`
- [ ] No other changes to `main.py`
- [ ] mypy backend/src/ --strict — zero errors

**Conventional commit:** `feat(api): add compiled_graph singleton to lifespan app state`

---

### T05 — `deps.py`: add `CompiledGraphDep`

**What:** Add one new FastAPI dependency alias to `backend/src/api/deps.py`. The alias follows the same pattern as existing deps (`QdrantClientDep`, `SettingsDep`).

**Design:** A `get_compiled_graph(request: Request) -> CompiledStateGraph` function reads `request.app.state.compiled_graph` and returns it. `CompiledGraphDep` is an `Annotated[CompiledStateGraph, Depends(get_compiled_graph)]` alias. This alias is the sole mechanism by which route handlers access the graph — no route handler may import from `graph/` directly.

**Acceptance criteria:**
- [ ] `CompiledGraphDep` added to `backend/src/api/deps.py`
- [ ] No changes to any other file in this task
- [ ] mypy backend/src/ --strict — zero errors

**Conventional commit:** `feat(api): add CompiledGraphDep dependency alias`

---

### T06 — Unit tests: graph skeleton

**Files:**
- `backend/tests/unit/graph/test_edges.py` — conditional edge function tests
- `backend/tests/unit/graph/test_builder.py` — graph compilation and stub invocation

**`test_edges.py` required test cases:**

| # | Scenario | Expected result |
|---|----------|----------------|
| 1 | `route_after_grader`: at least one score ≥ 0.5 | `"generator"` |
| 2 | `route_after_grader`: all scores < 0.5, `retry_count == 0` | `"retriever"` |
| 3 | `route_after_grader`: all scores < 0.5, `retry_count == 1` (max reached) | `"generator"` |
| 4 | `route_after_critic`: `critic_score ≤ 0.7` | `"end"` |
| 5 | `route_after_critic`: `critic_score > 0.7`, `retry_count == 0` | `"retriever"` |
| 6 | `route_after_critic`: `critic_score > 0.7`, `retry_count == 1` (max reached) | `"end"` |

**`test_builder.py` required test cases:**
1. `build_graph()` returns a non-None compiled graph when called with a mock retriever and mock settings
2. `compiled_graph.astream()` with a minimal `AgentState` and stub nodes completes without exception
3. `SqliteSaver` is instantiated with the path value from settings (verified via mock)

**Acceptance criteria:**
- [ ] `test_edges.py` — ≥ 6 test cases covering all branching paths
- [ ] `test_builder.py` — ≥ 3 test cases
- [ ] All tests pass with pytest backend/tests/unit/ -q
- [ ] No real Azure OpenAI or Qdrant calls in any test

**Conventional commit:** `test(graph): add edge routing and builder compilation tests`

---

## Phase 2b Gate Criteria

All of the following must be true before Phase 2c (Agent Nodes) begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | `backend/src/graph/` module | All files exist; mypy strict 0 errors |
| G02 | `edges.py` | Both conditional functions implemented with correct return types |
| G03 | `builder.py` | `build_graph()` compiles without runtime error |
| G04 | `main.py` | `app.state.compiled_graph` set in lifespan |
| G05 | `deps.py` | `CompiledGraphDep` exported |
| G06 | `test_edges.py` | ≥ 6 tests, all green |
| G07 | `test_builder.py` | ≥ 3 tests, all green |
| G08 | All existing tests | Still green (no regressions) |
| G09 | `.env.example` | `SQLITE_CHECKPOINTER_PATH` present |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| LangGraph `add_conditional_edges` signature differs from expected | Low | Medium | Confirm against pinned version docs before writing builder |
| `SqliteSaver` import path different from LangGraph public docs | Medium | Low | ADR-004 amendment (2a-T02) confirms exact path before this task |
| Stub node mypy errors due to partial `AgentState` update typing | Low | Low | Return `dict[str, Any]` explicitly; cast where needed |
| `CompiledStateGraph` not exported from expected module path | Low | Low | Check public API in pinned version; use `Any` with comment if needed |
