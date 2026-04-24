# Architecture Rules

Structural constraints that govern how the system is designed and extended. Read this before any design decision, new module, or cross-cutting change.

## Connector Abstraction — Always
Every data source and retriever implements `BaseLoader` or `BaseRetriever` ABC.
New sources are new files, not modifications to existing ones.

```python
# Adding Azure Blob = new file src/ingestion/loaders/azure_blob_loader.py
# Never = adding blob logic into local_loader.py
```

## Domain-Agnostic Retrieval
- No hard-coded domain routing. The `Router` agent classifies **query intent** (factual, analytical, multi-hop, ambiguous) — not a knowledge domain.
- Metadata fields (`filename`, `file_type`, `tags`, `source_path`) are stored in Qdrant payload and used for **optional filtering** at query time, not mandatory routing.
- Any document from any domain should be retrievable by a well-formed query.

## Document Metadata Schema — Always Complete
Every chunk upserted to Qdrant must carry the full `ChunkMetadata` payload:

```
doc_id, chunk_id, source_path, filename, file_type, title,
page_number, chunk_index, total_chunks, char_count, ingested_at, tags
```

Never upsert a vector without payload. The `domain` field is intentionally absent — see ADR-003.

## Phased Implementation — No Skipping Ahead
Build phases in order. Do not implement Phase 2 agent logic until Phase 1 MVP gates pass:
- RAGAS faithfulness ≥ 0.70
- Full stack runs via `docker compose up`
- All unit tests green

## AgentState is the Single Source of Truth
In Phase 2+, all data flows through `AgentState`. Agents read from state, write to state.
No agent returns a value directly to another agent. No global variables.

```python
class AgentState(TypedDict):
    session_id: str
    query: str
    query_rewritten: str | None
    query_type: Literal["factual", "analytical", "multi_hop", "ambiguous"]
    retrieval_strategy: Literal["dense", "hybrid", "web"]
    retrieved_docs: list[Document]
    graded_docs: list[Document]
    answer: str | None
    citations: list[Citation]
    confidence: float
    hallucination_risk: float
    fallback_triggered: bool
    steps_taken: list[str]
    user_id: str
```

## API Versioning
All routes are prefixed `/api/v1/`. Never change an existing route signature — add a new version instead.

## Streaming — SSE for Query Responses
`POST /api/v1/query` streams via Server-Sent Events (SSE) using FastAPI `StreamingResponse`.
The frontend consumes with `fetch` + `ReadableStream`, not `EventSource` (to support POST).
Three event types only: `token`, `citations`, `done`.

## Architecture Decision Records
Every significant architectural choice gets an ADR in `docs/adr/`.

**When to write one:** choosing between two viable options, accepting a trade-off, deciding to defer something.

**Template:**
```markdown
# ADR-NNN: Title

## Status
Accepted

## Context
What problem or question prompted this decision.

## Decision
What was decided.

## Alternatives Considered
What else was evaluated and why it was rejected.

## Consequences
What becomes easier, harder, or different as a result.
```

Existing ADRs: `docs/adr/001` through `005` covering Qdrant, Azure AI Foundry, hybrid retrieval, LangGraph, and Next.js.
