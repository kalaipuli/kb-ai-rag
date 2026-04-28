# Phase 2d — Architect Review Fixes

> Created: 2026-04-27 | Source: Architect review of Phase 2d implementation | Cleared: 2026-04-27
> Rule: development-process.md §9 — all Critical and High fixes must clear before Phase 2e starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On | Assigned To |
|----|----------|--------|----------|---------|------------|-------------|
| F01 | High | ✅ Fixed | Correctness | `_parse_duration_ms` raises unguarded `ValueError` on malformed `steps_taken` entry — exception escapes `try/except`, silently kills SSE stream without `done` | — | backend-developer |
| F02 | High | ✅ Fixed | Spec Deviation | `_build_agent_step_event` helper not implemented; timing extraction + payload construction duplicated 3× inline | F01 | backend-developer |
| F03 | High | ✅ Fixed | Test Coverage | `test_graph_exception_yields_done_event` does not assert `structlog.error` emission — mandatory error-path requirement not met | — | backend-developer |
| F04 | Major | ✅ Fixed | Correctness | `chunks_retrieved` always emits `0` — generator node state delta does not include `graded_docs` | — | backend-developer |
| F05 | Major | ✅ Fixed | Test Location | Test file at wrong path (`tests/unit/test_query_agentic.py` vs spec-mandated `tests/unit/api/test_query_agentic.py`) | — | backend-developer |
| F06 | Major | ✅ Fixed | Wire Format | `token` event emits full answer as one chunk; spec mandates one event per logical unit (per-word, matching Phase 1) | F02 | backend-developer |
| F07 | Minor | ✅ Fixed | Correctness | `str.rstrip("ms")` is a character-set strip, not a literal suffix strip — use `str.removesuffix("ms")` | — | backend-developer |
| F08 | Minor | ✅ Fixed | Clarity | `done` event placed outside `try` block with no comment documenting the deliberate always-emit intent | — | backend-developer |
| F09 | Advisory | ✅ Fixed | Schema Design | `AgentStepEvent.payload` is an undiscriminated union — safe today due to mutually exclusive fields, but rationale is undocumented | — | backend-developer |

---

## Detailed Fix Specifications

### F01 — `_parse_duration_ms` raises on malformed input (High)

**File:** `backend/src/api/routes/query_agentic.py:28–31`

**Issue:** `_parse_duration_ms` calls `int()` on the result of `rsplit`/`rstrip` without a guard. A malformed or partial `steps_taken` entry (e.g. `"router_timeout"`, an empty string, or a node that wrote no timing) causes `ValueError` to propagate out of the `async for` streaming loop. This exception is not caught by the inner `try/except Exception`, which wraps only the `astream` iteration — the parse call happens inside the loop but the ValueError bubbles through `except Exception` only if it occurs inside the `try` block body. In the current layout the parse call IS inside the `try` block, so it is caught — however it then skips the `done` event emission that is outside the block, leaving the SSE stream open without a terminal event. A dedicated unit test for `_parse_duration_ms` is also absent.

**Fix:**
```python
def _parse_duration_ms(step: str) -> int:
    """Parse duration_ms from a steps_taken entry like 'router:factual:hybrid:45ms'.

    Returns 0 if the entry is malformed rather than raising.
    """
    try:
        raw = step.rsplit(":", 1)[-1]
        return int(raw.removesuffix("ms"))
    except (ValueError, IndexError):
        return 0
```

Add a unit test covering three cases: `""` → `0`, `"router_timeout"` → `0`, `"router:factual:hybrid:45ms"` → `45`.

**Rule:** development-process.md §3 — error-path coverage required for every function that processes external-produced data. anti-patterns.md — "Write tests that only cover the happy path."

---

### F02 — `_build_agent_step_event` helper missing; logic inlined and duplicated (High)

**File:** `backend/src/api/routes/query_agentic.py:59–106`

**Issue:** The T02 task spec explicitly mandates a private function `_build_agent_step_event(node_name: str, state_update: dict) -> AgentStepEvent` that isolates timing extraction from the streaming loop. The implementation inlines the `steps_taken` extraction, `_parse_duration_ms` call, and payload construction three separate times (once per node branch). The streaming loop now has two reasons to change (event structure changes and streaming protocol changes), violating single responsibility. It also means timing logic is tested only indirectly.

**Fix:** Extract:
```python
def _build_agent_step_event(
    node_name: str, state_update: dict[str, object]
) -> AgentStepEvent:
    steps: list[str] = state_update.get("steps_taken", [])  # type: ignore[assignment]
    duration_ms = _parse_duration_ms(steps[0]) if steps else 0
    if node_name == "router":
        return AgentStepEvent(
            node="router",
            payload=RouterStepPayload(
                query_type=state_update["query_type"],  # type: ignore[arg-type]
                strategy=state_update["retrieval_strategy"],  # type: ignore[arg-type]
                duration_ms=duration_ms,
            ),
        )
    if node_name == "grader":
        return AgentStepEvent(
            node="grader",
            payload=GraderStepPayload(
                scores=state_update.get("grader_scores", []),  # type: ignore[arg-type]
                web_fallback=state_update.get("all_below_threshold", False),  # type: ignore[arg-type]
                duration_ms=duration_ms,
            ),
        )
    # critic
    critic_score: float = state_update.get("critic_score") or 0.0  # type: ignore[assignment]
    return AgentStepEvent(
        node="critic",
        payload=CriticStepPayload(
            hallucination_risk=critic_score,
            reruns=state_update.get("retry_count", 0),  # type: ignore[arg-type]
            duration_ms=duration_ms,
        ),
    )
```

The streaming loop body for each recognised node name reduces to:
```python
event = _build_agent_step_event(node_name, state_update)
yield f"data: {event.model_dump_json()}\n\n"
```

**Rule:** T02 DoD spec — `_build_agent_step_event` helper is required. architecture-rules.md — single responsibility; each module has one reason to change.

---

### F03 — Error-path test does not assert `structlog.error` emission (High)

**File:** `backend/tests/unit/test_query_agentic.py:224–248`

**Issue:** `test_graph_exception_yields_done_event` patches `astream` to raise `RuntimeError` and asserts the response closes with a `done` event or returns HTTP 500. It does not assert that `structlog.error` is emitted with `event == "agentic_stream_error"`. development-process.md §3 mandates that error-path tests assert the structlog error event. Additionally, the conditional branch (`if response.status_code == 200 … else assert 500`) is misleading — the current implementation always returns 200 with a `done` event because exceptions are caught inside `_stream()`. The ambiguous branch conceals a possible regression.

**Fix:** Replace the test body with:
```python
import structlog.testing

async def _failing_astream(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
    raise RuntimeError("graph failed")
    yield  # makes this an async generator

mock_graph = MagicMock()
mock_graph.astream = _failing_astream
app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

try:
    with structlog.testing.capture_logs() as captured:
        with test_client_1d.stream(
            "POST", "/api/v1/query/agentic",
            json={"query": "What is X?"}, headers=authenticated_headers,
        ) as response:
            assert response.status_code == 200
            lines = list(response.iter_lines())

    events = _parse_events(lines)
    assert events[-1]["type"] == "done"

    error_events = [e for e in captured if e["event"] == "agentic_stream_error"]
    assert len(error_events) == 1
    assert error_events[0]["log_level"] == "error"
finally:
    app.dependency_overrides.pop(get_compiled_graph, None)
```

**Rule:** development-process.md §3 — error-path test must assert structlog error event is emitted.

---

### F04 — `chunks_retrieved` always emits 0 (Major)

**File:** `backend/src/api/routes/query_agentic.py:123`

**Issue:** `chunks_retrieved = len(state_update.get("graded_docs", []))` reads from the generator node's state delta. The generator node writes `answer`, `citations`, `confidence`, `messages`, and `steps_taken` — it does not re-write `graded_docs`. Because `stream_mode="updates"` yields only the fields written by each node, `graded_docs` is absent from the generator chunk. `chunks_retrieved` is therefore always `0`, breaking any frontend latency or retrieval-count display that depends on this value.

**Fix (Option A — preferred, no node change):** Capture the grader doc count when the grader chunk is processed and reuse it when emitting the `citations` event:

```python
# Before the async for loop:
_grader_doc_count: int = 0

# Inside the grader branch:
_grader_doc_count = len(state_update.get("graded_docs", []))

# Inside the generator branch when emitting citations:
chunks_retrieved = _grader_doc_count
```

**Rule:** architecture-rules.md — `stream_mode="updates"` yields only the delta written by the node; do not assume a field is present unless that node writes it.

---

### F05 — Test file placed at wrong path (Major)

**File:** `backend/tests/unit/test_query_agentic.py`

**Issue:** The T04 task spec mandates the file at `backend/tests/unit/api/test_query_agentic.py`. The implementation placed it one level up in the flat `unit/` directory. The `api/` subdirectory mirrors the source layout (`src/api/routes/`) — the project convention used by all other route tests.

**Fix:** Move the file:
```bash
mkdir -p backend/tests/unit/api
mv backend/tests/unit/test_query_agentic.py backend/tests/unit/api/test_query_agentic.py
# Ensure __init__.py exists if the test runner requires it
touch backend/tests/unit/api/__init__.py
```
Verify with `poetry run pytest backend/tests/unit/ -q` — all tests collected.

**Rule:** T04 DoD spec — file path explicitly stated as `backend/tests/unit/api/test_query_agentic.py`. development-process.md §1 — implementation must match the agreed design.

---

### F06 — `token` event emits full answer as one chunk (Major)

**File:** `backend/src/api/routes/query_agentic.py:111–113`

**Issue:** The T02 spec states "yield one `token` event per logical unit of the answer string." The Phase 1 static endpoint emits one `token` event per word. The agentic endpoint emits one `token` event containing the entire answer string. This divergence means the frontend `useAgentStream` hook (Phase 2e) must special-case the agentic endpoint rather than sharing a common token-accumulation path. If Phase 2e is built against this behaviour it will be difficult to correct later.

**Fix:** Split the answer into per-word tokens to match Phase 1 semantics:
```python
answer = state_update.get("answer") or ""
for word in answer.split(" "):
    if word:
        yield f"data: {json.dumps({'type': 'token', 'content': word + ' '})}\n\n"
```

If the team decides a single-token model is acceptable for the agentic path, document the divergence explicitly in ADR-004 before Phase 2e begins and update the `test_happy_path_event_order` assertion accordingly.

**Rule:** T02 DoD spec — "yield one `token` event per logical unit." architecture-rules.md — SSE contract for agentic endpoint must not diverge from Phase 1 token semantics without an ADR.

---

### F07 — `str.rstrip("ms")` is a character-set strip (Minor)

**File:** `backend/src/api/routes/query_agentic.py:31`

**Issue:** `str.rstrip(chars)` removes all trailing characters appearing in the `chars` argument as a set, not as a literal string. `"45ms".rstrip("ms")` → `"45"` works today by coincidence. `str.removesuffix("ms")` (Python 3.9+, available in this Python 3.12 project) removes the literal suffix `"ms"` only, making intent explicit and eliminating the character-set ambiguity.

**Fix:** Replace `part.rstrip("ms")` with `part.removesuffix("ms")`. This fix is subsumed by F01.

**Rule:** python-rules.md — use the most semantically precise stdlib function available.

---

### F08 — `done` event outside `try` block has no documenting comment (Minor)

**File:** `backend/src/api/routes/query_agentic.py:132–133`

**Issue:** The `done` event `yield` is deliberately placed after the `try/except` block so it is always emitted, even when the graph raises. This is the correct design, but the intent is undocumented. A future developer may move the `yield` inside the `try` block during a refactor, silently breaking the always-emits-done guarantee.

**Fix:** Add one comment line:
```python
# Always emit done — even after a mid-stream exception — so the client can close.
yield f"data: {json.dumps({'type': 'done'})}\n\n"
```

**Rule:** python-rules.md — non-obvious design decisions require an inline explanation.

---

### F09 — `AgentStepEvent.payload` is an undiscriminated union (Advisory)

**File:** `backend/src/api/schemas/agentic.py:34–37`

**Issue:** `payload: RouterStepPayload | GraderStepPayload | CriticStepPayload` has no Pydantic `discriminator` annotation. Runtime resolution is correct today because the three types have mutually exclusive required fields. However, code that receives an `AgentStepEvent` and needs to narrow `payload` to a concrete type must use `isinstance()` checks — mypy cannot narrow the union automatically without a `Field(discriminator=...)` declaration. The T01 spec notes "Discriminated by `node` field" without mandating a Pydantic annotation.

**Fix (Advisory — no immediate code change required):** Add an inline comment to the `payload` field documenting why the discriminator annotation is absent:
```python
# Union resolved at runtime by mutually exclusive required fields.
# Add Field(discriminator="...") if a future payload type shares field names.
payload: RouterStepPayload | GraderStepPayload | CriticStepPayload
```

**Rule:** architecture-rules.md — schema evolution rules; non-obvious design decisions must be documented.

---

## Clearance Order

**Batch 1 — Independent; no other fix depends on these:**
- F07 (subsumed by F01 — fix together)
- F08 (comment only)
- F09 (advisory comment only)

**Batch 2 — Core correctness (F01 must land before F02):**
- F01: Fix `_parse_duration_ms` with `removesuffix` and `try/except`; add dedicated unit tests
- F04: Fix `chunks_retrieved` by tracking grader doc count during grader chunk processing

**Batch 3 — After F01 is merged:**
- F02: Extract `_build_agent_step_event` helper using the corrected parse function

**Batch 4 — After F02 + F04 (route stable):**
- F06: Fix `token` emission to per-word split (or write ADR-004 amendment if single-token is accepted)

**Batch 5 — Test layer (after route is stable):**
- F03: Add `structlog.testing.capture_logs()` assertion to error-path test
- F05: Move test file to `backend/tests/unit/api/test_query_agentic.py`

---

## Verification Checklist

Run from `backend/` via `poetry run`. All commands verified clean 2026-04-27 (316 tests passing).

- [x] `poetry run ruff check backend/src/ backend/tests/` — zero output
- [x] `poetry run mypy backend/src/ --strict` — zero errors (54 source files)
- [x] `poetry run pytest backend/tests/unit/ -q --tb=short` — 316 passed, 0 failed
- [x] F01: `_parse_duration_ms("")` → `0`; `_parse_duration_ms("router_timeout")` → `0`; `_parse_duration_ms("router:factual:hybrid:45ms")` → `45` — `TestParseDurationMs` class in test file
- [x] F02: `_build_agent_step_event` at line 42; one call site; inline duplication removed
- [x] F03: `capture_logs` + `agentic_stream_error` present in `test_graph_exception_yields_done_event`
- [x] F04: `test_happy_path_event_order` asserts `chunks_retrieved == 1`
- [x] F05: `find backend/tests/unit/api -name "test_query_agentic.py"` — one result; flat path gone
- [x] F06: `test_happy_path_event_order` asserts `len(token_events) >= 2`
- [x] F07: zero `rstrip` matches in `query_agentic.py`
- [x] F08: "Always emit done" comment present at line 147
- [x] F09: discriminator rationale comment on `payload` field in `schemas/agentic.py`
