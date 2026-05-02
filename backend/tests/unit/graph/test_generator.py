"""Unit tests for the Generator node.

Covers:
1. Generates answer using graded_docs as context
2. Falls back to retrieved_docs when graded_docs is empty and web_fallback_used True
3. Appends HumanMessage and AIMessage to state["messages"]
4. LLM failure → fallback answer, empty citations, confidence 0.0 (error path)
5. confidence is within [0.0, 1.0]
6. steps_taken contains generator entry with duration_ms
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage

from src.graph.nodes.generator import _build_citations, _GeneratorOutput, generator_node


def _make_doc(content: str, chunk_id: str = "c1", source: str = "/data/doc.pdf") -> Document:
    return Document(
        page_content=content,
        metadata={"chunk_id": chunk_id, "source": source},
    )


def _make_state(
    graded_docs: list[Document],
    retrieved_docs: list[Document] | None = None,
    web_fallback_used: bool = False,
    messages: list[Any] | None = None,
    query: str = "What is X?",
) -> dict[str, Any]:
    return {
        "session_id": "s1",
        "query": query,
        "filters": None,
        "k": None,
        "query_type": "factual",
        "retrieval_strategy": "hybrid",
        "query_rewritten": None,
        "retrieved_docs": retrieved_docs or [],
        "web_fallback_used": web_fallback_used,
        "grader_scores": [],
        "graded_docs": graded_docs,
        "all_below_threshold": False,
        "retry_count": 0,
        "answer": None,
        "citations": [],
        "confidence": None,
        "critic_score": None,
        "messages": messages or [],
        "steps_taken": [],
    }


def _mock_llm(answer: str = "Paris", confidence: float = 0.9) -> MagicMock:
    output = _GeneratorOutput(answer=answer, confidence=confidence, reasoning="test")
    chain_mock = MagicMock()
    chain_mock.ainvoke = AsyncMock(return_value=output)
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    return llm


# ---------------------------------------------------------------------------
# Test 1: generates answer using graded_docs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generates_answer_from_graded_docs() -> None:
    graded_docs = [_make_doc("Paris is the capital of France.", "c1")]
    llm = _mock_llm(answer="Paris is the capital.", confidence=0.95)
    state = _make_state(graded_docs=graded_docs)

    result = await generator_node(state, llm=llm)  # type: ignore[arg-type]

    assert result["answer"] == "Paris is the capital."
    assert len(result["citations"]) == 1
    assert result["citations"][0].chunk_id == "c1"
    assert result["citations"][0].filename == "doc.pdf"


# ---------------------------------------------------------------------------
# Test 2: falls back to retrieved_docs when graded_docs empty + web_fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_to_retrieved_docs_when_web_fallback() -> None:
    retrieved = [_make_doc("Web result about X.", "w1", "/web/result.txt")]
    llm = _mock_llm(answer="X is described in web results.", confidence=0.7)
    state = _make_state(
        graded_docs=[],
        retrieved_docs=retrieved,
        web_fallback_used=True,
    )

    result = await generator_node(state, llm=llm)  # type: ignore[arg-type]

    assert result["answer"] == "X is described in web results."
    assert len(result["citations"]) == 1
    assert result["citations"][0].chunk_id == "w1"


# ---------------------------------------------------------------------------
# Test 3: appends HumanMessage and AIMessage to messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_appends_human_and_ai_messages() -> None:
    graded_docs = [_make_doc("Some context.")]
    llm = _mock_llm(answer="The answer.")
    state = _make_state(graded_docs=graded_docs, query="What is Y?")

    result = await generator_node(state, llm=llm)  # type: ignore[arg-type]

    msgs = result["messages"]
    assert len(msgs) == 2
    assert isinstance(msgs[0], HumanMessage)
    assert msgs[0].content == "What is Y?"
    assert isinstance(msgs[1], AIMessage)
    assert msgs[1].content == "The answer."


# ---------------------------------------------------------------------------
# Test 4: LLM failure → fallback answer, empty citations, confidence 0.0
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_failure_returns_fallback() -> None:
    chain_mock = MagicMock()
    chain_mock.ainvoke = AsyncMock(side_effect=RuntimeError("Azure down"))
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    state = _make_state(graded_docs=[_make_doc("context")])

    result = await generator_node(state, llm=llm)  # type: ignore[arg-type]

    assert "error" in result["answer"].lower()
    assert result["citations"] == []
    assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Test 5: confidence clamped to [0.0, 1.0]
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confidence_clamped() -> None:
    # LLM returns a value outside bounds — node must clamp it
    output = _GeneratorOutput(answer="answer", confidence=1.5, reasoning="test")
    chain_mock = MagicMock()
    chain_mock.ainvoke = AsyncMock(return_value=output)
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    state = _make_state(graded_docs=[_make_doc("context")])

    result = await generator_node(state, llm=llm)  # type: ignore[arg-type]

    assert 0.0 <= result["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# Test 6: steps_taken contains generator entry with duration_ms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_steps_taken_contains_generator_entry() -> None:
    graded_docs = [_make_doc("context")]
    llm = _mock_llm()
    state = _make_state(graded_docs=graded_docs)

    result = await generator_node(state, llm=llm)  # type: ignore[arg-type]

    assert len(result["steps_taken"]) == 1
    step = result["steps_taken"][0]
    assert step.startswith("generator:")
    assert "ms" in step


# ---------------------------------------------------------------------------
# Test 7: grader_score and retrieval_score are independent fields
# ---------------------------------------------------------------------------


def test_build_citations_grader_score_in_separate_field() -> None:
    doc = Document(
        page_content="content",
        metadata={
            "chunk_id": "c1",
            "source": "/data/doc.pdf",
            "grader_score": 0.85,
            "retrieval_score": 0.42,
        },
    )
    citations = _build_citations([doc])
    assert len(citations) == 1
    assert citations[0].retrieval_score == 0.42  # direct read, not grader override
    assert citations[0].grader_score == 0.85


def test_build_citations_grader_score_none_when_absent() -> None:
    doc = Document(
        page_content="content",
        metadata={
            "chunk_id": "c2",
            "source": "/data/doc.pdf",
            "retrieval_score": 0.63,
        },
    )
    citations = _build_citations([doc])
    assert len(citations) == 1
    assert citations[0].retrieval_score == 0.63
    assert citations[0].grader_score is None


def test_build_citations_web_docs_use_retrieval_score() -> None:
    """Web docs set 'retrieval_score' directly (no 'score' key after T03)."""
    doc = Document(
        page_content="web content",
        metadata={
            "chunk_id": "",
            "source": "https://example.com/page",
            "retrieval_score": 0.71,
        },
    )
    citations = _build_citations([doc])
    assert len(citations) == 1
    assert citations[0].retrieval_score == 0.71
    assert citations[0].grader_score is None
