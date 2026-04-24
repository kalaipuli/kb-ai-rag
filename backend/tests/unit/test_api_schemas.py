"""Unit tests for API request/response schemas."""

import pytest
from pydantic import ValidationError

from src.api.schemas import (
    CitationItem,
    CollectionInfo,
    CollectionsResponse,
    IngestAcceptedResponse,
    IngestRequest,
    QueryRequest,
    QueryResponse,
)


class TestQueryRequest:
    def test_minimal_creation(self) -> None:
        req = QueryRequest(query="what is RAG?")
        assert req.query == "what is RAG?"
        assert req.filters is None
        assert req.k is None

    def test_with_all_fields(self) -> None:
        req = QueryRequest(query="q", filters={"file_type": "pdf"}, k=5)
        assert req.filters == {"file_type": "pdf"}
        assert req.k == 5

    def test_empty_query_raises_validation_error(self) -> None:
        """query='' violates min_length=1 and must be rejected by Pydantic."""
        with pytest.raises(ValidationError):
            QueryRequest(query="")


class TestCitationItem:
    def test_creation(self) -> None:
        c = CitationItem(
            chunk_id="abc",
            filename="doc.pdf",
            source_path="/data/doc.pdf",
            page_number=3,
        )
        assert c.page_number == 3


class TestQueryResponse:
    def test_creation_with_citations(self) -> None:
        citation = CitationItem(
            chunk_id="c1",
            filename="f.pdf",
            source_path="/f.pdf",
            page_number=0,
        )
        resp = QueryResponse(query="q", answer="answer", citations=[citation], confidence=0.85)
        assert resp.confidence == 0.85
        assert len(resp.citations) == 1

    def test_empty_citations(self) -> None:
        resp = QueryResponse(query="q", answer="idk", citations=[], confidence=0.1)
        assert resp.citations == []


class TestIngestRequest:
    def test_data_dir_defaults_to_none(self) -> None:
        """IngestRequest with no arguments has data_dir=None (fully optional)."""
        req = IngestRequest()
        assert req.data_dir is None

    def test_data_dir_is_set_when_provided(self) -> None:
        """Providing data_dir stores the value on the model."""
        req = IngestRequest(data_dir="/mnt/docs")
        assert req.data_dir == "/mnt/docs"


class TestIngestAcceptedResponse:
    def test_required_fields_serialise_correctly(self) -> None:
        """status and message are present and round-trip through model_dump."""
        resp = IngestAcceptedResponse(status="accepted", message="Ingestion started for /data")
        dumped = resp.model_dump()
        assert dumped["status"] == "accepted"
        assert dumped["message"] == "Ingestion started for /data"

    def test_status_field(self) -> None:
        """status field holds the provided string value."""
        resp = IngestAcceptedResponse(status="accepted", message="ok")
        assert resp.status == "accepted"

    def test_message_field(self) -> None:
        """message field holds the provided string value."""
        resp = IngestAcceptedResponse(status="accepted", message="Ingestion started for /tmp")
        assert resp.message == "Ingestion started for /tmp"


class TestCollectionInfo:
    def test_all_required_fields_present(self) -> None:
        """CollectionInfo stores name, document_count, and vector_count."""
        info = CollectionInfo(name="kb_documents", document_count=100, vector_count=100)
        assert info.name == "kb_documents"
        assert info.document_count == 100
        assert info.vector_count == 100

    def test_correct_types(self) -> None:
        """name is str; document_count and vector_count are int."""
        info = CollectionInfo(name="col", document_count=0, vector_count=0)
        assert isinstance(info.name, str)
        assert isinstance(info.document_count, int)
        assert isinstance(info.vector_count, int)

    def test_zeroed_counts_are_valid(self) -> None:
        """Zero counts are valid (e.g. empty or partially-failed collection)."""
        info = CollectionInfo(name="empty", document_count=0, vector_count=0)
        assert info.document_count == 0
        assert info.vector_count == 0


class TestCollectionsResponse:
    def test_collections_is_a_list_of_collection_info(self) -> None:
        """collections field contains CollectionInfo instances."""
        items = [
            CollectionInfo(name="col_a", document_count=5, vector_count=5),
            CollectionInfo(name="col_b", document_count=10, vector_count=10),
        ]
        resp = CollectionsResponse(collections=items)
        assert len(resp.collections) == 2
        assert all(isinstance(c, CollectionInfo) for c in resp.collections)

    def test_empty_collections_list_is_valid(self) -> None:
        """An empty collections list is a valid response (no collections indexed yet)."""
        resp = CollectionsResponse(collections=[])
        assert resp.collections == []
