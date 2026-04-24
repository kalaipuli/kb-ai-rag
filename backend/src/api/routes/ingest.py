"""POST /api/v1/ingest — trigger document ingestion as a background task."""

from pathlib import Path

import structlog
from fastapi import APIRouter, BackgroundTasks

from src.api.deps import SettingsDep
from src.api.schemas import IngestAcceptedResponse, IngestRequest
from src.ingestion.pipeline import run_pipeline

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/ingest", status_code=202, response_model=IngestAcceptedResponse)
async def ingest_endpoint(
    background_tasks: BackgroundTasks,
    settings: SettingsDep,
    body: IngestRequest | None = None,
) -> IngestAcceptedResponse:
    """Trigger document ingestion from a folder as a background task.

    Returns 202 Accepted immediately. The pipeline runs after the response
    is sent. If no body is provided, uses the configured data_dir.
    """
    data_dir = (
        Path(body.data_dir) if body and body.data_dir else Path(settings.data_dir)
    )
    background_tasks.add_task(run_pipeline, data_dir, settings)
    logger.info("ingest_accepted", data_dir=str(data_dir))
    return IngestAcceptedResponse(
        status="accepted",
        message=f"Ingestion started for {data_dir}",
    )
