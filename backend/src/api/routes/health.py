"""Health-check endpoint.

GET /api/v1/health returns the service status and a quick connectivity probe
against the configured Qdrant instance.  The endpoint never returns HTTP 500 —
a degraded dependency is reported in the response body with status "ok" so
that load-balancer health checks are not tripped by a temporarily unavailable
vector store.
"""

import structlog
from fastapi import APIRouter, Depends
from qdrant_client import AsyncQdrantClient

from src.api.schemas import HealthResponse
from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:  # noqa: B008
    """Return service liveness and Qdrant connectivity status.

    Args:
        settings: Injected application settings (via FastAPI dependency).

    Returns:
        HealthResponse with ``qdrant="connected"`` and a live collection count,
        or ``qdrant="disconnected"`` with ``collection_count=0`` when the vector
        store cannot be reached.
    """
    try:
        client = AsyncQdrantClient(url=settings.qdrant_url)
        result = await client.get_collections()
        await client.close()
        collection_count = len(result.collections)
        logger.info(
            "health_check_ok",
            qdrant="connected",
            collection_count=collection_count,
        )
        return HealthResponse(
            status="ok",
            qdrant="connected",
            collection_count=collection_count,
        )
    except Exception as exc:
        logger.warning("health_check_qdrant_unreachable", error=str(exc))
        return HealthResponse(
            status="ok",
            qdrant="disconnected",
            collection_count=0,
        )
