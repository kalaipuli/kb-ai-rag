import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentTrace } from "@/components/AgentTrace";
import type { AgentStep } from "@/types";

const routerStep: AgentStep = {
  node: "router",
  payload: { query_type: "factual", strategy: "dense", duration_ms: 50 },
  timestamp: new Date().toISOString(),
};

const retrieverStep: AgentStep = {
  node: "retriever",
  payload: { strategy: "hybrid", docs_retrieved: 5, duration_ms: 120 },
  timestamp: new Date().toISOString(),
};

const graderStep: AgentStep = {
  node: "grader",
  payload: { scores: [0.8, 0.6], web_fallback_used: false, duration_ms: 80 },
  timestamp: new Date().toISOString(),
};

const generatorStep: AgentStep = {
  node: "generator",
  payload: { docs_used: 3, confidence: 0.85, duration_ms: 200 },
  timestamp: new Date().toISOString(),
};

const criticStep: AgentStep = {
  node: "critic",
  payload: { critic_score: 0.2, reruns: 0, duration_ms: 30 },
  timestamp: new Date().toISOString(),
};

const allFiveSteps = [routerStep, retrieverStep, graderStep, generatorStep, criticStep];

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
      payload: { critic_score: 0.55, reruns: 0, duration_ms: 30 },
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
      payload: { critic_score: 0.9, reruns: 1, duration_ms: 30 },
      timestamp: new Date().toISOString(),
    };
    const { container } = render(
      <AgentTrace steps={[highCriticStep]} isStreaming={false} />,
    );
    expect(container.querySelector(".bg-red-500")).toBeInTheDocument();
  });

  it("latency bars not rendered while isStreaming is true", () => {
    render(
      <AgentTrace steps={allFiveSteps} isStreaming={true} />,
    );
    expect(screen.queryByText("Latency breakdown")).not.toBeInTheDocument();
  });

  it("latency bars rendered when all 5 nodes present and isStreaming is false", () => {
    render(
      <AgentTrace steps={allFiveSteps} isStreaming={false} />,
    );
    expect(screen.getByText("Latency breakdown")).toBeInTheDocument();
  });

  it("latency bars hidden when retriever node is missing", () => {
    render(
      <AgentTrace
        steps={[routerStep, graderStep, generatorStep, criticStep]}
        isStreaming={false}
      />,
    );
    expect(screen.queryByText("Latency breakdown")).not.toBeInTheDocument();
  });

  it("latency bars hidden when generator node is missing", () => {
    render(
      <AgentTrace
        steps={[routerStep, retrieverStep, graderStep, criticStep]}
        isStreaming={false}
      />,
    );
    expect(screen.queryByText("Latency breakdown")).not.toBeInTheDocument();
  });

  it("summary shows step count", () => {
    render(
      <AgentTrace steps={[routerStep, graderStep]} isStreaming={false} />,
    );
    expect(screen.getByText("Agent Trace (2 steps)")).toBeInTheDocument();
  });

  it("RetrieverCard renders strategy badge and docs count", () => {
    render(<AgentTrace steps={[retrieverStep]} isStreaming={false} />);
    expect(screen.getByText("Hybrid search")).toBeInTheDocument();
    expect(screen.getByText("5 docs retrieved")).toBeInTheDocument();
  });

  it("GeneratorCard renders confidence bar and docs count", () => {
    const { container } = render(
      <AgentTrace steps={[generatorStep]} isStreaming={false} />,
    );
    expect(screen.getByText("85% confidence")).toBeInTheDocument();
    expect(screen.getByText("3 docs")).toBeInTheDocument();
    // high confidence (0.85) → inverted risk (0.15) → bg-green-500
    expect(container.querySelector(".bg-green-500")).toBeInTheDocument();
  });

  it("topology reference text renders", () => {
    render(<AgentTrace steps={[routerStep]} isStreaming={false} />);
    expect(
      screen.getByText("Router → Retriever → Grader → Generator → Critic"),
    ).toBeInTheDocument();
  });

  it("second retriever step shows #2 iteration badge", () => {
    const retrieverStep2: AgentStep = {
      node: "retriever",
      payload: { strategy: "web", docs_retrieved: 3, duration_ms: 90 },
      timestamp: new Date().toISOString(),
    };
    render(
      <AgentTrace
        steps={[routerStep, retrieverStep, graderStep, retrieverStep2]}
        isStreaming={false}
      />,
    );
    expect(screen.getByText("#2")).toBeInTheDocument();
  });

  it("latency bars show per-run labels when a node repeats", () => {
    const retrieverStep2: AgentStep = {
      node: "retriever",
      payload: { strategy: "web", docs_retrieved: 3, duration_ms: 90 },
      timestamp: new Date().toISOString(),
    };
    const graderStep2: AgentStep = {
      node: "grader",
      payload: { scores: [0.9], web_fallback_used: false, duration_ms: 60 },
      timestamp: new Date().toISOString(),
    };
    render(
      <AgentTrace
        steps={[
          routerStep,
          retrieverStep,
          graderStep,
          retrieverStep2,
          graderStep2,
          generatorStep,
          criticStep,
        ]}
        isStreaming={false}
      />,
    );
    expect(screen.getByText("Latency breakdown")).toBeInTheDocument();
    expect(screen.getByText("Retriever #2")).toBeInTheDocument();
    expect(screen.getByText("Grader #2")).toBeInTheDocument();
  });
});
