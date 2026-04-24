# Stack Upgrade Proposal

> **Status:** Accepted — 2026-04-24
> **Reviewed by:** Architect · Backend Developer · Frontend Developer agents
> **Applies to:** All phases. Actions are time-gated — each tier is a prerequisite for the phase it precedes.

This document captures every version update, deprecated-API fix, and implementation pattern change identified during the April 2026 stack review. Items are organized by **when they must be done**, not by package. Nothing here is optional — each tier is a gate condition for the phase that follows it.

---

## Quick Reference

| Tier | Do When | Key Actions |
|------|---------|-------------|
| [Tier 1](#tier-1--before-phase-1d-starts) | Before Phase 1d starts | 4 immediate fixes to pyproject.toml + chain.py |
| [Tier 2](#tier-2--phase-1d-implementation-patterns) | During Phase 1d | FastAPI patterns for all new endpoint code |
| [Tier 3](#tier-3--phase-2-pre-requisites-gate-zero) | Phase 2 gate zero | LangGraph version lock + AgentState schema |
| [Tier 4](#tier-4--frontend-before-any-component-code) | Before first frontend component | Next.js 15 + React 19 + Tailwind 4 bundle |
| [Hold](#hold--do-not-upgrade-yet) | Future phases | RAGAS isolation (Ph 5), Python 3.13 (Ph 4) |

---

## Tier 1 — Before Phase 1d Starts

These four changes take under an hour combined. Two are runtime-breaking if left until after Phase 1d adds more code on top of them.

### T1-1: Fix pytest-asyncio mode (breaking in 0.25)

**File:** `backend/pyproject.toml`

`asyncio_mode = "auto"` is deprecated in pytest-asyncio 0.24 and **removed** in 0.25. Tests without an explicit `@pytest.mark.asyncio` marker will silently pass without executing any `await` calls under strict mode — a silent correctness failure, not a loud test failure.

**Change:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
addopts = "-q --tb=short"
```

**Also required:** Add `pytestmark = pytest.mark.asyncio` at module level in every test file that contains async tests. Async fixtures must use `@pytest_asyncio.fixture` (from `import pytest_asyncio`) instead of `@pytest.fixture`. The existing `conftest.py` uses only sync fixtures — no change needed there.

**Why now:** Doing this before Phase 1d ensures all 142 existing tests are verified under strict mode before any new async tests are added.

---

### T1-2: Unwrap SecretStr before passing to AzureChatOpenAI

**File:** `backend/src/generation/chain.py`

`langchain-openai ^0.2.9+` passes the `api_key` argument directly to the underlying `openai.AzureOpenAI` client, which expects `str | None`. Passing a Pydantic `SecretStr` object triggers a validation error in some patch versions.

**Change:**
```python
# Before
api_key=settings.azure_openai_api_key,

# After
api_key=settings.azure_openai_api_key.get_secret_value(),
```

This is a one-line fix but is silent in the current installed version and will surface as an auth failure on the next `langchain-openai` patch upgrade.

---

### T1-3: Bump qdrant-client to ^1.12

**File:** `backend/pyproject.toml`

qdrant-client 1.12 introduces the `query_points` API as the unified replacement for `client.search`. The old `search` method is soft-deprecated in 1.12 (hard removal planned for 2.0). Migration is confined entirely to `backend/src/retrieval/dense.py`.

**Change in pyproject.toml:**
```toml
qdrant-client = "^1.12"
```

**Follow-up in dense.py:** After bumping, replace `client.search(...)` with `client.query_points(...)`. Verify the `# type: ignore[attr-defined]` comment on that call still suppresses the correct mypy error code (if it changes from `attr-defined` to `no-untyped-call` after the bump, update the comment to match or add a stub).

**Also note:** qdrant-client 1.12 changes the default `close()` timeout from `None` to `5.0s`. No code change needed, but if test teardown becomes flaky, mock `close` with `AsyncMock` in the affected test.

---

### T1-4: Replace `_aget_relevant_documents` with the public method

**File:** `backend/src/generation/chain.py`

The project calls `await kb_retriever._aget_relevant_documents(query, run_manager=...)` directly (underscore = internal method). In `langchain-core 0.3.20+`, this method's signature is changing for streaming retriever support. The public wrapper `aget_relevant_documents` is the stable contract.

**Change:**
```python
# Before
docs = await kb_retriever._aget_relevant_documents(query, run_manager=noop)

# After
docs = await kb_retriever.aget_relevant_documents(query)
```

The public method handles callbacks and metadata automatically; the explicit `run_manager` argument is no longer needed.

---

## Tier 2 — Phase 1d Implementation Patterns

These are not version upgrades but architectural patterns that all Phase 1d endpoint code must follow. They replace the ad-hoc patterns currently in `health.py`.

### T2-1: Lifespan state for singleton services

Do **not** construct `Embedder`, `HybridRetriever`, or `GenerationChain` inside route handlers or with `lru_cache + Depends` (the cache key is not hashable). Use FastAPI's lifespan to build singletons once and expose them via `app.state`:

```python
# backend/src/api/main.py
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    bm25_store = BM25Store(index_path=Path(settings.bm25_index_path))
    if Path(settings.bm25_index_path).exists():
        bm25_store.load()
    embedder = Embedder(settings=settings)
    retriever = HybridRetriever(settings=settings, bm25_store=bm25_store, embedder=embedder)
    app.state.generation_chain = GenerationChain(settings=settings, hybrid_retriever=retriever)
    app.state.bm25_store = bm25_store
    yield
    await retriever.close()
```

Dependency functions then pull from state:
```python
def get_generation_chain(request: Request) -> GenerationChain:
    return request.app.state.generation_chain  # type: ignore[no-any-return]
```

### T2-2: Annotated dependency injection (eliminates noqa comments)

Use `Annotated` instead of `= Depends(...)` default values. The current `health.py` uses the old form with `# noqa: B008`. All Phase 1d routes must use the new form:

```python
from typing import Annotated
from fastapi import Depends

SettingsDep = Annotated[Settings, Depends(get_settings)]
GenerationChainDep = Annotated[GenerationChain, Depends(get_generation_chain)]

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(body: QueryRequest, chain: GenerationChainDep) -> QueryResponse:
    ...
```

### T2-3: BackgroundTasks for POST /api/v1/ingest

`run_pipeline` is a long-running async coroutine. Return `202 Accepted` immediately:

```python
@router.post("/ingest", status_code=202)
async def ingest_endpoint(
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
) -> IngestAcceptedResponse:
    background_tasks.add_task(run_pipeline, Path(settings.data_dir), settings)
    return IngestAcceptedResponse(status="accepted", message="Ingestion started")
```

FastAPI 0.115 runs async `BackgroundTasks` in the same event loop after the response is sent — correct for a fully async pipeline.

### T2-4: StreamingResponse for POST /api/v1/query (if streaming)

If Phase 1d query returns tokens incrementally (SSE):

```python
from fastapi.responses import StreamingResponse

async def _token_stream(query: str, chain: GenerationChain) -> AsyncIterator[str]:
    async for chunk in chain._llm.astream(query):
        yield f"data: {chunk.content}\n\n"
    yield "data: [DONE]\n\n"

@router.post("/query/stream")
async def query_stream(body: QueryRequest, chain: GenerationChainDep) -> StreamingResponse:
    return StreamingResponse(_token_stream(body.query, chain), media_type="text/event-stream")
```

If Phase 1d only needs a synchronous JSON response, use `chain.ainvoke` with `response_model=QueryResponse` and no streaming.

### T2-5: Audit and remove unused direct dependencies

Before Phase 1d: check whether any import in `backend/src/` references `langchain_community`. If not, remove `langchain-community` as a direct dependency — it is the highest-churn sub-package in the ecosystem and adds solver noise. The `langchain` meta-package (the thin shim) can similarly be removed if all actual imports are from `langchain_core` and `langchain_openai`.

```bash
grep -r "from langchain_community" backend/src/
grep -r "from langchain " backend/src/
```

---

## Tier 3 — Phase 2 Pre-requisites (Gate Zero)

**None of these are optional.** Phase 2 cannot start until all five are done. The LangGraph version lock in particular is a hard prerequisite — writing agent nodes against an unconfirmed API surface will cause breakage mid-phase.

### T3-1: Lock LangGraph to an exact confirmed version

**Do not use `langgraph = "^0.2"`** for Phase 2 work. The `^` range allows minor-version upgrades that can change the `StateGraph` API, checkpointer import paths, and node return semantics.

Procedure:
1. Install the current stable LangGraph release.
2. Confirm that `StateGraph`, `add_node`, `add_conditional_edges`, `compile`, and `SqliteSaver.from_conn_string` all exist with the expected signatures.
3. Pin to a tilde range: `langgraph = "~1.0.x"` (or whatever the confirmed version is).
4. Upgrade `langchain`, `langchain-openai`, `langchain-core`, and `langgraph` **together in one PR** — they share a `langchain-core` transitive dependency and must resolve compatibly.

```toml
# Target — exact major.minor, not a caret range
langgraph = "~1.0.0"   # replace with confirmed version
```

### T3-2: Write ADR-004 amendment

Before the first agent node: update `docs/adr/004-langgraph-vs-chain.md` with:
- Confirmed version number
- Confirmed `SqliteSaver` import path (may have moved to `langgraph.checkpoint.sqlite` or a separate `langgraph-checkpoint-sqlite` package)
- Confirmed `MessagesState` base class name if used
- Any API surface differences from the 0.2.x documentation

### T3-3: Define AgentState schema before any node code

The `AgentState` TypedDict in `backend/src/graph/state.py` is the Phase 2 interface contract. It must be written and reviewed before any agent node function is implemented. Once defined, no node may extend or modify it without architectural review.

Pattern — use `Annotated` reducers for accumulated fields:

```python
from typing import Annotated, TypedDict, Literal
from langgraph.graph.message import add_messages
from langchain_core.documents import Document

class AgentState(TypedDict):
    # Accumulated fields — use Annotated reducer, never overwrite
    messages: Annotated[list[BaseMessage], add_messages]
    retrieved_docs: Annotated[list[Document], operator.add]
    steps_taken: Annotated[list[str], operator.add]
    # Overwritten fields — plain type, one node is responsible
    session_id: str
    query: str
    query_rewritten: str | None
    query_type: Literal["factual", "analytical", "multi_hop", "ambiguous"]
    retrieval_strategy: Literal["dense", "hybrid", "web"]
    graded_docs: list[Document]
    answer: str | None
    citations: list[Citation]
    confidence: float
    hallucination_risk: float
    fallback_triggered: bool
    user_id: str
```

Nodes must return **partial dicts** (only the keys they update), not the full state:
```python
# Correct
async def router_node(state: AgentState) -> dict[str, object]:
    return {"query_type": "factual", "retrieval_strategy": "hybrid"}

# Wrong — returning full state causes merge errors in LangGraph 0.3+
async def router_node(state: AgentState) -> AgentState:
    state["query_type"] = "factual"
    return state
```

### T3-4: Confirm SqliteSaver import path

The `SqliteSaver` import path changed between LangGraph 0.1 and 0.2, and may change again in 1.x (potentially moving to a separate `langgraph-checkpoint-sqlite` installable package). Confirm the import path for the locked version before writing any graph compilation code:

```python
# Verify this works for the locked version
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string(":memory:") as checkpointer:
    graph = workflow.compile(checkpointer=checkpointer)
```

If it has moved to a separate package, add `langgraph-checkpoint-sqlite` to `pyproject.toml` and update ADR-004.

### T3-5: Wrap GenerationChain in Generator node (no rewrite needed)

The existing `GenerationChain.generate()` becomes the implementation body of the Generator agent node. No rewrite is needed — wrap it:

```python
async def generator_node(state: AgentState, config: RunnableConfig) -> dict[str, object]:
    result = await generation_chain.generate(
        query=state["query"],
        docs=state["graded_docs"],
        config=config,   # forward LangGraph's RunnableConfig (includes callbacks/tracers)
    )
    return {"answer": result.answer, "citations": result.citations, "confidence": result.confidence}
```

Pass `config` through rather than constructing a noop `AsyncCallbackManagerForRetrieverRun` — LangGraph's graph-level tracer is carried in `config.callbacks`.

---

## Tier 4 — Frontend: Before Any Component Code

The frontend has zero production code written. Every breaking change in Next.js 15, React 19, and Tailwind 4 costs nothing to adopt from scratch. Upgrading after even a few components exist is significantly more expensive.

**Upgrade all five items together in a single `npm install` pass** before writing any component.

### Frontend package.json targets

| Package | Current | Target | Change |
|---------|---------|--------|--------|
| `next` | 14.2.18 | 15.3.x (pin exact) | Async Request APIs, React 19 peer dep, `fetch` no-store default |
| `react` / `react-dom` | ^18.3.1 | ^19.1.0 | `useOptimistic` for chat UI, `forwardRef` no longer required |
| `@types/react` / `@types/react-dom` | ^18.x | ^19.x | Must match React major version |
| `tailwindcss` | ^3.4.14 | ^4.1.x | CSS-first config, automatic content detection |
| `@tailwindcss/postcss` | — | ^4.1.x | **Add** — replaces old PostCSS plugin entry |
| `autoprefixer` | ^10.4.20 | **Remove** | Tailwind 4 handles vendor prefixes internally |
| `eslint` | ^8.57.1 | ^9.x | Flat config (`eslint.config.mjs`) |
| `eslint-config-next` | 14.2.18 | 15.3.x | Must match `next` version; ships native flat config |
| `typescript` | ^5.6.3 | ^5.8.x | Stricter narrowing for streaming state variables |
| `@types/node` | ^20.16.11 | Keep ^20 | Must match Dockerfile `node:20-alpine` |
| `lucide-react` | ^0.460.0 | Keep | `^` resolves to current 0.5xx; React 19 compat at 0.469+ |
| `@tanstack/react-query` | ^5.59.0 | Keep | `^` resolves to current; no breaking changes in 5.x |

### Tailwind 4 config migration

`tailwind.config.ts` is replaced by a CSS `@theme` block. The existing config (two colour tokens, standard content paths) becomes:

```css
/* frontend/src/app/globals.css */
@import "tailwindcss";

@theme {
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));
}
```

`postcss.config.mjs` changes from:
```js
{ plugins: { tailwindcss: {}, autoprefixer: {} } }
```
to:
```js
{ plugins: { "@tailwindcss/postcss": {} } }
```

Content detection is automatic in v4 — no `content` array.

### React 19 patterns for the chat UI

- **`useOptimistic`**: Append the user's message to the conversation list immediately on submit, before the SSE stream starts. Removes perceived lag.
- **Ref as prop**: `forwardRef` wrapper is no longer needed on components that accept a `ref`. Pass `ref` directly.
- **Testing**: `act` moves from `react-dom/test-utils` to `react-dom`. Update any test imports accordingly.

### ESLint 9 flat config

Delete `.eslintrc.json`. Create `eslint.config.mjs`:
```js
import { FlatCompat } from "@eslint/eslintrc";
// eslint-config-next 15.x ships a native flat config export
import nextConfig from "eslint-config-next/flat";

export default [...nextConfig];
```

### SSE streaming pattern (confirmed)

The `POST /api/v1/query` endpoint cannot use `EventSource` (POST-only). The confirmed pattern:

**`src/lib/streaming.ts`** — pure async generator, no React:
```typescript
export async function* streamQuery(
  payload: QueryRequest,
): AsyncGenerator<StreamEvent> {
  const response = await fetch("/api/v1/query/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": getApiKey() },
    body: JSON.stringify(payload),
  });
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  // parse SSE lines, yield typed StreamEvent discriminated union
}
```

**`useStream` hook** — React state bridge, drives the generator:
```typescript
export function useStream() {
  const [tokens, setTokens] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const mutation = useMutation({ mutationFn: initiateStream });
  // onSuccess: consume the async generator, accumulate state
}
```

Do **not** use `EventSource`, `@microsoft/fetch-event-source`, or `experimental_streamedQuery`. The `fetch` + `ReadableStream` pattern is the correct, dependency-free approach as confirmed in ADR-005.

---

## Hold — Do Not Upgrade Yet

| Item | Current | Upgrade When | Reason to Wait |
|------|---------|-------------|----------------|
| **RAGAS** `^0.2` | 0.2.x | Before Phase 5 starts | Isolate into `[tool.poetry.group.eval.dependencies]` at Phase 5 design — keeps it out of the API runtime's solver and prevents transitive conflicts with `langchain-core` |
| **Python** `^3.12` | 3.12.x | Phase 4 evaluation | `sentence-transformers → torch` wheel chain for 3.13 needs re-validation; no 3.13-specific features needed through Phase 3 |
| **FastAPI** `^0.115` | 0.115.x | No action needed | Already the correct version for Phase 1d; SSE, BackgroundTasks, lifespan all present |
| **Pydantic** `^2.9` | 2.9.x | No action needed | PrivateAttr migration complete; patterns are correct for 2.9–2.11 |
| **LangChain** `^0.3` | 0.3.x | Bundle with LangGraph at Phase 2 gate zero | Upgrade langchain, langchain-openai, langchain-core, langgraph together — they share transitive deps |
| **RAGAS solver isolation** | direct dep | Before Phase 5 | `ragas ^0.2` may conflict with a future `langchain-core` version; move it to an eval group before that conflict surface |
| `httpx[asyncio]` extra | unnecessary | Opportunistic | The `[asyncio]` extra has been built-in since httpx 0.20; remove during any routine `pyproject.toml` edit |

---

## Backend Version Matrix (Full)

| Package | Pinned | Status | Next Action |
|---------|--------|--------|-------------|
| python | ^3.12 | Current | Hold through Phase 2 |
| fastapi | ^0.115 | Current | No action |
| uvicorn | ^0.32 | Current | No action |
| pydantic | ^2.9 | Current | No action |
| pydantic-settings | ^2.6 | Current | No action |
| structlog | ^24.4 | Current | No action |
| langchain | ^0.3 | Shim only | Audit imports; remove if unused |
| langchain-openai | ^0.2 | Current | Bundle-upgrade at Ph 2 gate |
| langchain-community | ^0.3 | Audit needed | Remove if no `langchain_community` imports |
| langgraph | ^0.2 | Outdated | Lock to exact `~1.0.x` at Ph 2 gate zero |
| qdrant-client | ^1.11 | Bump needed | → `^1.12` in Tier 1 |
| rank-bm25 | ^0.2 | Current | No action |
| sentence-transformers | ^3.3 | Current | No action |
| pypdf | ^5.1 | Current | No action |
| azure-identity | ^1.17 | Current | No action |
| azure-keyvault-secrets | ^4.8 | Current | No action |
| azure-storage-blob | ^12.23 | Current | No action |
| tavily-python | ^0.5 | Current | Verify API compat at Phase 2 |
| tenacity | ^9.0 | Current | No action |
| ragas | ^0.2 | Isolated at Ph 5 | Move to eval group before Phase 5 |
| httpx | ^0.27 | Current | Remove `[asyncio]` extra opportunistically |
| pytest | ^8.3 | Current | No action |
| pytest-asyncio | ^0.24 | Fix now | Change to `strict` mode (Tier 1) |
| pytest-cov | ^6.0 | Current | No action |
| pytest-mock | ^3.14 | Current | No action |
| mypy | ^1.13 | Current | After qdrant bump: re-verify `type: ignore` comment |
| ruff | ^0.8 | Current | No action; current `select` list is safe on 0.9+ |

---

## Frontend Version Matrix (Full)

| Package | Pinned | Status | Next Action |
|---------|--------|--------|-------------|
| next | 14.2.18 | Outdated | → 15.3.x in Tier 4 |
| react / react-dom | ^18.3.1 | Outdated | → ^19.1.0 in Tier 4 |
| @types/react / @types/react-dom | ^18.x | Outdated | → ^19.x in Tier 4 |
| tailwindcss | ^3.4.14 | Outdated | → ^4.1.x in Tier 4; rewrite config |
| @tailwindcss/postcss | — | Missing | Add ^4.1.x in Tier 4 |
| autoprefixer | ^10.4.20 | Remove | Delete in Tier 4 |
| eslint | ^8.57.1 | Outdated | → ^9.x in Tier 4 (pair with Next.js 15) |
| eslint-config-next | 14.2.18 | Outdated | → 15.3.x in Tier 4 |
| typescript | ^5.6.3 | Current | Pin to `^5.8.x` explicitly in Tier 4 |
| @types/node | ^20.16.11 | Current | Keep — matches Dockerfile node:20-alpine |
| lucide-react | ^0.460.0 | Current | `^` resolves to 0.5xx with React 19 compat |
| @tanstack/react-query | ^5.59.0 | Current | No action |
| clsx | ^2.1.1 | Current | No action |
| tailwind-merge | ^2.5.4 | Current | Verify Tailwind 4 compat at Tier 4 time |
| postcss | ^8.4.47 | Current | Keep (required by @tailwindcss/postcss) |
