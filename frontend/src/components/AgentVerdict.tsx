"use client";

import type { JSX } from "react";
import type { AgentMessage, Message } from "@/types";
import { isCriticPayload, isRetrieverPayload } from "@/lib/agentTypeGuards";

interface AgentVerdictProps {
  staticMessages: Message[];
  agentMessages: AgentMessage[];
}

type VerdictWinner = "agentic" | "static" | "tie";

interface Verdict {
  winner: VerdictWinner;
  reason: string;
  agentConf: number;
  staticConf: number;
}

function computeVerdict(
  staticMessages: Message[],
  agentMessages: AgentMessage[],
): Verdict {
  const lastStaticAssistant = [...staticMessages]
    .reverse()
    .find((m) => m.role === "assistant");
  const lastAgentAssistant = [...agentMessages]
    .reverse()
    .find((m) => m.role === "assistant");

  const staticConf = lastStaticAssistant?.confidence ?? 0;
  const agentConf = lastAgentAssistant?.confidence ?? 0;
  const agentSteps = lastAgentAssistant?.agentSteps ?? [];

  const criticStep = agentSteps.find((s) => s.node === "critic");

  const criticScore =
    criticStep && isCriticPayload(criticStep.payload)
      ? criticStep.payload.hallucination_risk
      : 0;

  const retrieverWebStep = agentSteps.find(
    (s) => s.node === "retriever" && isRetrieverPayload(s.payload) && s.payload.strategy === "web"
  );
  const webFallbackUsed = retrieverWebStep !== undefined;

  if (criticScore > 0.7) {
    return { winner: "static", reason: "Agentic pipeline flagged high hallucination risk", agentConf, staticConf };
  }
  if (webFallbackUsed) {
    return {
      winner: "agentic",
      reason: "Agentic pipeline used web search for missing knowledge",
      agentConf,
      staticConf,
    };
  }
  if (agentConf > staticConf + 0.1) {
    return { winner: "agentic", reason: "Higher confidence answer via agentic reasoning", agentConf, staticConf };
  }
  return { winner: "tie", reason: "Both pipelines produced comparable answers", agentConf, staticConf };
}

const BORDER_COLORS: Record<VerdictWinner, string> = {
  agentic: 'var(--agentic)',
  static: 'var(--static-chain)',
  tie: 'var(--border-default)',
};

const WINNER_LABELS: Record<VerdictWinner, string> = {
  agentic: '🔮 Agentic Pipeline wins',
  static: '⚡ Static Chain wins',
  tie: '≈ Comparable Results',
};

export function AgentVerdict({
  staticMessages,
  agentMessages,
}: AgentVerdictProps): JSX.Element | null {
  const hasStaticAssistant = staticMessages.some((m) => m.role === "assistant");
  const hasAgentAssistant = agentMessages.some((m) => m.role === "assistant");

  if (!hasStaticAssistant || !hasAgentAssistant) return null;

  const verdict = computeVerdict(staticMessages, agentMessages);
  const delta = Math.abs(verdict.agentConf - verdict.staticConf);

  return (
    <div
      className="flex items-center gap-4 px-4 py-3 animate-slide-down"
      style={{
        background: 'var(--surface-raised)',
        borderLeft: `4px solid ${BORDER_COLORS[verdict.winner]}`,
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
        {WINNER_LABELS[verdict.winner]}
      </span>
      {delta > 0 && (
        <span
          className="text-xs px-2 py-0.5 rounded"
          style={{
            fontFamily: 'var(--font-mono)',
            background: 'var(--surface-overlay)',
            color: 'var(--text-secondary)',
          }}
        >
          +{(delta * 100).toFixed(0)}% confidence
        </span>
      )}
      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        {verdict.reason}
      </span>
    </div>
  );
}
