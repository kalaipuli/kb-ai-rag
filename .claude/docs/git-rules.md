# Git & GitHub Rules

Applies to every commit, PR, and branch in this repository.

## Branch Strategy
```
main      ← protected; requires PR + CI pass; triggers CD to Azure
develop   ← integration; CI only
feature/* ← one feature per branch; PR → develop
```

## Commit Format — Conventional Commits (required)
```
feat(scope): short description
fix(scope): short description
docs(adr): add ADR-003
chore(deps): bump qdrant-client
```

Valid scopes: `ingestion`, `retrieval`, `agents`, `graph`, `api`, `frontend`, `infra`, `eval`, `adr`, `deps`, `config`

## PR Rules
- Every PR has a description explaining **why**, not just what
- No PR merges if CI fails (ruff + mypy + tsc + unit tests)
- ADR updated in same PR if an architectural decision was made
- `.env.example` updated in same PR if a new env var was added

## Commit Size
- One logical change per commit
- Never commit commented-out code
- Never commit `.env` files — `.gitignore` must exclude them
