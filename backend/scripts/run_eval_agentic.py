"""Agentic evaluation runner script for Phase 2f.

Calls the live POST /api/v1/query/agentic endpoint for each golden-dataset
question, collects SSE events, and computes RAGAS metrics.

Usage:
    poetry run python scripts/run_eval_agentic.py [--dataset PATH] [--output PATH]
    [--base-url URL] [--faithfulness-gate FLOAT]

Prerequisites:
    1. poetry install --with eval
    2. Full stack running: docker compose -f infra/docker-compose.yml up -d
    3. Knowledge corpus ingested (POST /api/v1/ingest already run)
    4. .env file with valid Azure OpenAI + Tavily credentials

Example:
    poetry run python scripts/run_eval_agentic.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

# Ensure project root is on the path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Settings
from src.evaluation.ragas_eval import load_baseline, save_baseline
from src.evaluation.runner import EvaluationRunner

DEFAULT_DATASET = Path(__file__).parent.parent / "src" / "evaluation" / "golden_dataset.json"
DEFAULT_OUTPUT = Path(__file__).parent.parent.parent / "data" / "eval_agentic_baseline.json"
DEFAULT_FAITHFULNESS_GATE = 0.85


async def main(
    dataset_path: Path,
    output_path: Path,
    base_url: str,
    faithfulness_gate: float,
) -> int:
    settings = Settings()  # type: ignore[call-arg]

    runner = EvaluationRunner(
        settings=settings,
        dataset_path=dataset_path,
        endpoint="agentic",
        base_url=base_url,
    )

    print(f"Running RAGAS agentic evaluation over {dataset_path} ...")
    print(f"Target endpoint: {base_url}/api/v1/query/agentic")
    result = await runner.run()

    # Save to JSON with run metadata
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_date": date.today().isoformat(),
        "endpoint": "agentic",
        "metrics": {
            "faithfulness": result.faithfulness,
            "answer_relevancy": result.answer_relevancy,
            "context_recall": result.context_recall,
            "context_precision": result.context_precision,
            "answer_correctness": result.answer_correctness,
        },
        "per_sample": result.per_sample,
        "failure_report": [
            s
            for s in result.per_sample
            if float(s.get("faithfulness", 1.0)) < 0.7
            or float(s.get("answer_correctness", 1.0)) < 0.7
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nResults written to {output_path}")

    # Also save as EvaluationResult for load_baseline compatibility
    baseline_path = output_path.parent / "eval_agentic_eval_result.json"
    save_baseline(result, baseline_path)

    # Load static baseline for comparison diff column
    static_baseline_path = Path("data/eval_baseline.json")
    prior = load_baseline(static_baseline_path)

    print("\n" + result.to_markdown(prior=prior))
    print(f"\nfaithfulness = {result.faithfulness:.4f}  (gate: ≥ {faithfulness_gate})")

    if result.faithfulness < faithfulness_gate:
        print(
            f"\nFAIL: faithfulness {result.faithfulness:.4f} is below Phase 2f gate of {faithfulness_gate}"
        )
        print(
            "Remediation: increase GRADER_THRESHOLD, reduce Tavily max_results to 3, "
            "or request architect review."
        )
        return 1

    print(f"\nPASS: faithfulness {result.faithfulness:.4f} ≥ {faithfulness_gate}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAGAS agentic evaluation (Phase 2f)")
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
        help="Output path for eval_agentic_baseline.json",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running API server",
    )
    parser.add_argument(
        "--faithfulness-gate",
        type=float,
        default=DEFAULT_FAITHFULNESS_GATE,
        help="Minimum faithfulness score to pass the gate",
    )
    args = parser.parse_args()
    sys.exit(
        asyncio.run(
            main(
                dataset_path=args.dataset,
                output_path=args.output,
                base_url=args.base_url,
                faithfulness_gate=args.faithfulness_gate,
            )
        )
    )
