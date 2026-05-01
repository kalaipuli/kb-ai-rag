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

FILE_A = Path("/tmp/data/a.txt")
FILE_B = Path("/tmp/data/b.txt")


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
        chunk_a = _make_chunk("c1")
        call_order: list[str] = []

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.discover_files = MagicMock(
                side_effect=lambda: call_order.append("discover") or [FILE_A, FILE_B]
            )
            mock_loader.doc_id_for = MagicMock(return_value="test-doc-id")
            mock_loader.load_one = AsyncMock(
                side_effect=lambda p: call_order.append("load_one") or [_make_doc(p.name)]
            )
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(
                side_effect=lambda _: call_order.append("split") or [chunk_a]
            )
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(
                side_effect=lambda _: call_order.append("embed") or [chunk_a]
            )
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock(side_effect=lambda: call_order.append("ensure"))
            mock_vs.doc_exists = AsyncMock(return_value=False)
            mock_vs.upsert = AsyncMock(side_effect=lambda _: call_order.append("upsert"))
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock(side_effect=lambda _: call_order.append("bm25_build"))
            mock_bm25.asave = AsyncMock(side_effect=lambda: call_order.append("bm25_save"))
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        # ensure_collection once, then per-file loop, then BM25
        assert call_order == [
            "discover",
            "ensure",
            "load_one",
            "split",
            "embed",
            "upsert",  # file A
            "load_one",
            "split",
            "embed",
            "upsert",  # file B
            "bm25_build",
            "bm25_save",
        ]
        assert isinstance(result, PipelineResult)
        assert result.docs_processed == 2
        assert result.chunks_created == 2
        assert result.errors == []

    async def test_pipeline_result_has_positive_duration(self) -> None:
        settings = _make_settings()
        chunk = _make_chunk("c1")

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.discover_files = MagicMock(return_value=[FILE_A])
            mock_loader.doc_id_for = MagicMock(return_value="test-doc-id")
            mock_loader.load_one = AsyncMock(return_value=[_make_doc("a.txt")])
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=[chunk])
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(return_value=[chunk])
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            mock_vs.doc_exists = AsyncMock(return_value=False)
            mock_vs.upsert = AsyncMock()
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.asave = AsyncMock()
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
            mock_loader.discover_files = MagicMock(return_value=[])
            mock_loader_cls.return_value = mock_loader

            result = await run_pipeline(Path("/tmp/empty"), settings)

        assert result.docs_processed == 0
        assert result.chunks_created == 0
        assert result.errors == []

    async def test_ensure_collection_failure_aborts_run(self) -> None:
        settings = _make_settings()

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.discover_files = MagicMock(return_value=[FILE_A])
            mock_loader_cls.return_value = mock_loader

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock(side_effect=RuntimeError("qdrant down"))
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert result.docs_processed == 0
        assert len(result.errors) == 1
        assert "qdrant down" in result.errors[0]

    async def test_one_file_embed_failure_continues_other_files(self) -> None:
        """Embedding failure on file A should not block file B from being processed."""
        settings = _make_settings()
        chunk_b = _make_chunk("c2")

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.discover_files = MagicMock(return_value=[FILE_A, FILE_B])
            mock_loader.doc_id_for = MagicMock(return_value="test-doc-id")
            mock_loader.load_one = AsyncMock(side_effect=lambda p: [_make_doc(p.name)])
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=[_make_chunk("c1")])
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(side_effect=[EmbeddingError("quota"), [chunk_b]])
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            mock_vs.doc_exists = AsyncMock(return_value=False)
            mock_vs.upsert = AsyncMock()
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.asave = AsyncMock()
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert len(result.errors) == 1
        assert "quota" in result.errors[0]
        assert result.chunks_created == 1  # file B succeeded
        assert mock_vs.upsert.call_count == 1
        assert mock_bm25.build.call_count == 1

    async def test_upsert_failure_skips_file_continues_others(self) -> None:
        """Upsert failure on file A should not block file B; BM25 built from file B only."""
        settings = _make_settings()
        chunk_b = _make_chunk("c2")

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.discover_files = MagicMock(return_value=[FILE_A, FILE_B])
            mock_loader.doc_id_for = MagicMock(return_value="test-doc-id")
            mock_loader.load_one = AsyncMock(side_effect=lambda p: [_make_doc(p.name)])
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=[_make_chunk("c1")])
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(side_effect=[[_make_chunk("c1")], [chunk_b]])
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            mock_vs.doc_exists = AsyncMock(return_value=False)
            mock_vs.upsert = AsyncMock(side_effect=[IngestionError("upsert boom"), None])
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.asave = AsyncMock()
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert len(result.errors) == 1
        assert "upsert boom" in result.errors[0]
        assert result.chunks_created == 1
        assert mock_bm25.build.call_count == 1  # built from file B

    async def test_all_upserts_fail_skips_bm25(self) -> None:
        settings = _make_settings()

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.discover_files = MagicMock(return_value=[FILE_A])
            mock_loader.doc_id_for = MagicMock(return_value="test-doc-id")
            mock_loader.load_one = AsyncMock(return_value=[_make_doc("a.txt")])
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=[_make_chunk("c1")])
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(return_value=[_make_chunk("c1")])
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            mock_vs.doc_exists = AsyncMock(return_value=False)
            mock_vs.upsert = AsyncMock(side_effect=IngestionError("upsert boom"))
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.asave = AsyncMock()
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert len(result.errors) == 1
        assert "upsert boom" in result.errors[0]
        assert mock_bm25.build.call_count == 0
        assert mock_bm25.asave.await_count == 0

    async def test_already_ingested_file_is_skipped(self) -> None:
        """Files whose doc_id already exists in Qdrant must not be re-embedded or re-upserted."""
        settings = _make_settings()
        chunk = _make_chunk("c1")

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.discover_files = MagicMock(return_value=[FILE_A, FILE_B])
            mock_loader.doc_id_for = MagicMock(side_effect=lambda p: f"doc-{p.name}")
            mock_loader.load_one = AsyncMock(side_effect=lambda p: [_make_doc(p.name)])
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=[chunk])
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(return_value=[chunk])
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            # FILE_A already exists; FILE_B does not
            mock_vs.doc_exists = AsyncMock(side_effect=[True, False])
            mock_vs.upsert = AsyncMock()
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.asave = AsyncMock()
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        # Only FILE_B should have been loaded, embedded, and upserted
        assert mock_loader.load_one.await_count == 1
        assert mock_embedder.embed_chunks.await_count == 1
        assert mock_vs.upsert.await_count == 1
        assert result.chunks_created == 1
        assert result.errors == []

    async def test_bm25_save_failure_adds_error(self) -> None:
        settings = _make_settings()
        chunk = _make_chunk("c1")

        with (
            patch("src.ingestion.pipeline.LocalFileLoader") as mock_loader_cls,
            patch("src.ingestion.pipeline.DocumentSplitter") as mock_splitter_cls,
            patch("src.ingestion.pipeline.Embedder") as mock_embedder_cls,
            patch("src.ingestion.pipeline.QdrantVectorStore") as mock_vs_cls,
            patch("src.ingestion.pipeline.BM25Store") as mock_bm25_cls,
        ):
            mock_loader = MagicMock()
            mock_loader.discover_files = MagicMock(return_value=[FILE_A])
            mock_loader.doc_id_for = MagicMock(return_value="test-doc-id")
            mock_loader.load_one = AsyncMock(return_value=[_make_doc("a.txt")])
            mock_loader_cls.return_value = mock_loader

            mock_splitter = MagicMock()
            mock_splitter.split = MagicMock(return_value=[chunk])
            mock_splitter_cls.return_value = mock_splitter

            mock_embedder = MagicMock()
            mock_embedder.embed_chunks = AsyncMock(return_value=[chunk])
            mock_embedder_cls.return_value = mock_embedder

            mock_vs = MagicMock()
            mock_vs.ensure_collection = AsyncMock()
            mock_vs.doc_exists = AsyncMock(return_value=False)
            mock_vs.upsert = AsyncMock()
            mock_vs.close = AsyncMock()
            mock_vs_cls.return_value = mock_vs

            mock_bm25 = MagicMock()
            mock_bm25.build = MagicMock()
            mock_bm25.asave = AsyncMock(side_effect=IngestionError("bm25 save failed"))
            mock_bm25_cls.return_value = mock_bm25

            result = await run_pipeline(Path("/tmp/data"), settings)

        assert len(result.errors) == 1
        assert "bm25 save failed" in result.errors[0]
