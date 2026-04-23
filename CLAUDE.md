# CLAUDE.md — Development Rules & Principles

> This file governs every development session on this project. Read it before writing any code.

---

## Development Process (Foundation)

These principles apply to every change, regardless of size or phase. They are not optional.

### 1. Decompose Before You Code
Every piece of work follows the same hierarchy before a single line is written:

```
Phase → Feature → Tasks → Subtasks (if needed)
```

- A **Phase** delivers a working vertical slice of the system (e.g., MVP RAG pipeline)
- A **Feature** is a coherent capability within a phase (e.g., hybrid retrieval, ingestion pipeline)
- A **Task** is a single, completable unit of work — one function, one module, one endpoint
- Write the task list before starting. Never start coding an undefined task.

### 2. Small, Incremental Changes
- Each commit implements exactly one task. Not one feature — one task.
- A change that cannot be described in a single Conventional Commit subject line is too large — split it.
- Never refactor and implement in the same commit.
- Changes are integrated continuously; no long-running branches that diverge for days.

### 3. Test First, Then Code
- Write the unit test **before or alongside** the implementation — never after.
- Every task has at least one corresponding test. No exceptions.
- A task is not complete until its test is written **and passes**.
- Test the behaviour (what the function does), not the implementation (how it does it).

```
Task: implement RRF fusion
  → Write test_hybrid.py::test_rrf_merges_and_ranks_correctly first
  → Implement hybrid.py::reciprocal_rank_fusion
  → Run test — green → commit
```

### 4. Automate All Tests
- Tests run automatically on every commit via GitHub Actions CI.
- No manual "I tested it locally" is sufficient for a merge — CI must be green.
- Tests are organised into:
  - `tests/unit/` — fast, no I/O, no network, run in < 30s total
  - `tests/integration/` — requires Docker Compose up, tests real Qdrant + API behaviour
- Unit tests run on every PR. Integration tests run on merge to `develop` and `main`.
- A failing test is a blocked task. Fix the test before moving to the next task.

### 5. Cross-Check Integrity After Every Feature
Before marking a feature complete and moving to the next:
- Run the full unit test suite — all green
- Run mypy and ruff — zero errors
- Run the TypeScript compiler check (`tsc --noEmit`) if frontend was touched
- Manually verify the end-to-end path for the feature (not just the unit under test)
- Check that no existing tests were broken (regression check)
- Review that the `AgentState` schema, API schemas, and metadata schemas are still consistent

### 6. Use the Latest Stable Versions
- Always pin to the latest **stable** (non-alpha, non-beta) version of every dependency.
- Check for newer versions when starting a new phase, not mid-phase.
- Version upgrades are their own task and commit — never bundled with feature work.
- Document the version choice in `pyproject.toml` comments if a newer version was intentionally skipped (e.g., breaking API change).

### 7. Definition of Done (per task)
A task is done when **all** of the following are true:
- [ ] Implementation is complete and matches the agreed design
- [ ] Unit test written and passing
- [ ] `mypy` passes (backend) / `tsc --noEmit` passes (frontend)
- [ ] `ruff` / `eslint` passes with zero warnings
- [ ] `.env.example` updated if a new config variable was introduced
- [ ] ADR written if an architectural decision was made
- [ ] Committed with a valid Conventional Commit message

### 8. No Orphaned Code
- Do not write code that is not yet called or tested — it will rot and mislead.
- Stub functions are allowed only if they are called by a test that documents the expected behaviour.
- If a planned function is deferred to a later phase, it does not exist in code yet.

### 9. Maintain a Task Status Tracker

All task registries live under `docs/registry/`. This directory is the ground truth for all task, fix, and phase-gate tracking across the full project lifetime.

#### Directory layout

```
docs/registry/
├── DASHBOARD.md          ← cross-phase project status board (project-manager owns)
├── _template/
│   └── tasks.md          ← copy this when starting a new phase
├── phase0/
│   ├── tasks.md          ← Phase 0 task registry
│   └── fixes.md          ← architect review fixes (created on demand)
├── phase1/
│   └── tasks.md
└── phaseN/
    └── tasks.md
```

#### Lifecycle rules

- **Before a phase starts:** copy `_template/tasks.md` → `registry/phaseN/tasks.md`; list all tasks as `⏳ Pending`; update `DASHBOARD.md` to mark the phase active.
- **During work:** update each task's status as it progresses. Never leave a stale status.
- **After a gate passes:** update `DASHBOARD.md` with the gate result and completion date; link the new phase registry.
- **When architect review produces fixes:** create `registry/phaseN/fixes.md`; all critical fixes must clear before Phase N+1 starts.

#### Task status lifecycle

```
⏳ Pending → 🔄 In Progress → ✅ Done
```

- Only one task should be `🔄 In Progress` per agent at a time.
- A task must not reach `✅ Done` unless every item in the Definition of Done (§7) is satisfied.

#### Mandatory task columns (every task table)

```
| ID | Status | Task | Agent | Depends On |
```

#### DASHBOARD.md

`docs/registry/DASHBOARD.md` is the single cross-phase view. It must always show:
- Phase status table (all phases, gate pass/fail date)
- Currently in-progress tasks (cross-phase)
- Blocked / at-risk items

The `project-manager` agent updates it at every phase transition and gate check.

```
| T01 | ✅ Done        | Write ADRs              | architect    | —       |
| T02 | 🔄 In Progress | Create folder structure  | architect    | T01     |
| T03 | ⏳ Pending     | Define test plan        | test-manager | T01,T02 |
```

---

## Agent Conduct

Rules for how the AI agent operates during every session.

### No End-of-Response Summaries
Do not append a summary paragraph at the end of a response. The work product speaks for itself — narrating what was just done adds noise. Only state what changed if it is not already visible from the tool output or diff.

### Read Only What the Task Requires
Do not pre-emptively open files that are not needed for the current task. Open a file only when its content is directly required to complete the step in hand. Reading speculatively wastes context and slows down the session.

### Use Tools Efficiently
- Prefer `grep` / `find` over reading full files when the goal is to locate a symbol or pattern.
- Run independent tool calls in parallel in a single message rather than sequentially.
- Do not re-read a file immediately after editing it — the edit either succeeded or errored.
- Use the `Explore` sub-agent for broad codebase searches that would otherwise take more than three direct queries.

---

## Project at a Glance

Enterprise Agentic RAG platform. Five LangGraph agents orchestrate hybrid retrieval (Qdrant + BM25) over PDF/text knowledge articles, evaluated with RAGAS, deployed on Azure.

- **Goal:** [GOAL.md](GOAL.md) — AI Architect portfolio showcase
- **Plan:** [PROJECT_PLAN.md](PROJECT_PLAN.md) — phased delivery roadmap
- **ADRs:** `docs/adr/` — every architectural decision is recorded here

---

## Repository Layout

```
kb-ai-rag/
├── backend/            Python 3.12 + FastAPI + LangGraph
├── frontend/           Next.js 14 + TypeScript + Tailwind
├── infra/              Docker Compose (local) + Bicep (Azure)
├── docs/
│   ├── adr/            Architecture Decision Records
│   └── registry/       Task + fix registries (all phases)
│       ├── DASHBOARD.md
│       ├── _template/
│       └── phase0/ … phaseN/
└── .github/            CI and CD workflows
```

---

## Running Locally

```bash
# Full stack (API + Qdrant + Frontend)
docker compose -f infra/docker-compose.yml up

# Backend only (dev with reload)
cd backend && poetry run uvicorn src.api.main:app --reload --port 8000

# Frontend only (dev)
cd frontend && npm run dev
```

URLs:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard

---

## Backend Commands

```bash
cd backend

# Install dependencies
poetry install

# Lint (must pass — no warnings tolerated)
poetry run ruff check .
poetry run ruff format .

# Type check (strict mode — must pass)
poetry run mypy src/

# Tests
poetry run pytest tests/unit -q
poetry run pytest tests/integration -q   # requires docker compose up

# Ingestion (local files in backend/data/)
poetry run python -m src.ingestion.pipeline

# RAGAS evaluation
poetry run python -m src.evaluation.ragas_eval
```

## Frontend Commands

```bash
cd frontend

npm ci                   # install
npm run dev              # dev server
npm run build            # production build
npx tsc --noEmit         # type check (must pass)
npx eslint src/          # lint (must pass)
```

---

## Python Code Rules

### Types — no exceptions
- Every function has a return type annotation
- Every parameter has a type annotation
- `mypy --strict` must pass before any commit
- Use `TypedDict` for LangGraph `AgentState`
- Use `Pydantic BaseModel` for all API request/response schemas and config

```python
# Correct
async def embed_texts(texts: list[str]) -> list[list[float]]:
    ...

# Wrong — missing annotations
async def embed_texts(texts):
    ...
```

### Async
- All I/O operations are `async` — Qdrant calls, Azure OpenAI calls, file reads
- Never use `time.sleep()` — use `asyncio.sleep()`
- Use `asyncio.gather()` for concurrent fan-out (e.g., multi-hop sub-retrieval)
- FastAPI route handlers are `async def`

### Logging — structlog only
- Never use `print()` or `logging.info()` directly
- Use `structlog.get_logger(__name__)` in every module
- Every log event is a structured key-value dict, never a formatted string

```python
# Correct
logger.info("retrieval_complete", chunk_count=len(docs), duration_ms=elapsed)

# Wrong
logger.info(f"Retrieved {len(docs)} chunks in {elapsed}ms")
```

### Error handling
- Raise domain-specific exceptions (define in `src/exceptions.py`), not bare `Exception`
- Never silently swallow exceptions — at minimum log and re-raise
- FastAPI exception handlers translate domain exceptions to HTTP responses
- Circuit breaker pattern on all Azure OpenAI calls (Phase 6); until then, use `tenacity` retry

### No hardcoded values
- All configuration lives in `src/config.py` via `pydantic-settings`
- All secrets come from environment variables (`.env` locally, Azure Key Vault in prod)
- No API keys, endpoints, or model names in source code

### Imports
- Absolute imports only: `from src.retrieval.hybrid import reciprocal_rank_fusion`
- No wildcard imports: never `from module import *`

---

## Architecture Rules

### Connector abstraction — always
Every data source and retriever implements `BaseLoader` or `BaseRetriever` ABC.
New sources are new files, not modifications to existing ones.

```python
# Adding Azure Blob = new file src/ingestion/loaders/azure_blob_loader.py
# Never = adding blob logic into local_loader.py
```

### Domain-agnostic retrieval
- No hard-coded domain routing. The `Router` agent classifies **query intent** (factual, analytical, multi-hop, ambiguous) — not a knowledge domain.
- Metadata fields (`filename`, `file_type`, `tags`, `source_path`) are stored in Qdrant payload and used for **optional filtering** at query time, not mandatory routing.
- Any document from any domain should be retrievable by a well-formed query.

### Document metadata schema — always complete
Every chunk upserted to Qdrant must carry the full `ChunkMetadata` payload:
`doc_id`, `chunk_id`, `source_path`, `filename`, `file_type`, `title`, `page_number`, `chunk_index`, `total_chunks`, `char_count`, `ingested_at`, `tags`

Never upsert a vector without payload.

### Phased implementation — no skipping ahead
Build phases in order. Do not implement Phase 2 agent logic until Phase 1 MVP gates pass:
- RAGAS faithfulness ≥ 0.70
- Full stack runs via `docker compose up`
- All unit tests green

### AgentState is the single source of truth
In Phase 2+, all data flows through `AgentState`. Agents read from state, write to state.
No agent returns a value directly to another agent. No global variables.

### API versioning
All routes are prefixed `/api/v1/`. Never change an existing route signature — add a new version instead.

### Streaming — SSE for query responses
`POST /api/v1/query` streams via Server-Sent Events (SSE) using FastAPI `StreamingResponse`.
The frontend consumes with `fetch` + `ReadableStream`, not `EventSource` (to support POST).
Three event types only: `token`, `citations`, `done`.

---

## TypeScript / Frontend Rules

- **TypeScript strict mode** — `"strict": true` in `tsconfig.json`
- All API response types are defined in `src/types/index.ts` — no `any`
- Components in `src/components/` are named exports, not default exports
- Fetch calls live in `src/lib/api.ts` only — no `fetch()` calls inside components
- SSE streaming logic lives in `src/lib/streaming.ts` only
- Use `shadcn/ui` components before writing custom UI primitives

---

## Git & GitHub Rules

### Branch strategy
```
main      ← protected; requires PR + CI pass; triggers CD to Azure
develop   ← integration; CI only
feature/* ← one feature per branch; PR → develop
```

### Commit format (Conventional Commits — required)
```
feat(scope): short description
fix(scope): short description
docs(adr): add ADR-003
chore(deps): bump qdrant-client
```
Scopes: `ingestion`, `retrieval`, `agents`, `graph`, `api`, `frontend`, `infra`, `eval`, `adr`, `deps`, `config`

### PR rules
- Every PR has a description explaining **why**, not just what
- No PR merges if CI fails (ruff + mypy + tsc + unit tests)
- ADR updated in same PR if an architectural decision was made
- `.env.example` updated in same PR if a new env var was added

### Commit size
- One logical change per commit
- Never commit commented-out code
- Never commit `.env` files — `.gitignore` must exclude them

---

## Architecture Decision Records

Every significant architectural choice gets an ADR in `docs/adr/`.

**When to write one:** choosing between two viable options, accepting a trade-off, deciding to defer something.

**Template:**
```markdown
# ADR-NNN: Title

## Status
Accepted

## Context
What problem or question prompted this decision.

## Decision
What was decided.

## Alternatives Considered
What else was evaluated and why it was rejected.

## Consequences
What becomes easier, harder, or different as a result.
```

Current ADRs to write (Phase 0):
- `001-vector-db-qdrant.md`
- `002-azure-ai-foundry.md`
- `003-hybrid-retrieval.md`
- `004-langgraph-vs-chain.md`
- `005-nextjs-frontend.md`

---

## What Not To Do

| Don't | Do instead |
|-------|-----------|
| Use `print()` for debugging | `structlog` with structured keys |
| Skip type annotations | Annotate everything; mypy must pass |
| Put secrets in code | `config.py` + `.env` / Key Vault |
| Hardcode domain names in routing | Metadata filters + intent classification |
| Add RAG logic to API route handlers | Keep routes thin; logic in `src/retrieval/` or `src/graph/` |
| Write agents before Phase 1 gates pass | Follow the phase gates |
| Create a new abstraction for < 3 use cases | YAGNI — only abstract when the third case arrives |
| Use `Any` in TypeScript | Define proper types in `src/types/index.ts` |
| Commit untested code to `main` | All tests pass before merge |
| Skip the ADR when making an architectural choice | Write the ADR in the same PR |

---

## Environment Variables Reference

All variables defined in `backend/.env` (local) or Azure Key Vault (prod).
See `backend/.env.example` for the full list with descriptions.

Key variables:
```
AZURE_OPENAI_ENDPOINT        Azure AI Foundry project endpoint
AZURE_OPENAI_API_KEY         Foundry API key
AZURE_CHAT_DEPLOYMENT        Deployed model name for chat (gpt-4o)
AZURE_EMBEDDING_DEPLOYMENT   Deployed model name for embeddings
API_KEY                      X-API-Key header value for this service
QDRANT_URL                   Qdrant service URL
DATA_DIR                     Path to local PDF/TXT files (Docker volume)
LANGSMITH_API_KEY            LangSmith tracing (Phase 2+)
TAVILY_API_KEY               Web search fallback (Phase 2+)
```
