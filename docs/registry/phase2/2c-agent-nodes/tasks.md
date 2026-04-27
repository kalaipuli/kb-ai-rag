# Phase 2c — Agent Nodes (Router, Retriever, Grader, Generator, Critic)

> Status: ✅ Complete | Phase: 2c | Gate passed: 2026-04-27
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-27
>
> **Prerequisite:** Phase 2b gate must pass before any task here starts.
> **Goal:** Replace all stub node functions with real implementations. Each node is a standalone, fully tested async function. No node begins implementation until the preceding node's tests are green.

---

## Context

Each node is implemented and tested in isolation before being wired together. The sequence is strictly enforced by data dependencies in `AgentState`:
- Router must precede Retriever — Retriever reads `retrieval_strategy` written by Router
- Retriever must precede Grader — Grader reads `retrieved_docs` written by Retriever
- Grader must precede Generator — Generator reads `graded_docs` written by Grader
- Generator must precede Critic — Critic evaluates `answer` written by Generator

**Agentic patterns implemented in this phase:**

| Pattern | Node | Mechanism |
|---------|------|-----------|
| Adaptive RAG | Router | Selects retrieval strategy per classified query type |
| HyDE (Hypothetical Document Embeddings) | Router | Rewrites `analytical` queries to a hypothetical answer document before embedding |
| Step-back prompting | Router | Rewrites `multi_hop` queries to a broader generalisation before retrieval |
| Corrective RAG (CRAG) | Grader → edge | When all chunks score below `GRADER_THRESHOLD`, edge routes to Tavily web fallback |
| Self-RAG | Critic → edge | When `critic_score > CRITIC_THRESHOLD`, edge routes back to retriever for re-retrieval |

**LLM model assignment (cost-aware):**

| Node | Model | Rationale |
|------|-------|-----------|
| Router | GPT-4o-mini | Classification only; low token budget |
| Grader | GPT-4o-mini | Scoring only; batched across chunks |
| Critic | GPT-4o-mini | Binary hallucination check; low token budget |
| Generator | GPT-4o | Answer generation — quality-critical path |

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Implement Router node (query classification + HyDE + step-back) | backend-developer | 2b all |
| T02 | ✅ Done | Implement Retriever node (HybridRetriever + Tavily web fallback) | backend-developer | T01 |
| T03 | ✅ Done | Implement Grader node (chunk relevance scoring + `all_below_threshold` flag) | backend-developer | T02 |
| T04 | ✅ Done | Implement Generator node (GPT-4o cited answer) | backend-developer | T03 |
| T05 | ✅ Done | Implement Critic node (hallucination risk scoring) | backend-developer | T04 |
| T06 | ✅ Done | Integration smoke test: full graph end-to-end with mocked LLMs | backend-developer | T01–T05 |

---

## Ordered Execution Plan

Each task is strictly sequential — do not start the next until the previous task's tests are green.

### Batch 1
- **T01** — Router node

### Batch 2 — After T01 green
- **T02** — Retriever node

### Batch 3 — After T02 green
- **T03** — Grader node

### Batch 4 — After T03 green
- **T04** — Generator node

### Batch 5 — After T04 green
- **T05** — Critic node

### Batch 6 — After all nodes green
- **T06** — Full graph smoke test

---

## Definition of Done Per Task

### T01 — Router node

**File:** `backend/src/graph/nodes/router.py` (replace stub)

**Governed by:** ADR-004 (amended)

**State interface:**

| Direction | Fields read/written | Notes |
|-----------|--------------------|----|
| Reads | `state.query` | Raw user query |
| Writes | `query_type` | Classification result |
| Writes | `retrieval_strategy` | Derived from `query_type` |
| Writes | `query_rewritten` | Set for `analytical` (HyDE) and `multi_hop` (step-back); `None` otherwise |
| Writes | `steps_taken` | Appends one entry: `"router:{query_type}:{strategy}:{duration_ms}ms"` |

**Responsibilities:**
1. Call GPT-4o-mini with structured output to classify `query_type` from `state.query`
2. Derive `retrieval_strategy` from classification: `factual` → `hybrid`; `analytical` → `hybrid` (with HyDE rewrite); `multi_hop` → `hybrid` (with step-back rewrite); `ambiguous` → `dense`
3. For `analytical` queries: generate a hypothetical document answer (HyDE) via a second GPT-4o-mini call; store in `query_rewritten`
4. For `multi_hop` queries: rewrite query to a broader step-back question via GPT-4o-mini; store in `query_rewritten`
5. Record wall-clock duration and append to `steps_taken`

**LLM call pattern:** `AzureChatOpenAI(model="gpt-4o-mini")` injected via the builder closure. The node does not instantiate or import `AzureChatOpenAI` directly.

**Router structured output schema** (internal to the node, not exported):

| Field | Type | Purpose |
|-------|------|---------|
| `query_type` | `Literal["factual", "analytical", "multi_hop", "ambiguous"]` | Classification result |
| `retrieval_strategy` | `Literal["dense", "hybrid", "web"]` | Strategy to use |
| `reasoning` | `str` | LangSmith trace visibility only; not stored in state |

**Error handling:** If the LLM call raises any exception, log via structlog and return safe defaults: `query_type = "factual"`, `retrieval_strategy = "hybrid"`, `query_rewritten = None`. The graph must continue — do not re-raise.

**Unit tests (`test_router.py`) must cover:**
1. Classifies a factual query correctly (mock structured output)
2. Sets `retrieval_strategy = "hybrid"` for factual query
3. Generates HyDE rewrite and stores in `query_rewritten` for analytical query
4. Generates step-back rewrite and stores in `query_rewritten` for multi_hop query
5. Falls back to `"factual"/"hybrid"` defaults when LLM raises (error path)
6. `duration_ms` value present in `steps_taken` output

**Acceptance criteria:**
- [ ] Node function implemented with full docstring
- [ ] Structured output schema defined as a Pydantic model within the node module
- [ ] `backend/tests/unit/graph/test_router.py` — ≥ 6 tests including error path
- [ ] mypy backend/src/ --strict — zero errors
- [ ] pytest backend/tests/unit/ -q — all green
- [ ] ruff check — zero warnings
- [ ] No real Azure OpenAI calls in tests (all mocked with `AsyncMock`)

**Conventional commit:** `feat(graph): implement Router node with Adaptive RAG + HyDE + step-back`

---

### T02 — Retriever node

**File:** `backend/src/graph/nodes/retriever.py` (replace stub)

**State interface:**

| Direction | Fields read/written | Notes |
|-----------|--------------------|----|
| Reads | `state.retrieval_strategy` | Determines retrieval path |
| Reads | `state.query_rewritten` | Used as retrieval query if set; otherwise falls back to `state.query` |
| Reads | `state.query` | Fallback when `query_rewritten` is `None` |
| Reads | `state.k`, `state.filters` | Retrieval parameters |
| Writes | `retrieved_docs` | Appended via `operator.add` reducer |
| Writes | `web_fallback_used` | `True` if Tavily was called |
| Writes | `steps_taken` | Appends one entry with `duration_ms` |

**Responsibilities:**
1. Determine the effective query: use `state.query_rewritten` if set, otherwise `state.query`
2. Branch on `state.retrieval_strategy`:
   - `dense` or `hybrid` → call `HybridRetriever.retrieve(query, k)` (injected via builder closure)
   - `web` → call Tavily search (triggered by CRAG edge routing)
3. Convert all results to `langchain_core.documents.Document` objects with source metadata
4. Set `web_fallback_used = True` if and only if Tavily was called
5. Record wall-clock duration and append to `steps_taken`

**New dependency:** `tavily-python` — must be added to `pyproject.toml`. New `Settings` field: `TAVILY_API_KEY: SecretStr`. Must use `.get_secret_value()` when passing to Tavily client — never log or expose the raw key.

**Dependency injection rule:** The node function receives `HybridRetriever` via a builder closure. The node module must not import from `backend/src/retrieval/` directly. This enforces the layered architecture rule: `graph/nodes/` may call `retrieval/` only through injected interfaces.

**Error handling:**
- Tavily call fails: log via structlog; set `web_fallback_used = False`; return empty `retrieved_docs` update — do not raise
- `HybridRetriever.retrieve` fails: log via structlog; return empty `retrieved_docs` update — do not raise

**Unit tests (`test_retriever.py`) must cover:**
1. Calls `HybridRetriever.retrieve()` when strategy is `"hybrid"`
2. Uses `query_rewritten` as the retrieval query when set (not raw `query`)
3. Calls Tavily when strategy is `"web"`; sets `web_fallback_used = True`
4. Falls back gracefully when Tavily raises (error path)
5. Falls back gracefully when `HybridRetriever` raises (error path)
6. `steps_taken` contains retriever entry with `duration_ms`

**Acceptance criteria:**
- [ ] `tavily-python` added to `pyproject.toml`
- [ ] `TAVILY_API_KEY` added to `Settings` and `.env.example`
- [ ] Node implemented; `HybridRetriever` injected via builder closure (no direct import from `retrieval/`)
- [ ] `backend/tests/unit/graph/test_retriever.py` — ≥ 6 tests including 2 error paths
- [ ] mypy backend/src/ --strict — zero errors
- [ ] pytest backend/tests/unit/ -q — all green

**Conventional commit:** `feat(graph): implement Retriever node with HybridRetriever + Tavily web fallback`

---

### T03 — Grader node

**File:** `backend/src/graph/nodes/grader.py` (replace stub)

**State interface:**

| Direction | Fields read/written | Notes |
|-----------|--------------------|----|
| Reads | `state.retrieved_docs` | All retrieved chunks to score |
| Reads | `state.query` | Used as the relevance reference for scoring |
| Writes | `grader_scores` | Float score per chunk, same order as `retrieved_docs` |
| Writes | `graded_docs` | Chunks where score ≥ `GRADER_THRESHOLD` |
| Writes | `all_below_threshold` | `True` when every chunk scored below threshold |
| Writes | `retry_count` | Incremented by 1; the edge function checks this against `MAX_RETRIES` |
| Writes | `steps_taken` | Appends one entry with scores summary and `duration_ms` |

**Responsibilities:**
1. Score each document in `state.retrieved_docs` for relevance to `state.query` using GPT-4o-mini structured output
2. Use batched LLM calls (`llm.batch()`) rather than sequential calls to control cost and latency; cap batch at 10 chunks maximum
3. Filter `graded_docs` to docs where `score >= GRADER_THRESHOLD` (imported from `edges.py`)
4. Set `all_below_threshold = True` if every score falls below `GRADER_THRESHOLD`
5. Increment `retry_count` by 1 (edge function, not this node, decides whether to re-route)
6. Record wall-clock duration and scores summary in `steps_taken`

**Grader structured output schema** (internal to the node, not exported):

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `score` | `float` | `0.0 ≤ score ≤ 1.0` | Relevance score |
| `reasoning` | `str` | — | LangSmith trace visibility only |

**Routing responsibility boundary:** The Grader node sets `all_below_threshold` and increments `retry_count`. The decision to re-route to the Retriever is made entirely by `route_after_grader` in `edges.py`. The node does not contain routing logic.

**Error handling:** If the LLM call fails for any individual chunk, assign a score of `0.0` for that chunk and log a warning via structlog. Do not raise.

**Unit tests (`test_grader.py`) must cover:**
1. All scores above threshold: `graded_docs` contains all retrieved docs; `all_below_threshold = False`
2. All scores below threshold: `graded_docs` is empty; `all_below_threshold = True`
3. Mixed scores: only above-threshold docs in `graded_docs`
4. `retry_count` incremented by 1 from its incoming value
5. LLM failure for one chunk: that chunk receives score `0.0` (error path)
6. `steps_taken` contains grader entry with `duration_ms`

**Acceptance criteria:**
- [ ] Node implemented with batched LLM scoring; batch capped at 10 chunks
- [ ] `backend/tests/unit/graph/test_grader.py` — ≥ 6 tests including error path
- [ ] mypy backend/src/ --strict — zero errors
- [ ] pytest backend/tests/unit/ -q — all green

**Conventional commit:** `feat(graph): implement Grader node with chunk relevance scoring`

---

### T04 — Generator node

**File:** `backend/src/graph/nodes/generator.py` (replace stub)

**State interface:**

| Direction | Fields read/written | Notes |
|-----------|--------------------|----|
| Reads | `state.graded_docs` | Primary context for answer generation |
| Reads | `state.retrieved_docs` | Fallback context when `graded_docs` is empty and `web_fallback_used = True` |
| Reads | `state.query` | The question to answer |
| Reads | `state.messages` | Last 5 messages for conversation context |
| Reads | `state.web_fallback_used` | Controls which docs are used as context |
| Writes | `answer` | Generated answer text |
| Writes | `citations` | List of `Citation` objects referencing chunks used |
| Writes | `confidence` | Generator self-assessed confidence in `[0.0, 1.0]` |
| Writes | `messages` | Appends `HumanMessage(query)` + `AIMessage(answer)` via `add_messages` reducer |
| Writes | `steps_taken` | Appends one entry with `duration_ms` |

**Responsibilities:**
1. Select context: use `state.graded_docs`; if empty and `web_fallback_used = True`, fall back to `state.retrieved_docs`
2. Construct prompt: system prompt + last 5 messages from `state.messages` + context chunks + query
3. Call GPT-4o (quality-critical path) to generate a cited answer using structured output
4. Append `HumanMessage(state.query)` and `AIMessage(answer)` to `messages`
5. Record wall-clock duration in `steps_taken`

**Prompt reuse rule:** The system prompt from the Phase 1 `GenerationChain` must be imported from its existing module (do not copy-paste). Duplication of prompt text is a violation of the single-responsibility rule and a maintenance hazard.

**Token streaming note:** This node populates `state.answer` synchronously. SSE `token` events are produced by the route handler as it iterates over graph stream output, not by the node. Confirm the streaming mechanism (post-graph re-stream vs `stream_mode="messages"`) in the ADR-004 amendment before implementing the route handler in 2d.

**Generator structured output schema** (internal to the node):

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `answer` | `str` | — | Generated answer |
| `citations` | `list[CitationRef]` | — | References to source chunks |
| `confidence` | `float` | `0.0 ≤ value ≤ 1.0` | Self-assessed answer quality |
| `reasoning` | `str` | — | LangSmith trace visibility only |

**Error handling:** If the LLM call fails, return a safe fallback state update: `answer` set to a user-facing error message, `citations` set to an empty list, `confidence` set to `0.0`. Do not raise.

**Unit tests (`test_generator.py`) must cover:**
1. Generates answer using `graded_docs` as context
2. Falls back to `retrieved_docs` when `graded_docs` is empty and `web_fallback_used = True`
3. Appends `HumanMessage` and `AIMessage` to `state.messages`
4. Handles LLM failure gracefully (error path): returns fallback answer, empty citations, confidence `0.0`
5. `confidence` value is within `[0.0, 1.0]`
6. `steps_taken` contains generator entry with `duration_ms`

**Acceptance criteria:**
- [ ] Node implemented; system prompt imported from Phase 1 module (no copy-paste)
- [ ] `backend/tests/unit/graph/test_generator.py` — ≥ 6 tests including error path
- [ ] mypy backend/src/ --strict — zero errors
- [ ] pytest backend/tests/unit/ -q — all green

**Conventional commit:** `feat(graph): implement Generator node with cited answer generation`

---

### T05 — Critic node

**File:** `backend/src/graph/nodes/critic.py` (replace stub)

**State interface:**

| Direction | Fields read/written | Notes |
|-----------|--------------------|----|
| Reads | `state.answer` | The answer to evaluate for hallucination |
| Reads | `state.graded_docs` | Context the answer should be grounded in |
| Writes | `critic_score` | Hallucination risk in `[0.0, 1.0]`; higher = more risk |
| Writes | `steps_taken` | Appends one entry with score and `duration_ms` |

**Responsibilities:**
1. Assess whether `state.answer` makes claims not supported by `state.graded_docs`
2. Call GPT-4o-mini with structured output to produce a hallucination risk score
3. Set `critic_score` in `AgentState`
4. Record wall-clock duration in `steps_taken`

**Routing responsibility boundary:** The Critic node sets `critic_score`. The decision to re-route to the Retriever is made entirely by `route_after_critic` in `edges.py`. The node does not contain routing logic.

**Critic structured output schema** (internal to the node):

| Field | Type | Constraint | Purpose |
|-------|------|-----------|---------|
| `hallucination_risk` | `float` | `0.0 ≤ value ≤ 1.0` | Risk score |
| `unsupported_claims` | `list[str]` | — | Claims not grounded in context; for LangSmith trace visibility |
| `reasoning` | `str` | — | LangSmith trace visibility only |

**Error handling:** If the LLM call fails, return `critic_score = 0.0` (assume safe) and log a warning via structlog. Do not raise.

**Unit tests (`test_critic.py`) must cover:**
1. Low `critic_score` (≤ 0.7): state updated correctly; `unsupported_claims` accessible
2. High `critic_score` (> 0.7): state updated correctly (edge function handles routing, not tested here)
3. `unsupported_claims` field present in node output (for tracing)
4. LLM failure: `critic_score` returns `0.0` (error path)
5. `steps_taken` contains critic entry with `duration_ms`

**Acceptance criteria:**
- [ ] Node implemented
- [ ] `backend/tests/unit/graph/test_critic.py` — ≥ 5 tests including error path
- [ ] mypy backend/src/ --strict — zero errors
- [ ] pytest backend/tests/unit/ -q — all green

**Conventional commit:** `feat(graph): implement Critic node with hallucination risk scoring`

---

### T06 — Integration smoke test: full graph with mocked LLMs

**File:** `backend/tests/unit/graph/test_graph_integration.py`

**What:** Invoke the compiled graph end-to-end using real `AgentState` initial values, real `edges.py` conditional functions (not mocked), and mocked LLM/Qdrant calls. All five real node implementations must be active — no stubs.

**Required test cases:**

| # | Path name | Setup | Expected terminal state |
|---|-----------|-------|------------------------|
| 1 | Happy path | Factual query; all grader scores ≥ 0.5; `critic_score ≤ 0.7` | Graph reaches `END` in one pass |
| 2 | CRAG path | All grader scores < 0.5; `retry_count = 0` on first pass | Graph routes retriever → grader a second time; reaches `END` on second pass |
| 3 | Self-RAG path | `critic_score > 0.7`; `retry_count = 0` | Graph routes back to retriever after critic; reaches `END` on second pass |
| 4 | Max retry guard | Both grader and critic would fire indefinitely | Graph terminates after `MAX_RETRIES = 1`; does not loop |

**Acceptance criteria:**
- [ ] `test_graph_integration.py` — ≥ 4 test cases
- [ ] All 4 execution paths verified without real LLM or Qdrant calls
- [ ] pytest backend/tests/unit/ -q — all green
- [ ] mypy backend/src/ --strict — zero errors

**Conventional commit:** `test(graph): add end-to-end graph smoke tests for all routing paths`

---

## Phase 2c Gate Criteria

All of the following must be true before Phase 2d (Agentic API) begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | All 5 node files | No stub implementations remaining |
| G02 | mypy backend/src/ --strict | Zero errors |
| G03 | ruff check | Zero warnings |
| G04 | pytest backend/tests/unit/ -q | All green including ≥ 27 new node + edge + integration tests |
| G05 | No real LLM calls in unit tests | All external calls mocked |
| G06 | Error path coverage | Each node has ≥ 1 error-path test |
| G07 | `TAVILY_API_KEY` in `.env.example` | Present |
| G08 | System prompt reuse | Generator imports from Phase 1 module (no copy-paste) |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| GPT-4o-mini structured output fails to parse `RouterOutput` | Medium | Medium | Add retry with exponential backoff; fall back to default classification |
| Tavily SDK API shape changes (non-pinned transitive dep) | Low | Low | Pin `tavily-python` to exact version; wrap in an adapter function |
| Generator prompt context too long for GPT-4o context window | Low | High | Truncate `graded_docs` to top 5 by score; truncate chunk text to 500 tokens |
| LangGraph `state.messages` reducer conflicts with `messages` field name in LangChain | Low | Medium | Verify reducer is `add_messages` from `langgraph.graph.message`, not LangChain |
| Batched grader LLM call exceeds Azure OpenAI TPM limit | Low | Medium | Cap batch to 10 chunks max; add 1s delay between batches if needed |
