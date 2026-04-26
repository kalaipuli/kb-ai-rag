# Phase 1g — Architect Review Fixes

> Created: 2026-04-26 | Source: Architect review of Phase 1g implementation  
> Rule: development-process.md §9 — all critical fixes must clear before Phase 2 starts.  
> Status key: ⏳ Pending · 🔄 In Progress · ✅ Fixed · ⚠️ Deferred

---

## Fix Registry

| ID | Severity | Status | Category | Summary | Depends On |
|----|----------|--------|----------|---------|------------|
| F01 | Critical | ✅ Fixed | Architecture | `pipeline.py:65` creates a second `Embedder(settings)` on every `run_pipeline` call — the lifespan singleton passed via `embedder` param is used only for `SplitterFactory` but Stage 3 embedding ignores it. Violates ADR-009 §4 — "no hidden client duplication". | — |
| F02 | Critical | ✅ Fixed | Correctness | `chain.py:120` and `embedder.py:66` pass `settings.azure_openai_api_key` (raw `SecretStr`) directly to `AzureChatOpenAI` / `AzureOpenAIEmbeddings` without `.get_secret_value()`. Fails DoD gate §7 check 5. | — |
| F03 | High | ✅ Fixed | Tests | `test_ingestion_splitter.py` has zero error-path tests. `DocumentSplitter` now delegates to `SplitterFactory` which raises `ConfigurationError` for unknown strategies, but no test exercises this propagation path. | F01 |
| F04 | Medium | ✅ Fixed | Config | `backend/.env.example:30` — `CHUNK_OVERLAP=200` duplicated. First occurrence at line 16 (pre-existing). Harmless at runtime but misleading. | — |
| F05 | Medium | ✅ Fixed | Config | `.gitignore:53` — entry is `data/eval_baseline.json` but the file lands at `backend/data/eval_baseline.json` (backend CWD). The broader `backend/data/*` pattern catches it incidentally, but the explicit entry is wrong. | — |
| F06 | Medium | ✅ Fixed | Tests | `test_sentence_window_splitter.py` has zero error-path tests. `nltk.sent_tokenize` is an external call; no test covers `LookupError` from missing NLTK data. | — |
| F07 | Medium | ✅ Fixed | Docs | `docs/adr/009-chunking-strategy-abstraction.md:44` — `cl100k_base` rationale says "matching `text-embedding-3-large`" but the default `AZURE_EMBEDDING_DEPLOYMENT` is `text-embedding-ada-002`. Both use `cl100k_base`, so the default is correct but the comment is inaccurate. | — |
| F08 | Low | ✅ Fixed | Registry | `docs/registry/phase1/1g-retrieval-quality/tasks.md` T15 DoD bullet references `Dockerfile.api` — actual filename is `Dockerfile`. | — |

---

## Detailed Fix Specifications

### F01 — pipeline.py: use lifespan Embedder singleton in Stage 3 (Critical)

**File:** `backend/src/ingestion/pipeline.py:65`  
**Current:** `embed_client = Embedder(settings=settings)` created unconditionally; `embedder` param only forwarded to `DocumentSplitter`.  
**Fix:**
- Remove line 65 (`embed_client = Embedder(settings=settings)`).
- Change Stage 3 (line 116) from `embed_client.embed_chunks(chunks)` to `embedder.embed_chunks(chunks)`.
- If `embedder` is `None` (only possible in the `__main__` entry-point or direct test calls), construct a local fallback with a `structlog.warning` so production codepath always uses the singleton.

```python
_local_embedder = embedder
if _local_embedder is None:
    logger.warning("pipeline_embedder_not_injected_using_local")
    _local_embedder = Embedder(settings=settings)
```

- Update docstring: "Lifespan-managed `Embedder` singleton is passed in; Stage 3 uses it directly."  
**Rule:** ADR-009 §4 — "Embedder singleton ownership remains with the lifespan block — no hidden client duplication"; architecture-rules.md Tier 2 lifespan singleton pattern.

---

### F02 — SecretStr boundary in chain.py and embedder.py (Critical)

**Files:** `backend/src/generation/chain.py:120`, `backend/src/ingestion/embedder.py:66`  
**Current:** `api_key=settings.azure_openai_api_key` (raw `SecretStr`)  
**Fix:**

`chain.py:120`:
```python
api_key=settings.azure_openai_api_key.get_secret_value(),
```

`embedder.py:66`:
```python
api_key=settings.azure_openai_api_key.get_secret_value(),
```

Add `# type: ignore[arg-type]` with justification if mypy complains about the LangChain stub type for `api_key`.  
**Rule:** python-rules.md — "call `.get_secret_value()` before passing to external libraries"; development-process.md §7 gate check 5.  
**Note:** This was previously flagged as F01 in the Phase 1d fixes (chain.py), accepted as "LangChain accepts SecretStr natively". The DoD gate check (§7 check 5) explicitly greps for this pattern and counts it as a failure regardless of runtime behaviour. The gate must pass cleanly.

---

### F03 — Error-path test for ConfigurationError propagation in DocumentSplitter (High)

**File:** `backend/tests/unit/test_ingestion_splitter.py`  
**Issue:** Zero error-path tests. `DocumentSplitter.__init__` delegates to `SplitterFactory.build()`, which raises `ConfigurationError` for unknown or deferred strategies. No test exercises this.  
**Fix:** Add one test:

```python
def test_invalid_strategy_raises_configuration_error() -> None:
    settings = _make_settings(chunk_strategy="invalid_strategy")
    with pytest.raises(ConfigurationError, match="invalid_strategy"):
        DocumentSplitter(settings)
```

Import `ConfigurationError` from `src.exceptions`. Confirm `_make_settings` accepts `chunk_strategy` keyword.  
**Rule:** development-process.md §3 — "at least one error-path test per external call"; CLAUDE.md §1 DoD.

---

### F04 — Duplicate CHUNK_OVERLAP in .env.example (Medium)

**File:** `backend/.env.example:30`  
**Current:** `CHUNK_OVERLAP=200` at line 16 and again at line 30.  
**Fix:** Remove the second occurrence at line 30. Keep the first at line 16 which is in the main chunking settings block. Move `CHUNK_STRATEGY`, `CHUNK_TOKENIZER_MODEL`, and `EVAL_BASELINE_PATH` immediately after `CHUNK_OVERLAP` so all chunking settings are grouped together.  
**Rule:** development-process.md §7 DoD — "`.env.example` updated for every new Settings field" (no duplicates).

---

### F05 — .gitignore path for eval_baseline.json (Medium)

**File:** `.gitignore:53`  
**Current:** `data/eval_baseline.json`  
**Fix:** Change to `backend/data/eval_baseline.json` to match the actual path from the repo root.  
**Explanation:** The backend process runs with `backend/` as CWD, so `Settings.eval_baseline_path = "data/eval_baseline.json"` resolves to `backend/data/eval_baseline.json` from the repo root. The existing `backend/data/*` pattern in `.gitignore` already covers this file, but the explicit entry should be correct and unambiguous.  
**Rule:** T13 DoD — "`.gitignore` entry matches actual file path".

---

### F06 — NLTK error-path test in test_sentence_window_splitter.py (Medium)

**File:** `backend/tests/unit/test_sentence_window_splitter.py`  
**Issue:** `nltk.sent_tokenize` is an external call. No test patches it to raise `LookupError` (missing punkt_tab data).  
**Fix:** Add one test:

```python
from unittest.mock import patch
import pytest

def test_tokenize_lookup_error_propagates() -> None:
    from src.ingestion.sentence_window_splitter import SentenceWindowSplitter
    splitter = SentenceWindowSplitter(chunk_size=100, chunk_overlap=10)
    with patch("nltk.sent_tokenize", side_effect=LookupError("punkt_tab not found")):
        with pytest.raises(LookupError, match="punkt_tab"):
            splitter.split_text("Some sentence here.")
```

**Rule:** development-process.md §3 — error-path coverage for external library calls.

---

### F07 — ADR-009 cl100k_base rationale comment (Medium)

**File:** `docs/adr/009-chunking-strategy-abstraction.md:44`  
**Current:** `(default \`cl100k_base\`, matching \`text-embedding-3-large\`)`  
**Fix:** Change to:
```
(default `cl100k_base`, matching both `text-embedding-ada-002` and `text-embedding-3-large`)
```
Both models use the `cl100k_base` encoding. The `.env.example` default is `text-embedding-ada-002`; a developer configuring either model uses the same tokenizer.  
**Rule:** architecture-rules.md — ADRs must be accurate.

---

### F08 — tasks.md T15 DoD Dockerfile name (Low)

**File:** `docs/registry/phase1/1g-retrieval-quality/tasks.md`  
**Current:** T15 DoD bullet reads `"RUN python -m nltk.downloader punkt_tab added to Dockerfile.api"`  
**Fix:** Change `Dockerfile.api` to `Dockerfile`. The actual backend image file is `backend/Dockerfile` with no `.api` suffix.  
**Rule:** Registry accuracy.

---

## Clearance Order

Critical and High fixes must clear before Phase 2 begins. Medium/Low may be resolved concurrently.

```
Batch 1 — Code fixes (parallel, no dependencies):
  F01  F02  F04  F05  F07  F08

Batch 2 — Test fixes (after F01/F02 code is stable):
  F03  F06
```

## Verification Checklist

Verified 2026-04-26:
- [x] `ruff check src/ tests/` — zero warnings
- [x] `mypy src/ --strict` — zero errors (42 source files)
- [x] `pytest tests/unit/` — 252 passed (up from 241; includes new ConfigurationError + NLTK error-path tests)
- [x] DoD gate check 5: `grep -rn "api_key=settings\." src/ --include="*.py" | grep -v "get_secret_value"` — zero matches
- [x] `.gitignore` entry corrected to `backend/data/eval_baseline.json`
