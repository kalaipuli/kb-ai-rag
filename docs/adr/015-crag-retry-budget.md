# ADR-015: CRAG Retry Budget — Counter Ownership, Budget Sharing, and Default Reachability

## Status
Accepted

## Context

The CRAG execution path is: Router → Retriever → Grader → (retry loop) → Generator → Critic → (retry loop).

A single shared field `retry_count: int` in `AgentState` tracks how many retrieval passes have occurred. The grader node increments this counter; the edge functions `route_after_grader` and `route_after_critic` compare it against `settings.graph_max_retries` to decide whether to loop back to the retriever.

**The dead-branch bug.** With the current default `graph_max_retries = 1`:

1. Graph starts: `retry_count = 0`
2. Grader runs: increments → `retry_count = 1`
3. `route_after_grader` checks: `state["retry_count"] < settings.graph_max_retries` → `1 < 1` → `False`
4. Routes immediately to Generator — no retry is ever taken

The grader retry branch is structurally unreachable with the default configuration. The critic retry branch is also unreachable: the critic node does not increment `retry_count`, so after the grader has already pushed the counter to 1 (equalling the limit), the critic edge check `1 < 1` is likewise always `False`.

Additionally, the grader's web-escalation trigger fires when `new_retry_count >= 2` (per ADR-012). With `graph_max_retries = 1` the counter never reaches 2, so escalation is also unreachable by default.

The question this ADR resolves:

- Which node owns the counter increment?
- Is the budget shared between grader and critic retries, or separate?
- What default value makes the grader retry branch reachable out of the box?

## Decision

**Option A — Fix the default value to `graph_max_retries = 2`.**

- The grader node remains the sole incrementor of `retry_count` (no change to node ownership).
- The single `retry_count` field is retained; no new `AgentState` fields are introduced.
- `graph_max_retries` is changed from `1` to `2` in `backend/src/config.py`.
- The edge checks `state["retry_count"] < settings.graph_max_retries` remain unchanged.
- No changes to `state.py` or `edges.py` beyond this default value correction.

**Semantics with `graph_max_retries = 2`:**

| Step | retry_count | Edge check (< 2) | Action |
|------|-------------|-------------------|--------|
| After 1st grader pass | 1 | `1 < 2` → True | Routes back to Retriever (retry) |
| After 2nd grader pass | 2 | `2 < 2` → False | Routes to Generator |

The grader retry branch is now reachable on the first pass. The web-escalation threshold (`new_retry_count >= 2`) aligns exactly with the second grader pass, matching the intended semantics from ADR-012.

**Counter ownership and budget sharing rules:**

- `retry_count` is incremented **only by the grader node**, on every execution (including the first pass).
- Edge functions are pure routing functions: they read `retry_count` and `graph_max_retries` but never write state (per ADR-012).
- The critic retry path shares the same counter and the same budget. This is intentional: the total number of retrieval attempts across both loops is bounded by one tunable value.
- Operators who need independent grader and critic budgets may override `graph_max_retries` via the environment variable `GRAPH_MAX_RETRIES`. Separate counters are not introduced (see Alternatives Considered).

**Summary of exact changes required for T08:**

| File | Change |
|------|--------|
| `backend/src/config.py` | `graph_max_retries: int = 2` |
| `backend/src/graph/state.py` | No change |
| `backend/src/graph/edges.py` | No change |
| `backend/src/graph/nodes/grader.py` | No change |

## Alternatives Considered

**Option B — Separate counters (`grader_retry_count`, `critic_retry_count`).**
Introduces two new `AgentState` fields and two new `Settings` fields (`graph_max_grader_retries`, `graph_max_critic_retries`). Allows independent budget tuning for each loop. Rejected because: (1) it violates the principle of not adding `AgentState` fields without clear necessity; (2) the shared budget is the correct model — total retrieval cost is what operators care about, not which loop consumed it; (3) it doubles configuration surface for a feature that requires only a one-character fix to the default value.

**Option C — Change edge check from `<` to `<=`.**
Keep `graph_max_retries = 1` and change the comparison to `state["retry_count"] <= settings.graph_max_retries`. This is a semantics inversion: `graph_max_retries` would mean "the maximum value `retry_count` may hold before the loop exits" rather than "the number of retries allowed". The field name `graph_max_retries` most naturally reads as a count of retries, not as a ceiling on the counter value. With `graph_max_retries = 1` under Option C, the grader would be allowed one retry (counter goes 1 → 2 on re-entry), but the web-escalation trigger at `new_retry_count >= 2` would fire on the first re-entry, eliminating the vector retry entirely. The semantics are confusing and the escalation alignment breaks. Rejected.

## Consequences

**Easier:**
- The grader retry branch is reachable with the default configuration; CRAG tests can exercise it without overriding settings.
- The web-escalation trigger at `new_retry_count >= 2` fires on the intended second grader pass.
- No `AgentState` schema change is required, keeping ADR-011 and the reducer contract stable.
- A single `GRAPH_MAX_RETRIES` env var controls total retrieval budget for both loops.

**Harder / different:**
- The shared budget means a critic-triggered retry consumes from the same pool as a grader retry. Operators who need strict per-loop limits must implement Option B in a future ADR.
- `graph_max_retries = 2` means up to three grader passes are possible (pass 0 at `retry_count=0` pre-increment, pass 1 at `retry_count=1`, pass 2 exits). Implementors must read the counter as "number of completed grader passes" not "number of retries remaining".
