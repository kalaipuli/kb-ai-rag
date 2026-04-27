# Phase 2a — Architect Review Fixes

> Created: 2026-04-27 | Source: Architect review of Phase 2a Gate Zero implementation
> Rule: development-process.md §9 — all High findings must clear before Phase 2b starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On |
|----|----------|--------|----------|---------|------------|
| F01 | High | ⏳ Pending | Docs | ADR-004 §6 wire format uses `"event"` discriminant + top-level `duration_ms` + raw `"delta"` — conflicts with TypeScript `AgentStepEvent` which uses `"type"`, structured `"payload"`, and `duration_ms` inside payload. One artifact must be corrected before Phase 2b writes any streaming code. | — |
| F02 | High | ⏳ Pending | Architecture | `AgentState` 19-field implementation diverges from the canonical schema in `architecture-rules.md` with no covering ADR: 3 fields renamed/absent (`hallucination_risk`, `fallback_triggered`, `user_id`), 5 new fields added (`filters`, `k`, `grader_scores`, `all_below_threshold`, `retry_count`). Two sources of truth exist. | — |
| F03 | Major | ⏳ Pending | Docs | `architecture-rules.md` SSE rule still reads "Three event types only: token, citations, done" — `agent_step` not mentioned. A Phase 2b reviewer running the checklist will flag `agent_step` as a rule violation. | F01 |
| F04 | Major | ⏳ Pending | Types | `AgentStepNode` union is `"router" \| "grader" \| "critic"` — omits `"retriever"` and `"generator"`. Events from those nodes will fail TypeScript discriminated union narrowing. | F01 |
| F05 | Minor | ⏳ Pending | Correctness | `from __future__ import annotations` in `state.py` defers annotation evaluation. LangGraph resolves reducers via `get_type_hints(include_extras=True)` at compile time — currently safe, but latent `NameError` risk if any import is removed. Remove from `state.py`. | — |
| F06 | Advisory | ⏳ Pending | Docs | `confidence: float \| None` in `state.py` diverges from canonical `confidence: float` in `architecture-rules.md` without documentation. Resolve as part of F02 schema reconciliation. | F02 |

---

## Detailed Fix Specifications

### F01 — ADR-004 wire format conflicts with TypeScript AgentStepEvent (High)

**Files:** `docs/adr/004-langgraph-vs-chain.md` (Amendment §6) vs `frontend/src/types/index.ts:64`
**Issue:** The ADR-004 Amendment §6 documents the `agent_step` SSE payload as:
```json
{ "event": "agent_step", "node": "<node_name>", "delta": state_delta, "duration_ms": duration_ms }
```
The TypeScript `AgentStepEvent` interface defines:
```typescript
{ type: "agent_step"; node: AgentStepNode; payload: RouterStepPayload | GraderStepPayload | CriticStepPayload; }
```
Three concrete conflicts: (1) discriminant key is `"event"` in the ADR vs `"type"` in TypeScript — the frontend union narrows on `type`, so an event carrying only `"event"` will never narrow; (2) raw `"delta": state_delta` in ADR vs structured typed `"payload"` object in TypeScript; (3) `duration_ms` at top level in ADR vs inside each payload struct in TypeScript.

**Fix:** Amend ADR-004 §6 to match the TypeScript definition, which is the more precise contract:
```json
{ "type": "agent_step", "node": "<node_name>", "payload": { "<node-specific fields>", "duration_ms": <int> } }
```
Do not change the TypeScript interface — it was purpose-built for discriminated union narrowing.
**Rule:** architecture-rules.md — Schema Ownership, Single Definition Rule; ADR is the written contract Phase 2b implementers will use to build the streaming endpoint.

---

### F02 — AgentState diverges from canonical schema in architecture-rules.md (High)

**File:** `backend/src/graph/state.py` vs `.claude/docs/architecture-rules.md` (AgentState section)
**Issue:** The `architecture-rules.md` canonical AgentState schema includes fields absent from the implementation (`hallucination_risk: float`, `fallback_triggered: bool`, `user_id: str`) and the implementation adds 5 fields not in the spec (`filters`, `k`, `grader_scores`, `all_below_threshold`, `retry_count`). The `architecture-rules.md` states AgentState changes require Architect approval, but no ADR covers the divergence. The `user_id` omission is the most consequential gap — multi-tenant audit trails depend on it.

**Fix:** Update `architecture-rules.md` to reflect the implemented 19-field schema as the new canonical spec, documenting for each change: (a) `critic_score: float | None` replaces `hallucination_risk: float` — rename to align with the Critic node's output semantics; (b) `web_fallback_used: bool` replaces `fallback_triggered: bool` — more descriptive for the Tavily CRAG pattern; (c) `user_id` deferred to Phase 4 multi-tenant work — stateless for Phase 2; (d) 5 new fields added for CRAG control flow. Update the status note with date 2026-04-27.
**Rule:** architecture-rules.md — "AgentState is the Single Source of Truth. Do not modify this schema without a corresponding ADR."

---

### F03 — architecture-rules.md SSE contract not updated to include agent_step (Major)

**File:** `.claude/docs/architecture-rules.md` (SSE Streaming section)
**Issue:** The rule reads: "Three event types only: `token`, `citations`, `done`." Phase 2 introduces `agent_step` as a fourth SSE event type, documented in ADR-004 §6. A Phase 2b implementer reading this rule will believe `agent_step` is prohibited; a reviewer running the checklist will flag it as a violation.

**Fix:** Update the SSE section to read: "Static pipeline (`POST /api/v1/query`): `token`, `citations`, `done`. Agentic pipeline (`POST /api/v1/query/agentic`): additionally `agent_step` — see ADR-004 §6 for payload contract." Do not merge the two endpoint contracts; keep them clearly separated.
**Rule:** architecture-rules.md is the document Phase 2b implementers read first — stale rules cause violations by implementers following them in good faith.

---

### F04 — AgentStepNode union omits retriever and generator nodes (Major)

**File:** `frontend/src/types/index.ts:60`
**Issue:** `AgentStepNode = "router" | "grader" | "critic"`. The LangGraph graph has five nodes (router, retriever, grader, generator, critic). The `steps_taken` reducer tests accumulate `["router", "retriever", "grader", "generator"]` — confirming four node names are in active use. If `retriever` or `generator` emit `agent_step` SSE events, the TypeScript type will not cover them and discriminated union narrowing will fail for those events.

**Fix:** If retriever and generator intentionally emit `agent_step` events: extend `AgentStepNode` to `"router" | "retriever" | "grader" | "generator" | "critic"` and add `RetrieverStepPayload` and `GeneratorStepPayload` interfaces. If they do not emit `agent_step` events (they only update `steps_taken` silently): document this constraint explicitly in ADR-004 — "retriever and generator nodes do not emit agent_step SSE events."
**Rule:** No rule — architectural judgment. Resolve as part of F01 ADR-004 update to avoid a third round-trip.

---

### F05 — from __future__ import annotations in state.py (Minor)

**File:** `backend/src/graph/state.py:7`
**Issue:** PEP 563 defers all annotation evaluation, storing them as strings. LangGraph resolves `Annotated` reducers at `StateGraph` compile time via `get_type_hints(AgentState, include_extras=True)`. All referenced names are currently imported at module scope so resolution succeeds — but any future import removal will raise `NameError` at graph compile time rather than at import time, making the error harder to diagnose. The `from __future__ import annotations` serves no purpose in a schema definition file.

**Fix:** Remove `from __future__ import annotations` from `state.py`. Keep it in `test_state.py` where it has no runtime impact.
**Rule:** python-rules.md — types correctness; prefer explicit over implicit.

---

### F06 — confidence field type undocumented divergence (Advisory)

**File:** `backend/src/graph/state.py:64`
**Issue:** Canonical schema declares `confidence: float`; implementation declares `confidence: float | None`. Downstream nodes that read `confidence` must handle `None` whereas the canonical spec allows assuming a float is always present. The divergence is intentional (confidence is `None` until the Generator node populates it) but undocumented.

**Fix:** Resolve as part of F02 — update the canonical schema in `architecture-rules.md` to `confidence: float | None` and note the field lifecycle (populated by Generator node; `None` for all prior nodes).
**Rule:** No rule — architectural judgment.

---

## Clearance Order

High findings must clear before Phase 2b implementation begins.

```
Batch 1 — Docs/contract alignment (parallel, no code changes):
  F01  (amend ADR-004 §6 wire format)
  F02  (update architecture-rules.md canonical AgentState schema)

Batch 2 — Depends on Batch 1:
  F03  (update SSE rule in architecture-rules.md — do after F01 confirms agent_step shape)
  F04  (extend AgentStepNode — do after F01 resolves whether retriever/generator emit events)
  F06  (update confidence type in canonical schema — do as part of F02)

Batch 3 — Code fix (independent):
  F05  (remove from __future__ import annotations from state.py)
```

---

## Verification Checklist

_Complete after all fixes are applied:_

- [ ] ADR-004 §6 payload structure matches `AgentStepEvent` TypeScript interface
- [ ] `architecture-rules.md` AgentState canonical schema matches `state.py` (19 fields)
- [ ] `architecture-rules.md` SSE rule mentions `agent_step` for the agentic endpoint
- [ ] `AgentStepNode` covers all nodes that emit `agent_step` events (or ADR-004 documents which do not)
- [ ] `from __future__ import annotations` removed from `state.py`
- [ ] `ruff check backend/src/ backend/tests/` — zero warnings
- [ ] `mypy backend/src/ --strict` — zero errors
- [ ] `pytest backend/tests/unit/ -q` — all green (no regressions)
- [ ] `tsc --noEmit` — zero errors
