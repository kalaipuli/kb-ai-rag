# Phase 0 — Scaffolding Task Registry

> Status: Complete | Phase: 0 | Days: 1–2
> Governed by: CLAUDE.md — all tasks follow the Definition of Done checklist
> Last updated: 2026-04-23

---

## Task Overview

| # | Status | Task | Agent | Depends On | Commit Hint |
|---|--------|------|-------|-----------|-------------|
| T01 | ✅ Done | Write 5 ADRs in `docs/adr/` | architect | — | `docs(adr): add ADR-001 through ADR-005` |
| T02 | ✅ Done | Define folder structure + create empty packages | architect | T01 | `chore(infra): scaffold project directory structure` |
| T03 | ✅ Done | Define Phase 0 test plan | test-manager | T01, T02 | `docs(eval): define Phase 0 unit test plan` |
| T04 | ✅ Done | Create `backend/pyproject.toml` with all Phase 1 deps | backend-developer | T02 | `chore(deps): initialise Poetry project with Phase 0/1 deps` |
| T05 | ✅ Done | Create `backend/.env.example` | backend-developer | T04 | `chore(config): add .env.example with all required variables` |
| T06 | ✅ Done | Implement `backend/src/config.py` (Pydantic Settings) | backend-developer | T04, T05 | `feat(config): add Pydantic Settings config loader` |
| T07 | ✅ Done | Implement `backend/src/exceptions.py` | backend-developer | T04 | `feat(api): add domain exception hierarchy` |
| T08 | ✅ Done | Implement `backend/src/logging_config.py` (structlog JSON) | backend-developer | T04 | `feat(api): add structlog JSON logging with correlation ID` |
| T09 | ✅ Done | Implement `backend/src/api/schemas.py` (base Pydantic schemas) | backend-developer | T06 | `feat(api): add base Pydantic request/response schemas` |
| T10 | ✅ Done | Implement `backend/src/api/middleware/auth.py` (X-API-Key) | backend-developer | T06, T07 | `feat(api): add X-API-Key authentication middleware` |
| T11 | ✅ Done | Implement `backend/src/api/routes/health.py` (GET /api/v1/health) | backend-developer | T09 | `feat(api): add GET /api/v1/health liveness endpoint` |
| T12 | ✅ Done | Implement `backend/src/api/main.py` (FastAPI app + lifespan) | backend-developer | T08, T10, T11 | `feat(api): wire FastAPI app with lifespan, middleware, routes` |
| T13 | ✅ Done | Create `backend/tests/conftest.py` | backend-developer | T12 | `test(api): add pytest conftest with TestClient fixture` |
| T14 | ✅ Done | Create `backend/Dockerfile` | backend-developer | T12 | `chore(infra): add backend Dockerfile` |
| T15 | ✅ Done | Bootstrap Next.js 14 frontend with TypeScript strict + Tailwind | frontend-developer | T02 | `feat(frontend): bootstrap Next.js 14 App Router with TS strict` |
| T16 | ✅ Done | Create `frontend/src/types/index.ts` (shared TypeScript types) | frontend-developer | T15 | `feat(frontend): add shared TypeScript API response types` |
| T17 | ✅ Done | Create `frontend/Dockerfile` | frontend-developer | T15 | `chore(infra): add frontend Dockerfile` |
| T18 | ✅ Done | Write `backend/tests/unit/test_config.py` | tester | T06, T13 | `test(config): unit tests for Pydantic Settings config loading` |
| T19 | ✅ Done | Write `backend/tests/unit/test_auth_middleware.py` | tester | T10, T13 | `test(api): unit tests for X-API-Key auth middleware` |
| T20 | ✅ Done | Write `backend/tests/unit/test_logging_config.py` | tester | T08, T13 | `test(api): unit tests for structlog JSON logging output` |
| T21 | ✅ Done | Verify: run `ruff check`, `mypy src/`, `pytest tests/unit -q` | backend-developer | T18, T19, T20 | — |
| T22 | ✅ Done | Verify: run `tsc --noEmit`, `eslint src/` on frontend | frontend-developer | T16 | — |
| T23 | ✅ Done | Create `infra/docker-compose.yml` (API + Qdrant + Frontend) | project-manager | T14, T17 | `chore(infra): add Docker Compose stack for local dev` |
| T24 | ✅ Done | Create `.github/workflows/ci.yml` + `deploy.yml` + `ragas-weekly.yml` | project-manager | T21, T22 | `chore(infra): add GitHub Actions CI workflows` |
| T25 | ✅ Done | Create `.github/pull_request_template.md` | project-manager | — | `chore(infra): add PR description template` |
| T26 | ✅ Done | Create `CONTRIBUTING.md` + `.gitignore` + `backend/data/.gitkeep` | project-manager | — | `docs: add CONTRIBUTING guide and repo hygiene files` |

---

## Ordered Task Sequence

### Batch 1 — Parallel (no dependencies)
- **T01** — architect writes 5 ADRs
- **T25** — project-manager creates PR template
- **T26** — project-manager creates CONTRIBUTING.md

### Batch 2 — After T01
- **T02** — architect defines and creates folder structure

### Batch 3 — After T02 (parallel)
- **T03** — test-manager defines test plan
- **T04** — backend-developer initialises pyproject.toml
- **T15** — frontend-developer bootstraps Next.js

### Batch 4 — After T04 (parallel)
- **T05** — backend-developer creates .env.example
- **T07** — backend-developer creates exceptions.py
- **T08** — backend-developer creates logging_config.py

### Batch 5 — After T05 + T04
- **T06** — backend-developer creates config.py (needs .env.example for var names)

### Batch 6 — After T06 (parallel)
- **T09** — backend-developer creates schemas.py
- **T10** — backend-developer creates auth middleware (needs config + exceptions)

### Batch 7 — After T09
- **T11** — backend-developer creates health route

### Batch 8 — After T08, T10, T11 (parallel)
- **T12** — backend-developer wires main.py
- **T16** — frontend-developer creates types/index.ts (after T15)
- **T17** — frontend-developer creates frontend Dockerfile (after T15)

### Batch 9 — After T12
- **T13** — backend-developer creates conftest.py
- **T14** — backend-developer creates backend Dockerfile

### Batch 10 — After T13, T03 (parallel)
- **T18** — tester writes test_config.py
- **T19** — tester writes test_auth_middleware.py
- **T20** — tester writes test_logging.py

### Batch 11 — After T18, T19, T20
- **T21** — backend-developer verifies ruff + mypy + pytest

### Batch 12 — After T16, T22 (parallel with T21)
- **T22** — frontend-developer verifies tsc + eslint

### Batch 13 — After T14, T17
- **T23** — project-manager creates docker-compose.yml

### Batch 14 — After T21, T22
- **T24** — project-manager creates GitHub Actions CI

---

## Definition of Done Per Task

### T01 — ADRs
- [ ] All 5 ADR files exist in `docs/adr/`
- [ ] Each follows the ADR template from CLAUDE.md
- [ ] Each covers: Context, Decision, Alternatives Considered, Consequences
- [ ] Files: `001-vector-db-qdrant.md`, `002-azure-ai-foundry.md`, `003-hybrid-retrieval.md`, `004-langgraph-vs-chain.md`, `005-nextjs-frontend.md`

### T02 — Folder Structure
- [ ] All directories created with `__init__.py` where needed
- [ ] No orphaned files — only directories with a planned purpose for Phase 0/1

### T03 — Test Plan
- [ ] Written test plan document covering all 3 unit test modules
- [ ] Pass criteria defined per test case
- [ ] Fixtures and mocking strategy documented

### T04 — pyproject.toml
- [ ] Poetry project initialised for Python 3.12
- [ ] All Phase 0+1 dependencies pinned to latest stable versions
- [ ] ruff + mypy configured in `[tool.ruff]` and `[tool.mypy]` sections
- [ ] mypy set to strict mode
- [ ] pytest configured in `[tool.pytest.ini_options]`

### T05 — .env.example
- [ ] All environment variables listed with descriptions
- [ ] No real secrets — only placeholder values
- [ ] `.env` added to `.gitignore`

### T06 — config.py
- [ ] All env vars mapped as Pydantic Settings fields
- [ ] `model_config = SettingsConfigDict(env_file=".env")`
- [ ] Type annotations on every field
- [ ] mypy strict passes

### T07 — exceptions.py
- [ ] Base `KBException` class defined
- [ ] At minimum: `ConfigurationError`, `AuthenticationError`, `NotFoundError`
- [ ] All exceptions have descriptive messages
- [ ] mypy strict passes

### T08 — logging_config.py
- [ ] structlog configured for JSON output
- [ ] Correlation ID injected per request via context var
- [ ] `configure_logging()` function callable at app startup
- [ ] No `print()` or stdlib `logging` used directly

### T09 — schemas.py
- [ ] `HealthResponse` Pydantic model defined
- [ ] `ErrorResponse` Pydantic model defined
- [ ] All fields typed
- [ ] mypy strict passes

### T10 — auth.py (middleware)
- [ ] Starlette `BaseHTTPMiddleware` subclass
- [ ] Reads `X-API-Key` header
- [ ] Returns 401 JSON if header missing or value wrong
- [ ] Skips auth for `/docs`, `/openapi.json`, `/api/v1/health`
- [ ] Config-driven (no hardcoded key values)
- [ ] mypy strict passes

### T11 — health.py (route)
- [ ] `GET /api/v1/health` returns `{"status": "ok"}` with 200
- [ ] Returns `HealthResponse` schema
- [ ] Async handler
- [ ] mypy strict passes

### T12 — main.py
- [ ] FastAPI app with lifespan context manager
- [ ] structlog configured in lifespan startup
- [ ] Auth middleware registered
- [ ] Health router mounted at `/api/v1`
- [ ] Exception handlers for domain exceptions
- [ ] mypy strict passes

### T13 — conftest.py
- [ ] `TestClient` fixture with override for `API_KEY` env var
- [ ] `async_client` fixture for async tests if needed
- [ ] Clean setup/teardown

### T14 — backend Dockerfile
- [ ] Multi-stage build (builder + runtime)
- [ ] Non-root user
- [ ] Exposes port 8000
- [ ] Installs dependencies via poetry export

### T15 — Frontend Bootstrap
- [ ] `next.config.ts` configured
- [ ] `tsconfig.json` with `"strict": true`
- [ ] Tailwind CSS configured
- [ ] `eslint.config.mjs` configured
- [ ] App Router directory structure: `src/app/`, `src/components/`, `src/lib/`, `src/types/`
- [ ] `tsc --noEmit` passes on clean scaffold
- [ ] `eslint src/` passes with zero warnings

### T16 — types/index.ts
- [ ] `HealthResponse` TypeScript interface
- [ ] `ApiError` TypeScript interface
- [ ] No `any` types
- [ ] Strict type check passes

### T17 — frontend Dockerfile
- [ ] Multi-stage build (deps + builder + runner)
- [ ] Non-root user
- [ ] Exposes port 3000
- [ ] Uses `npm ci` for reproducible installs

### T18 — test_config.py
- [ ] Tests that valid env vars load correctly
- [ ] Tests that missing required vars raise `ValidationError`
- [ ] Tests default values where applicable
- [ ] No I/O, no network — pure unit test

### T19 — test_auth_middleware.py
- [ ] Tests that missing `X-API-Key` returns 401
- [ ] Tests that wrong key returns 401
- [ ] Tests that correct key allows request through
- [ ] Tests that `/api/v1/health` is accessible without auth (if health is public)
- [ ] Uses `TestClient` from conftest

### T20 — test_logging.py
- [ ] Tests that `configure_logging()` produces JSON output
- [ ] Tests that log events include required keys (event, timestamp, level)
- [ ] Tests structlog structured key-value format
- [ ] No I/O beyond capturing log output

### T21 — Backend Verification
- [ ] `ruff check .` — zero errors
- [ ] `ruff format --check .` — no formatting diffs
- [ ] `mypy src/` — zero errors (strict mode)
- [ ] `pytest tests/unit -q` — all green
- [ ] If failures: fix before marking done

### T22 — Frontend Verification
- [ ] `tsc --noEmit` — zero errors
- [ ] `eslint src/` — zero warnings
- [ ] If failures: fix before marking done

### T23 — docker-compose.yml
- [ ] Three services: `api`, `qdrant`, `frontend`
- [ ] Qdrant image: `qdrant/qdrant:v1.11.3`
- [ ] API depends on qdrant healthcheck
- [ ] Frontend depends on api
- [ ] Volume for Qdrant persistence
- [ ] `.env` file reference for secrets
- [ ] Port mappings: 8000 (api), 6333 (qdrant), 3000 (frontend)

### T24 — ci.yml
- [ ] Triggers on: push to `develop`, PR to `main`
- [ ] Jobs: `lint-backend`, `typecheck-backend`, `test-backend`, `lint-frontend`, `typecheck-frontend`
- [ ] Uses Python 3.12
- [ ] Uses Node.js 20
- [ ] Caches Poetry deps and npm deps
- [ ] Integration tests skipped in CI skeleton (require Docker)

### T25 — PR Template
- [ ] Sections: Summary, Changes, Test Plan, ADR Updated (Y/N), `.env.example` Updated (Y/N)
- [ ] Conventional Commit reminder

### T26 — CONTRIBUTING.md
- [ ] Local setup instructions (Docker Compose + backend-only + frontend-only)
- [ ] Branch strategy documented
- [ ] Commit format with examples
- [ ] How to run tests

---

## Phase 0 Gate Criteria

All of the following must be true before Phase 1 begins:

| Gate | Check | Pass Condition |
|------|-------|---------------|
| G01 | `docker compose -f infra/docker-compose.yml up` | All 3 services start without error |
| G02 | `GET /api/v1/health` | HTTP 200, `{"status": "ok"}` |
| G03 | `GET /api/v1/health` without `X-API-Key` | HTTP 401 |
| G04 | `poetry run ruff check .` in `backend/` | Zero errors |
| G05 | `poetry run mypy src/` in `backend/` | Zero errors (strict mode) |
| G06 | `npx tsc --noEmit` in `frontend/` | Zero errors |
| G07 | `npx eslint src/` in `frontend/` | Zero warnings |
| G08 | `poetry run pytest tests/unit -q` in `backend/` | All green |
| G09 | `docs/adr/` | 5 ADR files present and complete |
| G10 | `.github/workflows/ci.yml` | File exists and is valid YAML |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| mypy strict fails on initial scaffold | Medium | Medium | Set up mypy config before writing any code |
| Next.js scaffold has ESLint warnings by default | Low | Low | Configure `.eslintrc` to match project rules during bootstrap |
| Docker Compose networking issues between services | Low | Medium | Use named networks + healthchecks |
| Poetry dependency conflicts on latest stable versions | Low | Medium | Resolve at T04, never mid-feature |
