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

## Secrets — `SecretStr` boundary rule
- Every credential field in `Settings` is typed `pydantic.SecretStr`, not `str`
- Unwrap with `.get_secret_value()` **only at the single line** where it is passed to a third-party client constructor — never earlier, never assigned to an intermediate `str` variable
- Never log a `SecretStr` field; never include it in `model_dump()` output
- Any `# type: ignore` comment that would be removed by using `SecretStr` correctly is itself a rule violation

```python
# Correct — unwrap only at the injection boundary
AzureChatOpenAI(api_key=settings.azure_openai_api_key.get_secret_value(), ...)

# Wrong — stores secret as plain str; loses pydantic protection
key = settings.azure_openai_api_key.get_secret_value()
AzureChatOpenAI(api_key=key, ...)
```

## Blocking I/O in async functions
- Every file-read, pickle load, or CPU-bound library call inside an `async def` must use `asyncio.to_thread()`
- Use `AsyncQdrantClient` everywhere Qdrant is accessed from async code — never `QdrantClient`
- Helper methods may remain synchronous; the dispatch from the `async def` caller must be async

```python
# Correct
text = await asyncio.to_thread(lambda: pypdf.PdfReader(path).pages[0].extract_text())

# Wrong — blocks the event loop
text = pypdf.PdfReader(path).pages[0].extract_text()
```

## Pydantic private attributes
- Private fields in a `BaseModel` subclass must use `PrivateAttr(default=...)` — not bare `_field: Type` annotations
- Never access `obj._private` on a foreign object; add a public method to that class instead

```python
# Correct
class KBRetriever(BaseRetriever):
    _retriever: HybridRetriever = PrivateAttr()
    def __init__(self, retriever: HybridRetriever) -> None:
        super().__init__()
        self._retriever = retriever

# Wrong — bare underscore annotation causes ValidationError in Pydantic v2
class KBRetriever(BaseRetriever):
    _retriever: HybridRetriever
```

## No Hardcoded Values
- All configuration lives in `src/config.py` via `pydantic-settings`
- All secrets come from environment variables (`.env` locally, Azure Key Vault in prod)
- No API keys, endpoints, model names, or numeric tuning constants in source code
- After writing any module, review all integer literals ≥ 10 and string literals ≥ 4 chars; each must either be a domain constant in `Settings` or an obvious algorithm value (0, 1, loop index)

## Imports
- Absolute imports only: `from src.retrieval.hybrid import reciprocal_rank_fusion`
- No wildcard imports: never `from module import *`
