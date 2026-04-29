"use client";

import type { JSX } from "react";
import type { AgentStep, RouterStepPayload, RetrieverStepPayload } from "@/types";
import {
  isCriticPayload,
  isGeneratorPayload,
  isGraderPayload,
  isRetrieverPayload,
  isRouterPayload,
} from "@/lib/agentTypeGuards";

interface AgentTraceProps {
  steps: AgentStep[];
  isStreaming: boolean;
}

const QUERY_TYPE_LABELS: Record<RouterStepPayload["query_type"], string> = {
  factual: "Direct fact lookup",
  analytical: "Analytical reasoning",
  multi_hop: "Multi-step reasoning",
  ambiguous: "Needs clarification",
};

const STRATEGY_LABELS: Record<RouterStepPayload["strategy"], string> = {
  hybrid: "Hybrid search",
  dense: "Dense search",
  web: "Web search",
};

const RETRIEVER_STRATEGY_LABELS: Record<RetrieverStepPayload["strategy"], string> = {
  hybrid: "Hybrid search",
  dense: "Dense search",
  web: "Web search",
};

function criticColour(risk: number): string {
  if (risk < 0.4) return "bg-green-500";
  if (risk <= 0.7) return "bg-amber-500";
  return "bg-red-500";
}

function IterationBadge({ run }: { run: number | undefined }): JSX.Element | null {
  if (run === undefined || run <= 1) return null;
  return (
    <span className="ml-1 rounded-full bg-orange-100 px-1.5 py-0.5 text-orange-600">
      #{run}
    </span>
  );
}

function RouterCard({ step, run }: { step: AgentStep; run?: number }): JSX.Element | null {
  if (!isRouterPayload(step.payload)) return null;
  const { query_type, strategy, duration_ms } = step.payload;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
      <div className="mb-1 flex items-center font-semibold text-gray-700">
        Router
        <IterationBadge run={run} />
      </div>
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-blue-700">
          {QUERY_TYPE_LABELS[query_type]}
        </span>
        <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-indigo-700">
          {STRATEGY_LABELS[strategy]}
        </span>
      </div>
      <div className="mt-1 text-gray-400">{duration_ms}ms</div>
    </div>
  );
}

function RetrieverCard({ step, run }: { step: AgentStep; run?: number }): JSX.Element | null {
  if (!isRetrieverPayload(step.payload)) return null;
  const { strategy, docs_retrieved, duration_ms } = step.payload;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
      <div className="mb-1 flex items-center font-semibold text-gray-700">
        Retriever
        <IterationBadge run={run} />
      </div>
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full bg-green-100 px-2 py-0.5 text-green-700">
          {RETRIEVER_STRATEGY_LABELS[strategy]}
        </span>
        <span className="text-gray-500">{docs_retrieved} docs retrieved</span>
      </div>
      <div className="mt-1 text-gray-400">{duration_ms}ms</div>
    </div>
  );
}

function GraderCard({ step, run }: { step: AgentStep; run?: number }): JSX.Element | null {
  if (!isGraderPayload(step.payload)) return null;
  const { scores, web_fallback, duration_ms } = step.payload;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
      <div className="mb-1 flex items-center font-semibold text-gray-700">
        Grader
        <IterationBadge run={run} />
      </div>
      <div className="space-y-1">
        {scores.map((score, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-blue-400"
                style={{ width: `${Math.min(score * 100, 100)}%` }}
              />
            </div>
            <span className="w-8 text-right text-gray-500">{score != null ? (score * 100).toFixed(0) : "—"}%</span>
          </div>
        ))}
      </div>
      {web_fallback && (
        <span className="mt-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-amber-700">
          Web fallback
        </span>
      )}
      <div className="mt-1 text-gray-400">{duration_ms}ms</div>
    </div>
  );
}

function GeneratorCard({ step, run }: { step: AgentStep; run?: number }): JSX.Element | null {
  if (!isGeneratorPayload(step.payload)) return null;
  const { docs_used, confidence, duration_ms } = step.payload;
  const colourClass = criticColour(1 - confidence);
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
      <div className="mb-1 flex items-center font-semibold text-gray-700">
        Generator
        <IterationBadge run={run} />
      </div>
      <div className="flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full ${colourClass}`}
            style={{ width: `${confidence * 100}%` }}
          />
        </div>
        <span className="w-24 text-right text-gray-500">
          {(confidence * 100).toFixed(0)}% confidence
        </span>
      </div>
      <div className="mt-1 text-gray-500">{docs_used} docs</div>
      <div className="mt-1 text-gray-400">{duration_ms}ms</div>
    </div>
  );
}

function CriticCard({ step, run }: { step: AgentStep; run?: number }): JSX.Element | null {
  if (!isCriticPayload(step.payload)) return null;
  const { hallucination_risk, reruns, duration_ms } = step.payload;
  const colourClass = criticColour(hallucination_risk);
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
      <div className="mb-1 flex items-center font-semibold text-gray-700">
        Critic
        <IterationBadge run={run} />
      </div>
      <div className="flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full ${colourClass}`}
            style={{ width: `${Math.min(hallucination_risk * 100, 100)}%` }}
          />
        </div>
        <span className="w-12 text-right text-gray-500">
          {hallucination_risk != null ? (hallucination_risk * 100).toFixed(0) : "—"}% risk
        </span>
      </div>
      {reruns > 0 && (
        <div className="mt-1 text-gray-500">
          {reruns} rerun{reruns !== 1 ? "s" : ""}
        </div>
      )}
      <div className="mt-1 text-gray-400">{duration_ms}ms</div>
    </div>
  );
}

function LatencyBars({ steps }: { steps: AgentStep[] }): JSX.Element | null {
  const allNodesPresent = ["router", "retriever", "grader", "generator", "critic"].every(
    (n) => steps.some((s) => s.node === n),
  );
  if (!allNodesPresent) return null;

  const runCount = new Map<string, number>();
  const rows: Array<{ label: string; ms: number }> = steps.map((step) => {
    runCount.set(step.node, (runCount.get(step.node) ?? 0) + 1);
    const count = runCount.get(step.node)!;
    const nodeLabel =
      step.node === "router"
        ? "Router"
        : step.node === "retriever"
          ? "Retriever"
          : step.node === "grader"
            ? "Grader"
            : step.node === "generator"
              ? "Generator"
              : "Critic";
    const label = count > 1 ? `${nodeLabel} #${count}` : nodeLabel;
    const ms = (step.payload as { duration_ms: number }).duration_ms;
    return { label, ms };
  });

  const total = rows.reduce((sum, r) => sum + r.ms, 0);

  return (
    <div className="mt-3 space-y-1 text-xs">
      <div className="font-semibold text-gray-600">Latency breakdown</div>
      {rows.map(({ label, ms }, i) => (
        <div key={`${label}-${i}`} className="flex items-center gap-2">
          <span className="w-20 shrink-0 text-gray-500">{label}</span>
          <div className="flex-1 overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-2 rounded-full bg-blue-400"
              style={{ width: `${total > 0 ? (ms / total) * 100 : 0}%` }}
            />
          </div>
          <span className="w-12 text-right text-gray-500">{ms}ms</span>
        </div>
      ))}
      <div className="pt-1 text-right text-gray-400">Total: {total}ms</div>
    </div>
  );
}

export function AgentTrace({ steps, isStreaming }: AgentTraceProps): JSX.Element {
  const runCount = new Map<string, number>();

  return (
    <details open className="mt-2 text-xs">
      <summary className="cursor-pointer select-none font-semibold text-gray-500">
        Agent Trace ({steps.length} steps)
      </summary>
      <div className="mt-2 space-y-2">
        <div className="mb-2 flex flex-wrap items-center gap-1 text-gray-400">
          <span>Router → Retriever → Grader → Generator → Critic</span>
          <span className="ml-1 text-gray-300">(⟲ loops on escalation)</span>
        </div>
        {steps.map((step, i) => {
          runCount.set(step.node, (runCount.get(step.node) ?? 0) + 1);
          const run = runCount.get(step.node)!;
          const isLast = i === steps.length - 1;
          return (
            <div key={`${step.node}-${i}`} className="relative">
              {step.node === "router" && <RouterCard step={step} run={run} />}
              {step.node === "retriever" && <RetrieverCard step={step} run={run} />}
              {step.node === "grader" && <GraderCard step={step} run={run} />}
              {step.node === "generator" && <GeneratorCard step={step} run={run} />}
              {step.node === "critic" && <CriticCard step={step} run={run} />}
              {isLast && isStreaming && (
                <div className="absolute right-2 top-2">
                  <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
                </div>
              )}
            </div>
          );
        })}
      </div>
      {!isStreaming && <LatencyBars steps={steps} />}
    </details>
  );
}
