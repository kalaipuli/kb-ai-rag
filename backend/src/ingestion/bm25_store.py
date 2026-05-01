"""BM25 sparse index: build, persist, and load for hybrid retrieval."""

import asyncio
import pickle
from pathlib import Path
from typing import cast

import structlog
from rank_bm25 import BM25Okapi

from src.exceptions import IngestionError
from src.ingestion.models import ChunkedDocument

logger = structlog.get_logger(__name__)


class BM25Store:
    """Build and persist a BM25Okapi index over ingested chunk texts.

    The index and the parallel list of ``ChunkedDocument`` objects are pickled
    together so that retrieval can map BM25 scores back to chunks without a
    separate lookup.

    Note: ``rank-bm25`` does not support incremental updates; the index is
    rebuilt from scratch on each full ingestion run.
    """

    def __init__(self, index_path: Path) -> None:
        self._index_path = index_path
        self._index: BM25Okapi | None = None
        self._chunks: list[ChunkedDocument] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def build(self, chunks: list[ChunkedDocument]) -> None:
        """Tokenise chunk texts and build a new BM25Okapi index in memory."""
        if not chunks:
            logger.warning("bm25_build_called_with_no_chunks")
            self._index = None
            self._chunks = []
            return

        tokenised = [chunk.text.lower().split() for chunk in chunks]
        self._index = BM25Okapi(tokenised)
        self._chunks = list(chunks)

        logger.info("bm25_build_complete", chunk_count=len(chunks))

    async def asave(self) -> None:
        """Pickle the BM25 index and chunk list to ``index_path`` (async-safe)."""
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {"index": self._index, "chunks": self._chunks}
        path = self._index_path
        await asyncio.to_thread(lambda: path.write_bytes(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)))  # noqa: S301 — trusted local file
        logger.info("bm25_saved", path=str(self._index_path))

    async def aload(self) -> None:
        """Load the pickled BM25 index and chunk list from ``index_path`` (async-safe).

        Raises ``IngestionError`` if the file does not exist.
        """
        if not self._index_path.exists():
            raise IngestionError(
                f"BM25 index file not found at {self._index_path}. "
                "Run the ingestion pipeline first."
            )
        path = self._index_path
        payload: dict[str, object] = await asyncio.to_thread(lambda: pickle.loads(path.read_bytes()))  # noqa: S301 — trusted local file
        self._index = cast(BM25Okapi, payload["index"])
        self._chunks = cast(list[ChunkedDocument], payload["chunks"])
        logger.info(
            "bm25_loaded",
            path=str(self._index_path),
            chunk_count=len(self._chunks),
        )

    # ------------------------------------------------------------------
    # Properties for retrieval-side access
    # ------------------------------------------------------------------

    @property
    def index(self) -> BM25Okapi | None:
        """The in-memory BM25Okapi index, or ``None`` if not yet built/loaded."""
        return self._index

    @property
    def chunks(self) -> list[ChunkedDocument]:
        """The chunks parallel to the BM25 corpus rows."""
        return self._chunks
