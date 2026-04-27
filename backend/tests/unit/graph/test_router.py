"""Unit tests for the router node (T01 — Phase 2c)."""

import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.nodes.router import router_node


def _make_state(query: str = "What is retrieval-augmented generation?") -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "query": query,
        "filters": None,
        "k": None,
        "query_type": "factual",
        "retrieval_strategy": "hybrid",
        "query_rewritten": None,
        "retrieved_docs": [],
        "web_fallback_used": False,
        "grader_scores": [],
        "graded_docs": [],
        "all_below_threshold": False,
        "retry_count": 0,
        "answer": None,
        "citations": [],
        "confidence": None,
        "critic_score": None,
        "messages": [],
        "steps_taken": [],
    }


def _make_llm_with_structured_output(
    query_type: str,
    retrieval_strategy: str,
    rewritten_query: str | None = None,
) -> MagicMock:
    """Build a mock AzureChatOpenAI whose with_structured_output().ainvoke() returns
    the appropriate Pydantic-like object depending on the schema requested."""

    from src.graph.nodes.router import (  # type: ignore[attr-defined]  # private classes accessed only in tests
        _RewriteOutput,
        _RouterOutput,
    )

    router_result = MagicMock(spec=_RouterOutput)
    router_result.query_type = query_type
    router_result.retrieval_strategy = retrieval_strategy
    router_result.reasoning = "test reasoning"

    rewrite_result = MagicMock(spec=_RewriteOutput)
    rewrite_result.rewritten_query = rewritten_query or "broader rewritten query"

    def _with_structured_output(schema: type) -> MagicMock:
        chain = MagicMock()
        if schema is _RouterOutput:
            chain.ainvoke = AsyncMock(return_value=router_result)
        else:
            chain.ainvoke = AsyncMock(return_value=rewrite_result)
        return chain

    llm = MagicMock()
    llm.with_structured_output = MagicMock(side_effect=_with_structured_output)
    return llm


# ---------------------------------------------------------------------------
# Test 1: factual query → correct query_type and query_rewritten=None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factual_query_classification() -> None:
    llm = _make_llm_with_structured_output("factual", "hybrid")
    state = _make_state("What is RAG?")

    result = await router_node(state, llm=llm)  # type: ignore[arg-type]  # mock accepted where AzureChatOpenAI expected

    assert result["query_type"] == "factual"
    assert result["query_rewritten"] is None


# ---------------------------------------------------------------------------
# Test 2: factual query → retrieval_strategy is "hybrid"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factual_query_uses_hybrid_strategy() -> None:
    llm = _make_llm_with_structured_output("factual", "hybrid")
    state = _make_state("What is RAG?")

    result = await router_node(state, llm=llm)  # type: ignore[arg-type]

    assert result["retrieval_strategy"] == "hybrid"


# ---------------------------------------------------------------------------
# Test 3: analytical query → HyDE rewrite stored in query_rewritten
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analytical_query_generates_hyde_rewrite() -> None:
    expected_rewrite = "Retrieval-augmented generation combines dense retrieval with generation..."
    llm = _make_llm_with_structured_output("analytical", "hybrid", rewritten_query=expected_rewrite)
    state = _make_state("Explain how RAG improves factual accuracy in LLMs.")

    result = await router_node(state, llm=llm)  # type: ignore[arg-type]

    assert result["query_type"] == "analytical"
    assert result["retrieval_strategy"] == "hybrid"
    assert isinstance(result["query_rewritten"], str)
    assert len(result["query_rewritten"]) > 0
    assert result["query_rewritten"] == expected_rewrite


# ---------------------------------------------------------------------------
# Test 4: multi_hop query → step-back rewrite stored in query_rewritten
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_hop_query_generates_stepback_rewrite() -> None:
    expected_rewrite = "What are the components of modern question-answering systems?"
    llm = _make_llm_with_structured_output("multi_hop", "hybrid", rewritten_query=expected_rewrite)
    state = _make_state("What model does the RAG system use and who built it and when was it released?")

    result = await router_node(state, llm=llm)  # type: ignore[arg-type]

    assert result["query_type"] == "multi_hop"
    assert result["retrieval_strategy"] == "hybrid"
    assert isinstance(result["query_rewritten"], str)
    assert len(result["query_rewritten"]) > 0
    assert result["query_rewritten"] == expected_rewrite


# ---------------------------------------------------------------------------
# Test 5: LLM raises on classification → safe defaults returned, no re-raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_error_falls_back_to_safe_defaults() -> None:
    llm = MagicMock()
    chain = MagicMock()
    chain.ainvoke = AsyncMock(side_effect=RuntimeError("Azure timeout"))
    llm.with_structured_output = MagicMock(return_value=chain)

    state = _make_state("What is RAG?")

    with patch("src.graph.nodes.router.log") as mock_log:
        result = await router_node(state, llm=llm)  # type: ignore[arg-type]

    assert result["query_type"] == "factual"
    assert result["retrieval_strategy"] == "hybrid"
    assert result["query_rewritten"] is None
    mock_log.warning.assert_called_once()
    call_kwargs = mock_log.warning.call_args
    assert call_kwargs[0][0] == "router_llm_failed"


# ---------------------------------------------------------------------------
# Test 6: steps_taken contains "router:factual:hybrid:{n}ms" pattern
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_steps_taken_contains_router_step_string() -> None:
    llm = _make_llm_with_structured_output("factual", "hybrid")
    state = _make_state("What is RAG?")

    result = await router_node(state, llm=llm)  # type: ignore[arg-type]

    assert len(result["steps_taken"]) == 1
    step = result["steps_taken"][0]
    assert re.fullmatch(r"router:factual:hybrid:\d+ms", step), (
        f"step string '{step}' did not match expected pattern"
    )
