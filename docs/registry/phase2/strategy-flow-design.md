# Strategy Flow Design — `query_type` & `retrieval_strategy` Across the Graph

> Created: 2026-04-28 | Source: Architect review of agentic query log analysis
> Scope: `src/graph/` and `src/retrieval/` — no API route changes, no new AgentState fields
> Status: Approved for implementation

---

## Background

Analysis of a live agentic query log revealed five concrete bugs in how `query_type` and
`retrieval_strategy` are defined, assigned, and used across the graph:

1. `"dense"` and `"hybrid"` have no operational difference — both call the same `HybridRetriever.retrieve()`.
2. `"web"` is unreachable — `_STRATEGY_MAP` in the router never assigns it; Tavily is dead code at runtime.
3. CRAG retry escalation is missing — `route_after_grader` re-runs the same Qdrant search, never escalating to Tavily.
4. `retrieval_strategy` is frozen after the router — it is set once and never updated on retry paths.
5. `retrieved_docs` uses `operator.add` reducer — docs accumulate across retries and across sessions via the SQLite checkpointer, inflating grader input.

This document defines the correct semantics and the exact changes required to fix all five.

---

## Section 1 — Strategy Value Semantics

### Operational definitions

| Value | Pipeline | Use case | Who assigns it |
|---|---|---|---|
| `"dense"` | Embed → Qdrant cosine search → cross-encoder rerank. BM25 and RRF are skipped. | Ambiguous queries where keyword matching adds noise rather than signal. | Router via `_STRATEGY_MAP` |
| `"hybrid"` | Embed → Qdrant dense → BM25 sparse → RRF fusion → cross-encoder rerank. | Factual, analytical, multi-hop queries with lexical signal (entity names, codes, exact terms). | Router via `_STRATEGY_MAP` |
| `"web"` | Tavily external search. No Qdrant call. | CRAG escalation only — when local KB retrieval has failed at least twice. | Grader node / Critic node (never the router) |

### Key constraint: router never assigns `"web"`

The router classifies query **intent**. It has no visibility into whether local retrieval will succeed.
`"web"` is a corrective escalation target, not an intent classification. The router's `_RouterOutput`
Pydantic model must be narrowed to `Literal["dense", "hybrid"]`. The `"web"` value in the
`AgentState.retrieval_strategy` field remains valid — it is written by graph nodes on the CRAG path.

### `_STRATEGY_MAP` stays deterministic

The LLM's `retrieval_strategy` output field in `_RouterOutput` is discarded in favour of `_STRATEGY_MAP`.
This is correct and intentional — intent classification is the LLM's job; strategy derivation is
deterministic and must not depend on LLM reasoning.

---

## Section 2 — `HybridRetriever` Interface Change

### Constraint: YAGNI

Three strategy values require two distinct code paths in `HybridRetriever`:
- `"hybrid"` → existing pipeline (unchanged)
- `"dense"` → embed + Qdrant search + rerank, skipping BM25 and RRF
- `"web"` → handled by Tavily in the retriever node; `HybridRetriever` is not called

Two paths, one existing class. A new abstraction is not warranted. The correct change is a single
`mode` parameter on `HybridRetriever.retrieve()`:

```python
async def retrieve(
    self,
    query: str,
    k: int | None = None,
    filters: dict[str, str] | None = None,
    mode: Literal["dense", "hybrid"] = "hybrid",
) -> list[RetrievalResult]:
```

**When `mode == "dense"`**: skip `self._sparse.search()` and `reciprocal_rank_fusion()`; pass dense
results directly to `self._reranker.rerank()`.

**When `mode == "hybrid"`**: existing path unchanged.

The retriever node passes `state["retrieval_strategy"]` as `mode` when strategy is `"dense"` or
`"hybrid"`. Since `"web"` never reaches `HybridRetriever`, the `Literal["dense", "hybrid"]` type is
accurate with no cast required.

---

## Section 3 — Router → State Transition

### What the router writes (unchanged set, corrected semantics)

| Field | Value range | Notes |
|---|---|---|
| `query_type` | `"factual"` \| `"analytical"` \| `"multi_hop"` \| `"ambiguous"` | LLM classification result |
| `retrieval_strategy` | `"dense"` \| `"hybrid"` only | Derived from `_STRATEGY_MAP`; LLM strategy output is ignored |
| `query_rewritten` | `str` or `None` | HyDE for `"analytical"`, step-back for `"multi_hop"`, `None` otherwise |

### Required changes to `router.py`

1. Narrow `_RouterOutput.retrieval_strategy` to `Literal["dense", "hybrid"]` — remove `"web"` from the
   LLM output schema.
2. Update `_ROUTER_SYSTEM_PROMPT` to remove all mention of `"web"` as a selectable strategy.
3. No changes to `_STRATEGY_MAP`, query rewriting logic, or fallback behaviour.

### Why the router must not assign `"web"`

Per `architecture-rules.md` — domain-agnostic retrieval: the router classifies query intent, not
retrieval source. Web vs. local is a quality-gate escalation decision made after observing retrieval
failure, not an intent-based classification.

---

## Section 4 — Edge Function Design

### Rule: edge functions are pure routing functions

LangGraph edge functions return a routing string. They must not write to state. Any state mutation
required before a retry must be performed by the **node that precedes the edge**, not by the edge itself.

### Revised responsibilities

`route_after_grader` — pure function, no change to logic:
```
if all_below_threshold AND retry_count < max_retries → "retriever"
else → "generator"
```

`route_after_critic` — pure function, no change to logic:
```
if critic_score > critic_threshold AND retry_count < max_retries → "retriever"
else → "end"
```

### State mutation before retry — owned by nodes

**Grader node** writes `retrieval_strategy` escalation on the CRAG path:

| Condition | Action |
|---|---|
| `all_below_threshold=True`, post-increment `retry_count == 1` | Keep `retrieval_strategy` unchanged (first failure — retry same strategy) |
| `all_below_threshold=True`, post-increment `retry_count >= 2`, `web_search_enabled=True`, `web_fallback_used=False` | Write `retrieval_strategy = "web"` |
| `all_below_threshold=True`, `retry_count >= 2`, `web_search_enabled=False` | Keep `retrieval_strategy` unchanged (no Tavily available) |

**Critic node** mirrors grader escalation for the hallucination-retry path (deferred — lower priority
than CRAG path; implement after T01–T06 are complete).

### `web_search_enabled` injection

`web_search_enabled: bool = tavily_client is not None` is computed once in `build_graph()` and
captured in the grader and critic closures. No new `AgentState` field is needed. The boolean is
infrastructure state, not graph state.

### CRAG escalation sequence (with fix applied)

```
Pass 1:  router → strategy = "hybrid"
         retriever → HybridRetriever(mode="hybrid") → Qdrant hybrid search
         grader → all_below_threshold=True, retry_count becomes 1
                  retry_count == 1 → keep strategy = "hybrid"
         route_after_grader → "retriever"

Pass 2:  retriever → HybridRetriever(mode="hybrid") → second Qdrant hybrid search
         grader → all_below_threshold=True, retry_count becomes 2
                  retry_count >= 2, web_search_enabled=True → write strategy = "web"
         route_after_grader → "retriever"

Pass 3:  retriever → strategy == "web" → Tavily search
         grader → docs pass threshold → route_after_grader → "generator"
```

If `TAVILY_API_KEY` is not set: pass 2 keeps `strategy = "hybrid"`, re-retrieves from Qdrant again.
Graph always terminates at `max_retries` regardless.

---

## Section 5 — `retrieved_docs` Reducer Fix

### Current state

```python
# state.py (current — incorrect)
retrieved_docs: Annotated[list[Document], operator.add]
```

`operator.add` on a list is concatenation. Each retriever call appends to the existing list.

**On CRAG retry within a session:**
- Pass 1 returns 5 docs → state contains [doc0..doc4]
- Pass 2 returns 5 docs → state contains [doc0..doc9]
- Grader on pass 2 scores all 10 docs, 5 of which were already scored and rejected

**On checkpointer resumption (same `session_id` = same `thread_id`):**
- Previous session's docs carry forward; new retrieval appends to stale docs
- Live log evidence: BM25 index has 15 total chunks; grader reported `total_chunks=15`
  despite retriever returning only 5 — the 10 extra were from a prior session checkpoint

### Decision

Remove the reducer annotation — plain replacement:

```python
# state.py (corrected)
retrieved_docs: list[Document]
```

With no reducer, LangGraph replaces `retrieved_docs` entirely when the retriever returns a new list.
Each retrieval cycle produces a clean working set for the grader.

### Why `operator.add` is correct for `steps_taken` and wrong for `retrieved_docs`

| Field | Semantics | Correct reducer |
|---|---|---|
| `steps_taken` | Append-only observability audit log — accumulation is the intent | `operator.add` |
| `messages` | Conversation history — deduplication by message ID | `add_messages` |
| `retrieved_docs` | Per-cycle working buffer — consumed and replaced each retrieval pass | Plain replacement (no reducer) |

### Consequences

- Grader scores only fresh docs from the current pass — correct CRAG semantics
- Checkpointer resumption no longer accumulates stale docs
- Unit tests for grader and retriever node must be updated to expect replacement, not append semantics
- This is a `AgentState` contract change requiring ADR-011 before merge

---

## Section 6 — State Transition Table

| Node / Edge | Fields READ | Fields WRITTEN | Notes |
|---|---|---|---|
| **router** | `query` | `query_type`, `retrieval_strategy` (`"dense"`\|`"hybrid"` only), `query_rewritten`, `steps_taken` | Runs once at graph entry. Never re-invoked on retry. |
| **retriever** | `retrieval_strategy`, `query`, `query_rewritten`, `k`, `filters` | `retrieved_docs` (replaces), `web_fallback_used`, `steps_taken` | If `strategy="web"` and `tavily_client=None`: returns empty list, `web_fallback_used=False`. Passes `mode=strategy` to `HybridRetriever` when strategy is `"dense"` or `"hybrid"`. |
| **grader** | `retrieved_docs`, `query`, `retry_count`, `web_fallback_used` | `grader_scores`, `graded_docs`, `all_below_threshold`, `retry_count` (+1), `retrieval_strategy` (conditional), `steps_taken` | Writes `retrieval_strategy="web"` only when: `all_below_threshold=True`, post-increment `retry_count >= 2`, `web_search_enabled=True`, `web_fallback_used=False`. |
| **route_after_grader** | `all_below_threshold`, `retry_count` | _(none — pure routing function)_ | Returns `"retriever"` or `"generator"`. |
| **generator** | `query`, `graded_docs`, `query_type` | `answer`, `citations`, `confidence`, `steps_taken` | Uses `graded_docs` only; `retrieval_strategy` not read. |
| **critic** | `query`, `answer`, `graded_docs`, `retry_count`, `retrieval_strategy`, `web_fallback_used` | `critic_score`, `retrieval_strategy` (conditional), `steps_taken` | Hallucination-retry escalation mirrors grader logic. Deferred (T07). |
| **route_after_critic** | `critic_score`, `retry_count` | _(none — pure routing function)_ | Returns `"retriever"` or `"end"`. |

---

## Section 7 — Required ADRs

Three decisions require ADRs. Each must be written before its corresponding task is merged.

| ADR | Title | Key decision |
|---|---|---|
| **ADR-011** | `retrieved_docs` reducer: working buffer vs. audit log | Remove `operator.add` from `retrieved_docs`; change to plain replacement. Records the CRAG retry correctness argument and checkpointer contamination consequence of the original design. |
| **ADR-012** | CRAG escalation state ownership: nodes, not edges | `retrieval_strategy` escalation is written by grader/critic nodes, not edge functions. Records why edge functions must remain pure routing functions in LangGraph. |
| **ADR-013** | Router strategy scope: `"web"` is a CRAG escalation value only | Remove `"web"` from `_RouterOutput` schema. Records the semantic split between intent classification (router) and corrective escalation (CRAG path). |

---

## Implementation Tasks

Tasks are ordered by dependency. Tasks within the same batch may be done in parallel.

### Batch 1 — Foundation (no dependencies)

| ID | File | Change |
|---|---|---|
| **T01** | `backend/src/graph/state.py` | Remove `operator.add` reducer from `retrieved_docs`. Write ADR-011 before merging. Update all tests that rely on append semantics. |
| **T04** | `backend/src/graph/nodes/router.py` | Narrow `_RouterOutput.retrieval_strategy` to `Literal["dense", "hybrid"]`. Remove `"web"` from `_ROUTER_SYSTEM_PROMPT`. Write ADR-013 before merging. |

### Batch 2 — HybridRetriever (depends on T01)

| ID | File | Change |
|---|---|---|
| **T02** | `backend/src/retrieval/retriever.py` | Add `mode: Literal["dense", "hybrid"] = "hybrid"` param to `HybridRetriever.retrieve()`. When `mode="dense"`: skip sparse search and RRF. Add `test_retrieval_retriever.py` test for `mode="dense"`. |
| **T03** | `backend/src/graph/nodes/retriever.py` | Pass `mode=strategy` to `retriever.retrieve()` when `strategy in ("dense", "hybrid")`. Update `test_retriever.py` to assert correct `mode` is forwarded. |

### Batch 3 — CRAG escalation (depends on T01, T02, T03)

| ID | File | Change |
|---|---|---|
| **T05** | `backend/src/graph/builder.py` | Derive `web_search_enabled: bool = tavily_client is not None`. Capture in `_grader_node` and `_critic_node` closures. |
| **T06** | `backend/src/graph/nodes/grader.py` | Write `retrieval_strategy = "web"` in return dict when escalation conditions are met (see Section 4). Update `test_grader.py` with escalation and no-escalation cases. Write ADR-012 before merging. |

### Batch 4 — Cleanup (no blockers, low risk)

| ID | File | Change |
|---|---|---|
| **T07** | `backend/src/graph/nodes/critic.py` | Mirror grader escalation logic for hallucination-retry path. _(Deferred — implement after T01–T06 pass DoD gates.)_ |
| **T08** | `backend/src/graph/edges.py` | Correct `route_after_grader` docstring: remove "fall back to Tavily retrieval" — the edge is a pure routing function and does not drive strategy transitions. |

---

## Definition of Done (per task)

Each task must satisfy all gates in `development-process.md §7` before being marked done:

```bash
ruff check backend/src/ backend/tests/
mypy backend/src/ --strict
pytest backend/tests/unit/ -q --tb=short
```

Plus:
- [ ] ADR written for T01, T04, T06 before those tasks are merged
- [ ] At least one error-path test per external call touched by the task
- [ ] No new `# type: ignore` without inline justification
- [ ] Committed with a valid Conventional Commit message
