# Phase 2h — Score Data Model Fix Task Registry

> Status: ⏳ Not Started | Phase: 2h | Estimated Days: 1–2
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-05-02

## Context

Architect review identified six structural design issues (D01–D06) in how relevance scores flow through the agentic pipeline. The core problem: `Citation.retrieval_score` carries two incompatible semantics (LLM grader judgment in the agentic chain; cross-encoder sigmoid in the static chain), `GraderStepPayload.web_fallback` maps to the wrong state field, the grader node mutates `Document` objects in-place bypassing LangGraph state management, and the raw cross-encoder logit leaks into doc metadata where it has no stable contract.

**Goal:** Make both pipelines use the same signal — `sigmoid(cross_encoder_logit)` — for the displayed "Relevance %" in citations and the grader scorecard. Separate `grader_score` into its own named field so downstream consumers have unambiguous access to each signal.

**Root cause findings:** D01 (two metadata keys in retriever), D02 (grader writes a different key, generator resolves conflict in wrong layer), D03 (wrong state field in GraderStepPayload), D04 (scores list has no pass/fail split), D05 (Citation.retrieval_score overloaded), D06 (in-place doc mutation).

---

## Task Overview

| ID  | Status     | Task                                                              | Agent              | Depends On    |
|-----|------------|-------------------------------------------------------------------|--------------------|---------------|
| T01 | ⏳ Pending | Fix `Citation` schema — add `grader_score` field                 | backend-developer  | —             |
| T02 | ⏳ Pending | Fix `GraderStepPayload` schema — rename and add fields           | backend-developer  | —             |
| T03 | ⏳ Pending | Fix retriever node — remove raw `score` from doc metadata        | backend-developer  | —             |
| T04 | ⏳ Pending | Fix grader node — stop in-place mutation, write new Document objects | backend-developer | —          |
| T05 | ⏳ Pending | Fix generator node — populate both Citation fields, no selection logic | backend-developer | T01, T03, T04 |
| T06 | ⏳ Pending | Fix static chain — store `retrieval_score` directly in KBRetriever | backend-developer | T01           |
| T07 | ⏳ Pending | Fix agentic route — pass correct fields into GraderStepPayload   | backend-developer  | T02, T04      |
| T08 | ⏳ Pending | Update frontend types — Citation and GraderStepPayload           | frontend-developer | T01, T02      |
| T09 | ⏳ Pending | Fix GraderCard — use `scores_all`, `passed_count`, `threshold`   | frontend-developer | T08           |
| T10 | ⏳ Pending | Fix AgentVerdict — replace `web_fallback` with retriever strategy | frontend-developer | T08           |
| T11 | ⏳ Pending | Verify CitationList — confirm `retrieval_score` is cross-encoder for both pipelines | frontend-developer | T08 |
| T12 | ⏳ Pending | Update backend unit tests                                         | backend-developer  | T03–T07       |
| T13 | ⏳ Pending | Update frontend component tests                                   | frontend-developer | T09–T11       |

---

## Ordered Execution Plan

### Batch 1 — Parallel (no dependencies between tasks)

- **T01** — Add `grader_score: float | None = None` to `Citation` in `backend/src/api/schemas/__init__.py`
- **T02** — Rewrite `GraderStepPayload` in `backend/src/api/schemas/agentic.py`
- **T03** — Remove raw `score` key from `_result_to_document` in `backend/src/graph/nodes/retriever.py`
- **T04** — Fix in-place mutation in `backend/src/graph/nodes/grader.py`

### Batch 2 — After T01, T03, T04

- **T05** — Fix `_build_citations` in `backend/src/graph/nodes/generator.py`

### Batch 2 — After T01 (parallel with T05)

- **T06** — Fix `KBRetriever` and `_build_citations` in `backend/src/generation/chain.py`

### Batch 3 — After T02, T04

- **T07** — Fix `_build_agent_step_event` GRADER branch in `backend/src/api/routes/query_agentic.py`

### Batch 4 — After T01, T02

- **T08** — Update `frontend/src/types/index.ts`

### Batch 5 — After T08

- **T09** — Fix `GraderCard` in `frontend/src/components/AgentTrace.tsx`
- **T10** — Fix `AgentVerdict` in `frontend/src/components/AgentVerdict.tsx`
- **T11** — Verify `CitationList` in `frontend/src/components/CitationList.tsx`

### Batch 6 — After T03–T07 complete

- **T12** — Update backend unit tests

### Batch 7 — After T09–T11 complete

- **T13** — Update frontend component tests

---

## Detailed Task Specifications

---

### T01 — Fix `Citation` schema

**File:** `backend/src/api/schemas/__init__.py`

**Change:** Add a second score field to the `Citation` model:

```python
class Citation(BaseModel):
    chunk_id: str
    filename: str
    source_path: str
    page_number: int | None = None
    retrieval_score: float | None = None   # sigmoid(cross_encoder_logit) — both pipelines
    grader_score: float | None = None      # LLM relevance judgment — agentic pipeline only
```

**Rule:** Schema Ownership — `Citation` is the canonical shared type; no re-declaration elsewhere.

**DoD:**
- [ ] `grader_score: float | None = None` added to `Citation`
- [ ] `retrieval_score` doc comment clarified to state "sigmoid(cross_encoder_logit)"
- [ ] No duplicate `Citation` class anywhere in `backend/src/` (gate check)
- [ ] `mypy --strict` passes on `schemas/__init__.py`

---

### T02 — Fix `GraderStepPayload` schema

**File:** `backend/src/api/schemas/agentic.py`

**Change:** Replace the existing `GraderStepPayload`:

```python
# Before
class GraderStepPayload(BaseModel):
    scores: list[float]
    web_fallback: bool
    duration_ms: int

# After
class GraderStepPayload(BaseModel):
    scores_all: list[float]        # one score per retrieved doc (includes below-threshold docs)
    passed_count: int              # number of docs that met the threshold
    threshold: float               # the grader_threshold setting value used in this run
    all_below_threshold: bool      # True when every score was below threshold (CRAG trigger signal)
    duration_ms: int
```

**Why:** `web_fallback` was populated from `all_below_threshold` (a trigger condition, not an execution outcome). Renaming it removes the semantic confusion. `passed_count` and `threshold` give the UI a self-contained interpretation without client-side threshold knowledge.

**DoD:**
- [ ] `web_fallback` field removed from `GraderStepPayload`
- [ ] `scores_all`, `passed_count`, `threshold`, `all_below_threshold` fields present with correct types
- [ ] `mypy --strict` passes on `schemas/agentic.py`
- [ ] `GeneratorStepPayload.confidence` and `CriticStepPayload.hallucination_risk` still carry `Field(ge=0.0, le=1.0)` validators (no regression)

---

### T03 — Fix retriever node doc metadata

**File:** `backend/src/graph/nodes/retriever.py`

**Change:** In `_result_to_document`, remove the raw `score` key; retain only `retrieval_score`:

```python
# Before
metadata: dict[str, Any] = {
    "chunk_id": result.chunk_id,
    "score": result.score,
    "retrieval_score": 1.0 / (1.0 + math.exp(-result.score)),
}

# After
metadata: dict[str, Any] = {
    "chunk_id": result.chunk_id,
    "retrieval_score": 1.0 / (1.0 + math.exp(-result.score)),
}
```

Web path (Tavily) already writes `retrieval_score` directly — no change required there, but verify the `score` key is also absent from the web path.

**Why:** `score` (raw logit, unbounded) has no stable contract downstream. Consumers that accidentally read `score` and apply sigmoid will double-transform. One key, one meaning.

**DoD:**
- [ ] `"score"` key absent from all `Document` metadata produced by `_result_to_document`
- [ ] `"score"` key absent from Tavily `Document` metadata (web path)
- [ ] `retrieval_score` present and in [0.0, 1.0] for hybrid/dense results
- [ ] `retrieval_score` present for web results (raw Tavily score, already [0,1])
- [ ] No other file reads `doc.metadata["score"]` after this change (grep check)
- [ ] Unit tests for `_result_to_document` updated and passing

---

### T04 — Fix grader node — stop in-place mutation

**File:** `backend/src/graph/nodes/grader.py`

**Change:** Replace in-place mutation of `doc.metadata` with new `Document` objects in `graded_docs`:

```python
# Before
graded_docs = []
for doc, score in zip(docs, scores, strict=True):
    if score >= settings.grader_threshold:
        doc.metadata["grader_score"] = float(score)   # mutates retrieved_docs in-place
        graded_docs.append(doc)

# After
from langchain_core.documents import Document

graded_docs = []
for doc, score in zip(docs, scores, strict=True):
    if score >= settings.grader_threshold:
        new_meta = {**doc.metadata, "grader_score": float(score)}
        graded_docs.append(Document(page_content=doc.page_content, metadata=new_meta))
```

**Why:** `docs` is a slice of `retrieved_docs` which is accumulated in AgentState via `operator.add`. Mutating those objects means the grader's score bleeds into the accumulating state without going through a state-update dict, bypassing LangGraph's checkpointing and making retry semantics unpredictable.

**DoD:**
- [ ] `doc.metadata` is never mutated in `grader_node` — all writes go to new dict via `{**doc.metadata, ...}`
- [ ] `graded_docs` contains new `Document` objects; the original `docs` list objects are unchanged
- [ ] Objects in `retrieved_docs` and `graded_docs` do not share identity (assert in tests)
- [ ] `grader_score` key present in `graded_docs[i].metadata` for all passing docs
- [ ] `grader_score` key absent from any doc in `retrieved_docs` (the accumulated list)
- [ ] All existing grader unit tests pass; add one test asserting no shared object identity

---

### T05 — Fix generator node citation builder

**File:** `backend/src/graph/nodes/generator.py`

**Change:** Replace conditional score-selection logic with direct reads into two Citation fields:

```python
# Before
grader_score: float | None = meta.get("grader_score")
retrieval_score: float | None = grader_score if grader_score is not None else (meta.get("retrieval_score") or meta.get("score"))
citations.append(Citation(
    chunk_id=chunk_id,
    filename=filename,
    source_path=raw_path,
    page_number=page_number,
    retrieval_score=retrieval_score,
))

# After
citations.append(Citation(
    chunk_id=chunk_id,
    filename=filename,
    source_path=raw_path,
    page_number=page_number,
    retrieval_score=meta.get("retrieval_score"),
    grader_score=meta.get("grader_score"),
))
```

**Why:** The generator must not adjudicate which upstream score signal wins. Each node writes one key it owns; the generator reads both keys and populates both Citation fields. Zero conditional logic.

**DoD:**
- [ ] `_build_citations` contains no ternary score-selection logic
- [ ] `Citation.retrieval_score` is populated from `meta.get("retrieval_score")` directly
- [ ] `Citation.grader_score` is populated from `meta.get("grader_score")` directly (None for web docs without grader score)
- [ ] `math` import removed if no longer used in `generator.py` after this change
- [ ] Unit tests updated: verify both fields on citations; verify `grader_score` is None when doc has no grader annotation

---

### T06 — Fix static chain — store `retrieval_score` in KBRetriever

**File:** `backend/src/generation/chain.py`

**Change 1 — `KBRetriever._aget_relevant_documents`:** Store `retrieval_score = sigmoid(r.score)` directly; remove raw `score` key:

```python
# Before
metadata={
    "chunk_id": r.metadata["chunk_id"],
    ...
    "score": r.score,   # raw logit
}

# After
import math
metadata={
    "chunk_id": r.metadata["chunk_id"],
    ...
    "retrieval_score": float(1.0 / (1.0 + math.exp(-float(r.score)))),
}
```

**Change 2 — `GenerationChain._build_citations`:** Read `retrieval_score` directly; remove sigmoid recomputation:

```python
# Before
raw_score = doc.metadata.get("score")
retrieval_score=(
    float(1.0 / (1.0 + math.exp(-float(raw_score)))) if raw_score is not None else None
)

# After
retrieval_score=doc.metadata.get("retrieval_score"),
```

**Change 3 — `GenerationChain._build_citations`:** Confidence computation currently reads `doc.metadata.get("score", 0.0)` for the top-3 mean. After removing `score`, read `retrieval_score` instead. Note: confidence is `sigmoid(mean_logit)` — after this change, mean of already-sigmoidised values is used. Document this intentional change.

**Why:** The static chain should follow the same pattern as the agentic chain: normalize once at the retriever boundary, pass `retrieval_score` downstream. Both pipelines now write and read the same key.

**DoD:**
- [ ] `"score"` key absent from all `Document` metadata produced by `KBRetriever`
- [ ] `"retrieval_score"` present and equal to `sigmoid(r.score)` in `KBRetriever` output
- [ ] `_build_citations` reads `meta.get("retrieval_score")` with no sigmoid recomputation
- [ ] `Citation.grader_score` is `None` for all static chain citations (static chain has no grader)
- [ ] Confidence calculation updated to use `retrieval_score` values; change documented in code comment
- [ ] Static chain unit tests pass; verify `retrieval_score` in citations

---

### T07 — Fix agentic route GraderStepPayload construction

**File:** `backend/src/api/routes/query_agentic.py`

**Change:** Update the GRADER branch of `_build_agent_step_event` to pass the new payload fields. Accumulate `web_fallback_used` from the retriever delta to remove it from the grader payload entirely:

```python
# In _stream(), add accumulator at top:
_web_fallback_used: bool = False

# In RETRIEVER branch, update accumulator:
_web_fallback_used = bool(state_update.get("web_fallback_used", False))

# Pass _web_fallback_used to _build_agent_step_event for RETRIEVER node if needed,
# or surface via RetrieverStepPayload.strategy == "web" (already present).

# In _build_agent_step_event GRADER branch:
if node_name == GRADER:
    settings = get_settings()
    return AgentStepEvent(
        node=GRADER,
        run=run,
        payload=GraderStepPayload(
            scores_all=state_update.get("grader_scores", []),
            passed_count=len(state_update.get("graded_docs", [])),
            threshold=settings.grader_threshold,
            all_below_threshold=bool(state_update.get("all_below_threshold", False)),
            duration_ms=duration_ms,
        ),
    )
```

**DoD:**
- [ ] `GraderStepPayload` constructed with `scores_all`, `passed_count`, `threshold`, `all_below_threshold`
- [ ] `web_fallback` field no longer referenced anywhere in `query_agentic.py`
- [ ] `passed_count` equals `len(graded_docs)` from state update
- [ ] `threshold` sourced from `get_settings().grader_threshold`
- [ ] `all_below_threshold` sourced from `state_update.get("all_below_threshold", False)`
- [ ] Unit tests for `_build_agent_step_event` GRADER branch updated

---

### T08 — Update frontend types

**File:** `frontend/src/types/index.ts`

**Changes:**

```typescript
// Citation — add grader_score
export interface Citation {
  chunk_id: string;
  filename: string;
  source_path: string;
  page_number: number | null;
  retrieval_score?: number;   // sigmoid(cross_encoder_logit) — both pipelines
  grader_score?: number;      // LLM relevance judgment — agentic pipeline only
}

// GraderStepPayload — new shape
export interface GraderStepPayload {
  scores_all: number[];       // one per retrieved doc
  passed_count: number;       // docs that met threshold
  threshold: number;          // grader_threshold value
  all_below_threshold: boolean;
  duration_ms: number;
}
```

**DoD:**
- [ ] `Citation.grader_score?: number` added
- [ ] `GraderStepPayload` fields match T02 backend schema exactly
- [ ] `web_fallback` removed from `GraderStepPayload`
- [ ] `tsc --noEmit` passes with zero errors
- [ ] `agentTypeGuards.ts` updated if `isGraderPayload` checks any renamed field

---

### T09 — Fix GraderCard in AgentTrace

**File:** `frontend/src/components/AgentTrace.tsx`

**Change:** Update `GraderCard` to use `scores_all`, `passed_count`, and `threshold`:

- Render one bar per entry in `scores_all`
- Bars at index `< passed_count` (i.e., passed docs) render at full opacity with the agentic accent colour
- Bars at index `>= passed_count` (i.e., filtered-out docs) render dimmed (e.g., `opacity: 0.35`)
- Show `passed_count / scores_all.length` summary label (e.g., "3 of 5 passed")
- Remove the `web_fallback` badge — the retriever card already shows `strategy: "web"` when Tavily ran

**DoD:**
- [ ] `GraderCard` reads `scores_all`, `passed_count`, `threshold` from payload
- [ ] Passing bars visually distinct from filtered bars
- [ ] `passed_count / total` summary rendered
- [ ] `web_fallback` badge removed
- [ ] `all_below_threshold` badge shown if `all_below_threshold === true` (label: "All below threshold — escalation possible")
- [ ] `eslint` passes; `tsc --noEmit` passes
- [ ] `AgentTrace` snapshot/component test updated

---

### T10 — Fix AgentVerdict web fallback detection

**File:** `frontend/src/components/AgentVerdict.tsx`

**Change:** Replace `graderStep.payload.web_fallback` with retriever step `strategy === "web"`:

```typescript
// Before
const webFallbackUsed =
  graderStep && isGraderPayload(graderStep.payload)
    ? graderStep.payload.web_fallback
    : false;

// After
const retrieverStep = agentSteps.find(
  (s) => s.node === "retriever" && isRetrieverPayload(s.payload) && s.payload.strategy === "web"
);
const webFallbackUsed = retrieverStep !== undefined;
```

**Why:** `all_below_threshold` (formerly `web_fallback`) signals intent, not execution. The retriever step with `strategy === "web"` is the definitive evidence that Tavily actually ran.

**DoD:**
- [ ] `webFallbackUsed` derived from retriever step strategy, not grader payload
- [ ] `isGraderPayload` guard no longer used for web fallback determination
- [ ] `AgentVerdict` still renders correctly for agentic-wins, static-wins, and tie cases
- [ ] `AgentVerdict.test.tsx` updated to cover the new detection logic
- [ ] `tsc --noEmit` passes

---

### T11 — Verify CitationList shows `retrieval_score` for both pipelines

**File:** `frontend/src/components/CitationList.tsx`

**Verification only** (no logic change expected): The component already reads `c.retrieval_score` for the bar. After T05 and T06, `retrieval_score` in both pipelines is the cross-encoder sigmoid value. Confirm:

- Static chain citations arrive with `retrieval_score = sigmoid(cross_encoder_logit)`, `grader_score = undefined`
- Agentic chain citations arrive with `retrieval_score = sigmoid(cross_encoder_logit)`, `grader_score = LLM score`
- The bar uses `retrieval_score` in both cases — same signal, consistent display

If `grader_score` should also be surfaced (e.g., as a tooltip or secondary label for agentic citations), add it here. Defer to user decision.

**DoD:**
- [ ] No logic change required in `CitationList.tsx` (confirm by reading)
- [ ] If a change is made, `tsc --noEmit` and `eslint` pass
- [ ] `CitationList.test.tsx` includes a test case asserting the bar uses `retrieval_score` not `grader_score`

---

### T12 — Update backend unit tests

**Files:** `backend/tests/unit/` — grader, generator, retriever node tests; static chain tests

**Required test updates:**

- `test_retriever_node.py` — assert `"score"` key absent from doc metadata; assert `"retrieval_score"` present and in [0.0, 1.0]
- `test_grader_node.py` — assert docs in `retrieved_docs` are unchanged after grader runs; assert `graded_docs` contains new `Document` objects; assert no shared object identity between the two lists
- `test_generator_node.py` — assert `Citation.retrieval_score` equals `meta["retrieval_score"]`; assert `Citation.grader_score` equals `meta["grader_score"]`; assert both are `None` when absent from metadata
- `test_chain.py` — assert `KBRetriever` output has no `"score"` key; assert `"retrieval_score"` present; assert `Citation.retrieval_score` in static chain citations; assert `Citation.grader_score` is `None`
- `test_query_agentic.py` — assert `GraderStepPayload` contains `scores_all`, `passed_count`, `threshold`, `all_below_threshold`; assert `web_fallback` absent

**DoD:**
- [ ] All modified test files pass with `pytest backend/tests/unit/ -q --tb=short`
- [ ] No tests deleted — only updated to match new contracts
- [ ] Error-path tests unchanged (grader batch failure, generator fallback)

---

### T13 — Update frontend component tests

**Files:** `frontend/src/__tests__/` — AgentTrace, AgentVerdict, AgentPanel; `frontend/src/components/CitationList.test.tsx`

**Required test updates:**

- `AgentTrace.test.tsx` — update `GraderStepPayload` fixtures to use `scores_all`, `passed_count`, `threshold`, `all_below_threshold`; assert passing bars and dimmed bars render correctly; assert "web fallback" badge absent
- `AgentVerdict.test.tsx` — update fixtures; assert `webFallbackUsed` logic reads from retriever step strategy
- `CitationList.test.tsx` — assert bar renders from `retrieval_score`; add case where both `retrieval_score` and `grader_score` are present

**DoD:**
- [ ] All frontend tests pass with `npm test` (or equivalent)
- [ ] `tsc --noEmit` passes
- [ ] `eslint` passes — zero warnings

---

## Phase Gate Criteria

All of the following must be true before this fix is considered complete and Phase 3 begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | `grep -rn '"score"' backend/src/graph/nodes/retriever.py backend/src/generation/chain.py` | Zero matches — raw logit key absent from both retriever implementations |
| G02 | `grep -rn 'grader_score if grader_score is not None' backend/src/` | Zero matches — no score-selection logic in generator |
| G03 | `grep -rn 'web_fallback' backend/src/ frontend/src/` | Zero matches — field fully removed from all layers |
| G04 | `poetry run mypy backend/src/ --strict` | Zero errors |
| G05 | `poetry run ruff check backend/src/ backend/tests/` | Zero warnings |
| G06 | `poetry run pytest backend/tests/unit/ -q --tb=short` | All green |
| G07 | `npm run tsc -- --noEmit` (frontend) | Zero errors |
| G08 | `npm test` (frontend) | All green |
| G09 | Manual: submit a query on agentic pipeline — citation "Relevance %" matches cross-encoder signal, not LLM score | Consistent with static chain display |
| G10 | Manual: GraderCard shows passing bars (full colour) vs filtered bars (dimmed) with "N of M passed" label | Visually correct |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Static chain confidence computation changes when switching from `sigmoid(mean_logit)` to `mean(sigmoid_values)` — these are not mathematically equal | Medium | Low | Document the change in T06; update eval baseline if confidence scores shift noticeably |
| Grader node creates more `Document` objects per query (T04) — minor memory increase on large batches | Low | Low | Acceptable; `graded_docs` is already a filtered subset |
| Frontend fixtures in tests reference `scores` / `web_fallback` — if missed, tests will silently pass with stale mocks | Medium | Medium | T13 explicitly lists all fixture files to update; run `grep -rn "web_fallback\|\.scores"` in frontend tests before marking T13 done |
| `get_settings()` call inside `_build_agent_step_event` (T07) — this function is called per-event; settings are cached via `@lru_cache` so no performance concern | Low | Low | Verify `get_settings` uses `@lru_cache` before merging T07 |
