"""BM25 sparse retrieval backed by a pre-built BM25Store."""

import numpy as np
import structlog

from src.exceptions import RetrievalError
from src.ingestion.bm25_store import BM25Store
from src.retrieval.models import RetrievalResult

logger = structlog.get_logger(__name__)


class SparseRetriever:
    """Retrieve chunks using BM25Okapi keyword scoring.

    Tokenisation mirrors the build-time strategy: ``text.lower().split()``.
    The ``BM25Store`` must already be built or loaded before calling
    ``search``; otherwise ``RetrievalError`` is raised.
    """

    def __init__(self, store: BM25Store) -> None:
        self._store = store

    def search(self, query: str, k: int) -> list[RetrievalResult]:
        """Return up to ``k`` results ranked by BM25 score descending.

        Raises ``RetrievalError`` if the index has not been built.
        """
        if self._store.index is None:
            raise RetrievalError(
                "BM25 index is not built. Call BM25Store.build() or BM25Store.load() first."
            )

        tokens = query.lower().split()
        scores: np.ndarray[tuple[int], np.dtype[np.float64]] = self._store.index.get_scores(tokens)

        n = min(k, len(self._store.chunks))
        top_indices: np.ndarray[tuple[int], np.dtype[np.intp]] = np.argsort(scores)[::-1][:n]

        results: list[RetrievalResult] = []
        for idx in top_indices:
            chunk = self._store.chunks[int(idx)]
            results.append(
                RetrievalResult(
                    chunk_id=chunk.metadata["chunk_id"],
                    text=chunk.text,
                    metadata=chunk.metadata,
                    score=float(scores[int(idx)]),
                )
            )

        logger.info("sparse_search_complete", result_count=len(results), k=k)
        return results
