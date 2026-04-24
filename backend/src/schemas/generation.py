"""Shared generation schemas used by both the domain layer and the API layer.

Neither ``src/generation/`` nor ``src/api/`` should define these types locally.
Both import from this module to ensure a single canonical definition.
"""

from pydantic import BaseModel


class Citation(BaseModel):
    """A single source chunk cited in a generated answer."""

    chunk_id: str
    filename: str
    source_path: str
    page_number: int | None = None


class GenerationResult(BaseModel):
    """Full output of the GenerationChain for a single query."""

    query: str
    answer: str
    citations: list[Citation]
    confidence: float
