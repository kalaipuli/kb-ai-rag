"""Unit tests for BM25Store."""

from pathlib import Path

import pytest

from src.exceptions import IngestionError
from src.ingestion.bm25_store import BM25Store
from src.ingestion.models import ChunkedDocument, ChunkMetadata


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
        "total_chunks": 2,
        "char_count": len(text),
        "ingested_at": "2025-01-15T10:00:00Z",
        "tags": [],
    }
    return ChunkedDocument(text=text, metadata=meta, vector=[0.1, 0.2])


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


class TestBM25StoreBuild:
    def test_build_sets_index(self, tmp_path: Path) -> None:
        store = BM25Store(index_path=tmp_path / "idx.pkl")
        chunks = [
            _make_chunk("the quick brown fox jumps", "c1"),
            _make_chunk("over the lazy dog today", "c2"),
        ]
        store.build(chunks)
        assert store.index is not None

    def test_build_stores_chunks(self, tmp_path: Path) -> None:
        store = BM25Store(index_path=tmp_path / "idx.pkl")
        chunks = [_make_chunk("hello world", "c1")]
        store.build(chunks)
        assert len(store.chunks) == 1
        assert store.chunks[0].metadata["chunk_id"] == "c1"

    def test_build_empty_chunks_clears_index(self, tmp_path: Path) -> None:
        store = BM25Store(index_path=tmp_path / "idx.pkl")
        store.build([])
        assert store.index is None
        assert store.chunks == []


# ---------------------------------------------------------------------------
# save + load round-trip
# ---------------------------------------------------------------------------


class TestBM25StoreSaveLoad:
    def test_save_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / "bm25_index.pkl"
        store = BM25Store(index_path=path)
        store.build([_make_chunk("some content here", "c1")])
        store.save()
        assert path.exists()

    def test_load_restores_chunks(self, tmp_path: Path) -> None:
        path = tmp_path / "bm25_index.pkl"
        chunk = _make_chunk("hello retrieval world", "c99")

        store1 = BM25Store(index_path=path)
        store1.build([chunk])
        store1.save()

        store2 = BM25Store(index_path=path)
        store2.load()

        assert len(store2.chunks) == 1
        assert store2.chunks[0].metadata["chunk_id"] == "c99"

    def test_load_restores_functional_index(self, tmp_path: Path) -> None:
        path = tmp_path / "bm25_index.pkl"
        chunks = [
            _make_chunk("the quick brown fox", "c1"),
            _make_chunk("lazy dog sits today", "c2"),
        ]

        store1 = BM25Store(index_path=path)
        store1.build(chunks)
        store1.save()

        store2 = BM25Store(index_path=path)
        store2.load()

        assert store2.index is not None
        # BM25 score query
        scores = store2.index.get_scores("quick brown".split())
        assert len(scores) == 2

    def test_load_raises_ingestion_error_when_file_missing(self, tmp_path: Path) -> None:
        store = BM25Store(index_path=tmp_path / "nonexistent.pkl")
        with pytest.raises(IngestionError, match="BM25 index file not found"):
            store.load()

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        nested_path = tmp_path / "deep" / "nested" / "bm25.pkl"
        store = BM25Store(index_path=nested_path)
        store.build([_make_chunk("text content here", "c1")])
        store.save()
        assert nested_path.exists()
