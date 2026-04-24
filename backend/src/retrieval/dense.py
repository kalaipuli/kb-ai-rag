"""Dense vector retrieval using Qdrant AsyncQdrantClient."""

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from src.config import Settings
from src.exceptions import RetrievalError
from src.ingestion.models import ChunkMetadata
from src.retrieval.models import RetrievalResult

logger = structlog.get_logger(__name__)


class DenseRetriever:
    """Search the Qdrant collection with a query embedding vector.

    Optional ``filters`` map payload field names to exact-match string values
    (e.g. ``{"file_type": "pdf"}``), translated to Qdrant ``FieldCondition``
    must-clauses.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncQdrantClient(url=settings.qdrant_url)
        self._collection = settings.qdrant_collection

    async def search(
        self,
        query_vector: list[float],
        k: int,
        filters: dict[str, str] | None = None,
    ) -> list[RetrievalResult]:
        """Return up to ``k`` results ranked by cosine similarity.

        Raises ``RetrievalError`` on any Qdrant failure.
        """
        query_filter: Filter | None = None
        if filters:
            query_filter = Filter(
                must=[
                    FieldCondition(key=field, match=MatchValue(value=value))
                    for field, value in filters.items()
                ]
            )

        try:
            result = await self._client.query_points(
                collection_name=self._collection,
                query=query_vector,
                limit=k,
                query_filter=query_filter,
                with_payload=True,
            )
            hits = result.points
        except Exception as exc:
            logger.error("qdrant_search_failed", error=str(exc), collection=self._collection)
            raise RetrievalError(f"Qdrant search failed: {exc}") from exc

        results: list[RetrievalResult] = []
        for point in hits:
            payload = point.payload or {}
            metadata: ChunkMetadata = {
                "doc_id": str(payload.get("doc_id", "")),
                "chunk_id": str(payload.get("chunk_id", "")),
                "source_path": str(payload.get("source_path", "")),
                "filename": str(payload.get("filename", "")),
                "file_type": str(payload.get("file_type", "")),
                "title": str(payload.get("title", "")),
                "page_number": int(payload.get("page_number", -1)),
                "chunk_index": int(payload.get("chunk_index", 0)),
                "total_chunks": int(payload.get("total_chunks", 0)),
                "char_count": int(payload.get("char_count", 0)),
                "ingested_at": str(payload.get("ingested_at", "")),
                "tags": list(payload.get("tags", [])),
            }
            results.append(
                RetrievalResult(
                    chunk_id=str(payload["chunk_id"]),
                    text=str(payload.get("text", payload.get("title", ""))),
                    metadata=metadata,
                    score=float(point.score),
                )
            )

        logger.info(
            "dense_search_complete",
            collection=self._collection,
            result_count=len(results),
            k=k,
        )
        return results

    async def close(self) -> None:
        """Close the underlying async HTTP client."""
        await self._client.close()
