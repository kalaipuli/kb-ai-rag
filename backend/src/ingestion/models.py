"""Pydantic models and TypedDict schemas for the ingestion pipeline.

``Document`` represents a raw loaded file (pre-split).
``ChunkedDocument`` represents a single text chunk ready for embedding and upsert.
``ChunkMetadata`` is the canonical payload schema stored in Qdrant.
"""

from typing import Any

from pydantic import BaseModel
from typing_extensions import TypedDict


class ChunkMetadata(TypedDict):
    """Canonical metadata payload stored alongside every Qdrant vector.

    All fields are required except ``page_number`` (``-1`` when not applicable)
    and ``tags`` (empty list when none extracted).
    """

    doc_id: str
    """UUID5 of the source file path — stable across re-ingestion."""

    chunk_id: str
    """UUID4 — unique per chunk."""

    source_path: str
    """Absolute path (local) or blob URL (prod)."""

    filename: str
    """Basename of the source file, e.g. ``ubuntu-22-04-manual.pdf``."""

    file_type: str
    """``"pdf"`` or ``"txt"``."""

    title: str
    """First 80 chars of chunk text (stripped), or filename stem if absent."""

    page_number: int
    """0-indexed page number.  ``-1`` when the source has no pages (e.g. TXT)."""

    chunk_index: int
    """0-based position of this chunk within the document."""

    total_chunks: int
    """Total number of chunks produced from this document."""

    char_count: int
    """``len(chunk_text)`` after splitting."""

    ingested_at: str
    """ISO 8601 UTC timestamp of ingestion, e.g. ``2025-01-15T10:30:00Z``."""

    tags: list[str]
    """Extracted keywords or an empty list.  Reserved for future filtering."""


class Document(BaseModel):
    """Raw document content returned by a loader before splitting.

    ``metadata`` carries loader-level fields: ``source_path``, ``filename``,
    ``file_type``, ``page_number``, ``doc_id``.  It is intentionally untyped
    so each loader can attach extra keys without breaking the base contract.
    """

    content: str
    metadata: dict[str, Any]


class ChunkedDocument(BaseModel):
    """A single text chunk produced by the splitter, ready for embedding."""

    text: str
    """The chunk text."""

    metadata: ChunkMetadata
    """Full canonical metadata for this chunk."""

    vector: list[float] = []
    """Embedding vector.  Populated by ``Embedder.embed_chunks``."""
