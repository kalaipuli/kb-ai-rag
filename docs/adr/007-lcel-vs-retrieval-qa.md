# ADR-007: LCEL over RetrievalQA for the Generation Chain

## Status
Accepted

## Context
The current generation layer (`backend/src/generation/chain.py`) uses `RetrievalQA.from_chain_type` from `langchain`. In LangChain 0.3, `RetrievalQA` is a legacy abstraction that emits `LangChainDeprecationWarning` at runtime and is scheduled for removal in LangChain 0.4. The project pins `langchain = "^0.3"` and `langchain-openai = "^0.2"`, so the deprecation is active today.

Beyond the deprecation, `RetrievalQA` introduces several structural problems for this codebase:

1. **Implicit variable mapping.** `RetrievalQA` maps the chain's input key (`"query"`) to the prompt variable `{question}` via an undocumented internal convention. If the prompt template changes its variable name, the mapping breaks silently at runtime rather than failing at construction time.

2. **Type erasure.** `RetrievalQA.from_chain_type` returns `Chain`, forcing the declaration `chain: Any` to suppress mypy. This removes static safety from the most critical call path in the system.

3. **Side-channel for source documents.** Retrieved documents are only accessible after the call via `result["source_documents"]`. The `KBRetriever._last_results` private attribute exists solely as a second side-channel to recover `RetrievalResult` objects for confidence scoring. This is a symptom of the abstraction's opacity.

4. **Incompatibility with Phase 2 LangGraph agents.** LangGraph nodes are plain async functions that receive and return `AgentState`. The Phase 2 `GeneratorAgent` node must accept pre-retrieved and graded documents from state rather than triggering its own retrieval. `RetrievalQA` couples retrieval and generation into a single opaque unit, making it unsuitable as a LangGraph node.

The context window is not a constraint in Phase 1: with `reranker_top_k=5` and `chunk_size=1000` characters, the maximum context payload is approximately 5 KB — well within GPT-4o's 128 K token window. The simpler `chain_type="stuff"` strategy (concatenate all chunks, pass once) is correct and sufficient. `map_reduce` and `refine` strategies would add latency and token cost with no quality benefit at this context size. If `top_k` increases significantly in a future phase, this trade-off must be revisited.

## Decision
Replace `RetrievalQA` with an explicit LCEL pipeline for the generation layer.

The LCEL composition is:

```python
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

chain = (
    RunnablePassthrough.assign(
        context=RunnableLambda(_format_docs),
        source_documents=RunnableLambda(_retrieve_docs),
    )
    | QA_PROMPT
    | llm
    | StrOutputParser()
)
```

Retrieved documents flow explicitly through the chain as a named key (`source_documents`). The `_last_results` side-channel on `KBRetriever` is eliminated. Variable names in the LCEL pipeline match the prompt template variables exactly, making mismatches a construction-time error. The return type of the chain is `str`, which mypy resolves without suppression.

For Phase 2, the `GeneratorAgent` node will accept a `list[Document]` from `AgentState.graded_docs` and invoke only the `prompt | llm | parser` portion of the chain, bypassing the retriever step entirely. LCEL's composable structure makes this split natural; `RetrievalQA` makes it impossible.

## Alternatives Considered

**Keep `RetrievalQA` with a suppression comment.** Rejected. The deprecation warning is not cosmetic — it signals that the abstraction will be removed. Suppressing warnings does not eliminate the coupling problems or the `_last_results` side-channel. It defers the migration cost to a point where LangChain 0.4 forces it under time pressure.

**Replace with a fully manual pipeline (no LangChain).** Rejected. The project already depends on `langchain-openai` for `AzureChatOpenAI` and `AzureOpenAIEmbeddings`. LCEL is the idiomatic composition layer in LangChain 0.3+ and does not add a new dependency. A hand-rolled pipeline would duplicate functionality already provided and would diverge from the patterns used in Phase 2 LangGraph nodes.

**Use `create_retrieval_chain` (LangChain 0.3 recommended replacement).** Evaluated. `create_retrieval_chain` is the officially suggested migration target from the LangChain docs. It is however still a higher-level wrapper that constrains the input/output key names. For this project, where the same prompt template must be reused by Phase 2 LangGraph nodes without a retriever attached, the lower-level LCEL composition gives more explicit control and better Phase 2 alignment. `create_retrieval_chain` is not rejected outright for general use but is not the right fit here.

## Consequences

**Positive:**
- Eliminates `LangChainDeprecationWarning` from the runtime logs
- `chain: Any` annotation and its associated mypy suppression are removed
- `KBRetriever._last_results` side-channel is eliminated; confidence scoring reads scores from the document metadata dict directly, keeping all data in the explicit data flow
- Prompt variable names are validated at chain construction time, not at first invocation
- The retriever step and the generation step are independently composable, which directly enables the Phase 2 `GeneratorAgent` node pattern where pre-graded documents are injected from `AgentState` without re-retrieval
- `chain_type="stuff"` remains the correct strategy for Phase 1 context sizes and is now expressed explicitly in the pipeline rather than as a string argument to a factory method

**Negative:**
- Requires rewriting `chain.py` and its unit tests; estimated scope is contained within `backend/src/generation/`
- LCEL's `RunnablePassthrough.assign` pattern is less immediately readable to developers unfamiliar with LangChain 0.3+ idioms; this is mitigated by inline comments in the implementation

---

## Schema Ownership

### Context
`generation/models.py` defines `Citation` and `GenerationResult`. `api/schemas.py` defines `CitationItem` and `QueryResponse` with identical fields. Any field change requires two edits in two files, and the names diverge (`Citation` vs `CitationItem`) without a documented reason. This duplication was introduced because the generation layer and the API layer were built independently; it was not a deliberate design choice.

Three options were considered:

- **Option A — `api/schemas.py` imports from `generation/models.py`:** The API layer importing from the domain layer is an unconventional dependency direction and couples the API contract to internal generation model names.
- **Option B — `generation/chain.py` imports from `api/schemas.py`:** The domain layer importing from the presentation layer is a layering violation. The generation module must not depend on the API module.
- **Option C — shared `src/schemas/` module:** Both layers import from a neutral module that has no dependency on either. This is the standard solution to cross-layer type sharing.

### Decision
Adopt **Option C**. Create `backend/src/schemas/generation.py` as the single canonical location for the shared types.

Module layout:
```
backend/src/schemas/__init__.py        # empty, marks the package
backend/src/schemas/generation.py     # Citation, GenerationResult
```

`Citation` is the canonical name (not `CitationItem` — the `Item` suffix was an API-layer convention applied incorrectly to a domain type). `GenerationResult` is unchanged.

Import contracts after the migration:
- `api/schemas.py` imports `Citation` from `src.schemas.generation` and re-exports it as `CitationItem` for backward API compatibility, or renames directly if no external consumer has been pinned to the `CitationItem` name.
- `api/schemas.py` imports `GenerationResult` from `src.schemas.generation` and uses it as the basis for `QueryResponse`, or exposes it directly.
- `generation/chain.py` imports `Citation` and `GenerationResult` from `src.schemas.generation`.
- `generation/models.py` is deleted once imports are migrated.

### Consequences
- Single definition of each type; field changes are made in one file
- `src/schemas/` has no dependency on `src/api/` or `src/generation/`, so it can be imported by Phase 2 LangGraph agent nodes without introducing circular imports
- `AgentState.citations` (defined in `architecture-rules.md`) references `Citation` by name; after this migration it will import from `src.schemas.generation`, which is the correct source
