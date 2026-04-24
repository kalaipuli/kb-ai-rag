# CLAUDE.md — Development Rules & Principles

> This file is the index. Every session starts here. Load section files on demand based on the task at hand — do not load all files speculatively.

---

@.claude/docs/agent-conduct.md

---

## Project

Enterprise Agentic RAG platform. Five LangGraph agents orchestrate hybrid retrieval (Qdrant + BM25) over PDF/text knowledge articles, evaluated with RAGAS, deployed on Azure. See [GOAL.md](GOAL.md) and [PROJECT_PLAN.md](PROJECT_PLAN.md) for full context.

---

## Section Index

| File | When to read it |
|------|----------------|
| [agent-conduct.md](.claude/docs/agent-conduct.md) | **Auto-loaded** via `@import` above — always active, no manual read needed |
| [development-process.md](.claude/docs/development-process.md) | Before starting any task — decomposition rules, test discipline, Definition of Done, task registry lifecycle |
| [architecture-rules.md](.claude/docs/architecture-rules.md) | Before any design decision, new module, or cross-cutting change — connectors, AgentState, API versioning, SSE, ADR rules |
| [python-rules.md](.claude/docs/python-rules.md) | Before writing or reviewing any Python — types, async, structlog, error handling, imports |
| [frontend-rules.md](.claude/docs/frontend-rules.md) | Before touching `frontend/` — TypeScript strict mode, component conventions, fetch/SSE patterns |
| [git-rules.md](.claude/docs/git-rules.md) | Before committing or opening a PR — branch strategy, Conventional Commits, PR checklist |
| [project-context.md](.claude/docs/project-context.md) | When setting up the environment or orienting to the repo — layout, local dev commands, env vars |
| [anti-patterns.md](.claude/docs/anti-patterns.md) | When in doubt about an approach — prohibited patterns and correct alternatives |

---

## Always-Apply Rules

These three rules are active in every session without needing to load a section file.

**1. Definition of Done** — a task is not complete until:
- [ ] Implementation matches the agreed design
- [ ] Unit test written and passing
- [ ] `mypy` / `tsc --noEmit` passes
- [ ] `ruff` / `eslint` passes — zero warnings
- [ ] `.env.example` updated if a new env var was introduced
- [ ] ADR written if an architectural decision was made
- [ ] Committed with a valid Conventional Commit message

**2. No Orphaned Code** — do not write code that is not yet called or tested.

**3. Phase Gate Order** — do not implement Phase N+1 until Phase N gate passes. Current gate requirements are in [DASHBOARD.md](docs/registry/DASHBOARD.md).
