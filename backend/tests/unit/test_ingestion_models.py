"""Unit tests for ingestion data models."""

import pytest

from src.ingestion.models import ChunkedDocument, ChunkMetadata, Document


class TestDocument:
    def test_document_stores_content_and_metadata(self) -> None:
        doc = Document(content="hello world", metadata={"source_path": "/tmp/foo.txt"})
        assert doc.content == "hello world"
        assert doc.metadata["source_path"] == "/tmp/foo.txt"

    def test_document_empty_metadata_allowed(self) -> None:
        doc = Document(content="text", metadata={})
        assert doc.metadata == {}

    def test_document_requires_content_field(self) -> None:
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            Document(metadata={})  # type: ignore[call-arg]


class TestChunkedDocument:
    def _make_metadata(self) -> ChunkMetadata:
        return ChunkMetadata(
            doc_id="doc-uuid",
            chunk_id="chunk-uuid",
            source_path="/tmp/a.txt",
            filename="a.txt",
            file_type="txt",
            title="First 80 chars",
            page_number=-1,
            chunk_index=0,
            total_chunks=3,
            char_count=200,
            ingested_at="2025-01-15T10:00:00Z",
            tags=[],
        )

    def test_chunked_document_defaults_vector_to_empty(self) -> None:
        meta = self._make_metadata()
        chunk = ChunkedDocument(text="some text here", metadata=meta)
        assert chunk.vector == []

    def test_chunked_document_stores_vector(self) -> None:
        meta = self._make_metadata()
        vec = [0.1, 0.2, 0.3]
        chunk = ChunkedDocument(text="some text here", metadata=meta, vector=vec)
        assert chunk.vector == vec

    def test_chunked_document_metadata_fields(self) -> None:
        meta = self._make_metadata()
        chunk = ChunkedDocument(text="text", metadata=meta)
        assert chunk.metadata["doc_id"] == "doc-uuid"
        assert chunk.metadata["file_type"] == "txt"
        assert chunk.metadata["tags"] == []
        assert chunk.metadata["page_number"] == -1

    def test_chunked_document_model_copy_update(self) -> None:
        meta = self._make_metadata()
        chunk = ChunkedDocument(text="text", metadata=meta)
        updated = chunk.model_copy(update={"vector": [1.0, 2.0]})
        assert updated.vector == [1.0, 2.0]
        assert chunk.vector == []  # original unchanged


class TestChunkMetadataTypedDict:
    def test_chunk_metadata_is_dict_subtype(self) -> None:
        meta: ChunkMetadata = {
            "doc_id": "d1",
            "chunk_id": "c1",
            "source_path": "/tmp/x.pdf",
            "filename": "x.pdf",
            "file_type": "pdf",
            "title": "Some title",
            "page_number": 0,
            "chunk_index": 0,
            "total_chunks": 5,
            "char_count": 300,
            "ingested_at": "2025-01-15T10:00:00Z",
            "tags": ["keyword1"],
        }
        # TypedDict instances are plain dicts at runtime.
        assert isinstance(meta, dict)
        assert meta["file_type"] == "pdf"
        assert meta["tags"] == ["keyword1"]
