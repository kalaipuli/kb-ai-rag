"""Critic node stub — scores answer for hallucination risk."""

from typing import Any

from src.graph.state import AgentState


async def critic_node(state: AgentState) -> dict[str, Any]:
    """Stub: returns a low risk score so the graph terminates cleanly.

    Phase 2c will replace this with GPT-4o-mini hallucination detection.
    """
    return {
        "critic_score": 0.1,
        "steps_taken": ["critic"],
    }
