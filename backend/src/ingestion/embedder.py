"""Async batch embedder using Azure OpenAI text-embedding-3-large."""

import asyncio

import structlog
from langchain_openai import AzureOpenAIEmbeddings

from src.config import Settings
from src.exceptions import EmbeddingError
from src.ingestion.models import ChunkedDocument

logger = structlog.get_logger(__name__)


class Embedder:
    """Embed chunks using Azure OpenAI, batching to respect rate limits.

    Chunks are split into batches of ``settings.embedding_batch_size`` and
    all batches are embedded concurrently via ``asyncio.gather``.
    """

    def __init__(self, settings: Settings) -> None:
        self._batch_size = settings.embedding_batch_size
        self._embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_embedding_deployment,
        )

    async def embed_chunks(self, chunks: list[ChunkedDocument]) -> list[ChunkedDocument]:
        """Embed all chunks and return them with the ``vector`` field populated.

        Raises ``EmbeddingError`` if the Azure call fails.
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
            results = await asyncio.gather(
                *[self._embeddings.aembed_documents(batch) for batch in batches]
            )
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
