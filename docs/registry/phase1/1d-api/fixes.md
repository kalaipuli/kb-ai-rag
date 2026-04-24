# Phase 1d — Architect Review Fixes

> Created: 2026-04-24 | Source: Architect review of Phase 1d implementation
> Rule: development-process.md §9 — all critical fixes must clear before Phase 1e/Phase 2 starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On |
|----|----------|--------|----------|---------|------------|
| F01 | Critical | ✅ Fixed | Correctness | `api_key=settings.azure_openai_api_key` missing `.get_secret_value()` — confirmed: `AzureChatOpenAI` accepts `SecretStr` natively; DoD item wording was incorrect. Verified by mypy. | — |
| F02 | Major | ✅ Fixed | Correctness | SSE stream now wrapped in `try/except GenerationError`; yields `done` event on error and logs via structlog | F01 |
| F03 | Major | ✅ Fixed | Correctness | `run_pipeline` accepts `bm25_store` param; ingest route passes `app.state.bm25_store` so lifespan singleton is updated in-place after each ingest | — |
| F04 | Major | ✅ Fixed | Correctness | Health route now uses `QdrantClientDep` from deps.py — no per-request client creation | — |
| F05 | Minor | ✅ Fixed | Correctness | Collections route wraps each `get_collection()` call in `try/except`; logs warning and includes collection with zeroed counts on failure — returns partial results instead of 503 | — |
| F06 | Minor | ✅ Fixed | Correctness | Single `_settings = get_settings()` at top of main.py; used consistently for CORSMiddleware and lifespan | — |
| F07 | Major | ✅ Fixed | Architecture | `health.py` migrated to `SettingsDep`; `# noqa: B008` removed | — |
| F08 | Major | ✅ Fixed | Architecture | `ragas` moved to `[tool.poetry.group.eval.dependencies]` in pyproject.toml | — |
| F09 | Minor | ✅ Fixed | Architecture | `secrets.compare_digest` replaces `!=` in auth middleware | — |
| F10 | Major | ✅ Fixed | Tests | Unit tests added for all 4 schemas in `test_api_schemas.py` | F05 |
| F11 | Major | ✅ Fixed | Tests | SSE error-path test added; async generator stub used (not `AsyncMock`) to correctly simulate `GenerationError` mid-iteration | F02 |
| F12 | Major | ✅ Fixed | Tests | Tests added for missing `query` field (→ 422) and empty string (→ 422); `min_length=1` added to `QueryRequest.query` | — |
| F13 | Minor | ✅ Fixed | Tests | `run_pipeline` patched with `new_callable=AsyncMock` in all ingest tests | — |
| F14 | Minor | ✅ Fixed | Tests | Test added confirming 202 returned for invalid `data_dir` path | — |
| F15 | Minor | ✅ Fixed | Tests | Partial `get_collection` failure test added; asserts 200 + partial results | F05 |
| F16 | Minor | ✅ Fixed | Style | `pytestmark = pytest.mark.asyncio` moved to module level in `test_generation_chain.py` | — |
| F17 | Observation | ✅ Fixed | Registry | T02, T05, T07 notes added in tasks.md with DoD gap explanations; fixes.md linked from tasks.md header | F01, F07, F10 |

---

## Detailed Fix Specifications

### F01 — SecretStr unwrap in chain.py (Critical)

**File:** `backend/src/generation/chain.py:120`
**Current:** `api_key=settings.azure_openai_api_key`
**Fix:** `api_key=settings.azure_openai_api_key.get_secret_value()`
**Rule:** T02 DoD item; python-rules.md — no bare `SecretStr` passed to third-party clients

---

### F02 — SSE stream error handling in query route (Major)

**Files:** `backend/src/api/routes/query.py`, `backend/src/generation/chain.py:276-280`
**Issue:** When `astream_generate` raises `GenerationError` mid-stream, the exception escapes the async generator. FastAPI's `StreamingResponse` silently closes the stream — client receives no `done` event.
**Fix (must respect architecture-rules.md — three SSE event types only: token, citations, done):**
- Wrap the generator body in `_stream()` with `try/except GenerationError`
- On error: log via structlog with error details
- Yield `data: {"type": "done"}\n\n` to close the stream cleanly
- Do NOT add a 4th event type without writing an ADR
**Rule:** python-rules.md — "Never silently swallow exceptions — at minimum log and re-raise"; architecture-rules.md SSE contract

---

### F03 — BM25 singleton staleness after ingest (Major)

**Files:** `backend/src/ingestion/pipeline.py:99,150`, `backend/src/api/main.py:49-56`
**Issue:** `run_pipeline` creates a new `BM25Store` internally, builds/persists it, then discards it. The lifespan singleton on `app.state` is never updated, so the running retriever has a stale sparse index after every ingest.
**Fix:**
- The ingest route (`POST /api/v1/ingest`) should pass `app.state.bm25_store` (the live singleton) to `run_pipeline` as a parameter
- `run_pipeline` should call `bm25_store.rebuild(documents)` (or equivalent) so the live instance is updated in-place
- Confirm the `BM25Store` API supports in-place rebuild; if it only supports construction, replace it on `app.state` after ingest
**Rule:** architecture-rules.md — lifespan singletons are the single source of state

---

### F04 — Health route Qdrant client churn (Major)

**File:** `backend/src/api/routes/health.py:35-37`
**Issue:** Creates a new `AsyncQdrantClient` per health probe request.
**Fix:** Inject `QdrantClientDep` from `deps.py` and use the lifespan singleton instead.
**Rule:** architecture-rules.md — Tier 2 pattern, lifespan singletons on `app.state`

---

### F05 — Collections per-collection error isolation (Minor)

**File:** `backend/src/api/routes/collections.py:21-27`
**Issue:** Any single `get_collection(col.name)` failure inside the batch loop returns 503 for all collections.
**Fix:** Move the `get_collection()` call into a per-collection `try/except` block. Log individual failures with structlog and continue iterating, returning partial results.
**Rule:** python-rules.md error handling; resilience for a liveness-adjacent endpoint

---

### F06 — CORS settings import-time call (Minor)

**File:** `backend/src/api/main.py:80`
**Issue:** `get_settings()` called at module import time for `CORSMiddleware` setup — env var overrides applied after import won't take effect (relevant in test environments).
**Fix:** Resolve once at the top of `main.py` as `_settings = get_settings()` before app creation, and use `_settings.cors_origins` consistently for both the middleware and the lifespan, so there is a single call site.
**Rule:** architecture-rules.md — config isolation via pydantic-settings; no inconsistent state between startup paths

---

### F07 — health.py must use SettingsDep (Major)

**File:** `backend/src/api/routes/health.py:23`
**Current:** `settings: Settings = Depends(get_settings)  # noqa: B008`
**Fix:** `settings: SettingsDep` imported from `src.api.deps`
**Remove** the `# noqa: B008` comment.
**Rule:** T07 DoD; stack-upgrade-proposal Tier 2 T2-2; anti-patterns.md — no `# noqa` suppression

---

### F08 — ragas must move to eval dep group (Major)

**File:** `backend/pyproject.toml`
**Issue:** `ragas` is in main `[tool.poetry.dependencies]` — must move to eval group.
**Fix:** Create or use `[tool.poetry.group.eval.dependencies]` group, move `ragas = "^0.2"` there.
**Rule:** DASHBOARD.md hold item; development-process.md §5 — phase gate compliance; PROJECT_PLAN.md Phase 5 pre-requisite

---

### F09 — Timing-safe API key comparison (Minor)

**File:** `backend/src/api/middleware/auth.py:48`
**Current:** `api_key != settings.api_key.get_secret_value()`
**Fix:** `not secrets.compare_digest(api_key, settings.api_key.get_secret_value())`
**Import:** `import secrets` (stdlib, no new dep)
**Rule:** GOAL.md — "Production thinking (auth, observability, error handling)"

---

### F10 — Schema unit tests for 4 new Phase 1d types (Major)

**File:** `backend/tests/unit/test_api_schemas.py`
**Issue:** `IngestRequest`, `IngestAcceptedResponse`, `CollectionInfo`, `CollectionsResponse` have zero tests.
**Fix:** Add test classes covering: required vs optional fields, default values, serialisation.
**Rule:** development-process.md §3 — every task has at least one test; T05 DoD

---

### F11 — SSE error path test (Major)

**File:** `backend/tests/unit/test_api_query.py`
**Issue:** No test asserts what happens when `astream_generate` raises mid-stream.
**Fix (after F02 is applied):** Add test mocking `astream_generate` to raise `GenerationError`. Assert the stream closes with a `done` event and that the error is logged.
**Rule:** development-process.md §3 — test behaviour including error paths; T09 DoD

---

### F12 — Empty/missing query validation test (Major)

**File:** `backend/tests/unit/test_api_query.py`
**Fix:** Add tests: (a) missing `query` field → 422; (b) empty string `""` → either 422 (if `min_length=1` validator added) or document as accepted by design.
**Note:** If empty string is allowed by design, add `min_length=1` to `QueryRequest.query` so the behaviour is explicit.
**Rule:** development-process.md §3 — test edge cases

---

### F13 — AsyncMock for run_pipeline in ingest tests (Minor)

**File:** `backend/tests/unit/test_api_ingest.py`
**Current:** `patch("src.api.routes.ingest.run_pipeline")` uses default `MagicMock`
**Fix:** `patch("src.api.routes.ingest.run_pipeline", new_callable=AsyncMock)`
**Rule:** development-process.md §3 — test the actual contract

---

### F14 — Invalid data_dir test (Minor)

**File:** `backend/tests/unit/test_api_ingest.py`
**Fix:** Add test with `data_dir="/completely/invalid/path/xyz"` confirming 202 returned immediately and error surfaces only in the background task.
**Rule:** development-process.md §3 — test behaviour on invalid inputs

---

### F15 — Partial collection failure test (Minor)

**File:** `backend/tests/unit/test_api_collections.py`
**Fix (after F05 is applied):** Add test where `get_collections` returns two names, `get_collection` raises for one. Assert partial results returned (not 503).
**Rule:** development-process.md §3 — test observable failure modes

---

### F16 — pytest.mark.asyncio consistency (Minor)

**File:** `backend/tests/unit/test_generation_chain.py:375`
**Issue:** `pytestmark = pytest.mark.asyncio` used at class level in `TestGenerationChainStream`, inconsistent with per-method marks used in `TestKBRetriever` and `TestGenerationChain` in the same file.
**Fix:** Move `pytestmark = pytest.mark.asyncio` to module level (covers all async tests in the file), removing the class-level placement.
**Rule:** python-rules.md — consistency; development-process.md §3

---

### F17 — Reopen T02, T05, T07 in task registry (Observation)

**File:** `docs/registry/phase1/1d-api/tasks.md`
**Fix:** After F01 and F07 are applied, update T02 and T07 status in tasks.md to ✅ Done with a note that the DoD gap was resolved via fixes.md. After F10 (schema tests) is applied, T05 can be confirmed done.
**Rule:** development-process.md §7 and §9 — task must not reach ✅ Done unless every DoD item is satisfied

---

## Clearance Order

Critical and Major fixes must clear before Phase 1e continues and before Phase 2 starts.

```
Batch 1 — Code fixes (parallel):
  F01  F03  F04  F06  F07  F08  F09

Batch 2 — Depends on Batch 1:
  F02  (depends on F01 — chain.py settled)
  F05  (minor, independent)

Batch 3 — Test fixes (after code fixes stable):
  F10  F11  F12  F13  F14  F15  F16

Batch 4 — Registry:
  F17  (after all fixes applied and verified)
```

## Verification Checklist

Verified 2026-04-24:
- [x] `ruff check backend/src/ backend/tests/` — zero warnings
- [x] `mypy backend/src/` — zero errors (37 source files)
- [x] `pytest backend/tests/unit/ -q` — 177 passed (up from 162)
- [x] `ragas` no longer appears in `[tool.poetry.dependencies]`
- [x] health.py has no `# noqa` comment
- [x] `secrets.compare_digest` in auth.py
- [x] SSE stream yields `done` event on `GenerationError`
