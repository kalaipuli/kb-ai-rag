# Anti-Patterns — What Not To Do

Quick reference of prohibited patterns and their correct alternatives. Check this when in doubt about an approach.

| Don't | Do instead |
|-------|-----------|
| Use `print()` for debugging | `structlog` with structured key-value events |
| Skip type annotations | Annotate everything; `mypy --strict` must pass |
| Put secrets in source code | `src/config.py` + `.env` locally / Azure Key Vault in prod |
| Hardcode domain names in routing | Metadata filters + Router agent intent classification |
| Add RAG logic to API route handlers | Keep routes thin; logic in `src/retrieval/` or `src/graph/` |
| Write agents before Phase 1 gates pass | Follow the phase gate order — no skipping ahead |
| Create a new abstraction for < 3 use cases | YAGNI — only abstract when the third case arrives |
| Use `any` in TypeScript | Define proper types in `src/types/index.ts` |
| Commit untested code to `main` | All tests pass before merge; CI must be green |
| Skip the ADR when making an architectural choice | Write the ADR in the same PR as the change |
| Modify an existing `BaseLoader` to add a new source | Create a new file implementing the ABC |
| Upsert a vector without a payload | Every chunk carries the full `ChunkMetadata` |
| Use `time.sleep()` | Use `asyncio.sleep()` |
| Return values directly between LangGraph agents | Write to `AgentState`; agents read from state only |
| Mix refactor and feature work in one commit | One logical change per commit |
