# Phase 2d — Agentic API Endpoint

> Status: ✅ Complete | Phase: 2d | Estimated Days: 1–2
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-27
>
> **Prerequisite:** Phase 2c gate must pass before any task here starts.
> **Goal:** Expose the compiled graph via `POST /api/v1/query/agentic` with SSE streaming. The Phase 1 `POST /api/v1/query` endpoint is frozen — no modifications permitted.

---

## Context

**Architectural constraints governing this endpoint (established in architect review):**

- **Separate route file** — `backend/src/api/routes/query_agentic.py` is a new file; `query.py` is not touched
- **Frozen Phase 1 endpoint** — `POST /api/v1/query` must not be modified in this phase or any subsequent phase without an explicit version bump to `/api/v2/`; git diff on `query.py` must show zero modifications at the Phase 2d gate
- **`X-Session-ID` header** — read from HTTP request headers, not the request body; passed as `config={"configurable": {"thread_id": session_id}}` to `compiled_graph.astream()`; if absent, the route handler generates a UUID for the duration of the request
- **`duration_ms` in every `agent_step` payload** — this is a day-one wire format commitment documented in ADR-004 amendment; adding `duration_ms` after the fact requires a wire format version bump
- **No client instantiation in route handlers** — route handlers access the graph exclusively via `CompiledGraphDep`; `AzureChatOpenAI`, `AsyncQdrantClient`, and `AzureOpenAIEmbeddings` must not be instantiated in any file under `backend/src/api/routes/`
- **Dependency direction** — route handler calls `compiled_graph.astream()`; it must not import from `graph/nodes/` directly

---

## SSE Wire Format

The agentic endpoint emits exactly five event types in the order below. All events use the `data: {...}\n\n` Server-Sent Events framing.

| Event type | Emitting node | Payload fields |
|------------|--------------|---------------|
| `agent_step` (router) | Router node update | `type: "agent_step"`, `node: "router"`, `payload.query_type`, `payload.strategy`, `payload.duration_ms` |
| `agent_step` (grader) | Grader node update | `type: "agent_step"`, `node: "grader"`, `payload.scores`, `payload.web_fallback`, `payload.duration_ms` |
| `agent_step` (critic) | Critic node update | `type: "agent_step"`, `node: "critic"`, `payload.hallucination_risk`, `payload.reruns`, `payload.duration_ms` |
| `token` | Generator node update | `type: "token"`, `content: str` |
| `citations` | Generator node update | `type: "citations"`, `citations: list`, `confidence: float`, `chunks_retrieved: int` |
| `done` | Stream end | `type: "done"` |

`duration_ms` is an `int` in every `agent_step` payload. Its value is sourced from the timing entry each node appends to `state.steps_taken`. This field is required — the frontend renders per-node latency bars from it.

The `token`, `citations`, and `done` event shapes are identical to the Phase 1 endpoint and must not diverge.

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Define `AgentStepEvent` Pydantic schemas for SSE serialization | backend-developer | 2c all |
| T02 | ✅ Done | Implement `POST /api/v1/query/agentic` SSE route handler | backend-developer | T01 |
| T03 | ✅ Done | Register agentic router in `main.py` | backend-developer | T01, T02 |
| T04 | ✅ Done | Unit tests for the agentic route (mocked graph, SSE event shape) | backend-developer | T01–T03 |
| T05 | ✅ Done | Next.js proxy route `/api/proxy/query/agentic/route.ts` | frontend-developer | T02 |

---

## Ordered Execution Plan

### Batch 1 — No dependencies (after 2c gate)
- **T01** — Pydantic SSE schemas (defines wire contract before route is written)

### Batch 2 — After T01
- **T02** — Route handler implementation

### Batch 3 — After T02
- **T03** — Register router in `main.py`

### Batch 4 — After T01–T03
- **T04** — Unit tests (backend)
- **T05** — Next.js proxy (frontend, parallel with T04)

---

## Definition of Done Per Task

### T01 — `AgentStepEvent` Pydantic schemas

**File:** `backend/src/api/schemas/agentic.py` (new file — do not add to existing `schemas.py`)

**Governed by:** ADR-004 (amended)

**What:** Backend Pydantic models that serialise SSE events from the agentic endpoint to JSON. These are the server-side mirror of the TypeScript types defined in 2a-T04.

**Models and their field contracts:**

`RouterStepPayload`:

| Field | Type | Constraint | Wire name |
|-------|------|-----------|-----------|
| `query_type` | `Literal["factual", "analytical", "multi_hop", "ambiguous"]` | — | `query_type` |
| `strategy` | `Literal["dense", "hybrid", "web"]` | — | `strategy` |
| `duration_ms` | `int` | — | `duration_ms` |

`GraderStepPayload`:

| Field | Type | Constraint | Wire name |
|-------|------|-----------|-----------|
| `scores` | `list[float]` | — | `scores` |
| `web_fallback` | `bool` | — | `web_fallback` |
| `duration_ms` | `int` | — | `duration_ms` |

`CriticStepPayload`:

| Field | Type | Constraint | Wire name |
|-------|------|-----------|-----------|
| `hallucination_risk` | `float` | `0.0 ≤ value ≤ 1.0` | `hallucination_risk` |
| `reruns` | `int` | — | `reruns` |
| `duration_ms` | `int` | — | `duration_ms` |

`AgentStepEvent`:

| Field | Type | Notes |
|-------|------|-------|
| `type` | `Literal["agent_step"]` | Discriminant; default value `"agent_step"` |
| `node` | `Literal["router", "grader", "critic"]` | Which node produced this step |
| `payload` | `RouterStepPayload \| GraderStepPayload \| CriticStepPayload` | Discriminated by `node` field |

`AgentQueryRequest` (request body schema):

| Field | Type | Constraint |
|-------|------|-----------|
| `query` | `str` | `min_length=1`, `max_length=2000` |
| `k` | `int \| None` | `1 ≤ k ≤ 20` when set |
| `filters` | `dict[str, str] \| None` | Optional metadata filter passthrough |

**Pre-implementation check:** Verify no `AgentStepEvent` or `AgentQueryRequest` class already exists in `backend/src/`. Duplicate class names are caught by the Gate 3 grep check.

**Acceptance criteria:**
- [ ] `backend/src/api/schemas/agentic.py` created with all models above
- [ ] `AgentStepEvent.type` is a `Literal["agent_step"]` with a default value
- [ ] mypy backend/src/ --strict — zero errors
- [ ] No duplicate class names (grep for `^class ` across `backend/src/` produces zero duplicates)

**Conventional commit:** `feat(api): add AgentStepEvent Pydantic schemas for agentic SSE wire format`

---

### T02 — `POST /api/v1/query/agentic` route handler

**File:** `backend/src/api/routes/query_agentic.py` (new file)

**What:** A FastAPI route that streams the compiled graph's output as SSE events to the client.

**Route signature and parameter contract:**

| Parameter | Source | Type | Notes |
|-----------|--------|------|-------|
| `body` | Request body (JSON) | `AgentQueryRequest` | Validated by Pydantic |
| `compiled_graph` | FastAPI dependency | `CompiledGraphDep` | Injected via `deps.py`; no direct graph import |
| `settings` | FastAPI dependency | `SettingsDep` | For configuration access |
| Session ID | `X-Session-ID` header | `str` | Read from `request.headers`; falls back to generated UUID |

**`X-Session-ID` contract:** The route handler reads this header from the incoming HTTP request and passes it as `config={"configurable": {"thread_id": session_id}}` to `compiled_graph.astream()`. This maps each browser session to a `SqliteSaver` conversation thread. The session ID is never included in the request body.

**Initial state construction:** The route handler constructs the initial `AgentState` dict with only the input fields (`session_id`, `query`, `filters`, `k`). All other fields are populated by node functions. Do not pre-populate node output fields.

**SSE streaming loop:** The handler calls `compiled_graph.astream(initial_state, config=config, stream_mode="updates")`. Each yielded chunk is a `dict[node_name, partial_state_update]`. For each chunk:
- If the node is `"router"`, `"grader"`, or `"critic"`: construct the matching `AgentStepEvent`, extract `duration_ms` from the `steps_taken` entry, and yield it as an SSE `data:` line
- If the node is `"generator"`: yield one `token` event per logical unit of the answer string, then one `citations` event
- After the async generator is exhausted: yield the `done` event

**`build_agent_step_event` helper:** A private function in the same module that receives `(node_name: str, state_update: dict)` and returns the correct `AgentStepEvent` by extracting `duration_ms` from `state.steps_taken`. This isolates the timing extraction logic from the streaming loop.

**Gate 3 constraint check:** After implementation, the following grep must produce zero matches: `AsyncQdrantClient(`, `AzureChatOpenAI(`, `AzureOpenAIEmbeddings(` anywhere in `backend/src/api/routes/`.

**Acceptance criteria:**
- [ ] Route file created; handler uses `CompiledGraphDep` exclusively (no import from `graph/`)
- [ ] `X-Session-ID` header read from request headers (not body)
- [ ] All 5 event types emitted in the correct order when graph completes
- [ ] `StreamingResponse` returned with `media_type="text/event-stream"`
- [ ] mypy backend/src/ --strict — zero errors
- [ ] ruff check — zero warnings
- [ ] No client instantiation in route handler

**Conventional commit:** `feat(api): implement POST /api/v1/query/agentic SSE streaming endpoint`

---

### T03 — Register agentic router in `main.py`

**What:** Add one `app.include_router()` call in `main.py`. The prefix is `/api/v1` and the tag is `"query"` — consistent with the Phase 1 query router. No other changes to `main.py` are permitted.

**Acceptance criteria:**
- [ ] Router registered in `main.py`
- [ ] `GET /openapi.json` includes the new endpoint
- [ ] No other changes to `main.py`

**Conventional commit:** `feat(api): register agentic query router`

---

### T04 — Unit tests for agentic route

**File:** `backend/tests/unit/api/test_query_agentic.py`

**Mock strategy:** Mock `compiled_graph.astream()` to yield a predefined sequence of `{node_name: state_update}` dicts. No real graph is invoked.

**Required test cases:**

| # | Scenario | Assertion |
|---|----------|-----------|
| 1 | Happy path: valid body, graph yields all node updates | SSE stream contains `agent_step` (router), `agent_step` (grader), `agent_step` (critic), `token`, `citations`, `done` in that order |
| 2 | `X-Session-ID` header present | Session ID from header used as graph `thread_id` in config |
| 3 | `X-Session-ID` header absent | Auto-generated UUID used as graph `thread_id` |
| 4 | Invalid body (empty query string) | HTTP 422 Unprocessable Entity |
| 5 | Graph raises exception mid-stream | HTTP 500 response; SSE stream does not hang open |

**Acceptance criteria:**
- [ ] `test_query_agentic.py` — ≥ 5 tests
- [ ] SSE event order verified in test assertions
- [ ] pytest backend/tests/unit/ -q — all green
- [ ] mypy — zero errors

**Conventional commit:** `test(api): add unit tests for agentic query endpoint`

---

### T05 — Next.js proxy route

**File:** `frontend/src/app/api/proxy/query/agentic/route.ts` (new file)

**Governed by:** ADR-005

**What:** A thin Next.js App Router server-side proxy, structurally identical to the existing `query/route.ts`. The only addition is forwarding the `X-Session-ID` header when it is present on the incoming browser request. The proxy does not generate session IDs — that responsibility belongs to the `useAgentStream` hook.

**Proxy contract:**

| Concern | Behaviour |
|---------|-----------|
| HTTP method | POST only |
| Forwarded headers | `Content-Type: application/json`, `X-API-Key` from env, `X-Session-ID` (when present on incoming request) |
| Body forwarding | Raw JSON body from browser request forwarded unchanged |
| Response | Streamed `Response` object returned to browser; `text/event-stream` content type preserved |
| Existing `query/route.ts` | Must not be modified |

**Acceptance criteria:**
- [ ] Proxy file created; `X-Session-ID` forwarded when present in the incoming request
- [ ] tsc --noEmit — zero errors
- [ ] eslint — zero warnings
- [ ] Existing `query/route.ts` unchanged

**Conventional commit:** `feat(proxy): add /api/proxy/query/agentic Next.js route with session ID forwarding`

---

## Phase 2d Gate Criteria

All of the following must be true before Phase 2e (Parallel UI) begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | `POST /api/v1/query/agentic` | Endpoint exists in OpenAPI docs |
| G02 | SSE wire format | All 5 event types emitted in correct order |
| G03 | `X-Session-ID` | Header read, passed to graph config |
| G04 | `duration_ms` | Present in every `agent_step` payload |
| G05 | Phase 1 `query.py` | Unchanged — git diff shows zero modifications |
| G06 | mypy backend/src/ --strict | Zero errors |
| G07 | ruff check | Zero warnings |
| G08 | pytest backend/tests/unit/ -q | All green |
| G09 | tsc --noEmit | Zero errors |
| G10 | Next.js proxy | `/api/proxy/query/agentic` route exists |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `stream_mode="updates"` yields unexpected chunk shape for generator node | Medium | Medium | Write test asserting chunk shape before route logic depends on it |
| `duration_ms` not available in `state_update` (timing not stored by nodes) | Medium | High | Nodes must store timing in `steps_taken` (2c design) — confirm before starting T02 |
| SSE connection drops mid-stream | Low | Low | Client-side `useAgentStream` hook handles reconnect (2e) |
| `X-Session-ID` not forwarded by Next.js proxy | Low | Medium | Covered by T05; also verified in T04 test case 2 |
