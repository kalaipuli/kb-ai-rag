"""Unit tests for GET /api/v1/collections."""

from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.config import Settings


def _make_mock_qdrant(
    collection_names: list[str] | None = None,
    points_count: int = 10,
    vectors_count: int = 10,
) -> MagicMock:
    """Return a mock AsyncQdrantClient for collections tests."""
    names = collection_names or []

    col_desc = [MagicMock(name=n) for n in names]
    for desc, n in zip(col_desc, names, strict=True):
        desc.name = n

    collections_result = MagicMock()
    collections_result.collections = col_desc

    col_info = MagicMock()
    col_info.points_count = points_count
    col_info.indexed_vectors_count = vectors_count

    mock = MagicMock()
    mock.get_collections = AsyncMock(return_value=collections_result)
    mock.get_collection = AsyncMock(return_value=col_info)
    return mock


class TestCollectionsEndpoint:
    def test_collections_requires_auth(
        self,
        test_client_1d: TestClient,
    ) -> None:
        """GET /api/v1/collections without X-API-Key returns 401."""
        response = test_client_1d.get("/api/v1/collections")
        assert response.status_code == 401

    def test_collections_returns_empty_list(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """When Qdrant has no collections, response contains an empty list."""
        from src.api.deps import get_qdrant_client
        from src.api.main import app

        mock_qdrant = _make_mock_qdrant(collection_names=[])
        app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant

        try:
            response = test_client_1d.get(
                "/api/v1/collections", headers=authenticated_headers
            )
            assert response.status_code == 200
            body = response.json()
            assert body["collections"] == []
        finally:
            app.dependency_overrides.pop(get_qdrant_client, None)

    def test_collections_returns_collection_list(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Collections endpoint returns name, document_count, and vector_count for each entry."""
        from src.api.deps import get_qdrant_client
        from src.api.main import app

        mock_qdrant = _make_mock_qdrant(
            collection_names=["kb_documents"], points_count=42, vectors_count=42
        )
        app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant

        try:
            response = test_client_1d.get(
                "/api/v1/collections", headers=authenticated_headers
            )
            assert response.status_code == 200
            body = response.json()
            assert len(body["collections"]) == 1
            col = body["collections"][0]
            assert col["name"] == "kb_documents"
            assert col["document_count"] == 42
            assert col["vector_count"] == 42
        finally:
            app.dependency_overrides.pop(get_qdrant_client, None)

    def test_collections_multiple_entries(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Multiple collections are all included in the response."""
        from src.api.deps import get_qdrant_client
        from src.api.main import app

        mock_qdrant = _make_mock_qdrant(collection_names=["col_a", "col_b", "col_c"])
        app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant

        try:
            response = test_client_1d.get(
                "/api/v1/collections", headers=authenticated_headers
            )
            assert response.status_code == 200
            names = [c["name"] for c in response.json()["collections"]]
            assert set(names) == {"col_a", "col_b", "col_c"}
        finally:
            app.dependency_overrides.pop(get_qdrant_client, None)

    def test_collections_qdrant_failure_returns_503(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """If Qdrant raises, the endpoint returns 503 via the RetrievalError handler."""
        from src.api.deps import get_qdrant_client
        from src.api.main import app

        mock_qdrant = MagicMock()
        mock_qdrant.get_collections = AsyncMock(side_effect=Exception("qdrant down"))
        app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant

        try:
            response = test_client_1d.get(
                "/api/v1/collections", headers=authenticated_headers
            )
            assert response.status_code == 503
        finally:
            app.dependency_overrides.pop(get_qdrant_client, None)
