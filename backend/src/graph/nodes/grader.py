"""Grader node stub — scores retrieved chunks for relevance."""

from typing import Any

from src.graph.state import AgentState


async def grader_node(state: AgentState) -> dict[str, Any]:
    """Stub: returns a passing score so the graph proceeds to generator.

    Phase 2c will replace this with GPT-4o-mini chunk relevance scoring.
    """
    return {
        "grader_scores": [0.8],
        "graded_docs": [],
        "all_below_threshold": False,
        "retry_count": state.get("retry_count", 0),
        "steps_taken": ["grader"],
    }
