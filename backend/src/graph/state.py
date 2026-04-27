"""AgentState TypedDict — shared interface contract for the Phase 2 LangGraph graph.

Every field in this module is Architect-approved. Do not modify this schema
without a corresponding ADR and Architect sign-off.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.schemas.generation import Citation


class AgentState(TypedDict):
    """Shared state passed between every node in the LangGraph workflow.

    Fields annotated with a reducer (``Annotated[list[...], reducer]``) are
    *append-only* — LangGraph merges partial updates by applying the reducer
    rather than replacing the previous value.  All other fields are plain
    TypedDict entries whose values are replaced on each update.
    """

    # ------------------------------------------------------------------
    # Input (provided by the caller before graph execution begins)
    # ------------------------------------------------------------------
    session_id: str
    query: str
    filters: dict[str, str] | None
    k: int | None

    # ------------------------------------------------------------------
    # Router node outputs
    # ------------------------------------------------------------------
    query_type: Literal["factual", "analytical", "multi_hop", "ambiguous"]
    retrieval_strategy: Literal["dense", "hybrid", "web"]
    query_rewritten: str | None

    # ------------------------------------------------------------------
    # Retriever node outputs
    # reducer: operator.add — partial updates append rather than replace
    # ------------------------------------------------------------------
    retrieved_docs: Annotated[list[Document], operator.add]
    web_fallback_used: bool

    # ------------------------------------------------------------------
    # Grader node outputs
    # ------------------------------------------------------------------
    grader_scores: list[float]
    graded_docs: list[Document]
    all_below_threshold: bool
    retry_count: int

    # ------------------------------------------------------------------
    # Generator node outputs
    # ------------------------------------------------------------------
    answer: str | None
    citations: list[Citation]
    confidence: float | None

    # ------------------------------------------------------------------
    # Critic node outputs
    # ------------------------------------------------------------------
    critic_score: float | None

    # ------------------------------------------------------------------
    # Conversation history
    # reducer: add_messages — deduplicates by message ID
    # ------------------------------------------------------------------
    messages: Annotated[list[BaseMessage], add_messages]

    # ------------------------------------------------------------------
    # Observability
    # reducer: operator.add — each node appends its step label
    # ------------------------------------------------------------------
    steps_taken: Annotated[list[str], operator.add]
