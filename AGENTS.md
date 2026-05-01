# AGENTS.md — Development Rules & Principles

> This file is the index. Every session starts here. Load section files on demand based on the task at hand — do not load all files speculatively.

---

@.claude/docs/agent-conduct.md

---

## Project

Enterprise Agentic RAG platform. Five LangGraph agents orchestrate hybrid retrieval (Qdrant + BM25) over PDF/text knowledge articles, evaluated with RAGAS, deployed on Azure. See [GOAL.md](GOAL.md) and [PROJECT_PLAN_SUMMARY.md](PROJECT_PLAN_SUMMARY.md) for full context.

---

## Section Index

| File | When to read it |
|------|----------------|
| [agent-conduct.md](.claude/docs/agent-conduct.md) | **Auto-loaded** via `@import` above — always active, no manual read needed |
| [development-process.md](.claude/docs/development-process.md) | Before starting any task — decomposition rules, test discipline, Definition of Done, task registry lifecycle |
| [architecture-rules.md](.claude/docs/architecture-rules.md) | Before any design decision, new module, or cross-cutting change — connectors, AgentState, API versioning, SSE, ADR rules |
| [python-rules.md](.claude/docs/python-rules.md) | Before writing or reviewing any Python — types, async, structlog, error handling, imports |
| [frontend-rules.md](.claude/docs/frontend-rules.md) | Before touching `frontend/` — TypeScript strict mode, component conventions, fetch/SSE patterns |
| [git-rules.md](.claude/docs/git-rules.md) | For any development, enhancements and bug fixes. Also, Before committing or opening a PR — branch strategy, Conventional Commits, PR checklist |
| [project-context.md](.claude/docs/project-context.md) | When setting up the environment or orienting to the repo — layout, local dev commands, env vars |
| [anti-patterns.md](.claude/docs/anti-patterns.md) | When in doubt about an approach — prohibited patterns and correct alternatives |
| [architect-review-checklist.md](.claude/docs/architect-review-checklist.md) | At the start of every architect review — 7 priority-ordered grep checks to run before reading implementation detail |

---

## Orchestrator Role

The main Claude instance (this session) is the **orchestrator**. Its job is to plan, decompose, brief, and validate — not to implement. All actual implementation, testing, and file writes are performed by sub-agents.

**Orchestrator responsibilities:**
- Read all required section files before forming a plan
- Run pre-implementation gate checks (grep commands from `development-process.md §1`) and confirm results before briefing an agent
- Compose complete, self-contained sub-agent briefs that include all required context
- Validate sub-agent output (read changed files, run DoD gate commands) before marking a task done
- Update `tasks.md` and `DASHBOARD.md` after each task completes

**What the orchestrator must NOT do:**
- Write implementation code directly (use `backend-developer`, `frontend-developer`, etc.)
- Write tests directly (use `tester` or the implementing agent)
- Skip sub-agent delegation and implement inline to save time

---

## Sub-Agent Briefing Requirements

When invoking a sub-agent, you **must** read and pass the full content of the required files listed below for that agent type. Do not summarise or paraphrase — pass the actual file content in the agent prompt. A sub-agent brief that omits a required file is incomplete and may produce non-compliant output.

| Agent | Required files to pass (read and include verbatim) |
|-------|---------------------------------------------------|
| `backend-developer` | `development-process.md`, `python-rules.md`, `anti-patterns.md` |
| `frontend-developer` | `development-process.md`, `frontend-rules.md`, `anti-patterns.md` |
| `architect` | `architecture-rules.md`, `development-process.md`, `anti-patterns.md` |
| `data-engineer` | `development-process.md`, `python-rules.md`, `anti-patterns.md` |
| `tester` | `development-process.md`, `python-rules.md` |
| `test-manager` | `development-process.md` |
| `security-reviewer` | `architecture-rules.md`, `python-rules.md`, `anti-patterns.md` |
| `project-manager` | `development-process.md` |

**Additional context required for every `backend-developer` invocation:**
- The relevant `tasks.md` entry (full DoD spec for the task being implemented)
- The current stub file being replaced (so the agent knows exactly what to overwrite)
- All `AgentState` fields and any injected dependencies the node touches
- The pre-implementation gate check results (§1 of `development-process.md`) run and confirmed before the brief is sent

---

## Always-Apply Rules

These three rules are active in every session without needing to load a section file.

**1. Definition of Done** — a task is not complete until all DoD command gates in `development-process.md §7` pass with zero output, **plus**:
- [ ] Implementation matches the agreed design
- [ ] Unit test written and passing (including at least one error-path test per external call)
- [ ] `mypy --strict` / `tsc --noEmit` passes — zero errors
- [ ] `ruff` / `eslint` passes — zero warnings
- [ ] `.env.example` updated if a new env var was introduced
- [ ] ADR written if an architectural decision was made
- [ ] Committed with a valid Conventional Commit message

**2. No Orphaned Code** — do not write code that is not yet called or tested.

**3. Phase Gate Order** — do not implement Phase N+1 until Phase N gate passes. Current gate requirements are in [DASHBOARD.md](docs/registry/DASHBOARD.md).
