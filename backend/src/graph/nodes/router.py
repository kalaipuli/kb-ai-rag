"""Router node stub — classifies query type and selects retrieval strategy."""

from typing import Any

from src.graph.state import AgentState


async def router_node(state: AgentState) -> dict[str, Any]:
    """Stub: returns deterministic classification without LLM calls.

    Phase 2c will replace this with GPT-4o-mini structured output.
    """
    return {
        "query_type": "factual",
        "retrieval_strategy": "hybrid",
        "query_rewritten": None,
        "steps_taken": ["router"],
    }
