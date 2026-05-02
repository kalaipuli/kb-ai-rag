"use client";

import type { JSX } from "react";
import type { AgentMessage, Message } from "@/types";
import { isCriticPayload, isGraderPayload } from "@/lib/agentTypeGuards";

interface AgentVerdictProps {
  staticMessages: Message[];
  agentMessages: AgentMessage[];
}

type VerdictWinner = "agentic" | "static" | "tie";

interface Verdict {
  winner: VerdictWinner;
  reason: string;
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
  const graderStep = agentSteps.find((s) => s.node === "grader");

  const criticRisk =
    criticStep && isCriticPayload(criticStep.payload)
      ? criticStep.payload.critic_score
      : 0;
  const webFallback =
    graderStep && isGraderPayload(graderStep.payload)
      ? graderStep.payload.web_fallback_used
      : false;

  if (criticRisk > 0.7) {
    return { winner: "static", reason: "Agentic pipeline flagged high hallucination risk" };
  }
  if (webFallback) {
    return {
      winner: "agentic",
      reason: "Agentic pipeline used web search for missing knowledge",
    };
  }
  if (agentConf > staticConf + 0.1) {
    return { winner: "agentic", reason: "Higher confidence answer via agentic reasoning" };
  }
  return { winner: "tie", reason: "Both pipelines produced comparable answers" };
}

const BADGE_CLASSES: Record<VerdictWinner, string> = {
  agentic: "bg-green-100 text-green-800",
  static: "bg-blue-100 text-blue-800",
  tie: "bg-gray-100 text-gray-700",
};

const BADGE_LABELS: Record<VerdictWinner, string> = {
  agentic: "Agentic Pipeline wins",
  static: "Static Chain wins",
  tie: "Tie",
};

export function AgentVerdict({
  staticMessages,
  agentMessages,
}: AgentVerdictProps): JSX.Element | null {
  const hasStaticAssistant = staticMessages.some((m) => m.role === "assistant");
  const hasAgentAssistant = agentMessages.some((m) => m.role === "assistant");

  if (!hasStaticAssistant || !hasAgentAssistant) return null;

  const verdict = computeVerdict(staticMessages, agentMessages);

  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-4 py-2 text-sm">
      <span
        className={`rounded-full px-3 py-0.5 text-xs font-semibold ${BADGE_CLASSES[verdict.winner]}`}
      >
        {BADGE_LABELS[verdict.winner]}
      </span>
      <span className="text-gray-600">{verdict.reason}</span>
    </div>
  );
}
