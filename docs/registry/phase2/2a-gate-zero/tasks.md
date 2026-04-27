# Phase 2a — Gate Zero (Tier 3 Pre-requisites)

> Status: ✅ Complete | Phase: 2a | Gate Passed: 2026-04-27
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Governed by: stack-upgrade-proposal.md §Tier-3
> Last updated: 2026-04-26
>
> **Hard gate:** No Phase 2b task may begin until every task here is ✅ Done and CI is green.
> This is not optional — agent node code written against an unconfirmed LangGraph API surface will break mid-phase.

---

## Context

Phase 2 introduces a LangGraph state machine replacing the Phase 1 LCEL `GenerationChain` for the agentic pipeline. The parallel-view UI runs both pipelines simultaneously. Before any graph or node code is written, three pre-requisites from stack-upgrade-proposal.md Tier 3 must be completed:

1. **Exact LangGraph + LangChain bundle version lock** — prevents mid-phase API surface breaks
2. **ADR-004 amendment** — documents confirmed version, `SqliteSaver` import path, `stream_mode` decision, and concurrency constraint
3. **`AgentState` TypedDict** — the shared state schema is the Phase 2 interface contract; all node functions are written against it
4. **`AgentStreamEvent` TypeScript union** — frontend types must exist before any hook or component is written

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Resolve and pin exact LangGraph + LangChain bundle versions | backend-developer | — |
| T02 | ✅ Done | Write ADR-004 amendment | architect | T01 |
| T03 | ✅ Done | Define `AgentState` TypedDict + unit tests | backend-developer | T01, T02 |
| T04 | ✅ Done | Define `AgentStreamEvent` TypeScript union in `frontend/src/types/index.ts` | frontend-developer | T02 |
| T05 | ✅ Done | Gate zero CI verification — all commands clean | backend-developer | T01–T04 |

---

## Ordered Execution Plan

### Batch 1 — No dependencies
- **T01** — Resolve LangGraph + LangChain bundle; pin exact version in `pyproject.toml`

### Batch 2 — After T01
- **T02** — Write ADR-004 amendment (requires confirmed version number from T01)

### Batch 3 — After T02
- **T03** — `AgentState` TypedDict + unit tests (backend)
- **T04** — `AgentStreamEvent` TS union (frontend)

### Batch 4 — After T03 + T04
- **T05** — Full CI gate run; confirm zero errors across all commands

---

## Definition of Done Per Task

### T01 — Resolve and pin LangGraph + LangChain bundle

**What:**
Resolve a compatible bundle of `langgraph`, `langchain`, `langchain-openai`, and `langchain-core` using dry-run resolution. Confirm the following LangGraph public API surface exists in the resolved version: `StateGraph`, `add_node`, `add_conditional_edges`, `compile`, and `CompiledStateGraph.astream()`. Confirm the `SqliteSaver` import path — it may reside in `langgraph.checkpoint.sqlite` or in a separate `langgraph-checkpoint-sqlite` package. Pin all four packages with tilde ranges (major.minor.patch) — no caret ranges. Install into a clean environment and verify the lockfile resolves without conflicts. Confirm `stream_mode="updates"` yields `dict[node_name, partial_state]` per node and `stream_mode="values"` yields full state after every node; record the chosen mode decision.

**Acceptance criteria:**
- [ ] `langgraph`, `langchain`, `langchain-openai`, `langchain-core` pinned to tilde ranges in `pyproject.toml`
- [ ] `poetry.lock` updated and committed
- [ ] `from langgraph.graph import StateGraph` imports without error in a scratch test
- [ ] `SqliteSaver` import path confirmed and noted in commit message
- [ ] `stream_mode` behaviour confirmed; decision recorded for ADR-004 amendment
- [ ] ruff check — zero warnings
- [ ] mypy backend/src/ --strict — zero errors (no new ignores introduced)
- [ ] pytest backend/tests/unit/ -q — all existing tests still green

**Conventional commit:** `chore(deps): lock LangGraph ~X.Y.Z + LangChain bundle for Phase 2`

---

### T02 — Write ADR-004 amendment

**Governed by:** ADR-004 (`docs/adr/004-langgraph-vs-chain.md`)

**What:** Append an `## Amendment — Phase 2 Confirmed Configuration` section to `docs/adr/004-langgraph-vs-chain.md`. Do not rewrite the original ADR — append only. The status line must be updated to `Accepted (amended Phase 2 — YYYY-MM-DD)`.

**The amendment must document all six items below:**

1. Confirmed LangGraph version and tilde-pin rationale
2. Confirmed `SqliteSaver` import path and package (in-package or separate)
3. Confirmed `stream_mode` decision (`"updates"` vs `"values"`) with rationale
4. `SqliteSaver` single-writer constraint: `--workers 1` is required for Phase 2 dev; `PostgresSaver` or `CosmosSaver` is required for Phase 7 multi-replica deployment
5. `X-Session-ID` header contract: the route handler reads this header and passes it as `config={"configurable": {"thread_id": session_id}}` to `compiled_graph.astream()`
6. `duration_ms` field commitment: every `agent_step` SSE event payload must include `duration_ms: int` from day one; retrofitting this field requires a wire format version bump

**Acceptance criteria:**
- [ ] Amendment section appended to `docs/adr/004-langgraph-vs-chain.md`
- [ ] All six items above documented
- [ ] ADR status line updated

**Conventional commit:** `docs(adr): amend ADR-004 with Phase 2 LangGraph confirmed configuration`

---

### T03 — Define `AgentState` TypedDict + unit tests

**File:** `backend/src/graph/state.py` (new file; `backend/src/graph/__init__.py` must be created first)

**Governed by:** ADR-004 (amended)

`AgentState` is the shared interface contract for the entire Phase 2 graph. Every node reads from and writes to this TypedDict. No node may be implemented without this schema in place.

**Field groups and their design:**

| Group | Fields | Type / Shape | Purpose | Reducer |
|-------|--------|--------------|---------|---------|
| Input | `session_id` | `str` | Identifies the LangGraph thread via `SqliteSaver` | None — set once by route handler |
| Input | `query` | `str` | Raw user query | None |
| Input | `filters` | `dict[str, str] \| None` | Optional Qdrant metadata filters | None |
| Input | `k` | `int \| None` | Max chunks to retrieve | None |
| Router output | `query_type` | `Literal["factual", "analytical", "multi_hop", "ambiguous"]` | Classification driving retrieval strategy | None |
| Router output | `retrieval_strategy` | `Literal["dense", "hybrid", "web"]` | Strategy selected by Router node | None |
| Router output | `query_rewritten` | `str \| None` | HyDE or step-back rewrite; `None` if no rewrite applied | None |
| Retriever output | `retrieved_docs` | `list[Document]` | Raw retrieval results | `operator.add` — append-only across retries |
| Retriever output | `web_fallback_used` | `bool` | True if Tavily was called | None |
| Grader output | `grader_scores` | `list[float]` | Per-chunk relevance scores in `[0.0, 1.0]` | None |
| Grader output | `graded_docs` | `list[Document]` | Chunks that passed the grader threshold | None |
| Grader output | `all_below_threshold` | `bool` | True when every chunk scored below `GRADER_THRESHOLD` | None |
| Grader output | `retry_count` | `int` | Retry counter; max value 1, enforced by edge functions | None |
| Generator output | `answer` | `str \| None` | Generated answer text | None |
| Generator output | `citations` | `list[Citation]` | Citation objects referencing `graded_docs` | None |
| Generator output | `confidence` | `float \| None` | Generator self-assessed confidence in `[0.0, 1.0]` | None |
| Critic output | `critic_score` | `float \| None` | Hallucination risk score in `[0.0, 1.0]`; higher = more risk | None |
| Conversation history | `messages` | `list[BaseMessage]` | Full conversation thread | `add_messages` from `langgraph.graph.message` — deduplicates by message ID |
| Observability | `steps_taken` | `list[str]` | Ordered log of node names + timing entries | `operator.add` — append-only |

`Document` is `langchain_core.documents.Document`. `Citation` is `src.schemas.generation.Citation`.

Fields with `operator.add` or `add_messages` reducers use the `Annotated[T, reducer]` form. All other fields are plain TypedDict fields with no reducer — later writes overwrite earlier writes for the same key.

**Unit tests:** `backend/tests/unit/graph/test_state.py`

Tests must cover:
1. `retrieved_docs` reducer: two partial updates append (not overwrite)
2. `messages` reducer: `add_messages` deduplicates by message ID correctly
3. `steps_taken` reducer: string list appends across two updates
4. All required field names present in `AgentState.__annotations__`

**Acceptance criteria:**
- [ ] `backend/src/graph/__init__.py` created
- [ ] `backend/src/graph/state.py` created with all fields from the table above
- [ ] `backend/tests/unit/graph/__init__.py` created
- [ ] `backend/tests/unit/graph/test_state.py` with ≥ 4 tests covering all three reducers and field presence
- [ ] mypy backend/src/ --strict — zero errors
- [ ] pytest backend/tests/unit/ -q — all green including new state tests
- [ ] No new `# type: ignore` comments introduced

**Conventional commit:** `feat(graph): define AgentState TypedDict with Annotated reducers`

---

### T04 — Define `AgentStreamEvent` TypeScript union

**File:** `frontend/src/types/index.ts` (append to existing — do not rewrite existing types)

**Governed by:** ADR-004 (amended), ADR-005

This task defines the discriminated union of all SSE event types the agentic endpoint can emit. It must be completed before any hook or component touches the agentic stream.

**New types to add (append only):**

`RouterStepPayload` — payload shape for the router `agent_step` event:

| Field | Type | Purpose |
|-------|------|---------|
| `query_type` | `"factual" \| "analytical" \| "multi_hop" \| "ambiguous"` | Router classification result |
| `strategy` | `"dense" \| "hybrid" \| "web"` | Retrieval strategy selected |
| `duration_ms` | `number` | Node wall-clock time in milliseconds |

`GraderStepPayload` — payload for the grader `agent_step` event:

| Field | Type | Purpose |
|-------|------|---------|
| `scores` | `number[]` | Per-chunk relevance scores |
| `web_fallback` | `boolean` | True if Tavily web fallback was triggered |
| `duration_ms` | `number` | Node wall-clock time in milliseconds |

`CriticStepPayload` — payload for the critic `agent_step` event:

| Field | Type | Purpose |
|-------|------|---------|
| `hallucination_risk` | `number` | Risk score in `[0.0, 1.0]` |
| `reruns` | `number` | Number of re-retrieval cycles triggered |
| `duration_ms` | `number` | Node wall-clock time in milliseconds |

`AgentStepNode` — discriminant helper: union of `"router" | "grader" | "critic"`.

`AgentStepEvent` — discriminated union member with discriminant field `type: "agent_step"`:

| Field | Type |
|-------|------|
| `type` | `"agent_step"` (literal — discriminant) |
| `node` | `AgentStepNode` |
| `payload` | `RouterStepPayload \| GraderStepPayload \| CriticStepPayload` |

`AgentStreamEvent` — top-level event union: `StreamEvent | AgentStepEvent`. `StreamEvent` is the existing type covering `token`, `citations`, and `done` events. `AgentStreamEvent` is additive — it does not replace `StreamEvent`.

`AgentStep` — in-memory representation of a completed agent step stored on a message:

| Field | Type | Purpose |
|-------|------|---------|
| `node` | `AgentStepNode` | Which node produced this step |
| `payload` | `RouterStepPayload \| GraderStepPayload \| CriticStepPayload` | Step data |
| `timestamp` | `string` | ISO 8601 wall-clock time when event was received |

**Acceptance criteria:**
- [ ] All five types (`RouterStepPayload`, `GraderStepPayload`, `CriticStepPayload`, `AgentStepEvent`, `AgentStreamEvent`) appended to `frontend/src/types/index.ts`
- [ ] `AgentStepEvent.type` is a string literal (`"agent_step"`) — valid discriminant
- [ ] `AgentStreamEvent = StreamEvent | AgentStepEvent` — no existing types modified
- [ ] tsc --noEmit — zero errors
- [ ] eslint — zero warnings
- [ ] No existing type definitions modified

**Conventional commit:** `feat(types): add AgentStreamEvent union for Phase 2 agentic SSE`

---

### T05 — Gate zero CI verification

Run all DoD commands and confirm zero output. Commands (unformatted, for reference):

- ruff check backend/src/ backend/tests/
- mypy backend/src/ --strict
- pytest backend/tests/unit/ -q --tb=short
- grep -rn "RetrievalQA\|LLMChain\|StuffDocumentsChain\|ConversationalRetrievalChain" backend/src/ --include="*.py"
- grep -rn "api_key=settings\." backend/src/ --include="*.py" | grep -v "get_secret_value"
- grep -rn "AsyncQdrantClient(\|AzureChatOpenAI(\|AzureOpenAIEmbeddings(" backend/src/api/routes/ --include="*.py"
- grep -rn "^class " backend/src/ --include="*.py" | awk -F: '{print $NF}' | sort | uniq -d
- grep -rn "^[[:space:]]*print(" backend/src/ --include="*.py"
- tsc --noEmit
- npm run lint

**Acceptance criteria:**
- [ ] All commands above produce zero output / zero errors
- [ ] npm run build succeeds (frontend)
- [ ] CI workflow green on the gate-zero branch

---

## Phase 2a Gate Criteria

All of the following must be true before Phase 2b (Graph Skeleton) begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | `langgraph` version in `pyproject.toml` | Tilde-pinned, no caret |
| G02 | `poetry.lock` | Committed, no conflicts |
| G03 | ADR-004 amendment | Appended, all 6 items documented |
| G04 | `backend/src/graph/state.py` | Exists, all fields present, mypy strict passes |
| G05 | `backend/tests/unit/graph/test_state.py` | ≥ 4 tests, all green |
| G06 | `frontend/src/types/index.ts` | `AgentStreamEvent` union present, tsc clean |
| G07 | All existing unit tests | Still green (no regressions) |
| G08 | CI | Green on gate-zero branch |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| LangGraph version incompatible with current `langchain-core` pin | Medium | High | Run bundle resolution as first step; if conflict, adjust `langchain-core` bound with architect sign-off |
| `SqliteSaver` moved to a separate package (`langgraph-checkpoint-sqlite`) | Medium | Low | Check PyPI before pinning; add package if needed; document in ADR-004 amendment |
| `stream_mode="updates"` yields unexpected structure in confirmed version | Low | High | Write smoke test asserting event structure before any route handler code |
| New `mypy` errors from LangGraph stubs | Low | Medium | Add targeted `# type: ignore[import-untyped]` on LangGraph imports only; document reason |
