from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.evaluation.ragas_eval import EvaluationResult, RagasEvaluator, _nanmean
from src.exceptions import GenerationError
from src.schemas.generation import Citation, GenerationResult

# ---------------------------------------------------------------------------
# Fixtures
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

MOCK_GEN_RESULT = GenerationResult(
    query="How do I reset my VPN?",
    answer="Disconnect and reconnect after clearing credentials.",
    citations=[
        Citation(
            chunk_id="c1",
            filename="vpn_setup.txt",
            source_path="/data/vpn_setup.txt",
            page_number=None,
        )
    ],
    confidence=0.85,
)


def _mock_ragas_result(
    faithfulness: float = 0.90,
    answer_relevancy: float = 0.82,
    context_recall: float = 0.75,
    context_precision: float = 0.78,
    n: int = 2,
) -> MagicMock:
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: {  # type: ignore[assignment]
        "faithfulness": [faithfulness] * n,
        "answer_relevancy": [answer_relevancy] * n,
        "context_recall": [context_recall] * n,
        "context_precision": [context_precision] * n,
    }[key]
    mock.scores = [
        {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_recall": context_recall,
            "context_precision": context_precision,
        }
    ] * n
    return mock


@pytest.fixture
def dataset_file(tmp_path: Path) -> Path:
    p = tmp_path / "golden.json"
    p.write_text(json.dumps(GOLDEN_DATASET))
    return p


@pytest.fixture
def mock_chain() -> MagicMock:
    chain = MagicMock()
    chain.generate = AsyncMock(return_value=MOCK_GEN_RESULT)
    return chain


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.azure_openai_endpoint = "https://fake.openai.azure.com/"
    settings.azure_openai_api_key.get_secret_value.return_value = "fake-key"
    settings.azure_chat_deployment = "gpt-4o"
    settings.azure_embedding_deployment = "text-embedding-3-large"
    settings.azure_openai_api_version = "2024-08-01-preview"
    return settings


def _make_evaluator(
    mock_chain: MagicMock,
    mock_settings: MagicMock,
    dataset_file: Path,
    context_fetcher: object = None,
) -> RagasEvaluator:
    with (
        patch("src.evaluation.ragas_eval.AzureChatOpenAI"),
        patch("src.evaluation.ragas_eval.AzureOpenAIEmbeddings"),
        patch("src.evaluation.ragas_eval.LangchainLLMWrapper"),
        patch("src.evaluation.ragas_eval.LangchainEmbeddingsWrapper"),
    ):
        return RagasEvaluator(
            generation_chain=mock_chain,
            settings=mock_settings,
            dataset_path=dataset_file,
            context_fetcher=context_fetcher,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Tests — EvaluationResult
# ---------------------------------------------------------------------------


def test_to_markdown_contains_all_metrics() -> None:
    result = EvaluationResult(
        faithfulness=0.90,
        answer_relevancy=0.82,
        context_recall=0.75,
        context_precision=0.78,
    )
    md = result.to_markdown()
    assert "Faithfulness" in md
    assert "Answer Relevancy" in md
    assert "Context Recall" in md
    assert "Context Precision" in md
    assert "0.9000" in md
    assert "0.8200" in md


def test_to_markdown_table_format() -> None:
    result = EvaluationResult(
        faithfulness=0.70,
        answer_relevancy=0.65,
        context_recall=0.60,
        context_precision=0.55,
    )
    md = result.to_markdown()
    assert "|" in md
    assert "RAGAS Evaluation Results" in md


# ---------------------------------------------------------------------------
# Tests — _nanmean
# ---------------------------------------------------------------------------


def test_nanmean_normal() -> None:
    assert _nanmean([0.8, 0.9, 0.7]) == pytest.approx(0.8)


def test_nanmean_with_nan() -> None:
    import math

    result = _nanmean([0.9, float("nan"), 0.7])
    assert not math.isnan(result)
    assert result == pytest.approx(0.8)


def test_nanmean_all_nan() -> None:
    assert _nanmean([float("nan"), float("nan")]) == 0.0


def test_nanmean_empty() -> None:
    assert _nanmean([]) == 0.0


# ---------------------------------------------------------------------------
# Tests — RagasEvaluator.run()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_happy_path(
    dataset_file: Path, mock_chain: MagicMock, mock_settings: MagicMock
) -> None:
    evaluator = _make_evaluator(mock_chain, mock_settings, dataset_file)
    ragas_mock = _mock_ragas_result(n=2)

    with patch("src.evaluation.ragas_eval.evaluate", return_value=ragas_mock):
        result = await evaluator.run()

    assert result.faithfulness == pytest.approx(0.90)
    assert result.answer_relevancy == pytest.approx(0.82)
    assert result.context_recall == pytest.approx(0.75)
    assert result.context_precision == pytest.approx(0.78)
    assert len(result.per_sample) == 2
    assert mock_chain.generate.await_count == 2


@pytest.mark.asyncio
async def test_run_generation_error_propagates(
    dataset_file: Path, mock_chain: MagicMock, mock_settings: MagicMock
) -> None:
    mock_chain.generate = AsyncMock(side_effect=GenerationError("LLM timeout"))
    evaluator = _make_evaluator(mock_chain, mock_settings, dataset_file)

    with pytest.raises(GenerationError, match="LLM timeout"):
        await evaluator.run()


@pytest.mark.asyncio
async def test_run_unexpected_error_wrapped_as_generation_error(
    dataset_file: Path, mock_chain: MagicMock, mock_settings: MagicMock
) -> None:
    mock_chain.generate = AsyncMock(side_effect=RuntimeError("network error"))
    evaluator = _make_evaluator(mock_chain, mock_settings, dataset_file)

    with pytest.raises(GenerationError, match="Evaluation generate failed"):
        await evaluator.run()


@pytest.mark.asyncio
async def test_run_custom_context_fetcher_called(
    dataset_file: Path, mock_chain: MagicMock, mock_settings: MagicMock
) -> None:
    captured: list[list[Citation]] = []

    def fetcher(citations: list[Citation]) -> list[str]:
        captured.append(list(citations))
        return ["custom context text"]

    evaluator = _make_evaluator(mock_chain, mock_settings, dataset_file, context_fetcher=fetcher)
    ragas_mock = _mock_ragas_result(n=2)

    with patch("src.evaluation.ragas_eval.evaluate", return_value=ragas_mock):
        await evaluator.run()

    assert len(captured) == 2
    assert captured[0][0].chunk_id == "c1"


# ---------------------------------------------------------------------------
# Tests — dataset loading
# ---------------------------------------------------------------------------


def test_load_dataset_returns_correct_count(
    dataset_file: Path, mock_chain: MagicMock, mock_settings: MagicMock
) -> None:
    evaluator = _make_evaluator(mock_chain, mock_settings, dataset_file)
    data = evaluator._load_dataset()
    assert len(data) == 2
    assert data[0]["question"] == "How do I reset my VPN?"


def test_load_dataset_missing_file_raises(
    tmp_path: Path, mock_chain: MagicMock, mock_settings: MagicMock
) -> None:
    evaluator = _make_evaluator(mock_chain, mock_settings, tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError):
        evaluator._load_dataset()
