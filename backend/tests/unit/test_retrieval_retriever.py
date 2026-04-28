"""Unit tests for HybridRetriever — all pipeline stages are mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingestion.models import ChunkMetadata
from src.retrieval.models import RetrievalResult
from src.retrieval.retriever import HybridRetriever

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _make_result(chunk_id: str, score: float = 0.5) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        text="text",
        metadata=_make_metadata(chunk_id),
        score=score,
    )


def _make_settings(
    retrieval_top_k: int = 10,
    reranker_top_k: int = 5,
    rrf_k: int = 60,
    reranker_model: str = "test-model",
) -> MagicMock:
    s = MagicMock()
    s.qdrant_url = "http://localhost:6333"
    s.qdrant_collection = "test_collection"
    s.retrieval_top_k = retrieval_top_k
    s.reranker_top_k = reranker_top_k
    s.rrf_k = rrf_k
    s.reranker_model = reranker_model
    return s


def _make_embedder(vector: list[float] | None = None) -> MagicMock:
    v = vector or [0.1] * 3072
    embedder = MagicMock()
    embedder.embed_query = AsyncMock(return_value=v)
    return embedder


def _make_bm25_store() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHybridRetriever:
    def test_retrieve_calls_all_pipeline_stages(self) -> None:
        settings = _make_settings()
        embedder = _make_embedder()
        bm25_store = _make_bm25_store()

        dense_results = [_make_result("d1", 0.9)]
        sparse_results = [_make_result("s1", 1.5)]
        reranked_results = [_make_result("d1", 3.0)]

        with (
            patch("src.retrieval.retriever.DenseRetriever") as mock_dense_cls,
            patch("src.retrieval.retriever.SparseRetriever") as mock_sparse_cls,
            patch("src.retrieval.retriever.CrossEncoderReranker") as mock_reranker_cls,
        ):
            mock_dense = MagicMock()
            mock_dense.search = AsyncMock(return_value=dense_results)
            mock_dense_cls.return_value = mock_dense

            mock_sparse = MagicMock()
            mock_sparse.search = MagicMock(return_value=sparse_results)
            mock_sparse_cls.return_value = mock_sparse

            mock_reranker = MagicMock()
            mock_reranker.rerank = MagicMock(return_value=reranked_results)
            mock_reranker_cls.return_value = mock_reranker

            retriever = HybridRetriever(settings, bm25_store, embedder)

            import asyncio

            asyncio.get_event_loop().run_until_complete(
                retriever.retrieve("test query", mode="hybrid")
            )

        embedder.embed_query.assert_called_once_with("test query")
        mock_dense.search.assert_called_once()
        mock_sparse.search.assert_called_once()
        mock_reranker.rerank.assert_called_once()

    def test_retrieve_returns_reranked_results(self) -> None:
        settings = _make_settings()
        embedder = _make_embedder()
        bm25_store = _make_bm25_store()

        expected = [_make_result("r1", 4.2), _make_result("r2", 2.1)]

        with (
            patch("src.retrieval.retriever.DenseRetriever") as mock_dense_cls,
            patch("src.retrieval.retriever.SparseRetriever") as mock_sparse_cls,
            patch("src.retrieval.retriever.CrossEncoderReranker") as mock_reranker_cls,
        ):
            mock_dense = MagicMock()
            mock_dense.search = AsyncMock(return_value=[_make_result("r1")])
            mock_dense_cls.return_value = mock_dense

            mock_sparse = MagicMock()
            mock_sparse.search = MagicMock(return_value=[_make_result("r2")])
            mock_sparse_cls.return_value = mock_sparse

            mock_reranker = MagicMock()
            mock_reranker.rerank = MagicMock(return_value=expected)
            mock_reranker_cls.return_value = mock_reranker

            retriever = HybridRetriever(settings, bm25_store, embedder)

            import asyncio

            results = asyncio.get_event_loop().run_until_complete(retriever.retrieve("query"))

        assert results is expected

    def test_retrieve_passes_filters_to_dense(self) -> None:
        settings = _make_settings()
        embedder = _make_embedder()
        bm25_store = _make_bm25_store()
        filters = {"file_type": "pdf"}

        with (
            patch("src.retrieval.retriever.DenseRetriever") as mock_dense_cls,
            patch("src.retrieval.retriever.SparseRetriever") as mock_sparse_cls,
            patch("src.retrieval.retriever.CrossEncoderReranker") as mock_reranker_cls,
        ):
            mock_dense = MagicMock()
            mock_dense.search = AsyncMock(return_value=[])
            mock_dense_cls.return_value = mock_dense

            mock_sparse = MagicMock()
            mock_sparse.search = MagicMock(return_value=[])
            mock_sparse_cls.return_value = mock_sparse

            mock_reranker = MagicMock()
            mock_reranker.rerank = MagicMock(return_value=[])
            mock_reranker_cls.return_value = mock_reranker

            retriever = HybridRetriever(settings, bm25_store, embedder)

            import asyncio

            asyncio.get_event_loop().run_until_complete(
                retriever.retrieve("query", filters=filters)
            )

        call_kwargs = mock_dense.search.call_args.kwargs
        assert call_kwargs["filters"] == filters

    def test_retrieve_k_override_hybrid_mode(self) -> None:
        settings = _make_settings(retrieval_top_k=10)
        embedder = _make_embedder()
        bm25_store = _make_bm25_store()

        with (
            patch("src.retrieval.retriever.DenseRetriever") as mock_dense_cls,
            patch("src.retrieval.retriever.SparseRetriever") as mock_sparse_cls,
            patch("src.retrieval.retriever.CrossEncoderReranker") as mock_reranker_cls,
        ):
            mock_dense = MagicMock()
            mock_dense.search = AsyncMock(return_value=[])
            mock_dense_cls.return_value = mock_dense

            mock_sparse = MagicMock()
            mock_sparse.search = MagicMock(return_value=[])
            mock_sparse_cls.return_value = mock_sparse

            mock_reranker = MagicMock()
            mock_reranker.rerank = MagicMock(return_value=[])
            mock_reranker_cls.return_value = mock_reranker

            retriever = HybridRetriever(settings, bm25_store, embedder)

            import asyncio

            asyncio.get_event_loop().run_until_complete(
                retriever.retrieve("query", k=3, mode="hybrid")
            )

        dense_call_kwargs = mock_dense.search.call_args.kwargs
        assert dense_call_kwargs["k"] == 3

        sparse_call_args = mock_sparse.search.call_args
        assert sparse_call_args.kwargs.get("k") == 3

    def test_retrieve_dense_mode_skips_sparse_and_rrf(self) -> None:
        settings = _make_settings()
        embedder = _make_embedder()
        bm25_store = _make_bm25_store()

        dense_results = [_make_result("d1", 0.9), _make_result("d2", 0.7)]
        reranked_results = [_make_result("d1", 3.0)]

        with (
            patch("src.retrieval.retriever.DenseRetriever") as mock_dense_cls,
            patch("src.retrieval.retriever.SparseRetriever") as mock_sparse_cls,
            patch("src.retrieval.retriever.CrossEncoderReranker") as mock_reranker_cls,
            patch("src.retrieval.retriever.reciprocal_rank_fusion") as mock_rrf,
        ):
            mock_dense = MagicMock()
            mock_dense.search = AsyncMock(return_value=dense_results)
            mock_dense_cls.return_value = mock_dense

            mock_sparse = MagicMock()
            mock_sparse.search = MagicMock(return_value=[])
            mock_sparse_cls.return_value = mock_sparse

            mock_reranker = MagicMock()
            mock_reranker.rerank = MagicMock(return_value=reranked_results)
            mock_reranker_cls.return_value = mock_reranker

            retriever = HybridRetriever(settings, bm25_store, embedder)

            import asyncio

            results = asyncio.get_event_loop().run_until_complete(
                retriever.retrieve("query", mode="dense")
            )

        mock_dense.search.assert_called_once()
        mock_sparse.search.assert_not_called()
        mock_rrf.assert_not_called()
        # reranker receives the raw dense results, not an RRF-fused list
        mock_reranker.rerank.assert_called_once_with(
            "query", dense_results, top_k=settings.reranker_top_k
        )
        assert results is reranked_results

    def test_retrieve_raises_retrieval_error_on_embedding_failure(self) -> None:
        from src.exceptions import EmbeddingError, RetrievalError

        settings = _make_settings()
        bm25_store = _make_bm25_store()
        embedder = MagicMock()
        embedder.embed_query = AsyncMock(side_effect=EmbeddingError("Azure down"))

        with (
            patch("src.retrieval.retriever.DenseRetriever"),
            patch("src.retrieval.retriever.SparseRetriever"),
            patch("src.retrieval.retriever.CrossEncoderReranker"),
        ):
            retriever = HybridRetriever(settings, bm25_store, embedder)

            import asyncio

            with pytest.raises(RetrievalError, match="Query embedding failed"):
                asyncio.get_event_loop().run_until_complete(retriever.retrieve("query"))

    def test_retrieve_returns_empty_when_no_results_found(self) -> None:
        settings = _make_settings()
        embedder = _make_embedder()
        bm25_store = _make_bm25_store()

        with (
            patch("src.retrieval.retriever.DenseRetriever") as mock_dense_cls,
            patch("src.retrieval.retriever.SparseRetriever") as mock_sparse_cls,
            patch("src.retrieval.retriever.CrossEncoderReranker") as mock_reranker_cls,
        ):
            mock_dense = MagicMock()
            mock_dense.search = AsyncMock(return_value=[])
            mock_dense_cls.return_value = mock_dense

            mock_sparse = MagicMock()
            mock_sparse.search = MagicMock(return_value=[])
            mock_sparse_cls.return_value = mock_sparse

            mock_reranker = MagicMock()
            mock_reranker.rerank = MagicMock(return_value=[])
            mock_reranker_cls.return_value = mock_reranker

            retriever = HybridRetriever(settings, bm25_store, embedder)

            import asyncio

            results = asyncio.get_event_loop().run_until_complete(retriever.retrieve("empty query"))

        assert results == []

    def test_close_propagates_to_dense(self) -> None:
        settings = _make_settings()
        embedder = _make_embedder()
        bm25_store = _make_bm25_store()

        with (
            patch("src.retrieval.retriever.DenseRetriever") as mock_dense_cls,
            patch("src.retrieval.retriever.SparseRetriever"),
            patch("src.retrieval.retriever.CrossEncoderReranker"),
        ):
            mock_dense = MagicMock()
            mock_dense.close = AsyncMock()
            mock_dense_cls.return_value = mock_dense

            retriever = HybridRetriever(settings, bm25_store, embedder)

            import asyncio

            asyncio.get_event_loop().run_until_complete(retriever.close())

        mock_dense.close.assert_called_once()
