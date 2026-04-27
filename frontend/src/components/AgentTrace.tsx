"use client";

import type { JSX } from "react";
import type { AgentStep, RouterStepPayload } from "@/types";
import {
  isCriticPayload,
  isGraderPayload,
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

function criticColour(risk: number): string {
  if (risk < 0.4) return "bg-green-500";
  if (risk <= 0.7) return "bg-amber-500";
  return "bg-red-500";
}

function RouterCard({ step }: { step: AgentStep }): JSX.Element | null {
  if (!isRouterPayload(step.payload)) return null;
  const { query_type, strategy, duration_ms } = step.payload;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
      <div className="mb-1 font-semibold text-gray-700">Router</div>
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

function GraderCard({ step }: { step: AgentStep }): JSX.Element | null {
  if (!isGraderPayload(step.payload)) return null;
  const { scores, web_fallback, duration_ms } = step.payload;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
      <div className="mb-1 font-semibold text-gray-700">Grader</div>
      <div className="space-y-1">
        {scores.map((score, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-blue-400"
                style={{ width: `${Math.min(score * 100, 100)}%` }}
              />
            </div>
            <span className="w-8 text-right text-gray-500">{(score * 100).toFixed(0)}%</span>
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

function CriticCard({ step }: { step: AgentStep }): JSX.Element | null {
  if (!isCriticPayload(step.payload)) return null;
  const { hallucination_risk, reruns, duration_ms } = step.payload;
  const colourClass = criticColour(hallucination_risk);
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs">
      <div className="mb-1 font-semibold text-gray-700">Critic</div>
      <div className="flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full ${colourClass}`}
            style={{ width: `${Math.min(hallucination_risk * 100, 100)}%` }}
          />
        </div>
        <span className="w-12 text-right text-gray-500">
          {(hallucination_risk * 100).toFixed(0)}% risk
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
  const router = steps.find((s) => s.node === "router");
  const grader = steps.find((s) => s.node === "grader");
  const critic = steps.find((s) => s.node === "critic");

  if (!router || !grader || !critic) return null;

  if (
    !isRouterPayload(router.payload) ||
    !isGraderPayload(grader.payload) ||
    !isCriticPayload(critic.payload)
  ) {
    return null;
  }

  const routerMs = router.payload.duration_ms;
  const graderMs = grader.payload.duration_ms;
  const criticMs = critic.payload.duration_ms;
  const total = routerMs + graderMs + criticMs;

  const rows: Array<{ label: string; ms: number }> = [
    { label: "Router", ms: routerMs },
    { label: "Grader", ms: graderMs },
    { label: "Critic", ms: criticMs },
  ];

  return (
    <div className="mt-3 space-y-1 text-xs">
      <div className="font-semibold text-gray-600">Latency breakdown</div>
      {rows.map(({ label, ms }) => (
        <div key={label} className="flex items-center gap-2">
          <span className="w-12 shrink-0 text-gray-500">{label}</span>
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
  return (
    <details open className="mt-2 text-xs">
      <summary className="cursor-pointer select-none font-semibold text-gray-500">
        Agent Trace ({steps.length} steps)
      </summary>
      <div className="mt-2 space-y-2">
        {steps.map((step, i) => {
          const isLast = i === steps.length - 1;
          return (
            <div key={`${step.node}-${i}`} className="relative">
              {step.node === "router" && <RouterCard step={step} />}
              {step.node === "grader" && <GraderCard step={step} />}
              {step.node === "critic" && <CriticCard step={step} />}
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
