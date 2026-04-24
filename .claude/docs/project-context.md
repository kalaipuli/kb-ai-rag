# Project Context

Reference for project overview, repository layout, local dev commands, and environment variables. Read when orienting to the project or setting up a new environment.

## Project at a Glance

Enterprise Agentic RAG platform. Five LangGraph agents orchestrate hybrid retrieval (Qdrant + BM25) over PDF/text knowledge articles, evaluated with RAGAS, deployed on Azure.

- **Goal:** [GOAL.md](../../GOAL.md) — AI Architect portfolio showcase
- **Plan:** [PROJECT_PLAN.md](../../PROJECT_PLAN.md) — phased delivery roadmap
- **ADRs:** `docs/adr/` — every architectural decision is recorded here
- **Dashboard:** `docs/registry/DASHBOARD.md` — cross-phase task and gate status

## Repository Layout

```
kb-ai-rag/
├── backend/            Python 3.12 + FastAPI + LangGraph
├── frontend/           Next.js 14 + TypeScript + Tailwind
├── infra/              Docker Compose (local) + Terraform (Azure)
├── docs/
│   ├── adr/            Architecture Decision Records
│   └── registry/       Task + fix registries (all phases)
│       ├── DASHBOARD.md
│       ├── _template/
│       └── phase0/ … phaseN/
└── .github/            CI and CD workflows
```

## Running Locally

```bash
# Full stack (API + Qdrant + Frontend)
docker compose -f infra/docker-compose.yml up

# Backend only (dev with reload)
cd backend && poetry run uvicorn src.api.main:app --reload --port 8000

# Frontend only (dev)
cd frontend && npm run dev
```

Local URLs:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Qdrant dashboard: http://localhost:6333/dashboard

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

## Environment Variables Reference

All variables defined in `backend/.env` (local) or Azure Key Vault (prod).
See `backend/.env.example` for the full list with descriptions.

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure AI Foundry project endpoint |
| `AZURE_OPENAI_API_KEY` | Foundry API key |
| `AZURE_CHAT_DEPLOYMENT` | Deployed model name for chat (gpt-4o) |
| `AZURE_EMBEDDING_DEPLOYMENT` | Deployed model name for embeddings |
| `API_KEY` | `X-API-Key` header value for this service |
| `QDRANT_URL` | Qdrant service URL |
| `DATA_DIR` | Path to local PDF/TXT files (Docker volume) |
| `LANGSMITH_API_KEY` | LangSmith tracing (Phase 2+) |
| `TAVILY_API_KEY` | Web search fallback (Phase 2+) |
