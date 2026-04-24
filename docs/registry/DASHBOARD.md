# Registry Dashboard

> Maintained by: project-manager agent | Last updated: 2026-04-24

This is the single cross-phase status view. For task-level detail, open the linked feature registry (`phaseN/Nf-feature-name/tasks.md`).

---

## Project Status

| Phase | Name | Registry | Status | Gate |
|-------|------|----------|--------|------|
| 0 | Scaffolding + Architect Fixes | [tasks](phase0/tasks.md) · [fixes](phase0/fixes.md) | ✅ Complete | Passed 2026-04-23 |
| 1 | Core MVP | [1a](phase1/1a-ingestion/tasks.md) · [1b](phase1/1b-retrieval/tasks.md) · [1c](phase1/1c-generation/tasks.md) · [1c fixes](phase1/1c-generation/fixes.md) · [1d](phase1/1d-api/tasks.md) · [1d fixes](phase1/1d-api/fixes.md) · [1e](phase1/1e-ui/tasks.md) | 🔄 In Progress | — |
| 2 | Agentic Pipeline (LangGraph) | — | ⏳ Not Started | — |
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

**Feature 1c — Generation** complete + architect fixes resolved 2026-04-24. All 13 issues closed (2 Critical, 3 High, 5 Medium, 3 Low). LCEL migration done, shared schema module (`src/schemas/`), ADR-007 + ADR-008 written. See [1c fixes](phase1/1c-generation/fixes.md).

**142 unit tests passing | mypy strict: 0 errors (33 files) | ruff: 0 warnings**

**Feature 1d — API** complete 2026-04-24. All 14 tasks done + 17-item architect review resolved 2026-04-24. Tier 1 fixes applied, Tier 2 patterns used throughout. **177 unit tests passing** | mypy strict: 0 errors (37 files) | ruff: 0 warnings. See [1d tasks](phase1/1d-api/tasks.md) · [1d fixes](phase1/1d-api/fixes.md).

Key fixes applied: SSE error-path handling, BM25 singleton staleness after ingest, health route Qdrant client churn, `SettingsDep` migration, `ragas` moved to eval dep group, `secrets.compare_digest` for API key auth, 15 new unit tests (177 total).

**Feature 1e — UI** ✅ Complete 2026-04-24. All 17 tasks done. Next.js 15.3.9 · React 19.2.5 · Tailwind 4 · ESLint 9 · TypeScript 5.8. Components: ConfidenceBadge · CitationList · ChatMessage · ChatInput · Sidebar · QueryProvider. Hook: useStream (reducer + STREAM_END). **31 frontend tests passing** | tsc: 0 errors | eslint: 0 warnings | npm run build ✓. See [1e tasks](phase1/1e-ui/tasks.md).

**Feature 1f — Evaluation Baseline** is next. RAGAS stays at `^0.2`; move to eval dep group before Phase 5.

---

## Currently In Progress

_Nothing — 1e complete. Feature 1f (RAGAS evaluation baseline) is next._

---

## Blocked / At Risk

_No blockers._

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

### Phase 1 — Core MVP 🔄 In Progress

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
| Next.js chat interface | Query input + answer display | ⏳ Pending |
| Citations display | Filename + page number per source | ⏳ Pending |
| Confidence badge | Visual confidence indicator | ⏳ Pending |
| Sidebar | Collection stats + ingest trigger | ⏳ Pending |

#### 1f. Evaluation Baseline

> **Stack note:** RAGAS stays at `^0.2` for Phase 1f. Before Phase 5 automation, move it to a separate Poetry eval group. See [RAGAS isolation](../stack-upgrade-proposal.md#hold--do-not-upgrade-yet).

| Feature | Description | Status |
|---------|-------------|--------|
| Golden dataset | 20-question Q&A set from knowledge corpus | ⏳ Pending |
| RAGAS run | faithfulness, answer relevancy, context recall, precision | ⏳ Pending |
| Results persisted | `docs/evaluation_results.md` | ⏳ Pending |

**MVP gate (all must pass before Phase 2):**
- [ ] Ingest 30+ local files end-to-end without errors
- [ ] `POST /query` returns answer + citations in < 8s P95 locally
- [ ] RAGAS faithfulness ≥ 0.70
- [ ] API key blocks unauthenticated requests
- [ ] `docker compose up` — full stack running in < 90s

---

### Phase 2 — Agentic Pipeline ⏳ Not Started

> **Stack gate zero:** Before any Phase 2 task begins, complete [Tier 3 pre-requisites](../stack-upgrade-proposal.md#tier-3--phase-2-pre-requisites-gate-zero): lock LangGraph to an exact confirmed version, upgrade the LangChain bundle together, write the ADR-004 amendment, and define `AgentState` schema. Do not write any agent node until these are done.

#### LangGraph State Machine

| Feature | Description | Status |
|---------|-------------|--------|
| `AgentState` TypedDict | Full state schema with `Annotated` reducers — define before any node | ⏳ Pending |
| Graph compilation | `StateGraph` + `SqliteSaver` checkpointer | ⏳ Pending |
| Conditional edges | Router → Retriever → Grader → Generator → Critic routing | ⏳ Pending |

#### Agent Nodes

| Agent | Role | Model | Status |
|-------|------|-------|--------|
| **Router** | Classifies query type + retrieval strategy | GPT-4o-mini | ⏳ Pending |
| **Retriever** | Executes retrieval (no LLM) | — | ⏳ Pending |
| **Grader** | Scores chunk relevance | GPT-4o-mini | ⏳ Pending |
| **Generator** | Produces cited answer | GPT-4o | ⏳ Pending |
| **Critic** | Detects hallucination risk, triggers re-retrieve | GPT-4o-mini | ⏳ Pending |

#### Agentic Patterns

| Pattern | Description | Status |
|---------|-------------|--------|
| Corrective RAG (CRAG) | Grader triggers Tavily web search when all chunks score < 0.5 | ⏳ Pending |
| Self-RAG | Critic re-retrieves with refined query when hallucination risk > 0.7 | ⏳ Pending |
| Adaptive RAG | Router selects dense / hybrid / web strategy per query type | ⏳ Pending |
| HyDE | Hypothetical Document Embeddings for abstract queries | ⏳ Pending |
| Step-back prompting | Reframe specific → general before retrieval | ⏳ Pending |

#### Conversational Memory

| Feature | Description | Status |
|---------|-------------|--------|
| `SqliteSaver` checkpointer | Per-session SQLite state persistence | ⏳ Pending |
| Session ID header | `X-Session-ID` passed in API request | ⏳ Pending |
| Context window | Last 5 exchanges injected into agent context | ⏳ Pending |

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
| 1 | — | Gate: faithfulness ≥ 0.70, full stack < 90s, 30+ files ingested |
