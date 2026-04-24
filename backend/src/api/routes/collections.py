"""GET /api/v1/collections — list indexed Qdrant collections."""

import structlog
from fastapi import APIRouter

from src.api.deps import QdrantClientDep
from src.api.schemas import CollectionInfo, CollectionsResponse
from src.exceptions import RetrievalError

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/collections", response_model=CollectionsResponse)
async def list_collections(qdrant: QdrantClientDep) -> CollectionsResponse:
    """Return all Qdrant collections with document and vector counts."""
    try:
        result = await qdrant.get_collections()
        infos: list[CollectionInfo] = []
        for col in result.collections:
            info = await qdrant.get_collection(col.name)
            infos.append(
                CollectionInfo(
                    name=col.name,
                    document_count=info.points_count or 0,
                    vector_count=info.indexed_vectors_count or 0,
                )
            )
        logger.info("collections_listed", count=len(infos))
        return CollectionsResponse(collections=infos)
    except RetrievalError:
        raise
    except Exception as exc:
        logger.error("collections_list_failed", error=str(exc))
        raise RetrievalError(f"Failed to list collections: {exc}") from exc
