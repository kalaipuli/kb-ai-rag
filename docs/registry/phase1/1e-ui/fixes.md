# Phase 1e — Architect Review Fix Registry

> Reviewed: 2026-04-24 | Fixed: 2026-04-24 | Status: ✅ All fixes resolved
> Architect decision: F03 resolved as server-side proxy (API key never exposed to browser)

---

## Issues

| # | Severity | File(s) | Description | Agent | Status |
|---|----------|---------|-------------|-------|--------|
| F01 | **Critical** | `src/types/index.ts`, `src/lib/streaming.ts` | `QueryRequest` sends `question` but backend expects `query` — every POST /query returns 422 | frontend-developer | ✅ Done |
| F02 | **Critical** | `src/lib/streaming.ts`, `src/hooks/useStream.ts` | SSE parser tracked `event:` lines backend never emits — rewrote to parse `type` from inside JSON data object; updated `handleEvent` for discriminated union | frontend-developer | ✅ Done |
| F03 | **Critical** | `src/lib/api.ts`, `src/lib/streaming.ts`, `src/app/api/proxy/` | API key exposed to browser as empty string. Fixed with server-side Next.js proxy routes (`/api/proxy/collections`, `/api/proxy/ingest`, `/api/proxy/query`) | architect + frontend-developer | ✅ Done |
| F04 | **High** | `src/types/index.ts` | `Citation` fields corrected to match backend `CitationItem`: `chunk_id`, `filename`, `source_path`, `page_number` | frontend-developer | ✅ Done |
| F05 | **High** | `src/types/index.ts` | Removed `DonePayload`; replaced with discriminated union `TokenEvent \| CitationsEvent \| DoneEvent` | frontend-developer | ✅ Done |
| F06 | **High** | `src/lib/api.ts`, `src/lib/streaming.ts` | Duplicate `API_URL`/`API_KEY` constants extracted to `src/lib/config.ts` (server-only) | frontend-developer | ✅ Done |
| F07 | **High** | `src/lib/api.test.ts` (9 tests), `src/lib/streaming.test.ts` (11 tests) | New unit tests for `api.ts` and `streaming.ts` including all error paths | tester | ✅ Done |
| F08 | **High** | `src/hooks/useStream.ts` | Added `hadError` flag to suppress post-error SSE events and skip `STREAM_END` after `ERROR` | frontend-developer | ✅ Done |
| F09 | **High** | `.claude/docs/frontend-rules.md` | Scoped "named exports only" rule to `src/components/`; added explicit carve-out for App Router entry files in `src/app/**` | architect | ✅ Done |
| F10 | **Medium** | `src/types/index.ts`, `src/hooks/useStream.ts` | Unchecked `as` casts eliminated by discriminated union (F02/F05) | frontend-developer | ✅ Done |
| F11 | **Medium** | `src/components/CitationList.tsx` | `key={i}` → `key={c.chunk_id}`; `c.page` → `c.page_number` | frontend-developer | ✅ Done |
| F12 | **Medium** | ConfidenceBadge, CitationList, ChatMessage, ChatInput, useStream | `React.JSX.Element` / `React.Dispatch` replaced with explicit named imports from `"react"` | frontend-developer | ✅ Done |
| F13 | **Medium** | `src/lib/api.ts` | Removed orphaned `getHealth()`, `parseApiError()`, and `HealthResponse` | frontend-developer | ✅ Done |
| F14 | **Medium** | `src/hooks/useStream.test.ts`, `CitationList.test.tsx`, `ChatMessage.test.tsx` | Citation fixtures verified to use correct shape (`chunk_id`, `source_path`, `page_number`); `QueryRequest` fixtures use `query:` | tester | ✅ Done |
| F15 | **Low** | `frontend/.env.example` | Added `BACKEND_URL` and `API_KEY` with server-only comments; clarified `NEXT_PUBLIC_API_URL` points to Next.js server | frontend-developer | ✅ Done |
| F16 | **Low** | `src/hooks/useStream.test.ts` | Added test asserting `isStreaming=true` during an in-flight never-resolving stream | tester | ✅ Done |

---

## DoD Gate Result (post-fix)

| Check | Result |
|-------|--------|
| `npx tsc --noEmit` | ✅ 0 errors |
| `npx eslint src/` | ✅ 0 warnings |
| `npm run build` | ✅ Exit 0 |
| `npm run test` | ✅ 54 tests / 8 files passing |
