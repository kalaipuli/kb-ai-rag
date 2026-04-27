"""Unit tests for conditional edge routing functions in graph/edges.py.

All six branching paths are covered:
  route_after_grader — passes / all-below+retries-left / all-below+max-retries
  route_after_critic — low-risk / high-risk+retries-left / high-risk+max-retries
"""

from src.graph.edges import (
    CRITIC_THRESHOLD,
    GRADER_THRESHOLD,
    MAX_RETRIES,
    route_after_critic,
    route_after_grader,
)
from src.graph.state import AgentState


def _base_state() -> AgentState:
    """Minimal AgentState with only the fields read by edge functions."""
    return AgentState(  # type: ignore[call-arg]
        session_id="test",
        query="q",
        filters=None,
        k=None,
        query_type="factual",
        retrieval_strategy="hybrid",
        query_rewritten=None,
        retrieved_docs=[],
        web_fallback_used=False,
        grader_scores=[],
        graded_docs=[],
        all_below_threshold=False,
        retry_count=0,
        answer=None,
        citations=[],
        confidence=None,
        critic_score=None,
        messages=[],
        steps_taken=[],
    )


# ---------------------------------------------------------------------------
# route_after_grader
# ---------------------------------------------------------------------------


class TestRouteAfterGrader:
    def test_at_least_one_score_passing_routes_to_generator(self) -> None:
        state = _base_state()
        state["grader_scores"] = [GRADER_THRESHOLD + 0.1]
        state["all_below_threshold"] = False
        state["retry_count"] = 0

        assert route_after_grader(state) == "generator"

    def test_all_below_threshold_with_retries_left_routes_to_retriever(self) -> None:
        state = _base_state()
        state["grader_scores"] = [GRADER_THRESHOLD - 0.1]
        state["all_below_threshold"] = True
        state["retry_count"] = 0

        assert route_after_grader(state) == "retriever"

    def test_all_below_threshold_at_max_retries_routes_to_generator(self) -> None:
        state = _base_state()
        state["grader_scores"] = [GRADER_THRESHOLD - 0.1]
        state["all_below_threshold"] = True
        state["retry_count"] = MAX_RETRIES

        assert route_after_grader(state) == "generator"


# ---------------------------------------------------------------------------
# route_after_critic
# ---------------------------------------------------------------------------


class TestRouteAfterCritic:
    def test_low_risk_score_routes_to_end(self) -> None:
        state = _base_state()
        state["critic_score"] = CRITIC_THRESHOLD - 0.1
        state["retry_count"] = 0

        assert route_after_critic(state) == "end"

    def test_high_risk_score_with_retries_left_routes_to_retriever(self) -> None:
        state = _base_state()
        state["critic_score"] = CRITIC_THRESHOLD + 0.1
        state["retry_count"] = 0

        assert route_after_critic(state) == "retriever"

    def test_high_risk_score_at_max_retries_routes_to_end(self) -> None:
        state = _base_state()
        state["critic_score"] = CRITIC_THRESHOLD + 0.1
        state["retry_count"] = MAX_RETRIES

        assert route_after_critic(state) == "end"

    def test_none_critic_score_treated_as_zero_routes_to_end(self) -> None:
        state = _base_state()
        state["critic_score"] = None
        state["retry_count"] = 0

        assert route_after_critic(state) == "end"
