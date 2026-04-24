# Phase 1e — UI Task Registry

> Status: 🔄 In Progress | Phase: 1e | Estimated Days: 2–3
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-24
> Stack gate: Tier 4 frontend upgrade must be complete before T04 begins (Next.js 15 + React 19 + Tailwind 4 + ESLint 9 + TypeScript 5.8)

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Tier 4 stack upgrade — Next.js 15.3.9, React 19, Tailwind 4.1, ESLint 9, TypeScript 5.8 | frontend-developer | — |
| T02 | ✅ Done | Migrate Tailwind config → CSS @theme in globals.css | frontend-developer | T01 |
| T03 | ✅ Done | ESLint 9 flat config — create eslint.config.mjs | frontend-developer | T01 |
| T04 | ✅ Done | Extend src/types/index.ts — add CollectionInfo type for Sidebar | frontend-developer | T01 |
| T05 | ✅ Done | Extend src/lib/api.ts — add getCollections() function | frontend-developer | T04 |
| T06 | ✅ Done | Verify src/lib/streaming.ts (SSE async generator for POST /api/v1/query) | frontend-developer | T04 |
| T07 | ✅ Done | Implement src/hooks/useStream.ts — React state bridge for streaming | frontend-developer | T06 |
| T08 | ✅ Done | Implement src/components/ConfidenceBadge.tsx | frontend-developer | T04 |
| T09 | ✅ Done | Implement src/components/CitationList.tsx | frontend-developer | T04 |
| T10 | ✅ Done | Implement src/components/ChatMessage.tsx — uses CitationList + ConfidenceBadge | frontend-developer | T08, T09 |
| T11 | ✅ Done | Implement src/components/ChatInput.tsx | frontend-developer | T07 |
| T12 | ✅ Done | Implement src/components/Sidebar.tsx — collection stats + ingest trigger | frontend-developer | T05 |
| T13 | ✅ Done | Wire src/app/chat/page.tsx — compose all components with useStream | frontend-developer | T07, T10, T11, T12 |
| T14 | ✅ Done | Write unit tests for useStream hook | tester | T07 |
| T15 | ✅ Done | Write component tests for ConfidenceBadge, CitationList, ChatMessage | tester | T10 |
| T16 | ✅ Done | Write component tests for ChatInput and Sidebar | tester | T11, T12 |
| T17 | ✅ Done | DoD gate: tsc --noEmit zero errors + eslint zero warnings + npm run build | frontend-developer | T13, T14, T15, T16 |
| T18 | ✅ Done | Commit all 1e changes (Conventional Commits) + update DASHBOARD.md | project-manager | T17 |
| T19 | ✅ Done | Architect review — 16 findings raised + all resolved (see fixes.md) | architect + frontend-developer + tester | T18 |

---

## Ordered Execution Plan

### Batch 0 — Stack Prerequisite (complete before any component code)
- **T01** — Tier 4 stack upgrade ✅
- **T02** — Tailwind 4 CSS-first config migration ✅
- **T03** — ESLint 9 flat config ✅

### Batch 1 — Types and API (parallel, after T01)
- **T04** — Extend src/types/index.ts with CollectionInfo
- **T05** — Extend src/lib/api.ts with getCollections()

### Batch 2 — Core streaming lib + hook (sequential)
- **T06** — Verify src/lib/streaming.ts
- **T07** — Implement src/hooks/useStream.ts

### Batch 3 — Leaf components (parallel, after T04)
- **T08** — ConfidenceBadge.tsx
- **T09** — CitationList.tsx
- **T10** — ChatMessage.tsx (after T08, T09)

### Batch 4 — Interactive components (parallel, after T07/T05)
- **T11** — ChatInput.tsx (after T07)
- **T12** — Sidebar.tsx (after T05)

### Batch 5 — Page wiring
- **T13** — chat/page.tsx (after T07, T10, T11, T12)

### Batch 6 — Tests (parallel after respective implementations)
- **T14** — useStream tests (after T07)
- **T15** — ConfidenceBadge + CitationList + ChatMessage tests (after T10)
- **T16** — ChatInput + Sidebar tests (after T11, T12)

### Batch 7 — DoD gate
- **T17** — tsc + eslint + build (after T13, T14, T15, T16)

### Batch 8 — Close out
- **T18** — Commit + DASHBOARD.md update (after T17)

---

## Definition of Done Per Task

Each task must also satisfy the global DoD from CLAUDE.md §7 (ruff/mypy apply to backend only; tsc + eslint apply to frontend).

### T01 — Tier 4 stack upgrade
- [x] package.json updated: next 15.3.9, react/react-dom ^19.1.0, tailwindcss ^4.1.0, eslint ^9.0.0, typescript ^5.8.3
- [x] autoprefixer removed; @tailwindcss/postcss added
- [x] npm install succeeds with no critical errors
- [x] tsc --noEmit: zero errors
- [x] eslint src/: zero warnings

### T02 — Tailwind 4 config migration
- [x] tailwind.config.ts deleted
- [x] globals.css uses @import "tailwindcss" + @theme block
- [x] postcss.config.mjs uses @tailwindcss/postcss only

### T03 — ESLint 9 flat config
- [x] eslint.config.mjs created with FlatCompat adapter
- [x] eslint src/: zero warnings

### T04 — Extend types/index.ts
- [ ] CollectionInfo interface added: { name: string; vectors_count: number; points_count: number }
- [ ] CollectionsResponse interface added: { collections: CollectionInfo[] }
- [ ] tsc --noEmit: zero errors after addition

### T05 — Extend api.ts
- [ ] getCollections() added — returns CollectionsResponse
- [ ] No fetch() calls inside components (rule: all fetch in src/lib/api.ts only)
- [ ] tsc --noEmit: zero errors

### T06 — Verify streaming.ts
- [ ] streamQuery() correctly parses SSE: event: token/citations/done + data: …
- [ ] onError callback used for network failures and non-ok responses
- [ ] reader.releaseLock() called in finally block
- [ ] tsc --noEmit: zero errors

### T07 — useStream hook
- [ ] useStream() returns { tokens, citations, confidence, isStreaming, error, submit }
- [ ] useOptimistic used to append user message immediately before SSE starts
- [ ] useMutation drives the async generator consumption
- [ ] tsc --noEmit: zero errors

### T08 — ConfidenceBadge
- [ ] Named export: ConfidenceBadge
- [ ] Props: { confidence: number } — confidence is 0.0–1.0
- [ ] Visual: colour-coded (green ≥0.8, amber 0.5–0.8, red <0.5)
- [ ] tsc --noEmit: zero errors; eslint: zero warnings

### T09 — CitationList
- [ ] Named export: CitationList
- [ ] Props: { citations: Citation[] }
- [ ] Renders filename + page number per source (page null → "—")
- [ ] tsc --noEmit: zero errors; eslint: zero warnings

### T10 — ChatMessage
- [ ] Named export: ChatMessage
- [ ] Props: { message: Message }
- [ ] User messages: right-aligned bubble; assistant messages: left-aligned with CitationList + ConfidenceBadge
- [ ] tsc --noEmit: zero errors; eslint: zero warnings

### T11 — ChatInput
- [ ] Named export: ChatInput
- [ ] Props: { onSubmit: (question: string) => void; disabled: boolean }
- [ ] Textarea + submit button; Enter submits, Shift+Enter newline
- [ ] Disabled during streaming
- [ ] tsc --noEmit: zero errors; eslint: zero warnings

### T12 — Sidebar
- [ ] Named export: Sidebar
- [ ] Shows collection name + doc count from getCollections()
- [ ] Ingest trigger button — calls triggerIngest(), shows loading state
- [ ] tsc --noEmit: zero errors; eslint: zero warnings

### T13 — chat/page.tsx
- [ ] Replaces placeholder with full chat layout: Sidebar (left) + chat area (right)
- [ ] QueryClientProvider wraps page for @tanstack/react-query
- [ ] useStream provides state; ChatInput.onSubmit calls useStream.submit
- [ ] Message list renders ChatMessage for each Message
- [ ] tsc --noEmit: zero errors; eslint: zero warnings

### T14 — useStream tests
- [ ] Test: submit() sets isStreaming=true, accumulates token events into tokens
- [ ] Test: citations event updates citations array
- [ ] Test: done event sets isStreaming=false and confidence
- [ ] Test (error path): network error sets error state

### T15 — Component tests (badges + messages)
- [ ] ConfidenceBadge: renders green for 0.9, amber for 0.6, red for 0.3
- [ ] CitationList: renders filename + page; renders "—" for null page
- [ ] ChatMessage: user message right-aligned; assistant message shows citations

### T16 — Component tests (input + sidebar)
- [ ] ChatInput: Enter submits; Shift+Enter does not submit; disabled when prop is true
- [ ] Sidebar: renders collection name + count; ingest button shows loading

### T17 — DoD gate
- [ ] tsc --noEmit: zero errors
- [ ] eslint src/: zero warnings
- [ ] npm run build: exits 0

### T18 — Commit
- [ ] Git branch: feature/1e-ui
- [ ] Conventional Commits: feat(ui): implement Phase 1e chat interface
- [ ] DASHBOARD.md updated: 1e status → ✅ Done or In Progress (whichever is correct)

---

## Phase Gate Criteria (MVP — required before Phase 2)

All of the following must pass before Phase 2 begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | Ingest 30+ local files end-to-end | No errors |
| G02 | POST /query returns answer + citations | < 8s P95 locally |
| G03 | RAGAS faithfulness | ≥ 0.70 |
| G04 | API key auth | Unauthenticated requests blocked (401) |
| G05 | docker compose up (full stack) | Running in < 90s |
| G06 | Phase 1f evaluation baseline | RAGAS run complete, results in docs/evaluation_results.md |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| React 19 + @tanstack/react-query compat issue | Low | Medium | useQuery/useMutation API is stable in v5; no breaking changes for our usage |
| Tailwind 4 CSS-first config missing utility classes | Medium | Low | Run npm run build and scan for missing styles; add explicit @source if needed |
| SSE ReadableStream not available in test environment | Medium | High | Mock fetch in tests; test streaming logic separately from React state |
| Next.js 15 async params breaking page | Low | Medium | chat/page.tsx has no params; layout.tsx uses no async APIs |
