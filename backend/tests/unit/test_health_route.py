"""Unit tests for GET /api/v1/health."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from src.config import Settings


def test_health_returns_connected_when_qdrant_ok(
    mock_settings: Settings,
    test_client: TestClient,
    mock_qdrant_client: MagicMock,
    authenticated_headers: dict[str, str],
) -> None:
    """When AsyncQdrantClient.get_collections() succeeds the response shows 'connected'."""
    collection_mock = MagicMock()
    collection_mock.collections = [MagicMock(), MagicMock()]
    mock_qdrant_client.get_collections = AsyncMock(return_value=collection_mock)

    response = test_client.get("/api/v1/health", headers=authenticated_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["qdrant"] == "connected"
    assert body["collection_count"] == 2


def test_health_returns_disconnected_when_qdrant_fails(
    mock_settings: Settings,
    test_client: TestClient,
    authenticated_headers: dict[str, str],
) -> None:
    """When AsyncQdrantClient raises any exception the endpoint still returns HTTP 200."""
    with patch("src.api.routes.health.AsyncQdrantClient") as mock_cls:
        mock_cls.side_effect = ConnectionRefusedError("qdrant not running")
        response = test_client.get("/api/v1/health", headers=authenticated_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["qdrant"] == "disconnected"
    assert body["collection_count"] == 0


def test_health_endpoint_is_exempt_from_auth(
    mock_settings: Settings,
    test_client: TestClient,
    mock_qdrant_client: MagicMock,
) -> None:
    """/api/v1/health must be reachable without an API key."""
    mock_qdrant_client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_schema(
    mock_settings: Settings,
    test_client: TestClient,
    mock_qdrant_client: MagicMock,
    authenticated_headers: dict[str, str],
) -> None:
    """Response body must contain exactly the three expected keys."""
    mock_qdrant_client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    response = test_client.get("/api/v1/health", headers=authenticated_headers)
    body = response.json()
    assert set(body.keys()) == {"status", "qdrant", "collection_count"}
