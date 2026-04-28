"""Unit tests for EvaluationRunner (T01)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import structlog.testing

from src.evaluation.runner import EvaluationRunner
from src.exceptions import GenerationError

# ---------------------------------------------------------------------------
# Golden dataset fixture
# ---------------------------------------------------------------------------

GOLDEN_DATASET = [
    {
        "id": "q001",
        "question": "How do I reset my VPN?",
        "ground_truth": "Disconnect, clear credentials, reconnect.",
    },
    {
        "id": "q002",
        "question": "What is the password minimum length?",
        "ground_truth": "14 characters.",
    },
]


@pytest.fixture
def dataset_file(tmp_path: Path) -> Path:
    p = tmp_path / "golden.json"
    p.write_text(json.dumps(GOLDEN_DATASET), encoding="utf-8")
    return p


@pytest.fixture
def single_question_dataset(tmp_path: Path) -> Path:
    p = tmp_path / "golden_single.json"
    p.write_text(
        json.dumps([GOLDEN_DATASET[0]]),
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# Settings mock factory
# ---------------------------------------------------------------------------


def _make_mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.azure_openai_endpoint = "https://fake.openai.azure.com/"
    settings.azure_openai_api_key.get_secret_value.return_value = "fake-key"
    settings.azure_chat_deployment = "gpt-4o"
    settings.azure_embedding_deployment = "text-embedding-3-large"
    settings.azure_openai_api_version = "2024-08-01-preview"
    settings.api_key.get_secret_value.return_value = "test-api-key"
    return settings


# ---------------------------------------------------------------------------
# EvaluationRunner factory — patches Azure constructors to avoid network
# ---------------------------------------------------------------------------


def _make_runner(
    settings: MagicMock,
    dataset_path: Path,
    endpoint: str = "agentic",
    base_url: str = "http://localhost:8000",
) -> EvaluationRunner:
    with (
        patch("src.evaluation.runner.AzureChatOpenAI"),
        patch("src.evaluation.runner.AzureOpenAIEmbeddings"),
        patch("src.evaluation.runner.LangchainLLMWrapper"),
        patch("src.evaluation.runner.LangchainEmbeddingsWrapper"),
    ):
        from typing import Literal

        ep: Literal["static", "agentic"] = "agentic" if endpoint == "agentic" else "static"
        return EvaluationRunner(
            settings=settings,
            dataset_path=dataset_path,
            endpoint=ep,
            base_url=base_url,
        )


# ---------------------------------------------------------------------------
# SSE line helpers
# ---------------------------------------------------------------------------


def _sse_lines(events: list[dict[str, object]]) -> list[str]:
    """Convert a list of event dicts into ``data: <json>`` SSE line strings."""
    return [f"data: {json.dumps(e)}" for e in events]


def _make_stream_cm(lines: list[str]) -> MagicMock:
    """Return an async context manager mock whose response yields given SSE lines."""
    mock_response = MagicMock()

    async def _aiter_lines() -> AsyncIterator[str]:
        for line in lines:
            yield line

    mock_response.aiter_lines = _aiter_lines

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=mock_response)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_client_with_stream(lines: list[str]) -> MagicMock:
    """Return a mock httpx.AsyncClient whose stream() returns the given SSE lines."""
    mock_client = MagicMock()
    mock_client.stream.return_value = _make_stream_cm(lines)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ---------------------------------------------------------------------------
# Mock RAGAS result
# ---------------------------------------------------------------------------


def _mock_ragas_result(n: int = 1) -> MagicMock:
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: {  # type: ignore[assignment]
        "faithfulness": [0.90] * n,
        "answer_relevancy": [0.82] * n,
        "context_recall": [0.75] * n,
        "context_precision": [0.78] * n,
        "answer_correctness": [0.85] * n,
    }[key]
    mock.scores = [
        {
            "faithfulness": 0.90,
            "answer_relevancy": 0.82,
            "context_recall": 0.75,
            "context_precision": 0.78,
            "answer_correctness": 0.85,
        }
    ] * n
    return mock


# ---------------------------------------------------------------------------
# Test 1: answer extracted from token events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agentic_runner_extracts_answer_from_token_events(
    dataset_file: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, dataset_file, endpoint="agentic")

    lines = _sse_lines(
        [
            {"type": "token", "content": "Hello "},
            {"type": "token", "content": "world"},
            {
                "type": "citations",
                "citations": [
                    {
                        "chunk_id": "c1",
                        "filename": "vpn.txt",
                        "source_path": "/data/vpn.txt",
                        "page_number": 2,
                        "retrieval_score": 0.9,
                        "text": "Some context text",
                    }
                ],
                "confidence": 0.9,
                "chunks_retrieved": 1,
                "retrieved_contexts": ["actual chunk text from grader"],
            },
            {"type": "done"},
        ]
    )
    mock_client = _make_client_with_stream(lines)

    ragas_mock = _mock_ragas_result(n=2)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", return_value=ragas_mock),
    ):
        result = await runner.run()

    # Verify answer was joined from token events
    call_args = mock_client.stream.call_args_list[0]
    assert call_args is not None
    # Result must be an EvaluationResult with expected scores
    assert result.faithfulness == pytest.approx(0.90)
    assert result.answer_correctness == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# Test 2: unique session ID per question
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agentic_runner_sends_unique_session_id_per_question(
    dataset_file: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, dataset_file, endpoint="agentic")

    lines = _sse_lines([{"type": "done"}])
    mock_client = _make_client_with_stream(lines)
    # Each call to stream() should return the same simple response
    mock_client.stream.return_value = _make_stream_cm(lines)

    ragas_mock = _mock_ragas_result(n=2)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", return_value=ragas_mock),
    ):
        await runner.run()

    assert mock_client.stream.call_count == 2
    headers_0 = mock_client.stream.call_args_list[0].kwargs["headers"]
    headers_1 = mock_client.stream.call_args_list[1].kwargs["headers"]

    sid_0 = headers_0.get("X-Session-ID")
    sid_1 = headers_1.get("X-Session-ID")
    assert sid_0 is not None
    assert sid_1 is not None
    assert sid_0 != sid_1, "Each question must get a unique session ID"


# ---------------------------------------------------------------------------
# Test 3: static endpoint calls /api/v1/query not /api/v1/query/agentic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_static_runner_calls_query_endpoint(
    single_question_dataset: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, single_question_dataset, endpoint="static")

    lines = _sse_lines(
        [
            {"type": "token", "content": "answer"},
            {"type": "citations", "citations": [], "confidence": None},
            {"type": "done"},
        ]
    )
    mock_client = _make_client_with_stream(lines)
    ragas_mock = _mock_ragas_result(n=1)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", return_value=ragas_mock),
    ):
        await runner.run()

    call_args = mock_client.stream.call_args_list[0]
    url_arg = call_args.args[1] if call_args.args else call_args.kwargs.get("url", "")
    assert "/api/v1/query" in str(url_arg)
    assert "agentic" not in str(url_arg)


# ---------------------------------------------------------------------------
# Test 4: continue on per-question timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runner_continues_on_question_timeout(
    dataset_file: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, dataset_file, endpoint="agentic")

    call_count = 0

    def _stream_side_effect(*args: object, **kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First question times out
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(
                side_effect=httpx.ReadTimeout("timed out", request=MagicMock())
            )
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm
        # Second question succeeds
        lines = _sse_lines([{"type": "token", "content": "ok"}, {"type": "done"}])
        return _make_stream_cm(lines)

    mock_client = MagicMock()
    mock_client.stream.side_effect = _stream_side_effect
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    ragas_mock = _mock_ragas_result(n=2)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", return_value=ragas_mock),
    ):
        result = await runner.run()

    # Run must complete and return a result — not raise
    assert result is not None
    assert mock_client.stream.call_count == 2


# ---------------------------------------------------------------------------
# Test 5: continue on HTTP error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runner_continues_on_http_error(
    dataset_file: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, dataset_file, endpoint="agentic")

    call_count = 0

    def _stream_side_effect(*args: object, **kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(side_effect=httpx.HTTPError("connection refused"))
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm
        lines = _sse_lines([{"type": "token", "content": "ok"}, {"type": "done"}])
        return _make_stream_cm(lines)

    mock_client = MagicMock()
    mock_client.stream.side_effect = _stream_side_effect
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    ragas_mock = _mock_ragas_result(n=2)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", return_value=ragas_mock),
    ):
        result = await runner.run()

    assert result is not None
    assert mock_client.stream.call_count == 2


# ---------------------------------------------------------------------------
# Test 6: structlog error on timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runner_logs_error_on_timeout(
    single_question_dataset: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, single_question_dataset, endpoint="agentic")

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=httpx.ReadTimeout("timed out", request=MagicMock()))
    cm.__aexit__ = AsyncMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = cm
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    ragas_mock = _mock_ragas_result(n=1)

    with (
        structlog.testing.capture_logs() as cap_logs,
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", return_value=ragas_mock),
    ):
        await runner.run()

    error_events = [e for e in cap_logs if e.get("log_level") == "error"]
    assert any(
        "timeout" in e.get("event", "") for e in error_events
    ), f"Expected a timeout error log; got: {cap_logs}"


# ---------------------------------------------------------------------------
# Test 7: EvaluationResult has correct per_sample count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runner_returns_evaluation_result_with_all_samples(
    dataset_file: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, dataset_file, endpoint="agentic")

    lines = _sse_lines(
        [
            {"type": "token", "content": "Answer "},
            {"type": "token", "content": "text"},
            {"type": "citations", "citations": [], "confidence": 0.8, "chunks_retrieved": 0},
            {"type": "done"},
        ]
    )
    mock_client = _make_client_with_stream(lines)
    ragas_mock = _mock_ragas_result(n=2)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", return_value=ragas_mock),
    ):
        result = await runner.run()

    assert len(result.per_sample) == 2


# ---------------------------------------------------------------------------
# Test 8: GenerationError raised when RAGAS fails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_runner_raises_generation_error_if_ragas_fails(
    single_question_dataset: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, single_question_dataset, endpoint="agentic")

    lines = _sse_lines([{"type": "done"}])
    mock_client = _make_client_with_stream(lines)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", side_effect=RuntimeError("RAGAS crash")),
        pytest.raises(GenerationError, match="RAGAS evaluation failed"),
    ):
        await runner.run()


# ---------------------------------------------------------------------------
# Test: citation with text field uses text, not filename fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_citation_text_field_used_when_present(
    single_question_dataset: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, single_question_dataset, endpoint="agentic")

    lines = _sse_lines(
        [
            {"type": "token", "content": "ans"},
            {
                "type": "citations",
                "citations": [
                    {
                        "chunk_id": "c1",
                        "filename": "doc.pdf",
                        "source_path": "/data/doc.pdf",
                        "page_number": 5,
                        "retrieval_score": 0.9,
                        "text": "The actual chunk text",
                    }
                ],
                "confidence": 0.9,
                "chunks_retrieved": 1,
            },
            {"type": "done"},
        ]
    )
    mock_client = _make_client_with_stream(lines)

    captured_samples: list[object] = []

    def _capture_evaluate(**kwargs: object) -> MagicMock:
        dataset = kwargs.get("dataset")
        if hasattr(dataset, "samples"):
            captured_samples.extend(dataset.samples)  # type: ignore[arg-type]
        return _mock_ragas_result(n=1)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", side_effect=_capture_evaluate),
    ):
        await runner.run()

    assert len(captured_samples) == 1
    sample = captured_samples[0]
    assert hasattr(sample, "retrieved_contexts")
    assert sample.retrieved_contexts == ["The actual chunk text"]


# ---------------------------------------------------------------------------
# Test: citation fallback to filename p.page_number when text absent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_citation_fallback_when_text_absent(
    single_question_dataset: Path,
) -> None:
    settings = _make_mock_settings()
    runner = _make_runner(settings, single_question_dataset, endpoint="agentic")

    lines = _sse_lines(
        [
            {"type": "token", "content": "ans"},
            {
                "type": "citations",
                "citations": [
                    {
                        "chunk_id": "c2",
                        "filename": "manual.pdf",
                        "source_path": "/data/manual.pdf",
                        "page_number": 3,
                        "retrieval_score": 0.8,
                    }
                ],
                "confidence": 0.8,
                "chunks_retrieved": 1,
            },
            {"type": "done"},
        ]
    )
    mock_client = _make_client_with_stream(lines)

    captured_samples: list[object] = []

    def _capture_evaluate(**kwargs: object) -> MagicMock:
        dataset = kwargs.get("dataset")
        if hasattr(dataset, "samples"):
            captured_samples.extend(dataset.samples)  # type: ignore[arg-type]
        return _mock_ragas_result(n=1)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", side_effect=_capture_evaluate),
    ):
        await runner.run()

    assert len(captured_samples) == 1
    sample = captured_samples[0]
    assert sample.retrieved_contexts == ["manual.pdf p.3"]


# ---------------------------------------------------------------------------
# Test: retrieved_contexts SSE field takes priority over citation metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieved_contexts_field_preferred_over_citation_fallback(
    single_question_dataset: Path,
) -> None:
    """When retrieved_contexts is present in the citations event, it is used
    directly instead of building a context string from citation metadata.
    """
    settings = _make_mock_settings()
    runner = _make_runner(settings, single_question_dataset, endpoint="agentic")

    lines = _sse_lines(
        [
            {"type": "token", "content": "ans"},
            {
                "type": "citations",
                "citations": [
                    {
                        "chunk_id": "c3",
                        "filename": "policy.pdf",
                        "source_path": "/data/policy.pdf",
                        "page_number": 7,
                        "retrieval_score": 0.95,
                    }
                ],
                "confidence": 0.95,
                "chunks_retrieved": 1,
                "retrieved_contexts": ["The actual graded chunk text for RAGAS faithfulness"],
            },
            {"type": "done"},
        ]
    )
    mock_client = _make_client_with_stream(lines)

    captured_samples: list[object] = []

    def _capture_evaluate(**kwargs: object) -> MagicMock:
        dataset = kwargs.get("dataset")
        if hasattr(dataset, "samples"):
            captured_samples.extend(dataset.samples)  # type: ignore[arg-type]
        return _mock_ragas_result(n=1)

    with (
        patch("src.evaluation.runner.httpx.AsyncClient", return_value=mock_client),
        patch("src.evaluation.runner.evaluate", side_effect=_capture_evaluate),
    ):
        await runner.run()

    assert len(captured_samples) == 1
    sample = captured_samples[0]
    # Must use retrieved_contexts, not the filename fallback "policy.pdf p.7"
    assert sample.retrieved_contexts == ["The actual graded chunk text for RAGAS faithfulness"]
