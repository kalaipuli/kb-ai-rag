# Phase 1g — Retrieval Quality Task Registry

> Status: ✅ Complete 2026-04-26 | Phase: 1g | Estimated Days: 4–5  
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)  
> Last updated: 2026-04-26  
> ADR: [ADR-009](../../../adr/009-chunking-strategy-abstraction.md)

---

## Context

Phase 1 hard-codes `RecursiveCharacterTextSplitter` with a character-based length function and fixed parameters. This phase introduces:

1. Token-aware chunking (tiktoken) — correctness fix, always applied.
2. A configurable `SplitterFactory` with `ChunkStrategy` enum — enables strategy experimentation via `.env`.
3. Improved evaluation output — per-sample tables, `AnswerCorrectness` metric, stddev, failure report, and baseline comparison.

After both are implemented, RAGAS is re-run under the new strategy and results are documented as evidence of improvement.

**Architect review:** 2026-04-26. Two blockers resolved in task design: (a) `SplitterFactory` receives the `Embedder` singleton — never creates its own; (b) `eval_baseline_path` is a `Settings` field written to `data/`, not `docs/`.

---

## Pre-Implementation Gate (run before any code)

**Gate 1 — No duplicate ChunkStrategy or SplitterFactory class:**
```bash
grep -rn "class ChunkStrategy\|class SplitterFactory" backend/src/ --include="*.py"
```
Expected: zero matches.

**Gate 2 — ADR-009 accepted:**
`docs/adr/009-chunking-strategy-abstraction.md` must exist and status must be `Accepted`.

**Gate 3 — langchain-experimental dry-run:**
```bash
cd backend && poetry add langchain-experimental --dry-run
```
If conflict: `semantic` strategy is deferred; `ChunkStrategy.semantic` raises `ConfigurationError`. Document result in ADR-009.

**Gate 4 — No deprecated LangChain symbols:**
```bash
grep -rn "RetrievalQA\|LLMChain\|StuffDocumentsChain" backend/src/ --include="*.py"
```
Expected: zero matches.

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Add `tiktoken ^0.8` to pyproject.toml | backend-developer | — |
| T02 | ✅ Done | Add `chunk_strategy`, `chunk_tokenizer_model`, `eval_baseline_path` to Settings + .env.example | backend-developer | — |
| T03 | ✅ Done | Replace `length_function=len` with tiktoken counter in `DocumentSplitter` | backend-developer | T01, T02 |
| T04 | ✅ Done | Add `app.state.embedder` to lifespan + `EmbedderDep` to deps.py | backend-developer | — |
| T05 | ✅ Done | Create `splitter_factory.py`: `ChunkStrategy` enum + `SplitterFactory.build()` | backend-developer | T02, T04 |
| T06 | ✅ Done | Implement `sentence_window` strategy in `SplitterFactory` (nltk) | backend-developer | T05 |
| T07 | ✅ Done | `semantic` strategy deferred — raises `ConfigurationError`; langchain-experimental conflict documented in ADR-009 | backend-developer | T05 |
| T08 | ✅ Done | Refactor `DocumentSplitter.__init__` to call `SplitterFactory.build()` | backend-developer | T05 |
| T09 | ✅ Done | Update `run_pipeline` to accept `embedder` param; update ingest route to pass it | backend-developer | T04, T08 |
| T10 | ✅ Done | Add `AnswerCorrectness` metric + `answer_correctness` field to `RagasEvaluator` | backend-developer | T02 |
| T11 | ✅ Done | Extend `EvaluationResult.to_markdown()`: per-sample table, stddev, failure section | backend-developer | T10 |
| T12 | ✅ Done | Add baseline persistence + diff column to eval runner | backend-developer | T11 |
| T13 | ✅ Done | Add `data/eval_baseline.json` to `.gitignore` | backend-developer | T12 |
| T14 | ✅ Done | Re-run RAGAS with updated metrics; store baseline; document comparison | backend-developer | T03, T12 |
| T15 | ✅ Done | Write NLTK punkt download step to Dockerfile + README | backend-developer | T06 |

---

## Ordered Execution Plan

### Batch 1 — Parallel (no dependencies)
- **T01** — Add tiktoken to pyproject.toml
- **T02** — Add Settings fields + update .env.example
- **T04** — Add app.state.embedder to lifespan + EmbedderDep to deps.py

### Batch 2 — After T01, T02
- **T03** — Token-aware length function in DocumentSplitter

### Batch 3 — After T02 and T04 (Gate 3 must pass)
- **T05** — Create splitter_factory.py

### Batch 4 — After T05 (parallel)
- **T06** — Sentence window strategy
- **T07** — Semantic strategy (if Gate 3 passed)
- **T08** — Refactor DocumentSplitter to use factory

### Batch 5 — After T04, T08
- **T09** — Update run_pipeline + ingest route

### Batch 6 — After T02 (parallel, independent of chunking tasks)
- **T10** — AnswerCorrectness metric

### Batch 7 — After T10
- **T11** — Extend to_markdown()

### Batch 8 — After T11
- **T12** — Baseline persistence + diff
- **T13** — .gitignore entry

### Batch 9 — After T03, T06/T07/T08, T12
- **T14** — Re-run RAGAS, store baseline, document comparison
- **T15** — Dockerfile + README for nltk punkt

---

## Definition of Done Per Task

### T01 — Add tiktoken to pyproject.toml
- [x] `tiktoken = "^0.8"` in `[tool.poetry.dependencies]`
- [x] `poetry lock` runs without conflict
- [x] `ruff` + `mypy --strict` clean after change

### T02 — Settings fields + .env.example
- [x] `chunk_strategy: str = "recursive_character"` added to `Settings`
- [x] `chunk_tokenizer_model: str = "cl100k_base"` added to `Settings`
- [x] `eval_baseline_path: str = "data/eval_baseline.json"` added to `Settings`
- [x] `.env.example` updated with all three fields and descriptions
- [x] `test_config.py` updated to cover new fields

### T03 — Token-aware length function
- [x] `DocumentSplitter.__init__` uses `tiktoken.get_encoding(settings.chunk_tokenizer_model)` as `length_function`
- [x] Unit test asserts chunk boundaries respect token count, not char count
- [x] `mypy --strict` passes

### T04 — app.state.embedder + EmbedderDep
- [x] `app.state.embedder = embedder` added to lifespan block in `main.py`
- [x] `get_embedder(request: Request) -> Embedder` added to `deps.py`
- [x] `EmbedderDep = Annotated[Embedder, Depends(get_embedder)]` exported from `deps.py`
- [x] Unit test covers embedder state access

### T05 — SplitterFactory
- [x] `ChunkStrategy` enum in `splitter_factory.py`: `recursive_character`, `sentence_window`, `semantic`
- [x] `SplitterFactory.build(settings, embedder=None)` returns correct `TextSplitter` per strategy
- [x] `semantic` without `embedder` raises `ConfigurationError` with message referencing ADR-009
- [x] Unknown strategy value raises `ConfigurationError`
- [x] Unit tests cover all three strategy paths + both error paths
- [x] `mypy --strict` passes

### T06 — Sentence window strategy
- [x] `nltk` sentence tokenizer splits text into sentences
- [x] Sentences grouped into windows of `chunk_size` tokens with `chunk_overlap` token overlap
- [x] Chunks shorter than `_MIN_CHUNK_CHARS` discarded (same rule as existing splitter)
- [x] Unit test: correct window grouping; handles single-sentence docs
- [x] `nltk.download("punkt_tab")` called once on module import (guarded with `quiet=True`)

### T07 — Semantic strategy (deferred)
- [x] Gate 3 (dry-run) result documented in ADR-009: CONFLICT — `langchain-experimental ^0.4.1` requires `langchain-text-splitters >=1.0.0`, project pins `^0.3`
- [x] `ChunkStrategy.semantic` raises `ConfigurationError("semantic strategy requires langchain-experimental; see ADR-009")`; deferred to Phase 2
- [x] Unit test: factory raises `ConfigurationError` for `semantic` strategy

### T08 — Refactor DocumentSplitter
- [x] `DocumentSplitter.__init__` calls `SplitterFactory.build(settings, embedder)` — no hardcoded `RecursiveCharacterTextSplitter`
- [x] Existing `split()` method body unchanged
- [x] All existing `test_ingestion_splitter.py` tests still pass
- [x] `mypy --strict` passes

### T09 — run_pipeline + ingest route
- [x] `run_pipeline` signature: `embedder: Embedder | None = None`
- [x] `embedder` forwarded to `DocumentSplitter(settings, embedder)`
- [x] Ingest route accepts `EmbedderDep` and passes it to `run_pipeline`
- [x] Error-path test: ingest route passes embedder through to pipeline
- [x] `mypy --strict` passes

### T10 — AnswerCorrectness metric
- [x] `AnswerCorrectness()` added to `metrics=[]` in `RagasEvaluator.run()`
- [x] `answer_correctness: float` field added to `EvaluationResult` dataclass
- [x] `_nanmean` called for `answer_correctness` from `ragas_result`
- [x] Unit test: `EvaluationResult` includes `answer_correctness`
- [x] Cost note in ADR-009 amended: eval run makes 5× LLM calls vs. 4-metric baseline

### T11 — Extend to_markdown()
- [x] Per-sample score table emitted after aggregate table (5 metrics per row, question index as row label)
- [x] Min / max / stddev per metric emitted below aggregate table (`statistics.stdev`)
- [x] Failure section: any sample where `faithfulness < 0.7` OR `answer_correctness < 0.7` printed with question text + scores
- [x] `dataclasses.asdict()` used (not `.model_dump()`) for serialisation — `EvaluationResult` is a `@dataclass`
- [x] Unit tests: failure section appears when threshold breached; absent when all pass; stddev computed correctly

### T12 — Baseline persistence + diff
- [x] `EvaluationResult` serialised via `dataclasses.asdict()` and written to `Settings.eval_baseline_path` as JSON
- [x] On next run, prior baseline loaded; diff column (current − prior, formatted `+0.02` / `−0.01`) appended to aggregate table
- [x] If baseline file missing, diff column omitted (first-run case)
- [x] Unit tests: diff column present when baseline exists; absent on first run; negative diff formatted correctly

### T13 — .gitignore entry
- [x] `data/eval_baseline.json` added to repo `.gitignore`
- [x] Confirmed `git status` does not surface the file after a simulated write

### T14 — Re-run RAGAS + document comparison
- [x] RAGAS run executed with default strategy (`recursive_character`, tiktoken-aware)
- [x] Results stored in `docs/evaluation_results.md` (5 metrics, per-sample table, failure section)
- [x] Baseline written to `data/eval_baseline.json` (verified round-trips via `load_baseline`)
- [ ] `sentence_window` strategy comparison — deferred to Phase 2 alongside `semantic`

### T15 — Dockerfile + README
- [x] `RUN python -m nltk.downloader punkt_tab` added to `Dockerfile`
- [x] README updated with note: "sentence_window strategy requires NLTK punkt_tab data (downloaded automatically on first import)"

---

## Phase Gate Criteria

All of the following must be true before Phase 1h begins:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | `pytest backend/tests/unit/ -q` | All tests green, including new splitter factory tests |
| G02 | `mypy backend/src/ --strict` | Zero errors |
| G03 | `ruff check backend/src/ backend/tests/` | Zero warnings |
| G04 | RAGAS re-run | `eval_baseline.json` exists at `Settings.eval_baseline_path`; all 5 metrics reported |
| G05 | ADR-009 status | `Accepted` and langchain-experimental dry-run result documented |
| G06 | `.env.example` | Covers `CHUNK_STRATEGY`, `CHUNK_TOKENIZER_MODEL`, `EVAL_BASELINE_PATH` |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `langchain-experimental` conflicts with langchain-core pin | Medium | Medium | Dry-run gate before implementation; defer semantic to Phase 2 if conflict |
| NLTK punkt download fails in Docker build (network) | Low | Medium | Pin NLTK data version; add `--quiet` flag; cache in layer |
| AnswerCorrectness LLM calls exceed Azure rate limit during eval | Low | Low | Add `asyncio.sleep` between samples if rate error encountered; document in eval script |
| Semantic chunking produces variable chunk counts, breaking BM25 index assumptions | Low | Medium | BM25 builds from whatever chunks are produced; no structural assumption on count |
