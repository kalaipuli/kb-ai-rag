"""Async batch embedder using Azure OpenAI text-embedding-3-large."""

import asyncio

import structlog
from langchain_openai import AzureOpenAIEmbeddings
from openai import RateLimitError
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)
from tenacity.wait import wait_base

from src.config import Settings
from src.exceptions import EmbeddingError
from src.ingestion.models import ChunkedDocument

logger = structlog.get_logger(__name__)

_FALLBACK_WAIT = wait_exponential(multiplier=1, min=4, max=60) + wait_random(0, 2)


class _RetryAfterWait(wait_base):
    """Tenacity wait strategy that honours Azure's Retry-After response header.

    Falls back to exponential + jitter when the header is absent so that
    concurrent batches don't all wake up at the same instant.
    """

    def __call__(self, retry_state: RetryCallState) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(exc, RateLimitError) and exc.response is not None:
            retry_after = exc.response.headers.get("retry-after")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
        return _FALLBACK_WAIT(retry_state)


_RETRY_WAIT = _RetryAfterWait()
_RETRY_STOP = stop_after_attempt(5)
_RETRY_CONDITION = retry_if_exception_type(RateLimitError)


class Embedder:
    """Embed chunks using Azure OpenAI, batching to respect rate limits.

    Chunks are split into batches of ``settings.embedding_batch_size``.
    Concurrent batch requests are capped by ``settings.embedding_max_concurrency``
    and each batch retries up to 5 times on HTTP 429, honouring the
    ``Retry-After`` header when present and falling back to exponential+jitter.
    """

    def __init__(self, settings: Settings) -> None:
        self._batch_size = settings.embedding_batch_size
        self._inter_batch_delay = settings.embedding_inter_batch_delay
        self._semaphore = asyncio.Semaphore(settings.embedding_max_concurrency)
        self._embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_embedding_deployment,
        )

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        """Embed one batch, honouring the concurrency semaphore and retrying on 429."""
        async for attempt in AsyncRetrying(
            retry=_RETRY_CONDITION,
            wait=_RETRY_WAIT,
            stop=_RETRY_STOP,
            reraise=True,
        ):
            with attempt:
                async with self._semaphore:
                    vectors = await self._embeddings.aembed_documents(batch)
                    await asyncio.sleep(self._inter_batch_delay)
                    return vectors
        return []  # unreachable; satisfies type checker

    async def embed_chunks(self, chunks: list[ChunkedDocument]) -> list[ChunkedDocument]:
        """Embed all chunks and return them with the ``vector`` field populated.

        Raises ``EmbeddingError`` if the Azure call fails after all retries.
        """
        if not chunks:
            return chunks

        texts = [chunk.text for chunk in chunks]
        batches = [texts[i : i + self._batch_size] for i in range(0, len(texts), self._batch_size)]

        logger.info(
            "embedding_start",
            total_chunks=len(chunks),
            batch_count=len(batches),
            batch_size=self._batch_size,
        )

        try:
            results = await asyncio.gather(*[self._embed_batch(batch) for batch in batches])
        except Exception as exc:
            logger.error("embedding_failed", error=str(exc))
            raise EmbeddingError(f"Azure OpenAI embedding request failed: {exc}") from exc

        flat_vectors: list[list[float]] = [vec for batch_result in results for vec in batch_result]

        if len(flat_vectors) != len(chunks):
            raise EmbeddingError(
                f"Embedding count mismatch: expected {len(chunks)}, got {len(flat_vectors)}"
            )

        embedded: list[ChunkedDocument] = []
        for chunk, vector in zip(chunks, flat_vectors, strict=True):
            embedded.append(chunk.model_copy(update={"vector": vector}))

        logger.info("embedding_complete", embedded_count=len(embedded))
        return embedded

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string for retrieval."""
        try:
            async for attempt in AsyncRetrying(
                retry=_RETRY_CONDITION,
                wait=_RETRY_WAIT,
                stop=_RETRY_STOP,
                reraise=True,
            ):
                with attempt:
                    return await self._embeddings.aembed_query(query)
            return []  # unreachable; satisfies type checker
        except RateLimitError as exc:
            logger.error("query_embedding_failed", error=str(exc))
            raise EmbeddingError(f"Azure OpenAI query embedding failed: {exc}") from exc
        except Exception as exc:
            logger.error("query_embedding_failed", error=str(exc))
            raise EmbeddingError(f"Azure OpenAI query embedding failed: {exc}") from exc
