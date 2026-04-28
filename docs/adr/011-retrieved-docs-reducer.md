# ADR-011: `retrieved_docs` Reducer — Working Buffer vs. Audit Log

## Status
Accepted

## Context

`retrieved_docs` was annotated `Annotated[list[Document], operator.add]`, making it
an append-only field.  LangGraph applies the reducer whenever a node returns a
partial state update containing `retrieved_docs`, so each retrieval pass _appended_
to the existing list rather than replacing it.

This caused two distinct bugs:

**Bug 1 — CRAG retry double-scoring.**  In the Corrective-RAG retry loop, Pass 1
returns N docs and the grader filters some below threshold.  When the retriever node
runs again (Pass 2) it returns another N docs, but `operator.add` appends them to the
N docs still sitting in state from Pass 1.  The grader on Pass 2 therefore scores 2N
documents — including docs already examined and rejected on Pass 1.  This inflates
latency and can cause previously-rejected chunks to resurface in the final answer.

**Bug 2 — Checkpointer contamination across sessions.**  The SQLite checkpointer
persists graph state keyed by `thread_id` (= `session_id`).  When a session is
resumed, LangGraph rehydrates the last checkpoint, which still contains the
`retrieved_docs` list from the previous run.  On the next retrieval pass the reducer
appends new docs to that stale list.  Live log evidence: the BM25 index held 15 total
chunks; the grader reported `total_chunks=15` despite the retriever returning only 5
— the extra 10 were accumulated from a prior session checkpoint.

## Decision

Remove `operator.add` from `retrieved_docs`.  The field is declared as a plain
`list[Document]` TypedDict entry with no reducer annotation.  LangGraph treats
unannotated fields as plain replacement: when a node returns `retrieved_docs`, the
new value wholly replaces the previous one.

Each retriever node invocation therefore produces a clean working set of documents
that is consumed by the immediately following grader node, and nothing more.

`steps_taken` and `messages` retain their own reducers (`operator.add` and
`add_messages` respectively), which are correct for their append-only semantics —
`steps_taken` is an observability audit log that must accumulate across all nodes,
and `messages` is a conversation history that must deduplicate by message ID.

## Alternatives Considered

**Clear `retrieved_docs` at the start of each grader node invocation.**  The grader
node could reset the list before scoring.  Rejected because the grader node does not
own retrieval state; ownership belongs to the retriever node.  Adding retrieval state
management to the grader violates single-responsibility and makes the dependency
implicit.

**Slice only the last N docs in the grader.**  The grader could take only the last K
entries, where K equals the configured retrieval batch size.  Rejected as fragile:
it couples the grader to knowledge of the retriever's batch size and silently
misbehaves if that size changes or if retrieval is partial.

## Consequences

- Grader always scores exactly the documents returned by the current retrieval pass —
  no stale docs from prior passes or prior sessions.
- Checkpointer resumption no longer accumulates documents from previous session
  checkpoints.
- Unit tests in `backend/tests/unit/graph/test_state.py` are updated: the two tests
  that verified `operator.add` append behaviour are replaced by a single test that
  asserts no `__metadata__` attribute exists on the `retrieved_docs` annotation
  (i.e., no `Annotated` wrapper is present).
- `import operator` is retained in `state.py` because `steps_taken` still requires it.
