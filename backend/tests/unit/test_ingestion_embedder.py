"""Unit tests for Embedder.

Azure OpenAI calls are mocked so no network I/O occurs.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import RateLimitError
from tenacity import RetryCallState

from src.config import Settings
from src.exceptions import EmbeddingError
from src.ingestion.embedder import Embedder, _RetryAfterWait
from src.ingestion.models import ChunkedDocument, ChunkMetadata

pytestmark = pytest.mark.asyncio


def _make_settings(
    batch_size: int = 2,
    max_concurrency: int = 3,
    inter_batch_delay: float = 0.0,
) -> Settings:
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="key",
        api_key="apikey",
        data_dir="/tmp",
        chunk_size=1000,
        chunk_overlap=200,
        embedding_batch_size=batch_size,
        embedding_max_concurrency=max_concurrency,
        embedding_inter_batch_delay=inter_batch_delay,
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

    async def test_inter_batch_delay_called_once_per_batch(self) -> None:
        """asyncio.sleep must be called once per batch to enforce the inter-batch delay."""
        chunks = [_make_chunk(f"text {i}", i) for i in range(4)]
        call_results = [[[float(i)] for i in range(2)], [[float(i)] for i in range(2, 4)]]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_documents = AsyncMock(side_effect=call_results)
            mock_cls.return_value = mock_instance

            with patch("src.ingestion.embedder.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                embedder = Embedder(_make_settings(batch_size=2, inter_batch_delay=0.5))
                await embedder.embed_chunks(chunks)

        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.5)
        assert mock_instance.aembed_documents.call_count == 2


def _make_rate_limit_exc(retry_after: str | None = None) -> RateLimitError:
    """Build a RateLimitError whose response headers optionally include Retry-After."""
    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["retry-after"] = retry_after
    response = MagicMock(status_code=429, headers=headers)
    return RateLimitError("rate limit", response=response, body={})


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

    async def test_retries_on_rate_limit_then_succeeds(self) -> None:
        """A single 429 should be retried and ultimately succeed."""
        chunks = [_make_chunk("some text", 0)]
        fake_vectors = [[0.1, 0.2]]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_documents = AsyncMock(
                side_effect=[_make_rate_limit_exc(), fake_vectors]
            )
            mock_cls.return_value = mock_instance

            with patch("src.ingestion.embedder._FALLBACK_WAIT", return_value=0):
                embedder = Embedder(_make_settings(batch_size=10))
                result = await embedder.embed_chunks(chunks)

        assert mock_instance.aembed_documents.call_count == 2
        assert result[0].vector == [0.1, 0.2]

    async def test_raises_after_max_retries_on_rate_limit(self) -> None:
        """Persistent 429s should bubble up as EmbeddingError after 5 attempts."""
        chunks = [_make_chunk("some text", 0)]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_documents = AsyncMock(side_effect=_make_rate_limit_exc())
            mock_cls.return_value = mock_instance

            with patch("src.ingestion.embedder._FALLBACK_WAIT", return_value=0):
                embedder = Embedder(_make_settings(batch_size=10))
                with pytest.raises(EmbeddingError):
                    await embedder.embed_chunks(chunks)

        assert mock_instance.aembed_documents.call_count == 5

    async def test_retry_after_header_used_as_wait_duration(self) -> None:
        """_RetryAfterWait must return the Retry-After value when the header is present."""
        wait = _RetryAfterWait()
        exc = _make_rate_limit_exc(retry_after="7")

        outcome = MagicMock()
        outcome.exception.return_value = exc
        retry_state = MagicMock(spec=RetryCallState)
        retry_state.outcome = outcome

        assert wait(retry_state) == 7.0

    async def test_retry_after_header_absent_falls_back_to_exponential(self) -> None:
        """_RetryAfterWait must delegate to _FALLBACK_WAIT when the header is absent."""
        wait = _RetryAfterWait()
        exc = _make_rate_limit_exc(retry_after=None)

        outcome = MagicMock()
        outcome.exception.return_value = exc
        retry_state = MagicMock(spec=RetryCallState)
        retry_state.outcome = outcome

        with patch("src.ingestion.embedder._FALLBACK_WAIT", return_value=10.0) as mock_fallback:
            result = wait(retry_state)

        mock_fallback.assert_called_once_with(retry_state)
        assert result == 10.0


class TestEmbedQueryRetry:
    async def test_embed_query_retries_on_rate_limit_then_succeeds(self) -> None:
        """embed_query must retry on 429 and return the vector on success."""
        fake_vector = [0.1, 0.2, 0.3]

        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_query = AsyncMock(
                side_effect=[_make_rate_limit_exc(), fake_vector]
            )
            mock_cls.return_value = mock_instance

            with patch("src.ingestion.embedder._FALLBACK_WAIT", return_value=0):
                embedder = Embedder(_make_settings())
                result = await embedder.embed_query("hello world")

        assert mock_instance.aembed_query.call_count == 2
        assert result == fake_vector

    async def test_embed_query_raises_embedding_error_after_max_retries(self) -> None:
        """embed_query must raise EmbeddingError when all retries are exhausted."""
        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_query = AsyncMock(side_effect=_make_rate_limit_exc())
            mock_cls.return_value = mock_instance

            with patch("src.ingestion.embedder._FALLBACK_WAIT", return_value=0):
                embedder = Embedder(_make_settings())
                with pytest.raises(EmbeddingError):
                    await embedder.embed_query("hello world")

        assert mock_instance.aembed_query.call_count == 5

    async def test_embed_query_raises_embedding_error_on_non_rate_limit_exc(self) -> None:
        """embed_query must not retry generic errors, just wrap them in EmbeddingError."""
        with patch("src.ingestion.embedder.AzureOpenAIEmbeddings") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.aembed_query = AsyncMock(side_effect=RuntimeError("network down"))
            mock_cls.return_value = mock_instance

            embedder = Embedder(_make_settings())
            with pytest.raises(EmbeddingError, match="network down"):
                await embedder.embed_query("hello world")

        assert mock_instance.aembed_query.call_count == 1
