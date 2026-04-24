"""Unit tests for QdrantVectorStore.

AsyncQdrantClient is mocked — no real Qdrant connection is made.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.exceptions import IngestionError
from src.ingestion.models import ChunkedDocument, ChunkMetadata
from src.ingestion.vector_store import QdrantVectorStore


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


def _make_chunk(chunk_id: str, vector: list[float]) -> ChunkedDocument:
    meta: ChunkMetadata = {
        "doc_id": "doc-1",
        "chunk_id": chunk_id,
        "source_path": "/tmp/a.pdf",
        "filename": "a.pdf",
        "file_type": "pdf",
        "title": "A title",
        "page_number": 0,
        "chunk_index": 0,
        "total_chunks": 1,
        "char_count": 200,
        "ingested_at": "2025-01-15T10:00:00Z",
        "tags": [],
    }
    return ChunkedDocument(text="some text content here", metadata=meta, vector=vector)


# ---------------------------------------------------------------------------
# ensure_collection
# ---------------------------------------------------------------------------


class TestEnsureCollection:
    async def test_creates_collection_when_absent(self) -> None:
        settings = _make_settings()

        with patch("src.ingestion.vector_store.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            # No existing collections
            collections_response = MagicMock()
            collections_response.collections = []
            mock_client.get_collections = AsyncMock(return_value=collections_response)
            mock_client.create_collection = AsyncMock()
            mock_client.create_payload_index = AsyncMock()
            mock_client.close = AsyncMock()
            mock_cls.return_value = mock_client

            store = QdrantVectorStore(settings=settings)
            await store.ensure_collection()

        mock_client.create_collection.assert_awaited_once()
        call_kwargs = mock_client.create_collection.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_col"

    async def test_skips_creation_when_collection_exists(self) -> None:
        settings = _make_settings()

        with patch("src.ingestion.vector_store.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            existing_col = MagicMock()
            existing_col.name = "test_col"
            collections_response = MagicMock()
            collections_response.collections = [existing_col]
            mock_client.get_collections = AsyncMock(return_value=collections_response)
            mock_client.create_collection = AsyncMock()
            mock_client.close = AsyncMock()
            mock_cls.return_value = mock_client

            store = QdrantVectorStore(settings=settings)
            await store.ensure_collection()

        mock_client.create_collection.assert_not_awaited()

    async def test_payload_indexes_created(self) -> None:
        settings = _make_settings()

        with patch("src.ingestion.vector_store.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            collections_response = MagicMock()
            collections_response.collections = []
            mock_client.get_collections = AsyncMock(return_value=collections_response)
            mock_client.create_collection = AsyncMock()
            mock_client.create_payload_index = AsyncMock()
            mock_client.close = AsyncMock()
            mock_cls.return_value = mock_client

            store = QdrantVectorStore(settings=settings)
            await store.ensure_collection()

        assert mock_client.create_payload_index.await_count == 4
        indexed_fields = {
            call.kwargs["field_name"] for call in mock_client.create_payload_index.call_args_list
        }
        assert indexed_fields == {"filename", "file_type", "doc_id", "ingested_at"}


# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------


class TestUpsert:
    async def test_upsert_calls_client_with_correct_payload(self) -> None:
        settings = _make_settings()
        vec = [0.1, 0.2, 0.3]
        chunk = _make_chunk("chunk-uuid-1", vec)

        with patch("src.ingestion.vector_store.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.upsert = AsyncMock()
            mock_client.close = AsyncMock()
            mock_cls.return_value = mock_client

            store = QdrantVectorStore(settings=settings)
            await store.upsert([chunk])

        mock_client.upsert.assert_awaited_once()
        call_kwargs = mock_client.upsert.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_col"
        points = call_kwargs["points"]
        assert len(points) == 1
        assert points[0].id == "chunk-uuid-1"
        assert points[0].vector == vec
        # Full payload must be present
        payload = points[0].payload
        assert payload["doc_id"] == "doc-1"
        assert payload["filename"] == "a.pdf"
        assert payload["file_type"] == "pdf"

    async def test_upsert_no_chunks_skips_call(self) -> None:
        settings = _make_settings()

        with patch("src.ingestion.vector_store.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.upsert = AsyncMock()
            mock_client.close = AsyncMock()
            mock_cls.return_value = mock_client

            store = QdrantVectorStore(settings=settings)
            await store.upsert([])

        mock_client.upsert.assert_not_awaited()

    async def test_upsert_raises_ingestion_error_on_failure(self) -> None:
        settings = _make_settings()
        chunk = _make_chunk("chunk-uuid-2", [1.0, 2.0])

        with patch("src.ingestion.vector_store.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.upsert = AsyncMock(side_effect=RuntimeError("Qdrant down"))
            mock_client.close = AsyncMock()
            mock_cls.return_value = mock_client

            store = QdrantVectorStore(settings=settings)
            with pytest.raises(IngestionError, match="Qdrant down"):
                await store.upsert([chunk])

    async def test_upsert_raises_if_chunk_has_no_vector(self) -> None:
        settings = _make_settings()
        chunk = _make_chunk("chunk-no-vec", [])  # empty vector

        with patch("src.ingestion.vector_store.AsyncQdrantClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.upsert = AsyncMock()
            mock_client.close = AsyncMock()
            mock_cls.return_value = mock_client

            store = QdrantVectorStore(settings=settings)
            with pytest.raises(IngestionError, match="no vector"):
                await store.upsert([chunk])
