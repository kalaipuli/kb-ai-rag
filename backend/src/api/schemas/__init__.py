"""Pydantic schemas for the kb-ai-rag API layer.

All request and response bodies are defined here so that route handlers stay
thin and schema evolution is centralised in one place.

``CitationItem`` and ``QueryResponse`` are backward-compatible aliases for the
canonical types defined in ``src.schemas.generation``.
"""

from pydantic import BaseModel, Field

from src.schemas.generation import Citation as CitationItem
from src.schemas.generation import GenerationResult as QueryResponse

__all__ = [
    "HealthResponse",
    "ErrorResponse",
    "QueryRequest",
    "CitationItem",
    "QueryResponse",
    "IngestRequest",
    "IngestAcceptedResponse",
    "CollectionInfo",
    "CollectionsResponse",
    "EvalMetrics",
    "EvalBaselineResponse",
]


class HealthResponse(BaseModel):
    """Response body for GET /api/v1/health."""

    status: str
    qdrant: str
    collection_count: int


class ErrorResponse(BaseModel):
    """Generic error response body used by exception handlers."""

    detail: str


class QueryRequest(BaseModel):
    """Request body for POST /api/v1/query."""

    query: str = Field(..., min_length=1)
    filters: dict[str, str] | None = None
    k: int | None = None


class IngestRequest(BaseModel):
    """Request body for POST /api/v1/ingest. All fields are optional."""

    data_dir: str | None = None


class IngestAcceptedResponse(BaseModel):
    """202 Accepted response for POST /api/v1/ingest."""

    status: str
    message: str


class CollectionInfo(BaseModel):
    """Info about a single Qdrant collection."""

    name: str
    document_count: int
    vector_count: int


class CollectionsResponse(BaseModel):
    """Response body for GET /api/v1/collections."""

    collections: list[CollectionInfo]


class EvalMetrics(BaseModel):
    """Five RAGAS metric scores from one evaluation run."""

    faithfulness: float
    answer_relevancy: float
    context_recall: float
    context_precision: float
    answer_correctness: float


class EvalBaselineResponse(BaseModel):
    """Normalized response for GET /api/v1/eval/baseline."""

    pipeline: str
    run_date: str | None
    metrics: EvalMetrics
