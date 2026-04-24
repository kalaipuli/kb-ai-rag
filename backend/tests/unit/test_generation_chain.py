"""Unit tests for src/generation/chain.py.

All external I/O (HybridRetriever, AzureChatOpenAI) is mocked so no real
network calls are made.

The LCEL pipeline ``QA_PROMPT | llm | StrOutputParser()`` is exercised by
patching ``AzureChatOpenAI`` with a ``RunnableLambda`` that returns an
``AIMessage``.  ``RunnableLambda`` implements ``__or__`` correctly so the full
``|`` composition works end-to-end without hitting Azure.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.asyncio
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from pydantic import SecretStr

from src.exceptions import GenerationError
from src.generation.chain import GenerationChain, KBRetriever
from src.ingestion.models import ChunkMetadata
from src.retrieval.models import RetrievalResult
from src.schemas.generation import GenerationResult

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_chunk_metadata(chunk_id: str = "c1") -> ChunkMetadata:
    return ChunkMetadata(
        doc_id="doc-1",
        chunk_id=chunk_id,
        source_path="/data/geo.pdf",
        filename="geo.pdf",
        file_type="pdf",
        title="Geography",
        page_number=1,
        chunk_index=0,
        total_chunks=3,
        char_count=200,
        ingested_at="2025-01-15T10:00:00Z",
        tags=[],
    )


def _make_retrieval_result(
    chunk_id: str = "c1",
    text: str = "Paris is the capital of France.",
    score: float = 2.5,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        text=text,
        metadata=_make_chunk_metadata(chunk_id),
        score=score,
        rank=0,
    )


def _make_settings() -> MagicMock:
    s = MagicMock()
    s.azure_openai_endpoint = "https://test.openai.azure.com/"
    s.azure_openai_api_key = SecretStr("test-key")
    s.azure_chat_deployment = "gpt-4o"
    s.azure_openai_api_version = "2024-08-01-preview"
    return s


def _make_hybrid_retriever(results: list[RetrievalResult] | None = None) -> MagicMock:
    hybrid = MagicMock()
    hybrid.retrieve = AsyncMock(return_value=results or [])
    return hybrid


def _make_llm_runnable(answer: str = "Mocked answer.") -> RunnableLambda:  # type: ignore[type-arg]
    """Return a RunnableLambda that acts as the LLM in the LCEL pipeline.

    ``RunnableLambda`` implements ``__or__`` so ``QA_PROMPT | runnable |
    StrOutputParser()`` composes correctly without hitting Azure.
    """

    async def _fake_llm(input_data: object) -> AIMessage:
        return AIMessage(content=answer)

    return RunnableLambda(_fake_llm)


# ---------------------------------------------------------------------------
# KBRetriever tests
# ---------------------------------------------------------------------------


class TestKBRetriever:
    @pytest.mark.asyncio
    async def test_kb_retriever_aget_returns_documents(self) -> None:
        """_aget_relevant_documents converts RetrievalResults to LangChain Documents."""
        r1 = _make_retrieval_result("c1", "text one", 1.0)
        r2 = _make_retrieval_result("c2", "text two", 0.8)
        hybrid = _make_hybrid_retriever([r1, r2])

        retriever = KBRetriever(hybrid_retriever=hybrid, k=5, filters=None)
        run_manager = MagicMock()
        docs = await retriever._aget_relevant_documents("test query", run_manager=run_manager)

        assert len(docs) == 2
        assert docs[0].page_content == "text one"
        assert docs[1].page_content == "text two"
        assert docs[0].metadata["chunk_id"] == "c1"
        assert docs[0].metadata["filename"] == "geo.pdf"
        assert docs[0].metadata["source_path"] == "/data/geo.pdf"
        assert docs[0].metadata["page_number"] == 1
        assert docs[0].metadata["score"] == 1.0

    def test_kb_retriever_get_raises(self) -> None:
        """_get_relevant_documents must raise NotImplementedError (sync path forbidden)."""
        hybrid = _make_hybrid_retriever()
        retriever = KBRetriever(hybrid_retriever=hybrid)
        run_manager = MagicMock()

        with pytest.raises(NotImplementedError, match="Use async only"):
            retriever._get_relevant_documents("query", run_manager=run_manager)


# ---------------------------------------------------------------------------
# GenerationChain tests
# ---------------------------------------------------------------------------


def _source_doc(
    chunk_id: str = "c1",
    filename: str = "geo.pdf",
    source_path: str = "/data/geo.pdf",
    page_number: int | None = 1,
    score: float = 2.5,
) -> Document:
    return Document(
        page_content="Paris is the capital of France.",
        metadata={
            "chunk_id": chunk_id,
            "filename": filename,
            "source_path": source_path,
            "page_number": page_number,
            "score": score,
        },
    )


class TestGenerationChain:
    @pytest.mark.asyncio
    async def test_generation_chain_returns_result(self, mocker: MagicMock) -> None:
        """GenerationChain.generate returns a valid GenerationResult with correct fields."""
        settings = _make_settings()
        hybrid = _make_hybrid_retriever([_make_retrieval_result("c1", score=2.5)])

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=_make_llm_runnable("Paris is the capital."),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)
        result = await gen_chain.generate("What is the capital of France?")

        assert isinstance(result, GenerationResult)
        assert result.answer == "Paris is the capital."
        assert len(result.citations) == 1
        assert result.citations[0].filename == "geo.pdf"
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_generation_chain_deduplicates_citations(self, mocker: MagicMock) -> None:
        """Same chunk_id appearing twice in retrieved docs yields only one citation."""
        settings = _make_settings()
        # Two results with identical chunk_id — only one citation expected.
        hybrid = _make_hybrid_retriever(
            [
                _make_retrieval_result("c1", score=1.0),
                _make_retrieval_result("c1", score=0.9),
            ]
        )

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=_make_llm_runnable("Deduplicated."),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)
        result = await gen_chain.generate("question")

        assert len(result.citations) == 1
        assert result.citations[0].chunk_id == "c1"

    @pytest.mark.asyncio
    async def test_generation_chain_no_docs_confidence_zero(self, mocker: MagicMock) -> None:
        """When retrieval returns no docs, confidence must be exactly 0.0."""
        settings = _make_settings()
        hybrid = _make_hybrid_retriever([])

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=_make_llm_runnable("No docs."),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)
        result = await gen_chain.generate("any question")

        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_generation_chain_propagates_error(self, mocker: MagicMock) -> None:
        """If retrieval raises, GenerationError is raised with the original message."""
        settings = _make_settings()
        hybrid = MagicMock()
        hybrid.retrieve = AsyncMock(side_effect=Exception("retrieval exploded"))

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=_make_llm_runnable(),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)

        with pytest.raises(GenerationError, match="retrieval exploded"):
            await gen_chain.generate("broken question")

    @pytest.mark.asyncio
    async def test_generation_chain_multiple_citations_order_preserved(
        self, mocker: MagicMock
    ) -> None:
        """Citations are returned in retrieval order (first occurrence of each chunk_id)."""
        settings = _make_settings()
        # c2 first, then c1, then c2 again — expected order: c2, c1
        hybrid = _make_hybrid_retriever(
            [
                _make_retrieval_result("c2", score=1.5),
                _make_retrieval_result("c1", score=1.2),
                _make_retrieval_result("c2", score=0.8),  # duplicate — skipped
            ]
        )

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=_make_llm_runnable("Multi."),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)
        result = await gen_chain.generate("question")

        assert len(result.citations) == 2
        assert result.citations[0].chunk_id == "c2"
        assert result.citations[1].chunk_id == "c1"

    @pytest.mark.asyncio
    async def test_generation_chain_confidence_in_unit_interval(
        self, mocker: MagicMock
    ) -> None:
        """Confidence is clamped to [0.0, 1.0] regardless of raw cross-encoder scores."""
        settings = _make_settings()
        # Extremely high score — sigmoid output approaches 1.0 but must not exceed it.
        hybrid = _make_hybrid_retriever(
            [_make_retrieval_result("c1", score=1000.0)]
        )

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=_make_llm_runnable("High confidence."),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)
        result = await gen_chain.generate("question")

        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_generation_chain_page_number_none_for_sentinel(
        self, mocker: MagicMock
    ) -> None:
        """page_number -1 sentinel from ChunkMetadata maps to None in Citation."""
        settings = _make_settings()
        # Build a result whose page_number is -1 (TXT source, no pages)
        meta = _make_chunk_metadata("c1")
        meta["page_number"] = -1
        result_no_page = RetrievalResult(
            chunk_id="c1",
            text="Some text.",
            metadata=meta,
            score=1.0,
            rank=0,
        )
        hybrid = _make_hybrid_retriever([result_no_page])

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=_make_llm_runnable("Answer."),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)
        result = await gen_chain.generate("question")

        assert len(result.citations) == 1
        assert result.citations[0].page_number is None

    @pytest.mark.asyncio
    async def test_generation_chain_llm_error_raises_generation_error(
        self, mocker: MagicMock
    ) -> None:
        """If the LCEL chain ainvoke raises, GenerationError wraps the exception."""
        settings = _make_settings()
        hybrid = _make_hybrid_retriever([_make_retrieval_result("c1", score=1.0)])

        # Use a RunnableLambda that raises rather than returning a response.
        async def _failing_llm(input_data: object) -> AIMessage:
            raise RuntimeError("LLM failed")

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=RunnableLambda(_failing_llm),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)

        with pytest.raises(GenerationError, match="LLM failed"):
            await gen_chain.generate("question")

    @pytest.mark.asyncio
    async def test_generation_chain_negative_score_confidence_low(
        self, mocker: MagicMock
    ) -> None:
        """Strongly negative cross-encoder score yields confidence in [0.0, 1.0) and below 0.1.

        The ms-marco-MiniLM-L-6-v2 cross-encoder returns raw logits that are
        frequently negative for irrelevant passages.  sigmoid(-5.0) ≈ 0.0067,
        so confidence must be well below 0.1 rather than wrapping or clamping
        to an invalid value.
        """
        settings = _make_settings()
        hybrid = _make_hybrid_retriever(
            [_make_retrieval_result("c1", score=-5.0)]
        )

        mocker.patch(
            "src.generation.chain.AzureChatOpenAI",
            return_value=_make_llm_runnable("Low confidence answer."),
        )

        gen_chain = GenerationChain(settings=settings, hybrid_retriever=hybrid)
        result = await gen_chain.generate("irrelevant question")

        assert 0.0 <= result.confidence < 0.1
