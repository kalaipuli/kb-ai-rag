# Contributing to KB AI RAG

## Prerequisites

- Python 3.12, Poetry 1.8+
- Node.js 20+, npm
- Docker Desktop
- An Azure AI Foundry project with GPT-4o and text-embedding-3-large deployed

## Local Setup

### 1. Clone and configure

```bash
git clone https://github.com/<your-username>/kb-ai-rag.git
cd kb-ai-rag
cp backend/.env.example backend/.env
# Edit backend/.env with your Azure AI Foundry credentials
```

### 2. Start the full stack

```bash
docker compose -f infra/docker-compose.yml up
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Qdrant dashboard | http://localhost:6333/dashboard |

### 3. Backend dev (hot reload)

```bash
cd backend
poetry install
poetry run uvicorn src.api.main:app --reload --port 8000
```

### 4. Frontend dev

```bash
cd frontend
npm ci
npm run dev
```

## Running Checks

```bash
# Backend
cd backend
poetry run ruff check .          # lint
poetry run ruff format .         # format
poetry run mypy src/             # type check
poetry run pytest tests/unit -q  # unit tests

# Frontend
cd frontend
npx tsc --noEmit                 # type check
npx next lint                    # lint
```

## Branch Strategy

```
main      ← protected; requires PR + CI pass; triggers CD
develop   ← integration branch; CI only
feature/* ← one feature per branch; PR → develop
```

## Commit Format (Conventional Commits)

```
feat(ingestion): add local PDF loader with pypdf
fix(retrieval): correct RRF score normalisation
docs(adr): add ADR-003 hybrid retrieval decision
chore(deps): bump qdrant-client to 1.11.3
```

Valid scopes: `ingestion`, `retrieval`, `agents`, `graph`, `api`, `frontend`, `infra`, `eval`, `adr`, `deps`, `config`

## Development Rules

All development follows the principles in [CLAUDE.md](CLAUDE.md):

1. Decompose work into Phase → Feature → Tasks before writing code
2. Small incremental changes — one task per commit
3. Write the unit test before or alongside the implementation
4. Automate all tests — CI must be green before merge
5. Cross-check integrity after every feature
6. Use the latest stable dependency versions
7. A task is done only when its Definition of Done checklist is fully satisfied
8. No orphaned code — only what is called and tested
9. Maintain a task status tracker and update it as work progresses

## Definition of Done

A task is complete only when all of these are true:

- [ ] Implementation complete and matches agreed design
- [ ] Unit test written and passing
- [ ] `mypy` passes (backend) / `tsc --noEmit` passes (frontend)
- [ ] `ruff` / `next lint` passes with zero warnings
- [ ] `.env.example` updated if new config variable introduced
- [ ] ADR written if architectural decision was made
- [ ] Committed with valid Conventional Commit message
- [ ] Task marked Done in phase task registry
