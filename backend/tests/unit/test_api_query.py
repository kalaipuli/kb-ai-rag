"""Unit tests for POST /api/v1/query (SSE streaming endpoint)."""

import json
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.config import Settings


async def _make_fake_stream(
    tokens: list[str] | None = None,
    citations: list[dict[str, object]] | None = None,
    confidence: float = 0.85,
) -> AsyncGenerator[str, None]:
    """Yield a predictable sequence of SSE events for testing."""
    for token in tokens or ["Hello", " world"]:
        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
    yield f"data: {json.dumps({'type': 'citations', 'citations': citations or [], 'confidence': confidence})}\n\n"
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


class TestQueryEndpoint:
    def test_query_requires_auth(
        self,
        test_client_1d: TestClient,
    ) -> None:
        """POST /api/v1/query without X-API-Key returns 401."""
        response = test_client_1d.post("/api/v1/query", json={"query": "test"})
        assert response.status_code == 401

    def test_query_returns_event_stream(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """POST /api/v1/query returns 200 with text/event-stream content type."""
        from src.api.deps import get_generation_chain
        from src.api.main import app

        mock_chain = MagicMock()
        mock_chain.astream_generate = lambda *a, **kw: _make_fake_stream()
        app.dependency_overrides[get_generation_chain] = lambda: mock_chain

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query",
                json={"query": "What is X?"},
                headers=authenticated_headers,
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
        finally:
            app.dependency_overrides.pop(get_generation_chain, None)

    def test_query_streams_token_events(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """SSE stream contains token events before citations and done."""
        from src.api.deps import get_generation_chain
        from src.api.main import app

        mock_chain = MagicMock()
        mock_chain.astream_generate = lambda *a, **kw: _make_fake_stream(
            tokens=["Hello", " world"]
        )
        app.dependency_overrides[get_generation_chain] = lambda: mock_chain

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query",
                json={"query": "question"},
                headers=authenticated_headers,
            ) as response:
                lines = [l for l in response.iter_lines() if l.startswith("data: ")]

            events = [json.loads(l[len("data: "):]) for l in lines]
            types = [e["type"] for e in events]

            assert "token" in types
            assert "citations" in types
            assert "done" in types
            # tokens come before citations and done
            last_token_idx = max(i for i, t in enumerate(types) if t == "token")
            citations_idx = types.index("citations")
            done_idx = types.index("done")
            assert last_token_idx < citations_idx < done_idx
        finally:
            app.dependency_overrides.pop(get_generation_chain, None)

    def test_query_citations_event_has_confidence(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Citations SSE event includes a confidence field."""
        from src.api.deps import get_generation_chain
        from src.api.main import app

        mock_chain = MagicMock()
        mock_chain.astream_generate = lambda *a, **kw: _make_fake_stream(confidence=0.92)
        app.dependency_overrides[get_generation_chain] = lambda: mock_chain

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query",
                json={"query": "question"},
                headers=authenticated_headers,
            ) as response:
                lines = [l for l in response.iter_lines() if l.startswith("data: ")]

            events = [json.loads(l[len("data: "):]) for l in lines]
            citations_event = next(e for e in events if e["type"] == "citations")

            assert "confidence" in citations_event
            assert citations_event["confidence"] == pytest.approx(0.92)
        finally:
            app.dependency_overrides.pop(get_generation_chain, None)

    def test_query_done_is_last_event(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """The done event is always the final event in the stream."""
        from src.api.deps import get_generation_chain
        from src.api.main import app

        mock_chain = MagicMock()
        mock_chain.astream_generate = lambda *a, **kw: _make_fake_stream()
        app.dependency_overrides[get_generation_chain] = lambda: mock_chain

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query",
                json={"query": "question"},
                headers=authenticated_headers,
            ) as response:
                lines = [l for l in response.iter_lines() if l.startswith("data: ")]

            events = [json.loads(l[len("data: "):]) for l in lines]
            assert events[-1]["type"] == "done"
        finally:
            app.dependency_overrides.pop(get_generation_chain, None)
