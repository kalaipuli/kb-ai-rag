"""Unit tests for run_pipeline.

All external dependencies (LocalFileLoader, DocumentSplitter, Embedder,
QdrantVectorStore, BM25Store) are mocked so no real I/O occurs.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.exceptions import EmbeddingError, IngestionError
from src.ingestion.models import ChunkedDocument, ChunkMetadata, Document
from src.ingestion.pipeline import PipelineResult, run_pipeline

pytestmark = pytest.mark.asyncio


def _make_settings() -> Settings:
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="key",
        api_key="apikey",
        data_dir="/tmp",
        chunk_size=1000,
        chunk_overlap=200,
        embedding_batch_size=16,
        bm25_index_path="/tmp/bm25.pkl",
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_col",
    )


def _make_doc(filename: str) -> Document:
    return Document(
        content="Some content that is long enough to be useful.",
        metadata={
            "doc_id": "doc-1",
            "source_path": f"/tmp/{filename}",
            "filename": filename,
            "file_type": "txt",
            "page_number": -1,
        },
    )


def _make_chunk(chunk_id: str) -> ChunkedDocument:
    meta: ChunkMetadata = {
        "doc_id": "doc-1",
        "chunk_id": chunk_id,
        "source_path": "/tmp/a.txt",
        "filename": "a.txt",
        "file_type": "txt",
        "title": "A title",
        "page_number": -1,
        "chunk_index": 0,
        "total_chunks": 1,
        "char_count": 200,
        "ingested_at": "2025-01-15T10:00:00Z",
        "tags": [],
    }
    return ChunkedDocument(text="some text content here", metadata=meta, vector=[0.1, 0.2])


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestRunPipelineHappyPath:
    async def test_all_stages_called_in_order(self) -> None:
        settings = _make_settings()
        docs = [_make_doc("a.txt"), _make_doc("b.txt")]
        chunks = [_make_chunk("c1"), _make_chunk("c2")]
        embedded = [_make_chunk("c1"), _make_chunk("c2")]

        call_order: list[str] = []

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            # Loader
            mock_loader = MagicMock()
            mock_loader.load = AsyncMock(side_effect=lambda: call_order.append("load") or docs)
            mock_loader_cls.return_value = mock_loader

            # Splitter
            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(
                side_effect=lambda d: call_order.append("split") or chunks
            )
            mock_splitter_cls.return_value = mock_splitter

            # Embedder
            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(
                side_effect=lambda c: call_order.append("embed") or embedded
            )
            mock_embedder_cls.return_value = mock_embedder

            # VectorStore
            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock(side_effect=lambda: call_order.append("ensure"))
            mock_vs.upsert = AsyncMock(side_effect=lambda c: call_order.append("upsert"))
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            # BM25Store
            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock(side_effect=lambda c: call_order.append("bm25_build"))
            mock_bm25.save = MagicMock(side_effect=lambda: call_order.append("bm25_save"))
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert call_order == [
            "load",
            "split",
            "embed",
            "ensure",
            "upsert",
            "bm25_build",
            "bm25_save",
        ]
        assert isinstance(result, PipelineResult)
        assert result.docs_processed == 2
        assert result.chunks_created == 2
        assert result.errors == []

    async def test_pipeline_result_has_positive_duration(self) -> None:
        settings = _make_settings()
        docs = [_make_doc("doc.txt")]
        chunks = [_make_chunk("c1")]

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.load = AsyncMock(return_value=docs)
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=chunks)
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(return_value=chunks)
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            mock_vs.upsert = AsyncMock()
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.save = MagicMock()
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Empty / edge cases
# ---------------------------------------------------------------------------


class TestRunPipelineEdgeCases:
    async def test_empty_data_dir_returns_zero_counts(self) -> None:
        settings = _make_settings()

        with patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.load = AsyncMock(return_value=[])
            mock_loader_cls.return_value = mock_loader

            result = await run_pipeline(Path("/tmp/empty"), settings)

        assert result.docs_processed == 0
        assert result.chunks_created == 0
        assert result.errors == []

    async def test_load_failure_adds_error_and_returns(self) -> None:
        settings = _make_settings()

        with patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.load = AsyncMock(side_effect=RuntimeError("disk error"))
            mock_loader_cls.return_value = mock_loader

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert result.docs_processed == 0
        assert len(result.errors) == 1
        assert "disk error" in result.errors[0]

    async def test_embed_failure_adds_error(self) -> None:
        settings = _make_settings()
        docs = [_make_doc("doc.txt")]
        chunks = [_make_chunk("c1")]

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.load = AsyncMock(return_value=docs)
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=chunks)
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(
                side_effect=EmbeddingError("Azure quota exceeded")
            )
            mock_embedder_cls.return_value = mock_embedder

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert len(result.errors) == 1
        assert "Azure quota exceeded" in result.errors[0]
        # docs were loaded and chunks created even though embedding failed
        assert result.docs_processed == 1
        assert result.chunks_created == 1

    async def test_upsert_failure_adds_error_and_skips_bm25(self) -> None:
        settings = _make_settings()
        docs = [_make_doc("a.txt")]
        chunks = [_make_chunk("c1")]

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.load = AsyncMock(return_value=docs)
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=chunks)
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(return_value=chunks)
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            mock_vs.upsert = AsyncMock(side_effect=IngestionError("upsert boom"))
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.save = MagicMock()
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert len(result.errors) == 1
        assert "upsert boom" in result.errors[0]
        assert mock_bm25.build.call_count == 0
        assert mock_bm25.save.call_count == 0

    async def test_bm25_save_failure_adds_error(self) -> None:
        settings = _make_settings()
        docs = [_make_doc("a.txt")]
        chunks = [_make_chunk("c1")]

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.load = AsyncMock(return_value=docs)
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=chunks)
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(return_value=chunks)
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            mock_vs.upsert = AsyncMock()
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.save = MagicMock(side_effect=IngestionError("bm25 save failed"))
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert len(result.errors) == 1
        assert "bm25 save failed" in result.errors[0]
