# Development Process

These principles apply to every change, regardless of size or phase. They are not optional.

## 1. Decompose Before You Code
Every piece of work follows the same hierarchy before a single line is written:

```
Phase → Feature → Tasks → Subtasks (if needed)
```

- A **Phase** delivers a working vertical slice of the system (e.g., MVP RAG pipeline)
- A **Feature** is a coherent capability within a phase (e.g., hybrid retrieval, ingestion pipeline)
- A **Task** is a single, completable unit of work — one function, one module, one endpoint
- Write the task list before starting. Never start coding an undefined task.

### Pre-implementation gate — mandatory before writing any code

Before the implementing agent writes a single line, the following must be verified and recorded in the task's registry entry. Implementation does not start until all four checks are pasted as output in `docs/registry/phaseN/tasks.md`.

**Gate 1 — No duplicate schema for the type this task will produce:**
```bash
grep -rn "class <YourTypeName>" backend/src/ --include="*.py"
```
Expected: zero matches. Multiple definitions of the same concept is a blocker. Canonical location: `backend/src/api/schemas.py`.

**Gate 2 — ADR read for every architectural choice in the task plan:**
List which ADRs govern the approach (`ls docs/adr/`). If no ADR covers a meaningful design choice in the plan, write the ADR first.

**Gate 3 — Lifespan singleton path confirmed for every shared resource:**
```bash
grep -n "app.state\|QdrantClientDep\|SettingsDep\|GenerationChainDep" \
  backend/src/api/deps.py backend/src/api/main.py
```
If the resource is not on `app.state` with a `Dep` alias in `deps.py`, add it there before writing the route.

**Gate 4 — No deprecated LangChain symbols in the plan:**
```bash
grep -rn "RetrievalQA\|LLMChain\|StuffDocumentsChain\|ConversationalRetrievalChain" \
  backend/src/ --include="*.py"
```
Expected: zero matches. Use LCEL (`prompt | llm | parser`) for all chain composition.

## 2. Small, Incremental Changes
- Each commit implements exactly one task. Not one feature — one task.
- A change that cannot be described in a single Conventional Commit subject line is too large — split it.
- Never refactor and implement in the same commit.
- Changes are integrated continuously; no long-running branches that diverge for days.

## 3. Test First, Then Code
- Write the unit test **before or alongside** the implementation — never after.
- Every task has at least one corresponding test. No exceptions.
- A task is not complete until its test is written **and passes**.
- Test the behaviour (what the function does), not the implementation (how it does it).

**Error-path coverage is required, not optional.** For every function that calls an external service (Azure OpenAI, Qdrant, disk I/O), the test file must include at least one test that:
1. Patches the external call to raise an exception
2. Asserts the correct domain exception is raised by the function under test
3. Asserts a structlog error event is emitted

A task whose tests cover only the happy path does **not** satisfy the Definition of Done.

```
Task: implement RRF fusion
  → Write test_hybrid.py::test_rrf_merges_and_ranks_correctly first
  → Write test_hybrid.py::test_rrf_raises_on_malformed_input (error path)
  → Implement hybrid.py::reciprocal_rank_fusion
  → Run test — green → commit
```

## 4. Automate All Tests
- Tests run automatically on every commit via GitHub Actions CI.
- No manual "I tested it locally" is sufficient for a merge — CI must be green.
- Tests are organised into:
  - `tests/unit/` — fast, no I/O, no network, run in < 30s total
  - `tests/integration/` — requires Docker Compose up, tests real Qdrant + API behaviour
- Unit tests run on every PR. Integration tests run on merge to `develop` and `main`.
- A failing test is a blocked task. Fix the test before moving to the next task.

## 5. Cross-Check Integrity After Every Feature
Before marking a feature complete and moving to the next:
- Run the full unit test suite — all green
- Run mypy and ruff — zero errors
- Run the TypeScript compiler check (`tsc --noEmit`) if frontend was touched
- Manually verify the end-to-end path for the feature (not just the unit under test)
- Check that no existing tests were broken (regression check)
- Review that the `AgentState` schema, API schemas, and metadata schemas are still consistent

## 6. Use the Latest Stable Versions
- Always pin to the latest **stable** (non-alpha, non-beta) version of every dependency.
- Check for newer versions when starting a new phase, not mid-phase.
- Version upgrades are their own task and commit — never bundled with feature work.
- Document the version choice in `pyproject.toml` comments if a newer version was intentionally skipped (e.g., breaking API change).

## 7. Definition of Done (per task)
A task is done when **all** of the following commands produce zero output or pass cleanly. Run them in order; a failure is a blocker — do not mark the task ✅ Done until every command is clean.

```bash
# 1. Lint — zero warnings
ruff check backend/src/ backend/tests/

# 2. Type check — strict, zero errors
mypy backend/src/ --strict

# 3. Tests — all green
pytest backend/tests/unit/ -q --tb=short

# 4. No deprecated LangChain symbols
grep -rn "RetrievalQA\|LLMChain\|StuffDocumentsChain\|ConversationalRetrievalChain" \
  backend/src/ --include="*.py"

# 5. No raw SecretStr passed to third-party clients
grep -rn "api_key=settings\." backend/src/ --include="*.py" | grep -v "get_secret_value"

# 6. No client instantiation inside route handlers
grep -rn "AsyncQdrantClient(\|AzureChatOpenAI(\|AzureOpenAIEmbeddings(" \
  backend/src/api/routes/ --include="*.py"

# 7. No duplicate class names across modules
grep -rn "^class " backend/src/ --include="*.py" | awk -F: '{print $NF}' | sort | uniq -d

# 8. No print() in source files
grep -rn "^[[:space:]]*print(" backend/src/ --include="*.py"

# 9. .env.example covers every new Settings field (manual check)
#    Compare Settings fields vs .env.example entries; report any gap
```

In addition to the command gates above, confirm:
- [ ] Implementation matches the agreed design (no scope creep)
- [ ] `.env.example` updated for every new `Settings` field
- [ ] ADR written if an architectural decision was made
- [ ] Committed with a valid Conventional Commit message
- [ ] Error-path test exists for every function that calls an external service

## 8. No Orphaned Code
- Do not write code that is not yet called or tested — it will rot and mislead.
- Stub functions are allowed only if they are called by a test that documents the expected behaviour.
- If a planned function is deferred to a later phase, it does not exist in code yet.

## 9. Maintain a Task Status Tracker

All task registries live under `docs/registry/`. This directory is the ground truth for all task, fix, and phase-gate tracking across the full project lifetime.

### Directory layout

```
docs/registry/
├── DASHBOARD.md          ← cross-phase project status board (project-manager owns)
├── _template/
│   └── tasks.md          ← copy this when starting a new phase
├── phase0/
│   ├── tasks.md          ← Phase 0 task registry
│   └── fixes.md          ← architect review fixes (created on demand)
├── phase1/
│   └── tasks.md
└── phaseN/
    └── tasks.md
```

### Lifecycle rules

- **Before a phase starts:** copy `_template/tasks.md` → `registry/phaseN/tasks.md`; list all tasks as `⏳ Pending`; update `DASHBOARD.md` to mark the phase active.
- **During work:** update each task's status as it progresses. Never leave a stale status.
- **After a gate passes:** update `DASHBOARD.md` with the gate result and completion date; link the new phase registry.
- **When architect review produces fixes:** create `registry/phaseN/fixes.md`; all critical fixes must clear before Phase N+1 starts.

### Task status lifecycle

```
⏳ Pending → 🔄 In Progress → ✅ Done
```

- Only one task should be `🔄 In Progress` per agent at a time.
- A task must not reach `✅ Done` unless every item in the Definition of Done (§7) is satisfied.

### Mandatory task columns (every task table)

```
| ID | Status | Task | Agent | Depends On |
```

### DASHBOARD.md

`docs/registry/DASHBOARD.md` is the single cross-phase view. It must always show:
- Phase status table (all phases, gate pass/fail date)
- Currently in-progress tasks (cross-phase)
- Blocked / at-risk items

The `project-manager` agent updates it at every phase transition and gate check.

```
| T01 | ✅ Done        | Write ADRs              | architect    | —       |
| T02 | 🔄 In Progress | Create folder structure  | architect    | T01     |
| T03 | ⏳ Pending     | Define test plan        | test-manager | T01,T02 |
```

## 10. Version Control

- Create a new branch for every task or change. Use clear, descriptive branch names (e.g., `feature/add-login`, `fix/api-timeout`).
- Keep changes scoped to the task; avoid mixing unrelated updates in the same branch.
- Test all changes thoroughly and fix any issues before committing.
- Once validated, commit with meaningful messages that explain what was changed and why.
- Merge the branch into `main` only after testing is complete and the work is stable.
