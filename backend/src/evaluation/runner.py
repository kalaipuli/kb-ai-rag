"""EvaluationRunner — evaluate the API pipeline (static or agentic) via HTTP.

Sends each golden-dataset question to the running API over SSE, collects the
answer tokens and cited contexts, then computes the same five RAGAS metrics
used by RagasEvaluator.

This module must not be imported inside a FastAPI route handler.  It is an
offline evaluation tool run as a standalone script.  See ADR-009 §4.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Literal

import httpx
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

from src.config import Settings
from src.evaluation.ragas_eval import EvaluationResult, _nanmean
from src.exceptions import GenerationError

logger = structlog.get_logger(__name__)

_ENDPOINT_MAP: dict[str, str] = {
    "static": "/api/v1/query",
    "agentic": "/api/v1/query/agentic",
}

_QUESTION_TIMEOUT_SECONDS: float = 60.0


def _citation_to_context(citation: dict[str, object]) -> str:
    """Convert a single citations-event citation dict to a context string.

    Uses the ``text`` field when present; falls back to
    ``"{filename} p.{page_number}"``.
    """
    if citation.get("text"):
        return str(citation["text"])
    filename = citation.get("filename", "")
    page = citation.get("page_number")
    return f"{filename} p.{page}"


class EvaluationRunner:
    """Calls the running API over HTTP and runs RAGAS metrics on the results.

    Supports both the static chain (``POST /api/v1/query``) and the agentic
    pipeline (``POST /api/v1/query/agentic``).  Each question is sent in an
    independent ``httpx.AsyncClient.stream`` call with a 60-second timeout.
    Timeout or HTTP errors are logged and treated as empty answers so the run
    continues to completion.

    Args:
        settings: Application settings — used for the ``X-API-Key`` header
                  and for building the Azure LLM / embeddings wrappers that
                  RAGAS needs internally for metric computation.
        dataset_path: Path to ``golden_dataset.json``.
        endpoint: ``"static"`` or ``"agentic"``.
        base_url: Base URL of the running API server.  Defaults to
                  ``"http://localhost:8000"``.
    """

    def __init__(
        self,
        settings: Settings,
        dataset_path: Path,
        endpoint: Literal["static", "agentic"],
        base_url: str = "http://localhost:8000",
    ) -> None:
        self._settings = settings
        self._dataset_path = dataset_path
        self._endpoint = endpoint
        self._base_url = base_url
        self._api_path = _ENDPOINT_MAP[endpoint]

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
                api_key=api_key_str,  # type: ignore[arg-type]
                azure_deployment=settings.azure_embedding_deployment,
                api_version=settings.azure_openai_api_version,
            )
        )

    def _load_dataset(self) -> list[dict[str, str]]:
        raw = self._dataset_path.read_text(encoding="utf-8")
        data: list[dict[str, str]] = json.loads(raw)
        return data

    def _build_headers(self, session_id: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "X-API-Key": self._settings.api_key.get_secret_value(),
            "Accept": "text/event-stream",
        }
        if session_id is not None:
            headers["X-Session-ID"] = session_id
        return headers

    async def _query_question(
        self,
        client: httpx.AsyncClient,
        question: str,
    ) -> tuple[str, list[str]]:
        """Send a single question to the API and collect answer + contexts.

        Returns a ``(answer, contexts)`` tuple.  On timeout or HTTP error the
        tuple is ``("", [])``.
        """
        headers = self._build_headers(
            session_id=str(uuid.uuid4()) if self._endpoint == "agentic" else None
        )
        payload: dict[str, str] = {"query": question}

        tokens: list[str] = []
        contexts: list[str] = []

        try:
            async with client.stream(
                "POST",
                self._api_path,
                json=payload,
                headers=headers,
                timeout=_QUESTION_TIMEOUT_SECONDS,
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        event: dict[str, object] = json.loads(line.removeprefix("data: "))
                    except json.JSONDecodeError:
                        continue
                    event_type = event.get("type")
                    if event_type == "token":
                        tokens.append(str(event.get("content", "")))
                    elif event_type == "citations":
                        raw_citations = event.get("citations")
                        if isinstance(raw_citations, list):
                            contexts = [
                                _citation_to_context(c)
                                for c in raw_citations
                                if isinstance(c, dict)
                            ]
                    elif event_type == "done":
                        break
        except httpx.ReadTimeout as exc:
            logger.error(
                "evaluation_question_timeout",
                question=question,
                endpoint=self._endpoint,
                error=str(exc),
            )
            return "", []
        except httpx.HTTPError as exc:
            logger.error(
                "evaluation_question_http_error",
                question=question,
                endpoint=self._endpoint,
                error=str(exc),
            )
            return "", []

        return "".join(tokens), contexts

    async def run(self) -> EvaluationResult:
        """Query the pipeline for every golden question and compute RAGAS metrics.

        Returns:
            An :class:`EvaluationResult` with aggregated and per-sample scores.

        Raises:
            GenerationError: If the RAGAS ``evaluate`` call fails.
        """
        dataset = self._load_dataset()
        samples: list[SingleTurnSample] = []

        async with httpx.AsyncClient(base_url=self._base_url) as client:
            for entry in dataset:
                question = entry["question"]
                ground_truth = entry["ground_truth"]

                answer, contexts = await self._query_question(client, question)

                samples.append(
                    SingleTurnSample(
                        user_input=question,
                        retrieved_contexts=contexts,
                        response=answer,
                        reference=ground_truth,
                    )
                )

        logger.info(
            "evaluation_runner_samples_collected",
            endpoint=self._endpoint,
            sample_count=len(samples),
        )

        eval_dataset = EvaluationDataset(samples=samples)

        try:
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
        except Exception as exc:
            logger.error(
                "evaluation_runner_ragas_failed",
                endpoint=self._endpoint,
                error=str(exc),
            )
            raise GenerationError(f"RAGAS evaluation failed: {exc}") from exc

        faithfulness = _nanmean(ragas_result["faithfulness"])
        answer_relevancy = _nanmean(ragas_result["answer_relevancy"])
        context_recall = _nanmean(ragas_result["context_recall"])
        context_precision = _nanmean(ragas_result["context_precision"])
        answer_correctness = _nanmean(ragas_result["answer_correctness"])

        logger.info(
            "evaluation_runner_complete",
            endpoint=self._endpoint,
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
