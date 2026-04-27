# Phase 2e — Architect Review Fixes

> Created: 2026-04-27 | Source: Architect review of Phase 2e Parallel-View Chat UI implementation
> Rule: development-process.md §9 — all Major and above fixes must clear before Phase 2f starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On | Assigned To |
|----|----------|--------|----------|---------|------------|-------------|
| F01 | Major | ✅ | DRY / Single-Definition | `isCriticPayload` and `isGraderPayload` duplicated verbatim in `AgentTrace.tsx` and `AgentVerdict.tsx` | — | frontend-developer |
| F02 | Minor | ⏳ | Visual Correctness | `isStreaming` passed to all `AgentTrace` instances; older completed traces show a spinner during new-message streaming | — | frontend-developer |
| F03 | Advisory | ⏳ | Type Hygiene | `AgentVerdictProps`, `VerdictWinner`, and `Verdict` are defined locally in `AgentVerdict.tsx`; `AgentVerdictProps` is not shared across components but shares the `AgentMessage` / `Message` domain; assess whether they belong in `src/types/index.ts` | — | frontend-developer |

---

## Detailed Fix Specifications

### F01 — Duplicate type-guard functions across components (Major)

**File:** `frontend/src/components/AgentTrace.tsx` and `frontend/src/components/AgentVerdict.tsx`

**Issue:** `isCriticPayload` and `isGraderPayload` are defined independently and identically in both files. The anti-patterns rule states: "Re-declare a shared type in `generation/`, `retrieval/`, or `ingestion/`" → "Import from the authoritative location." The same principle applies on the frontend: shared runtime logic must not be defined twice. If the `AgentStep["payload"]` discriminant field names change (e.g., `hallucination_risk` renamed), the fix must be applied in two places and a missed update causes a silent runtime bug.

**Fix:** Extract both type guards into `src/lib/agentTypeGuards.ts` (or `src/lib/typeGuards.ts` if other guards exist). Import them in both `AgentTrace.tsx` and `AgentVerdict.tsx`. The extracted module must be covered by at least one unit test verifying the discriminant field check for each guard.

```typescript
// src/lib/agentTypeGuards.ts
import type { AgentStep, CriticStepPayload, GraderStepPayload, RouterStepPayload } from "@/types";

export function isRouterPayload(payload: AgentStep["payload"]): payload is RouterStepPayload {
  return "query_type" in payload;
}

export function isGraderPayload(payload: AgentStep["payload"]): payload is GraderStepPayload {
  return "web_fallback" in payload;
}

export function isCriticPayload(payload: AgentStep["payload"]): payload is CriticStepPayload {
  return "hallucination_risk" in payload;
}
```

Note: `isRouterPayload` is currently defined only in `AgentTrace.tsx`. Move it to the same shared module for consistency, even though it is not yet duplicated.

**Rule:** anti-patterns.md — "Re-declare a shared type … → Import from the authoritative location." architecture-rules.md — Schema Ownership / Single Definition Rule (applied to runtime utilities, not only Pydantic models).

**DoD verification:**
```
grep -r "isGraderPayload\|isCriticPayload" frontend/src/components/
# must show only import statements, not function definitions

poetry run pytest   # (no backend impact — confirm no accidental file changes)
cd frontend && npm run test -- --testPathPattern=agentTypeGuards
cd frontend && npm run lint
cd frontend && npm run build
```

---

### F02 — isStreaming passed to completed AgentTrace instances (Minor)

**File:** `frontend/src/components/AgentPanel.tsx`

**Issue:** `AgentPanel` renders `<AgentTrace steps={message.agentSteps} isStreaming={isStreaming} />` for every message in the `messages` array, where `isStreaming` is the panel-level prop. When a new message is being streamed, all previously completed messages receive `isStreaming=true`. This causes:
1. The last step card of every historical message shows the spinning indicator while the new message streams.
2. `LatencyBars` is suppressed (`!isStreaming` guard) for all historical messages until the new message finishes.

The visual contract is that `isStreaming` on an `AgentTrace` communicates "this particular trace is still accumulating steps." Passing the panel-level flag violates that contract for completed messages.

**Fix:** Pass `isStreaming` as `true` only for the last message in the array while streaming; pass `false` for all earlier messages regardless of panel state.

```typescript
// AgentPanel.tsx
{messages.map((message, index) => {
  const isLastMessage = index === messages.length - 1;
  return (
    <div key={message.id}>
      <ChatMessage message={message} />
      {message.role === "assistant" &&
        message.agentSteps &&
        message.agentSteps.length > 0 && (
          <AgentTrace
            steps={message.agentSteps}
            isStreaming={isStreaming && isLastMessage}
          />
        )}
    </div>
  );
})}
```

**Rule:** frontend-rules.md — components must render correct visual state. Architecture constraint from tasks.md: right panel is `AgentPanel` + `useAgentStream` only — no logic change to `AgentTrace` itself is needed.

**DoD verification:**
```
cd frontend && npm run test -- --testPathPattern=AgentPanel
cd frontend && npm run lint
cd frontend && npm run build
```

---

### F03 — Local interface definitions in AgentVerdict.tsx (Advisory)

**File:** `frontend/src/components/AgentVerdict.tsx`

**Issue:** `AgentVerdictProps`, `VerdictWinner` (type alias), and `Verdict` (interface) are defined locally. `frontend-rules.md` states: "No inline type definitions in components or hooks" and "All API response types are defined in `src/types/index.ts`." Strictly interpreted, `VerdictWinner` and `Verdict` are component-internal computation types, not API response types. However, `AgentVerdictProps` is a component interface that crosses the component boundary (it is passed from `page.tsx`). If a second component ever references verdict state, these types will need to move anyway.

**Assessment:** This is Advisory. Component-private interfaces (`Verdict`, `VerdictWinner`) that are not exported and not shared across components are categorically different from API response types. Moving them to `src/types/index.ts` would over-expose internal computation details. The recommended action is to export `AgentVerdictProps` to `src/types/index.ts` (since it is already consumed by `page.tsx` via prop passing) and leave `Verdict` and `VerdictWinner` local.

**Fix (optional — clear before Phase 3):**
1. Move `AgentVerdictProps` to `src/types/index.ts` and import it in `AgentVerdict.tsx`.
2. Leave `Verdict` and `VerdictWinner` local — they are implementation details of `computeVerdict`.

**Rule:** frontend-rules.md — "All API response types are defined in `src/types/index.ts`." (Advisory — not blocking Phase 2f.)

**DoD verification:**
```
cd frontend && npx tsc --noEmit
cd frontend && npm run lint
```

---

## Clearance Order

**Batch 1 — Parallel (no dependencies between F01 and F02):**
- F01: Extract type guards to `src/lib/agentTypeGuards.ts`
- F02: Fix `isStreaming` scoping in `AgentPanel`

**Batch 2 — After Batch 1 clears:**
- F03 (Advisory): Relocate `AgentVerdictProps` to `src/types/index.ts`

F01 and F02 must be cleared before Phase 2f begins. F03 may be deferred to the Phase 2f implementation window or addressed alongside the evaluation UI work.

---

## Verification Checklist

- [x] F01: `isGraderPayload` and `isCriticPayload` definitions removed from `AgentTrace.tsx` and `AgentVerdict.tsx`
- [x] F01: Both guards imported from `src/lib/agentTypeGuards.ts` in both components
- [x] F01: `isRouterPayload` also moved to `src/lib/agentTypeGuards.ts` (no duplication risk, but consistent extraction)
- [x] F01: Unit test for `agentTypeGuards.ts` — 9 test cases (3 per guard: positive + 2 negative)
- [x] F01: `npm run lint` — zero warnings
- [x] F01: `npm run build` — succeeds
- [ ] F02: `AgentPanel` passes `isStreaming && isLastMessage` to each `AgentTrace`
- [ ] F02: `npm run test -- --testPathPattern=AgentPanel` — passes
- [ ] F02: `npm run build` — succeeds
- [ ] F03 (Advisory): `AgentVerdictProps` moved to `src/types/index.ts`
- [ ] F03 (Advisory): `npx tsc --noEmit` — zero errors
