"""Unit tests for the Grader node.

Covers:
1. All scores above threshold → graded_docs contains all docs; all_below_threshold False
2. All scores below threshold → graded_docs empty; all_below_threshold True
3. Mixed scores → only above-threshold docs in graded_docs
4. retry_count incremented by 1 from incoming value
5. LLM batch failure for one batch only (partial failure) → failed chunks get 0.0, passing batch preserved
6. steps_taken contains grader entry with duration_ms
7. empty retrieved_docs → no batch call, all_below_threshold False
8. all batches fail → GraderError raised
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from src.exceptions import GraderError
from src.graph.nodes.grader import _GradeDoc, grader_node


def _make_doc(content: str, chunk_id: str = "c1") -> Document:
    return Document(page_content=content, metadata={"chunk_id": chunk_id})


def _make_state(
    docs: list[Document],
    query: str = "What is X?",
    retry_count: int = 0,
    web_fallback_used: bool = False,
) -> dict[str, Any]:
    return {
        "session_id": "s1",
        "query": query,
        "filters": None,
        "k": None,
        "query_type": "factual",
        "retrieval_strategy": "hybrid",
        "query_rewritten": None,
        "retrieved_docs": docs,
        "web_fallback_used": web_fallback_used,
        "grader_scores": [],
        "graded_docs": [],
        "all_below_threshold": False,
        "retry_count": retry_count,
        "answer": None,
        "citations": [],
        "confidence": None,
        "critic_score": None,
        "messages": [],
        "steps_taken": [],
    }


def _mock_llm_with_scores(scores: list[float]) -> MagicMock:
    """Return a mock LLM whose batch() yields _GradeDoc results for the given scores."""
    grade_results = [_GradeDoc(score=s, reasoning="test") for s in scores]
    chain_mock = MagicMock()
    chain_mock.batch = MagicMock(return_value=grade_results)
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    return llm


# ---------------------------------------------------------------------------
# Test 1: all scores above threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_above_threshold() -> None:
    docs = [_make_doc("doc A", "c1"), _make_doc("doc B", "c2")]
    llm = _mock_llm_with_scores([0.9, 0.8])
    state = _make_state(docs)

    result = await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert len(result["graded_docs"]) == 2
    assert result["all_below_threshold"] is False
    assert result["grader_scores"] == [0.9, 0.8]


# ---------------------------------------------------------------------------
# Test 2: all scores below threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_below_threshold() -> None:
    docs = [_make_doc("doc A", "c1"), _make_doc("doc B", "c2")]
    llm = _mock_llm_with_scores([0.2, 0.1])
    state = _make_state(docs)

    result = await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert result["graded_docs"] == []
    assert result["all_below_threshold"] is True


# ---------------------------------------------------------------------------
# Test 3: mixed scores
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mixed_scores() -> None:
    doc_a = _make_doc("doc A", "c1")
    doc_b = _make_doc("doc B", "c2")
    doc_c = _make_doc("doc C", "c3")
    llm = _mock_llm_with_scores([0.8, 0.3, 0.6])
    state = _make_state([doc_a, doc_b, doc_c])

    result = await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert len(result["graded_docs"]) == 2
    assert doc_a in result["graded_docs"]
    assert doc_c in result["graded_docs"]
    assert doc_b not in result["graded_docs"]
    assert result["all_below_threshold"] is False


# ---------------------------------------------------------------------------
# Test 4: retry_count incremented by 1
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_count_incremented() -> None:
    docs = [_make_doc("doc A")]
    llm = _mock_llm_with_scores([0.7])
    state = _make_state(docs, retry_count=2)

    result = await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert result["retry_count"] == 3


# ---------------------------------------------------------------------------
# Test 5: partial batch failure — first batch raises, second batch succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_failure_assigns_zero_score() -> None:
    """First batch (docs 0-9) fails → 0.0 scores; second batch succeeds → real scores preserved."""
    # With default grader_batch_size=10, docs 0..9 form batch 1, docs 10..10 form batch 2.
    # We need 11 docs so there are two batches; the first raises, the second succeeds.
    docs_batch1 = [_make_doc(f"doc {i}", f"c{i}") for i in range(10)]
    doc_batch2 = _make_doc("doc 10", "c10")
    all_docs = docs_batch1 + [doc_batch2]

    second_batch_result = [_GradeDoc(score=0.8, reasoning="ok")]
    chain_mock = MagicMock()
    chain_mock.batch = MagicMock(
        side_effect=[RuntimeError("Azure unavailable"), second_batch_result]
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    state = _make_state(all_docs)

    result = await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    # First 10 chunks scored 0.0 due to batch failure; last chunk scored 0.8
    assert result["grader_scores"] == [0.0] * 10 + [0.8]
    assert len(result["graded_docs"]) == 1
    assert result["graded_docs"][0] == doc_batch2


# ---------------------------------------------------------------------------
# Test 6: steps_taken contains grader entry with duration_ms
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_steps_taken_contains_grader_entry() -> None:
    docs = [_make_doc("doc A")]
    llm = _mock_llm_with_scores([0.9])
    state = _make_state(docs)

    result = await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert len(result["steps_taken"]) == 1
    step = result["steps_taken"][0]
    assert step.startswith("grader:")
    assert "ms" in step


# ---------------------------------------------------------------------------
# Test 7: empty retrieved_docs → no batch call, all_below_threshold False
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_docs_no_batch_call() -> None:
    llm = MagicMock()
    chain_mock = MagicMock()
    chain_mock.batch = MagicMock(return_value=[])
    llm.with_structured_output.return_value = chain_mock
    state = _make_state([])

    result = await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert result["graded_docs"] == []
    assert result["grader_scores"] == []
    assert result["all_below_threshold"] is False


# ---------------------------------------------------------------------------
# Test 8: all batches fail → GraderError raised
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_batches_fail_raises_grader_error() -> None:
    docs = [_make_doc("doc A", "c1"), _make_doc("doc B", "c2")]
    chain_mock = MagicMock()
    chain_mock.batch = MagicMock(side_effect=RuntimeError("Azure unavailable"))
    llm = MagicMock()
    llm.with_structured_output.return_value = chain_mock
    state = _make_state(docs)

    with pytest.raises(GraderError):
        await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level


# ---------------------------------------------------------------------------
# Test 9: CRAG escalation — escalates to web on second retry when enabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalates_to_web_on_second_retry_when_enabled() -> None:
    """all_below=True, post-increment retry_count=2, web enabled, not yet used → escalate."""
    docs = [_make_doc("doc A", "c1"), _make_doc("doc B", "c2")]
    llm = _mock_llm_with_scores([0.2, 0.1])
    state = _make_state(docs, retry_count=1, web_fallback_used=False)

    result = await grader_node(state, llm=llm, web_search_enabled=True)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert result.get("retrieval_strategy") == "web"


# ---------------------------------------------------------------------------
# Test 10: no escalation on first retry (post-increment retry_count == 1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_escalation_on_first_retry() -> None:
    """all_below=True, post-increment retry_count=1 — not enough retries to escalate."""
    docs = [_make_doc("doc A", "c1"), _make_doc("doc B", "c2")]
    llm = _mock_llm_with_scores([0.2, 0.1])
    state = _make_state(docs, retry_count=0, web_fallback_used=False)

    result = await grader_node(state, llm=llm, web_search_enabled=True)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert "retrieval_strategy" not in result


# ---------------------------------------------------------------------------
# Test 11: no escalation when web search is disabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_escalation_when_web_disabled() -> None:
    """all_below=True, retry_count>=2, but web_search_enabled=False → no escalation."""
    docs = [_make_doc("doc A", "c1"), _make_doc("doc B", "c2")]
    llm = _mock_llm_with_scores([0.2, 0.1])
    state = _make_state(docs, retry_count=1, web_fallback_used=False)

    result = await grader_node(state, llm=llm, web_search_enabled=False)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert "retrieval_strategy" not in result


# ---------------------------------------------------------------------------
# Test 12: no escalation when web fallback already used
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_escalation_when_web_already_used() -> None:
    """all_below=True, retry_count>=2, web enabled, but web_fallback_used=True → no escalation."""
    docs = [_make_doc("doc A", "c1"), _make_doc("doc B", "c2")]
    llm = _mock_llm_with_scores([0.2, 0.1])
    state = _make_state(docs, retry_count=1, web_fallback_used=True)

    result = await grader_node(state, llm=llm, web_search_enabled=True)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert "retrieval_strategy" not in result


# ---------------------------------------------------------------------------
# Test 13: no escalation when scores are above threshold
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_escalation_when_above_threshold() -> None:
    """all_below=False → escalation must not trigger regardless of retry_count."""
    docs = [_make_doc("doc A", "c1"), _make_doc("doc B", "c2")]
    llm = _mock_llm_with_scores([0.9, 0.8])
    state = _make_state(docs, retry_count=1, web_fallback_used=False)

    result = await grader_node(state, llm=llm, web_search_enabled=True)  # type: ignore[arg-type]  # MagicMock passed for AzureChatOpenAI in unit tests; real typing enforced at integration level

    assert "retrieval_strategy" not in result
