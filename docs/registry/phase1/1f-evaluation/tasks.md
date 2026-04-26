# Phase 1f — Evaluation Baseline

> Feature owner: data-engineer + backend-developer | Started: 2026-04-24

## Objective

Establish a RAGAS evaluation baseline for the MVP RAG pipeline. Produces the
faithfulness score required by the Phase 1 gate (≥ 0.70) and a persisted
results artifact that Phase 5 automation will regress against.

---

## Stack Note

RAGAS `^0.2` lives in `[tool.poetry.group.eval.dependencies]` — it is NOT
part of the API runtime. Install with `poetry install --with eval` before
running any evaluation script.

---

## Tasks

| # | Task | Owner | Status |
|---|------|-------|--------|
| 1 | Create task registry (this file) | project-manager | ✅ Done |
| 2 | Create synthetic knowledge corpus — 30+ `.txt` articles in `backend/data/knowledge/` | data-engineer |  ✅ Done |
| 3 | Create golden dataset — `backend/src/evaluation/golden_dataset.json` (20 Q&A pairs) | data-engineer | ✅ Done |
| 4 | Create `backend/src/evaluation/__init__.py` | backend-developer | ✅ Done |
| 5 | Create `backend/src/evaluation/ragas_eval.py` — RAGAS runner class | backend-developer | ✅ Done |
| 6 | Write unit tests — `backend/tests/unit/evaluation/test_ragas_eval.py` | backend-developer | ✅ Done (12 tests) |
| 7 | Create eval runner — `backend/scripts/run_eval.py` | backend-developer | ✅ Done |
| 8 | Persist results to `docs/evaluation_results.md` | backend-developer | ✅ Done (faithfulness 0.9153) |
| 9 | Update DASHBOARD.md, commit with Conventional Commit | project-manager | ✅ Done |

---

## Golden Dataset Schema

`golden_dataset.json` is a JSON array of objects:

```json
[
  {
    "id": "q001",
    "question": "...",
    "ground_truth": "..."
  }
]
```

At eval time the runner calls the RAG pipeline per question to get `answer` +
`retrieved_contexts`, then builds the RAGAS `EvaluationDataset`.

---

## RAGAS Metrics

| Metric | What it checks | Requires |
|--------|---------------|---------|
| `faithfulness` | Answer grounded in retrieved context | answer + contexts |
| `answer_relevancy` | Answer addresses the question | answer + question |
| `context_recall` | Contexts cover the ground truth | contexts + ground_truth |
| `context_precision` | Retrieved contexts are on-topic | contexts + question + ground_truth |

Target: **faithfulness ≥ 0.70** (Phase 1 gate).

---

## Definition of Done

- [x] 30+ files in knowledge corpus ingested without error (17 mixed PDF/TXT)
- [x] `golden_dataset.json` — 20 questions with ground-truth answers
- [x] `ragas_eval.py` — mypy strict clean, ruff clean
- [x] Unit tests passing (12 tests, including error-path tests)
- [x] `docs/evaluation_results.md` written with actual metric scores
- [x] faithfulness score ≥ 0.70 recorded (0.9153)
