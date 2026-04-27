import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentTrace } from "@/components/AgentTrace";
import type { AgentStep } from "@/types";

const routerStep: AgentStep = {
  node: "router",
  payload: { query_type: "factual", strategy: "dense", duration_ms: 50 },
  timestamp: new Date().toISOString(),
};

const graderStep: AgentStep = {
  node: "grader",
  payload: { scores: [0.8, 0.6], web_fallback: false, duration_ms: 80 },
  timestamp: new Date().toISOString(),
};

const criticStep: AgentStep = {
  node: "critic",
  payload: { hallucination_risk: 0.2, reruns: 0, duration_ms: 30 },
  timestamp: new Date().toISOString(),
};

describe("AgentTrace", () => {
  it("renders details element in the DOM", () => {
    const { container } = render(
      <AgentTrace steps={[routerStep]} isStreaming={false} />,
    );
    expect(container.querySelector("details")).toBeInTheDocument();
  });

  it("router card renders human-readable label not raw enum value", () => {
    render(<AgentTrace steps={[routerStep]} isStreaming={false} />);
    expect(screen.getByText("Direct fact lookup")).toBeInTheDocument();
    expect(screen.queryByText("factual")).not.toBeInTheDocument();
  });

  it("router card renders human-readable strategy label", () => {
    render(<AgentTrace steps={[routerStep]} isStreaming={false} />);
    expect(screen.getByText("Dense search")).toBeInTheDocument();
    expect(screen.queryByText("dense")).not.toBeInTheDocument();
  });

  it("critic card renders bg-green-500 for low hallucination risk", () => {
    const { container } = render(
      <AgentTrace steps={[criticStep]} isStreaming={false} />,
    );
    expect(container.querySelector(".bg-green-500")).toBeInTheDocument();
  });

  it("critic card renders bg-amber-500 for medium hallucination risk", () => {
    const mediumCriticStep: AgentStep = {
      node: "critic",
      payload: { hallucination_risk: 0.55, reruns: 0, duration_ms: 30 },
      timestamp: new Date().toISOString(),
    };
    const { container } = render(
      <AgentTrace steps={[mediumCriticStep]} isStreaming={false} />,
    );
    expect(container.querySelector(".bg-amber-500")).toBeInTheDocument();
  });

  it("critic card renders bg-red-500 for high hallucination risk", () => {
    const highCriticStep: AgentStep = {
      node: "critic",
      payload: { hallucination_risk: 0.9, reruns: 1, duration_ms: 30 },
      timestamp: new Date().toISOString(),
    };
    const { container } = render(
      <AgentTrace steps={[highCriticStep]} isStreaming={false} />,
    );
    expect(container.querySelector(".bg-red-500")).toBeInTheDocument();
  });

  it("latency bars not rendered while isStreaming is true", () => {
    render(
      <AgentTrace
        steps={[routerStep, graderStep, criticStep]}
        isStreaming={true}
      />,
    );
    expect(screen.queryByText("Latency breakdown")).not.toBeInTheDocument();
  });

  it("latency bars rendered when isStreaming is false", () => {
    render(
      <AgentTrace
        steps={[routerStep, graderStep, criticStep]}
        isStreaming={false}
      />,
    );
    expect(screen.getByText("Latency breakdown")).toBeInTheDocument();
  });

  it("summary shows step count", () => {
    render(
      <AgentTrace steps={[routerStep, graderStep]} isStreaming={false} />,
    );
    expect(screen.getByText("Agent Trace (2 steps)")).toBeInTheDocument();
  });
});
