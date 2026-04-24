"""POST /api/v1/query — query the knowledge base via SSE streaming."""

from collections.abc import AsyncGenerator

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.deps import GenerationChainDep
from src.api.schemas import QueryRequest

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/query")
async def query_endpoint(
    body: QueryRequest,
    chain: GenerationChainDep,
) -> StreamingResponse:
    """Query the knowledge base and stream the answer via SSE.

    SSE event types (in order): ``token`` (0–N), ``citations`` (1), ``done`` (1).
    """
    logger.info("query_received", query_len=len(body.query))

    async def _stream() -> AsyncGenerator[str, None]:
        async for event in chain.astream_generate(
            body.query, k=body.k, filters=body.filters
        ):
            yield event

    return StreamingResponse(_stream(), media_type="text/event-stream")
