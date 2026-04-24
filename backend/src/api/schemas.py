"""Pydantic schemas for the kb-ai-rag API layer.

All request and response bodies are defined here so that route handlers stay
thin and schema evolution is centralised in one place.

``CitationItem`` and ``QueryResponse`` are backward-compatible aliases for the
canonical types defined in ``src.schemas.generation``.
"""

from pydantic import BaseModel

from src.schemas.generation import Citation as CitationItem
from src.schemas.generation import GenerationResult as QueryResponse

__all__ = [
    "HealthResponse",
    "ErrorResponse",
    "QueryRequest",
    "CitationItem",
    "QueryResponse",
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

    query: str
    filters: dict[str, str] | None = None
    k: int | None = None
