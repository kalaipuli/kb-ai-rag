"""Unit tests for DenseRetriever — all Qdrant I/O is mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.exceptions import RetrievalError
from src.retrieval.dense import DenseRetriever
from src.retrieval.models import RetrievalResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_settings() -> MagicMock:
    s = MagicMock()
    s.qdrant_url = "http://localhost:6333"
    s.qdrant_collection = "test_collection"
    return s


def _make_scored_point(
    chunk_id: str,
    score: float,
    title: str = "Sample title",
    text: str = "Full chunk text content",
) -> MagicMock:
    """Build a mock ScoredPoint as returned by qdrant_client.search."""
    payload: dict[str, object] = {
        "doc_id": "doc-1",
        "chunk_id": chunk_id,
        "source_path": "/tmp/a.txt",
        "filename": "a.txt",
        "file_type": "txt",
        "title": title,
        "text": text,
        "page_number": -1,
        "chunk_index": 0,
        "total_chunks": 2,
        "char_count": 20,
        "ingested_at": "2025-01-15T10:00:00Z",
        "tags": [],
    }
    point = MagicMock()
    point.id = chunk_id
    point.score = score
    point.payload = payload
    return point


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDenseRetriever:
    def test_search_returns_sorted_results(self) -> None:
        settings = _make_test_settings()
        with patch("src.retrieval.dense.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.search = AsyncMock(
                return_value=[
                    _make_scored_point("c1", 0.9, "First chunk"),
                    _make_scored_point("c2", 0.7, "Second chunk"),
                ]
            )
            mock_cls.return_value = mock_client

            retriever = DenseRetriever(settings)

            import asyncio

            results: list[RetrievalResult] = asyncio.get_event_loop().run_until_complete(
                retriever.search([0.1] * 3072, k=5)
            )

        assert len(results) == 2
        assert results[0].chunk_id == "c1"
        assert results[0].score == pytest.approx(0.9)
        assert results[1].chunk_id == "c2"
        assert results[1].score == pytest.approx(0.7)

    def test_search_empty_returns_empty_list(self) -> None:
        settings = _make_test_settings()
        with patch("src.retrieval.dense.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.search = AsyncMock(return_value=[])
            mock_cls.return_value = mock_client

            retriever = DenseRetriever(settings)

            import asyncio

            results = asyncio.get_event_loop().run_until_complete(
                retriever.search([0.0] * 3072, k=10)
            )

        assert results == []

    def test_search_raises_retrieval_error_on_failure(self) -> None:
        settings = _make_test_settings()
        with patch("src.retrieval.dense.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.search = AsyncMock(side_effect=RuntimeError("connection refused"))
            mock_cls.return_value = mock_client

            retriever = DenseRetriever(settings)

            import asyncio

            with pytest.raises(RetrievalError, match="Qdrant search failed") as exc_info:
                asyncio.get_event_loop().run_until_complete(retriever.search([0.0] * 3072, k=5))

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, RuntimeError)

    def test_search_raises_retrieval_error_on_connection_error(self) -> None:
        settings = _make_test_settings()
        with patch("src.retrieval.dense.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.search = AsyncMock(side_effect=ConnectionError("timeout"))
            mock_cls.return_value = mock_client

            retriever = DenseRetriever(settings)

            import asyncio

            with pytest.raises(RetrievalError, match="Qdrant search failed") as exc_info:
                asyncio.get_event_loop().run_until_complete(retriever.search([0.0] * 3072, k=5))

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_search_result_text_comes_from_payload_text_field(self) -> None:
        """F01: RetrievalResult.text must use the full 'text' payload key, not 'title'."""
        settings = _make_test_settings()
        with patch("src.retrieval.dense.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.search = AsyncMock(
                return_value=[
                    _make_scored_point("c1", 0.9, title="Short title", text="Full body text here"),
                ]
            )
            mock_cls.return_value = mock_client

            retriever = DenseRetriever(settings)

            import asyncio

            results: list[RetrievalResult] = asyncio.get_event_loop().run_until_complete(
                retriever.search([0.1] * 3072, k=5)
            )

        assert results[0].text == "Full body text here"
        assert results[0].chunk_id == "c1"

    def test_search_passes_filters_to_client(self) -> None:
        settings = _make_test_settings()
        with patch("src.retrieval.dense.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.search = AsyncMock(return_value=[])
            mock_cls.return_value = mock_client

            retriever = DenseRetriever(settings)

            import asyncio

            asyncio.get_event_loop().run_until_complete(
                retriever.search([0.0] * 3072, k=5, filters={"file_type": "pdf"})
            )

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["query_filter"] is not None
        must_conditions = call_kwargs["query_filter"].must
        assert len(must_conditions) == 1
        assert must_conditions[0].key == "file_type"
        assert must_conditions[0].match.value == "pdf"
