# Phase 2b — Architect Review Fixes

> Created: 2026-04-27 | Source: Architect review of Phase 2b implementation
> Rule: development-process.md §9 — all Major fixes must clear before Phase 2c starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On | Assigned To |
|----|----------|--------|----------|---------|------------|-------------|
| F01 | Major | ✅ Fixed | Tests | `test_builder.py` has zero error-path tests for `aiosqlite.connect` — an external I/O call with no failure coverage | — | backend-developer |
| F02 | Major | ✅ Fixed | Style | `type: ignore[attr-defined]` on `builder.py:80` has its justification in a block comment above the line, not inline — violates suppressor rule | — | backend-developer |
| F03 | High | ⚠️ Deferred | Architecture | Pre-existing lifespan singleton violations in `ingestion/`, `evaluation/`, `generation/` — client construction outside `main.py`/`deps.py` | — | backend-developer |
| F04 | High | ⚠️ Deferred | Architecture | Stub nodes do not include `duration_ms` field — ADR-004 amendment §6 requires it in every `agent_step` SSE payload from first Phase 2 emission | — | backend-developer |
| F05 | Minor | ⚠️ Deferred | Style | `conn.is_alive` monkey-patches a private aiosqlite attribute (`_thread`) — fragile across patch releases; `pyproject.toml` pin needs a removal reminder comment | — | backend-developer |
| F06 | High | ⚠️ Deferred | Architecture | Pre-existing sync I/O (`pickle.dump`, `PdfReader`, `read_text`) not wrapped in `asyncio.to_thread` in ingestion and evaluation modules | — | backend-developer |
| F07 | Advisory | ⚠️ Deferred | Architecture | ADR-004 amendment covers SqliteSaver import path, `--workers 1` constraint, `stream_mode`, and `duration_ms` commitment — no new ADR required; confirmed pass | — | — |

---

## Detailed Fix Specifications

### F01 — Error-path test for aiosqlite.connect in test_builder.py (Major)

**File:** `backend/tests/unit/graph/test_builder.py`
**Issue:** `build_graph` calls `aiosqlite.connect` (external I/O). development-process.md §3 requires at least one error-path test per external call: patch it to raise, assert the exception propagates. The file currently has 3 tests covering only the happy path — zero `pytest.raises` / `side_effect=Error` present.
**Fix:** Add a test that patches `aiosqlite.connect` to raise `OSError` and asserts `build_graph` propagates the exception rather than swallowing it. Example:

```python
@pytest.mark.asyncio
async def test_build_graph_propagates_aiosqlite_error(mock_settings, mock_retriever):
    with patch("aiosqlite.connect", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            await build_graph(settings=mock_settings, retriever=mock_retriever)
```

**Rule:** development-process.md §3 — "For every function that calls an external service … the test file must include at least one test that patches the external call to raise an exception."

---

### F02 — Inline suppressor justification on builder.py:80 (Major)

**File:** `backend/src/graph/builder.py:80`
**Issue:** The `# type: ignore[attr-defined]` suppressor has its explanation in a multi-line block comment above the line. The suppressor rule requires the justification to be on the same line as the suppressor so it is co-located and cannot be separated by later edits.
**Fix:** Consolidate the block comment into a single inline comment on the suppressor line and add a version-tracking TODO:

```python
conn.is_alive = conn._thread.is_alive  # type: ignore[attr-defined]  # aiosqlite 0.22 removed is_alive(); langgraph-checkpoint-sqlite 2.0.11 calls it in setup() — remove when langgraph-checkpoint-sqlite >= 2.0.12
```

Remove the now-redundant block comment above the line.
**Rule:** architect-review-checklist.md Priority 7 — "Every suppressor must have an inline justification."

---

### F03 — Pre-existing lifespan singleton violations in ingestion/evaluation/generation (High)

**Files:**
- `backend/src/ingestion/vector_store.py:33` — `AsyncQdrantClient(` constructed per call
- `backend/src/ingestion/embedder.py:64` — `AzureOpenAIEmbeddings(` constructed per call
- `backend/src/retrieval/dense.py:24` — `AsyncQdrantClient(` constructed per call
- `backend/src/generation/chain.py:116` — `AzureChatOpenAI(` constructed per call
- `backend/src/evaluation/ragas_eval.py:220,229` — `AzureChatOpenAI(` and `AzureOpenAIEmbeddings(` constructed on every evaluation call

**Issue:** Per-request client construction causes connection churn and defeats the lifespan singleton pattern established in Phase 0. The evaluation case is most severe — LLM clients are instantiated on every RAGAS evaluation call rather than accepting injected instances.
**Fix:** Migrate each construct to a lifespan singleton on `app.state` and inject via `deps.py` dependency aliases, following the same pattern as `QdrantClientDep` and `SettingsDep`. `ragas_eval.py` must accept `AzureChatOpenAI` and `AzureOpenAIEmbeddings` as parameters rather than constructing them internally.
**Target phase:** Phase 7 (pre multi-replica deployment hardening).
**Rule:** architecture-rules.md — Tier 2 lifespan singleton pattern; architect-review-checklist.md Priority 2.

---

### F04 — duration_ms field absent from stub nodes (High)

**Files:** `backend/src/graph/nodes/router.py`, `backend/src/graph/nodes/grader.py`, `backend/src/graph/nodes/critic.py`
**Issue:** ADR-004 amendment §6 states: "Every `agent_step` SSE event payload must include a `duration_ms: int` field from the first Phase 2 implementation." The stub nodes that will emit `agent_step` events do not include `duration_ms` in their return dict contract. Phase 2c must add `duration_ms` to every emitting node simultaneously with the LLM call — retrofitting across all nodes at once increases coordination cost.
**Fix:** When implementing real node logic in Phase 2c, include `duration_ms` in the return dict contract of every node that emits an `agent_step` event from day one. Do not defer it to a separate task. Add `duration_ms: int` to `AgentState` if not already present.
**Target phase:** Phase 2c — must be part of the node implementation task spec.
**Rule:** ADR-004 amendment §6.

---

### F05 — conn.is_alive monkey-patch is a version-coupling risk (Minor)

**File:** `backend/src/graph/builder.py:80`, `backend/pyproject.toml`
**Issue:** `conn.is_alive = conn._thread.is_alive` patches a private aiosqlite attribute. This is fragile across aiosqlite patch releases — if `_thread` is renamed or removed, the patch silently fails or raises `AttributeError` at startup.
**Fix:** Add a comment to `pyproject.toml` next to the `langgraph-checkpoint-sqlite` and `aiosqlite` pins reminding the reviewer to remove the workaround after upgrade:

```toml
langgraph-checkpoint-sqlite = "2.0.11"  # pin: builder.py:80 monkey-patch required until >= 2.0.12
aiosqlite = "0.20.0"                    # pin: _thread.is_alive workaround in builder.py:80
```

**Target phase:** Next dependency update cycle (Phase 2c or maintenance task).
**Rule:** development-process.md §6 — "Document the version choice in pyproject.toml comments if a newer version was intentionally skipped."

---

### F06 — Pre-existing sync I/O not wrapped in asyncio.to_thread (High)

**Files:**
- `backend/src/ingestion/pipeline.py` — `pickle.dump` (BM25 persistence)
- `backend/src/ingestion/local_loader.py:95` — `PdfReader` (blocking PDF parse)
- `backend/src/ingestion/local_loader.py:137` — `.read_text()`
- `backend/src/api/routes/eval.py:39` — `.read_text()`
- `backend/src/evaluation/ragas_eval.py:165,238` — `.read_text()`

**Issue:** Synchronous I/O calls inside `async def` functions block the event loop. Under concurrent load this causes request stalls. The Phase 1a fix addressed the ingestion loader but the pattern recurred in evaluation and BM25 persistence.
**Fix:** Wrap each blocking call in `asyncio.to_thread(...)`. Example:

```python
# Before
data = path.read_text()

# After
data = await asyncio.to_thread(path.read_text)
```

**Target phase:** Phase 5/6 hardening pass before load testing.
**Rule:** architect-review-checklist.md Priority 5 — "Any synchronous I/O call not wrapped in asyncio.to_thread inside an async def context is a High finding."

---

### F07 — ADR-004 amendment coverage confirmed (Advisory)

**File:** `docs/adr/ADR-004-*.md` (amended 2026-04-27)
**Issue:** None — this is a pass finding.
**Finding:** ADR-004 amendment explicitly documents the `AsyncSqliteSaver` import path, the `--workers 1` single-writer constraint, `stream_mode="updates"`, and the `duration_ms` commitment. The builder pattern (dependency injection of `settings` and `HybridRetriever` into `build_graph`) is a conformant implementation of the Phase 2a architect-approved design. No additional ADR is required for Phase 2b.
**Rule:** architect-review-checklist.md Priority 4 — ADR coverage verified.

---

## Clearance Order

F01 and F02 are blockers for Phase 2c. All other findings are deferred.

```
Phase 2c blockers — parallel (no dependencies):
  F01  F02

Phase 2c task spec — carry forward:
  F04  (duration_ms must be in Phase 2c node implementation spec from day one)

Phase 2c maintenance — parallel:
  F05  (pyproject.toml pin comments — low effort, no risk)

Phase 5/6 hardening:
  F06  (sync I/O — asyncio.to_thread pass)

Phase 7 pre-deployment:
  F03  (lifespan singleton violations in ingestion/evaluation/generation)
```

---

## Verification Checklist

- [x] `poetry run ruff check backend/src/ backend/tests/` — zero warnings
- [x] `poetry run mypy backend/src/ --strict` — zero errors
- [x] `poetry run pytest backend/tests/unit/ -q --tb=short` — all green (271 passed)
- [x] `test_builder.py` contains at least one `pytest.raises` / `side_effect=Error` test (F01)
- [x] `builder.py:80` suppressor has justification on the same line as `type: ignore` (F02)
- [x] Block comment above `builder.py:80` removed (F02)
