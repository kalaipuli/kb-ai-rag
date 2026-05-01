"""Unit tests for build_graph() in graph/builder.py.

Covers:
  1. build_graph() returns a non-None compiled graph with a mock retriever
  2. compiled_graph.astream() with stub nodes completes without exception
  3. AsyncSqliteSaver is instantiated using the path value from settings
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_openai import AzureChatOpenAI

from src.graph.builder import build_graph


def _mock_settings(tmp_path: Path) -> Any:
    settings = MagicMock()
    settings.sqlite_checkpointer_path = str(tmp_path / "test_checkpointer.sqlite")
    settings.sqlite_checkpointer_ttl_days = 7
    settings.azure_openai_endpoint = "https://fake-endpoint.openai.azure.com/"
    settings.azure_openai_api_key.get_secret_value.return_value = "fake-api-key"
    settings.azure_openai_api_version = "2024-08-01-preview"
    settings.azure_chat_deployment = "gpt-4o"
    settings.tavily_api_key.get_secret_value.return_value = ""
    settings.grader_threshold = 0.5
    settings.critic_threshold = 0.7
    settings.graph_max_retries = 2
    return settings


def _mock_retriever() -> MagicMock:
    return MagicMock()


def _mock_llm() -> MagicMock:
    return MagicMock(spec=AzureChatOpenAI)


def _initial_state() -> dict[str, Any]:
    return {
        "session_id": "test-session",
        "query": "What is the capital of France?",
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


# ---------------------------------------------------------------------------
# Test 1: build_graph returns a compiled graph
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_graph_returns_compiled_graph(tmp_path: Path) -> None:
    from langgraph.graph.state import CompiledStateGraph

    settings = _mock_settings(tmp_path)
    retriever = _mock_retriever()

    compiled = await build_graph(settings=settings, retriever=retriever, llm=_mock_llm(), llm_4o=_mock_llm())

    assert compiled is not None
    assert isinstance(compiled, CompiledStateGraph)


# ---------------------------------------------------------------------------
# Test 2: astream() with stub nodes completes without exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compiled_graph_astream_completes(tmp_path: Path) -> None:
    settings = _mock_settings(tmp_path)
    retriever = _mock_retriever()

    compiled = await build_graph(settings=settings, retriever=retriever, llm=_mock_llm(), llm_4o=_mock_llm())

    config = {"configurable": {"thread_id": "test-session"}}
    updates: list[Any] = []
    async for update in compiled.astream(_initial_state(), config=config, stream_mode="updates"):
        updates.append(update)

    assert len(updates) > 0


# ---------------------------------------------------------------------------
# Test 3: AsyncSqliteSaver is instantiated with the path from settings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_graph_uses_settings_checkpointer_path(tmp_path: Path) -> None:
    import aiosqlite

    expected_path = str(tmp_path / "custom_checkpointer.sqlite")
    settings = MagicMock()
    settings.sqlite_checkpointer_path = expected_path
    settings.sqlite_checkpointer_ttl_days = 7
    settings.azure_openai_endpoint = "https://fake-endpoint.openai.azure.com/"
    settings.azure_openai_api_key.get_secret_value.return_value = "fake-api-key"
    settings.azure_openai_api_version = "2024-08-01-preview"
    settings.azure_chat_deployment = "gpt-4o"
    settings.tavily_api_key.get_secret_value.return_value = ""
    settings.grader_threshold = 0.5
    settings.critic_threshold = 0.7
    settings.graph_max_retries = 2
    retriever = _mock_retriever()

    with patch("src.graph.builder.aiosqlite.connect", wraps=aiosqlite.connect) as mock_connect:
        await build_graph(settings=settings, retriever=retriever, llm=_mock_llm(), llm_4o=_mock_llm())
        # Two calls: one for the TTL cleanup (async with) and one for the checkpointer
        assert mock_connect.call_count == 2
        mock_connect.assert_any_call(expected_path)


# ---------------------------------------------------------------------------
# Test 4: build_graph propagates OSError raised by aiosqlite.connect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_graph_propagates_aiosqlite_connect_error(tmp_path: Path) -> None:
    settings = _mock_settings(tmp_path)
    retriever = _mock_retriever()
    with (
        patch("src.graph.builder.aiosqlite.connect", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        await build_graph(settings=settings, retriever=retriever, llm=_mock_llm(), llm_4o=_mock_llm())
