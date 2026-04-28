"""HybridRetriever — orchestrates dense + sparse + RRF + cross-encoder re-rank."""

from typing import Literal

import structlog

from src.config import Settings
from src.exceptions import EmbeddingError, RetrievalError
from src.ingestion.bm25_store import BM25Store
from src.ingestion.embedder import Embedder
from src.retrieval.dense import DenseRetriever
from src.retrieval.hybrid import reciprocal_rank_fusion
from src.retrieval.models import RetrievalResult
from src.retrieval.reranker import CrossEncoderReranker
from src.retrieval.sparse import SparseRetriever

logger = structlog.get_logger(__name__)


class HybridRetriever:
    """End-to-end retrieval pipeline: embed → dense → sparse → RRF → re-rank.

    Pipeline steps:
    1. Embed the query text to a float vector via Azure OpenAI.
    2. Dense search: top-k cosine-similarity results from Qdrant.
    3. Sparse search: top-k BM25 results from the in-memory BM25Store.
    4. RRF fusion: merge and deduplicate the two ranked lists.
    5. Cross-encoder re-rank: score each fused result and return top reranker_top_k.
    """

    def __init__(
        self,
        settings: Settings,
        bm25_store: BM25Store,
        embedder: Embedder,
    ) -> None:
        self._settings = settings
        self._dense = DenseRetriever(settings)
        self._sparse = SparseRetriever(bm25_store)
        self._reranker = CrossEncoderReranker(settings.reranker_model)
        self._embedder = embedder

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        filters: dict[str, str] | None = None,
        mode: Literal["dense", "hybrid"] = "hybrid",
    ) -> list[RetrievalResult]:
        """Run the retrieval pipeline and return re-ranked results.

        Args:
            query: Natural-language query string.
            k: Override for retrieval_top_k (dense + sparse candidate pool).
            filters: Optional payload field filters forwarded to dense search.
            mode: Retrieval strategy.
                ``"hybrid"`` (default) — embed → Qdrant dense → BM25 sparse → RRF fusion →
                cross-encoder rerank.
                ``"dense"`` — embed → Qdrant dense → cross-encoder rerank. BM25 and RRF are
                skipped entirely.

        Returns:
            Up to ``reranker_top_k`` results sorted by cross-encoder score.
        """
        top_k = k if k is not None else self._settings.retrieval_top_k

        try:
            query_vector = await self._embedder.embed_query(query)
        except EmbeddingError as exc:
            raise RetrievalError(f"Query embedding failed during retrieval: {exc}") from exc

        dense = await self._dense.search(query_vector, k=top_k, filters=filters)

        if mode == "dense":
            reranked = self._reranker.rerank(query, dense, top_k=self._settings.reranker_top_k)
            logger.info(
                "retrieval_complete",
                mode=mode,
                query_len=len(query),
                dense_count=len(dense),
                sparse_count=0,
                fused_count=len(dense),
                final_count=len(reranked),
            )
            return reranked

        # mode == "hybrid"
        sparse = self._sparse.search(query, k=top_k)
        fused = reciprocal_rank_fusion([dense, sparse], k=self._settings.rrf_k)
        reranked = self._reranker.rerank(query, fused, top_k=self._settings.reranker_top_k)

        logger.info(
            "retrieval_complete",
            mode=mode,
            query_len=len(query),
            dense_count=len(dense),
            sparse_count=len(sparse),
            fused_count=len(fused),
            final_count=len(reranked),
        )
        return reranked

    async def close(self) -> None:
        """Release resources held by the dense retriever."""
        await self._dense.close()
