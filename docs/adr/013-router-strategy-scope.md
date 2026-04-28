# ADR-013: Router Strategy Scope — `"web"` Is a CRAG Escalation Value Only

## Status
Accepted

## Context

The `_RouterOutput` Pydantic model in `src/graph/nodes/router.py` previously declared
`retrieval_strategy: Literal["dense", "hybrid", "web"]`. However, `"web"` is never
assigned by `_STRATEGY_MAP`, which derives the retrieval strategy deterministically
from `query_type` using a fixed mapping (`factual/analytical/multi_hop → "hybrid"`,
`ambiguous → "dense"`). If the LLM were to output `"web"` in its structured response,
the router would silently ignore it — `_STRATEGY_MAP` always overrides the LLM's
`retrieval_strategy` field. The presence of `"web"` in the LLM output schema was
therefore misleading: it implied the router could classify a query as requiring web
retrieval, which is not its responsibility. If future code ever changed to use the LLM's
`retrieval_strategy` output directly instead of `_STRATEGY_MAP`, the inclusion of `"web"`
could cause subtle breakage.

`"web"` is a valid value in `AgentState.retrieval_strategy` — it is written by the grader
node and critic node on the CRAG escalation path when local retrieval results fall below
quality thresholds.

## Decision

Narrow `_RouterOutput.retrieval_strategy` to `Literal["dense", "hybrid"]`. The `"web"`
value is intentionally excluded from the router's output schema because:

1. The router classifies query **intent** — it has no visibility into whether local
   retrieval will succeed.
2. `"web"` is a corrective escalation target on the CRAG path, owned by grader and
   critic nodes, not the router.
3. `_STRATEGY_MAP` never assigns `"web"`, so permitting it in the LLM schema only
   creates confusion and a potential bug surface.

`AgentState.retrieval_strategy` retains `"web"` as a valid value since grader and critic
nodes write it legitimately.

## Alternatives Considered

**Keep `"web"` in `_RouterOutput` but add a runtime assertion** — rejected. Pydantic
model validation is the correct enforcement boundary. A runtime assertion or comment is
not enforced at parse time and would be removed or missed in future edits.

**Allow the router to assign `"web"` for certain query types** — rejected. The router
classifies intent based on query structure, not on retrieval source availability. Routing
to web search is a fallback decision made after retrieval quality is assessed, which is
the grader/critic's domain.

## Consequences

- `_RouterOutput` now accurately reflects router responsibilities and cannot be
  misconfigured by a hallucinating LLM.
- `_STRATEGY_MAP` type narrows to `dict[str, Literal["dense", "hybrid"]]`, which is
  consistent with the values it actually contains.
- Pydantic validates at parse time that the LLM cannot produce `"web"` as a router
  output; any attempt raises a `ValidationError` rather than silently succeeding.
- Existing CRAG escalation behaviour (grader/critic writing `"web"` to `AgentState`) is
  unaffected.
