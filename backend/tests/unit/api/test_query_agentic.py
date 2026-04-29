"""Unit tests for POST /api/v1/query/agentic (agentic SSE streaming endpoint)."""

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import structlog.testing
from fastapi.testclient import TestClient

from src.api.routes.query_agentic import _parse_duration_ms
from src.config import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_doc() -> MagicMock:
    """Return a lightweight mock representing a LangChain Document."""
    doc = MagicMock()
    doc.page_content = "mock content"
    doc.metadata = {}
    return doc


def _make_astream_chunks() -> list[dict[str, Any]]:
    return [
        {
            "router": {
                "query_type": "factual",
                "retrieval_strategy": "hybrid",
                "query_rewritten": None,
                "steps_taken": ["router:factual:hybrid:45ms"],
            }
        },
        {
            "retriever": {
                "retrieved_docs": [_make_mock_doc(), _make_mock_doc()],
                "web_fallback_used": False,
                "steps_taken": ["retriever:hybrid:156ms"],
            }
        },
        {
            "grader": {
                "grader_scores": [0.8, 0.6],
                "graded_docs": [_make_mock_doc()],
                "all_below_threshold": False,
                "retry_count": 1,
                "steps_taken": ["grader:scored=2:passed=1:78ms"],
            }
        },
        {
            "generator": {
                "answer": "Test answer",
                "citations": [],
                "confidence": 0.9,
                "graded_docs": [],
                "steps_taken": ["generator:docs=1:confidence=0.90:120ms"],
            }
        },
        {
            "critic": {
                "critic_score": 0.15,
                "retry_count": 1,
                "steps_taken": ["critic:score=0.150:55ms"],
            }
        },
    ]


def _make_mock_graph(chunks: list[dict[str, Any]]) -> MagicMock:
    """Return a mock compiled_graph whose astream() yields the given chunks."""

    async def _astream(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        for chunk in chunks:
            yield chunk

    mock_graph = MagicMock()
    mock_graph.astream = _astream
    return mock_graph


def _parse_events(lines: list[str]) -> list[dict[str, Any]]:
    data_lines = [ln for ln in lines if ln.startswith("data: ")]
    return [json.loads(ln[len("data: ") :]) for ln in data_lines]


# ---------------------------------------------------------------------------
# _parse_duration_ms unit tests (F01)
# ---------------------------------------------------------------------------


class TestParseDurationMs:
    def test_empty_string_returns_zero(self) -> None:
        """Empty input must not raise — returns 0."""
        assert _parse_duration_ms("") == 0

    def test_malformed_no_suffix_returns_zero(self) -> None:
        """Entry without 'ms' suffix that cannot be parsed as int returns 0."""
        assert _parse_duration_ms("router_timeout") == 0

    def test_valid_entry_returns_milliseconds(self) -> None:
        """Well-formed entry parses the trailing ms value correctly."""
        assert _parse_duration_ms("router:factual:hybrid:45ms") == 45


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class TestQueryAgenticEndpoint:
    def test_happy_path_event_order(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """All node updates yield correct SSE event types in the right order."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        mock_graph = _make_mock_graph(_make_astream_chunks())
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query/agentic",
                json={"query": "What is X?"},
                headers=authenticated_headers,
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                lines = [ln for ln in response.iter_lines()]

            events = _parse_events(lines)
            types = [e["type"] for e in events]

            # Verify the full ordered sequence
            assert types.index("agent_step") < types.index("token")
            assert types.index("token") < types.index("citations")
            assert types.index("citations") < types.index("done")
            assert types[-1] == "done"

            # Verify agent_step node sequence: router → retriever → grader → generator → critic
            agent_step_events = [e for e in events if e["type"] == "agent_step"]
            assert len(agent_step_events) == 5
            node_sequence = [e["node"] for e in agent_step_events]
            assert node_sequence == ["router", "retriever", "grader", "generator", "critic"]

            # All first-run events must have run == 1
            for evt in agent_step_events:
                assert evt["run"] == 1, f"Expected run=1 for {evt['node']}, got {evt['run']}"

            # Generator agent_step comes after all tokens but before citations
            token_indices = [i for i, e in enumerate(events) if e["type"] == "token"]
            gen_step_index = next(
                i
                for i, e in enumerate(events)
                if e["type"] == "agent_step" and e["node"] == "generator"
            )
            citations_index = next(i for i, e in enumerate(events) if e["type"] == "citations")
            assert all(ti < gen_step_index for ti in token_indices)
            assert gen_step_index < citations_index

            # F04: chunks_retrieved comes from grader state, not generator state
            citations_event = next(e for e in events if e["type"] == "citations")
            assert citations_event["chunks_retrieved"] == 1

            # retrieved_contexts must be present in the citations event (additive field for RAGAS)
            assert "retrieved_contexts" in citations_event
            assert isinstance(citations_event["retrieved_contexts"], list)

            # F06: "Test answer" splits into 2 words → at least 2 token events
            token_events = [e for e in events if e["type"] == "token"]
            assert len(token_events) >= 2
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

    def test_session_id_header_forwarded(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """When X-Session-ID is present, astream is called with that thread_id."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        captured_config: dict[str, Any] = {}

        async def _astream(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            captured_config.update(kwargs.get("config") or {})
            for chunk in _make_astream_chunks():
                yield chunk

        mock_graph = MagicMock()
        mock_graph.astream = _astream
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            headers = {**authenticated_headers, "X-Session-ID": "test-session-123"}
            with test_client_1d.stream(
                "POST",
                "/api/v1/query/agentic",
                json={"query": "What is X?"},
                headers=headers,
            ) as response:
                assert response.status_code == 200
                list(response.iter_lines())  # drain the stream
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

        assert captured_config.get("configurable", {}).get("thread_id") == "test-session-123"

    def test_missing_session_id_generates_uuid(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """When X-Session-ID is absent, astream is called with a valid UUID thread_id."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        captured_config: dict[str, Any] = {}

        async def _astream(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            captured_config.update(kwargs.get("config") or {})
            for chunk in _make_astream_chunks():
                yield chunk

        mock_graph = MagicMock()
        mock_graph.astream = _astream
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query/agentic",
                json={"query": "What is X?"},
                headers=authenticated_headers,
            ) as response:
                assert response.status_code == 200
                list(response.iter_lines())
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

        thread_id: str = captured_config.get("configurable", {}).get("thread_id", "")
        assert thread_id not in ("", "None")
        # Must be a valid UUID
        parsed = uuid.UUID(thread_id)
        assert str(parsed) == thread_id

    def test_invalid_body_empty_query_returns_422(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """POST with query='' returns HTTP 422 because min_length=1 is enforced."""
        response = test_client_1d.post(
            "/api/v1/query/agentic",
            json={"query": ""},
            headers=authenticated_headers,
        )
        assert response.status_code == 422

    def test_graph_exception_yields_done_event(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """When astream raises mid-stream, done is always emitted and structlog error is logged."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        async def _failing_astream(*args: Any, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
            raise RuntimeError("graph failed")
            yield  # makes this an async generator

        mock_graph = MagicMock()
        mock_graph.astream = _failing_astream
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            with (
                structlog.testing.capture_logs() as captured,
                test_client_1d.stream(
                    "POST",
                    "/api/v1/query/agentic",
                    json={"query": "What is X?"},
                    headers=authenticated_headers,
                ) as response,
            ):
                assert response.status_code == 200
                lines = list(response.iter_lines())

            events = _parse_events(lines)
            assert events[-1]["type"] == "done"

            error_events = [e for e in captured if e["event"] == "agentic_stream_error"]
            assert len(error_events) == 1
            assert error_events[0]["log_level"] == "error"
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

    def test_router_payload_fields(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Router agent_step event has query_type, strategy, and duration_ms fields."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        mock_graph = _make_mock_graph(_make_astream_chunks())
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query/agentic",
                json={"query": "test"},
                headers=authenticated_headers,
            ) as response:
                lines = list(response.iter_lines())
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

        events = _parse_events(lines)
        router_event = next(
            e for e in events if e.get("type") == "agent_step" and e.get("node") == "router"
        )
        payload = router_event["payload"]
        assert payload["query_type"] == "factual"
        assert payload["strategy"] == "hybrid"
        assert payload["duration_ms"] == 45

    def test_retriever_payload_fields(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Retriever agent_step event has strategy, docs_retrieved, and duration_ms fields."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        mock_graph = _make_mock_graph(_make_astream_chunks())
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query/agentic",
                json={"query": "test"},
                headers=authenticated_headers,
            ) as response:
                lines = list(response.iter_lines())
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

        events = _parse_events(lines)
        retriever_event = next(
            e for e in events if e.get("type") == "agent_step" and e.get("node") == "retriever"
        )
        payload = retriever_event["payload"]
        assert payload["strategy"] == "hybrid"
        assert payload["docs_retrieved"] == 2
        assert payload["duration_ms"] == 156

    def test_generator_payload_fields(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Generator agent_step event has docs_used, confidence, and duration_ms fields."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        mock_graph = _make_mock_graph(_make_astream_chunks())
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query/agentic",
                json={"query": "test"},
                headers=authenticated_headers,
            ) as response:
                lines = list(response.iter_lines())
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

        events = _parse_events(lines)
        gen_event = next(
            e for e in events if e.get("type") == "agent_step" and e.get("node") == "generator"
        )
        payload = gen_event["payload"]
        # grader has 1 graded doc (_make_astream_chunks grader chunk)
        assert payload["docs_used"] == 1
        assert payload["confidence"] == 0.9
        assert payload["duration_ms"] == 120

    def test_run_field_increments_on_crag_retry(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """On CRAG escalation, retriever and grader run fields increment to 2 on second visit."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        crag_chunks: list[dict[str, Any]] = [
            {
                "router": {
                    "query_type": "factual",
                    "retrieval_strategy": "hybrid",
                    "steps_taken": ["router:factual:hybrid:45ms"],
                }
            },
            {
                "retriever": {
                    "retrieved_docs": [_make_mock_doc()],
                    "web_fallback_used": False,
                    "steps_taken": ["retriever:hybrid:100ms"],
                }
            },
            {
                "grader": {
                    "grader_scores": [0.1],
                    "graded_docs": [],
                    "all_below_threshold": True,
                    "retry_count": 0,
                    "steps_taken": ["grader:scored=1:passed=0:78ms"],
                }
            },
            {
                "retriever": {
                    "retrieved_docs": [_make_mock_doc(), _make_mock_doc()],
                    "web_fallback_used": True,
                    "steps_taken": ["retriever:web:200ms"],
                }
            },
            {
                "grader": {
                    "grader_scores": [0.9, 0.8],
                    "graded_docs": [_make_mock_doc(), _make_mock_doc()],
                    "all_below_threshold": False,
                    "retry_count": 1,
                    "steps_taken": ["grader:scored=2:passed=2:60ms"],
                }
            },
            {
                "generator": {
                    "answer": "Answer",
                    "citations": [],
                    "confidence": 0.85,
                    "steps_taken": ["generator:docs=2:confidence=0.85:300ms"],
                }
            },
            {
                "critic": {
                    "critic_score": 0.1,
                    "retry_count": 1,
                    "steps_taken": ["critic:score=0.100:55ms"],
                }
            },
        ]

        mock_graph = _make_mock_graph(crag_chunks)
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query/agentic",
                json={"query": "test CRAG"},
                headers=authenticated_headers,
            ) as response:
                lines = list(response.iter_lines())
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

        events = _parse_events(lines)
        retriever_events = [
            e for e in events if e.get("type") == "agent_step" and e.get("node") == "retriever"
        ]
        grader_events = [
            e for e in events if e.get("type") == "agent_step" and e.get("node") == "grader"
        ]

        assert len(retriever_events) == 2, "Expected 2 retriever agent_step events on CRAG retry"
        assert retriever_events[0]["run"] == 1
        assert retriever_events[1]["run"] == 2

        assert len(grader_events) == 2, "Expected 2 grader agent_step events on CRAG retry"
        assert grader_events[0]["run"] == 1
        assert grader_events[1]["run"] == 2

    def test_initial_state_includes_retry_count_zero(
        self,
        test_client_1d: TestClient,
        mock_settings: Settings,
        authenticated_headers: dict[str, str],
    ) -> None:
        """initial_state passed to astream must include retry_count=0 to prevent KeyError in grader."""
        from src.api.deps import get_compiled_graph
        from src.api.main import app

        captured_state: dict[str, Any] = {}

        async def _astream(
            state: Any, *_args: Any, **_kwargs: Any
        ) -> AsyncIterator[dict[str, Any]]:
            if isinstance(state, dict):
                captured_state.update(state)
            for chunk in _make_astream_chunks():
                yield chunk

        mock_graph = MagicMock()
        mock_graph.astream = _astream
        app.dependency_overrides[get_compiled_graph] = lambda: mock_graph

        try:
            with test_client_1d.stream(
                "POST",
                "/api/v1/query/agentic",
                json={"query": "test retry_count"},
                headers=authenticated_headers,
            ) as response:
                assert response.status_code == 200
                list(response.iter_lines())
        finally:
            app.dependency_overrides.pop(get_compiled_graph, None)

        assert "retry_count" in captured_state, "retry_count must be in initial_state"
        assert captured_state["retry_count"] == 0, "retry_count must start at 0"
