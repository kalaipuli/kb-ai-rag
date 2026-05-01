"""RAGAS evaluation runner for the MVP RAG pipeline.

Loads a golden dataset (question + ground_truth pairs), runs each question
through GenerationChain, and computes five RAGAS metrics:
faithfulness, answer_relevancy, context_recall, context_precision,
answer_correctness.

Install dependencies with: poetry install --with eval
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import math
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.evaluation import EvaluationResult as RagasEvaluationResult
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    AnswerCorrectness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from src.api.schemas import Citation, GenerationResult
from src.config import Settings
from src.exceptions import GenerationError
from src.generation.chain import GenerationChain

logger = structlog.get_logger(__name__)

_METRICS: list[str] = [
    "faithfulness",
    "answer_relevancy",
    "context_recall",
    "context_precision",
    "answer_correctness",
]


@dataclass
class EvaluationResult:
    """Aggregated RAGAS metrics for one evaluation run."""

    faithfulness: float
    answer_relevancy: float
    context_recall: float
    context_precision: float
    answer_correctness: float
    per_sample: list[dict[str, float]] = field(default_factory=list)

    def to_markdown(self, prior: EvaluationResult | None = None) -> str:
        show_diff = prior is not None

        if show_diff:
            assert prior is not None  # narrowed: show_diff is only True when prior is not None
            lines = [
                "## RAGAS Evaluation Results\n",
                "| Metric | Score | Δ vs Baseline |",
                "|--------|-------|----------------|",
            ]
            prior_vals: dict[str, float] = {
                "faithfulness": prior.faithfulness,
                "answer_relevancy": prior.answer_relevancy,
                "context_recall": prior.context_recall,
                "context_precision": prior.context_precision,
                "answer_correctness": prior.answer_correctness,
            }
            current_vals: dict[str, float] = {
                "faithfulness": self.faithfulness,
                "answer_relevancy": self.answer_relevancy,
                "context_recall": self.context_recall,
                "context_precision": self.context_precision,
                "answer_correctness": self.answer_correctness,
            }
            metric_labels: dict[str, str] = {
                "faithfulness": "Faithfulness",
                "answer_relevancy": "Answer Relevancy",
                "context_recall": "Context Recall",
                "context_precision": "Context Precision",
                "answer_correctness": "Answer Correctness",
            }
            for m in _METRICS:
                diff = current_vals[m] - prior_vals[m]
                diff_str = f"{diff:+.4f}"
                lines.append(f"| {metric_labels[m]} | {current_vals[m]:.4f} | {diff_str} |")
        else:
            lines = [
                "## RAGAS Evaluation Results\n",
                "| Metric | Score |",
                "|--------|-------|",
                f"| Faithfulness | {self.faithfulness:.4f} |",
                f"| Answer Relevancy | {self.answer_relevancy:.4f} |",
                f"| Context Recall | {self.context_recall:.4f} |",
                f"| Context Precision | {self.context_precision:.4f} |",
                f"| Answer Correctness | {self.answer_correctness:.4f} |",
            ]

        if self.per_sample:
            # Distribution statistics: min, max, stddev per metric
            lines.append("\n### Distribution Statistics\n")
            lines.append("| Metric | Min | Max | StdDev |")
            lines.append("|--------|-----|-----|--------|")
            for m in _METRICS:
                vals = [
                    float(s[m]) for s in self.per_sample if m in s and not math.isnan(float(s[m]))
                ]
                if vals:
                    mn = min(vals)
                    mx = max(vals)
                    sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
                    lines.append(
                        f"| {m.replace('_', ' ').title()} | {mn:.4f} | {mx:.4f} | {sd:.4f} |"
                    )

            # Per-sample table
            lines.append("\n### Per-Sample Scores\n")
            header = "| # | " + " | ".join(m.replace("_", " ").title() for m in _METRICS) + " |"
            sep = "|---|" + "---|" * len(_METRICS)
            lines.append(header)
            lines.append(sep)
            for i, sample in enumerate(self.per_sample):
                row_vals = " | ".join(f"{float(sample.get(m, float('nan'))):.4f}" for m in _METRICS)
                lines.append(f"| {i + 1} | {row_vals} |")

            # Failure section
            failures = [
                (i, s)
                for i, s in enumerate(self.per_sample)
                if float(s.get("faithfulness", 1.0)) < 0.7
                or float(s.get("answer_correctness", 1.0)) < 0.7
            ]
            if failures:
                lines.append("\n### Failures (faithfulness or answer_correctness < 0.7)\n")
                for i, s in failures:
                    lines.append(
                        f"- Sample {i + 1}: faithfulness={float(s.get('faithfulness', float('nan'))):.4f},"
                        f" answer_correctness={float(s.get('answer_correctness', float('nan'))):.4f}"
                    )

        return "\n".join(lines)


def save_baseline(result: EvaluationResult, path: Path) -> None:
    """Serialise EvaluationResult to JSON at path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataclasses.asdict(result), indent=2), encoding="utf-8")


def load_baseline(path: Path) -> EvaluationResult | None:
    """Load a prior EvaluationResult from JSON, or return None if file missing."""
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return EvaluationResult(**raw)


def _default_context_fetcher(citations: list[Citation]) -> list[str]:
    return [f"{c.filename} p.{c.page_number}" for c in citations]


def _get_contexts(
    result: GenerationResult, context_fetcher: Callable[[list[Citation]], list[str]]
) -> list[str]:
    if result.retrieved_contexts:
        return result.retrieved_contexts
    return context_fetcher(result.citations)


def _nanmean(values: list[float]) -> float:
    finite = [v for v in values if not math.isnan(v)]
    return statistics.fmean(finite) if finite else 0.0


class RagasEvaluator:
    """Runs a RAGAS evaluation pass over a golden dataset.

    This is an **offline evaluation tool** invoked as a standalone script, not
    via a FastAPI route handler.  It constructs its own ``AzureChatOpenAI`` and
    ``AzureOpenAIEmbeddings`` instances because it runs outside the FastAPI
    lifespan — there is no ``app.state`` to inject from.  If this class is ever
    wired into a live route it must accept injected clients via constructor
    instead of constructing its own.  See architecture-rules.md §P2 and
    ADR-009 §4.

    Args:
        generation_chain: Live GenerationChain to query per golden question.
        settings: Application settings used to build the Azure LLM/embeddings
                  wrappers that RAGAS uses internally for metric computation.
        dataset_path: Path to ``golden_dataset.json``.
        context_fetcher: Optional override that converts Citation objects to
                         raw text strings for the ``retrieved_contexts`` field.
                         Defaults to ``"{filename} p.{page_number}"`` strings.
    """

    def __init__(
        self,
        generation_chain: GenerationChain,
        settings: Settings,
        dataset_path: Path,
        context_fetcher: Callable[[list[Citation]], list[str]] | None = None,
    ) -> None:
        self._chain = generation_chain
        self._dataset_path = dataset_path
        self._context_fetcher = context_fetcher or _default_context_fetcher

        api_key_str = settings.azure_openai_api_key.get_secret_value()
        self._ragas_llm = LangchainLLMWrapper(
            AzureChatOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=api_key_str,  # type: ignore[arg-type]  # httpx str accepted at call site
                azure_deployment=settings.azure_chat_deployment,
                api_version=settings.azure_openai_api_version,
                temperature=0,
            )
        )
        self._ragas_embeddings = LangchainEmbeddingsWrapper(
            AzureOpenAIEmbeddings(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=api_key_str,  # type: ignore[arg-type]  # httpx str accepted at call site
                azure_deployment=settings.azure_embedding_deployment,
                api_version=settings.azure_openai_api_version,
            )
        )

    def _load_dataset(self) -> list[dict[str, str]]:
        raw = self._dataset_path.read_text(encoding="utf-8")
        data: list[dict[str, str]] = json.loads(raw)
        return data

    async def run(self) -> EvaluationResult:
        """Query the pipeline for each golden question and compute RAGAS metrics."""
        dataset = self._load_dataset()
        samples: list[SingleTurnSample] = []

        for entry in dataset:
            question = entry["question"]
            ground_truth = entry["ground_truth"]

            try:
                result = await self._chain.generate(question)
            except GenerationError:
                raise
            except Exception as exc:
                logger.error("evaluation_generate_failed", question=question, error=str(exc))
                raise GenerationError(f"Evaluation generate failed: {exc}") from exc

            contexts = _get_contexts(result, self._context_fetcher)
            samples.append(
                SingleTurnSample(
                    user_input=question,
                    retrieved_contexts=contexts,
                    response=result.answer,
                    reference=ground_truth,
                )
            )

        eval_dataset = EvaluationDataset(samples=samples)

        ragas_result: RagasEvaluationResult = await asyncio.to_thread(
            evaluate,
            dataset=eval_dataset,
            metrics=[
                Faithfulness(),
                AnswerRelevancy(),
                ContextRecall(),
                ContextPrecision(),
                AnswerCorrectness(),
            ],
            llm=self._ragas_llm,
            embeddings=self._ragas_embeddings,
            show_progress=False,
        )

        faithfulness = _nanmean(ragas_result["faithfulness"])
        answer_relevancy = _nanmean(ragas_result["answer_relevancy"])
        context_recall = _nanmean(ragas_result["context_recall"])
        context_precision = _nanmean(ragas_result["context_precision"])
        answer_correctness = _nanmean(ragas_result["answer_correctness"])

        logger.info(
            "ragas_evaluation_complete",
            sample_count=len(samples),
            faithfulness=round(faithfulness, 4),
            answer_correctness=round(answer_correctness, 4),
        )

        return EvaluationResult(
            faithfulness=faithfulness,
            answer_relevancy=answer_relevancy,
            context_recall=context_recall,
            context_precision=context_precision,
            answer_correctness=answer_correctness,
            per_sample=list(ragas_result.scores),
        )
