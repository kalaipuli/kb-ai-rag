# ADR-004: LangGraph for Agent Orchestration over Static LangChain Chain

## Status
Accepted

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
