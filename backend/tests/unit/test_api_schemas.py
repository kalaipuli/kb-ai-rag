"""Unit tests for API request/response schemas."""

from src.api.schemas import CitationItem, QueryRequest, QueryResponse


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
