# Phase 1h — Architect Review Fixes

> Created: 2026-04-26 | Source: Architect review of Phase 1h implementation  
> Rule: development-process.md §9 — all critical fixes must clear before Phase 2 starts.  
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On |
|----|----------|--------|----------|---------|------------|
| F01 | High | ✅ Fixed | Docs | `ragas_eval.py` creates its own `AzureChatOpenAI` and `AzureOpenAIEmbeddings` instances outside `main.py`/`deps.py`. Accepted exception for offline tool — but no docstring documents this boundary. Must be documented before any Phase 2 route could reuse the evaluator. | — |
| F02 | High | ✅ Fixed | Tests | `EvalBaseline.test.tsx` — loading state test missing. Component renders `Loading…` while fetch is in flight; no test covers the initial render before resolution. | — |
| F03 | High | ✅ Fixed | Tests | `ChatMessage.test.tsx` — distinct-source-count display is untested. Expanded panel shows "N distinct sources" derived from unique citation filenames; no test verifies this. | — |
| F04 | Medium | ✅ Fixed | Docs | `CitationList.tsx:17` — score bar displays `retrieval_score * 100` as a percentage. Cross-encoder logits are not bounded to [0, 1], so the display is only accurate for scores in that range. Needs a Phase 2 TODO comment; sigmoid normalisation deferred. | — |
| F05 | Low | ✅ Fixed | Tests | `Sidebar.test.tsx:9` — `vi.spyOn(global, "fetch")` called at module scope; `beforeEach` uses `vi.clearAllMocks()` instead of `vi.restoreAllMocks()`. The spy is not restored between test files, risking mock leak. | — |
| F06 | Low | ✅ Fixed | Tests | `EvalBaseline.test.tsx` — no test for HTTP 500 response. A 500 body is valid JSON but shaped as `{detail: "..."}`, not `BaselineMetrics`. Without the guard (F07), this causes `TypeError` in the component. | F07 |
| F07 | Low | ✅ Fixed | Correctness | `EvalBaseline.tsx:33` — fetch chain handles 404 but not other non-2xx responses. A 500 body passes `if (data) setMetrics(data)`, then `metrics[key].toFixed(4)` throws `TypeError` at render time. | — |

---

## Detailed Fix Specifications

### F01 — ragas_eval.py: document accepted offline exception boundary (High)

**File:** `backend/src/evaluation/ragas_eval.py`  
**Issue:** `RagasEvaluator.__init__` constructs `AzureChatOpenAI` and `AzureOpenAIEmbeddings` directly. The lifespan singleton architecture rule (architecture-rules.md P2) flags client instantiation outside `main.py`/`deps.py`. This is intentional: the evaluator is an offline CLI tool that runs independently of the FastAPI lifespan.  
**Fix:** Add a class-level docstring note (or inline comment) making the accepted exception explicit:

```python
class RagasEvaluator:
    """Offline RAGAS evaluation runner.

    Constructs its own Azure OpenAI clients because it runs outside the
    FastAPI lifespan — it is invoked as a standalone script, not via a route
    handler.  If this class is ever wired into a live route it must accept
    injected clients via constructor instead of constructing its own.
    See architecture-rules.md P2.
    """
```

**Rule:** architecture-rules.md P2 — "any match outside main.py or deps.py is a High finding" with accepted exception for offline tooling; must be documented.

---

### F02 — EvalBaseline.test.tsx: loading-state test (High)

**File:** `frontend/src/components/EvalBaseline.test.tsx`  
**Issue:** No test verifies the component renders "Loading…" before fetch resolves.  
**Fix:** Add test inside the `describe("EvalBaseline")` block:

```typescript
it("renders loading state before fetch resolves", () => {
  vi.spyOn(global, "fetch").mockReturnValue(new Promise(() => {})); // never resolves
  render(<EvalBaseline />);
  expect(screen.getByText(/Loading/)).toBeInTheDocument();
});
```

**Rule:** 1h T12 DoD — "Shows loading skeleton while fetching"; CLAUDE.md §1 DoD — unit test for every observable state.

---

### F03 — ChatMessage.test.tsx: distinct-source-count test (High)

**File:** `frontend/src/components/ChatMessage.test.tsx`  
**Issue:** The expanded panel shows "N distinct sources" derived from unique filenames in `citations`. No test verifies this.  
**Fix:** Add test:

```typescript
it("shows distinct source count in expanded panel", async () => {
  const citations = [
    { chunk_id: "c1", filename: "a.pdf", source_path: "/a.pdf", page_number: 1 },
    { chunk_id: "c2", filename: "a.pdf", source_path: "/a.pdf", page_number: 2 },
    { chunk_id: "c3", filename: "b.pdf", source_path: "/b.pdf", page_number: 1 },
  ];
  render(
    <ChatMessage
      message={makeMessage({ role: "assistant", content: "Answer", citations })}
    />,
  );
  await userEvent.click(screen.getByText("Sources (3)"));
  expect(screen.getByText(/2 distinct sources/)).toBeInTheDocument();
});
```

First read `ChatMessage.tsx` to confirm the exact text format used for distinct sources before writing this test.  
**Rule:** 1h T10 DoD — "Expanded body shows... distinct source file count".

---

### F04 — CitationList.tsx: Phase 2 sigmoid TODO comment (Medium)

**File:** `frontend/src/components/CitationList.tsx:17`  
**Issue:** `Math.round(c.retrieval_score * 100)` interprets a cross-encoder logit as a percentage. Cross-encoder scores from `ms-marco-MiniLM-L-6-v2` are logits (range roughly −10 to +10), not probabilities. Multiplying by 100 is only meaningful for logits in [0, 1]. The clamp to [0, 100] already in place prevents overflow but does not fix the semantic issue. Deferred to Phase 2.  
**Fix:** Add one comment on the `scorePct` computation line:

```typescript
// TODO Phase 2: normalize cross-encoder logit to [0,1] via sigmoid before display
const scorePct =
  c.retrieval_score !== undefined
    ? Math.min(100, Math.max(0, Math.round(c.retrieval_score * 100)))
    : undefined;
```

**Rule:** Risk register entry for 1h; Phase 2 pre-condition documentation.

---

### F05 — Sidebar.test.tsx: mock isolation fix (Low)

**File:** `frontend/src/components/Sidebar.test.tsx:9`  
**Current:**
```typescript
// module-level (line 9)
vi.spyOn(global, "fetch").mockResolvedValue(...);
// beforeEach (line 22)
vi.clearAllMocks();
```
**Issue:** `clearAllMocks` clears call history but does not restore the original `fetch`. The module-level spy persists across test files when vitest shares the module context. `EvalBaseline.test.tsx` correctly uses `restoreAllMocks`.  
**Fix:**
1. Remove the module-level `vi.spyOn(global, "fetch")` call.
2. Move a fresh spy into `beforeEach`:

```typescript
beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "No evaluation baseline found." }), { status: 404 }),
  );
});
```

**Rule:** frontend-rules.md — test isolation; Vitest best practices.

---

### F06 — EvalBaseline.test.tsx: HTTP 500 error-path test (Low)

**File:** `frontend/src/components/EvalBaseline.test.tsx`  
**Depends on:** F07 (guard must be in place before the test can assert the fallback)  
**Fix:** Add test:

```typescript
it("renders fallback message when fetch returns 500", async () => {
  vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Internal Server Error" }), { status: 500 }),
  );

  render(<EvalBaseline />);

  await waitFor(() => {
    expect(screen.getByText(/No baseline available/)).toBeInTheDocument();
  });
});
```

**Rule:** CLAUDE.md §1 DoD — "at least one error-path test per external call"; 1h T12 DoD.

---

### F07 — EvalBaseline.tsx: guard non-ok responses (Low)

**File:** `frontend/src/components/EvalBaseline.tsx:29`  
**Current fetch chain:**
```typescript
.then((res) => {
  if (res.status === 404) {
    setUnavailable(true);
    return null;
  }
  return res.json() as Promise<BaselineMetrics>;
})
.then((data) => {
  if (data) setMetrics(data);
})
```
**Issue:** Any non-404 error (500, 503, etc.) falls through to `res.json()`, returns `{detail: "..."}`, passes the `if (data)` check, and sets `metrics` to an invalid shape. When the render then calls `metrics[key].toFixed(4)`, it throws `TypeError` because `metrics.faithfulness` is `undefined`.  
**Fix:**
```typescript
.then((res) => {
  if (res.status === 404) {
    setUnavailable(true);
    return null;
  }
  if (!res.ok) {
    setUnavailable(true);
    return null;
  }
  return res.json() as Promise<BaselineMetrics>;
})
```

**Rule:** frontend-rules.md — error handling for fetch; implicit DoD contract in T12 that only valid metric objects set state.

---

## Clearance Order

High fixes must clear before Phase 2 begins. Low fixes should clear in the same batch.

```
Batch 1 — Code + docs fixes (parallel, no dependencies):
  F01  F04  F07

Batch 2 — Test fixes (F06 depends on F07; others parallel):
  F02  F03  F05
  F06  (after F07)
```

## Verification Checklist

Verified 2026-04-26:
- [x] `tsc --noEmit` — zero errors
- [x] `eslint` — zero warnings
- [x] `vitest run` — 68 passed across 9 test files (up from 54; includes loading-state, 500, distinct-source tests)
- [x] `grep -rn "clearAllMocks" frontend/src/` — Sidebar.test.tsx now uses `restoreAllMocks` in `beforeEach`
