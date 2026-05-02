"""Unit tests for the retriever node (T02 — Phase 2c)."""

import math
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document

from src.graph.nodes.retriever import retriever_node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    strategy: str = "hybrid",
    query: str = "What is RAG?",
    query_rewritten: str | None = None,
    k: int | None = None,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "query": query,
        "filters": filters,
        "k": k,
        "query_type": "factual",
        "retrieval_strategy": strategy,
        "query_rewritten": query_rewritten,
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


def _make_retrieval_result(
    text: str = "chunk text",
    score: float = 0.9,
    page_number: int = 2,
) -> MagicMock:
    """Return a MagicMock that looks like a RetrievalResult."""
    result = MagicMock()
    result.chunk_id = "chunk-001"
    result.text = text
    result.score = score
    result.metadata = {
        "source_path": "docs/file.pdf",
        "page_number": page_number,
    }
    return result


# ---------------------------------------------------------------------------
# Test 1: hybrid strategy → HybridRetriever.retrieve() called; docs are Documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_strategy_calls_retriever_and_returns_documents() -> None:
    raw = _make_retrieval_result()
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[raw])

    state = _make_state(strategy="hybrid")
    result = await retriever_node(state, retriever=mock_retriever)

    mock_retriever.retrieve.assert_awaited_once_with(
        "What is RAG?", k=None, filters=None, mode="hybrid"
    )

    docs = result["retrieved_docs"]
    assert len(docs) == 1
    assert isinstance(docs[0], Document)
    assert docs[0].page_content == "chunk text"
    assert docs[0].metadata["chunk_id"] == "chunk-001"
    assert docs[0].metadata["score"] == 0.9
    assert docs[0].metadata["retrieval_score"] == pytest.approx(1.0 / (1.0 + math.exp(-0.9)))
    assert docs[0].metadata["page_number"] == 2
    assert result["web_fallback_used"] is False


# ---------------------------------------------------------------------------
# Test 2: query_rewritten is used as the retrieval query when set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uses_query_rewritten_when_set() -> None:
    raw = _make_retrieval_result()
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[raw])

    state = _make_state(
        strategy="hybrid", query="original query", query_rewritten="rewritten query"
    )
    await retriever_node(state, retriever=mock_retriever)

    mock_retriever.retrieve.assert_awaited_once_with(
        "rewritten query", k=None, filters=None, mode="hybrid"
    )


# ---------------------------------------------------------------------------
# Test 3: web strategy → Tavily called; web_fallback_used = True; docs are Documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_strategy_calls_tavily_and_sets_fallback_flag() -> None:
    tavily_response = {
        "results": [
            {
                "url": "https://example.com/doc",
                "title": "Example",
                "content": "Tavily result content",
                "score": 0.85,
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.search.return_value = tavily_response

    state = _make_state(strategy="web")
    result = await retriever_node(state, tavily_client=mock_client)

    assert result["web_fallback_used"] is True
    docs = result["retrieved_docs"]
    assert len(docs) == 1
    assert isinstance(docs[0], Document)
    assert docs[0].page_content == "Tavily result content"
    assert docs[0].metadata["source"] == "https://example.com/doc"
    assert docs[0].metadata["title"] == "Example"
    assert docs[0].metadata["score"] == 0.85


# ---------------------------------------------------------------------------
# Test 4 (error path): Tavily raises → web_fallback_used=False, empty docs, no exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tavily_error_returns_empty_docs_without_raising() -> None:
    mock_client = MagicMock()
    mock_client.search.side_effect = RuntimeError("Tavily unavailable")

    state = _make_state(strategy="web")
    result = await retriever_node(state, tavily_client=mock_client)

    assert result["web_fallback_used"] is False
    assert result["retrieved_docs"] == []


# ---------------------------------------------------------------------------
# Test 5 (error path): HybridRetriever.retrieve raises → empty docs, no exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_retriever_error_returns_empty_docs_without_raising() -> None:
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(side_effect=RuntimeError("Qdrant down"))

    state = _make_state(strategy="hybrid")
    result = await retriever_node(state, retriever=mock_retriever)

    assert result["retrieved_docs"] == []
    assert result["web_fallback_used"] is False


# ---------------------------------------------------------------------------
# Test 6: steps_taken contains entry matching "retriever:{strategy}:{n}ms"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_steps_taken_contains_retriever_step_with_duration() -> None:
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[])

    state = _make_state(strategy="dense")
    result = await retriever_node(state, retriever=mock_retriever)

    assert len(result["steps_taken"]) == 1
    step = result["steps_taken"][0]
    assert re.fullmatch(
        r"retriever:dense:\d+ms", step
    ), f"step string '{step}' did not match expected pattern"


# ---------------------------------------------------------------------------
# Test 7: dense strategy forwards mode="dense" to HybridRetriever.retrieve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dense_strategy_forwards_mode_dense_to_retriever() -> None:
    raw = _make_retrieval_result(text="dense chunk")
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[raw])

    state = _make_state(strategy="dense", k=3)
    result = await retriever_node(state, retriever=mock_retriever)

    mock_retriever.retrieve.assert_awaited_once_with(
        "What is RAG?", k=3, filters=None, mode="dense"
    )
    assert len(result["retrieved_docs"]) == 1
    assert result["retrieved_docs"][0].page_content == "dense chunk"


# ---------------------------------------------------------------------------
# Test 8: hybrid strategy forwards mode="hybrid" to HybridRetriever.retrieve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hybrid_strategy_forwards_mode_hybrid_to_retriever() -> None:
    raw = _make_retrieval_result(text="hybrid chunk")
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[raw])

    state = _make_state(strategy="hybrid", k=5)
    result = await retriever_node(state, retriever=mock_retriever)

    mock_retriever.retrieve.assert_awaited_once_with(
        "What is RAG?", k=5, filters=None, mode="hybrid"
    )
    assert len(result["retrieved_docs"]) == 1
    assert result["retrieved_docs"][0].page_content == "hybrid chunk"


# ---------------------------------------------------------------------------
# Test 9: page_number=-1 (TXT files) is excluded from Document metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_page_number_minus_one_excluded_from_document_metadata() -> None:
    raw = _make_retrieval_result(page_number=-1)
    mock_retriever = MagicMock()
    mock_retriever.retrieve = AsyncMock(return_value=[raw])

    state = _make_state(strategy="hybrid")
    result = await retriever_node(state, retriever=mock_retriever)

    doc = result["retrieved_docs"][0]
    assert "page_number" not in doc.metadata
    assert doc.metadata["retrieval_score"] == pytest.approx(1.0 / (1.0 + math.exp(-0.9)))
