"""FastAPI dependency functions for Phase 1d routes.

All singleton services (GenerationChain, AsyncQdrantClient) are initialized
in the app lifespan and exposed via these dependency functions.
"""

from typing import Annotated

from fastapi import Depends, Request
from langchain_openai import AzureChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from qdrant_client import AsyncQdrantClient

from src.config import Settings, get_settings
from src.generation.chain import GenerationChain
from src.ingestion.embedder import Embedder

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_generation_chain(request: Request) -> GenerationChain:
    return request.app.state.generation_chain  # type: ignore[no-any-return]


def get_qdrant_client(request: Request) -> AsyncQdrantClient:
    return request.app.state.qdrant_client  # type: ignore[no-any-return]


def get_embedder(request: Request) -> Embedder:
    return request.app.state.embedder  # type: ignore[no-any-return]


GenerationChainDep = Annotated[GenerationChain, Depends(get_generation_chain)]
QdrantClientDep = Annotated[AsyncQdrantClient, Depends(get_qdrant_client)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]


def get_compiled_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.compiled_graph  # type: ignore[no-any-return]


CompiledGraphDep = Annotated[CompiledStateGraph, Depends(get_compiled_graph)]


def get_llm_chat(request: Request) -> AzureChatOpenAI:
    return request.app.state.llm_chat  # type: ignore[no-any-return]


def get_llm_4o(request: Request) -> AzureChatOpenAI:
    return request.app.state.llm_4o  # type: ignore[no-any-return]


LLMChatDep = Annotated[AzureChatOpenAI, Depends(get_llm_chat)]
LLM4oDep = Annotated[AzureChatOpenAI, Depends(get_llm_4o)]
