# Phase 2f — Architect Review Fixes

> Created: 2026-04-28 | Source: Architect review of Phase 2f implementation
> Rule: development-process.md §9 — all High and Major fixes must clear before Phase 3 starts.
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On | Assigned To |
|----|----------|--------|----------|---------|------------|-------------|
| F01 | High | ✅ Fixed | Type Safety | `runner.py:106` `type: ignore` missing inline justification | — | backend-developer |
| F02 | Minor | ✅ Fixed | Type Safety | `ragas_eval.py:222,231` `type: ignore` missing inline justification | — | backend-developer |
| F03 | High | ✅ Fixed | Async Hygiene | `eval.py` `.read_text()` blocking call in live async route handler — new instance not covered by 2b-F06 deferred scope | — | backend-developer |
| F04 | Major | ✅ Fixed | Schema Consistency | `eval_baseline.json` (flat) and `eval_agentic_baseline.json` (nested `metrics`) served by same route without normalization; no typed response schema | F01,F02,F03 | backend-developer |
| F05 | Minor | ✅ Fixed | Test Coverage | `test_returns_422_when_file_malformed` uses mock return value not `side_effect=json.JSONDecodeError` — error path not exercised at the exception boundary | F04 | tester |

---

## Detailed Fix Specifications

### F01 — `runner.py:106` type: ignore missing justification (High)

**File:** `backend/src/evaluation/runner.py:106`
**Issue:** The suppressor `# type: ignore[arg-type]` on the `AzureOpenAIEmbeddings` `api_key=` argument has no inline explanation. Line 97 carries the justification `# httpx str accepted at call site` for the same pattern, but line 106 has only the bare suppressor.
**Fix:** Append the explanatory comment to line 106:
```python
api_key=api_key_str,  # type: ignore[arg-type]  # httpx str accepted at call site
```
**Rule:** anti-patterns.md — "Every `type: ignore` and `noqa` suppressor must have an inline justification comment."

---

### F02 — `ragas_eval.py:222,231` type: ignore missing justification (Minor)

**File:** `backend/src/evaluation/ragas_eval.py:222` and `:231`
**Issue:** Both suppressors carry only `# type: ignore[arg-type]` with no explanatory text. The same `api_key` str-vs-SecretStr pattern applies as in `runner.py`, but neither line documents why the ignore is safe.
**Fix:** Append the justification comment to both lines:
```python
api_key=api_key_str,  # type: ignore[arg-type]  # httpx str accepted at call site
```
**Rule:** anti-patterns.md — "Every `type: ignore` and `noqa` suppressor must have an inline justification comment."

---

### F03 — Blocking `.read_text()` in live async route handler (High)

**File:** `backend/src/api/routes/eval.py:61`
**Issue:** `path.read_text(encoding="utf-8")` is a synchronous blocking disk I/O call inside `async def eval_baseline()`. This blocks the event loop. The deferred finding 2b-F06 covers offline evaluation tools that run outside FastAPI — `eval.py` is a live route handler and does not qualify for that exemption.
**Fix:** Replace the blocking read with `asyncio.to_thread`. Add `asyncio` to imports:
```python
import asyncio
...
raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
```
**Rule:** python-rules.md — "Every file-read inside an `async def` must use `asyncio.to_thread()`." architecture-rules.md — "All I/O is async."

---

### F04 — Divergent JSON structures served by same route without normalization (Major)

**File:** `backend/src/api/routes/eval.py` + `backend/src/api/schemas/__init__.py`
**Issue:** The two baseline files have structurally incompatible shapes:
- `eval_baseline.json`: flat top-level metric fields (`faithfulness`, `answer_relevancy`, …), no `run_date`, no `endpoint`, no `failure_report`.
- `eval_agentic_baseline.json`: metrics nested under a `metrics` key, plus `run_date`, `endpoint`, `failure_report`.

The route handler returns `dict[str, object]` for both with zero normalization. Any consumer must branch on file identity to find metric values. The route return type bypasses schema enforcement.

**Fix (two parts):**

1. Add to `backend/src/api/schemas/__init__.py` (and `__all__`):
```python
class EvalMetrics(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_recall: float
    context_precision: float
    answer_correctness: float

class EvalBaselineResponse(BaseModel):
    pipeline: str
    run_date: str | None
    metrics: EvalMetrics
```

2. In `eval.py`, normalize the raw JSON into `EvalBaselineResponse` before returning. For the static baseline (flat structure), read top-level fields into `EvalMetrics` and set `run_date=None`, `pipeline="static"`. For the agentic baseline (nested), read from the `metrics` sub-key.

The existing `test_api_eval.py` tests that assert on raw float keys must also be updated to match the new normalized response shape.

**Rule:** architecture-rules.md — "Schema Ownership — Single Definition Rule: `backend/src/api/schemas/__init__.py` is the authoritative location for all request/response types." API contracts served by the same route must be structurally consistent.

---

### F05 — `test_returns_422_when_file_malformed` does not exercise exception boundary (Minor)

**File:** `backend/tests/unit/test_api_eval.py`
**Issue:** The test patches `Path.read_text` to return invalid JSON and relies on `json.loads` raising `json.JSONDecodeError` incidentally. This does cover the 422 branch but does not directly assert the `except json.JSONDecodeError` handler contract. The architectural rule requires at least one error-path test per external call that fires a `side_effect=ExceptionType` at the call boundary.
**Fix:** Add a companion test that patches `json.loads` with `side_effect=json.JSONDecodeError("msg", "doc", 0)`:
```python
def test_returns_422_on_json_decode_error_side_effect(
    self,
    test_client: TestClient,
    authenticated_headers: dict[str, str],
    mock_settings: Settings,
) -> None:
    with (
        patch("src.api.routes.eval.Path.exists", return_value=True),
        patch("src.api.routes.eval.asyncio.to_thread", side_effect=json.JSONDecodeError("err", "", 0)),
    ):
        response = test_client.get(
            "/api/v1/eval/baseline",
            headers=authenticated_headers,
        )
    assert response.status_code == 422
    assert "malformed" in response.json()["detail"]
```
**Note:** After F03 is applied the read uses `asyncio.to_thread`, so the patch target may need adjustment. Implement F03 before writing this test.
**Rule:** anti-patterns.md — "Write tests that cover error paths. Each external call needs at least one error-path test using `side_effect=Exception`."

---

## Clearance Order

**Batch 1 — Parallel (no dependencies):**
- F01 — one-line comment addition in `runner.py`
- F02 — two-line comment additions in `ragas_eval.py`
- F03 — `asyncio.to_thread` wrap in `eval.py` + `asyncio` import

**Batch 2 — After Batch 1 (atomic, single commit):**
- F04 — `EvalMetrics` + `EvalBaselineResponse` in `schemas/__init__.py`; route normalization; update existing `test_api_eval.py` assertions to match new response shape

**Batch 3 — After F04:**
- F05 — add `side_effect=json.JSONDecodeError` test to `test_api_eval.py`

---

## Verification Checklist

- [x] F01: `runner.py:106` carries `# httpx str accepted at call site`; `mypy --strict` zero errors; `ruff` clean
- [x] F02: `ragas_eval.py:222,231` carry `# httpx str accepted at call site`; `mypy --strict` zero errors
- [x] F03: `eval.py` imports `asyncio`; route uses `await asyncio.to_thread(path.read_text, encoding="utf-8")`; `mypy --strict` zero errors; `ruff` clean
- [x] F04: `EvalMetrics` and `EvalBaselineResponse` in `schemas/__init__.py` and `__all__`; route returns `EvalBaselineResponse`; both static and agentic branches normalize correctly; 334 tests pass; `mypy --strict` zero errors
- [x] F05: New test `test_returns_422_on_json_decode_error_side_effect` added using `side_effect=json.JSONDecodeError` on `Path.read_text`; 334 tests all green
