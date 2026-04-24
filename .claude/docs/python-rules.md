# Python Code Rules

Applies to every `.py` file in `backend/`. All rules are enforced by mypy (strict) and ruff before any commit.

## Types — no exceptions
- Every function has a return type annotation
- Every parameter has a type annotation
- `mypy --strict` must pass before any commit
- Use `TypedDict` for LangGraph `AgentState`
- Use `Pydantic BaseModel` for all API request/response schemas and config

```python
# Correct
async def embed_texts(texts: list[str]) -> list[list[float]]:
    ...

# Wrong — missing annotations
async def embed_texts(texts):
    ...
```

## Async
- All I/O operations are `async` — Qdrant calls, Azure OpenAI calls, file reads
- Never use `time.sleep()` — use `asyncio.sleep()`
- Use `asyncio.gather()` for concurrent fan-out (e.g., multi-hop sub-retrieval)
- FastAPI route handlers are `async def`

## Logging — structlog only
- Never use `print()` or `logging.info()` directly
- Use `structlog.get_logger(__name__)` in every module
- Every log event is a structured key-value dict, never a formatted string

```python
# Correct
logger.info("retrieval_complete", chunk_count=len(docs), duration_ms=elapsed)

# Wrong
logger.info(f"Retrieved {len(docs)} chunks in {elapsed}ms")
```

## Error Handling
- Raise domain-specific exceptions (define in `src/exceptions.py`), not bare `Exception`
- Never silently swallow exceptions — at minimum log and re-raise
- FastAPI exception handlers translate domain exceptions to HTTP responses
- Circuit breaker pattern on all Azure OpenAI calls (Phase 6); until then, use `tenacity` retry

## No Hardcoded Values
- All configuration lives in `src/config.py` via `pydantic-settings`
- All secrets come from environment variables (`.env` locally, Azure Key Vault in prod)
- No API keys, endpoints, or model names in source code

## Imports
- Absolute imports only: `from src.retrieval.hybrid import reciprocal_rank_fusion`
- No wildcard imports: never `from module import *`
