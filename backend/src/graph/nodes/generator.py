"""Generator node — produces a cited answer from graded docs using GPT-4o.

Uses the shared SYSTEM_PROMPT from src.generation.prompts and builds citations
directly from the context documents passed to the LLM — the LLM returns the
answer text and a self-assessed confidence float; citations are derived from
the docs, not from LLM output.
"""

import time
from pathlib import Path
from typing import Any

import structlog
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel

from src.generation.prompts import SYSTEM_PROMPT
from src.graph.state import AgentState
from src.schemas.generation import Citation

log = structlog.get_logger(__name__)


class _GeneratorOutput(BaseModel):
    answer: str
    confidence: float  # 0.0 <= value <= 1.0
    reasoning: str  # LangSmith trace only; not stored in state


def _build_citations(docs: list[Any]) -> list[Citation]:
    citations: list[Citation] = []
    for doc in docs:
        meta = doc.metadata if hasattr(doc, "metadata") else {}
        chunk_id: str = meta.get("chunk_id", "")
        raw_path: str = meta.get("source", meta.get("source_path", "unknown"))
        filename: str = Path(raw_path).name
        page_number: int | None = meta.get("page_number")
        retrieval_score: float | None = meta.get("retrieval_score")
        citations.append(
            Citation(
                chunk_id=chunk_id,
                filename=filename,
                source_path=raw_path,
                page_number=page_number,
                retrieval_score=retrieval_score,
            )
        )
    return citations


async def generator_node(state: AgentState, *, llm: AzureChatOpenAI) -> dict[str, Any]:
    """Generate a cited answer from graded (or retrieved) documents.

    Selects context_docs from graded_docs; falls back to retrieved_docs when
    graded_docs is empty and web_fallback_used is True. Calls GPT-4o with
    structured output to produce answer + confidence. Citations are derived
    from the context docs directly.

    Args:
        state: Current AgentState.
        llm: AzureChatOpenAI (GPT-4o) injected by the builder closure.

    Returns:
        Partial state update with answer, citations, confidence, messages,
        and steps_taken.
    """
    query = state["query"]
    graded_docs = state["graded_docs"]
    retrieved_docs = state["retrieved_docs"]
    web_fallback_used = state["web_fallback_used"]
    prior_messages = state["messages"]
    start = time.monotonic()

    # Select context
    if graded_docs:
        context_docs = graded_docs
    elif web_fallback_used:
        context_docs = retrieved_docs
    else:
        context_docs = graded_docs  # empty list — LLM will say insufficient context

    # Build numbered context string
    context_parts = [
        f"[{i + 1}] {doc.page_content}" for i, doc in enumerate(context_docs)
    ]
    context_str = "\n\n".join(context_parts) if context_parts else "(no context available)"

    # Last 5 messages for conversation context
    recent_messages = prior_messages[-5:] if len(prior_messages) > 5 else prior_messages
    history_str = (
        "\n".join(
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in recent_messages
        )
        if recent_messages
        else ""
    )

    user_content = (
        f"Context:\n{context_str}\n\n"
        + (f"Conversation history:\n{history_str}\n\n" if history_str else "")
        + f"Question: {query}"
    )

    try:
        generator_chain = llm.with_structured_output(_GeneratorOutput)
        result: _GeneratorOutput = await generator_chain.ainvoke(  # type: ignore[assignment]  # with_structured_output returns Runnable[Any, _GeneratorOutput] but typed as generic Runnable
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ]
        )
        answer = result.answer
        confidence = max(0.0, min(1.0, result.confidence))
        citations = _build_citations(context_docs)
    except Exception as exc:
        duration_ms = round((time.monotonic() - start) * 1000)
        log.warning(
            "generator_llm_failed",
            error=str(exc),
            query=query,
            duration_ms=duration_ms,
        )
        return {
            "answer": "I encountered an error generating a response.",
            "citations": [],
            "confidence": 0.0,
            "messages": [HumanMessage(content=query)],
            "steps_taken": [f"generator:error:{duration_ms}ms"],
        }

    duration_ms = round((time.monotonic() - start) * 1000)
    step = f"generator:docs={len(context_docs)}:confidence={confidence:.2f}:{duration_ms}ms"

    log.info(
        "generator_complete",
        context_docs=len(context_docs),
        confidence=confidence,
        duration_ms=duration_ms,
    )

    return {
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
        "messages": [HumanMessage(content=query), AIMessage(content=answer)],
        "steps_taken": [step],
    }
