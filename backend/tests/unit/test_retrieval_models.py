"""Unit tests for RetrievalResult model."""

from src.ingestion.models import ChunkMetadata
from src.retrieval.models import RetrievalResult


def _make_metadata(chunk_id: str = "c1") -> ChunkMetadata:
    return ChunkMetadata(
        doc_id="doc-1",
        chunk_id=chunk_id,
        source_path="/tmp/a.txt",
        filename="a.txt",
        file_type="txt",
        title="Sample title",
        page_number=-1,
        chunk_index=0,
        total_chunks=1,
        char_count=12,
        ingested_at="2025-01-15T10:00:00Z",
        tags=[],
    )


class TestRetrievalResult:
    def test_result_creation_with_all_fields(self) -> None:
        result = RetrievalResult(
            chunk_id="c1",
            text="sample text",
            metadata=_make_metadata("c1"),
            score=0.85,
            rank=2,
        )
        assert result.chunk_id == "c1"
        assert result.text == "sample text"
        assert result.score == 0.85
        assert result.rank == 2

    def test_result_score_is_float(self) -> None:
        result = RetrievalResult(
            chunk_id="c2",
            text="text",
            metadata=_make_metadata("c2"),
            score=1,  # int promoted to float
        )
        assert isinstance(result.score, float)

    def test_result_rank_defaults_to_zero(self) -> None:
        result = RetrievalResult(
            chunk_id="c3",
            text="text",
            metadata=_make_metadata("c3"),
            score=0.5,
        )
        assert result.rank == 0
