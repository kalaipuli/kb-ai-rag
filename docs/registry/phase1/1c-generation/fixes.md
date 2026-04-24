# Phase 1c — Architect Review & Fix Registry

> Reviewed: 2026-04-24 | Status: 🔴 Blocked on #1, #2, #3

---

## Issues

| # | Severity | Category | Description | File:Line | Fix | Assigned To |
|---|----------|----------|-------------|-----------|-----|-------------|
| 1 | **Critical** | Pydantic v2 / Async | `KBRetriever` bare underscore annotations are not Pydantic v2 `PrivateAttr` — causes `ValidationError` at runtime | `chain.py:34-45` | Replace with `PrivateAttr()`; assign after `super().__init__()` | `backend-developer` |
| 2 | **Critical** | Config / Auth | `SecretStr` passed raw to `AzureChatOpenAI(api_key=...)` — auth will always fail | `chain.py:124` | Change to `.get_secret_value()` | `backend-developer` |
| 3 | **High** | Architecture / ADR | `RetrievalQA` is deprecated in LangChain 0.3; no ADR for LCEL vs RetrievalQA trade-off | `chain.py:7,134` | Write `docs/adr/007-lcel-vs-retrieval-qa.md`; migrate to LCEL expression | `architect` (ADR) + `backend-developer` (migration) |
| 4 | **High** | Schema Duplication | `generation/models.py::Citation` and `GenerationResult` duplicate `api/schemas.py::CitationItem` / `QueryResponse` field-for-field | `generation/models.py:6-22` | Decide ownership (architect); consolidate to one definition | `architect` (decision) + `backend-developer` (refactor) |
| 5 | **High** | Concurrency / Design | `_last_results` side-channel is mutable instance state; resolved by LCEL migration (#3) | `chain.py:70,129,167` | Eliminate with LCEL; pass scores via `Document.metadata` | `backend-developer` |
| 6 | **Medium** | Performance | `AzureChatOpenAI` client created on every `generate()` call | `chain.py:122-133` | Move construction to `__init__`; reuse `self._llm` | `backend-developer` |
| 7 | **Medium** | Type Safety | `chain: Any` and `# type: ignore` suppress mypy; resolved by LCEL migration (#3) | `chain.py:134`, `test_generation_chain.py:173,308` | Resolved by #3 | `backend-developer` |
| 8 | **Medium** | LangChain API | `{question}` key in prompt implicitly couples to `StuffDocumentsChain` internals | `chain.py:143`, `prompts.py:29` | Resolved by LCEL migration (#3) | `backend-developer` |
| 9 | **Medium** | Schema / Sentinel | `page_number: int` uses `-1` as sentinel with no documentation; inconsistent with `int \| None` convention | `generation/models.py:13`, `chain.py:163` | Change to `int \| None = None` or document sentinel | `backend-developer` |
| 10 | **Medium** | ADR | No ADR for `stuff` vs `map-reduce` context strategy; subsumed by issue #3's ADR | `chain.py:136` | Cover in ADR-007 | `architect` |
| 11 | **Low** | Test Coverage | No test for negative cross-encoder scores (common case for irrelevant passages) | `test_generation_chain.py` | Add `test_generation_chain_negative_score_confidence_low` | `test-manager` |
| 12 | **Low** | Test Coverage | `test_no_docs_confidence_zero` will need rewrite after LCEL migration | `test_generation_chain.py:216-235` | Track post-migration | `test-manager` |
| 13 | **Low** | Logging | Error log missing `session_id`; acceptable for Phase 1, needed in Phase 2 | `chain.py:145` | Add `session_id` when `AgentState` is available in Phase 2 | `backend-developer` |

---

## No Issues Found In

- `exceptions.py` — `GenerationError` pattern correct
- Structlog usage — all log calls are structured events
- Import style — all absolute, no wildcards
- `.env.example` — no new env vars; no update needed
- `__init__.py` — correctly empty
- Phase gate order — no Phase 2 code introduced

---

## Fix Priority

1. **#1, #2** — runtime-breaking; fix immediately
2. **#3** — ADR written by architect, then LCEL migration by backend-developer (resolves #5, #7, #8)
3. **#4, #6, #9** — after LCEL migration
4. **#11, #12** — single test commit last

**Phase 1c gate is blocked until #1, #2, #3 are resolved.**
