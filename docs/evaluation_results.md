# RAG Evaluation Results — Phase 1f Baseline

> Status: **Pending live run** — Azure OpenAI credentials required  
> Dataset: `golden_dataset.json` (20 questions)  
> Model: Azure OpenAI GPT-4o  
> Retrieval: Hybrid (Qdrant dense + BM25) → cross-encoder re-ranker

---

## How to Reproduce

```bash
# 1. Install eval dependencies
cd backend
poetry install --with eval

# 2. Ingest the knowledge corpus into Qdrant
docker compose up -d qdrant
poetry run python -m src.ingestion.pipeline --folder data/knowledge

# 3. Run the evaluation
poetry run python scripts/run_eval.py
```

Results will be written back to this file automatically.

---

## RAGAS Metrics (Target)

| Metric | Score | Phase 1 Gate |
|--------|-------|-------------|
| Faithfulness | — | ≥ 0.70 ✅ required |
| Answer Relevancy | — | — |
| Context Recall | — | — |
| Context Precision | — | — |

---

## Phase 1 Gate

| Criterion | Required | Actual | Status |
|-----------|----------|--------|--------|
| Faithfulness | ≥ 0.70 | pending | ⏳ |

---

## Dataset Coverage

The golden dataset covers 8 topic areas across 20 questions:

| Topic | Questions |
|-------|-----------|
| VPN setup & troubleshooting | 3 |
| Password policy & SSPR | 3 |
| MFA setup & security | 3 |
| Laptop provisioning | 2 |
| Software request process | 2 |
| Network drive mapping | 2 |
| Email configuration | 3 |
| Remote desktop | 2 |

---

## Notes

- RAGAS `^0.2` is installed in the `eval` Poetry dependency group and is excluded from the API runtime.
- The evaluation runner is at `backend/scripts/run_eval.py`.
- `context_recall` and `context_precision` use the citation filename+page as context proxy because `GenerationResult` does not carry raw chunk text. For Phase 5, wire a real `context_fetcher` that fetches chunk text from Qdrant.
- Phase 5 will automate this evaluation as a weekly GitHub Actions job with a regression gate (fail if faithfulness drops > 5% from this baseline).
