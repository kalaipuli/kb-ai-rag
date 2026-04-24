# Anti-Patterns — What Not To Do

Quick reference of prohibited patterns and their correct alternatives. Check this when in doubt about an approach.

| Don't | Do instead |
|-------|-----------|
| Use `print()` for debugging | `structlog` with structured key-value events |
| Skip type annotations | Annotate everything; `mypy --strict` must pass |
| Put secrets in source code | `src/config.py` + `.env` locally / Azure Key Vault in prod |
| Type a secret field as `str` in `Settings` | Use `pydantic.SecretStr`; unwrap with `.get_secret_value()` only at the SDK call site |
| Pass `SecretStr` to a third-party client without `.get_secret_value()` | Call `.get_secret_value()` in-line at the constructor argument |
| Call sync file I/O or CPU-bound libs inside `async def` | Wrap with `asyncio.to_thread(...)`; use `AsyncQdrantClient` not `QdrantClient` |
| Use bare `_field: Type` annotation on a `BaseModel` private attribute | Declare `_field: Type = PrivateAttr(default=...)` |
| Access `obj._private_attr` on a foreign object | Add a public method to that class instead |
| Define a new Pydantic model without grepping for an existing one | `grep -rn "class <TypeName>" backend/src/` before creating any model |
| Re-declare a shared type in `generation/`, `retrieval/`, or `ingestion/` | Import from `backend/src/api/schemas.py` (see ADR-008) |
| Use `RetrievalQA`, `LLMChain`, or `StuffDocumentsChain` | Use LCEL (`prompt \| llm \| parser`) — these are deprecated in LangChain 0.3 |
| Create a new client inside a route handler or health endpoint | Use the lifespan singleton via a `Dep` alias from `backend/src/api/deps.py` |
| Use `Depends(get_settings)` inline in a route with `# noqa: B008` | Import `SettingsDep` from `src.api.deps` |
| Write tests that only cover the happy path | Add at least one error-path test per external call (Azure, Qdrant, disk) |
| Mark a task ✅ Done before running the DoD command gates | Run all DoD commands in §7 of development-process.md; paste results before closing |
| Add a `# noqa` or `# type: ignore` without an inline justification comment | Fix the underlying issue; suppressors require an explanation on the same line |
| Store `__init__` parameters that no method ever reads | Remove the parameter; do not write orphaned code |
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
