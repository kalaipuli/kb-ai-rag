"""Conditional edge functions for the LangGraph agentic pipeline.

These are pure functions — no LLM calls, no I/O, no side effects.
They read AgentState and return a routing string consumed by LangGraph's
add_conditional_edges.
"""

from typing import Literal

from src.graph.state import AgentState

GRADER_THRESHOLD: float = 0.5
CRITIC_THRESHOLD: float = 0.7
MAX_RETRIES: int = 1


def route_after_grader(state: AgentState) -> Literal["retriever", "generator"]:
    """Route after grading: fall back to Tavily retrieval when all chunks fail.

    Returns "retriever" only when every grader score is below threshold AND
    retry budget remains.  Falls through to "generator" at max retries so the
    graph always terminates.
    """
    if state["all_below_threshold"] and state["retry_count"] < MAX_RETRIES:
        return "retriever"
    return "generator"


def route_after_critic(state: AgentState) -> Literal["retriever", "end"]:
    """Route after critic: re-retrieve when hallucination risk is too high.

    Returns "retriever" only when critic_score exceeds the threshold AND retry
    budget remains.  Falls through to "end" at max retries so the graph always
    terminates.
    """
    critic_score = state.get("critic_score") or 0.0
    if critic_score > CRITIC_THRESHOLD and state["retry_count"] < MAX_RETRIES:
        return "retriever"
    return "end"
