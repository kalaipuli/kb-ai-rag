"""Shared pytest fixtures for the kb-ai-rag backend test suite.

Environment variables required by ``src.config.Settings`` are injected at
module level (before any src import) so that ``get_settings()`` never fails
due to missing required fields during test collection or execution.
"""

import os
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

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

    ``mock_settings`` is applied first so the lifespan handler, middleware,
    and route handlers all see test configuration values.
    """
    from src.api.main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def authenticated_headers() -> dict[str, str]:
    """Return HTTP headers containing the test API key."""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_qdrant_client() -> Generator[MagicMock, None, None]:
    """Patch AsyncQdrantClient so health checks do not attempt real TCP connections."""
    with patch("src.api.routes.health.AsyncQdrantClient") as mock_cls:
        mock_instance = MagicMock()
        # get_collections and close are awaited in the async handler
        mock_instance.get_collections = AsyncMock()
        mock_instance.close = AsyncMock()
        mock_cls.return_value = mock_instance
        yield mock_instance
