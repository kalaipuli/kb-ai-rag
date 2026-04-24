"""Unit tests for CrossEncoderReranker — CrossEncoder is mocked."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.ingestion.models import ChunkMetadata
from src.retrieval.models import RetrievalResult
from src.retrieval.reranker import CrossEncoderReranker


def _make_metadata(chunk_id: str) -> ChunkMetadata:
    return ChunkMetadata(
        doc_id="doc-1",
        chunk_id=chunk_id,
        source_path="/tmp/a.txt",
        filename="a.txt",
        file_type="txt",
        title="title",
        page_number=-1,
        chunk_index=0,
        total_chunks=1,
        char_count=10,
        ingested_at="2025-01-15T10:00:00Z",
        tags=[],
    )


def _make_result(chunk_id: str, score: float = 0.5, text: str = "text") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        text=text,
        metadata=_make_metadata(chunk_id),
        score=score,
    )


class TestCrossEncoderReranker:
    def test_rerank_returns_top_k_sorted_by_score(self) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_cls:
            mock_model = MagicMock()
            # Assign scores: A=0.2, B=0.9, C=0.5
            mock_model.predict.return_value = np.array([0.2, 0.9, 0.5])
            mock_cls.return_value = mock_model

            reranker = CrossEncoderReranker("test-model")
            results = [_make_result("A"), _make_result("B"), _make_result("C")]
            reranked = reranker.rerank("query", results, top_k=2)

        assert len(reranked) == 2
        assert reranked[0].chunk_id == "B"
        assert reranked[1].chunk_id == "C"

    def test_rerank_with_fewer_results_than_top_k(self) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_cls:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.array([0.8, 0.3])
            mock_cls.return_value = mock_model

            reranker = CrossEncoderReranker("test-model")
            results = [_make_result("A"), _make_result("B")]
            reranked = reranker.rerank("query", results, top_k=10)

        # Only 2 results available; should not error and return all 2
        assert len(reranked) == 2

    def test_rerank_updates_score_field(self) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_cls:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.array([3.14])
            mock_cls.return_value = mock_model

            reranker = CrossEncoderReranker("test-model")
            results = [_make_result("A", score=0.0)]
            reranked = reranker.rerank("query", results, top_k=5)

        assert reranked[0].score == pytest.approx(3.14)

    def test_rerank_updates_rank_field(self) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_cls:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.array([0.1, 0.9, 0.5])
            mock_cls.return_value = mock_model

            reranker = CrossEncoderReranker("test-model")
            results = [_make_result("A"), _make_result("B"), _make_result("C")]
            reranked = reranker.rerank("query", results, top_k=3)

        for position, result in enumerate(reranked):
            assert result.rank == position

    def test_rerank_empty_results_returns_empty(self) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_cls:
            mock_cls.return_value = MagicMock()
            reranker = CrossEncoderReranker("test-model")
            result = reranker.rerank("query", [], top_k=5)
        assert result == []
        # predict must NOT be called when input is empty
        mock_cls.return_value.predict.assert_not_called()
