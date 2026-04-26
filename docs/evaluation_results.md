# RAG Evaluation Results — Phase 1g Baseline

> Generated: 2026-04-26
> Dataset: `golden_dataset.json` (20 questions)
> Model: Azure OpenAI GPT-4o
> Retrieval: Hybrid (Qdrant dense + BM25) → cross-encoder re-ranker
> Chunking: `recursive_character` · token-aware (tiktoken `cl100k_base`) · chunk_size=1000 tokens · overlap=200 tokens
> Baseline persisted: `data/eval_baseline.json`

---

## RAGAS Evaluation Results

| Metric | Score |
|--------|-------|
| Faithfulness | 0.9028 |
| Answer Relevancy | 0.9752 |
| Context Recall | 0.9542 |
| Context Precision | 0.9642 |
| Answer Correctness | 0.7650 |

### Distribution Statistics

| Metric | Min | Max | StdDev |
|--------|-----|-----|--------|
| Faithfulness | 0.5000 | 1.0000 | 0.1898 |
| Answer Relevancy | 0.8992 | 1.0000 | 0.0290 |
| Context Recall | 0.6667 | 1.0000 | 0.1130 |
| Context Precision | 0.7000 | 1.0000 | 0.0817 |
| Answer Correctness | 0.2292 | 0.9945 | 0.2268 |

### Per-Sample Scores

| # | Faithfulness | Answer Relevancy | Context Recall | Context Precision | Answer Correctness |
|---|---|---|---|---|---|
| 1 | 1.0000 | 0.9565 | 1.0000 | 0.7000 | 0.7441 |
| 2 | 1.0000 | 0.9348 | 0.7500 | 1.0000 | 0.9026 |
| 3 | 0.5000 | 0.9888 | 1.0000 | 1.0000 | 0.9921 |
| 4 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.7352 |
| 5 | 0.8889 | 1.0000 | 1.0000 | 1.0000 | 0.9885 |
| 6 | 1.0000 | 0.9632 | 1.0000 | 1.0000 | 0.8813 |
| 7 | 1.0000 | 0.9885 | 1.0000 | 1.0000 | 0.9913 |
| 8 | 1.0000 | 0.9879 | 0.6667 | 0.8333 | 0.7985 |
| 9 | 1.0000 | 0.9344 | 1.0000 | 0.9167 | 0.4792 |
| 10 | 0.5000 | 0.9869 | 1.0000 | 1.0000 | 0.5414 |
| 11 | 1.0000 | 0.9812 | 1.0000 | 1.0000 | 0.9945 |
| 12 | 1.0000 | 0.8992 | 1.0000 | 1.0000 | 0.7334 |
| 13 | 0.5000 | 0.9970 | 1.0000 | 1.0000 | 0.4221 |
| 14 | 0.6667 | 0.9967 | 1.0000 | 1.0000 | 0.8380 |
| 15 | 1.0000 | 0.9944 | 1.0000 | 1.0000 | 0.9928 |
| 16 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.4733 |
| 17 | 1.0000 | 0.9323 | 1.0000 | 1.0000 | 0.8349 |
| 18 | 1.0000 | 0.9788 | 1.0000 | 1.0000 | 0.9923 |
| 19 | 1.0000 | 0.9827 | 0.6667 | 0.8333 | 0.2292 |
| 20 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.7354 |

### Failures (faithfulness or answer_correctness < 0.7)

- Sample 3: faithfulness=0.5000, answer_correctness=0.9921
- Sample 9: faithfulness=1.0000, answer_correctness=0.4792
- Sample 10: faithfulness=0.5000, answer_correctness=0.5414
- Sample 13: faithfulness=0.5000, answer_correctness=0.4221
- Sample 14: faithfulness=0.6667, answer_correctness=0.8380
- Sample 16: faithfulness=1.0000, answer_correctness=0.4733
- Sample 19: faithfulness=1.0000, answer_correctness=0.2292

---

## Phase 1g Gate

| Criterion | Required | Actual | Status |
|-----------|----------|--------|--------|
| `eval_baseline.json` exists with 5 metrics | ✅ | `data/eval_baseline.json` | ✅ Pass |
| Faithfulness | ≥ 0.70 | 0.9028 | ✅ Pass |
| Answer Correctness | reported | 0.7650 | ✅ Pass |
| Context Recall | reported | 0.9542 | ✅ Pass |
| Context Precision | reported | 0.9642 | ✅ Pass |
| Answer Relevancy | reported | 0.9752 | ✅ Pass |

---

## Strategy Comparison

Only `recursive_character` (token-aware, tiktoken `cl100k_base`) was run in Phase 1g. The `sentence_window` strategy is available but a comparative run was not executed — scheduled for Phase 2 alongside the `semantic` strategy (pending `langchain-experimental` upgrade). The delta column in subsequent runs will populate automatically via `to_markdown(prior=load_baseline(...))`.

---

## Notes

- Faithfulness dropped marginally from Phase 1f (0.9153 → 0.9028) — within normal run-to-run variance given the 20-sample dataset.
- Answer Correctness stddev (0.2268) is high; samples 9, 13, 16, 19 score below 0.5. These are candidates for golden dataset review in Phase 5.
- The `answer_correctness` metric requires an additional LLM call per sample vs. Phase 1f (5 calls/sample vs. 4).
