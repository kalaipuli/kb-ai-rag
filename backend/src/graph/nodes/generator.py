"""Generator node stub — produces a cited answer from graded docs."""

from typing import Any

from src.graph.state import AgentState


async def generator_node(state: AgentState) -> dict[str, Any]:
    """Stub: returns a hardcoded answer without LLM calls.

    Phase 2c will replace this with GPT-4o cited answer generation.
    """
    return {
        "answer": "stub answer",
        "citations": [],
        "confidence": 0.9,
        "steps_taken": ["generator"],
    }
