"""Unit tests for the API-key authentication middleware.

Auth tests use a non-exempt path (``/api/v1/query-placeholder``) to exercise
the middleware's rejection logic.  The exempt paths (/api/v1/health, /docs,
/openapi.json, /redoc) bypass auth by design and are tested separately.
"""

from unittest.mock import MagicMock, patch

from fastapi import APIRouter
from fastapi.testclient import TestClient

from src.api.main import app
from src.config import Settings

# Register a protected sentinel route once at module level so it is available
# to all tests in this file.  It lives under a path that is NOT in EXEMPT_PATHS.
_sentinel_router = APIRouter()


@_sentinel_router.get("/api/v1/_auth-test")
async def _auth_sentinel() -> dict[str, str]:
    return {"ok": "true"}


app.include_router(_sentinel_router)

_PROTECTED = "/api/v1/_auth-test"
_VALID_KEY = "test-api-key"


def test_valid_api_key_is_accepted(mock_settings: Settings, test_client: TestClient) -> None:
    """A request with the correct X-API-Key must reach the handler."""
    response = test_client.get(_PROTECTED, headers={"X-API-Key": _VALID_KEY})
    assert response.status_code == 200


def test_missing_api_key_returns_401(mock_settings: Settings, test_client: TestClient) -> None:
    """A request without X-API-Key must be rejected with 401."""
    response = test_client.get(_PROTECTED)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_wrong_api_key_returns_401(mock_settings: Settings, test_client: TestClient) -> None:
    """A request with an incorrect key must be rejected with 401."""
    response = test_client.get(_PROTECTED, headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_health_path_exempt_from_auth(mock_settings: Settings, test_client: TestClient) -> None:
    """/api/v1/health must be reachable without any API key."""
    from unittest.mock import AsyncMock

    with patch("src.api.routes.health.AsyncQdrantClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
        mock_instance.close = AsyncMock()
        mock_cls.return_value = mock_instance
        response = test_client.get("/api/v1/health")
    assert response.status_code == 200


def test_docs_path_exempt_from_auth(mock_settings: Settings, test_client: TestClient) -> None:
    """The /docs path must bypass auth and return 200."""
    response = test_client.get("/docs")
    assert response.status_code == 200


def test_openapi_json_exempt_from_auth(mock_settings: Settings, test_client: TestClient) -> None:
    response = test_client.get("/openapi.json")
    assert response.status_code == 200


def test_redoc_path_exempt_from_auth(mock_settings: Settings, test_client: TestClient) -> None:
    response = test_client.get("/redoc")
    assert response.status_code == 200
