# Phase 0 — Architect Review Fixes Registry

> Status: Complete | Triggered by: Architect review 2026-04-23 | Verified: 2026-04-23
> All critical fixes applied and verified. Phase 1 may begin.

---

## Fix Overview

| # | Status | Issue | Agent | File(s) |
|---|--------|-------|-------|---------|
| C1 | ✅ Done | Sync `QdrantClient` inside `async def` — replace with `AsyncQdrantClient` | backend-developer | `src/api/routes/health.py` |
| C2 | ✅ Done | All domain exceptions map to HTTP 500 — add per-type status codes | backend-developer | `src/api/main.py` |
| C3b | ✅ Done | 422 `detail` returns `list[dict]` but `ErrorResponse.detail` is `str` | backend-developer | `src/api/main.py` |
| C6 | ✅ Done | Backend Dockerfile runs as root — add non-root user | backend-developer | `backend/Dockerfile` |
| C9 | ✅ Done | `settings` singleton — refactor to `get_settings()` + `@lru_cache` + `Depends` | backend-developer | `src/config.py`, `src/api/main.py`, `src/api/routes/health.py`, `src/api/middleware/auth.py` |
| C4 | ✅ Done | `PROJECT_PLAN.md` Phase 1a schema has `domain` field and missing fields | project-manager | `PROJECT_PLAN.md` |
| C7 | ✅ Done | `deploy.yml` triggers independently — must wait for CI to pass | project-manager | `.github/workflows/deploy.yml` |
| C8 | ✅ Done | `ragas-weekly.yml` missing `permissions: contents: write` | project-manager | `.github/workflows/ragas-weekly.yml` |
| C3f | ✅ Done | Frontend `ApiError.detail` is `string` but 422 sends `list[dict]` | frontend-developer | `frontend/src/types/index.ts` |
| C5 | ✅ Done | `NEXT_PUBLIC_API_URL` must be a build arg, not a runtime env var | frontend-developer | `frontend/Dockerfile`, `infra/docker-compose.yml` |

---

## Warning Fixes (post-Phase-1, tracked for visibility)

| # | Status | Issue | Agent |
|---|--------|-------|-------|
| W1 | ⏳ Pending | `cache_logger_on_first_use=False` — change to `True` before load testing | backend-developer |
| W2 | ⏳ Pending | `currentEventType` not reset between SSE events | frontend-developer |
| W3 | ⏳ Pending | `CORS allow_origins=["*"]` must be parameterised via settings | backend-developer |
| W4 | ⏳ Pending | Backend Dockerfile — add multi-stage builder/runner separation | backend-developer |
| W5 | ⏳ Pending | `ragas-weekly.yml` pushes directly to `main` — use bot PR instead | project-manager |
| W6 | ⏳ Pending | Phase 3+ deps in main group — move to optional groups | backend-developer |
| W7 | ⏳ Pending | `exempt_paths` security boundary needs ADR or comment | architect |
| W8 | ⏳ Pending | `PROJECT_PLAN.md` stale ADR filenames + Streamlit references | project-manager |
| W9 | ⏳ Pending | Add `Document` type to `src/retrieval/base.py` (Phase 1 prep) | backend-developer |

---

## Gate: All Critical Fixes Done

- [x] C1 — `AsyncQdrantClient` in health.py
- [x] C2 — Per-exception HTTP status codes
- [x] C3b — 422 handler returns stringified detail
- [x] C3f — Frontend `ApiError` updated
- [x] C4 — `PROJECT_PLAN.md` Phase 1a schema corrected
- [x] C5 — `NEXT_PUBLIC_API_URL` as build arg
- [x] C6 — Backend Dockerfile non-root user
- [x] C7 — `deploy.yml` waits for CI
- [x] C8 — `ragas-weekly.yml` has `permissions: contents: write`
- [x] C9 — `get_settings()` + `Depends` pattern
- [x] All backend unit tests still pass after refactor (29 passed)
- [x] `mypy src/` still passes after refactor (11 files, zero errors)
- [x] `ruff check .` still passes after refactor
- [x] `tsc --noEmit` still passes after frontend fix
