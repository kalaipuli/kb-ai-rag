# Enterprise Agentic Knowledge Base — AI RAG Platform
### Project Plan | Phased Delivery | MVP-First

> See [GOAL.md](GOAL.md) for the "why" behind every decision in this plan.
> Stack versions, upgrade schedule, and implementation patterns: [Stack Upgrade Proposal](docs/stack-upgrade-proposal.md).

---

## Confirmed Decisions

| Decision | Choice | Notes |
|----------|--------|-------|
| Data sources (MVP) | Local filesystem (PDF, TXT) | Docker volume mount |
| Data sources (prod) | Azure Blob Storage | Same ingestion pipeline, different loader |
| Vector DB | Qdrant (self-hosted Docker) | Open source, hybrid search native |
| Relational DB | None | Semantic search only via Qdrant |
| LLM | Azure OpenAI GPT-4o | ⚠️ Requires Azure OpenAI deployment — see open questions |
| Embeddings | Azure OpenAI text-embedding-3-large | ⚠️ Same dependency |
| Orchestration | LangGraph | Stateful agent graphs with conditional routing |
| RAG framework | LangChain | Loaders, splitters, tools |
| Deployment (MVP) | Docker Compose (local) | Full stack: API + Qdrant + UI |
| Deployment (prod) | Azure Container Apps | Terraform IaC |
| Language | Python 3.12 | Full type hints, mypy strict — see [upgrade proposal](docs/stack-upgrade-proposal.md) for version lock schedule |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│             Next.js UI    │  FastAPI REST  │  CLI           │
└─────────────────────────────────────────────────────────────┘
                                │
                         API Key Auth
                                │
┌─────────────────────────────────────────────────────────────┐
│              Agentic Orchestration — LangGraph              │
│                                                             │
│   ┌────────┐  ┌───────────┐  ┌────────┐  ┌─────────────┐  │
│   │ Router │→ │ Retriever │→ │ Grader │→ │  Generator  │  │
│   └────────┘  └───────────┘  └────────┘  └─────────────┘  │
│        │                          │              │          │
│   [query type]              [poor quality]  ┌────────┐     │
│        │                          ↓         │ Critic │     │
│   [strategy]              Web Search        └────────┘     │
│                           (Tavily)          [hallucination?]│
│                                             ↓              │
│                                      re-retrieve or return  │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Retrieval Layer                           │
│                                                             │
│  Qdrant (dense)  +  BM25 (sparse)  →  RRF Fusion           │
│                          ↓                                  │
│               Cross-encoder Re-ranker                       │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Data Source Layer                         │
│                                                             │
│  MVP: Local Filesystem (PDF, TXT)                          │
│  Prod: Azure Blob Storage (PDF, TXT)                        │
│  Phase 3+: Azure AI Search (enterprise index)              │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                     Azure Platform                          │
│                                                             │
│  Azure OpenAI  │  Azure Blob  │  Azure Container Apps      │
│  GPT-4o + Ada  │  Storage     │  API + Qdrant + Worker     │
│  Azure Monitor │  Key Vault   │  Container Registry        │
└─────────────────────────────────────────────────────────────┘
```

---

## Phased Delivery

---

### Phase 0 — Scaffolding (Days 1–2)
**Goal:** Working skeleton. No LLM calls yet. Every future phase builds on this.

**Deliverables:**
- Poetry project setup with `pyproject.toml`
- Ruff (lint + format) + mypy (strict type checking) configured
- Pydantic Settings: reads from `.env` locally, Azure Key Vault in prod
- Structured JSON logging with `structlog` (correlation ID per request)
- Docker Compose: FastAPI (placeholder) + Qdrant
- GitHub Actions CI: lint → type check (no deploy yet)
- `docs/adr/` folder with first ADR (001: why Qdrant)

**Done when:** `docker compose up` runs, `/health` returns 200, CI passes.

---

### Phase 1 — Core MVP (Days 3–8)
**Goal:** End-to-end RAG: ingest local files → embed → retrieve → answer. Demo-able.

#### 1a. Ingestion Pipeline
- **Loader abstraction:** `BaseLoader` ABC with `LocalFileLoader` (PDF via `pypdf`, TXT native)
- **Chunking:** `RecursiveCharacterTextSplitter` with configurable chunk size + overlap
- **Metadata per chunk:**
  ```
  doc_id, chunk_id, source_path, filename, file_type, title,
  page_number, chunk_index, total_chunks, char_count, ingested_at, tags
  # domain field is intentionally absent — see CLAUDE.md domain-agnostic retrieval rule and ADR-003
  ```
- **Embedder:** Azure OpenAI `text-embedding-3-large` (async batched calls)
- **Qdrant upsert:** vector + full payload stored per chunk
- **BM25 index:** built in-memory from same chunks at ingestion time, persisted to disk

#### 1b. Retrieval
- **Dense search:** Qdrant cosine similarity, top-k chunks
- **Sparse search:** BM25 keyword match, top-k chunks
- **Hybrid fusion:** Reciprocal Rank Fusion (RRF) merging both result sets
- **Re-ranker:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (HuggingFace, CPU, no GPU needed)

#### 1c. Generation (basic chain — no agents yet)
- LangChain `RetrievalQA` chain with Azure OpenAI GPT-4o
- System prompt enforces: answer only from context, cite sources, flag if unsure
- Response schema: `{answer, citations: [{filename, chunk_index, score}], confidence}`

#### 1d. API

> **Stack pre-requisite:** Complete [Tier 1 immediate fixes](docs/stack-upgrade-proposal.md#tier-1--before-phase-1d-starts) before writing any 1d code (pytest-asyncio strict mode, `SecretStr` unwrap, qdrant-client bump, public retriever method). Apply [Tier 2 implementation patterns](docs/stack-upgrade-proposal.md#tier-2--phase-1d-implementation-patterns) throughout (lifespan state, `Annotated` deps, `BackgroundTasks`, `StreamingResponse`).

- `POST /api/v1/ingest` — ingest a folder of files
- `POST /api/v1/query` — query the knowledge base
- `GET /api/v1/health` — liveness + Qdrant connectivity check
- `GET /api/v1/collections` — list indexed collections and document counts
- API key auth via `X-API-Key` header
- Full OpenAPI docs at `/docs`

#### 1e. UI

> **Stack pre-requisite:** Before writing the first component, complete the [Tier 4 frontend bundle upgrade](docs/stack-upgrade-proposal.md#tier-4--frontend-before-any-component-code): Next.js 15 + React 19 + Tailwind 4 + ESLint 9 + TypeScript 5.8. The frontend is greenfield — zero migration cost at this point, significant cost after.

- Next.js chat interface
- Displays answer, citations (filename + page), confidence badge
- Sidebar: collection stats, ingest trigger

#### 1f. Evaluation Baseline

> **Note:** RAGAS stays at `^0.2` for Phase 1f. Before Phase 5 automation is set up, move it into an isolated Poetry eval group — see [RAGAS isolation](docs/stack-upgrade-proposal.md#hold--do-not-upgrade-yet).

- Create 20-question golden dataset from the knowledge article corpus
- Run RAGAS: faithfulness, answer relevancy, context recall, context precision
- Persist results to `docs/evaluation_results.md`

**MVP gate (must pass before Phase 2):**
- [ ] Ingest 30+ local files end-to-end without errors
- [ ] `POST /query` returns answer + citations in < 8s P95 locally
- [ ] RAGAS faithfulness ≥ 0.70
- [ ] API key blocks unauthenticated requests
- [ ] `docker compose up` — full stack running in < 90s

---

### Phase 2 — Agentic Pipeline + Parallel-View UI (Days 9–20)
**Goal:** Replace static chain with LangGraph agent graph. The system now reasons, not just retrieves. A side-by-side UI lets users compare Static Chain vs Agentic Pipeline on the same query.

> **Scope change (2026-04-26):** Original plan had a single chat UI. Phase 2 now introduces a **parallel-view chat interface**: Left panel = Static Chain (Phase 1 LCEL, frozen), Right panel = Agentic Pipeline (Phase 2 LangGraph). Both pipelines submit the same query simultaneously. Architect review completed 2026-04-26. See [registry](docs/registry/phase2/) for full task breakdown.
>
> **Dependency direction (enforced):** `graph/nodes/` may import from `retrieval/` and `generation/`; `generation/` must NEVER import from `graph/`. `POST /api/v1/query` (Phase 1) is frozen — never modified.

#### 2a — Gate Zero (Tier 3 Pre-requisites)

> **Hard gate.** No Phase 2b code begins until all four items are committed and CI is green.

- **LangGraph + LangChain bundle version lock** — tilde-pinned (`~major.minor.patch`), not caret. Verify `StateGraph`, `add_conditional_edges`, `CompiledStateGraph.astream()`, and `SqliteSaver` import path against confirmed version before writing any node.
- **ADR-004 amendment** — append to `docs/adr/004-langgraph-vs-chain.md`: confirmed version, SqliteSaver import path, `stream_mode="updates"` decision, single-writer constraint (`--workers 1` for Phase 2; `PostgresSaver` for Phase 7), `X-Session-ID` header contract, `duration_ms` commitment.
- **`AgentState` TypedDict** — defined in `backend/src/graph/state.py` before any node. All fields + `Annotated` reducers for `retrieved_docs` (operator.add), `messages` (add_messages), `steps_taken` (operator.add). Unit tested (≥ 4 reducer tests).
- **`AgentStreamEvent` TypeScript union** — `AgentStepEvent` discriminated union added to `frontend/src/types/index.ts` before any hook or component.

#### 2b — Graph Skeleton (StateGraph + Builder)

All stub nodes first — proves topology and wiring before any LLM logic:
- `backend/src/graph/` module with stub node functions (return hardcoded partial state — not `NotImplementedError`)
- `edges.py` — `route_after_grader` and `route_after_critic` (pure functions, no LLM, fully unit tested)
- `builder.py` — `build_graph(settings, retriever) → CompiledStateGraph`; injects retriever singleton via closure
- `app.state.compiled_graph` added to lifespan in `main.py`; `CompiledGraphDep` added to `deps.py`
- New Settings field: `SQLITE_CHECKPOINTER_PATH` (default: `data/checkpointer.sqlite`)

#### 2c — Agent Nodes

> **Pre-conditions — must be done before any 2c code is written:**
> - **2b-F01 cleared:** add error-path test in `backend/tests/unit/graph/test_builder.py` for `aiosqlite.connect` failure
> - **2b-F02 cleared:** move `type: ignore[attr-defined]` justification inline on `backend/src/graph/builder.py:80`
>
> **Carry-forward from 2b architect review:**
> - **2b-F04 (High):** Every node that emits an `agent_step` SSE event must include `duration_ms: int` in its return dict from the first implementation — add `duration_ms: int` to `AgentState` if not already present. Do not implement nodes without this field; retrofitting all nodes simultaneously creates high coordination cost and a wire format version bump.
> - **2b-F05 (Minor):** Add removal-reminder comments to `langgraph-checkpoint-sqlite` and `aiosqlite` pins in `pyproject.toml` (see [2b fixes.md F05](docs/registry/phase2/2b-graph-skeleton/fixes.md)).

```
AgentState flow:
START → Router → Retriever → Grader → Generator → Critic → END
                    ↑           |                    |
                    └───────────┘ (CRAG web fallback) └──── (Self-RAG re-retrieve)
```

| Agent | LLM | Agentic Pattern | Key Output Fields |
|-------|-----|-----------------|-------------------|
| **Router** | GPT-4o-mini | Adaptive RAG · HyDE · Step-back | `query_type`, `retrieval_strategy`, `query_rewritten` |
| **Retriever** | None | CRAG trigger | `retrieved_docs` (append reducer), `web_fallback_used` |
| **Grader** | GPT-4o-mini | CRAG gate | `grader_scores`, `graded_docs`, `all_below_threshold`, `retry_count` |
| **Generator** | GPT-4o | — | `answer`, `citations`, `confidence`, appends to `messages` |
| **Critic** | GPT-4o-mini | Self-RAG | `critic_score` (hallucination risk [0–1]) |

- **Adaptive RAG**: Router classifies `query_type` and sets `retrieval_strategy` accordingly
- **HyDE**: For `analytical` queries, Router generates a hypothetical document, stores in `query_rewritten`
- **Step-back prompting**: For `multi_hop` queries, Router rewrites to more general form
- **CRAG**: If all `grader_scores < 0.5` and `retry_count < 1`, edge routes back to Retriever with Tavily web search
- **Self-RAG**: If `critic_score > 0.7` and `retry_count < 1`, edge routes back to Retriever with refined query
- **Max retry guard**: `MAX_RETRIES = 1` enforced in edge functions (not nodes)
- Cost discipline: GPT-4o only for Generator (quality-critical); GPT-4o-mini for all classification/scoring nodes

#### 2d — Agentic API Endpoint

- **New endpoint: `POST /api/v1/query/agentic`** — separate from existing `POST /api/v1/query` (frozen)
- **`X-Session-ID` header** — read from request headers, not body; passed as `config={"configurable": {"thread_id": session_id}}`
- **SSE wire format** (new event types — additive, existing format unchanged):
  ```
  {"type": "agent_step", "node": "router", "payload": {"query_type": "...", "strategy": "...", "duration_ms": 142}}
  {"type": "agent_step", "node": "grader", "payload": {"scores": [...], "web_fallback": false, "duration_ms": 380}}
  {"type": "agent_step", "node": "critic", "payload": {"hallucination_risk": 0.31, "reruns": 0, "duration_ms": 210}}
  {"type": "token", "content": "..."}
  {"type": "citations", "citations": [...], "confidence": 0.87, "chunks_retrieved": 5}
  {"type": "done"}
  ```
- **`duration_ms` in every `agent_step` payload** — day-one commitment; retrofitting requires wire format version bump
- **Next.js proxy** — `/api/proxy/query/agentic/route.ts` forwards `X-Session-ID` header; API key stays server-side

#### 2e — Parallel-View Chat UI

The UI is the portfolio demonstration surface for the Phase 2 decision.

**Layout:** `grid grid-cols-2` — "Static Chain" (left, existing components) vs "Agentic Pipeline" (right, new `AgentPanel`)

**New components:**
- `useAgentStream` hook — parallel to `useStream`; manages `sessionId` in `sessionStorage`; handles `agent_step` events by appending to `AgentMessage.agentSteps`
- `AgentTrace` — per-node step cards: Router (human-readable query type + strategy badges), Grader (score bars, web fallback indicator), Critic (color-coded hallucination risk gauge: green/amber/red)
- `AgentPanel` — composes existing `ChatMessage`, `CitationList`, `ConfidenceBadge` + new `AgentTrace`
- `SharedInput` — fires both hooks simultaneously; **functional guard** (not just visual) blocks submit while either stream active
- `AgentVerdict` — post-completion: compares static `confidence` vs agentic `critic_score`; one-sentence verdict
- Per-node latency bars — proportional `duration_ms` visualization; hidden during streaming

**Correctness constraint:** `SharedInput.onSubmit` must be a no-op (not just disabled) while `staticStreaming || agentStreaming`. Concurrent submission to same `session_id` SqliteSaver thread causes write corruption.

**UX labels:** Router payload mapped to human-readable strings — `"factual"` → `"Direct fact lookup"`, `"multi_hop"` → `"Multi-step reasoning"`, `"ambiguous"` → `"Needs clarification"`.

#### 2f — Agentic Pipeline Evaluation

- RAGAS re-run against `POST /api/v1/query/agentic` using the same 20-question golden dataset
- New output: `data/eval_agentic_baseline.json` (same schema as static baseline)
- Phase 2 gate: faithfulness ≥ 0.85; no regression below static chain baseline (0.9028)
- `GET /api/v1/eval/baseline?pipeline=agentic` — new query param on existing endpoint
- Comparison report: `docs/evaluation_agentic_results.md` — CRAG/Self-RAG activation rates, per query type breakdown, latency impact

**Phase 2 gate (all must pass):**
- [ ] 2a: LangGraph version locked · ADR-004 amended · AgentState unit tests green · TS types committed
- [ ] 2b: Graph compiles · edge tests green · no orphaned stubs
- [ ] 2c: All 5 nodes implemented · ≥ 27 new tests · all error paths covered
- [ ] 2d: SSE endpoint live · `duration_ms` in all agent_step payloads · `query.py` unchanged
- [ ] 2e: Both panels demo-able · SharedInput guard correct · ≥ 66 total frontend tests
- [ ] 2f: RAGAS faithfulness ≥ 0.85 · comparison report complete
- [ ] `mypy backend/src/ --strict` · `ruff check` · `tsc --noEmit` — all zero errors/warnings
- [ ] `npm run build` · `docker compose up` — succeed

---

### Phase 3 — Azure Blob + Enterprise Connector (Days 17–21)
**Goal:** Swap local file loader for Azure Blob. Add Azure AI Search as a second retrieval source.

#### Azure Blob Loader
- `AzureBlobLoader`: lists and downloads files from a configured container
- Same chunking + embedding pipeline as Phase 1 — only the source changes
- Incremental sync: tracks `last_modified` per blob, skips unchanged files
- Config: `AZURE_STORAGE_ACCOUNT`, `AZURE_STORAGE_CONTAINER` from Key Vault

#### Connector Abstraction (introduced here)
```python
class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(self, query: str, query_vector: list[float], k: int) -> list[Document]: ...
```
Implementations: `QdrantRetriever`, `AzureSearchRetriever`

#### Azure AI Search Connector
- Connects to an existing or newly created Azure AI Search index
- Semantic search mode using Azure's built-in semantic ranking
- Normalizes Azure Search results to internal `Document` schema
- Merged with Qdrant results via RRF

#### RetrieverRegistry
- Agents select retriever by name at runtime: `registry.get("qdrant")`, `registry.get("azure_search")`
- Router decides which sources to query based on query type and configured domains

---

### Phase 4 — Multi-Hop Planning (Days 22–26)
**Goal:** Handle complex questions that require decomposition and parallel sub-retrieval.

> **Stack note:** Evaluate Python `^3.13` bump at this phase — the `sentence-transformers → torch` wheel chain for 3.13 should be stable by Phase 4. See [hold items](docs/stack-upgrade-proposal.md#hold--do-not-upgrade-yet).

#### Planner Agent
- Detects `multi_hop` query type from Router
- Decomposes query into 2–4 ordered sub-questions using structured output (JSON)
- Dispatches sub-questions to Retriever agents concurrently (`asyncio.gather`)
- Synthesizer node merges partial answers into final coherent response

#### Human-in-the-Loop (Optional)
- LangGraph `interrupt_before` on Generator node when confidence < 0.4
- API returns `status: "awaiting_review"` with draft answer
- `POST /api/v1/query/{session_id}/approve` continues graph execution

---

### Phase 5 — Observability & Evaluation (Days 27–30)
**Goal:** Every agent step is visible. Quality is continuously measured.

> **Stack pre-requisite:** Before setting up RAGAS automation, move `ragas` out of the main dependencies into a separate Poetry eval group (`[tool.poetry.group.eval.dependencies]`). This prevents RAGAS from constraining the API runtime's solver. See [RAGAS isolation](docs/stack-upgrade-proposal.md#hold--do-not-upgrade-yet).
>
> **Carry-forward from 2b architect review (2b-F06 · High):** Wrap all blocking I/O in `asyncio.to_thread` before load testing begins. Affected files:
> - `backend/src/ingestion/pipeline.py` — `pickle.dump` (BM25 persistence)
> - `backend/src/ingestion/local_loader.py:95` — `PdfReader` (blocking PDF parse)
> - `backend/src/ingestion/local_loader.py:137` — `.read_text()`
> - `backend/src/api/routes/eval.py:39` — `.read_text()`
> - `backend/src/evaluation/ragas_eval.py:165,238` — `.read_text()`
>
> See [2b fixes.md F06](docs/registry/phase2/2b-graph-skeleton/fixes.md).

#### LangSmith Integration
- Every graph execution traced end-to-end
- Custom tags: `query_type`, `fallback_triggered`, `steps_taken`, `session_id`
- Token cost tracked per agent node

#### RAGAS Automation
- Weekly eval run against golden dataset via GitHub Actions scheduled job
- Regression gate in CI: if faithfulness drops > 5% from baseline, build fails
- Results written to `docs/evaluation_results.md`

#### Azure Application Insights
- Custom events: `query_received`, `retriever_invoked`, `fallback_triggered`, `answer_returned`
- Latency tracking: P50 / P95 per pipeline stage
- Dashboard: query volume, fallback rate, average confidence, cost per query

---

### Phase 6 — Production Hardening (Days 31–36)
**Goal:** Security, reliability, and operational posture for a real deployment.

#### Security
- Azure AD / Entra ID auth (OAuth2 Bearer JWT) — replaces API key
- Prompt injection detection layer before any LLM call (rule-based + lightweight classifier)
- All secrets in Azure Key Vault; zero secrets in code or env files in prod

#### Reliability
- Retry with exponential backoff on Azure OpenAI calls (tenacity)
- Circuit breaker per upstream: if Azure OpenAI fails 3x, return degraded response instead of 500
- Request timeout budgets per agent node (Router: 3s, Generator: 20s)
- Rate limiting per user: token bucket via Redis or Azure API Management

#### Async Ingestion Worker
- Ingestion jobs queued via Azure Service Bus
- Separate worker container handles embedding + Qdrant upsert
- Job status API: `GET /api/v1/jobs/{job_id}` returns `{status, progress, errors}`

---

### Phase 7 — Azure Deployment & CI/CD (Days 37–42)
**Goal:** One-command deploy to Azure. Automated pipeline from commit to production.

> **Carry-forward from 2b architect review (2b-F03 · High):** Before multi-replica deployment, migrate all per-call client constructions to lifespan singletons with `app.state` + `deps.py` aliases. Affected files and violations:
> - `backend/src/ingestion/vector_store.py:33` — `AsyncQdrantClient(` per call
> - `backend/src/ingestion/embedder.py:64` — `AzureOpenAIEmbeddings(` per call
> - `backend/src/retrieval/dense.py:24` — `AsyncQdrantClient(` per call
> - `backend/src/generation/chain.py:116` — `AzureChatOpenAI(` per call
> - `backend/src/evaluation/ragas_eval.py:220,229` — `AzureChatOpenAI(` and `AzureOpenAIEmbeddings(` on every eval call
>
> Each must follow the `QdrantClientDep` pattern: singleton on `app.state` in lifespan, injected via `Annotated[..., Depends(...)]` alias in `deps.py`. See [2b fixes.md F03](docs/registry/phase2/2b-graph-skeleton/fixes.md).

#### Infrastructure as Code (Terraform)
- `main.tf`: provider config, remote backend (Azure Blob Storage)
- Modules: `container_apps/`, `acr/`, `keyvault/`, `servicebus/`
- Environments: `dev.tfvars`, `prod.tfvars`
- `terraform plan && terraform apply` — single deploy command
- See ADR-006 for the decision rationale over Bicep

#### Docker
- `Dockerfile.api` — FastAPI service
- `Dockerfile.worker` — async ingestion worker
- Qdrant: official image with Azure Managed Disk for persistence

#### GitHub Actions
- `ci.yml`: lint → type check → unit tests → integration tests → RAGAS regression gate
- `deploy.yml`: build → push to ACR → deploy to Container Apps (trigger: merge to `main`)

#### Azure Container Apps
- API: autoscale 1–10 replicas on HTTP request queue depth
- Worker: scale-to-zero when no Service Bus messages pending
- Qdrant: single replica, persistent disk

---

## Project Structure

```
kb-ai-rag/
├── src/
│   ├── agents/
│   │   ├── base.py
│   │   ├── router.py
│   │   ├── retriever.py
│   │   ├── grader.py
│   │   ├── generator.py
│   │   ├── critic.py
│   │   └── planner.py              # Phase 4
│   ├── graph/
│   │   ├── state.py                # AgentState TypedDict
│   │   ├── nodes.py                # Node functions
│   │   ├── edges.py                # Conditional routing
│   │   └── workflow.py             # Graph compilation + entrypoint
│   ├── retrieval/
│   │   ├── base.py                 # BaseRetriever ABC
│   │   ├── qdrant_retriever.py
│   │   ├── azure_search_retriever.py  # Phase 3
│   │   ├── bm25_retriever.py
│   │   ├── hybrid.py               # RRF fusion
│   │   ├── reranker.py             # Cross-encoder
│   │   ├── web_search.py           # Tavily fallback
│   │   └── registry.py             # RetrieverRegistry
│   ├── ingestion/
│   │   ├── loaders/
│   │   │   ├── base.py
│   │   │   ├── local_loader.py     # Phase 1
│   │   │   └── azure_blob_loader.py   # Phase 3
│   │   ├── splitter.py
│   │   ├── embedder.py
│   │   └── pipeline.py
│   ├── memory/
│   │   └── checkpointer.py         # SQLite → Cosmos DB in prod
│   ├── security/
│   │   ├── auth.py                 # API key → Azure AD
│   │   └── injection_guard.py      # Phase 6
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── query.py
│   │   │   ├── ingest.py
│   │   │   ├── jobs.py             # Phase 6
│   │   │   └── metrics.py          # Phase 5
│   │   ├── middleware/
│   │   │   ├── auth.py
│   │   │   └── rate_limit.py       # Phase 6
│   │   └── schemas.py
│   ├── evaluation/
│   │   ├── ragas_eval.py
│   │   └── golden_dataset.json
│   └── config.py                   # Pydantic Settings
├── ui/
│   └── app.py                      # Next.js
├── worker/
│   └── main.py                     # Phase 6 ingestion worker
├── infra/
│   ├── docker-compose.yml          # MVP: API + Qdrant + UI
│   ├── docker-compose.prod.yml
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── terraform/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       ├── modules/
│       │   ├── container_apps/
│       │   ├── acr/
│       │   ├── keyvault/
│       │   └── servicebus/
│       └── environments/
│           ├── dev.tfvars
│           └── prod.tfvars
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── notebooks/
│   ├── 01_ingestion_demo.ipynb
│   ├── 02_retrieval_benchmarks.ipynb
│   └── 03_agent_traces.ipynb
├── docs/
│   ├── architecture.md
│   ├── connector_guide.md
│   ├── evaluation_results.md
│   └── adr/
│       ├── 001-vector-db-qdrant.md
│       ├── 002-azure-ai-foundry.md
│       ├── 003-hybrid-retrieval.md
│       ├── 004-langgraph-vs-chain.md
│       └── 005-nextjs-frontend.md
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── pyproject.toml
├── GOAL.md
├── PROJECT_PLAN.md
├── CONTRIBUTING.md
└── README.md
```

---

## Delivery Timeline

| Week | Phase | Key milestone |
|------|-------|---------------|
| 1 | 0 + 1a–c | Ingestion + retrieval working locally; hybrid search benchmarked |
| 1–2 | 1d–f | API + UI + RAGAS baseline — MVP complete |
| 2–3 | 2 | LangGraph agent graph; CRAG + Self-RAG + Adaptive RAG |
| 3 | 3 | Azure Blob loader; Azure AI Search connector |
| 4 | 4 | Multi-hop planner; parallel sub-retrieval |
| 5 | 5 | LangSmith traces; RAGAS automation; App Insights dashboard |
| 6 | 6 | Auth, prompt injection guard, circuit breakers, rate limiting |
| 7 | 7 | Azure Container Apps deployed; CI/CD pipeline live |

---

## Open Questions (Blocking or Near-Blocking)

| # | Question | Impact | Default if skipped |
|---|----------|--------|-------------------|
| **Q1** | Do you have an **Azure OpenAI** deployment (GPT-4o-mini + text-embedding-ada-002) approved and running? Azure OpenAI requires a separate access request — it's not automatic with an Azure subscription. | Blocks Phase 1 | Use OpenAI API directly for MVP, switch to Azure OpenAI in Phase 3 |
| **Q2** | What is the **knowledge domain** of the PDF/TXT files? (IT support, HR policies, engineering docs, financial, other?) | Shapes golden dataset, demo narrative, and Router prompt | Generic "enterprise knowledge base" |
| **Q3** | Do you have (or want to create) a **Tavily API account** for the CRAG web search fallback? Free tier: 1,000 searches/month. | Blocks CRAG pattern in Phase 2 | Web search node returns empty; CRAG skipped until key is available |
| **Q4** | Do you have a **LangSmith account**? Free tier available. | Blocks Phase 5 observability | Skip LangSmith; use local logging only until account is ready |
| **Q5** | Is **Azure AI Search** in scope as an enterprise connector (Phase 3), or should we focus only on Qdrant for the portfolio? | Shapes Phase 3 scope | Include it — it's a key differentiator for an AI Architect role |
| **Q6** | For the **re-ranker model**: are you comfortable downloading a HuggingFace model (~85MB) locally at startup? Alternatively, skip re-ranking in MVP and add in Phase 2. | Minor — model download only | Download on first run, cache in Docker volume |
| **Q7** | **Sample data**: do you have actual PDF/TXT knowledge articles ready, or should we use a public corpus (e.g., Azure documentation, Wikipedia subset) for MVP development? | Shapes ingestion testing | Use Azure docs PDFs (publicly available, appropriate domain) |
| **Q8** | Is **multi-turn conversation** required in the MVP, or Phase 2+? | Shapes session + checkpointer design | Phase 2+ (MVP is stateless single-turn) |
