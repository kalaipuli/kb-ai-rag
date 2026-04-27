# ADR-004: LangGraph for Agent Orchestration over Static LangChain Chain

## Status
Accepted (amended Phase 2 — 2026-04-27)

## Context
Phase 2 of the platform replaces the static Phase 1 RetrievalQA chain with a multi-agent pipeline that implements:
- **Corrective RAG (CRAG)**: Grader evaluates retrieved chunks; if all score below threshold, web search (Tavily) is triggered as a fallback
- **Self-RAG**: Critic evaluates the generated answer for hallucination risk; if risk exceeds threshold, the Retriever is re-invoked with a refined query (max 1 retry)
- **Adaptive RAG**: Router classifies query intent (factual, analytical, multi-hop, ambiguous) and selects retrieval strategy accordingly

These patterns require:
1. Conditional routing: the path through the pipeline depends on intermediate results
2. Retry loops: the Critic can send control back to the Retriever
3. Shared state: all agents must read from and write to a common state object without direct return-value coupling
4. Debuggability: each agent step must be inspectable in traces
5. Multi-turn memory: conversation history must persist across API requests within a session

A static LangChain LCEL chain cannot express conditional routing, loops, or shared mutable state.

## Decision
Use LangGraph to define a stateful directed graph where:
- Each agent (Router, Retriever, Grader, Generator, Critic) is a graph node (a Python function)
- Transitions between nodes are typed edges, with conditional edges for routing decisions
- The shared `AgentState` TypedDict is the single source of truth; agents read from it and return partial state updates
- `SqliteSaver` checkpointer persists state per session_id for multi-turn conversation

## Alternatives Considered

**Static LangChain LCEL chain**: Linear pipeline, composable with `|` operator. Rejected because: (a) LCEL cannot express conditional routing — there is no built-in branch operator for runtime decisions, (b) retry loops require custom code that defeats the purpose of using a chain abstraction, (c) no shared mutable state — each step receives the output of the previous step only, not a global state object.

**CrewAI**: Role-based multi-agent framework. Rejected because: (a) CrewAI abstracts the graph topology away, making it harder to control and reason about exact routing decisions, (b) debugging individual agent steps is less transparent than LangGraph's node-level tracing, (c) the portfolio value is in showing explicit architectural reasoning about agent flows, which CrewAI obscures.

**Custom async orchestrator (asyncio + handwritten state machine)**: Build a custom state machine with asyncio. Rejected because: (a) LangGraph already provides exactly this — a typed state machine with conditional edges — so building it again is a YAGNI violation, (b) LangSmith tracing integrates automatically with LangGraph, providing observability for free, (c) maintenance burden of a custom orchestrator in a solo project is too high.

**AutoGen (Microsoft)**: Multi-agent conversation framework. Rejected because: (a) conversation-based agent communication does not map cleanly onto the retrieve-grade-generate-critique pipeline, (b) AutoGen's primary strength is code execution agents, not retrieval-augmented generation pipelines.

## Consequences

**Positive:**
- All agents communicate exclusively through `AgentState` — no direct return-value coupling between agents, making the graph topology refactorable without changing agent internals
- LangGraph's conditional edges express the CRAG and Self-RAG routing logic declaratively
- `SqliteSaver` provides multi-turn conversation persistence with zero additional infrastructure
- LangSmith traces each graph execution end-to-end, with per-node latency and token cost visible
- The compiled graph is a callable object: `graph.invoke(state, config={"configurable": {"thread_id": session_id}})`

**Negative:**
- All agent functions must follow the LangGraph node contract: accept `AgentState`, return `dict[str, Any]` (partial state update). This is a non-standard function signature.
- LangGraph is a core dependency; a breaking API change in a minor version can stop agent orchestration. Pin the version and review changelogs before upgrading.
- `SqliteSaver` uses SQLite, which does not support concurrent writes from multiple API replicas. In production (Phase 7, multiple Container Apps replicas), migrate to `PostgresSaver` or `CosmosSaver`.
- The graph topology (edges, conditions) must be understood holistically — a local change to one edge can affect the entire execution path.

## Amendment — Phase 2 Confirmed Configuration

**Date:** 2026-04-27
**Trigger:** T01 environment audit completed prior to Phase 2 implementation gate.

### 1. Confirmed LangGraph version and pin rationale

Pinned versions in `pyproject.toml` (tilde ranges):

```
langgraph = "~0.2.76"
langchain = "~0.3.28"
langchain-core = "~0.3.84"
langchain-openai = "~0.2.14"
langchain-text-splitters = "~0.3.11"
```

Tilde ranges (`~X.Y.Z`) allow patch-level updates (Z increment) while blocking minor-version bumps. This prevents mid-phase API surface breaks — LangGraph has introduced breaking changes between minor versions (e.g., 0.1.x → 0.2.x) — while still receiving bug and security fixes automatically.

### 2. SqliteSaver status and checkpointer roadmap

`SqliteSaver` is **not bundled** in `langgraph 0.2.76`. It is shipped in the separate package `langgraph-checkpoint-sqlite`, which must be added as an explicit dependency when implementing session persistence.

Checkpointer roadmap by phase:

| Phase | Checkpointer | Notes |
|-------|-------------|-------|
| 2a (gate zero) | `MemorySaver` (from `langgraph.checkpoint.memory`) | Confirmed available in current install; no extra package required |
| 2b/2c (session persistence) | `SqliteSaver` (from `langgraph-checkpoint-sqlite`) | Add `langgraph-checkpoint-sqlite` to `pyproject.toml` when implementing |
| 7 (multi-replica production) | `PostgresSaver` or `CosmosSaver` | Required because SQLite does not support concurrent writes from multiple Container Apps replicas |

The original Consequences section referenced `SqliteSaver` as available without qualification. This amendment supersedes that claim for Phase 2a.

### 3. stream_mode decision

**Decision: `stream_mode="updates"` is the required mode for the agentic SSE endpoint.**

Confirmed behaviour:

- `stream_mode="updates"` → yields `AddableUpdatesDict` — one dict per node that ran: `{node_name: state_delta}`. Only the fields written by that node are included.
- `stream_mode="values"` → yields `AddableValuesDict` — full `AgentState` snapshot after each node tick.

Rationale for choosing `"updates"`:

The agentic SSE endpoint emits one `agent_step` event per node execution. The event payload is the state delta produced by that node. Using `"updates"` maps this directly: `state_delta = next(stream)` is the payload. Using `"values"` would send the entire `AgentState` on every node tick — including all previously accumulated messages, retrieved documents, and scores — making each SSE frame unnecessarily large and coupling the wire format to the full state schema.

### 4. SqliteSaver single-writer constraint

SQLite enforces a single-writer lock. When `SqliteSaver` is in use (Phase 2b/2c), the FastAPI process must be started with `--workers 1`. Running multiple Uvicorn workers against the same SQLite checkpoint database causes write contention and session corruption.

Enforcement:

- `Makefile` and `docker-compose.yml` for local dev must pass `--workers 1` when `SqliteSaver` is configured.
- Phase 7 migration to `PostgresSaver` or `CosmosSaver` removes this constraint and allows horizontal scaling.

### 5. X-Session-ID header contract

Every route handler that invokes the compiled graph must read the `X-Session-ID` request header and pass it to `astream()` as the LangGraph thread identifier:

```python
session_id: str = request.headers.get("X-Session-ID", str(uuid.uuid4()))
config = {"configurable": {"thread_id": session_id}}
async for update in compiled_graph.astream(input_state, config=config, stream_mode="updates"):
    ...
```

Rules:
- If the header is absent, the handler generates a new UUID for that request (stateless fallback).
- The header value is passed through verbatim as `thread_id`; no server-side transformation.
- The Next.js frontend must send `X-Session-ID` on every turn within a session to enable multi-turn memory.
- This contract is stable. Changing `thread_id` to any other `configurable` key is a breaking change requiring an ADR amendment.

### 6. duration_ms field commitment

Every `agent_step` SSE event payload must include a `duration_ms: int` field from the first Phase 2 implementation. This field records the wall-clock time in milliseconds for the node that produced the update.

Rationale:
- Per-node latency is required for RAGAS latency metrics and LangSmith trace validation.
- Retrofitting `duration_ms` after the wire format is established requires a version bump of the SSE event schema, which breaks existing frontend consumers.

Implementation contract:

```python
# Inside each node or the streaming wrapper
start = time.monotonic()
# ... node logic ...
duration_ms = int((time.monotonic() - start) * 1000)

# SSE payload structure (minimum required fields)
{
    "event": "agent_step",
    "node": "<node_name>",
    "delta": state_delta,
    "duration_ms": duration_ms
}
```

`duration_ms` is a required field. SSE consumers must not treat it as optional. Any future removal or rename is a breaking wire format change.

### Confirmed public API surface (as of langgraph 0.2.76)

```python
from langgraph.graph import StateGraph, CompiledStateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
```

Confirmed working methods: `StateGraph.add_node()`, `add_conditional_edges()`, `compile()`, `CompiledStateGraph.astream()`.
