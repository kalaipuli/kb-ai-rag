# Phase 1h — Quality Transparency Task Registry

> Status: ⏳ Not Started | Phase: 1h | Estimated Days: 3–4  
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)  
> Last updated: 2026-04-26  
> Depends on: Phase 1g (eval baseline JSON must exist for end-to-end testing of T05/T06)

---

## Context

Phase 1 shows a `ConfidenceBadge` (High/Medium/Low%) per answer. This is a single aggregate scalar. The cross-encoder scores per retrieved chunk are computed but discarded before the SSE event fires. This phase surfaces those scores in the UI, adds a retrieval quality panel per answer, and shows the system-level RAGAS baseline in the sidebar — turning the chat page into a transparency surface that demonstrates retrieval quality to any viewer.

**Architect review findings incorporated:**

- `chunks_retrieved` added to the existing `citations` SSE event (not a new event type). `CitationsEvent` TypeScript type must be updated atomically with the backend change.
- Proxy route for eval baseline must be named explicitly: `frontend/src/app/api/proxy/eval/baseline/route.ts`.
- `retrieval_score` in `Citation` uses `doc.metadata.get("score")` (not `["score"]`) — mypy strict safe.
- `chain.py` citation-building duplicated in `generate()` and `astream_generate()` — extracted to `_build_citations(docs)` private method as part of this phase.
- `EvalBaseline.tsx` fetches via the Next.js server-side proxy (API key never in browser).
- Frontend tests required for: score bar present, score bar absent, panel open/close, 404 fallback in EvalBaseline.

---

## Pre-Implementation Gate (run before any code)

**Gate 1 — No duplicate Citation definition:**
```bash
grep -rn "class Citation" backend/src/ --include="*.py"
```
Expected: exactly one match (`backend/src/schemas/generation.py`).

**Gate 2 — No client instantiation in route handlers:**
```bash
grep -rn "AsyncQdrantClient(\|AzureChatOpenAI(\|AzureOpenAIEmbeddings(" \
  backend/src/api/routes/ --include="*.py"
```
Expected: zero matches.

**Gate 3 — Phase 1g gate passed:**
`data/eval_baseline.json` exists (unit tests can mock; integration test requires Phase 1g complete).

**Gate 4 — No deprecated LangChain symbols:**
```bash
grep -rn "RetrievalQA\|LLMChain\|StuffDocumentsChain" backend/src/ --include="*.py"
```
Expected: zero matches.

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Add `retrieval_score: float \| None = None` to `Citation` schema | backend-developer | — |
| T02 | ✅ Done | Extract `_build_citations(docs)` private method in `chain.py` | backend-developer | T01 |
| T03 | ✅ Done | Populate `retrieval_score` from `doc.metadata.get("score")` in `_build_citations` | backend-developer | T02 |
| T04 | ✅ Done | Add `chunks_retrieved: int` to SSE `citations` event payload | backend-developer | T02 |
| T05 | ✅ Done | New route `GET /api/v1/eval/baseline` reading `Settings.eval_baseline_path` | backend-developer | — |
| T06 | ✅ Done | Register eval router in `main.py` | backend-developer | T05 |
| T07 | ✅ Done | Update `CitationsEvent` TypeScript type with `chunks_retrieved: number` | frontend-developer | T04 |
| T08 | ✅ Done | Update `Citation` TypeScript type with `retrieval_score?: number` | frontend-developer | T01 |
| T09 | ✅ Done | Update `CitationList.tsx` — render score bar per citation | frontend-developer | T08 |
| T10 | ✅ Done | Update `ChatMessage.tsx` — collapsible quality panel with `chunks_retrieved` + source count | frontend-developer | T07, T09 |
| T11 | ✅ Done | New proxy route `frontend/src/app/api/proxy/eval/baseline/route.ts` | frontend-developer | — |
| T12 | ✅ Done | New `EvalBaseline.tsx` component (fetches via proxy, 404-safe) | frontend-developer | T11 |
| T13 | ✅ Done | Add `EvalBaseline` to `Sidebar.tsx` | frontend-developer | T12 |

---

## Ordered Execution Plan

### Batch 1 — Parallel (no dependencies)
- **T01** — Add `retrieval_score` to `Citation` schema (backend)
- **T05** — New eval baseline route (backend)
- **T11** — New eval baseline proxy route (frontend)

### Batch 2 — After T01
- **T02** — Extract `_build_citations()` private method

### Batch 3 — After T02 (parallel)
- **T03** — Populate `retrieval_score` in `_build_citations`
- **T04** — Add `chunks_retrieved` to SSE citations event

### Batch 4 — After T05
- **T06** — Register eval router in main.py

### Batch 5 — After T01/T04 backend tasks merge (parallel frontend work)
- **T07** — Update `CitationsEvent` TypeScript type (atomic with T04)
- **T08** — Update `Citation` TypeScript type (atomic with T01)

### Batch 6 — After T07, T08
- **T09** — CitationList score bars
- **T10** — ChatMessage collapsible panel

### Batch 7 — After T11
- **T12** — EvalBaseline component

### Batch 8 — After T12
- **T13** — Add EvalBaseline to Sidebar

---

## Definition of Done Per Task

### T01 — Citation schema: retrieval_score field
- [ ] `retrieval_score: float | None = None` added to `Citation` in `backend/src/schemas/generation.py`
- [ ] `test_api_schemas.py` updated: test `Citation` serialises `retrieval_score` when present and absent
- [ ] `mypy --strict` passes

### T02 — Extract _build_citations private method
- [ ] `_build_citations(docs: list[Document]) -> tuple[list[Citation], float]` private method on `GenerationChain`
- [ ] Both `generate()` and `astream_generate()` call `_build_citations` — no duplicated logic
- [ ] All existing `test_generation_chain.py` tests still pass
- [ ] `mypy --strict` passes

### T03 — Populate retrieval_score
- [ ] `doc.metadata.get("score")` used (not `doc.metadata["score"]`) — safe on missing key
- [ ] `retrieval_score=float(raw_score) if raw_score is not None else None`
- [ ] Unit test: citation has `retrieval_score` populated when `doc.metadata["score"]` present
- [ ] Unit test: citation has `retrieval_score=None` when score key absent

### T04 — chunks_retrieved in SSE event
- [ ] `chunks_retrieved=len(docs)` added to the `citations` SSE event JSON payload in `astream_generate`
- [ ] Wire format: `{"type": "citations", "citations": [...], "confidence": 0.87, "chunks_retrieved": 10}`
- [ ] Unit test: SSE citations event payload includes `chunks_retrieved`
- [ ] `mypy --strict` passes

### T05 — GET /api/v1/eval/baseline route
- [ ] New file `backend/src/api/routes/eval.py`
- [ ] Route reads `settings.eval_baseline_path` via `SettingsDep` — no hardcoded path
- [ ] Returns 404 `{"detail": "No evaluation baseline found. Run the evaluator first."}` if file missing
- [ ] Returns JSON with 5 metric scores when file exists
- [ ] Unit test: 200 with mocked baseline file content
- [ ] Unit test: 404 when file missing
- [ ] Error-path test: raises `HTTPException` when file is present but malformed JSON
- [ ] `mypy --strict` passes

### T06 — Register eval router
- [ ] `from src.api.routes.eval import router as eval_router` in `main.py`
- [ ] `app.include_router(eval_router, prefix="/api/v1")` added
- [ ] `test_main.py` confirms route is registered (GET `/api/v1/eval/baseline` returns 404 or 200)

### T07 — CitationsEvent TypeScript type
- [ ] `chunks_retrieved: number` added to `CitationsEvent` in `frontend/src/types/index.ts`
- [ ] `tsc --noEmit` passes with zero errors

### T08 — Citation TypeScript type
- [ ] `retrieval_score?: number` added to `Citation` in `frontend/src/types/index.ts`
- [ ] `tsc --noEmit` passes with zero errors

### T09 — CitationList score bars
- [ ] Score bar rendered per citation only when `retrieval_score` is defined (not undefined)
- [ ] Score bar uses a `<div>` with Tailwind width percentage (not native `<progress>` — consistent with design system)
- [ ] Label reads "Relevance" (not "Confidence") — cross-encoder score, not aggregate sigmoid
- [ ] Score displayed as percentage: `Math.round(retrieval_score * 100)`
- [ ] Test: `CitationList` renders score bar when `retrieval_score` is defined
- [ ] Test: `CitationList` renders without score bar when `retrieval_score` is undefined
- [ ] `tsc --noEmit` + `eslint` pass

### T10 — ChatMessage collapsible quality panel
- [ ] `<details>` / `<summary>` element wraps the citations + confidence section
- [ ] Summary label: "Sources (N)" where N is `message.citations.length`
- [ ] Expanded body shows: chunks retrieved (`message.chunksRetrieved`), distinct source file count (derived from citations filenames), existing `CitationList` with score bars
- [ ] `ConfidenceBadge` remains visible outside the collapsible (not hidden inside)
- [ ] Test: panel opens on click; shows correct `chunks_retrieved` value
- [ ] Test: panel renders without crashing when `chunksRetrieved` is undefined (backward compat)
- [ ] `tsc --noEmit` + `eslint` pass

### T11 — Eval baseline proxy route
- [ ] New file `frontend/src/app/api/proxy/eval/baseline/route.ts`
- [ ] `GET` handler forwards to `${process.env.BACKEND_URL}/api/v1/eval/baseline`
- [ ] API key header injected server-side (same pattern as existing proxy routes)
- [ ] Passes through 404 from backend transparently
- [ ] `tsc --noEmit` passes

### T12 — EvalBaseline component
- [ ] Fetches `/api/proxy/eval/baseline` (not backend directly)
- [ ] Renders 5 metric scores as compact rows: `Faithfulness 0.9153`, etc.
- [ ] Shows "No baseline available — run evaluator first" when 404 received
- [ ] Shows loading skeleton while fetching
- [ ] Test: renders scores when fetch succeeds
- [ ] Test: renders 404 fallback message when fetch returns 404
- [ ] `tsc --noEmit` + `eslint` pass

### T13 — Add EvalBaseline to Sidebar
- [ ] `<EvalBaseline />` added to `Sidebar.tsx` below collection stats section
- [ ] Section header: "System Quality" or "Evaluation Baseline"
- [ ] `Sidebar.test.tsx` updated: confirms EvalBaseline is rendered
- [ ] `tsc --noEmit` + `eslint` pass

---

## Phase Gate Criteria

All of the following must be true before Phase 2 begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | `pytest backend/tests/unit/ -q` | All tests green, including new eval route and chain tests |
| G02 | `mypy backend/src/ --strict` | Zero errors |
| G03 | `ruff check backend/src/ backend/tests/` | Zero warnings |
| G04 | `tsc --noEmit` (frontend) | Zero errors |
| G05 | `eslint` (frontend) | Zero warnings |
| G06 | `npm run build` (frontend) | Build succeeds |
| G07 | SSE wire format | `citations` event includes `chunks_retrieved` and `retrieval_score` per citation |
| G08 | UI manual check | Score bars visible in chat, eval baseline visible in sidebar, panel collapses/expands |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `CitationsEvent` type not updated atomically with backend, causing silent undefined | Medium | Low | Both sides in same PR; tsc will surface the gap |
| Eval baseline file absent in dev, breaking EvalBaseline UI component | High | Low | 404 handled gracefully with fallback message |
| Score bar percentage > 100% for high cross-encoder logits (logit not bounded 0–1) | Medium | Low | Clamp to `Math.min(100, Math.max(0, Math.round(score * 100)))` in component |
| Collapsible panel breaks chat message layout on narrow viewport | Low | Low | Max-width constraint already on message bubble; test at 375px |
