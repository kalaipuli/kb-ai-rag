"""Unit tests for SparseRetriever — uses real BM25Store in memory."""

from pathlib import Path

import pytest

from src.exceptions import RetrievalError
from src.ingestion.bm25_store import BM25Store
from src.ingestion.models import ChunkedDocument, ChunkMetadata
from src.retrieval.sparse import SparseRetriever


def _make_chunk(text: str, chunk_id: str) -> ChunkedDocument:
    meta: ChunkMetadata = {
        "doc_id": "doc-1",
        "chunk_id": chunk_id,
        "source_path": "/tmp/a.txt",
        "filename": "a.txt",
        "file_type": "txt",
        "title": text[:80],
        "page_number": -1,
        "chunk_index": 0,
        "total_chunks": 3,
        "char_count": len(text),
        "ingested_at": "2025-01-15T10:00:00Z",
        "tags": [],
    }
    return ChunkedDocument(text=text, metadata=meta, vector=[0.1] * 3072)


def _build_store(chunks: list[ChunkedDocument], tmp_path: Path) -> BM25Store:
    store = BM25Store(index_path=tmp_path / "idx.pkl")
    store.build(chunks)
    return store


class TestSparseRetriever:
    def test_search_returns_top_k_sorted_by_score(self, tmp_path: Path) -> None:
        chunks = [
            _make_chunk("the quick brown fox jumps over the lazy dog", "c1"),
            _make_chunk("a completely different article about databases", "c2"),
            _make_chunk("quick brown fox is the fastest animal", "c3"),
        ]
        store = _build_store(chunks, tmp_path)
        retriever = SparseRetriever(store)

        results = retriever.search("quick brown fox", k=2)

        assert len(results) == 2
        # Both fox-related chunks should outscore the database chunk
        chunk_ids = {r.chunk_id for r in results}
        assert "c2" not in chunk_ids
        # First result should have the highest score
        assert results[0].score >= results[1].score

    def test_search_returns_all_when_k_greater_than_corpus(self, tmp_path: Path) -> None:
        chunks = [
            _make_chunk("hello world text", "c1"),
            _make_chunk("another document here", "c2"),
        ]
        store = _build_store(chunks, tmp_path)
        retriever = SparseRetriever(store)

        results = retriever.search("hello", k=100)

        assert len(results) == 2

    def test_search_raises_retrieval_error_when_index_none(self, tmp_path: Path) -> None:
        store = BM25Store(index_path=tmp_path / "idx.pkl")
        # do not call build — index stays None
        retriever = SparseRetriever(store)

        with pytest.raises(RetrievalError, match="BM25 index is not built"):
            retriever.search("any query", k=5)

    def test_search_tokenises_query_lowercase(self, tmp_path: Path) -> None:
        chunks = [_make_chunk("quick BROWN fox", "c1")]
        store = _build_store(chunks, tmp_path)
        retriever = SparseRetriever(store)

        # "QUICK" lowercased → "quick" matches the lowercased corpus
        results_upper = retriever.search("QUICK BROWN", k=5)
        results_lower = retriever.search("quick brown", k=5)

        assert len(results_upper) == 1
        assert results_upper[0].score == pytest.approx(results_lower[0].score)

    def test_search_text_matches_chunk_text(self, tmp_path: Path) -> None:
        original_text = "this is the full chunk text that should be preserved"
        chunks = [_make_chunk(original_text, "c1")]
        store = _build_store(chunks, tmp_path)
        retriever = SparseRetriever(store)

        results = retriever.search("full chunk text", k=1)

        assert len(results) == 1
        assert results[0].text == original_text
