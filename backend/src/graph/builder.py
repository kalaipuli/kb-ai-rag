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
from langchain_openai import AzureChatOpenAI
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
    llm = AzureChatOpenAI(
        azure_deployment="gpt-4o-mini",
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key.get_secret_value(),  # type: ignore[arg-type]  # AzureChatOpenAI.openai_api_key is SecretStr internally; langchain-openai stubs type the alias as SecretStr but the constructor accepts str at runtime
        api_version=settings.azure_openai_api_version,
    )

    llm_4o = AzureChatOpenAI(
        azure_deployment=settings.azure_chat_deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key.get_secret_value(),  # type: ignore[arg-type]  # AzureChatOpenAI.openai_api_key is SecretStr internally; langchain-openai stubs type the alias as SecretStr but the constructor accepts str at runtime
        api_version=settings.azure_openai_api_version,
    )

    async def _router_node(state: AgentState) -> dict[str, Any]:
        return await router_node(state, llm=llm)

    async def _retriever_node(state: AgentState) -> dict[str, Any]:
        return await retriever_node(state, retriever=retriever)

    async def _grader_node(state: AgentState) -> dict[str, Any]:
        return await grader_node(state, llm=llm)

    async def _generator_node(state: AgentState) -> dict[str, Any]:
        return await generator_node(state, llm=llm_4o)

    async def _critic_node(state: AgentState) -> dict[str, Any]:
        return await critic_node(state, llm=llm)

    graph: StateGraph = StateGraph(AgentState)

    graph.add_node("router", _router_node)
    graph.add_node("retriever", _retriever_node)
    graph.add_node("grader", _grader_node)
    graph.add_node("generator", _generator_node)
    graph.add_node("critic", _critic_node)

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
