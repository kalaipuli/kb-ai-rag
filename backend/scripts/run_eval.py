"""Evaluation runner script for Phase 1f.

Usage:
    poetry run python scripts/run_eval.py [--dataset PATH] [--output PATH]

Prerequisites:
    1. poetry install --with eval
    2. A running Qdrant instance with the knowledge corpus already ingested:
           poetry run python -m src.ingestion.pipeline --folder data/knowledge
    3. .env file with valid Azure OpenAI credentials

Example:
    poetry run python scripts/run_eval.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is on the path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Settings
from src.evaluation.ragas_eval import RagasEvaluator
from src.generation.chain import GenerationChain
from src.ingestion.bm25_store import BM25Store
from src.ingestion.embedder import Embedder
from src.retrieval.retriever import HybridRetriever

DEFAULT_DATASET = Path(__file__).parent.parent / "src" / "evaluation" / "golden_dataset.json"
DEFAULT_OUTPUT = Path(__file__).parent.parent.parent / "docs" / "evaluation_results.md"


async def main(dataset_path: Path, output_path: Path) -> int:
    settings = Settings()  # type: ignore[call-arg]

    bm25_store = BM25Store(index_path=Path(settings.bm25_index_path))
    if Path(settings.bm25_index_path).exists():
        bm25_store.load()
    embedder = Embedder(settings=settings)
    retriever = HybridRetriever(settings=settings, bm25_store=bm25_store, embedder=embedder)
    chain = GenerationChain(settings=settings, hybrid_retriever=retriever)

    evaluator = RagasEvaluator(
        generation_chain=chain,
        settings=settings,
        dataset_path=dataset_path,
    )

    print(f"Running RAGAS evaluation over {dataset_path} ...")
    result = await evaluator.run()

    print("\n" + result.to_markdown())
    print(f"\nfaithfulness = {result.faithfulness:.4f}  (gate: ≥ 0.70)")

    md = _build_results_doc(result, dataset_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    print(f"\nResults written to {output_path}")

    if result.faithfulness < 0.70:
        print("WARNING: faithfulness below Phase 1 gate threshold of 0.70")
        return 1
    return 0


def _build_results_doc(result: object, dataset_path: Path) -> str:
    from datetime import date

    from src.evaluation.ragas_eval import EvaluationResult

    assert isinstance(result, EvaluationResult)

    lines = [
        "# RAG Evaluation Results — Phase 1f Baseline",
        "",
        f"> Generated: {date.today().isoformat()}  ",
        f"> Dataset: `{dataset_path.name}` ({len(result.per_sample)} questions)  ",
        "> Model: Azure OpenAI GPT-4o  ",
        "> Retrieval: Hybrid (Qdrant dense + BM25) → cross-encoder re-ranker",
        "",
        "---",
        "",
        result.to_markdown(),
        "",
        "---",
        "",
        "## Phase 1 Gate",
        "",
        "| Criterion | Required | Actual | Status |",
        "|-----------|----------|--------|--------|",
        f"| Faithfulness | ≥ 0.70 | {result.faithfulness:.4f} | {'✅ Pass' if result.faithfulness >= 0.70 else '❌ Fail'} |",
        "",
        "---",
        "",
        "## Per-Sample Scores",
        "",
        "| # | Faithfulness | Answer Relevancy | Context Recall | Context Precision |",
        "|---|-------------|-----------------|---------------|------------------|",
    ]
    for i, s in enumerate(result.per_sample, start=1):
        lines.append(
            f"| {i} "
            f"| {s.get('faithfulness', float('nan')):.4f} "
            f"| {s.get('answer_relevancy', float('nan')):.4f} "
            f"| {s.get('context_recall', float('nan')):.4f} "
            f"| {s.get('context_precision', float('nan')):.4f} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation baseline")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to golden_dataset.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output path for evaluation_results.md",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.dataset, args.output)))
