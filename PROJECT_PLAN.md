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

### Phase 2 — Agentic Pipeline (Days 9–16)
**Goal:** Replace static chain with LangGraph agent graph. The system now reasons, not just retrieves.

> **Stack gate zero (before any agent node):** Complete all [Tier 3 pre-requisites](docs/stack-upgrade-proposal.md#tier-3--phase-2-pre-requisites-gate-zero): lock LangGraph to an exact confirmed version (not `^`), upgrade the LangChain bundle together, write the ADR-004 amendment, and define `AgentState` schema before writing any node function.

#### LangGraph State Machine
```python
class AgentState(TypedDict):
    session_id: str
    query: str
    query_rewritten: str | None
    query_type: Literal["factual", "analytical", "multi_hop", "ambiguous"]
    retrieval_strategy: Literal["dense", "hybrid", "web"]
    retrieved_docs: list[Document]
    graded_docs: list[Document]
    answer: str | None
    citations: list[Citation]
    confidence: float
    hallucination_risk: float
    fallback_triggered: bool
    steps_taken: list[str]
    user_id: str
```

#### Agent Nodes

| Agent | Input | Output | Model |
|-------|-------|--------|-------|
| **Router** | Raw query | query_type, retrieval_strategy | GPT-4o-mini (cheap, fast) |
| **Retriever** | Rewritten query + strategy | retrieved_docs | No LLM — pure retrieval |
| **Grader** | retrieved_docs | graded_docs, relevance_scores | GPT-4o-mini |
| **Generator** | graded_docs + query | answer, citations | GPT-4o |
| **Critic** | answer + graded_docs | hallucination_risk, decision | GPT-4o-mini |

#### Conditional Routing (Edges)
```
START
  → Router
  → Retriever
  → Grader
      → [all docs poor] → WebSearch → Generator
      → [docs OK]       → Generator
  → Critic
      → [hallucination risk high] → Retriever (refined query, max 1 retry)
      → [answer grounded]         → END
```

#### Agentic Patterns Implemented
1. **Corrective RAG (CRAG)** — Grader triggers Tavily web search fallback when all chunks score < 0.5
2. **Self-RAG** — Critic checks grounding; re-retrieves with refined query if risk > 0.7
3. **Adaptive RAG** — Router selects retrieval strategy per query type:
   - `factual` → hybrid (dense + BM25)
   - `analytical` → dense with larger k
   - `multi_hop` → query decomposition (Phase 3)
   - `ambiguous` → clarification or best-effort

#### Query Rewriting
- **HyDE** (Hypothetical Document Embeddings): generate a hypothetical answer, embed it, use that vector to retrieve — improves dense recall for abstract questions
- **Step-back prompting**: reframe specific questions as general principles before retrieval

#### Conversational Memory

> **Note:** Confirm `SqliteSaver` import path for the locked LangGraph version before writing checkpointer code — it may have moved to a separate `langgraph-checkpoint-sqlite` package. See [T3-4](docs/stack-upgrade-proposal.md#t3-4-confirm-sqlitesaver-import-path).

- LangGraph `SqliteSaver` checkpointer: one SQLite DB per session
- Session ID passed in API request header (`X-Session-ID`)
- Agent references prior turns in context window (last 5 exchanges)

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
