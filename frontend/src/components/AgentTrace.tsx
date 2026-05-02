"use client";

import { useState } from "react";
import type { JSX } from "react";
import type { AgentStep, AgentStepNode, RouterStepPayload, RetrieverStepPayload } from "@/types";
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

function criticRiskColor(score: number): string {
  if (score < 0.4) return 'var(--status-success)';
  if (score <= 0.7) return 'var(--status-warning)';
  return 'var(--status-danger)';
}

function CardWrapper({ children, index }: { children: React.ReactNode; index: number }): JSX.Element {
  return (
    <div
      className="rounded-lg p-3 text-xs animate-fade-in"
      style={{
        background: 'var(--surface-overlay)',
        borderLeft: '4px solid var(--agentic)',
        animationDelay: `${index * 80}ms`,
        animationFillMode: 'both',
      }}
    >
      {children}
    </div>
  );
}

function NodeLabel({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <div className="mb-2 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-primary)' }}>
      {children}
    </div>
  );
}

function IterationBadge({ run }: { run: number | undefined }): JSX.Element | null {
  if (run === undefined || run <= 1) return null;
  return (
    <span
      className="ml-1 rounded-full px-1.5 py-0.5 text-xs"
      style={{ background: 'var(--status-warning)', color: 'white' }}
    >
      #{run}
    </span>
  );
}

function RouterCard({ step, run, index }: { step: AgentStep; run?: number; index: number }): JSX.Element | null {
  if (!isRouterPayload(step.payload)) return null;
  const { query_type, strategy, duration_ms } = step.payload;
  return (
    <CardWrapper index={index}>
      <NodeLabel>Router <IterationBadge run={run} /></NodeLabel>
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full px-2 py-0.5" style={{ background: 'var(--accent-muted)', color: 'var(--accent-primary)' }}>
          {QUERY_TYPE_LABELS[query_type]}
        </span>
        <span className="rounded-full px-2 py-0.5" style={{ background: 'var(--surface-raised)', color: 'var(--text-secondary)' }}>
          {STRATEGY_LABELS[strategy]}
        </span>
      </div>
      <div className="mt-1" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{duration_ms}ms</div>
    </CardWrapper>
  );
}

function RetrieverCard({ step, run, index }: { step: AgentStep; run?: number; index: number }): JSX.Element | null {
  if (!isRetrieverPayload(step.payload)) return null;
  const { strategy, docs_retrieved, duration_ms } = step.payload;
  return (
    <CardWrapper index={index}>
      <NodeLabel>Retriever <IterationBadge run={run} /></NodeLabel>
      <div className="flex flex-wrap gap-2">
        <span className="rounded-full px-2 py-0.5" style={{ background: 'var(--surface-raised)', color: 'var(--text-secondary)' }}>
          {RETRIEVER_STRATEGY_LABELS[strategy]}
        </span>
        <span style={{ color: 'var(--text-muted)' }}>{docs_retrieved} docs retrieved</span>
      </div>
      <div className="mt-1" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{duration_ms}ms</div>
    </CardWrapper>
  );
}

function GraderCard({ step, run, index }: { step: AgentStep; run?: number; index: number }): JSX.Element | null {
  if (!isGraderPayload(step.payload)) return null;
  const { scores, web_fallback, duration_ms } = step.payload;
  return (
    <CardWrapper index={index}>
      <NodeLabel>Grader <IterationBadge run={run} /></NodeLabel>
      <div className="space-y-1">
        {scores.map((score, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: 'var(--border-subtle)' }}>
              <div
                className="h-full rounded-full"
                style={{ width: `${Math.min(score * 100, 100)}%`, background: 'var(--agentic)' }}
              />
            </div>
            <span className="w-8 text-right" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {score != null ? (score * 100).toFixed(0) : "—"}%
            </span>
          </div>
        ))}
      </div>
      {web_fallback && (
        <span className="mt-1 inline-block rounded-full px-2 py-0.5 text-xs" style={{ background: 'var(--status-warning)', color: 'white' }}>
          Web fallback
        </span>
      )}
      <div className="mt-1" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{duration_ms}ms</div>
    </CardWrapper>
  );
}

function GeneratorCard({ step, run, index }: { step: AgentStep; run?: number; index: number }): JSX.Element | null {
  if (!isGeneratorPayload(step.payload)) return null;
  const { docs_used, confidence, duration_ms } = step.payload;
  const fillColor = criticRiskColor(1 - confidence);
  return (
    <CardWrapper index={index}>
      <NodeLabel>Generator <IterationBadge run={run} /></NodeLabel>
      <div className="flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: 'var(--border-subtle)' }}>
          <div
            className="h-full rounded-full"
            style={{ width: `${confidence * 100}%`, backgroundColor: fillColor }}
          />
        </div>
        <span className="w-24 text-right" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {(confidence * 100).toFixed(0)}% confidence
        </span>
      </div>
      <div className="mt-1" style={{ color: 'var(--text-muted)' }}>{docs_used} docs</div>
      <div className="mt-0.5" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{duration_ms}ms</div>
    </CardWrapper>
  );
}

function CriticCard({ step, run, index }: { step: AgentStep; run?: number; index: number }): JSX.Element | null {
  if (!isCriticPayload(step.payload)) return null;
  const { hallucination_risk, reruns, duration_ms } = step.payload;
  const riskColor = criticRiskColor(hallucination_risk);
  return (
    <CardWrapper index={index}>
      <NodeLabel>Critic <IterationBadge run={run} /></NodeLabel>
      <div className="flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: 'var(--border-subtle)' }}>
          <div
            className="h-full rounded-full"
            style={{ width: `${Math.min(hallucination_risk * 100, 100)}%`, backgroundColor: riskColor }}
          />
        </div>
        <span className="w-12 text-right" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {hallucination_risk != null ? (hallucination_risk * 100).toFixed(0) : "—"}% risk
        </span>
      </div>
      {reruns > 0 && (
        <div className="mt-1" style={{ color: 'var(--text-muted)' }}>
          {reruns} rerun{reruns !== 1 ? "s" : ""}
        </div>
      )}
      <div className="mt-1" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{duration_ms}ms</div>
    </CardWrapper>
  );
}

const PIPELINE_ORDER: AgentStepNode[] = ["router", "retriever", "grader", "generator", "critic"];
const PIPELINE_LABELS: Record<AgentStepNode, string> = {
  router: "Router",
  retriever: "Retriever",
  grader: "Grader",
  generator: "Generator",
  critic: "Critic",
};

function GhostCard({ nodeName, isPending, index }: { nodeName: string; isPending: boolean; index: number }): JSX.Element {
  return (
    <div
      className="rounded-lg p-3 text-xs"
      style={{
        background: 'var(--surface-overlay)',
        borderLeft: '4px solid var(--border-subtle)',
        opacity: 0.45,
        animationDelay: `${index * 80}ms`,
      }}
    >
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
          {nodeName}
        </div>
        {isPending ? (
          <span
            className="inline-block h-2 w-2 animate-pulse rounded-full"
            style={{ background: 'var(--border-default)' }}
          />
        ) : (
          <span className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>—</span>
        )}
      </div>
    </div>
  );
}

function LatencyBars({ steps, isStreaming }: { steps: AgentStep[]; isStreaming: boolean }): JSX.Element | null {
  if (isStreaming) return null;
  const allNodesPresent = ["router", "retriever", "grader", "generator", "critic"].every(
    (n) => steps.some((s) => s.node === n),
  );
  if (!allNodesPresent) return null;

  const runCount = new Map<string, number>();
  const rows: Array<{ label: string; ms: number }> = steps.map((step) => {
    runCount.set(step.node, (runCount.get(step.node) ?? 0) + 1);
    const count = runCount.get(step.node)!;
    const nodeLabel =
      step.node === "router" ? "Router"
      : step.node === "retriever" ? "Retriever"
      : step.node === "grader" ? "Grader"
      : step.node === "generator" ? "Generator"
      : "Critic";
    const label = count > 1 ? `${nodeLabel} #${count}` : nodeLabel;
    const ms = (step.payload as { duration_ms: number }).duration_ms;
    return { label, ms };
  });

  const total = rows.reduce((sum, r) => sum + r.ms, 0);

  return (
    <div className="mt-3 space-y-1 text-xs">
      <div className="font-semibold" style={{ color: 'var(--text-secondary)' }}>Latency breakdown</div>
      {rows.map(({ label, ms }, i) => (
        <div key={`${label}-${i}`} className="flex items-center gap-2">
          <span className="w-20 shrink-0" style={{ color: 'var(--text-muted)' }}>{label}</span>
          <div className="flex-1 overflow-hidden rounded-full" style={{ background: 'var(--border-subtle)' }}>
            <div
              className="h-2 rounded-full animate-bar-fill"
              style={{
                ['--bar-target-width' as string]: `${total > 0 ? (ms / total) * 100 : 0}%`,
                background: 'var(--agentic)',
              }}
            />
          </div>
          <span className="w-12 text-right" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{ms}ms</span>
        </div>
      ))}
      <div className="pt-1 text-right" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Total: {total}ms</div>
    </div>
  );
}

export function AgentTrace({ steps, isStreaming }: AgentTraceProps): JSX.Element {
  const [collapsed, setCollapsed] = useState(false);
  const runCount = new Map<string, number>();

  return (
    <div className="mt-2 text-xs">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Router → Retriever → Grader → Generator → Critic
        </span>
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="ml-auto text-xs"
          style={{ color: 'var(--text-muted)' }}
        >
          {collapsed ? '▶ Show trace' : '▼ Hide trace'}
        </button>
      </div>
      {!collapsed && (
        <div className="space-y-2">
          {steps.map((step, i) => {
            runCount.set(step.node, (runCount.get(step.node) ?? 0) + 1);
            const run = runCount.get(step.node)!;
            return (
              <div key={`${step.node}-${i}`} className="relative">
                {step.node === "router" && <RouterCard step={step} run={run} index={i} />}
                {step.node === "retriever" && <RetrieverCard step={step} run={run} index={i} />}
                {step.node === "grader" && <GraderCard step={step} run={run} index={i} />}
                {step.node === "generator" && <GeneratorCard step={step} run={run} index={i} />}
                {step.node === "critic" && <CriticCard step={step} run={run} index={i} />}
                {i === steps.length - 1 && isStreaming && (
                  <div className="absolute right-2 top-2">
                    <span
                      className="inline-block h-3 w-3 animate-spin rounded-full border-2"
                      style={{ borderColor: 'var(--border-default)', borderTopColor: 'var(--agentic)' }}
                    />
                  </div>
                )}
              </div>
            );
          })}
          {PIPELINE_ORDER
            .filter((n) => !steps.some((s) => s.node === n))
            .map((n, i) => (
              <GhostCard
                key={n}
                nodeName={PIPELINE_LABELS[n]}
                isPending={isStreaming}
                index={steps.length + i}
              />
            ))}
        </div>
      )}
      <LatencyBars steps={steps} isStreaming={isStreaming} />
    </div>
  );
}
