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
