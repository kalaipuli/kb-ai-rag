"""Conditional edge functions for the LangGraph agentic pipeline.

These are pure functions — no LLM calls, no I/O, no side effects.
They read AgentState and return a routing string consumed by LangGraph's
add_conditional_edges.
"""

from typing import Literal

from src.config import get_settings
from src.graph.state import AgentState


def route_after_grader(state: AgentState) -> Literal["retriever", "generator"]:
    """Route after grading: fall back to Tavily retrieval when all chunks fail.

    Returns "retriever" only when every grader score is below threshold AND
    retry budget remains.  Falls through to "generator" at max retries so the
    graph always terminates.
    """
    settings = get_settings()
    if state["all_below_threshold"] and state["retry_count"] < settings.graph_max_retries:
        return "retriever"
    return "generator"


def route_after_critic(state: AgentState) -> Literal["retriever", "end"]:
    """Route after critic: re-retrieve when hallucination risk is too high.

    Returns "retriever" only when critic_score exceeds the threshold AND retry
    budget remains.  Falls through to "end" at max retries so the graph always
    terminates.
    """
    settings = get_settings()
    critic_score: float = state["critic_score"] if state["critic_score"] is not None else 0.0
    if (
        critic_score > settings.critic_threshold
        and state["retry_count"] < settings.graph_max_retries
    ):
        return "retriever"
    return "end"
