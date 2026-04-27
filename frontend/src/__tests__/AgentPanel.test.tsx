import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AgentPanel } from "@/components/AgentPanel";
import type { AgentMessage, AgentStep } from "@/types";

const steps: AgentStep[] = [
  {
    node: "router",
    payload: { query_type: "factual", strategy: "dense", duration_ms: 50 },
    timestamp: "",
  },
  {
    node: "grader",
    payload: { scores: [0.8], web_fallback: false, duration_ms: 80 },
    timestamp: "",
  },
  {
    node: "critic",
    payload: { hallucination_risk: 0.2, reruns: 0, duration_ms: 30 },
    timestamp: "",
  },
];

function makeAgentMsg(id: string): AgentMessage {
  return {
    id,
    role: "assistant",
    content: "Answer",
    timestamp: "",
    agentSteps: steps,
  };
}

describe("AgentPanel", () => {
  it("only the last message trace receives isStreaming=true when panel is streaming", () => {
    const messages: AgentMessage[] = [makeAgentMsg("msg-1"), makeAgentMsg("msg-2")];
    render(<AgentPanel messages={messages} isStreaming={true} error={null} />);

    // There are two AgentTrace instances. LatencyBars renders only when isStreaming=false.
    // The first (completed) message should show latency breakdown — its trace gets isStreaming=false.
    // The second (last, still streaming) message should NOT show latency breakdown.
    const latencyHeadings = screen.getAllByText("Latency breakdown");
    expect(latencyHeadings).toHaveLength(1);
  });

  it("all traces show latency bars when isStreaming=false", () => {
    const messages: AgentMessage[] = [makeAgentMsg("msg-1"), makeAgentMsg("msg-2")];
    render(<AgentPanel messages={messages} isStreaming={false} error={null} />);

    const latencyHeadings = screen.getAllByText("Latency breakdown");
    expect(latencyHeadings).toHaveLength(2);
  });

  it("renders error banner when error prop is non-null", () => {
    render(
      <AgentPanel
        messages={[]}
        isStreaming={false}
        error={new Error("something failed")}
      />,
    );
    expect(screen.getByText("something failed")).toBeInTheDocument();
  });
});
