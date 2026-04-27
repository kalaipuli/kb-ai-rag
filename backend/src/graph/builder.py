"""Graph builder — compiles the LangGraph StateGraph with injected singletons.

This is the sole place where the graph topology is declared.  It is called
once during FastAPI lifespan startup and the compiled graph is stored on
app.state.compiled_graph.

Governed by: ADR-004 (amended) — LangGraph version lock, AsyncSqliteSaver
import path, stream_mode decision, and single-worker constraint.
"""

from pathlib import Path
from typing import Any

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.config import Settings
from src.graph.edges import route_after_critic, route_after_grader
from src.graph.nodes.critic import critic_node
from src.graph.nodes.generator import generator_node
from src.graph.nodes.grader import grader_node
from src.graph.nodes.retriever import retriever_node
from src.graph.nodes.router import router_node
from src.graph.state import AgentState
from src.retrieval.retriever import HybridRetriever


async def build_graph(settings: Settings, retriever: HybridRetriever) -> CompiledStateGraph:
    """Compile the agentic StateGraph and return it with an AsyncSqliteSaver checkpointer.

    Must be called from an async context (FastAPI lifespan).  The retriever is
    captured in a closure so that retriever_node does not import from retrieval/
    directly — dependency direction is enforced here.

    Args:
        settings: Application settings (provides sqlite_checkpointer_path).
        retriever: HybridRetriever singleton from app.state.

    Returns:
        A compiled LangGraph StateGraph ready for astream() invocation.
    """
    async def _retriever_node(state: AgentState) -> dict[str, Any]:
        """Closure wrapping retriever_node; will receive the real retriever in 2c."""
        _ = retriever  # injected; used in Phase 2c implementation
        return await retriever_node(state)

    graph: StateGraph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("retriever", _retriever_node)
    graph.add_node("grader", grader_node)
    graph.add_node("generator", generator_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("router")

    graph.add_edge("router", "retriever")
    graph.add_edge("retriever", "grader")
    graph.add_conditional_edges(
        "grader",
        route_after_grader,
        {"generator": "generator", "retriever": "retriever"},
    )
    graph.add_edge("generator", "critic")
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {"end": END, "retriever": "retriever"},
    )

    checkpointer_path = Path(settings.sqlite_checkpointer_path)
    checkpointer_path.parent.mkdir(parents=True, exist_ok=True)
    conn = aiosqlite.connect(str(checkpointer_path))
    if not hasattr(conn, "is_alive"):
        conn.is_alive = conn._thread.is_alive  # type: ignore[attr-defined]  # aiosqlite 0.22 removed is_alive(); langgraph-checkpoint-sqlite 2.0.11 calls it in setup() — remove when langgraph-checkpoint-sqlite >= 2.0.12
    checkpointer = AsyncSqliteSaver(conn)

    return graph.compile(checkpointer=checkpointer)
