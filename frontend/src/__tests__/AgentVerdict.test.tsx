import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentVerdict } from "@/components/AgentVerdict";
import type { AgentMessage, AgentStep, Message } from "@/types";

function makeStaticAssistant(overrides: Partial<Message> = {}): Message {
  return {
    id: "s1",
    role: "assistant",
    content: "Static answer",
    timestamp: new Date().toISOString(),
    confidence: 0.7,
    ...overrides,
  };
}

function makeAgentAssistant(
  agentSteps: AgentStep[] = [],
  overrides: Partial<AgentMessage> = {},
): AgentMessage {
  return {
    id: "a1",
    role: "assistant",
    content: "Agentic answer",
    timestamp: new Date().toISOString(),
    confidence: 0.75,
    agentSteps,
    ...overrides,
  };
}

const graderStepNoFallback: AgentStep = {
  node: "grader",
  payload: { scores_all: [0.8], passed_count: 1, threshold: 0.5, all_below_threshold: false, duration_ms: 60 },
  timestamp: new Date().toISOString(),
};

// Web fallback is now detected via retriever strategy, not grader payload
const retrieverWebStep: AgentStep = {
  node: "retriever",
  payload: { strategy: "web", docs_retrieved: 3, duration_ms: 200 },
  timestamp: new Date().toISOString(),
};

const criticStepLowRisk: AgentStep = {
  node: "critic",
  payload: { hallucination_risk: 0.2, reruns: 0, duration_ms: 30 },
  timestamp: new Date().toISOString(),
};

const criticStepHighRisk: AgentStep = {
  node: "critic",
  payload: { hallucination_risk: 0.85, reruns: 1, duration_ms: 30 },
  timestamp: new Date().toISOString(),
};

describe("AgentVerdict", () => {
  it("does not render when staticMessages has no assistant message", () => {
    const { container } = render(
      <AgentVerdict
        staticMessages={[{ id: "u1", role: "user", content: "Q", timestamp: "" }]}
        agentMessages={[makeAgentAssistant()]}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("does not render when agentMessages has no assistant message", () => {
    const { container } = render(
      <AgentVerdict
        staticMessages={[makeStaticAssistant()]}
        agentMessages={[{ id: "u1", role: "user", content: "Q", timestamp: "" }]}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders agentic verdict when retriever used web strategy", () => {
    render(
      <AgentVerdict
        staticMessages={[makeStaticAssistant({ confidence: 0.7 })]}
        agentMessages={[
          makeAgentAssistant([retrieverWebStep, graderStepNoFallback, criticStepLowRisk], { confidence: 0.7 }),
        ]}
      />,
    );
    expect(screen.getByText(/Agentic Pipeline wins/)).toBeInTheDocument();
    expect(
      screen.getByText("Agentic pipeline used web search for missing knowledge"),
    ).toBeInTheDocument();
  });

  it("does not flag web fallback when retriever strategy is hybrid", () => {
    const retrieverHybridStep: AgentStep = {
      node: "retriever",
      payload: { strategy: "hybrid", docs_retrieved: 5, duration_ms: 120 },
      timestamp: new Date().toISOString(),
    };
    render(
      <AgentVerdict
        staticMessages={[makeStaticAssistant({ confidence: 0.7 })]}
        agentMessages={[
          makeAgentAssistant([retrieverHybridStep, graderStepNoFallback, criticStepLowRisk], { confidence: 0.7 }),
        ]}
      />,
    );
    expect(screen.queryByText("Agentic pipeline used web search for missing knowledge")).not.toBeInTheDocument();
  });

  it("renders static verdict when criticScore > 0.7", () => {
    render(
      <AgentVerdict
        staticMessages={[makeStaticAssistant({ confidence: 0.6 })]}
        agentMessages={[
          makeAgentAssistant([graderStepNoFallback, criticStepHighRisk], { confidence: 0.9 }),
        ]}
      />,
    );
    expect(screen.getByText(/Static Chain wins/)).toBeInTheDocument();
    expect(
      screen.getByText("Agentic pipeline flagged high hallucination risk"),
    ).toBeInTheDocument();
  });

  it("renders comparable results verdict when confidence difference is <= 0.1", () => {
    render(
      <AgentVerdict
        staticMessages={[makeStaticAssistant({ confidence: 0.75 })]}
        agentMessages={[
          makeAgentAssistant([graderStepNoFallback, criticStepLowRisk], { confidence: 0.78 }),
        ]}
      />,
    );
    expect(screen.getByText(/≈ Comparable Results/)).toBeInTheDocument();
    expect(
      screen.getByText("Both pipelines produced comparable answers"),
    ).toBeInTheDocument();
  });

  it("renders agentic verdict when agentConf > staticConf + 0.1", () => {
    render(
      <AgentVerdict
        staticMessages={[makeStaticAssistant({ confidence: 0.6 })]}
        agentMessages={[
          makeAgentAssistant([graderStepNoFallback, criticStepLowRisk], { confidence: 0.75 }),
        ]}
      />,
    );
    expect(screen.getByText(/Agentic Pipeline wins/)).toBeInTheDocument();
    expect(
      screen.getByText("Higher confidence answer via agentic reasoning"),
    ).toBeInTheDocument();
  });
});
