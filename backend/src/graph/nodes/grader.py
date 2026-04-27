"""Grader node — scores retrieved chunks for relevance using GPT-4o-mini structured output.

Each retrieved document is scored [0.0, 1.0] against the user query.
Chunks below GRADER_THRESHOLD are filtered out. The edge function
route_after_grader decides whether to re-retrieve or proceed to generation.
"""

import time
from typing import Any

import structlog
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from src.graph.edges import GRADER_THRESHOLD
from src.graph.state import AgentState

log = structlog.get_logger(__name__)

_BATCH_SIZE = 10

_GRADER_SYSTEM_PROMPT = (
    "You are a document relevance assessor. Given a user query and a document chunk, "
    "assign a relevance score from 0.0 (completely irrelevant) to 1.0 (highly relevant). "
    "A score >= 0.5 means the document is useful for answering the query. "
    "Provide brief reasoning."
)


class _GradeDoc(BaseModel):
    score: float  # 0.0 <= score <= 1.0
    reasoning: str  # for LangSmith trace only; not stored in state


async def grader_node(state: AgentState, *, llm: AzureChatOpenAI) -> dict[str, Any]:
    """Score each retrieved document for relevance to the user query.

    Uses GPT-4o-mini with structured output to produce a float score per chunk.
    Chunks scoring below GRADER_THRESHOLD are filtered from graded_docs.
    Increments retry_count by 1 — the edge function uses this to gate re-routing.

    Args:
        state: Current AgentState containing retrieved_docs and query.
        llm: AzureChatOpenAI instance injected by the builder closure.

    Returns:
        Partial state update with grader_scores, graded_docs, all_below_threshold,
        retry_count, and steps_taken.
    """
    query = state["query"]
    docs = state["retrieved_docs"]
    start = time.monotonic()

    grader_chain = llm.with_structured_output(_GradeDoc)
    scores: list[float] = []

    for batch_start in range(0, max(len(docs), 1), _BATCH_SIZE):
        batch = docs[batch_start : batch_start + _BATCH_SIZE]
        if not batch:
            break

        messages_batch = [
            [
                {"role": "system", "content": _GRADER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Query: {query}\n\nDocument chunk:\n{doc.page_content}",
                },
            ]
            for doc in batch
        ]

        try:
            results: list[_GradeDoc] = grader_chain.batch(messages_batch)  # type: ignore[arg-type, assignment]  # LangChain Runnable.batch stubs expect Sequence[PromptValue|str|...] but accept list[list[dict]] at runtime; assignment: returns list[Any] typed as list[_GradeDoc]
            scores.extend(r.score for r in results)
        except Exception as exc:
            log.warning(
                "grader_batch_failed",
                error=str(exc),
                batch_start=batch_start,
                batch_size=len(batch),
            )
            # assign 0.0 for every chunk in the failed batch
            scores.extend(0.0 for _ in batch)

    if not docs:
        scores = []

    graded_docs = [doc for doc, score in zip(docs, scores, strict=True) if score >= GRADER_THRESHOLD]
    all_below = len(scores) > 0 and all(s < GRADER_THRESHOLD for s in scores)

    duration_ms = round((time.monotonic() - start) * 1000)
    step = f"grader:scored={len(scores)}:passed={len(graded_docs)}:{duration_ms}ms"

    log.info(
        "grader_complete",
        total_chunks=len(docs),
        passed_chunks=len(graded_docs),
        all_below_threshold=all_below,
        duration_ms=duration_ms,
    )

    return {
        "grader_scores": scores,
        "graded_docs": graded_docs,
        "all_below_threshold": all_below,
        "retry_count": state.get("retry_count", 0) + 1,
        "steps_taken": [step],
    }
