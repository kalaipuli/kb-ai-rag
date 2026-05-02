"""Grader node — scores retrieved chunks for relevance using GPT-4o-mini structured output.

Each retrieved document is scored [0.0, 1.0] against the user query.
Chunks below grader_threshold (from settings) are filtered out. The edge function
route_after_grader decides whether to re-retrieve or proceed to generation.
"""

import asyncio
import functools
import time
from typing import Any, cast

import structlog
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from src.config import get_settings
from src.exceptions import GraderError
from src.graph.state import AgentState

log = structlog.get_logger(__name__)

_GRADER_SYSTEM_PROMPT = (
    "You are a document relevance assessor. Given a user query and a document chunk, "
    "assign a relevance score from 0.0 (completely irrelevant) to 1.0 (highly relevant). "
    "A score >= 0.5 means the document is useful for answering the query. "
    "Provide brief reasoning."
)


class _GradeDoc(BaseModel):
    score: float  # 0.0 <= score <= 1.0
    reasoning: str  # for LangSmith trace only; not stored in state


async def grader_node(
    state: AgentState, *, llm: AzureChatOpenAI, web_search_enabled: bool
) -> dict[str, Any]:
    """Score each retrieved document for relevance to the user query.

    Uses GPT-4o-mini with structured output to produce a float score per chunk.
    Chunks scoring below settings.grader_threshold are filtered from graded_docs.
    Increments retry_count by 1 — the edge function uses this to gate re-routing.

    CRAG escalation: when all scores are below threshold and the post-increment
    retry_count >= 2, this node writes retrieval_strategy="web" into the return dict
    to signal the retriever node to fall back to Tavily on the next attempt. This only
    applies when web_search_enabled=True and web_fallback_used=False (guards against
    double-escalation). Edge functions remain pure routing strings and do not mutate state.

    Raises:
        GraderError: when every batch fails, leaving no usable scores.

    Args:
        state: Current AgentState containing retrieved_docs and query.
        llm: AzureChatOpenAI instance injected by the builder closure.
        web_search_enabled: Whether Tavily web search is available. Captured in the
            build_graph() closure — it is infrastructure state, not graph state.

    Returns:
        Partial state update with grader_scores, graded_docs, all_below_threshold,
        retry_count, and steps_taken. Optionally includes retrieval_strategy="web"
        when CRAG escalation conditions are met.
    """
    settings = get_settings()
    query = state["query"]
    docs = state["retrieved_docs"]
    start = time.monotonic()

    if not docs:
        duration_ms = round((time.monotonic() - start) * 1000)
        step = f"grader:scored=0:passed=0:{duration_ms}ms"
        return {
            "grader_scores": [],
            "graded_docs": [],
            "all_below_threshold": False,
            "retry_count": state["retry_count"] + 1,
            "steps_taken": [step],
        }

    grader_chain = llm.with_structured_output(_GradeDoc)
    scores: list[float] = []
    failed_batches = 0
    total_batches = 0

    for batch_start in range(0, len(docs), settings.grader_batch_size):
        batch = docs[batch_start : batch_start + settings.grader_batch_size]
        total_batches += 1

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
            raw = await asyncio.to_thread(
                functools.partial(grader_chain.batch, messages_batch)  # type: ignore[arg-type]  # LangChain batch() stub types return as list[dict|Any]; functools.partial avoids lambda closure capture bug
            )
            results: list[_GradeDoc] = cast(list[_GradeDoc], raw)
            scores.extend(r.score for r in results)
        except Exception as exc:
            failed_batches += 1
            log.error(
                "grader_batch_failed",
                error=str(exc),
                batch_start=batch_start,
                batch_size=len(batch),
            )
            scores.extend(0.0 for _ in batch)

    if failed_batches == total_batches:
        raise GraderError(f"All {total_batches} grader batch(es) failed — LLM unavailable")

    graded_docs = []
    for doc, score in zip(docs, scores, strict=True):
        if score >= settings.grader_threshold:
            doc.metadata["grader_score"] = float(score)
            graded_docs.append(doc)
    all_below = all(s < settings.grader_threshold for s in scores)

    duration_ms = round((time.monotonic() - start) * 1000)
    step = f"grader:scored={len(scores)}:passed={len(graded_docs)}:{duration_ms}ms"

    new_retry_count = state["retry_count"] + 1
    web_fallback_used: bool = state["web_fallback_used"]

    log.info(
        "grader_complete",
        total_chunks=len(docs),
        passed_chunks=len(graded_docs),
        all_below_threshold=all_below,
        duration_ms=duration_ms,
    )

    result: dict[str, Any] = {
        "grader_scores": scores,
        "graded_docs": graded_docs,
        "all_below_threshold": all_below,
        "retry_count": new_retry_count,
        "steps_taken": [step],
    }

    if all_below and new_retry_count >= 2 and web_search_enabled and not web_fallback_used:
        log.info("grader_escalating_to_web", retry_count=new_retry_count)
        result["retrieval_strategy"] = "web"

    return result
