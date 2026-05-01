"""Graph builder — compiles the LangGraph StateGraph with injected singletons.

This is the sole place where the graph topology is declared.  It is called
once during FastAPI lifespan startup and the compiled graph is stored on
app.state.compiled_graph.

Governed by: ADR-004 (amended) — LangGraph version lock, AsyncSqliteSaver
import path, stream_mode decision, and single-worker constraint.
"""

import functools
from pathlib import Path
from typing import Any

import aiosqlite
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from tavily import TavilyClient

from src.config import Settings
from src.graph.edges import route_after_critic, route_after_grader
from src.graph.node_names import CRITIC, GENERATOR, GRADER, RETRIEVER, ROUTER
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

    Note:
        ``tavily_client`` is ``None`` when ``TAVILY_API_KEY`` is not configured;
        the retriever node handles this gracefully by logging a warning and
        skipping web-search augmentation.
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

    tavily_client: TavilyClient | None = (
        TavilyClient(api_key=settings.tavily_api_key.get_secret_value())
        if settings.tavily_api_key.get_secret_value()
        else None
    )
    web_search_enabled: bool = tavily_client is not None

    async def _retriever_node(state: AgentState) -> dict[str, Any]:
        return await retriever_node(state, retriever=retriever, tavily_client=tavily_client)

    async def _grader_node(state: AgentState) -> dict[str, Any]:
        return await grader_node(state, llm=llm, web_search_enabled=web_search_enabled)

    async def _generator_node(state: AgentState) -> dict[str, Any]:
        return await generator_node(state, llm=llm_4o)

    async def _critic_node(state: AgentState) -> dict[str, Any]:
        return await critic_node(state, llm=llm, web_search_enabled=web_search_enabled)

    graph: StateGraph = StateGraph(AgentState)

    graph.add_node(ROUTER, _router_node)
    graph.add_node(RETRIEVER, _retriever_node)
    graph.add_node(GRADER, _grader_node)
    graph.add_node(GENERATOR, _generator_node)
    graph.add_node(CRITIC, _critic_node)

    graph.set_entry_point(ROUTER)

    graph.add_edge(ROUTER, RETRIEVER)
    graph.add_edge(RETRIEVER, GRADER)
    graph.add_conditional_edges(
        GRADER,
        functools.partial(route_after_grader, settings=settings),
        {GENERATOR: GENERATOR, RETRIEVER: RETRIEVER},
    )
    graph.add_edge(GENERATOR, CRITIC)
    graph.add_conditional_edges(
        CRITIC,
        functools.partial(route_after_critic, settings=settings),
        {"end": END, RETRIEVER: RETRIEVER},
    )

    checkpointer_path = Path(settings.sqlite_checkpointer_path)
    checkpointer_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiosqlite.connect(str(checkpointer_path)) as _db:
            await _db.execute(
                "DELETE FROM checkpoints WHERE thread_ts < datetime('now', ? || ' days')",
                (f"-{settings.sqlite_checkpointer_ttl_days}",),
            )
            await _db.commit()
    except Exception:
        pass  # table may not exist on first startup; cleanup is best-effort

    conn = aiosqlite.connect(str(checkpointer_path))
    import importlib.metadata  # noqa: PLC0415  # local import to keep version check near the patch it guards

    _ckpt_ver = importlib.metadata.version("langgraph-checkpoint-sqlite")
    assert _ckpt_ver < "2.0.12", (
        f"Remove conn.is_alive monkey-patch: fixed upstream in langgraph-checkpoint-sqlite>=2.0.12 (installed: {_ckpt_ver})"
    )
    if not hasattr(conn, "is_alive"):
        conn.is_alive = conn._thread.is_alive  # type: ignore[attr-defined]  # aiosqlite 0.22 removed is_alive(); langgraph-checkpoint-sqlite 2.0.11 calls it in setup()
    checkpointer = AsyncSqliteSaver(conn)

    return graph.compile(checkpointer=checkpointer)
