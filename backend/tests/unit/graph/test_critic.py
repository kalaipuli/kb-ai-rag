"""Unit tests for the Critic node.

Covers:
1. Low critic_score (<= 0.7): state updated correctly
2. High critic_score (> 0.7): state updated correctly (edge handles routing)
3. steps_taken contains critic entry with duration_ms
4. LLM failure → critic_score returns 0.0 (error path)
5. Score is within [0.0, 1.0]
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document

from src.graph.nodes.critic import _CriticOutput, critic_node


def _make_doc(content: str) -> Document:
    return Document(page_content=content, metadata={"chunk_id": "c1"})


def _make_state(
    answer: str = "Paris is the capital of France.",
    graded_docs: list[Document] | None = None,
    query: str = "What is the capital of France?",
) -> dict[str, Any]:
    return {
        "session_id": "s1",
        "query": query,
        "filters": None,
        "k": None,
        "query_type": "factual",
        "retrieval_strategy": "hybrid",
        "query_rewritten": None,
        "retrieved_docs": [],
        "web_fallback_used": False,
        "grader_scores": [],
        "graded_docs": graded_docs or [_make_doc("Paris is the capital of France.")],
        "all_below_threshold": False,
        "retry_count": 0,
        "answer": answer,
        "citations": [],
        "confidence": 0.9,
        "critic_score": None,
        "messages": [],
        "steps_taken": [],
    }


def _mock_llm(hallucination_risk: float) -> MagicMock:
    output = _CriticOutput(
        hallucination_risk=hallucination_risk,
        unsupported_claims=[],
        reasoning="test",
    )
    chain_mock = MagicMock()
    chain_mock.ainvoke = AsyncMock(return_value=output)
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    return llm


# ---------------------------------------------------------------------------
# Test 1: low critic_score (<= 0.7)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_low_critic_score_state_updated() -> None:
    llm = _mock_llm(hallucination_risk=0.2)
    state = _make_state()

    result = await critic_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert result["critic_score"] == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# Test 2: high critic_score (> 0.7)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_high_critic_score_state_updated() -> None:
    llm = _mock_llm(hallucination_risk=0.85)
    state = _make_state(answer="The Eiffel Tower is in London.")

    result = await critic_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert result["critic_score"] == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# Test 3: steps_taken contains critic entry with duration_ms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_steps_taken_contains_critic_entry() -> None:
    llm = _mock_llm(hallucination_risk=0.3)
    state = _make_state()

    result = await critic_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert len(result["steps_taken"]) == 1
    step = result["steps_taken"][0]
    assert step.startswith("critic:")
    assert "ms" in step


# ---------------------------------------------------------------------------
# Test 4: LLM failure → critic_score = 0.0 (error path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_failure_returns_zero_score() -> None:
    chain_mock = MagicMock()
    chain_mock.ainvoke = AsyncMock(side_effect=RuntimeError("Azure timeout"))
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    state = _make_state()

    result = await critic_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert result["critic_score"] == 0.0


# ---------------------------------------------------------------------------
# Test 5: score is within [0.0, 1.0] even if LLM returns out-of-bounds value
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_clamped_to_valid_range() -> None:
    # Simulate LLM returning a value above 1.0
    output = _CriticOutput(
        hallucination_risk=1.8,
        unsupported_claims=["claim A"],
        reasoning="test",
    )
    chain_mock = MagicMock()
    chain_mock.ainvoke = AsyncMock(return_value=output)
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    state = _make_state()

    result = await critic_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert 0.0 <= result["critic_score"] <= 1.0
