# Agentic Flow Rendering — Design Proposal

> Created: 2026-05-02 | Source: Orchestrator design session
> Scope: `frontend/src/components/AgentTrace.tsx` and related components
> Status: Approved for implementation

---

## Problem

The current `AgentTrace` renders one card per completed node stacked vertically. It communicates
*progress* during streaming but communicates nothing about *decisions* after the flow completes.
Specifically:

- `query_rewritten` exists in `AgentState` and is now surfaced in `RouterStepPayload` but is
  never shown to the user.
- The rewrite technique (HyDE vs. Step-Back) is invisible.
- Grader routing decisions ("retry", "escalate to web", "proceed") are reduced to a warning badge
  with no explanation of what follows.
- Critic verdict ("accept" or "rerun") is not shown at all.
- CRAG retry loops appear as duplicate cards with a run-number badge — nothing shows *why* the loop
  happened or that it was a second pass over the same retrieval stage.

The three new backend fields (`rewrite_method`, `decision`, `verdict`) that were added in the
preceding commit are the prerequisite for this work. The rendering task assumes those fields are
present in the SSE stream.

---

## Guiding Principle

The flow has two distinct jobs depending on *when* the user sees it:

| Moment | User's question | Correct shape |
|--------|----------------|---------------|
| While streaming | "Is it working? Where is it?" | Progress — cards animate in one by one; pending nodes dimmed |
| After `done` | "What actually happened and why?" | Decision trail — the full story of what the agent chose |

These are rendered by two separate components. `AgentTrace` becomes a router that picks between them
on the `isStreaming` prop.

---

## Part 1 — Type Updates (prerequisite)

The frontend `types/index.ts` payload interfaces must mirror the new backend fields before any
rendering work begins.

```typescript
// types/index.ts — extend existing interfaces

interface RouterStepPayload {
  query_type: "factual" | "analytical" | "multi_hop" | "ambiguous";
  strategy: "dense" | "hybrid" | "web";
  duration_ms: number;
  query_rewritten: string | null;                      // NEW
  rewrite_method: "none" | "hyde" | "stepback";        // NEW
}

interface GraderStepPayload {
  scores_all: number[];
  passed_count: number;
  threshold: number;
  all_below_threshold: boolean;
  duration_ms: number;
  decision: "proceed" | "retry" | "escalate_web";      // NEW
}

interface CriticStepPayload {
  hallucination_risk: number;
  reruns: number;
  duration_ms: number;
  verdict: "accept" | "rerun";                         // NEW
}
```

No changes to `RetrieverStepPayload`, `GeneratorStepPayload`, or `AgentStepEvent`.

---

## Part 2 — Live Mode Enrichment (streaming cards)

The existing card-per-node stack is correct for the streaming case. Three cards get richer content.

### RouterCard — query transformation section

When `rewrite_method !== "none"`, render a transformation block below the strategy badges:

```
┌─ Router ────────────────────────────────────────┐
│  [Analytical reasoning]  [Hybrid search]        │
│                                                 │
│  ↳ HyDE rewrite                                │
│    "Transformer attention scales quadratically  │
│     because each token attends to all..."       │
│                                          43ms   │
└─────────────────────────────────────────────────┘
```

- Label is `"HyDE rewrite"` when `rewrite_method === "hyde"`, `"Step-back rewrite"` when
  `"stepback"`.
- The rewritten query text is `query_rewritten` from the payload (truncate to ~120 chars with
  ellipsis if longer).
- When `rewrite_method === "none"`, the section is absent entirely — no empty label.

### GraderCard — decision badge

Replace the current "escalation possible" warning badge with a badge derived from `decision`:

| `decision` | Badge style | Text |
|---|---|---|
| `"proceed"` | green | "Proceed to generation" |
| `"retry"` | amber | "Retry retrieval" |
| `"escalate_web"` | blue | "Escalating to web search" |

Remove the `all_below_threshold` inline warning. The `decision` field encodes the same information
more precisely.

### CriticCard — verdict badge

Append a verdict badge to the right of the risk bar:

| `verdict` | Badge style | Text |
|---|---|---|
| `"accept"` | green | "Accepted" |
| `"rerun"` | amber | "Rerun" |

---

## Part 3 — Post-Hoc Mode (after `done`)

When `isStreaming` transitions to `false`, `AgentTrace` replaces the card stack with
`AgentFlowSummary`. This component renders a three-zone layout.

### Zone 1 — Query Transformation (conditional)

Shown only when `rewrite_method !== "none"` on the router step.

A before/after block with a clear technique label:

```
Original query
  "What causes transformer attention to scale quadratically?"

HyDE hypothesis  (used for retrieval)
  "Transformer attention scales quadratically because each token must
   compute similarity against all other tokens, producing an n×n matrix..."
```

For Step-Back, the label is "Step-back generalisation". This zone answers the question that is
completely invisible today: *the retriever searched for something different from what the user typed,
and here is what and why.*

### Zone 2 — Execution Path

The pipeline is rendered as horizontal node tiles connected by decision-annotated arrows.

#### No-retry case (single lane):

```
Router          Retriever        Grader           Generator        Critic
analytical      12 docs          7/12 passed      85% conf         8% risk
hybrid          hybrid           ≥0.5             7 docs           ✓ accept
43ms       →    156ms       →    310ms       →    890ms       →    201ms
```

Each node is a compact tile showing its key metric on the second line and duration on the third.
Connectors between tiles are plain arrows for "proceed" decisions.

#### CRAG retry case (two lanes):

```
Run 1
  Router(43ms) ──→ Retriever(156ms) ──→ Grader(310ms)
  analytical        12 docs             0/12 passed
  hybrid            hybrid              ↩ retry → web

Run 2
                   Retriever(200ms) ──→ Grader(180ms) ──→ Generator(890ms) ──→ Critic(201ms)
                    5 web docs           4/5 passed         85% conf             8% risk
                    web                  → proceed           7 docs               ✓ accept
```

Each run is a horizontal lane labelled "Run 1", "Run 2", etc. The retry connector (↩) between lanes
is annotated with the grader's `decision` value. Router appears only in Run 1's lane since it
executes once per query.

**Key rationale:** retries are parallel lanes, not appended cards. Appended cards imply the pipeline
ran N extra steps sequentially. Parallel lanes show it made N passes at the same retrieval stage.
The run-number badge on current cards hints at this — lanes make it explicit.

### Zone 3 — Latency Waterfall

The existing `LatencyBars` component, unchanged. Stays at the bottom of the post-hoc view.

---

## Component Architecture

```
AgentTrace (existing — becomes a mode router)
  isStreaming=true  → AgentTraceCards   (extracted from current AgentTrace body)
  isStreaming=false → AgentFlowSummary  (new)
       ├── QueryTransformation           (new, conditional on rewrite_method)
       ├── ExecutionPath                 (new)
       │    ├── RunLane                  (new — one per retry pass)
       │    │    └── NodeTile            (new — one per node in that lane)
       │    └── RetryConnector           (new — between lanes, shows decision label)
       └── LatencyBars                   (existing, extracted from AgentTrace)
```

### RunLane grouping logic

Steps are grouped into lanes by the `run` field on each `AgentStep`:

- All steps with `run === 1` belong to lane 1. Steps with `run === 2` belong to lane 2, etc.
- Within a lane, nodes are ordered by `PIPELINE_ORDER`.
- If only one lane exists, omit the "Run 1" label — no retry means no need to distinguish lanes.
- Router always belongs to lane 1 (it has `run === 1` and never reruns).

### NodeTile content by node type

| Node | Line 1 (metric) | Line 2 (detail) |
|---|---|---|
| router | `query_type` label | `strategy` + rewrite badge if applicable |
| retriever | `docs_retrieved` docs | `strategy` label |
| grader | `passed_count`/`scores_all.length` passed | decision badge |
| generator | `confidence`% confidence | `docs_used` docs |
| critic | `hallucination_risk`% risk | verdict badge |

---

## Scope Boundaries

This proposal explicitly excludes:

- **Graph layout library** (Dagre, D3, ReactFlow). The topology is fixed at five node types with
  at most two retry lanes. CSS flex handles this without introducing a layout engine dependency.
- **Animated path highlight during streaming.** The stagger delays on cards already communicate
  streaming progress. Competing animations would obscure content.
- **Per-document grader reasoning.** The `_GradeDoc.reasoning` string is discarded at the backend
  node level and is not in the SSE payload. Surfacing it requires a separate backend change.
- **Critic retry budget display.** Whether a "rerun" verdict was actually actioned depends on the
  retry budget, which the SSE stream does not expose. The `verdict` field reflects the critic's
  recommendation, not the graph's final routing decision.

---

## Work Estimate

| Item | Scope |
|---|---|
| Update frontend types | ~15 lines |
| Enrich RouterCard (rewrite section) | ~25 lines |
| Enrich GraderCard (decision badge) | ~15 lines |
| Enrich CriticCard (verdict badge) | ~10 lines |
| Extract `AgentTraceCards` from `AgentTrace` | ~10 lines refactor |
| `QueryTransformation` component | ~40 lines |
| `ExecutionPath` + `RunLane` + `NodeTile` + `RetryConnector` | ~150 lines |
| Wire `AgentTrace` mode switch | ~15 lines |
| Component tests | ~80 lines |

---

## Definition of Done

- [ ] `tsc --noEmit` passes with zero errors after type changes
- [ ] `eslint` passes with zero warnings
- [ ] Component tests cover: no-rewrite case, HyDE rewrite case, stepback rewrite case,
      single-lane path, two-lane CRAG retry path, grader decision badges (all three values),
      critic verdict badges (both values)
- [ ] Manually verified in browser: streaming cards animate in correctly; post-hoc trail renders
      after `done` for both no-retry and CRAG-retry scenarios
- [ ] No graph layout library dependency introduced
- [ ] Committed with a valid Conventional Commit message
