"""Retriever node stub — calls HybridRetriever or Tavily web fallback."""

from typing import Any

from src.graph.state import AgentState


async def retriever_node(state: AgentState) -> dict[str, Any]:
    """Stub: returns empty doc list without retrieval calls.

    Phase 2c will inject HybridRetriever via builder closure and call Tavily
    when web_fallback is triggered by the grader edge.
    """
    return {
        "retrieved_docs": [],
        "web_fallback_used": False,
        "steps_taken": ["retriever"],
    }
