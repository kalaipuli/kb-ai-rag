"""Document splitter: converts raw ``Document`` objects into ``ChunkedDocument`` chunks."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime

import structlog

from src.config import Settings
from src.ingestion.models import ChunkedDocument, ChunkMetadata, Document
from src.ingestion.splitter_factory import SplitterFactory

logger = structlog.get_logger(__name__)

_MIN_CHUNK_CHARS = 100
_TITLE_MAX_CHARS = 80


class DocumentSplitter:
    """Split ``Document`` objects into fixed-size text chunks with full metadata.

    Delegates splitter construction to ``SplitterFactory`` so that the active
    ``chunk_strategy`` in Settings controls which algorithm is used.  Discards
    any chunk shorter than 100 characters (header/footer noise).
    """

    def __init__(self, settings: Settings, embedder: object | None = None) -> None:
        self._splitter = SplitterFactory.build(settings, embedder)

    def split(self, docs: list[Document]) -> list[ChunkedDocument]:
        """Split all documents and return a flat list of ``ChunkedDocument`` objects.

        Chunks shorter than ``_MIN_CHUNK_CHARS`` are discarded and logged.
        """
        # Group source docs by doc_id so we can compute total_chunks per doc.
        # We must do two passes: first split everything, then patch total_chunks.
        pre_chunks: list[tuple[str, int, str, dict[str, object]]] = []
        # (doc_id, page_number, text, base_metadata)

        for doc in docs:
            raw_chunks = self._splitter.split_text(doc.content)
            for raw in raw_chunks:
                stripped = raw.strip()
                if len(stripped) < _MIN_CHUNK_CHARS:
                    logger.warning(
                        "chunk_too_short_skipped",
                        doc_id=doc.metadata.get("doc_id"),
                        char_count=len(stripped),
                    )
                    continue
                pre_chunks.append(
                    (
                        str(doc.metadata["doc_id"]),
                        int(doc.metadata["page_number"]),
                        stripped,
                        doc.metadata,
                    )
                )

        # Count chunks per doc_id for total_chunks field.
        counts: dict[str, int] = defaultdict(int)
        for doc_id, _, _, _ in pre_chunks:
            counts[doc_id] += 1

        # Track per-doc chunk index as we iterate.
        indices: dict[str, int] = defaultdict(int)

        ingested_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        chunked: list[ChunkedDocument] = []

        for doc_id, page_number, text, base_meta in pre_chunks:
            chunk_index = indices[doc_id]
            indices[doc_id] += 1

            title = text[:_TITLE_MAX_CHARS].strip()

            metadata: ChunkMetadata = {
                "doc_id": doc_id,
                "chunk_id": str(uuid.uuid4()),
                "source_path": str(base_meta["source_path"]),
                "filename": str(base_meta["filename"]),
                "file_type": str(base_meta["file_type"]),
                "title": title,
                "page_number": page_number,
                "chunk_index": chunk_index,
                "total_chunks": counts[doc_id],
                "char_count": len(text),
                "ingested_at": ingested_at,
                "tags": [],
            }

            chunked.append(ChunkedDocument(text=text, metadata=metadata))

        logger.info(
            "split_complete",
            input_docs=len(docs),
            output_chunks=len(chunked),
        )
        return chunked
