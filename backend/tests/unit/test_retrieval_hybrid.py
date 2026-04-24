"""Unit tests for reciprocal_rank_fusion — pure function, no mocks needed."""

import pytest

from src.ingestion.models import ChunkMetadata
from src.retrieval.hybrid import reciprocal_rank_fusion
from src.retrieval.models import RetrievalResult


def _make_metadata(chunk_id: str) -> ChunkMetadata:
    return ChunkMetadata(
        doc_id="doc-1",
        chunk_id=chunk_id,
        source_path="/tmp/a.txt",
        filename="a.txt",
        file_type="txt",
        title="title",
        page_number=-1,
        chunk_index=0,
        total_chunks=1,
        char_count=10,
        ingested_at="2025-01-15T10:00:00Z",
        tags=[],
    )


def _make_result(chunk_id: str, score: float = 0.5, text: str = "text") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        text=text,
        metadata=_make_metadata(chunk_id),
        score=score,
    )


class TestRRF:
    def test_rrf_merges_two_lists_correctly(self) -> None:
        # list 1: [A, B], list 2: [B, C]
        # A: 1/(60+0+1) = 1/61
        # B: 1/(60+1+1) + 1/(60+0+1) = 1/62 + 1/61
        # C: 1/(60+1+1) = 1/62
        list1 = [_make_result("A"), _make_result("B")]
        list2 = [_make_result("B"), _make_result("C")]

        fused = reciprocal_rank_fusion([list1, list2], k=60)

        chunk_ids = [r.chunk_id for r in fused]
        assert "A" in chunk_ids
        assert "B" in chunk_ids
        assert "C" in chunk_ids
        # B appears in both lists → highest RRF score
        assert chunk_ids[0] == "B"

    def test_rrf_deduplicates_by_chunk_id(self) -> None:
        list1 = [_make_result("X"), _make_result("Y")]
        list2 = [_make_result("X"), _make_result("Z")]

        fused = reciprocal_rank_fusion([list1, list2], k=60)

        chunk_ids = [r.chunk_id for r in fused]
        assert chunk_ids.count("X") == 1

    def test_rrf_empty_lists_returns_empty(self) -> None:
        fused = reciprocal_rank_fusion([], k=60)
        assert fused == []

    def test_rrf_single_list_passes_through(self) -> None:
        results = [_make_result("A"), _make_result("B"), _make_result("C")]
        fused = reciprocal_rank_fusion([results], k=60)

        assert len(fused) == 3
        # A is rank 0 in the single list → highest score
        assert fused[0].chunk_id == "A"
        # Score for rank 0 with k=60: 1/61
        assert fused[0].score == pytest.approx(1.0 / 61)

    def test_rrf_output_sorted_descending(self) -> None:
        list1 = [_make_result("A"), _make_result("B"), _make_result("C")]
        list2 = [_make_result("C"), _make_result("A"), _make_result("B")]

        fused = reciprocal_rank_fusion([list1, list2], k=60)

        scores = [r.score for r in fused]
        assert scores == sorted(scores, reverse=True)

    def test_rrf_rank_field_updated(self) -> None:
        list1 = [_make_result("A"), _make_result("B")]
        list2 = [_make_result("B"), _make_result("C")]

        fused = reciprocal_rank_fusion([list1, list2], k=60)

        for position, result in enumerate(fused):
            assert result.rank == position

    def test_chunk_in_both_lists_accumulates_score_correctly(self) -> None:
        # "shared" appears at rank 0 in both lists
        # expected score = 1/(60+0+1) + 1/(60+0+1) = 2/61
        shared = _make_result("shared", 0.9)
        results = reciprocal_rank_fusion([[shared], [shared]], k=60)
        assert len(results) == 1
        assert results[0].chunk_id == "shared"
        assert results[0].score == pytest.approx(2.0 / 61, rel=1e-6)

    def test_two_empty_inner_lists_returns_empty(self) -> None:
        assert reciprocal_rank_fusion([[], []], k=60) == []
