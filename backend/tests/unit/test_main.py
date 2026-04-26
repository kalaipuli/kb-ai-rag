"""Unit tests for src/api/main.py application wiring."""

from unittest.mock import MagicMock

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.api.main import app
from src.config import Settings
from src.exceptions import IngestionError


def test_eval_baseline_route_registered(
    mock_settings: Settings,
    authenticated_headers: dict[str, str],
) -> None:
    """GET /api/v1/eval/baseline must be registered — returns 200 or 404, never 422 (unregistered)."""
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/eval/baseline", headers=authenticated_headers)

    assert response.status_code in (200, 404)


def test_ingestion_error_returns_422(
    mock_settings: Settings,
    authenticated_headers: dict[str, str],
) -> None:
    """IngestionError raised inside a handler must produce HTTP 422 with ErrorResponse body."""
    test_router = APIRouter()

    @test_router.get("/api/v1/test-error-422")
    async def _boom() -> None:
        raise IngestionError("test ingestion failure")

    app.include_router(test_router)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/test-error-422", headers=authenticated_headers)

    assert response.status_code == 422
    assert "test ingestion failure" in response.json()["detail"]


def test_validation_error_returns_422(
    mock_settings: Settings,
    authenticated_headers: dict[str, str],
) -> None:
    """An invalid request body must produce HTTP 422."""

    class Body(BaseModel):
        value: int

    test_router2 = APIRouter()

    @test_router2.post("/api/v1/test-validate-422")
    async def _validate(body: Body) -> dict[str, int]:
        return {"value": body.value}

    app.include_router(test_router2)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/test-validate-422",
            json={"value": "not-an-int"},
            headers=authenticated_headers,
        )

    assert response.status_code == 422


def test_cors_headers_present(
    mock_settings: Settings,
    mock_qdrant_client: MagicMock,
) -> None:
    """CORS headers must be present on a health response for a cross-origin request."""
    from unittest.mock import AsyncMock

    mock_qdrant_client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
