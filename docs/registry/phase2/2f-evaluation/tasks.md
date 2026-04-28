# Phase 2f — Agentic Pipeline Evaluation

> Status: ✅ Complete | Phase: 2f | Gate Passed: 2026-04-28
> Governed by: CLAUDE.md §9 — all tasks follow the Definition of Done checklist (§7)
> Last updated: 2026-04-28
>
> **Prerequisite:** Phase 2e gate must pass before any task here starts.
> **Goal:** Run RAGAS evaluation against the agentic pipeline using the same 20-question golden dataset from Phase 1f. Produce a comparison report (Phase 1 static chain vs Phase 2 agentic pipeline). Gate Phase 2 on RAGAS faithfulness ≥ 0.85.

---

## Context

Phase 1g persisted a RAGAS static chain baseline at `data/eval_baseline.json`:

| Metric | Phase 1 baseline |
|--------|-----------------|
| `faithfulness` | 0.9028 |
| `answer_relevancy` | 0.9752 |
| `context_recall` | 0.9542 |
| `context_precision` | 0.9642 |
| `answer_correctness` | 0.7650 |

This phase re-runs RAGAS against the agentic pipeline endpoint and:
1. Confirms the agentic pipeline meets the faithfulness gate (≥ 0.85)
2. Identifies which query types (factual / analytical / multi_hop) benefit most from agentic orchestration
3. Persists an agentic baseline JSON for Phase 5 automated regression gating
4. Documents results in a comparison report suitable for portfolio presentation

**Faithfulness gate rationale — why 0.85, not 0.90:**

The agentic pipeline introduces non-determinism via two retrieval expansion mechanisms: CRAG web fallback (Tavily) and Self-RAG re-retrieval. When these mechanisms activate, the retrieved context may be broader or more diverse than the static chain's tightly controlled Qdrant results. Broader context can introduce weakly-grounded sentences alongside accurate ones, slightly lowering RAGAS faithfulness scores on affected questions.

The 0.85 gate acknowledges this structural trade-off. It is not a quality regression — it is an acceptance that retrieval diversity has a faithfulness cost. The gate is not negotiable downward. If the agentic pipeline falls below 0.85, it means the CRAG or Self-RAG configuration is introducing too much off-topic context, which is a Phase 2 blocker requiring grading threshold tuning before proceeding.

If the agentic pipeline achieves faithfulness ≥ 0.9028 (matching or exceeding the static baseline), that is the preferred outcome. Falling between 0.85 and 0.9028 is acceptable but should be documented with a root cause analysis in the comparison report.

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ Done | Extend `EvaluationRunner` to support the agentic pipeline endpoint | backend-developer | 2e all |
| T02 | ✅ Done | Run RAGAS evaluation against agentic endpoint; persist results | backend-developer | T01 |
| T03 | ✅ Done | Produce comparison report (static vs agentic, per query type) | backend-developer | T02 |
| T04 | ✅ Done | Extend `GET /api/v1/eval/baseline` with `?pipeline=agentic` query parameter | backend-developer | T02 |
| T05 | ✅ Done | Phase 2 full gate review | architect | T01–T04 |

---

## Ordered Execution Plan

### Batch 1 — No dependencies (after 2e gate)
- **T01** — Extend evaluation runner

### Batch 2 — After T01 (requires live Azure OpenAI + Qdrant + Tavily)
- **T02** — Run RAGAS evaluation

### Batch 3 — After T02
- **T03** — Comparison report
- **T04** — Extend baseline API endpoint

### Batch 4 — After T01–T04
- **T05** — Phase 2 full gate review

---

## Definition of Done Per Task

### T01 — Extend `EvaluationRunner`

**File:** `backend/src/evaluation/runner.py` (extend existing — do not rewrite)

**What:** Add an `endpoint` parameter to `EvaluationRunner` (or its configuration object) that selects between the static chain path and the agentic pipeline path.

**Parameter contract:**

| Value | Target endpoint | Notes |
|-------|----------------|-------|
| `"static"` | `POST /api/v1/query` | Existing behaviour; must not regress |
| `"agentic"` | `POST /api/v1/query/agentic` | New path added in this task |

**Agentic runner behaviour:**
- Send a unique `X-Session-ID` UUID per question — prevents cross-question state contamination via `SqliteSaver` thread sharing
- Consume the full SSE stream for each question (all events until the `done` event)
- Extract `answer` by concatenating all `token` event `content` fields in order
- Extract `contexts` from the `citations` event (the list of source chunk texts)
- Construct the RAGAS input dict: `{question, answer, contexts, ground_truth}` — identical schema to the static runner output

**Existing static path constraint:** The `endpoint="static"` code path must produce identical output to the pre-amendment runner. No changes to static evaluation logic are permitted.

**Acceptance criteria:**
- [ ] `EvaluationRunner` accepts `endpoint: Literal["static", "agentic"]` parameter
- [ ] Agentic runner sends a unique `X-Session-ID` per question
- [ ] `answer` and `contexts` correctly extracted from the agentic SSE stream
- [ ] Static evaluation path unchanged (no regression)
- [ ] mypy backend/src/ --strict — zero errors
- [ ] pytest backend/tests/unit/ -q — all green

**Conventional commit:** `feat(eval): extend EvaluationRunner to support agentic pipeline endpoint`

---

### T02 — Run RAGAS evaluation (live Azure endpoint required)

**What:** Execute all 20 golden dataset questions against the agentic endpoint. This task requires the full stack to be running locally (`docker compose up`) with valid credentials: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and `TAVILY_API_KEY`.

**Pre-run checklist:**
- Knowledge files from Phase 1 ingested (17 files)
- All 5 LangGraph nodes confirmed to be real implementations (not stubs)
- `data/eval_agentic_baseline.json` not present in `.gitignore`

**Output file:** `data/eval_agentic_baseline.json`

**Output schema — same structure as `data/eval_baseline.json`:**

| Field | Type | Notes |
|-------|------|-------|
| `run_date` | `string` | ISO 8601 date |
| `endpoint` | `"agentic"` | Identifies the pipeline |
| `metrics` | `object` | Five RAGAS metric scores |
| `per_sample` | `array` | Per-question results |
| `failure_report` | `array` | Questions with metric failures |

The five metrics in `metrics`: `faithfulness`, `answer_relevancy`, `context_recall`, `context_precision`, `answer_correctness`.

**Hard gate:** `faithfulness ≥ 0.85`. If this gate is not met, Phase 2 is blocked pending architect review. Likely remediation: increase `GRADER_THRESHOLD`, reduce Tavily `max_results`, or disable CRAG for question types with low faithfulness scores.

**Preferred outcome:** `faithfulness ≥ 0.9028` (at or above static baseline). If faithfulness falls between 0.85 and 0.9028, the comparison report must include a root cause analysis section.

**Acceptance criteria:**
- [ ] Evaluation runs to completion; no unhandled exceptions; per-question timeout of 60 seconds enforced
- [ ] `data/eval_agentic_baseline.json` created with all 5 metrics and all 20 per-sample results
- [ ] `faithfulness ≥ 0.85` — hard gate
- [ ] All 20 questions answered (no skipped questions)

**Conventional commit:** `feat(eval): run RAGAS agentic baseline — faithfulness X.XXXX`

---

### T03 — Comparison report

**File:** `docs/evaluation_agentic_results.md` (new file)

**Required sections (all 7 must be present):**

| # | Section title | Content requirement |
|---|--------------|-------------------|
| 1 | Executive Summary | One table: Static Chain vs Agentic Pipeline, 5 RAGAS metrics side by side, delta column with explicit sign (+ or -) |
| 2 | Per Query Type Analysis | Breakdown by `query_type` (factual / analytical / multi_hop / ambiguous) — which types improved, which did not, supported by per-sample data |
| 3 | CRAG Activation Rate | Count and percentage of questions where `web_fallback = true` was observed in grader step data; interpretation of whether web fallback helped or hurt faithfulness |
| 4 | Self-RAG Activation Rate | Count and percentage of questions where `critic_score > CRITIC_THRESHOLD` triggered re-retrieval; interpretation of whether re-retrieval improved answer quality |
| 5 | Latency Impact | Average total `duration_ms` per node across all 20 questions; P95 end-to-end latency compared to Phase 1 static baseline P95 (8s) |
| 6 | Failure Analysis | Questions where `faithfulness < 0.7` or `answer_correctness < 0.7`; root cause per failure |
| 7 | Conclusion | One paragraph suitable for portfolio README; interview-ready prose describing what the agentic pipeline adds over the static chain in measurable terms |

**Acceptance criteria:**
- [ ] All 7 sections present
- [ ] Delta column shows sign clearly (e.g., `+0.012`, `-0.034`)
- [ ] CRAG and Self-RAG activation rates calculated from `per_sample` data in `eval_agentic_baseline.json`
- [ ] Conclusion paragraph is accurate and interview-ready

**Conventional commit:** `docs(eval): add Phase 2 agentic vs static pipeline comparison report`

---

### T04 — Extend `GET /api/v1/eval/baseline`

**File:** `backend/src/api/routes/eval.py` (extend existing — minimal change)

**What:** Add a `pipeline` query parameter to the existing endpoint. The default behaviour (no parameter) is unchanged — it continues to serve `data/eval_baseline.json` (static chain).

**Extended routing behaviour:**

| Request | Response |
|---------|---------|
| `GET /api/v1/eval/baseline` | Serves `data/eval_baseline.json` (static chain, default) |
| `GET /api/v1/eval/baseline?pipeline=agentic` | Serves `data/eval_agentic_baseline.json` |
| `GET /api/v1/eval/baseline?pipeline=agentic` when file does not exist | HTTP 404 with `{"detail": "Agentic baseline not yet generated"}` |

**Acceptance criteria:**
- [ ] Default behaviour (no query param) unchanged
- [ ] `?pipeline=agentic` returns agentic baseline; 404 if file not found
- [ ] mypy backend/src/ --strict — zero errors
- [ ] Unit tests for both paths added to existing `test_eval_router.py`

**Conventional commit:** `feat(api): extend eval baseline endpoint to serve agentic pipeline results`

---

### T05 — Phase 2 full gate review

**What:** Run all Phase 2 gate commands and confirm zero failures before marking Phase 2 complete and updating DASHBOARD.md.

**Backend gate commands (zero output expected):**
- ruff check backend/src/ backend/tests/
- mypy backend/src/ --strict
- pytest backend/tests/unit/ -q --tb=short
- grep -rn "RetrievalQA\|LLMChain\|StuffDocumentsChain\|ConversationalRetrievalChain" backend/src/ --include="*.py"
- grep -rn "api_key=settings\." backend/src/ --include="*.py" | grep -v "get_secret_value"
- grep -rn "AsyncQdrantClient(\|AzureChatOpenAI(\|AzureOpenAIEmbeddings(" backend/src/api/routes/ --include="*.py"
- grep -rn "^class " backend/src/ --include="*.py" | awk -F: '{print $NF}' | sort | uniq -d
- grep -rn "^[[:space:]]*print(" backend/src/ --include="*.py"

**Frontend gate commands:**
- tsc --noEmit
- npm run lint
- npm run test
- npm run build

**Manual checks:**

| Check | Pass condition |
|-------|---------------|
| `docker compose up` | Full stack running in < 90s |
| Factual query | Both panels respond correctly |
| Analytical query | Agentic panel shows HyDE rewrite in Router step card |
| Complex query (multi-hop) | CRAG web fallback activates if a knowledge-gap question is used |
| Verdict component | Renders correctly after both streams complete |
| Latency bars | Proportional widths shown after streaming ends; hidden during streaming |

**Acceptance criteria:**
- [ ] All backend and frontend gate commands produce zero output / zero errors
- [ ] All manual checks pass
- [ ] `data/eval_agentic_baseline.json` faithfulness ≥ 0.85
- [ ] DASHBOARD.md updated: Phase 2 marked ✅ Complete with gate date

**Conventional commit:** `chore(phase2): complete Phase 2 gate review — all criteria met`

---

## Phase 2 Overall Gate Criteria

Phase 2 is complete when ALL of the following are true:

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | Phase 2a (Gate Zero) | ✅ All 5 tasks done, CI green |
| G02 | Phase 2b (Graph Skeleton) | ✅ Graph compiles, all stub tests green |
| G03 | Phase 2c (Agent Nodes) | ✅ All 5 nodes + smoke test green |
| G04 | Phase 2d (Agentic API) | ✅ SSE endpoint live, all format checks pass |
| G05 | Phase 2e (Parallel UI) | ✅ Both panels demo-able, all frontend tests green |
| G06 | RAGAS faithfulness (agentic) | ≥ 0.85 |
| G07 | RAGAS faithfulness (no regression) | ≥ 0.9028 preferred; between 0.85–0.9028 requires root cause documentation |
| G08 | mypy backend/src/ --strict | Zero errors |
| G09 | ruff check | Zero warnings |
| G10 | tsc --noEmit | Zero errors |
| G11 | eslint | Zero warnings |
| G12 | npm run build | Succeeds |
| G13 | pytest backend/tests/unit/ -q | All green |
| G14 | docker compose up | Full stack in < 90s |
| G15 | Phase 1 `query.py` route | Git diff shows zero modifications |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Agentic faithfulness < 0.85 (CRAG web fallback introduces off-topic context) | Medium | High | Increase `GRADER_THRESHOLD`; reduce Tavily `max_results` to 3; require architect review before unblocking |
| RAGAS evaluation cost exceeds budget | Low | Medium | Estimate: ~80 GPT-4o-mini calls + 20 GPT-4o calls for 20 questions. Acceptable for a one-time baseline run |
| Evaluation runner hangs on agentic SSE stream (no timeout) | Low | Medium | Enforce 60s per-question timeout in runner; log and mark question as failed on timeout |
| `data/eval_agentic_baseline.json` accidentally excluded by `.gitignore` | Low | Medium | Confirm `data/*.json` is not gitignored before T02; confirm with `git status` after the file is written |
