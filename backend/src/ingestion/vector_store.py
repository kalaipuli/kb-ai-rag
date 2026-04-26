"""Qdrant vector store: collection management and chunk upsert."""

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    HnswConfigDiff,
    MatchValue,
    OptimizersConfigDiff,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from src.config import Settings
from src.exceptions import IngestionError
from src.ingestion.models import ChunkedDocument

logger = structlog.get_logger(__name__)


class QdrantVectorStore:
    """Manage the Qdrant collection and upsert embedded chunks.

    The collection is created with COSINE distance, HNSW index parameters,
    and payload indexes for fast keyword/date filtering.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncQdrantClient(url=settings.qdrant_url)
        self._collection = settings.qdrant_collection
        self._vector_size = settings.embedding_vector_size

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection if it does not already exist.

        Idempotent — safe to call on every pipeline run.
        """
        existing = await self._client.get_collections()
        existing_names = {c.name for c in existing.collections}

        if self._collection in existing_names:
            logger.info("collection_already_exists", collection=self._collection)
            return

        await self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(
                size=self._vector_size,
                distance=Distance.COSINE,
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=10_000,
            ),
            hnsw_config=HnswConfigDiff(
                m=16,
                ef_construct=100,
            ),
        )

        # Create payload indexes for fast filtering.
        for field, schema_type in [
            ("filename", PayloadSchemaType.KEYWORD),
            ("file_type", PayloadSchemaType.KEYWORD),
            ("doc_id", PayloadSchemaType.KEYWORD),
            ("ingested_at", PayloadSchemaType.DATETIME),
        ]:
            await self._client.create_payload_index(
                collection_name=self._collection,
                field_name=field,
                field_schema=schema_type,
            )

        logger.info("collection_created", collection=self._collection)

    async def doc_exists(self, doc_id: str) -> bool:
        """Return True if any point with this doc_id is already in the collection."""
        result = await self._client.count(
            collection_name=self._collection,
            count_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
            exact=False,
        )
        return result.count > 0

    async def upsert(self, chunks: list[ChunkedDocument]) -> None:
        """Upsert a list of embedded chunks into Qdrant.

        Every point carries the full ``ChunkMetadata`` payload.
        Raises ``IngestionError`` on failure.
        """
        if not chunks:
            logger.warning("upsert_called_with_no_chunks")
            return

        points: list[PointStruct] = []
        for chunk in chunks:
            if not chunk.vector:
                raise IngestionError(
                    f"Chunk {chunk.metadata['chunk_id']} has no vector; embed before upsert"
                )
            points.append(
                PointStruct(
                    id=chunk.metadata["chunk_id"],
                    vector=chunk.vector,
                    payload={**dict(chunk.metadata), "text": chunk.text},
                )
            )

        try:
            await self._client.upsert(
                collection_name=self._collection,
                points=points,
            )
        except Exception as exc:
            logger.error("upsert_failed", error=str(exc), chunk_count=len(chunks))
            raise IngestionError(f"Qdrant upsert failed: {exc}") from exc

        logger.info("upsert_complete", collection=self._collection, point_count=len(points))

    async def close(self) -> None:
        """Close the underlying async HTTP client."""
        await self._client.close()
