# Architect Review Checklist

Read this at the start of every architect review, before reading any implementation detail. Run each command first — findings from grep results are cheaper to fix than ones discovered mid-review.

> **Environment rule:** `grep`/`find`/`awk` may be run bare. All Python tool commands (`ruff`, `mypy`, `pytest`) must use `poetry run`. All Node tool commands must use `npm run`. See `project-context.md` Backend Commands for canonical forms. Any command block you write in an ADR, fix spec, or task registry must follow this convention.

## Priority 1 — Schema uniqueness (most expensive to fix late)

Duplicated types across modules propagate silently and require forced consolidation later (Phase 1c issue #4).

```bash
grep -rn "^class " backend/src/ --include="*.py" | \
  awk -F: '{print $NF}' | sort | uniq -d
```

Any duplicated class name is a **Critical** finding regardless of whether the fields match. Resolution: ADR-008 — canonical location is `backend/src/api/schemas.py`.

## Priority 2 — Lifespan singleton compliance

Per-request client construction causes connection churn and defeats the lifespan pattern (Phase 0 C1, Phase 1d F04).

```bash
grep -rn "AsyncQdrantClient(\|AzureChatOpenAI(\|AzureOpenAIEmbeddings(" \
  backend/src/ --include="*.py" | \
  grep -v "src/api/main.py\|src/api/deps.py"
```

Any match outside `main.py` or `deps.py` is a **High** finding.

## Priority 3 — SecretStr boundary compliance

Same bug appeared in four separate files across four phases (Phase 0 C9, Phase 1a F05, Phase 1c #2, Phase 1d F01).

```bash
grep -rn "api_key=settings\." backend/src/ --include="*.py" | grep -v "get_secret_value()"
```

Any `api_key=settings.something` without `.get_secret_value()` is a **Critical** finding.

## Priority 4 — ADR coverage for non-trivial choices

```bash
ls docs/adr/
```

For each chain composition, orchestration pattern, or schema ownership decision in the phase, confirm an ADR exists. Missing ADR for a meaningful choice (e.g., RetrievalQA vs LCEL in Phase 1c) is a **High** finding. Ask: "What choices did the implementer make that aren't covered by an ADR?"

## Priority 5 — Async hygiene

Blocking calls on the event loop cause intermittent stalls under load (Phase 1a F01).

```bash
grep -rn "\.read_text(\|PdfReader\|pickle\.load\|pickle\.dump" \
  backend/src/ --include="*.py" | grep -v "asyncio.to_thread"
```

Any synchronous I/O call not wrapped in `asyncio.to_thread` inside an `async def` context is a **High** finding.

## Priority 6 — Error path test coverage

For every module introduced in the phase, verify at least one error-path test per external call exists.

```bash
# grep is fine bare; for running tests use poetry run pytest
grep -c "pytest.raises\|side_effect.*Error\|side_effect.*Exception" \
  backend/tests/unit/test_<module_name>.py
```

A count of zero for any module that calls Azure or Qdrant is a **Major** finding. Happy-path-only test files are incomplete.

## Priority 7 — Suppressor audit

```bash
grep -rn "noqa\|type: ignore" backend/src/ --include="*.py"
```

Every suppressor must have an inline justification. Any `# noqa: B008` on a `Depends()` call in a route means `SettingsDep` from `deps.py` was not used — that is a **Major** finding (Phase 1d F07).

---

## Retrospective Root Cause

Across Phases 0–1d, every critical and high finding was detectable with a grep **before** code was written. The rules existed in `architecture-rules.md`, `python-rules.md`, and `anti-patterns.md`. The root cause was that the implementing agent had no structured obligation to run these checks before starting. The architect review ran post-hoc at maximum correction cost.

The pre-implementation gates in `development-process.md §1` and the DoD command gates in `development-process.md §7` convert advisory awareness into mandatory, traceable, grep-output-verified gates at both ends of implementation.
