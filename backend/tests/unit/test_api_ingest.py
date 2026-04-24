"""Unit tests for POST /api/v1/ingest."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.config import Settings


class TestIngestEndpoint:
    def test_ingest_returns_202(
        self,
        test_client_1d: TestClient,
        authenticated_headers: dict[str, str],
    ) -> None:
        """POST /api/v1/ingest returns 202 Accepted."""
        with patch("src.api.routes.ingest.run_pipeline", new_callable=AsyncMock):
            response = test_client_1d.post(
                "/api/v1/ingest",
                headers=authenticated_headers,
            )
        assert response.status_code == 202

    def test_ingest_requires_auth(
        self,
        test_client_1d: TestClient,
    ) -> None:
        """POST /api/v1/ingest without X-API-Key returns 401."""
        response = test_client_1d.post("/api/v1/ingest")
        assert response.status_code == 401

    def test_ingest_response_body(
        self,
        test_client_1d: TestClient,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Response body has status='accepted' and a non-empty message."""
        with patch("src.api.routes.ingest.run_pipeline", new_callable=AsyncMock):
            response = test_client_1d.post(
                "/api/v1/ingest",
                headers=authenticated_headers,
            )
        body = response.json()
        assert body["status"] == "accepted"
        assert "message" in body
        assert len(body["message"]) > 0

    def test_ingest_schedules_background_task(
        self,
        test_client_1d: TestClient,
        authenticated_headers: dict[str, str],
    ) -> None:
        """run_pipeline is called exactly once as a background task."""
        with patch(
            "src.api.routes.ingest.run_pipeline", new_callable=AsyncMock
        ) as mock_pipeline:
            test_client_1d.post(
                "/api/v1/ingest",
                headers=authenticated_headers,
            )
        mock_pipeline.assert_called_once()

    def test_ingest_body_data_dir_overrides_settings(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """When body.data_dir is provided it is passed to run_pipeline, not settings.data_dir."""
        with patch(
            "src.api.routes.ingest.run_pipeline", new_callable=AsyncMock
        ) as mock_pipeline:
            test_client_1d.post(
                "/api/v1/ingest",
                json={"data_dir": "/custom/path"},
                headers=authenticated_headers,
            )
        args, _ = mock_pipeline.call_args
        assert args[0] == Path("/custom/path")

    def test_ingest_no_body_uses_settings_data_dir(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """When no body is provided, settings.data_dir is used."""
        with patch(
            "src.api.routes.ingest.run_pipeline", new_callable=AsyncMock
        ) as mock_pipeline:
            test_client_1d.post(
                "/api/v1/ingest",
                headers=authenticated_headers,
            )
        args, _ = mock_pipeline.call_args
        assert args[0] == Path(mock_settings.data_dir)

    def test_ingest_invalid_data_dir_returns_202_immediately(
        self,
        test_client_1d: TestClient,
        authenticated_headers: dict[str, str],
    ) -> None:
        """An invalid data_dir path still returns 202 — validation happens in the background task."""
        with patch(
            "src.api.routes.ingest.run_pipeline", new_callable=AsyncMock
        ) as mock_pipeline:
            response = test_client_1d.post(
                "/api/v1/ingest",
                json={"data_dir": "/completely/invalid/path/xyz"},
                headers=authenticated_headers,
            )
        assert response.status_code == 202
        mock_pipeline.assert_called_once()
