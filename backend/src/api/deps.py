"""FastAPI dependency functions for Phase 1d routes.

All singleton services (GenerationChain, AsyncQdrantClient) are initialized
in the app lifespan and exposed via these dependency functions.
"""

from typing import Annotated

from fastapi import Depends, Request
from qdrant_client import AsyncQdrantClient

from src.config import Settings, get_settings
from src.generation.chain import GenerationChain

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_generation_chain(request: Request) -> GenerationChain:
    return request.app.state.generation_chain  # type: ignore[no-any-return]


def get_qdrant_client(request: Request) -> AsyncQdrantClient:
    return request.app.state.qdrant_client  # type: ignore[no-any-return]


GenerationChainDep = Annotated[GenerationChain, Depends(get_generation_chain)]
QdrantClientDep = Annotated[AsyncQdrantClient, Depends(get_qdrant_client)]
