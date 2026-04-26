# Test Guide

## Backend Tests (Python)

All tests run from the `backend/` directory.

```bash
cd backend
poetry install
```

### Run all unit tests

```bash
poetry run pytest
```

Output is compact by default (`-q --tb=short`). Add `-v` for verbose names.

### Run with coverage

```bash
poetry run pytest --cov=src --cov-report=term-missing
```

### Run a specific test file

```bash
poetry run pytest tests/unit/test_api_query.py
```

### Type checking

```bash
poetry run mypy --strict src/
```

### Linting

```bash
poetry run ruff check src/ tests/
```

---

## Frontend Tests (TypeScript)

```bash
cd frontend
npm install
npm test
```

This runs Vitest in watch mode. To run once and exit:

```bash
npm test -- --run
```

---

## RAGAS Evaluation

RAGAS evaluates answer quality against a golden dataset. It requires a live backend with documents already ingested.

```bash
cd backend
poetry run python scripts/run_eval.py
```

Results are written to `docs/evaluation_results.md`.

> RAGAS requires `LANGSMITH_API_KEY` and optionally `LANGCHAIN_TRACING_V2=true` in `backend/.env`.

---

## What Each Suite Covers

| Suite | What it tests |
|---|---|
| `tests/unit/test_api_*` | FastAPI route handlers (mocked dependencies) |
| `tests/unit/test_retrieval_*` | Dense, sparse, hybrid retrieval, reranker |
| `tests/unit/test_ingestion_*` | Chunking, embedding, BM25, vector store writes |
| `tests/unit/test_generation_chain.py` | LangGraph generation chain |
| `tests/unit/test_auth_middleware.py` | API key authentication |
| `frontend/src/**/*.test.*` | React components and streaming hooks |
