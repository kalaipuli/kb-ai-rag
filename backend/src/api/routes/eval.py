"""GET /api/v1/eval/baseline — serve the persisted RAGAS evaluation baseline."""

import json
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException

from src.api.deps import SettingsDep

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/eval/baseline")
async def eval_baseline(settings: SettingsDep) -> dict[str, object]:
    """Return the persisted RAGAS evaluation baseline metrics.

    Reads the JSON file at ``settings.eval_baseline_path``.

    Returns:
        JSON object with 5 RAGAS metric scores.

    Raises:
        HTTPException 404: File does not exist — evaluator has not been run yet.
        HTTPException 422: File exists but contains malformed JSON.
    """
    path = Path(settings.eval_baseline_path)

    if not path.exists():
        logger.info("eval_baseline_not_found", path=str(path))
        raise HTTPException(
            status_code=404,
            detail="No evaluation baseline found. Run the evaluator first.",
        )

    try:
        raw = path.read_text(encoding="utf-8")
        data: dict[str, object] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("eval_baseline_malformed", path=str(path), error=str(exc))
        raise HTTPException(
            status_code=422,
            detail=f"Evaluation baseline file is malformed: {exc}",
        ) from exc

    logger.info("eval_baseline_served", path=str(path))
    return data
