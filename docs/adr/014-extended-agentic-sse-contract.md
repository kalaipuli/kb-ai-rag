# ADR-014: Extended Agentic SSE Contract — Retriever/Generator Events and run Field

## Status
Accepted

## Context
ADR-004 defined the agent_step SSE event covering only three of the five LangGraph nodes
(router, grader, critic). Retriever and generator were invisible to the frontend. Additionally,
the CRAG escalation pattern means retriever and grader can run multiple times per query; the
frontend had no way to distinguish the first visit from a retry.

## Decision
1. Add RetrieverStepPayload and GeneratorStepPayload to the agentic SSE schema.
2. Add `run: int` (1-based, ge=1) to AgentStepEvent to track per-node iteration count.
3. Emit a retriever agent_step event when the retriever node completes (before grader).
4. Emit a generator agent_step event after tokens but before the citations event.
5. The backend streaming closure maintains a per-node run counter (_run_count dict) to compute run.

## Alternatives Considered
- Infer retriever/generator presence on the frontend from citations/done events: rejected —
  requires fragile client-side inference; server is authoritative on execution.
- Emit a separate "retry_start" event type for loops: rejected — run=N on each node event
  communicates the same information without a new event type.
- Fixed pipeline diagram on the frontend: rejected — cannot represent CRAG loops faithfully.

## Consequences
- Frontend can render a sequential execution trace with all 5 nodes in arrival order.
- Iteration badges (Retriever #2, Grader #2) communicate CRAG escalation naturally.
- Generator agent_step emits after tokens — informational metadata, not a streaming gate.
- The wire format gains a run field; existing frontend clients that ignore unknown fields
  will continue to work (additive change).
