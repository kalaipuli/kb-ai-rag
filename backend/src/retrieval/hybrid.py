"""Reciprocal Rank Fusion for combining dense and sparse retrieval result lists."""

from src.retrieval.models import RetrievalResult


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievalResult]],
    k: int = 60,
) -> list[RetrievalResult]:
    """Fuse multiple ranked result lists into a single list using RRF.

    Each chunk accumulates a score of ``1 / (k + rank + 1)`` per list it
    appears in, where ``rank`` is its 0-based position in that list.  Chunks
    appearing in multiple lists have their scores summed.  The returned list is
    sorted by accumulated RRF score descending with ``rank`` updated to reflect
    the final position.

    When the same ``chunk_id`` appears in more than one list, the metadata and
    text are taken from the first occurrence (lowest list index, lowest rank).
    """
    rrf_scores: dict[str, float] = {}
    first_seen: dict[str, RetrievalResult] = {}

    for result_list in result_lists:
        for rank, result in enumerate(result_list):
            cid = result.chunk_id
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
            if cid not in first_seen:
                first_seen[cid] = result

    fused: list[RetrievalResult] = sorted(
        (
            RetrievalResult(
                chunk_id=cid,
                text=first_seen[cid].text,
                metadata=first_seen[cid].metadata,
                score=score,
                rank=0,
            )
            for cid, score in rrf_scores.items()
        ),
        key=lambda r: r.score,
        reverse=True,
    )

    for position, result in enumerate(fused):
        fused[position] = result.model_copy(update={"rank": position})

    return fused
