"""LangGraph agentic pipeline package.

Public API:
    build_graph  — compiles the StateGraph with injected singletons
    AgentState   — shared TypedDict state contract
"""

from src.graph.builder import build_graph
from src.graph.state import AgentState

__all__ = ["AgentState", "build_graph"]
