"""Unit tests for GET /api/v1/eval/baseline route."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.config import Settings

_BASELINE_CONTENT = {
    "faithfulness": 0.9028,
    "answer_relevancy": 0.9752,
    "context_recall": 0.9542,
    "context_precision": 0.9642,
    "answer_correctness": 0.7650,
}


class TestEvalBaselineRoute:
    def test_returns_200_with_baseline_content(
        self,
        test_client: TestClient,
        authenticated_headers: dict[str, str],
        mock_settings: Settings,
    ) -> None:
        """Route returns 200 and JSON metrics when baseline file exists."""
        with (
            patch("src.api.routes.eval.Path.exists", return_value=True),
            patch(
                "src.api.routes.eval.Path.read_text",
                return_value=json.dumps(_BASELINE_CONTENT),
            ),
        ):
            response = test_client.get(
                "/api/v1/eval/baseline",
                headers=authenticated_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["faithfulness"] == pytest.approx(0.9028)
        assert data["answer_relevancy"] == pytest.approx(0.9752)
        assert data["answer_correctness"] == pytest.approx(0.7650)

    def test_returns_404_when_file_missing(
        self,
        test_client: TestClient,
        authenticated_headers: dict[str, str],
        mock_settings: Settings,
    ) -> None:
        """Route returns 404 with descriptive detail when baseline file is absent."""
        with patch("src.api.routes.eval.Path.exists", return_value=False):
            response = test_client.get(
                "/api/v1/eval/baseline",
                headers=authenticated_headers,
            )

        assert response.status_code == 404
        assert "evaluator" in response.json()["detail"]

    def test_returns_422_when_file_malformed(
        self,
        test_client: TestClient,
        authenticated_headers: dict[str, str],
        mock_settings: Settings,
    ) -> None:
        """Route returns 422 when baseline file exists but contains invalid JSON."""
        with (
            patch("src.api.routes.eval.Path.exists", return_value=True),
            patch(
                "src.api.routes.eval.Path.read_text",
                return_value="not valid json {{{",
            ),
        ):
            response = test_client.get(
                "/api/v1/eval/baseline",
                headers=authenticated_headers,
            )

        assert response.status_code == 422
        assert "malformed" in response.json()["detail"]
