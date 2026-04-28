"""GET /api/v1/eval/baseline — serve the persisted RAGAS evaluation baseline."""

import json
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query

from src.api.deps import SettingsDep

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/eval/baseline")
async def eval_baseline(
    settings: SettingsDep,
    pipeline: str | None = Query(default=None),
) -> dict[str, object]:
    """Return the persisted RAGAS evaluation baseline metrics.

    Reads the JSON file at ``settings.eval_baseline_path`` by default.
    When ``pipeline=agentic`` is supplied, reads the agentic baseline file
    (``eval_agentic_baseline.json``) located in the same directory.

    Args:
        pipeline: Optional query parameter.  Must be ``"agentic"`` or omitted.
                  Any other value returns 422.

    Returns:
        JSON object with 5 RAGAS metric scores.

    Raises:
        HTTPException 404: File does not exist — evaluator has not been run yet.
        HTTPException 422: File exists but contains malformed JSON, or
                           ``pipeline`` holds an invalid value.
    """
    if pipeline is not None and pipeline != "agentic":
        raise HTTPException(
            status_code=422,
            detail="Invalid pipeline value. Must be 'agentic' or omitted.",
        )

    if pipeline == "agentic":
        baseline_dir = Path(settings.eval_baseline_path).parent
        path = baseline_dir / "eval_agentic_baseline.json"
        not_found_detail = "Agentic baseline not yet generated"
    else:
        path = Path(settings.eval_baseline_path)
        not_found_detail = "No evaluation baseline found. Run the evaluator first."

    if not path.exists():
        logger.info("eval_baseline_not_found", path=str(path), pipeline=pipeline)
        raise HTTPException(
            status_code=404,
            detail=not_found_detail,
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

    logger.info("eval_baseline_served", path=str(path), pipeline=pipeline)
    return data
