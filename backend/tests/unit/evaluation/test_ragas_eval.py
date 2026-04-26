from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.evaluation.ragas_eval import (
    EvaluationResult,
    RagasEvaluator,
    _nanmean,
    load_baseline,
    save_baseline,
)
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
    answer_correctness: float = 0.85,
    n: int = 2,
) -> MagicMock:
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: {  # type: ignore[assignment]
        "faithfulness": [faithfulness] * n,
        "answer_relevancy": [answer_relevancy] * n,
        "context_recall": [context_recall] * n,
        "context_precision": [context_precision] * n,
        "answer_correctness": [answer_correctness] * n,
    }[key]
    mock.scores = [
        {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_recall": context_recall,
            "context_precision": context_precision,
            "answer_correctness": answer_correctness,
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
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    faithfulness: float = 0.90,
    answer_relevancy: float = 0.82,
    context_recall: float = 0.75,
    context_precision: float = 0.78,
    answer_correctness: float = 0.85,
    per_sample: list[dict[str, float]] | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        context_recall=context_recall,
        context_precision=context_precision,
        answer_correctness=answer_correctness,
        per_sample=per_sample or [],
    )


# ---------------------------------------------------------------------------
# Tests — EvaluationResult (T10: answer_correctness field)
# ---------------------------------------------------------------------------


def test_evaluation_result_has_answer_correctness_field() -> None:
    result = _make_result(answer_correctness=0.88)
    assert result.answer_correctness == pytest.approx(0.88)


def test_to_markdown_contains_answer_correctness() -> None:
    result = _make_result(answer_correctness=0.88)
    md = result.to_markdown()
    assert "Answer Correctness" in md
    assert "0.8800" in md


def test_to_markdown_contains_all_metrics() -> None:
    result = _make_result()
    md = result.to_markdown()
    assert "Faithfulness" in md
    assert "Answer Relevancy" in md
    assert "Context Recall" in md
    assert "Context Precision" in md
    assert "Answer Correctness" in md
    assert "0.9000" in md
    assert "0.8200" in md


def test_to_markdown_table_format() -> None:
    result = _make_result(
        faithfulness=0.70,
        answer_relevancy=0.65,
        context_recall=0.60,
        context_precision=0.55,
        answer_correctness=0.72,
    )
    md = result.to_markdown()
    assert "|" in md
    assert "RAGAS Evaluation Results" in md


# ---------------------------------------------------------------------------
# Tests — T11: extended to_markdown with per-sample table, stddev, failures
# ---------------------------------------------------------------------------


def _make_result_with_samples(
    faithfulness_vals: list[float],
    answer_correctness_vals: list[float],
) -> EvaluationResult:
    """Build an EvaluationResult with per_sample list from provided per-metric values."""
    n = len(faithfulness_vals)
    assert len(answer_correctness_vals) == n
    per_sample = [
        {
            "faithfulness": faithfulness_vals[i],
            "answer_relevancy": 0.80,
            "context_recall": 0.75,
            "context_precision": 0.78,
            "answer_correctness": answer_correctness_vals[i],
        }
        for i in range(n)
    ]
    return EvaluationResult(
        faithfulness=sum(faithfulness_vals) / n,
        answer_relevancy=0.80,
        context_recall=0.75,
        context_precision=0.78,
        answer_correctness=sum(answer_correctness_vals) / n,
        per_sample=per_sample,
    )


def test_per_sample_table_row_count() -> None:
    result = _make_result_with_samples(
        faithfulness_vals=[0.9, 0.8, 0.7],
        answer_correctness_vals=[0.85, 0.80, 0.75],
    )
    md = result.to_markdown()
    # Each data row starts with "| 1 |", "| 2 |", "| 3 |"
    assert "| 1 |" in md
    assert "| 2 |" in md
    assert "| 3 |" in md
    assert "| 4 |" not in md


def test_failure_section_appears_when_faithfulness_below_threshold() -> None:
    result = _make_result_with_samples(
        faithfulness_vals=[0.9, 0.65],  # second sample below 0.7
        answer_correctness_vals=[0.85, 0.80],
    )
    md = result.to_markdown()
    assert "Failures" in md
    assert "Sample 2" in md


def test_failure_section_appears_when_answer_correctness_below_threshold() -> None:
    result = _make_result_with_samples(
        faithfulness_vals=[0.9, 0.85],
        answer_correctness_vals=[0.85, 0.60],  # second sample below 0.7
    )
    md = result.to_markdown()
    assert "Failures" in md
    assert "Sample 2" in md


def test_failure_section_absent_when_all_pass() -> None:
    result = _make_result_with_samples(
        faithfulness_vals=[0.9, 0.85, 0.80],
        answer_correctness_vals=[0.88, 0.82, 0.75],
    )
    md = result.to_markdown()
    assert "Failures" not in md


def test_stddev_computed_correctly() -> None:
    import statistics

    vals = [0.6, 0.8, 1.0]
    result = _make_result_with_samples(
        faithfulness_vals=vals,
        answer_correctness_vals=[0.85, 0.85, 0.85],
    )
    md = result.to_markdown()
    expected_sd = statistics.stdev(vals)
    # The value is formatted to 4 decimal places in the table
    assert f"{expected_sd:.4f}" in md


def test_distribution_stats_section_present_with_per_sample() -> None:
    result = _make_result_with_samples(
        faithfulness_vals=[0.9, 0.8],
        answer_correctness_vals=[0.85, 0.75],
    )
    md = result.to_markdown()
    assert "Distribution Statistics" in md
    assert "StdDev" in md


def test_asdict_works_on_evaluation_result() -> None:
    """dataclasses.asdict() must work — used for JSON serialisation."""
    result = _make_result(
        per_sample=[{"faithfulness": 0.9, "answer_correctness": 0.85}]
    )
    d = dataclasses.asdict(result)
    assert d["faithfulness"] == pytest.approx(0.90)
    assert d["answer_correctness"] == pytest.approx(0.85)
    assert isinstance(d["per_sample"], list)


# ---------------------------------------------------------------------------
# Tests — T12: save_baseline / load_baseline / diff column
# ---------------------------------------------------------------------------


def test_save_and_load_baseline_round_trip(tmp_path: Path) -> None:
    baseline_path = tmp_path / "eval_baseline.json"
    result = _make_result(
        per_sample=[{"faithfulness": 0.9, "answer_relevancy": 0.8, "answer_correctness": 0.85,
                     "context_recall": 0.75, "context_precision": 0.78}]
    )
    save_baseline(result, baseline_path)
    loaded = load_baseline(baseline_path)
    assert loaded is not None
    assert loaded.faithfulness == pytest.approx(result.faithfulness)
    assert loaded.answer_correctness == pytest.approx(result.answer_correctness)
    assert loaded.per_sample == result.per_sample


def test_save_baseline_creates_parent_dirs(tmp_path: Path) -> None:
    nested_path = tmp_path / "nested" / "dir" / "baseline.json"
    result = _make_result()
    save_baseline(result, nested_path)
    assert nested_path.exists()


def test_load_baseline_returns_none_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.json"
    assert load_baseline(missing) is None


def test_diff_column_present_when_prior_passed() -> None:
    prior = _make_result(faithfulness=0.80, answer_correctness=0.75)
    current = _make_result(faithfulness=0.90, answer_correctness=0.85)
    md = current.to_markdown(prior=prior)
    assert "Δ vs Baseline" in md
    # +0.10 diff for faithfulness
    assert "+0.1000" in md


def test_diff_column_absent_when_no_prior() -> None:
    result = _make_result()
    md = result.to_markdown()
    assert "Δ vs Baseline" not in md


def test_negative_diff_formatted_with_minus_sign() -> None:
    prior = _make_result(faithfulness=0.90)
    current = _make_result(faithfulness=0.75)
    md = current.to_markdown(prior=prior)
    # -0.15 diff for faithfulness
    assert "-0.1500" in md


def test_diff_column_shows_all_five_metrics() -> None:
    prior = _make_result(
        faithfulness=0.80,
        answer_relevancy=0.70,
        context_recall=0.65,
        context_precision=0.68,
        answer_correctness=0.75,
    )
    current = _make_result(
        faithfulness=0.90,
        answer_relevancy=0.82,
        context_recall=0.75,
        context_precision=0.78,
        answer_correctness=0.85,
    )
    md = current.to_markdown(prior=prior)
    assert "Faithfulness" in md
    assert "Answer Correctness" in md
    assert "Δ vs Baseline" in md


# ---------------------------------------------------------------------------
# Tests — _nanmean
# ---------------------------------------------------------------------------


def test_nanmean_normal() -> None:
    assert _nanmean([0.8, 0.9, 0.7]) == pytest.approx(0.8)


def test_nanmean_with_nan() -> None:
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
    assert result.answer_correctness == pytest.approx(0.85)
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
