# ADR-012: CRAG Escalation State Ownership — Nodes, Not Edges

## Status
Accepted

## Context

The `route_after_grader` edge function routes to "retriever" when all grader scores fall
below `settings.grader_threshold`. The original design intent also required a strategy
escalation path: after multiple failed retrievals, the system should fall back from Qdrant
hybrid search to Tavily web search (CRAG — Corrective RAG pattern).

The naive approach was to put this escalation logic inside the edge function. However, edge
functions in LangGraph are **pure routing functions** — they receive state, compute a routing
key string, and return it. They do not return a dict and do not have write access to
`AgentState`. A conditional edge that returns `{"retrieval_strategy": "web", "next": "retriever"}`
instead of `"retriever"` is not valid under the LangGraph routing contract and will raise at
graph compile time.

This means that state mutation needed before a retry — specifically writing
`retrieval_strategy = "web"` — cannot happen in the edge and must happen elsewhere.

## Decision

State mutation before a retry is the **responsibility of the node that precedes the edge**,
not the edge function itself.

Specifically:

- The **grader node** writes `retrieval_strategy = "web"` into its return dict when the
  following escalation conditions are all true:
  - `all_below_threshold = True` (all chunk scores fell below threshold)
  - post-increment `retry_count >= 2` (first failure gets a same-strategy retry; only the
    second failure triggers escalation)
  - `web_search_enabled = True` (Tavily is available in this deployment)
  - `web_fallback_used = False` (Tavily has not already been used this session)
- When none of these conditions are met, the grader node's return dict does **not** include
  a `retrieval_strategy` key. LangGraph leaves the existing value unchanged (no-op).
- The edge function `route_after_grader` remains a pure routing function returning a string.

The `web_search_enabled` boolean is captured in the grader closure at `build_graph()` time
rather than stored in `AgentState`. It represents infrastructure configuration (whether Tavily
is configured), not transient graph state. This keeps `AgentState` free of deployment-time
constants.

## Alternatives Considered

**1. Escalation in the edge function via dict return.**
Rejected. LangGraph conditional edge functions must return a routing key string. Returning a
dict is not supported and breaks the routing contract.

**2. A dedicated "escalation node" inserted between grader and retriever.**
Rejected as over-engineering (YAGNI). The escalation logic is a three-condition guard that
fits naturally in the grader return dict. Adding an extra node increases graph complexity and
latency for a single dict key assignment.

**3. Store `web_search_enabled` in `AgentState`.**
Rejected. `web_search_enabled` is determined at deployment time from environment configuration.
It does not change during a graph run. Storing it in per-request state couples infrastructure
decisions to the graph schema and would require every test to supply the flag.

## Consequences

- Edge functions remain pure, stateless, and easily testable in isolation — they take state and
  return a string with no side effects.
- The grader node is responsible for both quality assessment and escalation signalling. This is
  a bounded addition: the escalation is a single conditional block on existing computed values.
- The `web_search_enabled` flag is passed via closure, consistent with how `llm` is already
  injected into the grader and other nodes.
- The `web_fallback_used` guard in `AgentState` prevents double-escalation within a session.
  Once Tavily has been used, `web_fallback_used` is set to `True` by the retriever node and
  the grader will not write `retrieval_strategy = "web"` again.
- The critic node mirrors this pattern for the hallucination-retry escalation path (deferred
  to T07): if hallucination risk is high and Tavily has not been used, the critic node writes
  `retrieval_strategy = "web"` before its return, and the edge routes to retriever.
