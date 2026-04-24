# Agent Conduct

Rules for how the AI agent operates during every session. These apply unconditionally to every request.

## No End-of-Response Summaries
Do not append a summary paragraph at the end of a response. The work product speaks for itself — narrating what was just done adds noise. Only state what changed if it is not already visible from the tool output or diff.

## Read Only What the Task Requires
Do not pre-emptively open files that are not needed for the current task. Open a file only when its content is directly required to complete the step in hand. Reading speculatively wastes context and slows down the session.

## Use Tools Efficiently
- Prefer `grep` / `find` over reading full files when the goal is to locate a symbol or pattern.
- Run independent tool calls in parallel in a single message rather than sequentially.
- Do not re-read a file immediately after editing it — the edit either succeeded or errored.
- Use the `Explore` sub-agent for broad codebase searches that would otherwise take more than three direct queries.

## Sub-Agents Utilization
- Before acting, outline a minimal plan or task list when the problem involves multiple steps.
- Delegate clearly scoped tasks to appropriate sub-agents when beneficial.
- Avoid over-delegation: use sub-agents only when they provide clear efficiency or separation of concerns.
- Validate and consolidate sub-agent outputs before responding.
- Track progress toward task completion and ensure no steps are left unfinished.

## Plugins Usage
- Treat plugins as structured capability extensions (commands, skills, sub-agents, hooks, MCP integrations), not generic tools.
- Do not assume plugins are available — only use them if they are explicitly installed and relevant to the task.
- Prefer explicit invocation (e.g., slash commands) when deterministic behavior is required.
- Allow implicit use of plugin-provided skills or agents only when clearly beneficial and aligned with the task.
- Avoid unnecessary plugin usage — prefer built-in tools or local `.claude/` configuration for simple or one-off tasks.
- Use plugins primarily for reusable, multi-step, or team-standardized workflows.
- Be aware of scope (user/project/local) and avoid relying on plugins that may not exist across environments.

## Task Execution Attempts
- Limit yourself to a maximum of three attempts when trying to complete a single task (e.g., running a command with different options).
- If those attempts fail, step back and reassess the root cause before proceeding. Clearly outline the next steps based on your analysis.
- If the root cause remains unclear or no viable options are left, consult the user for guidance.
