"""Shared pytest fixtures for the kb-ai-rag backend test suite.

Environment variables required by ``src.config.Settings`` are injected at
module level (before any src import) so that ``get_settings()`` never fails
due to missing required fields during test collection or execution.
"""

# ---------------------------------------------------------------------------
# Test settings conventions
#
# Two patterns are used across this test suite:
#
# 1. Real Settings object (use for route/middleware tests):
#    Use the `mock_settings` fixture defined below, which yields a real
#    Settings instance and wires it into FastAPI's dependency_overrides.
#
# 2. MagicMock settings (use for pure-unit retrieval/pipeline tests):
#    Define a local `_make_settings()` returning MagicMock(). This avoids
#    the pydantic-settings validation overhead and is appropriate when the
#    test only needs specific config attributes (e.g. retrieval_top_k=5).
#
# Phase 1c test authors: use pattern 2 for chain/retrieval unit tests,
# pattern 1 for any test that exercises FastAPI routes.
# ---------------------------------------------------------------------------

import os
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Inject required env vars before any src module is imported.
# This ensures Settings() succeeds at module-load time even without a .env file.
# ---------------------------------------------------------------------------
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-azure-key")
os.environ.setdefault("API_KEY", "test-api-key")

from src.config import Settings, get_settings  # noqa: E402  (must come after os.environ setup)


def _make_test_settings() -> Settings:
    """Return a Settings instance with safe in-memory test values.

    All Azure credentials and external service URLs are overridden so that
    tests never attempt real network calls.
    """
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="test-azure-key",
        azure_openai_api_version="2024-08-01-preview",
        azure_chat_deployment="gpt-4o",
        azure_embedding_deployment="text-embedding-3-large",
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_collection",
        api_key="test-api-key",
        data_dir="/tmp/test-data",
        chunk_size=512,
        chunk_overlap=64,
        bm25_index_path="/tmp/test-bm25.pkl",
        embedding_vector_size=3072,
        retrieval_top_k=10,
        reranker_top_k=5,
        reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        rrf_k=60,
        langsmith_api_key="",
        langchain_tracing_v2=False,
        tavily_api_key="",
    )


@pytest.fixture
def mock_settings() -> Generator[Settings, None, None]:
    """Override the ``get_settings`` dependency with deterministic test values.

    Uses FastAPI's dependency_overrides mechanism so every route that declares
    ``Depends(get_settings)`` receives the test Settings object.  Also clears
    the lru_cache so the factory is not used during the test.
    """
    from src.api.main import app

    test_settings = _make_test_settings()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield test_settings
    app.dependency_overrides.pop(get_settings, None)
    get_settings.cache_clear()


@pytest.fixture
def test_client(mock_settings: Settings) -> Generator[TestClient, None, None]:
    """Return a synchronous TestClient backed by the patched FastAPI app.

    Patches CrossEncoderReranker, Embedder, AzureChatOpenAI, and
    AsyncQdrantClient so the lifespan does not download HuggingFace models
    or attempt real Azure/Qdrant connections during test setup.
    """
    from unittest.mock import AsyncMock, patch

    from src.api.main import app

    mock_qdrant = MagicMock()
    mock_qdrant.close = AsyncMock()

    with (
        patch("src.retrieval.reranker.CrossEncoder", return_value=MagicMock()),
        patch("src.ingestion.embedder.AzureOpenAIEmbeddings", return_value=MagicMock()),
        patch("src.generation.chain.AzureChatOpenAI", return_value=MagicMock()),
        patch("src.api.main.AsyncQdrantClient", return_value=mock_qdrant),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield client


@pytest.fixture
def test_client_1d(mock_settings: Settings) -> Generator[TestClient, None, None]:
    """TestClient with lifespan service constructors patched for Phase 1d endpoint tests.

    Patches CrossEncoder, AzureOpenAIEmbeddings, AzureChatOpenAI, and
    AsyncQdrantClient to avoid HuggingFace model download and Azure credential
    checks during test setup. Dependency overrides for get_generation_chain and
    get_qdrant_client are applied per-test.
    """
    from unittest.mock import AsyncMock, patch

    from src.api.main import app

    mock_qdrant = MagicMock()
    mock_qdrant.close = AsyncMock()

    with (
        patch("src.retrieval.reranker.CrossEncoder", return_value=MagicMock()),
        patch("src.ingestion.embedder.AzureOpenAIEmbeddings", return_value=MagicMock()),
        patch("src.generation.chain.AzureChatOpenAI", return_value=MagicMock()),
        patch("src.api.main.AsyncQdrantClient", return_value=mock_qdrant),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        yield client


@pytest.fixture
def authenticated_headers() -> dict[str, str]:
    """Return HTTP headers containing the test API key."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_qdrant_client() -> Generator[MagicMock, None, None]:
    """Override the get_qdrant_client dependency so health checks do not attempt real TCP connections."""
    from src.api.deps import get_qdrant_client
    from src.api.main import app

    mock_instance = MagicMock()
    # get_collections is awaited in the async handler
    mock_instance.get_collections = AsyncMock()
    app.dependency_overrides[get_qdrant_client] = lambda: mock_instance
    yield mock_instance
    app.dependency_overrides.pop(get_qdrant_client, None)
