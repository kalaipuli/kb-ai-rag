"""Pydantic schema for a single retrieval result returned to callers."""

from pydantic import BaseModel

from src.ingestion.models import ChunkMetadata


class RetrievalResult(BaseModel):
    """A single retrieved chunk with its metadata and retrieval score.

    ``score`` carries the raw retrieval score (BM25, cosine, RRF) depending on
    the stage that produced this result.  After re-ranking, ``score`` reflects
    the cross-encoder logit and ``rank`` reflects the 0-based position in the
    final output list.
    """

    chunk_id: str
    text: str
    metadata: ChunkMetadata
    score: float
    rank: int = 0
