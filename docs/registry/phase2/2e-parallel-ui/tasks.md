# Phase 2e — Parallel-View Chat UI

> Status: ✅ Complete | Phase: 2e | Estimated Days: 2–3
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-27
>
> **Prerequisite:** Phase 2d gate must pass before any task here starts.
> **Goal:** Side-by-side comparison UI — left panel (Static Chain, Phase 1) versus right panel (Agentic Pipeline, Phase 2). Both submit the same query simultaneously. Shared input is functionally blocked while either stream is active.

---

## Context

The parallel-view UI is the primary portfolio demonstration surface. It demonstrates:
- The same query processed by two architectures side by side
- Latency difference visible in real time (static typically finishes first for simple queries; agentic adds reasoning value for complex ones)
- Agentic trace transparency: Router decision, Grader scores, Critic hallucination risk — each with per-node latency
- A post-completion "Why Agentic Won/Lost" verdict

**Architectural constraints (established in architect review):**

| Constraint | Rule |
|-----------|------|
| Left panel components | Unchanged — `useStream`, `ChatMessage`, `CitationList`, `ConfidenceBadge` are not modified |
| Right panel | New `AgentPanel` + new `useAgentStream` hook only |
| `SharedInput` blocking | `onSubmit` must be a no-op inside the handler when either stream is active — not just a visual `disabled` attribute on the input element |
| Session ID storage | `sessionStorage` (not `localStorage`) — scoped to browser tab lifetime |
| Router labels | Human-readable strings in DOM — raw enum values (`"factual"`, `"multi_hop"`) must not appear in rendered text |
| Comparison view controls | No free-text `filters` or `k` input fields in the parallel comparison view |
| Panel labels | "Static Chain" (left) and "Agentic Pipeline" (right) — not "Search" vs "AI" |

**`SharedInput` correctness rationale:** `SqliteSaver` is a single-writer store. Two concurrent `astream()` calls sharing the same `thread_id` corrupt the checkpoint. Even though the route handler creates a new session UUID when `X-Session-ID` is absent, the browser can reuse a session ID across rapid submits. The handler guard must be functional (inside the submit callback), not merely presentational, to prevent this race.

---

## Component Hierarchy

The component tree introduced in this phase:

    chat/page.tsx
    ├── SharedInput                  — single query input for both panels; fires both hooks
    ├── AgentVerdict                 — post-completion comparison verdict; shown after both streams end
    ├── [left column]
    │   └── existing Phase 1 components (unchanged)
    └── [right column]
        └── AgentPanel
            ├── ChatMessage          — reused from Phase 1, unchanged
            ├── CitationList         — reused from Phase 1, unchanged
            ├── ConfidenceBadge      — reused from Phase 1, unchanged
            └── AgentTrace
                ├── Router step card
                ├── Grader step card
                ├── Critic step card
                └── Latency bar chart (shown after streaming ends)

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Implement `useAgentStream` hook | frontend-developer | 2d all |
| T02 | ✅ Done | Implement `AgentTrace` component (per-node step cards) | frontend-developer | T01 |
| T03 | ✅ Done | Implement `AgentPanel` component | frontend-developer | T01, T02 |
| T04 | ✅ Done | Implement `SharedInput` component with functional streaming guard | frontend-developer | T01 |
| T05 | ✅ Done | Refactor `chat/page.tsx` to `grid grid-cols-2` with `StaticPanel` + `AgentPanel` | frontend-developer | T01–T04 |
| T06 | ✅ Done | Implement `AgentVerdict` component | frontend-developer | T05 |
| T07 | ✅ Done | Add per-node latency bar chart to `AgentTrace` | frontend-developer | T02, T06 |
| T08 | ✅ Done | Component tests for all new UI components | frontend-developer | T01–T07 |

---

## Ordered Execution Plan

### Batch 1 — No dependencies (after 2d gate)
- **T01** — `useAgentStream` hook (defines the data contract all components consume)

### Batch 2 — After T01
- **T02** — `AgentTrace` (reads `AgentStep[]` from hook state)
- **T04** — `SharedInput` (calls both submit functions)

### Batch 3 — After T01, T02
- **T03** — `AgentPanel` (composes `AgentTrace` + existing chat components)

### Batch 4 — After T01–T04
- **T05** — Page layout refactor

### Batch 5 — After T05
- **T06** — `AgentVerdict` component
- **T07** — Latency bars in `AgentTrace`

### Batch 6 — After T01–T07
- **T08** — All component tests

---

## Definition of Done Per Task

### T01 — `useAgentStream` hook

**File:** `frontend/src/hooks/useAgentStream.ts` (new file — do not modify `useStream.ts`)

**What:** A React hook that opens an SSE connection to `POST /api/proxy/query/agentic`, manages session persistence, and distributes incoming events into typed state. It is the single source of truth for the right panel.

**State shape managed by the hook:**

| Field | Type | Purpose |
|-------|------|---------|
| `messages` | `AgentMessage[]` | Message thread including agentic step trace data |
| `isStreaming` | `boolean` | `true` from submit until `done` event or error |
| `error` | `Error \| null` | Last stream error, if any |
| `sessionId` | `string` | Persisted session identifier (see lifecycle below) |

`AgentMessage` extends the base `Message` type from Phase 1 with one additional optional field: `agentSteps?: AgentStep[]`. This field is populated as `agent_step` SSE events arrive. `AgentMessage` must not break existing `Message` consumers — it only adds an optional field.

**Session ID lifecycle:**
- On hook initialisation: read from `sessionStorage` under the key `"kb_rag_session_id"`
- If absent: generate a new `crypto.randomUUID()` value and write it to `sessionStorage`
- Pass the session ID as the `X-Session-ID` HTTP header on every `POST /api/proxy/query/agentic` request

**SSE event handling:**

| Event type | Handler action |
|------------|---------------|
| `agent_step` | Append the step to `agentSteps` on the current in-progress `AgentMessage` |
| `token` | Append `content` to the current `AgentMessage.content` |
| `citations` | Set `citations` and `confidence` on the current `AgentMessage` |
| `done` | Set `isStreaming = false` |

**Correctness constraint:** The `submit` function must check `isStreaming` inside its own body and return early without opening a new connection when `isStreaming === true`. This is a functional guard, not a hint to the UI layer.

**Acceptance criteria:**
- [ ] `useAgentStream.ts` implemented
- [ ] `sessionId` initialised from `sessionStorage`; new UUID written to `sessionStorage` when absent
- [ ] All 4 event types handled correctly
- [ ] `isStreaming` set to `true` on submit; set to `false` on `done` or error
- [ ] `submit` is a no-op when `isStreaming === true`
- [ ] tsc --noEmit — zero errors
- [ ] eslint — zero warnings
- [ ] `useStream.ts` unchanged

**Conventional commit:** `feat(ui): add useAgentStream hook with session persistence and agent_step handling`

---

### T02 — `AgentTrace` component

**File:** `frontend/src/components/AgentTrace.tsx` (new file)

**What:** Renders a collapsible trace panel containing one step card per completed agent node. Receives the `AgentStep[]` array from `useAgentStream` state and `isStreaming` to control spinner and latency bar visibility.

**Props contract:**

| Prop | Type | Purpose |
|------|------|---------|
| `steps` | `AgentStep[]` | Array of completed node steps |
| `isStreaming` | `boolean` | Shows spinner on last card when `true`; shows latency bars when `false` |

**Router step card content:**

| Element | Value mapping |
|---------|--------------|
| Query type label | `"factual"` → `"Direct fact lookup"`, `"analytical"` → `"Analytical reasoning"`, `"multi_hop"` → `"Multi-step reasoning"`, `"ambiguous"` → `"Needs clarification"` |
| Strategy badge | `"hybrid"` → `"Hybrid search"`, `"dense"` → `"Dense search"`, `"web"` → `"Web search"` |
| Latency | `{duration_ms}ms` |

Raw enum values (`"factual"`, `"multi_hop"`, `"dense"`, etc.) must never appear as visible text in the rendered DOM. This is enforced by Gate G05.

**Grader step card content:** Per-chunk score bars (visual style reused from existing `CitationList` score bars); web fallback badge shown only when `web_fallback === true`; latency `{duration_ms}ms`.

**Critic step card content:** Hallucination risk gauge (a single horizontal bar, colour-coded by threshold); reruns count shown when `reruns > 0`; latency `{duration_ms}ms`.

Critic gauge colour mapping:

| `hallucination_risk` range | CSS class |
|---------------------------|-----------|
| `< 0.4` | `bg-green-500` |
| `0.4` to `0.7` inclusive | `bg-amber-500` |
| `> 0.7` | `bg-red-500` |

**Wrapper element:** The entire trace is wrapped in a `<details>` element with `<summary>Agent Trace ({steps.length} steps)</summary>`. Default state: open.

**Latency bar chart:** Rendered below the step cards, only when `isStreaming === false`. Three horizontal bars (Router, Grader, Critic) with widths proportional to `duration_ms / total_duration`. Total duration displayed below the bars. This avoids visual jank during active streaming.

**Acceptance criteria:**
- [ ] All three node card types rendered with correct content
- [ ] Router labels are human-readable (no raw enum strings in DOM)
- [ ] Critic gauge uses the correct colour class per threshold range
- [ ] `<details>` wrapper with `<summary>` present in DOM
- [ ] Latency bars not rendered while `isStreaming === true`
- [ ] tsc --noEmit — zero errors
- [ ] eslint — zero warnings

**Conventional commit:** `feat(ui): add AgentTrace component with per-node step cards`

---

### T03 — `AgentPanel` component

**File:** `frontend/src/components/AgentPanel.tsx` (new file)

**What:** The right-panel container. Composes existing Phase 1 chat components with the new `AgentTrace`. Contains no new chat rendering logic — all message display is delegated to existing components.

**Props contract:**

| Prop | Type | Purpose |
|------|------|---------|
| `messages` | `AgentMessage[]` | Message thread from `useAgentStream` |
| `isStreaming` | `boolean` | Passed to `AgentTrace` |
| `error` | `Error \| null` | Displayed as an error banner when non-null |

**Composition rule:** `AgentPanel` renders a `ChatMessage` for each message, and immediately below each assistant `AgentMessage`, renders an `AgentTrace` when `agentSteps` is non-empty. `CitationList` and `ConfidenceBadge` are reused unchanged. No rendering logic from Phase 1 components is copied into this file.

**Acceptance criteria:**
- [ ] Composes existing `ChatMessage`, `CitationList`, `ConfidenceBadge` — no copy-pasted rendering logic
- [ ] `AgentTrace` rendered below each assistant message when `agentSteps` is non-empty
- [ ] tsc --noEmit — zero errors

**Conventional commit:** `feat(ui): add AgentPanel component composing existing chat components with AgentTrace`

---

### T04 — `SharedInput` component

**File:** `frontend/src/components/SharedInput.tsx` (new file)

**What:** A single query input form that fires both the static and agentic submit functions. The input is functionally blocked — not merely visually disabled — while either stream is active.

**Props contract:**

| Prop | Type | Purpose |
|------|------|---------|
| `onSubmit` | `(query: string) => void` | Called once with the trimmed query; fires both hook submits at the page level |
| `isDisabled` | `boolean` | `true` while either stream is active |

**Functional blocking constraint:** The submit handler must check `isDisabled` and return early before calling `onSubmit`, even if the HTML `disabled` attribute is absent from the DOM. The guard is a conditional inside the handler body. This is required because a JavaScript test (or a browser extension) can remove the `disabled` attribute from the DOM without triggering a React re-render. The functional guard cannot be bypassed this way.

**Visual feedback when `isDisabled === true`:** Display a loading indicator and the label "Both pipelines processing..." adjacent to the input.

**Input clearing:** The input field value clears to an empty string immediately after `onSubmit` is called, before the stream begins.

**Acceptance criteria:**
- [ ] `onSubmit` is a no-op when `isDisabled === true` (functional guard inside handler body)
- [ ] Input value clears after submit
- [ ] "Both pipelines processing..." label shown when `isDisabled === true`
- [ ] tsc --noEmit — zero errors

**Conventional commit:** `feat(ui): add SharedInput component with functional streaming guard`

---

### T05 — `chat/page.tsx` parallel layout refactor

**File:** `frontend/src/app/chat/page.tsx` (minimal modification — two-column layout only)

**What:** Lift both hook states to the page level and add a `grid grid-cols-2` wrapper around the two panels. The left panel uses existing components unchanged. The right panel uses `AgentPanel`.

**State lifted to page level:**

| Variable | Source hook | Purpose |
|----------|------------|---------|
| `submit` (static) | `useStream()` | Fires Phase 1 retrieval |
| `messages` (static) | `useStream()` | Left panel messages |
| `isStreaming` (static) | `useStream()` | Left panel streaming flag |
| `submit` (agentic) | `useAgentStream()` | Fires Phase 2 graph |
| `messages` (agentic) | `useAgentStream()` | Right panel messages |
| `isStreaming` (agentic) | `useAgentStream()` | Right panel streaming flag |
| `sessionId` | `useAgentStream()` | Available for debugging; not rendered directly |

`isEitherStreaming = staticStreaming || agentStreaming` — passed to `SharedInput.isDisabled` and used to gate `AgentVerdict` rendering.

`handleSubmit(query: string)` at the page level calls both static and agentic submit functions with the same query string.

**Layout structure (prose description):**
- Outer wrapper: full-height flex column
- `SharedInput` at the top, receiving `onSubmit={handleSubmit}` and `isDisabled={isEitherStreaming}`
- `AgentVerdict` below `SharedInput`, rendered only when `isEitherStreaming === false` and both panels have at least one assistant message
- A `grid grid-cols-2 gap-4 flex-1 overflow-hidden` container below
- Left column: `border-r` divider, `"Static Chain"` heading, existing Phase 1 chat components
- Right column: `AgentPanel` receiving agentic messages, streaming flag, and error

Responsive breakpoint: `md:grid-cols-2 grid-cols-1` to prevent layout breakage on narrow viewports.

**Acceptance criteria:**
- [ ] `grid grid-cols-2` layout with both panels visible on desktop
- [ ] Both `submitStatic` and `submitAgentic` called from a single `handleSubmit`
- [ ] `isEitherStreaming` (not individual flags) passed to `SharedInput`
- [ ] Left panel uses existing components unchanged
- [ ] tsc --noEmit — zero errors
- [ ] npm run build — succeeds

**Conventional commit:** `feat(ui): refactor chat page to parallel two-panel layout`

---

### T06 — `AgentVerdict` component

**File:** `frontend/src/components/AgentVerdict.tsx` (new file)

**What:** A post-completion summary rendered after both streams have ended. Computes a verdict client-side from the last assistant messages of each pipeline. No API call is made.

**Rendering condition:** Render only when `isEitherStreaming === false` AND both pipelines have produced at least one assistant message.

**Verdict computation inputs:**

| Input | Source |
|-------|--------|
| `staticConf` | `confidence` from the last static pipeline assistant message |
| `criticRisk` | `hallucination_risk` from the critic `AgentStep` on the last agentic assistant message |
| `webFallback` | `web_fallback` from the grader `AgentStep` on the last agentic assistant message |
| `agentConf` | `confidence` from the last agentic assistant message |

**Verdict outcomes:**

| Condition (evaluated in order) | Winner | Reason text |
|-------------------------------|--------|-------------|
| `criticRisk > 0.7` | `"static"` | "Agentic pipeline flagged high hallucination risk" |
| `webFallback === true` | `"agentic"` | "Agentic pipeline used web search for missing knowledge" |
| `agentConf > staticConf + 0.1` | `"agentic"` | "Higher confidence answer via agentic reasoning" |
| Otherwise | `"tie"` | "Both pipelines produced comparable answers" |

**Display:** Winner badge (green for `"agentic"`, blue for `"static"`, grey for `"tie"`); one-sentence reason string below the badge. Rendered below `SharedInput`, above the two panels, or as a top banner — position is implementation-specific.

**Acceptance criteria:**
- [ ] Verdict rendered only after both streams complete
- [ ] All three outcomes (`static`, `agentic`, `tie`) handled with correct badge colours
- [ ] tsc --noEmit — zero errors

**Conventional commit:** `feat(ui): add AgentVerdict component for post-completion pipeline comparison`

---

### T07 — Per-node latency bar chart in `AgentTrace`

**Target file:** `frontend/src/components/AgentTrace.tsx` (extend T02 implementation)

**What:** After `isStreaming` transitions to `false`, render a horizontal proportional bar chart below the step cards showing `duration_ms` per node relative to the total pipeline duration.

**Bar chart design:**
- Three rows: Router, Grader, Critic
- Each bar width = `(node_duration_ms / total_duration_ms) * 100%`
- Label to the right of each bar: `{duration_ms}ms`
- Total duration row below the three bars
- Bars hidden while `isStreaming === true` (prevents jank during live streaming)

**Acceptance criteria:**
- [ ] Latency bars not rendered while `isStreaming === true`
- [ ] All three nodes shown with proportional bar widths
- [ ] Total duration displayed
- [ ] tsc --noEmit — zero errors

**Conventional commit:** `feat(ui): add per-node latency visualization to AgentTrace`

---

### T08 — Component tests

**Files:**
- `frontend/src/__tests__/useAgentStream.test.ts`
- `frontend/src/__tests__/AgentTrace.test.tsx`
- `frontend/src/__tests__/SharedInput.test.tsx`
- `frontend/src/__tests__/AgentVerdict.test.tsx`

**`useAgentStream` required test cases:**
1. `agent_step` event appends to current message's `agentSteps` array
2. `token` event appends to current message content
3. `done` event sets `isStreaming = false`
4. `submit` is a no-op when `isStreaming === true`
5. `sessionId` written to `sessionStorage` on first call and reread on subsequent renders

**`AgentTrace` required test cases:**
1. Router card renders human-readable label (e.g., `"Direct fact lookup"`, not `"factual"`)
2. Critic card renders correct CSS colour class for low risk, medium risk, and high risk
3. `<details>` element is present in the DOM
4. Latency bars are absent in the DOM while `isStreaming === true`

**`SharedInput` required test cases:**
1. `onSubmit` is not called when `isDisabled === true` (simulate form submit while disabled)
2. `onSubmit` is called with the trimmed query string when `isDisabled === false`
3. Input field value is cleared after a successful submit

**`AgentVerdict` required test cases:**
1. Component not rendered while either stream is still active
2. `"agentic"` verdict rendered when `webFallback === true`
3. `"static"` verdict rendered when `criticRisk > 0.7`
4. `"tie"` verdict rendered when confidence difference is negligible

**Acceptance criteria:**
- [ ] All 4 test files created with ≥ 3 tests each (≥ 16 total new frontend tests)
- [ ] npm run test — all green (no regressions in existing frontend tests)
- [ ] tsc --noEmit — zero errors
- [ ] eslint — zero warnings
- [ ] npm run build — succeeds

**Conventional commit:** `test(ui): add component tests for parallel-view chat UI`

---

## Phase 2e Gate Criteria

All of the following must be true before Phase 2f (Evaluation) begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | Parallel layout | Both panels visible in `grid grid-cols-2` |
| G02 | Static panel | Existing components unchanged; `useStream` still used |
| G03 | `SharedInput` guard | `onSubmit` is no-op (functional guard, not just UI disabled) while streaming |
| G04 | `sessionId` | Stored in `sessionStorage`, not `localStorage` |
| G05 | Router labels | Human-readable strings in DOM (no raw `"factual"`, `"multi_hop"`) |
| G06 | Latency bars | Hidden while streaming; shown with proportional widths after done |
| G07 | Verdict | Renders only after both streams complete |
| G08 | tsc --noEmit | Zero errors |
| G09 | eslint | Zero warnings |
| G10 | npm run build | Succeeds |
| G11 | All frontend tests | ≥ 70 passing (existing + ≥ 16 new) |
| G12 | Manual demo | Both panels show correct output for a factual query end-to-end |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `grid grid-cols-2` breaks mobile layout | Medium | Low | Add `md:grid-cols-2 grid-cols-1` responsive breakpoint (already in T05 spec) |
| `sessionStorage` cleared on tab close breaks conversation continuity | Low | Low | Document as known limitation: "Session resets on tab close" |
| Both SSE streams competing for browser connection pool | Low | Medium | Proxy routes go through Next.js server — browser makes 2 connections to Next.js, not backend directly |
| `AgentVerdict` verdict logic incorrect for edge cases | Low | Low | All 3 verdict outcomes covered in T08 component tests |
| Latency bar jank if `isStreaming` check applied inconsistently | Low | Low | Single `isStreaming` prop controls both step card spinner and bar visibility |
