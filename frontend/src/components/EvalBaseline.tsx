"use client";

import { useEffect, useState } from "react";
import type { JSX } from "react";

interface BaselineMetrics {
  faithfulness: number;
  answer_relevancy: number;
  context_recall: number;
  context_precision: number;
  answer_correctness: number;
}

const METRIC_LABELS: Record<keyof BaselineMetrics, string> = {
  faithfulness: "Faithfulness",
  answer_relevancy: "Answer Relevancy",
  context_recall: "Context Recall",
  context_precision: "Context Precision",
  answer_correctness: "Answer Correctness",
};

export function EvalBaseline(): JSX.Element {
  const [metrics, setMetrics] = useState<BaselineMetrics | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/proxy/eval/baseline")
      .then((res) => {
        if (res.status === 404) {
          setUnavailable(true);
          return null;
        }
        if (!res.ok) {
          setUnavailable(true);
          return null;
        }
        return res.json() as Promise<BaselineMetrics>;
      })
      .then((data) => {
        if (data) setMetrics(data);
      })
      .catch(() => setUnavailable(true))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="mt-2 text-xs text-gray-400">Loading…</p>;
  }

  if (unavailable || !metrics) {
    return (
      <p className="mt-2 text-xs text-gray-400">
        No baseline available — run evaluator first.
      </p>
    );
  }

  return (
    <ul className="mt-2 space-y-1">
      {(Object.keys(METRIC_LABELS) as Array<keyof BaselineMetrics>).map((key) => (
        <li key={key} className="flex justify-between text-xs text-gray-600">
          <span>{METRIC_LABELS[key]}</span>
          <span className="font-medium tabular-nums">{metrics[key] != null ? metrics[key].toFixed(4) : "—"}</span>
        </li>
      ))}
    </ul>
  );
}
