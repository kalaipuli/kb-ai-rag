# Git & GitHub Rules

Applies to every commit, PR, and branch in this repository.

## Branch Strategy
```
main      ← protected; direct merge from feature branch after CI passes
feature/* ← one task or phase per branch; PR → main
fix/*     ← bug fixes and architect-review corrections
```

No `develop` branch. All work flows: `feature/x` → `main`.

## One Branch at a Time (enforced)

**Before creating any new branch:**
1. Run `git branch` — if any branch other than `main` exists, stop.
2. Resolve the open branch first: merge it to `main`, then delete it.
3. Only then create the new branch.

**No parallel branches.** A new branch must not be created while another is open, regardless of whether the work seems independent.

**Continue on the current branch** if the new work is part of the same phase or closely related to the open task. Create a new branch only when the open branch has been merged and deleted.

## Branch Lifecycle

```
1. git checkout -b feature/<name>   ← create only after main is clean
2. implement, commit atomically
3. merge to main (no-ff merge commit)
4. git branch -d feature/<name>     ← delete immediately after merge
5. confirm: git branch shows only main
```

Never leave a merged branch around. Delete it in the same session as the merge.

## Atomic Commits

Each commit must:
- Represent one complete, self-consistent change (passes tests, lints clean)
- Not mix unrelated changes (e.g. a bug fix bundled with a feature)
- Leave the repo in a working state — no half-finished implementations

Never commit:
- Commented-out code
- `.env` files (must be in `.gitignore`)
- Failing tests or linting errors

## Commit Format — Conventional Commits (required)

```
feat(scope): short description
fix(scope): short description
docs(adr): add ADR-003
chore(deps): bump qdrant-client
```

Valid scopes: `ingestion`, `retrieval`, `agents`, `graph`, `api`, `frontend`, `infra`, `eval`, `adr`, `deps`, `config`

One scope per commit. If a commit spans multiple scopes, split it.

## Merge Rules

- Merge with `--no-ff` to preserve branch history in a merge commit
- No PR merges if CI fails (ruff + mypy + tsc + unit tests)
- ADR updated in same PR if an architectural decision was made
- `.env.example` updated in same PR if a new env var was added
- Every merge commit description explains **why**, not just what
