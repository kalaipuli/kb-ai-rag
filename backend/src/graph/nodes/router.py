"""Router node — classifies query type and selects retrieval strategy via LLM structured output."""

import time
from typing import Any, Literal

import structlog
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from src.graph.state import AgentState

log = structlog.get_logger(__name__)


class _RouterOutput(BaseModel):
    query_type: Literal["factual", "analytical", "multi_hop", "ambiguous"]
    retrieval_strategy: Literal["dense", "hybrid"]


class _RewriteOutput(BaseModel):
    rewritten_query: str


_STRATEGY_MAP: dict[str, Literal["dense", "hybrid"]] = {
    "factual": "hybrid",
    "analytical": "hybrid",
    "multi_hop": "hybrid",
    "ambiguous": "dense",
}

_ROUTER_SYSTEM_PROMPT = (
    "You are a query classification expert. Classify the user query into one of: "
    "factual, analytical, multi_hop, ambiguous. "
    "Also select the retrieval strategy: use 'hybrid' for factual/analytical/multi_hop, "
    "'dense' for ambiguous."
)

_HYDE_SYSTEM_PROMPT = (
    "You are a search query optimizer. Given a question, write a short hypothetical document "
    "that would answer the question. This document is used to improve retrieval accuracy."
)

_STEPBACK_SYSTEM_PROMPT = (
    "You are a search query optimizer. Given a specific multi-hop question, "
    "rewrite it as a broader, more general step-back question that captures the underlying concept."
)


async def router_node(state: AgentState, *, llm: AzureChatOpenAI) -> dict[str, Any]:
    query = state["query"]
    start = time.monotonic()

    try:
        router_chain = llm.with_structured_output(_RouterOutput)
        classification: _RouterOutput = await router_chain.ainvoke(  # type: ignore[assignment]  # with_structured_output returns Runnable[Any, _RouterOutput] but typed as generic Runnable
            [
                {"role": "system", "content": _ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ]
        )

        query_type = classification.query_type
        retrieval_strategy = _STRATEGY_MAP[query_type]

        query_rewritten: str | None = None

        if query_type == "analytical":
            rewrite_chain = llm.with_structured_output(_RewriteOutput)
            rewrite: _RewriteOutput = await rewrite_chain.ainvoke(  # type: ignore[assignment]  # same generic typing issue as above
                [
                    {"role": "system", "content": _HYDE_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ]
            )
            query_rewritten = rewrite.rewritten_query

        elif query_type == "multi_hop":
            rewrite_chain = llm.with_structured_output(_RewriteOutput)
            rewrite = await rewrite_chain.ainvoke(  # type: ignore[assignment]  # same generic typing issue as above
                [
                    {"role": "system", "content": _STEPBACK_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ]
            )
            query_rewritten = rewrite.rewritten_query

    except Exception as exc:
        duration_ms = round((time.monotonic() - start) * 1000)
        log.warning(
            "router_llm_failed",
            error=str(exc),
            query=query,
            duration_ms=duration_ms,
        )
        return {
            "query_type": "factual",
            "retrieval_strategy": "hybrid",
            "query_rewritten": None,
            "steps_taken": [f"router:factual:hybrid:{duration_ms}ms"],
        }

    duration_ms = round((time.monotonic() - start) * 1000)
    step = f"router:{query_type}:{retrieval_strategy}:{duration_ms}ms"

    log.info(
        "router_classified",
        query_type=query_type,
        retrieval_strategy=retrieval_strategy,
        query_rewritten=query_rewritten is not None,
        duration_ms=duration_ms,
    )

    return {
        "query_type": query_type,
        "retrieval_strategy": retrieval_strategy,
        "query_rewritten": query_rewritten,
        "steps_taken": [step],
    }
