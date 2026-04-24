"""Cross-encoder re-ranker using sentence-transformers."""

import structlog
from sentence_transformers import CrossEncoder

from src.retrieval.models import RetrievalResult

logger = structlog.get_logger(__name__)


class CrossEncoderReranker:
    """Re-rank a list of retrieval results using a cross-encoder model.

    The cross-encoder scores each (query, chunk-text) pair and returns the
    top-k results sorted by that score descending.
    """

    def __init__(self, model_name: str) -> None:
        self._model: CrossEncoder = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """Return the top ``top_k`` results re-ranked by cross-encoder score.

        ``score`` and ``rank`` on each returned result reflect the cross-encoder
        logit and 0-based output position respectively.
        """
        if not results:
            return []

        pairs: list[tuple[str, str]] = [(query, r.text) for r in results]
        raw_scores: list[float] = self._model.predict(pairs).tolist()

        scored = sorted(
            zip(raw_scores, results, strict=True),
            key=lambda t: t[0],
            reverse=True,
        )

        limit = min(top_k, len(results))
        reranked: list[RetrievalResult] = []
        for position, (score, result) in enumerate(scored[:limit]):
            reranked.append(result.model_copy(update={"score": score, "rank": position}))

        logger.info(
            "rerank_complete",
            input_count=len(results),
            output_count=len(reranked),
            top_k=top_k,
        )
        return reranked
