"""Unit tests for Embedder.

Azure OpenAI calls are mocked so no network I/O occurs.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Settings
from src.exceptions import EmbeddingError
from src.ingestion.embedder import Embedder
from src.ingestion.models import ChunkedDocument, ChunkMetadata


def _make_settings(batch_size: int = 2) -> Settings:
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="key",
        api_key="apikey",
        data_dir="/tmp",
        chunk_size=1000,
        chunk_overlap=200,
        embedding_batch_size=batch_size,
        bm25_index_path="/tmp/bm25.pkl",
    )


def _make_chunk(text: str, index: int = 0) -> ChunkedDocument:
    meta: ChunkMetadata = {
        "doc_id": "doc-1",
        "chunk_id": f"chunk-{index}",
        "source_path": "/tmp/a.txt",
        "filename": "a.txt",
        "file_type": "txt",
        "title": text[:80],
        "page_number": -1,
        "chunk_index": index,
        "total_chunks": 5,
        "char_count": len(text),
        "ingested_at": "2025-01-15T10:00:00Z",
        "tags": [],
    }
    return ChunkedDocument(text=text, metadata=meta)


class TestEmbedderHappyPath:
    async def test_embed_returns_chunks_with_vectors(self) -> None:
        chunks = [_make_chunk("text one", 0), _make_chunk("text two", 1)]
        fake_vectors = [[0.1, 0.2], [0.3, 0.4]]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_documents = AsyncMock(return_value=fake_vectors)
            mock_cls.return_value = mock_instance

            embedder = Embedder(_make_settings(batch_size=10))
            result = await embedder.embed_chunks(chunks)

        assert len(result) == 2
        assert result[0].vector == [0.1, 0.2]
        assert result[1].vector == [0.3, 0.4]

    async def test_original_chunks_not_mutated(self) -> None:
        chunks = [_make_chunk("some text here", 0)]
        fake_vectors = [[0.5, 0.6, 0.7]]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_documents = AsyncMock(return_value=fake_vectors)
            mock_cls.return_value = mock_instance

            embedder = Embedder(_make_settings(batch_size=10))
            result = await embedder.embed_chunks(chunks)

        assert chunks[0].vector == []  # original unchanged
        assert result[0].vector == [0.5, 0.6, 0.7]

    async def test_empty_input_returns_empty(self) -> None:
        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings"):
            embedder = Embedder(_make_settings())
            result = await embedder.embed_chunks([])
        assert result == []


class TestEmbedderBatching:
    async def test_batches_split_correctly(self) -> None:
        """With batch_size=2 and 5 chunks, expect 3 batches (2+2+1)."""
        chunks = [_make_chunk(f"text {i}", i) for i in range(5)]
        # Each batch returns vectors for its items
        batch_vectors_1 = [[float(i)] for i in range(2)]
        batch_vectors_2 = [[float(i)] for i in range(2, 4)]
        batch_vectors_3 = [[4.0]]

        call_results = [batch_vectors_1, batch_vectors_2, batch_vectors_3]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_documents = AsyncMock(side_effect=call_results)
            mock_cls.return_value = mock_instance

            embedder = Embedder(_make_settings(batch_size=2))
            result = await embedder.embed_chunks(chunks)

        assert mock_instance.aembed_documents.call_count == 3
        assert len(result) == 5

    async def test_single_batch_when_chunks_fit(self) -> None:
        chunks = [_make_chunk(f"text {i}", i) for i in range(3)]
        fake_vectors = [[float(i)] for i in range(3)]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_documents = AsyncMock(return_value=fake_vectors)
            mock_cls.return_value = mock_instance

            embedder = Embedder(_make_settings(batch_size=10))
            await embedder.embed_chunks(chunks)

        assert mock_instance.aembed_documents.call_count == 1


class TestEmbedderErrorPath:
    async def test_raises_embedding_error_on_azure_failure(self) -> None:
        chunks = [_make_chunk("some text", 0)]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_documents = AsyncMock(
                side_effect=RuntimeError("Rate limit exceeded")
            )
            mock_cls.return_value = mock_instance

            embedder = Embedder(_make_settings(batch_size=10))
            with pytest.raises(EmbeddingError, match="Rate limit exceeded"):
                await embedder.embed_chunks(chunks)
