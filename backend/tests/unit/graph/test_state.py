"""Unit tests for AgentState TypedDict schema (src/graph/state.py).

Tests cover:
  1. retrieved_docs reducer — operator.add appends, does not overwrite.
  2. messages reducer   — add_messages deduplicates by message ID.
  3. steps_taken reducer — operator.add appends string entries.
  4. Schema completeness — all 19 required field names are present.
"""

from __future__ import annotations

import operator

from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages

from src.graph.state import AgentState

# ---------------------------------------------------------------------------
# 1. retrieved_docs reducer: operator.add appends across partial updates
# ---------------------------------------------------------------------------


def test_retrieved_docs_reducer_appends() -> None:
    """operator.add on two lists produces a combined list, not a replacement."""
    from langchain_core.documents import Document

    first_batch: list[Document] = [Document(page_content="chunk-1")]
    second_batch: list[Document] = [Document(page_content="chunk-2")]

    merged = operator.add(first_batch, second_batch)

    assert len(merged) == 2
    assert merged[0].page_content == "chunk-1"
    assert merged[1].page_content == "chunk-2"


def test_retrieved_docs_reducer_does_not_overwrite() -> None:
    """Reducer result is distinct from both inputs — no in-place mutation."""
    from langchain_core.documents import Document

    a: list[Document] = [Document(page_content="a")]
    b: list[Document] = [Document(page_content="b")]

    merged = operator.add(a, b)

    # Original lists must remain unchanged
    assert len(a) == 1
    assert len(b) == 1
    assert len(merged) == 2


# ---------------------------------------------------------------------------
# 2. messages reducer: add_messages deduplicates by message ID
# ---------------------------------------------------------------------------


def test_messages_reducer_deduplicates_by_id() -> None:
    """Adding the same message twice results in a single entry."""
    msg = HumanMessage(content="hello", id="msg-001")
    existing: list[HumanMessage] = [msg]

    # Adding the same message (same id) a second time
    result = add_messages(existing, [msg])  # type: ignore[arg-type]

    assert len(result) == 1
    assert result[0].content == "hello"


def test_messages_reducer_adds_new_message() -> None:
    """A message with a new ID is appended to the existing list."""
    first = HumanMessage(content="first", id="msg-001")
    second = HumanMessage(content="second", id="msg-002")

    result = add_messages([first], [second])  # type: ignore[arg-type]

    assert len(result) == 2
    assert result[0].id == "msg-001"
    assert result[1].id == "msg-002"


# ---------------------------------------------------------------------------
# 3. steps_taken reducer: operator.add appends string entries
# ---------------------------------------------------------------------------


def test_steps_taken_reducer_appends_strings() -> None:
    """operator.add on string lists appends without overwriting."""
    first: list[str] = ["router"]
    second: list[str] = ["retriever"]

    merged = operator.add(first, second)

    assert merged == ["router", "retriever"]


def test_steps_taken_reducer_multiple_updates() -> None:
    """Successive operator.add calls accumulate all entries."""
    steps: list[str] = []
    steps = operator.add(steps, ["router"])
    steps = operator.add(steps, ["retriever"])
    steps = operator.add(steps, ["grader", "generator"])

    assert steps == ["router", "retriever", "grader", "generator"]


# ---------------------------------------------------------------------------
# 4. Schema completeness: all 19 required fields must be present
# ---------------------------------------------------------------------------

EXPECTED_FIELDS = {
    # Input
    "session_id",
    "query",
    "filters",
    "k",
    # Router
    "query_type",
    "retrieval_strategy",
    "query_rewritten",
    # Retriever
    "retrieved_docs",
    "web_fallback_used",
    # Grader
    "grader_scores",
    "graded_docs",
    "all_below_threshold",
    "retry_count",
    # Generator
    "answer",
    "citations",
    "confidence",
    # Critic
    "critic_score",
    # Conversation
    "messages",
    # Observability
    "steps_taken",
}


def test_agent_state_has_all_required_fields() -> None:
    """AgentState.__annotations__ must declare every field in the schema."""
    annotations = AgentState.__annotations__
    missing = EXPECTED_FIELDS - set(annotations.keys())
    assert not missing, f"Missing fields in AgentState: {missing}"


def test_agent_state_field_count() -> None:
    """AgentState must declare exactly 19 fields — no accidental additions."""
    assert len(AgentState.__annotations__) == len(EXPECTED_FIELDS)
