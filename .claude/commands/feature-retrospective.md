---
description: Write a feature retrospective summary.md to the correct registry folder after a feature implementation session. No arguments needed — phase and feature are inferred from the conversation history.
allowed-tools: Read, Write, Bash
---

## Purpose

Generate a concise `summary.md` retrospective for the feature just completed. Everything is inferred from this conversation — no arguments required. The file is written to the matching `docs/registry/phaseN/Xn-feature/` folder and becomes the handoff document for the next implementer.

## Step 1 — Infer phase and feature from the conversation

Read the conversation history and identify:

- **PHASE** — the phase label being worked on (e.g. `2a`, `2b`, `1d`). Look for explicit phase references, task registry mentions, DASHBOARD entries, or ADR context. Cross-check by running `find docs/registry -mindepth 2 -maxdepth 2 -type d | sort` to see what phases exist on disk.
- **FEATURE_SLUG** — the feature or section worked on (e.g. `gate-zero`, `graph-skeleton`). Derive from the topic of work: file paths touched, tasks discussed, feature names mentioned.
- **FEATURE_NAME** — a readable title (e.g. "Gate Zero Architect Review", "Graph Skeleton").
- **GATE_STATUS** — infer from the conversation: if all DoD commands were shown as passing, use `Passed`; if commands were partially run or skipped, use `Pending`; if a blocker was explicitly noted, use `Blocked`. Default: `Pending`.

## Step 2 — Locate the registry folder

Run:

```bash
find docs/registry -mindepth 2 -maxdepth 2 -type d | sort
```

Match the inferred PHASE and FEATURE_SLUG against the folder list. Convention: `docs/registry/phase<N>/<PHASE>-<FEATURE_SLUG>/` (e.g. `docs/registry/phase2/2a-gate-zero/`).

**Stop immediately with an error if no folder matches** — print the inferred phase/feature and the full folder list, then ask the user to clarify.

## Step 3 — Determine the output filename

Check whether `summary.md` already exists in the matched folder:

```bash
ls <matched-folder>/summary*.md 2>/dev/null
```

- If no `summary.md` exists → write `summary.md`.
- If `summary.md` exists → find the next available version: `summary-2.md`, `summary-3.md`, etc. Never overwrite an existing file.

## Step 4 — Write the summary file

Populate all sections entirely from the conversation history. Do not read `tasks.md` or `fixes.md` — the conversation is the sole source. Write the file to the matched folder using the **Output Format** below.

After writing, print:
- `Written: <full path> — review before committing with: docs(registry): add <feature-slug> summary`
- `DASHBOARD.md update required — run project-manager gate check for feature <PHASE>-<FEATURE_SLUG>.`

## Output Format

Write exactly this structure. Every section is required; write `— none identified` if a section has no content. Do not add sections not listed here.

```markdown
# Phase <PHASE> — <Feature Name> — Retrospective Summary

> Date: <YYYY-MM-DD> | Phase: <PHASE> | Feature: <feature-slug> | Gate Status: <GATE_STATUS>

---

## Feature Summary

<4–5 sentences. What was built, why it matters, and where it fits in the system. No bullet points — prose only. Reference the phase goal.>

---

## Architecture

<Short technical description. Use a table or bullets. Must include:>

| Item | Detail |
|------|--------|
| Pattern | <e.g. LangGraph StateGraph with TypedDict AgentState> |
| Components | <list of new modules / files introduced> |
| AgentState changes | <fields added/modified with types and reducers, or "none"> |
| ADRs governing this feature | <ADR-NNN titles, or "none"> |
| Cross-cutting contracts changed | <schema changes, API changes, or "none"> |

---

## Design

<Short technical description — decisions, trade-offs, version pins. Use a table or file references.>

| Item | Detail |
|------|--------|
| Key files | <repo-absolute paths, e.g. backend/src/graph/state.py:12> |
| Libraries / versions | <package==version for any new dependency> |
| Settings fields added | <field name + .env.example key, or "none"> |
| Tasks driving this design | <T01, T03 from [tasks.md](tasks.md)> |
| Findings that shaped the design | <F01, F02 from [fixes.md](fixes.md), or "none"> |

---

## Phase Gate Evidence

<List the gate commands that were run and their result. Do not embed full output — link to the gate criteria in tasks.md.>

| Command | Result |
|---------|--------|
| `poetry run ruff check backend/src/ backend/tests/` | ✅ zero warnings |
| `poetry run mypy backend/src/ --strict` | ✅ zero errors |
| `poetry run pytest backend/tests/unit/ -q` | ✅ N passed |
| `npm run tsc -- --noEmit` | ✅ zero errors / N/A |

See gate criteria: [tasks.md](tasks.md)

---

## Open Questions / Deferred Decisions

<Bullet list of unresolved questions or decisions deferred to a later phase. If none, write "— none identified". Each bullet should name the deferred phase if known.>

- <Question or deferred item — deferred to Phase N>

---

## What Went Well

<Exactly 3 bullets. Concrete observations, not generic praise.>

- 
- 
- 

---

## What Could Be Improved

<Exactly 3 bullets. Actionable, specific. Reference task IDs or finding IDs where applicable.>

- 
- 
- 
```

## Extraction rules (all sections from conversation history only)

- **Feature Summary**: derive from the stated goal of the work, what was built, and why it matters in context of the phase. Prose only — no bullets.
- **Architecture**: extract from design discussions, ADR references, AgentState / schema changes confirmed in the conversation.
- **Design**: extract from file paths mentioned, library versions pinned, Settings fields introduced. File references must be repo-absolute paths (`backend/src/graph/state.py:64`), not module names.
- **Phase Gate Evidence**: extract from any DoD command output shown in the conversation. If a command was not run or its output not shown, mark it `⚠️ not confirmed`.
- **Open Questions**: extract from any "deferred to Phase N", "out of scope", "TODO", or unresolved discussion threads in the conversation.
- **What Went Well / Could Be Improved**: synthesise from friction points, rework, re-attempts, and approaches that worked cleanly. One sentence per bullet.
