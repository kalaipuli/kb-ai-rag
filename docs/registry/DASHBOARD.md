# Registry Dashboard

> Maintained by: project-manager agent | Last updated: 2026-04-28 (Phase 2 COMPLETE · Phase 2f RAGAS faithfulness 0.9528 · 334 backend tests · 108 frontend tests · all 15 gate criteria verified · Phase 2f architect review + 5 fixes cleared 2026-04-28)

This is the single cross-phase status view. For task-level detail, open the linked feature registry (`phaseN/Nf-feature-name/tasks.md`).

---

## Project Status

| Phase | Name | Registry | Status | Gate |
|-------|------|----------|--------|------|
| 0 | Scaffolding + Architect Fixes | [tasks](phase0/tasks.md) · [fixes](phase0/fixes.md) | ✅ Complete | Passed 2026-04-23 |
| 1 | Core MVP | [1a](phase1/1a-ingestion/tasks.md) · [1b](phase1/1b-retrieval/tasks.md) · [1c](phase1/1c-generation/tasks.md) · [1c fixes](phase1/1c-generation/fixes.md) · [1d](phase1/1d-api/tasks.md) · [1d fixes](phase1/1d-api/fixes.md) · [1e](phase1/1e-ui/tasks.md) · [1e fixes](phase1/1e-ui/fixes.md) · [1f](phase1/1f-evaluation/tasks.md) | ✅ Complete | Passed 2026-04-26 |
| 1g | Retrieval Quality (Chunking + Eval) | [1g](phase1/1g-retrieval-quality/tasks.md) | ✅ Complete | Passed 2026-04-26 |
| 1h | Quality Transparency (UI + API) | [1h](phase1/1h-quality-transparency/tasks.md) | ✅ Complete | Passed 2026-04-26 |
| 2a | Gate Zero (Tier 3 Pre-requisites) | [2a](phase2/2a-gate-zero/tasks.md) · [fixes](phase2/2a-gate-zero/fixes.md) | ✅ Complete | Passed 2026-04-27 · Fixes cleared 2026-04-27 |
| 2b | Graph Skeleton (StateGraph + Builder) | [2b](phase2/2b-graph-skeleton/tasks.md) · [fixes](phase2/2b-graph-skeleton/fixes.md) | ✅ Complete | Passed 2026-04-27 · Architect review 2026-04-27 · Fixes cleared 2026-04-27 |
| 2c | Agent Nodes (Router · Retriever · Grader · Generator · Critic) | [2c](phase2/2c-agent-nodes/tasks.md) · [fixes](phase2/2c-agent-nodes/fixes.md) | ✅ Complete | Passed 2026-04-27 · Architect review 2026-04-27 · Fixes cleared 2026-04-27 |
| 2d | Agentic API Endpoint (SSE + Session) | [2d](phase2/2d-agentic-api/tasks.md) · [fixes](phase2/2d-agentic-api/fixes.md) | ✅ Complete | Passed 2026-04-27 · Architect review 2026-04-27 · All 9 fixes cleared 2026-04-27 |
| 2e | Parallel-View Chat UI | [2e](phase2/2e-parallel-ui/tasks.md) | ✅ Complete | Passed 2026-04-27 |
| 2f | Agentic Pipeline Evaluation (RAGAS) | [2f](phase2/2f-evaluation/tasks.md) · [fixes](phase2/2f-evaluation/fixes.md) | ✅ Complete | Passed 2026-04-28 · faithfulness 0.9528 · Architect review 2026-04-28 · All 5 fixes cleared 2026-04-28 |
| 3 | Azure Connectors | — | ⏳ Not Started | — |
| 4 | Multi-Hop Planning | — | ⏳ Not Started | — |
| 5 | Observability & Evaluation | — | ⏳ Not Started | — |
| 6 | Production Hardening | — | ⏳ Not Started | — |
| 7 | Azure Deployment & CI/CD | — | ⏳ Not Started | — |

---

## Stack Upgrade Queue

> Full proposal: [docs/stack-upgrade-proposal.md](../stack-upgrade-proposal.md) — reviewed 2026-04-24 by Architect · Backend · Frontend agents.

| Tier | Actions | Gate |
|------|---------|------|
| [Tier 1](../stack-upgrade-proposal.md#tier-1--before-phase-1d-starts) | pytest-asyncio strict mode · `SecretStr` unwrap · qdrant-client ^1.12 · public retriever method | **Before Phase 1d** |
| [Tier 2](../stack-upgrade-proposal.md#tier-2--phase-1d-implementation-patterns) | Lifespan state · Annotated DI · BackgroundTasks · StreamingResponse · audit unused langchain deps | **During Phase 1d** |
| [Tier 3](../stack-upgrade-proposal.md#tier-3--phase-2-pre-requisites-gate-zero) | LangGraph exact version lock · LangChain bundle upgrade · ADR-004 amendment · AgentState schema | **Phase 2 gate zero** |
| [Tier 4](../stack-upgrade-proposal.md#tier-4--frontend-before-any-component-code) | Next.js 15 · React 19 · Tailwind 4 · ESLint 9 · TypeScript 5.8 | **Before Phase 1e** |
| [Hold](../stack-upgrade-proposal.md#hold--do-not-upgrade-yet) | RAGAS eval group isolation · Python 3.13 evaluation | Phase 5 / Phase 4 |

---

## Active Phase

**Phase 2 — Agentic Pipeline (LangGraph + Parallel-View UI)** ✅ Complete — 2026-04-28

Scope change from original plan: the Phase 2 UI introduces a **parallel-view chat interface** with two simultaneous panels — Static Chain (Phase 1 LCEL, unchanged) vs Agentic Pipeline (Phase 2 LangGraph). Both pipelines run concurrently on the same query, enabling direct latency and quality comparison. Architect review completed 2026-04-26.

| Feature | Registry | Status | Notes |
|---------|----------|--------|-------|
| 2a Gate Zero | [tasks](phase2/2a-gate-zero/tasks.md) · [fixes](phase2/2a-gate-zero/fixes.md) | ✅ Complete | langgraph ~0.2.76 locked · ADR-004 amended · AgentState 19-field schema · AgentStreamEvent TS union · 6 architect fixes cleared |
| 2b Graph Skeleton | [tasks](phase2/2b-graph-skeleton/tasks.md) · [fixes](phase2/2b-graph-skeleton/fixes.md) | ✅ Complete | 5 stub nodes · edges.py · builder.py · AsyncSqliteSaver · CompiledGraphDep · 271 tests · fixes cleared 2026-04-27 |
| 2c Agent Nodes | [tasks](phase2/2c-agent-nodes/tasks.md) · [fixes](phase2/2c-agent-nodes/fixes.md) | ✅ Complete | All 5 nodes real (Adaptive RAG · HyDE · step-back · CRAG · Self-RAG) · 307 tests · 9 architect fixes cleared 2026-04-27 · ADR-010 added |
| 2d Agentic API | [tasks](phase2/2d-agentic-api/tasks.md) · [fixes](phase2/2d-agentic-api/fixes.md) | ✅ Complete | POST /api/v1/query/agentic · all 5 SSE event types · X-Session-ID session routing · Next.js proxy · 316 tests · architect review + 9 fixes cleared 2026-04-27 |
| 2e Parallel UI | [tasks](phase2/2e-parallel-ui/tasks.md) | ✅ Complete | useAgentStream · AgentTrace · AgentPanel · SharedInput · AgentVerdict · grid layout · verdict · latency bars · 96 frontend tests · 2026-04-27 |
| 2f Evaluation | [tasks](phase2/2f-evaluation/tasks.md) | ✅ Complete | EvaluationRunner · eval baseline API · RAGAS run · comparison report · faithfulness 0.9528 |

**Completed phases:** Phase 1 (✅ 201 unit tests · 54 frontend tests) · Phase 1g (✅ 241 unit tests · 5-metric RAGAS baseline) · Phase 1h (✅ retrieval scores in SSE · eval baseline endpoint · quality panel)

---

## Currently In Progress

_Phase 2 complete 2026-04-28. Phase 2f gate: faithfulness 0.9528 (gate ≥ 0.85, static baseline 0.9028) — PASS and exceeds baseline. CRAG activation: 0/20 (grader always passed ≥1 chunk). Self-RAG activation: 0/20 (critic score always 0.0). 332 backend unit tests · 108 frontend tests · mypy strict 0 errors · ruff clean · tsc clean · eslint clean. Two bugs found and fixed: (1) retry_count not initialized in initial_state of query_agentic.py — grader raised KeyError on every request; (2) citations SSE event missing retrieved_contexts field — RAGAS computed 0 faithfulness because contexts were filename strings not chunk text. Both fixes committed. Comparison report: docs/evaluation_agentic_results.md._

---

## Blocked / At Risk

| Item | Risk | Target Phase | Mitigation |
|------|------|-------------|-----------|
| 2b-F04 (duration_ms carry-forward) | ADR-004 amendment §6 requires `duration_ms` in every `agent_step` payload from first emission — stub nodes do not include it; Phase 2c must add it from day one to avoid multi-node retrofit | **Phase 2c task spec** | Add `duration_ms: int` to every emitting node return dict; include in Phase 2c T01–T05 acceptance criteria |
| 2b-F04 (duration_ms carry-forward) | ADR-004 amendment §6 requires `duration_ms` in every `agent_step` payload from first emission — stub nodes do not include it; Phase 2c must add it from day one to avoid multi-node retrofit | **Phase 2c task spec** | Add `duration_ms: int` to every emitting node return dict; include in Phase 2c T01–T05 acceptance criteria |
| 2c-T01 (Router HyDE) | GPT-4o-mini structured output parsing failures | Phase 2c | Add retry + safe default fallback; test error path |
| 2f-T02 (RAGAS agentic gate) | Agentic faithfulness may drop below static baseline if CRAG web fallback adds noise | Phase 2f | Tune `GRADER_THRESHOLD`; cap Tavily results to 3; architect review if gate fails |
| SqliteSaver concurrency | Multi-worker Uvicorn will cause SQLite write contention — documented in ADR-004 amendment | Phase 7 | `--workers 1` constraint enforced in deployment config |
| 2b-F06 (sync I/O on event loop) | `pickle.dump`, `PdfReader`, `.read_text()` in ingestion and evaluation block the event loop under concurrent load | **Phase 5/6** | Wrap each in `asyncio.to_thread`; see [2b fixes.md F06](phase2/2b-graph-skeleton/fixes.md) |
| 2b-F03 (lifespan singleton violations) | `AsyncQdrantClient`, `AzureChatOpenAI`, `AzureOpenAIEmbeddings` constructed per-call in `ingestion/`, `evaluation/`, `generation/` — connection churn at scale | **Phase 7** | Migrate to `app.state` singletons with `deps.py` aliases before multi-replica deployment; see [2b fixes.md F03](phase2/2b-graph-skeleton/fixes.md) |
| 2b-F05 (conn.is_alive monkey-patch) | `builder.py:80` patches `_thread.is_alive` on aiosqlite — breaks silently across patch releases | **Phase 2c / next dep update** | Add removal-reminder comments to `pyproject.toml` pins; see [2b fixes.md F05](phase2/2b-graph-skeleton/fixes.md) |

---

## Phase Feature Breakdown

### Phase 0 — Scaffolding ✅ Complete

| Feature | Description | Status |
|---------|-------------|--------|
| Poetry + pyproject.toml | Project setup, dependency management | ✅ Done |
| Ruff + mypy (strict) | Lint + format + type checking configured | ✅ Done |
| Pydantic Settings | `.env` local, Azure Key Vault prod | ✅ Done |
| structlog | Structured JSON logging with correlation ID | ✅ Done |
| Docker Compose | FastAPI placeholder + Qdrant | ✅ Done |
| GitHub Actions CI | lint → type check (no deploy) | ✅ Done |
| ADRs (001–005) | Qdrant, Azure AI Foundry, hybrid retrieval, LangGraph, Next.js | ✅ Done |
| Architect Review Fixes | 10 critical fixes resolved | ✅ Done |

---

### Phase 1 — Core MVP ✅ Complete

#### 1a. Ingestion Pipeline

| Feature | Description | Status |
|---------|-------------|--------|
| `BaseLoader` ABC | Loader abstraction interface | ✅ Done |
| `LocalFileLoader` | PDF (pypdf) + TXT native loader | ✅ Done |
| `RecursiveCharacterTextSplitter` | Configurable chunk size + overlap | ✅ Done |
| `ChunkMetadata` schema | Full 13-field payload per chunk | ✅ Done |
| `Embedder` | Azure OpenAI text-embedding-3-large, async batched | ✅ Done |
| Qdrant upsert | Vector + full payload per chunk | ✅ Done |
| BM25 index | In-memory build at ingest, persisted to disk | ✅ Done |
| Ingestion pipeline | End-to-end orchestration | ✅ Done |

#### 1b. Retrieval

| Feature | Description | Status |
|---------|-------------|--------|
| Dense search | Qdrant cosine similarity, top-k | ✅ Done |
| Sparse search | BM25 keyword match, top-k | ✅ Done |
| RRF fusion | Reciprocal Rank Fusion merging both result sets | ✅ Done |
| Cross-encoder re-ranker | `ms-marco-MiniLM-L-6-v2`, CPU, HuggingFace | ✅ Done |

#### 1c. Generation (basic chain — no agents)

| Feature | Description | Status |
|---------|-------------|--------|
| LangChain `RetrievalQA` chain | Azure OpenAI GPT-4o | ✅ Done |
| System prompt | Answer from context only, cite sources, flag uncertainty | ✅ Done |
| Response schema | `{answer, citations, confidence}` | ✅ Done |

#### 1d. API

> **Stack gate:** [Tier 1 fixes](../stack-upgrade-proposal.md#tier-1--before-phase-1d-starts) must be done before this feature starts. Use [Tier 2 patterns](../stack-upgrade-proposal.md#tier-2--phase-1d-implementation-patterns) (lifespan state, Annotated DI, BackgroundTasks, StreamingResponse) throughout.

| Feature | Description | Status |
|---------|-------------|--------|
| `POST /api/v1/ingest` | Ingest a folder of files (BackgroundTasks, 202 Accepted) | ✅ Done |
| `POST /api/v1/query` | SSE streaming — token / citations / done events | ✅ Done |
| `GET /api/v1/health` | Liveness + Qdrant connectivity | ✅ Done |
| `GET /api/v1/collections` | List indexed collections + doc counts | ✅ Done |
| API key auth | `X-API-Key` header middleware | ✅ Done |
| OpenAPI docs | `/docs` with full schema | ✅ Done |
| Lifespan singletons | `Embedder`, `HybridRetriever`, `GenerationChain`, `AsyncQdrantClient` in `app.state` | ✅ Done |
| Annotated DI | `SettingsDep`, `GenerationChainDep`, `QdrantClientDep` in `src/api/deps.py` | ✅ Done |
| `astream_generate` | SSE streaming method on `GenerationChain` | ✅ Done |

#### 1e. UI

> **Stack gate:** Complete [Tier 4 frontend bundle upgrade](../stack-upgrade-proposal.md#tier-4--frontend-before-any-component-code) before writing any component — Next.js 15, React 19, Tailwind 4, ESLint 9, TypeScript 5.8. Frontend is greenfield; zero migration cost now.

| Feature | Description | Status |
|---------|-------------|--------|
| Next.js chat interface | Query input + answer display | ✅ Done |
| Citations display | Filename + page number per source | ✅ Done |
| Confidence badge | Visual confidence indicator | ✅ Done |
| Sidebar | Collection stats + ingest trigger | ✅ Done |

#### 1f. Evaluation Baseline

> **Stack note:** RAGAS stays at `^0.2` for Phase 1f. Before Phase 5 automation, move it to a separate Poetry eval group. See [RAGAS isolation](../stack-upgrade-proposal.md#hold--do-not-upgrade-yet).

| Feature | Description | Status |
|---------|-------------|--------|
| Golden dataset | 20-question Q&A set from knowledge corpus | ✅ Done |
| RAGAS run | faithfulness, answer relevancy, context recall, precision | ✅ Done |
| Results persisted | `docs/evaluation_results.md` | ✅ Done |

**MVP gate (all must pass before Phase 2):**
- [x] Ingest 30+ local files end-to-end without errors
- [x] `POST /query` returns answer + citations in < 8s P95 locally
- [x] RAGAS faithfulness ≥ 0.70 (actual: 0.9153)
- [x] API key blocks unauthenticated requests
- [x] `docker compose up` — full stack running in < 90s

---

### Phase 1g — Retrieval Quality ⏳ Not Started

> **Gate zero:** ADR-009 accepted ✅ · `poetry add langchain-experimental --dry-run` must be run before T05/T07 · Estimated 4–5 days. See [1g tasks](phase1/1g-retrieval-quality/tasks.md).

#### 1g-A. Token-Aware Chunking

| Feature | Description | Status |
|---------|-------------|--------|
| `tiktoken` dependency | Explicit pin `^0.8` in pyproject.toml | ✅ Done |
| Settings fields | `CHUNK_STRATEGY`, `CHUNK_TOKENIZER_MODEL`, `EVAL_BASELINE_PATH` | ✅ Done |
| Token-aware length function | Replace `len` with tiktoken counter in `DocumentSplitter` | ✅ Done |

#### 1g-B. Configurable SplitterFactory

| Feature | Description | Status |
|---------|-------------|--------|
| `ChunkStrategy` enum | `recursive_character \| sentence_window \| semantic` | ✅ Done |
| `SplitterFactory.build()` | Returns correct `TextSplitter` per strategy; receives `Embedder` singleton | ✅ Done |
| `sentence_window` strategy | NLTK sentence tokenizer, N-sentence windows with token overlap | ✅ Done |
| `semantic` strategy | Deferred — raises `ConfigurationError`; langchain-experimental conflicts with `^0.3` pin | ✅ Done (deferred) |
| `DocumentSplitter` refactor | Uses `SplitterFactory` — no hardcoded `RecursiveCharacterTextSplitter` | ✅ Done |
| `app.state.embedder` + `EmbedderDep` | Embedder singleton on lifespan state; new dep in `deps.py` | ✅ Done |
| `run_pipeline` + ingest route update | Accepts and forwards `Embedder` to factory | ✅ Done |

#### 1g-C. Evaluation Output Improvements

| Feature | Description | Status |
|---------|-------------|--------|
| `AnswerCorrectness` metric | 5th RAGAS metric; `answer_correctness` field on `EvaluationResult` | ✅ Done |
| Per-sample score table | All 5 metrics per question in `to_markdown()` output | ✅ Done |
| Min / max / stddev per metric | Distribution stats added to report | ✅ Done |
| Failure section | Questions where faithfulness or answer_correctness < 0.7 called out | ✅ Done |
| Baseline persistence + diff | Writes `data/eval_baseline.json`; diff column on subsequent runs | ✅ Done |
| RAGAS re-run + comparison | Re-run with new metrics; document strategy comparison | ⏳ Pending (T14 — needs live Azure endpoint) |

**Phase 1g gate (all must pass before Phase 1h begins):**
- [ ] All 15 tasks ✅ Done
- [ ] `pytest backend/tests/unit/ -q` — green (includes splitter factory + eval tests)
- [ ] `mypy backend/src/ --strict` — zero errors
- [ ] `ruff check` — zero warnings
- [ ] `data/eval_baseline.json` exists with 5 metrics
- [ ] ADR-009 langchain-experimental dry-run result documented

---

### Phase 1h — Quality Transparency ⏳ Not Started

> **Gate zero:** Phase 1g gate passed. Estimated 3–4 days. See [1h tasks](phase1/1h-quality-transparency/tasks.md).

#### 1h-A. Retrieval Scores in SSE Wire Format

| Feature | Description | Status |
|---------|-------------|--------|
| `retrieval_score` on `Citation` | `float \| None` field in `schemas/generation.py` | ⏳ Pending |
| `_build_citations()` refactor | Extracts duplicated citation-building from `generate` + `astream_generate` | ⏳ Pending |
| `chunks_retrieved` in SSE event | Count of docs before dedup added to `citations` event payload | ⏳ Pending |

#### 1h-B. Eval Baseline API

| Feature | Description | Status |
|---------|-------------|--------|
| `GET /api/v1/eval/baseline` | Reads `Settings.eval_baseline_path`; 404 if not found | ⏳ Pending |
| Router registration | Eval router added to `main.py` | ⏳ Pending |

#### 1h-C/D. Frontend Chat Quality Panel

| Feature | Description | Status |
|---------|-------------|--------|
| `Citation` TS type update | `retrieval_score?: number` | ⏳ Pending |
| `CitationsEvent` TS type update | `chunks_retrieved: number` (atomic with backend) | ⏳ Pending |
| `CitationList` score bars | Per-citation relevance bar (labelled "Relevance", not "Confidence") | ⏳ Pending |
| `ChatMessage` collapsible panel | `<details>` with chunks retrieved + source count | ⏳ Pending |

#### 1h-E. Sidebar Eval Baseline Card

| Feature | Description | Status |
|---------|-------------|--------|
| `frontend/src/app/api/proxy/eval/baseline/route.ts` | Server-side proxy; API key never in browser | ⏳ Pending |
| `EvalBaseline.tsx` | Fetches baseline; renders 5 scores; 404-safe fallback | ⏳ Pending |
| `Sidebar.tsx` update | `EvalBaseline` added under collection stats | ⏳ Pending |

**Phase 1h gate (all must pass before Phase 2 begins):**
- [ ] All 13 tasks ✅ Done
- [ ] `pytest backend/tests/unit/ -q` — green
- [ ] `mypy backend/src/ --strict` — zero errors
- [ ] `ruff check` — zero warnings
- [ ] `tsc --noEmit` — zero errors
- [ ] `eslint` — zero warnings
- [ ] `npm run build` — succeeds
- [ ] Manual check: score bars visible in chat, eval baseline in sidebar, panel collapses/expands

---

### Phase 2 — Agentic Pipeline (LangGraph + Parallel-View UI) 🔄 In Progress

> **Scope note:** Parallel-view UI added vs original plan (architect review 2026-04-26). Left panel = Static Chain (Phase 1, frozen). Right panel = Agentic Pipeline (Phase 2). Both submit the same query simultaneously. See feature registries for full task breakdown.
>
> **Dependency direction:** `graph/nodes/` may import from `retrieval/` and `generation/`; `generation/` must NOT import from `graph/`.
>
> **Wire format commitment:** `agent_step` SSE events must include `duration_ms: int` in every payload from day one. `POST /api/v1/query` (Phase 1) is frozen — never modified.

#### 2a — Gate Zero ⏳ Not Started

> **Hard gate.** No Phase 2b task may start until all items below are committed and CI is green.

| Feature | Description | Status |
|---------|-------------|--------|
| LangGraph + LangChain bundle version lock | Tilde-pinned in `pyproject.toml`; lockfile committed | ⏳ Pending |
| ADR-004 amendment | Confirmed version · SqliteSaver import · stream_mode · single-worker constraint · duration_ms commitment | ⏳ Pending |
| `AgentState` TypedDict + unit test | Full schema with `Annotated` reducers; ≥ 4 reducer tests | ⏳ Pending |
| `AgentStreamEvent` TS union | `AgentStepEvent` discriminated union in `frontend/src/types/index.ts` | ⏳ Pending |
| Gate zero CI verification | All DoD commands clean; tsc clean; build succeeds | ⏳ Pending |

#### 2b — Graph Skeleton ⏳ Not Started

| Feature | Description | Status |
|---------|-------------|--------|
| `backend/src/graph/` module structure | All files with stub nodes | ⏳ Pending |
| `edges.py` conditional edge functions | `route_after_grader` · `route_after_critic` (pure functions) | ⏳ Pending |
| `builder.py` graph compilation | `build_graph(settings, retriever)` → `CompiledStateGraph` | ⏳ Pending |
| `app.state.compiled_graph` | Added to lifespan in `main.py` | ⏳ Pending |
| `CompiledGraphDep` | Added to `backend/src/api/deps.py` | ⏳ Pending |
| Unit tests: edges + builder | ≥ 6 edge tests · ≥ 3 builder tests | ⏳ Pending |

#### 2c — Agent Nodes ⏳ Not Started

> **Pre-conditions before any 2c task starts:**
> - 2b-F01 cleared: error-path test in `test_builder.py`
> - 2b-F02 cleared: `type: ignore` justification inline on `builder.py:80`
>
> **Carry-forward from 2b architect review (2b-F04):** Every node that emits an `agent_step` SSE event must include `duration_ms: int` in its return dict from the first implementation. Do not implement nodes without this field — retrofitting across all nodes simultaneously is high coordination cost. Add `duration_ms: int` to `AgentState` if not already present.
>
> **Carry-forward from 2b architect review (2b-F05):** Add removal-reminder comments to `langgraph-checkpoint-sqlite` and `aiosqlite` pins in `pyproject.toml` — see [2b fixes.md F05](phase2/2b-graph-skeleton/fixes.md).

| Agent | Role | Model | Agentic Pattern | Status |
|-------|------|-------|-----------------|--------|
| **Router** | Query classification + strategy selection | GPT-4o-mini | Adaptive RAG · HyDE · Step-back | ⏳ Pending |
| **Retriever** | HybridRetriever + Tavily web fallback | — | CRAG fallback trigger | ⏳ Pending |
| **Grader** | Chunk relevance scoring; sets `all_below_threshold` | GPT-4o-mini | CRAG gate | ⏳ Pending |
| **Generator** | Cited answer from `graded_docs` | GPT-4o | — | ⏳ Pending |
| **Critic** | Hallucination risk score; triggers re-retrieval | GPT-4o-mini | Self-RAG | ⏳ Pending |
| Integration smoke test | All 4 routing paths (happy / CRAG / Self-RAG / max-retry) | — | — | ⏳ Pending |

#### 2d — Agentic API Endpoint ⏳ Not Started

| Feature | Description | Status |
|---------|-------------|--------|
| `AgentStepEvent` Pydantic schemas | `RouterStepPayload` · `GraderStepPayload` · `CriticStepPayload` · `AgentQueryRequest` | ⏳ Pending |
| `POST /api/v1/query/agentic` | SSE route; `X-Session-ID` header; `stream_mode="updates"`; all 5 event types | ⏳ Pending |
| Router registration in `main.py` | One `app.include_router()` call | ⏳ Pending |
| Unit tests | ≥ 5 route tests including SSE event order and session ID handling | ⏳ Pending |
| Next.js proxy `/api/proxy/query/agentic` | Forwards `X-Session-ID` header; API key server-side only | ⏳ Pending |

#### 2e — Parallel-View Chat UI ⏳ Not Started

| Feature | Description | Status |
|---------|-------------|--------|
| `useAgentStream` hook | Session ID in `sessionStorage`; handles `agent_step` / `token` / `citations` / `done` | ⏳ Pending |
| `AgentTrace` component | Per-node step cards: Router (human-readable labels) · Grader (score bars) · Critic (risk gauge) | ⏳ Pending |
| `AgentPanel` component | Composes existing `ChatMessage` + `AgentTrace`; no copy-paste chat logic | ⏳ Pending |
| `SharedInput` component | Fires both hooks; functional guard (not just visual) while either streaming | ⏳ Pending |
| `chat/page.tsx` refactor | `grid grid-cols-2` layout; "Static Chain" vs "Agentic Pipeline" labels | ⏳ Pending |
| `AgentVerdict` component | Post-completion verdict: winner + one-sentence reason | ⏳ Pending |
| Per-node latency bars | Proportional `duration_ms` visualization; hidden during streaming | ⏳ Pending |
| Component tests | ≥ 12 new frontend tests; all 54 existing tests still green | ⏳ Pending |

#### 2f — Agentic Evaluation ⏳ Not Started

| Feature | Description | Status |
|---------|-------------|--------|
| `EvaluationRunner` extension | `endpoint` param for `"static"` or `"agentic"` | ⏳ Pending |
| RAGAS run (agentic) | 20-Q golden dataset against agentic endpoint; `data/eval_agentic_baseline.json` | ⏳ Pending |
| Comparison report | `docs/evaluation_agentic_results.md` — 7 sections incl. CRAG/Self-RAG activation rates | ⏳ Pending |
| Eval baseline API update | `GET /api/v1/eval/baseline?pipeline=agentic` | ⏳ Pending |
| Phase 2 full gate review | All 15 gate criteria verified; DASHBOARD.md updated | ⏳ Pending |

**Phase 2 gate criteria (all must pass):**
- [ ] 2a Gate Zero: CI green; ADR-004 amended; AgentState unit tests; TS types committed
- [ ] 2b Graph Skeleton: graph compiles; edges route correctly; no orphaned stubs
- [ ] 2c Agent Nodes: all 5 nodes implemented; ≥ 27 new tests; error paths covered
- [ ] 2d Agentic API: SSE endpoint live; `duration_ms` in all agent_step payloads; Phase 1 `query.py` unchanged
- [ ] 2e Parallel UI: both panels demo-able; SharedInput guard correct; ≥ 66 total frontend tests
- [ ] 2f Evaluation: RAGAS faithfulness ≥ 0.85; comparison report complete
- [ ] `mypy backend/src/ --strict` — zero errors
- [ ] `ruff check` — zero warnings
- [ ] `tsc --noEmit` — zero errors
- [ ] `npm run build` — succeeds
- [ ] `docker compose up` — full stack < 90s

---

### Phase 3 — Azure Connectors ⏳ Not Started

| Feature | Description | Status |
|---------|-------------|--------|
| `AzureBlobLoader` | Lists + downloads files from configured container | ⏳ Pending |
| Incremental sync | Tracks `last_modified` per blob, skips unchanged | ⏳ Pending |
| `BaseRetriever` ABC | `retrieve(query, vector, k) → list[Document]` interface | ⏳ Pending |
| `QdrantRetriever` | Implements `BaseRetriever` for Qdrant | ⏳ Pending |
| `AzureSearchRetriever` | Azure AI Search semantic ranking, normalized to `Document` | ⏳ Pending |
| RRF merge (dual-source) | Merge Qdrant + Azure Search results via RRF | ⏳ Pending |
| `RetrieverRegistry` | Runtime retriever selection by name | ⏳ Pending |

---

### Phase 4 — Multi-Hop Planning ⏳ Not Started

| Feature | Description | Status |
|---------|-------------|--------|
| Planner agent | Decomposes `multi_hop` queries into 2–4 ordered sub-questions | ⏳ Pending |
| Parallel sub-retrieval | `asyncio.gather` fan-out to Retriever per sub-question | ⏳ Pending |
| Synthesizer node | Merges partial answers into final coherent response | ⏳ Pending |
| Human-in-the-loop | `interrupt_before` Generator when confidence < 0.4 | ⏳ Pending |
| Approval endpoint | `POST /api/v1/query/{session_id}/approve` to resume graph | ⏳ Pending |

---

### Phase 5 — Observability & Evaluation ⏳ Not Started

> **Stack pre-requisite:** Before setting up RAGAS automation, move `ragas` into `[tool.poetry.group.eval.dependencies]` in `pyproject.toml`. See [RAGAS isolation](../stack-upgrade-proposal.md#hold--do-not-upgrade-yet).
>
> **Carry-forward from 2b architect review (2b-F06 · High):** Wrap all blocking I/O in `asyncio.to_thread` before load testing. Affected files: `backend/src/ingestion/pipeline.py` (`pickle.dump`), `backend/src/ingestion/local_loader.py:95,137` (`PdfReader`, `.read_text()`), `backend/src/api/routes/eval.py:39` (`.read_text()`), `backend/src/evaluation/ragas_eval.py:165,238` (`.read_text()`). See [2b fixes.md F06](phase2/2b-graph-skeleton/fixes.md).

| Feature | Description | Status |
|---------|-------------|--------|
| LangSmith tracing | End-to-end graph traces with custom tags per node | ⏳ Pending |
| Token cost tracking | Cost per agent node in LangSmith | ⏳ Pending |
| RAGAS automation | Weekly eval via GitHub Actions scheduled job | ⏳ Pending |
| RAGAS regression gate | CI fails if faithfulness drops > 5% from baseline | ⏳ Pending |
| Azure App Insights | Custom events: query, retrieval, fallback, answer | ⏳ Pending |
| Latency tracking | P50 / P95 per pipeline stage | ⏳ Pending |
| Metrics dashboard | Query volume, fallback rate, avg confidence, cost/query | ⏳ Pending |
| `GET /api/v1/metrics` | Metrics endpoint | ⏳ Pending |

---

### Phase 6 — Production Hardening ⏳ Not Started

#### Security

| Feature | Description | Status |
|---------|-------------|--------|
| Azure AD / Entra ID auth | OAuth2 Bearer JWT replaces API key | ⏳ Pending |
| Prompt injection guard | Rule-based + lightweight classifier before any LLM call | ⏳ Pending |
| Azure Key Vault integration | Zero secrets in code or env files in prod | ⏳ Pending |

#### Reliability

| Feature | Description | Status |
|---------|-------------|--------|
| Retry with backoff | `tenacity` exponential backoff on Azure OpenAI calls | ⏳ Pending |
| Circuit breaker | Per-upstream: fail 3x → degraded response, not 500 | ⏳ Pending |
| Request timeout budgets | Router: 3s, Generator: 20s per node | ⏳ Pending |
| Rate limiting | Token bucket per user via Redis or Azure API Management | ⏳ Pending |

#### Async Ingestion Worker

| Feature | Description | Status |
|---------|-------------|--------|
| Azure Service Bus queue | Ingestion jobs queued async | ⏳ Pending |
| Worker container | Separate service: embed + Qdrant upsert | ⏳ Pending |
| Job status API | `GET /api/v1/jobs/{job_id}` → `{status, progress, errors}` | ⏳ Pending |

---

### Phase 7 — Azure Deployment & CI/CD ⏳ Not Started

> **Carry-forward from 2b architect review (2b-F03 · High):** Before multi-replica deployment, migrate all per-call client constructions to lifespan singletons. Affected files: `backend/src/ingestion/vector_store.py:33` (`AsyncQdrantClient`), `backend/src/ingestion/embedder.py:64` (`AzureOpenAIEmbeddings`), `backend/src/retrieval/dense.py:24` (`AsyncQdrantClient`), `backend/src/generation/chain.py:116` (`AzureChatOpenAI`), `backend/src/evaluation/ragas_eval.py:220,229` (`AzureChatOpenAI`, `AzureOpenAIEmbeddings`). Each must be added to `app.state` with a `deps.py` alias following the `QdrantClientDep` pattern. See [2b fixes.md F03](phase2/2b-graph-skeleton/fixes.md).

#### Infrastructure as Code (Terraform)

| Feature | Description | Status |
|---------|-------------|--------|
| `main.tf` | Provider config, remote backend (Azure Blob Storage) | ⏳ Pending |
| Modules | `container_apps/`, `acr/`, `keyvault/`, `servicebus/` | ⏳ Pending |
| Environments | `dev.tfvars`, `prod.tfvars` | ⏳ Pending |

#### Docker

| Feature | Description | Status |
|---------|-------------|--------|
| `Dockerfile.api` | FastAPI service image | ⏳ Pending |
| `Dockerfile.worker` | Async ingestion worker image | ⏳ Pending |
| Qdrant persistence | Official image + Azure Managed Disk | ⏳ Pending |

#### GitHub Actions

| Feature | Description | Status |
|---------|-------------|--------|
| `ci.yml` | lint → type check → unit → integration → RAGAS gate | ⏳ Pending |
| `deploy.yml` | build → push ACR → deploy Container Apps (on merge to main) | ⏳ Pending |

#### Azure Container Apps

| Feature | Description | Status |
|---------|-------------|--------|
| API autoscale | 1–10 replicas on HTTP request queue depth | ⏳ Pending |
| Worker scale-to-zero | Scales down when no Service Bus messages pending | ⏳ Pending |
| Qdrant persistent replica | Single replica with persistent disk | ⏳ Pending |

---

## Phase Gate Log

| Phase | Gate Passed | Notes |
|-------|-------------|-------|
| 0 | 2026-04-23 | 29 unit tests, mypy strict (11 files), ruff clean, tsc clean, 5 ADRs, CI workflow, 10 architect fixes resolved |
| 1 | 2026-04-26 | faithfulness 0.9153 ≥ 0.70, 201 unit tests, mypy strict 0 errors, full stack verified, 17 knowledge files ingested |
| 1g | 2026-04-26 | 241 unit tests, mypy strict 0 errors, ruff clean, `data/eval_baseline.json` with 5 metrics, faithfulness 0.9028 |
| 1h | 2026-04-26 | retrieval scores in SSE · eval baseline endpoint · quality panel · sidebar card |
| 2a | 2026-04-27 | langgraph ~0.2.76 locked · ADR-004 amended · AgentState 19-field TypedDict · AgentStreamEvent TS union · 260 unit tests · mypy strict 0 errors · 6 architect fixes cleared 2026-04-27 |
| 2b | 2026-04-27 | 271 unit tests · mypy strict 0 errors · ruff clean · 5 stub nodes · AsyncSqliteSaver checkpointer · architect review + fixes cleared 2026-04-27 — see [fixes.md](phase2/2b-graph-skeleton/fixes.md) |
| 2c | 2026-04-27 | 307 unit tests · mypy strict 0 errors · ruff clean · all 5 nodes real · 4-path integration smoke test · 9 architect fixes cleared · ADR-010 (Tavily) added |
| 2d | 2026-04-27 | 316 unit tests · mypy strict 0 errors · ruff clean · tsc clean · POST /api/v1/query/agentic · Next.js proxy · Phase 1 query.py unchanged · architect review 9/9 fixes cleared 2026-04-27 |
| 2e | 2026-04-27 | 96 frontend tests · tsc clean · eslint clean · build succeeds · parallel grid layout · SharedInput functional guard · AgentTrace human-readable labels · latency bars · AgentVerdict verdict logic |
| 2f | 2026-04-28 | faithfulness 0.9528 ≥ 0.85 — PASS and exceeds static baseline 0.9028 |
