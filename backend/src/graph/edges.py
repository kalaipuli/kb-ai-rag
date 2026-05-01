"""Conditional edge functions for the LangGraph agentic pipeline.

These are pure functions — no LLM calls, no I/O, no side effects.
They read AgentState and return a routing string consumed by LangGraph's
add_conditional_edges.
"""

from typing import Literal

from src.config import Settings
from src.graph.state import AgentState


def route_after_grader(state: AgentState, settings: Settings) -> Literal["retriever", "generator"]:
    """Route after grading: pure routing based on grader outcome and retry budget.

    Returns "retriever" only when every grader score is below threshold AND
    retry budget remains.  Falls through to "generator" at max retries so the
    graph always terminates.  Strategy transitions (e.g. escalating to web
    retrieval on the CRAG path) are the grader node's responsibility — this
    function only routes.
    """
    if state["all_below_threshold"] and state["retry_count"] < settings.graph_max_retries:
        return "retriever"
    return "generator"


def route_after_critic(state: AgentState, settings: Settings) -> Literal["retriever", "end"]:
    """Route after critic: re-retrieve when hallucination risk is too high.

    Returns "retriever" only when critic_score exceeds the threshold AND retry
    budget remains.  Falls through to "end" at max retries so the graph always
    terminates.
    """
    critic_score: float = state["critic_score"] if state["critic_score"] is not None else 0.0
    if (
        critic_score > settings.critic_threshold
        and state["retry_count"] < settings.graph_max_retries
    ):
        return "retriever"
    return "end"
