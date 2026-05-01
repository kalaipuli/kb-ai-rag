"""Critic node — assesses hallucination risk in the generated answer.

Uses GPT-4o-mini with structured output to score how well the answer is
grounded in graded_docs.  A high hallucination_risk score causes
route_after_critic to send the graph back to the retriever (up to MAX_RETRIES).
"""

import time
from typing import Any

import structlog
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from src.graph.state import AgentState

log = structlog.get_logger(__name__)

_CRITIC_SYSTEM_PROMPT = (
    "You are a hallucination detection expert. Given a question, the source documents "
    "used as context, and a generated answer, assess how well the answer is grounded "
    "in the provided documents.\n\n"
    "Assign a hallucination_risk score from 0.0 (fully grounded, no hallucination) "
    "to 1.0 (answer contains claims not supported by any document).\n\n"
    "List any specific claims in the answer that are not supported by the context "
    "documents in the context."
)


class _CriticOutput(BaseModel):
    hallucination_risk: float  # 0.0 <= value <= 1.0


async def critic_node(
    state: AgentState, *, llm: AzureChatOpenAI, web_search_enabled: bool
) -> dict[str, Any]:
    """Score the generated answer for hallucination risk.

    Compares the answer against graded_docs to identify unsupported claims.
    Sets critic_score in state — the edge function route_after_critic uses
    this value to decide whether to re-retrieve.

    Args:
        state: Current AgentState containing answer and graded_docs.
        llm: AzureChatOpenAI (GPT-4o-mini) injected by the builder closure.

    Returns:
        Partial state update with critic_score and steps_taken.
    """
    answer = state.get("answer") or ""
    graded_docs = state["graded_docs"]
    query = state["query"]
    start = time.monotonic()

    context_parts = [f"[{i + 1}] {doc.page_content}" for i, doc in enumerate(graded_docs)]
    context_str = "\n\n".join(context_parts) if context_parts else "(no context available)"

    user_content = (
        f"Question: {query}\n\n"
        f"Source documents:\n{context_str}\n\n"
        f"Generated answer:\n{answer}"
    )

    try:
        critic_chain = llm.with_structured_output(_CriticOutput)
        result: _CriticOutput = await critic_chain.ainvoke(  # type: ignore[assignment]  # with_structured_output returns Runnable[Any, _CriticOutput] but typed as generic Runnable
            [
                {"role": "system", "content": _CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ]
        )
        critic_score = max(0.0, min(1.0, result.hallucination_risk))
    except Exception as exc:
        duration_ms = round((time.monotonic() - start) * 1000)
        log.warning(
            "critic_llm_failed",
            error=str(exc),
            query=query,
            duration_ms=duration_ms,
        )
        return {
            "critic_score": 0.0,
            "steps_taken": [f"critic:error:score=0.0:{duration_ms}ms"],
        }

    duration_ms = round((time.monotonic() - start) * 1000)
    step = f"critic:score={critic_score:.3f}:{duration_ms}ms"

    log.info(
        "critic_complete",
        critic_score=critic_score,
        duration_ms=duration_ms,
    )

    return {
        "critic_score": critic_score,
        "steps_taken": [step],
    }
