"""Pydantic schemas for the kb-ai-rag API layer.

All request and response bodies are defined here so that route handlers stay
thin and schema evolution is centralised in one place.
"""

from pydantic import BaseModel


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


class CitationItem(BaseModel):
    """A single source chunk cited in a query response."""

    chunk_id: str
    filename: str
    source_path: str
    page_number: int


class QueryResponse(BaseModel):
    """Response body for POST /api/v1/query."""

    query: str
    answer: str
    citations: list[CitationItem]
    confidence: float
