import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useAgentStream } from "@/hooks/useAgentStream";
import * as streaming from "@/lib/streaming";
import type { AgentStreamEvent } from "@/types";

vi.mock("@/lib/streaming");

async function* makeAgentGenerator(
  events: AgentStreamEvent[],
): AsyncGenerator<AgentStreamEvent> {
  for (const event of events) {
    yield event;
  }
}

describe("useAgentStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("starts with empty state", () => {
    const { result } = renderHook(() => useAgentStream());
    expect(result.current.messages).toEqual([]);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("agent_step event appends to current message agentSteps", async () => {
    const events: AgentStreamEvent[] = [
      {
        type: "agent_step",
        node: "router",
        payload: {
          query_type: "factual",
          strategy: "dense",
          duration_ms: 42,
        },
      },
    ];
    vi.spyOn(streaming, "streamAgentQuery").mockReturnValue(makeAgentGenerator(events));

    const { result } = renderHook(() => useAgentStream());

    await act(async () => {
      await result.current.submit("test query");
    });

    const assistant = result.current.messages.find((m) => m.role === "assistant");
    expect(assistant?.agentSteps).toHaveLength(1);
    expect(assistant?.agentSteps?.[0].node).toBe("router");
  });

  it("token event appends to assistant message content", async () => {
    const events: AgentStreamEvent[] = [
      { type: "token", content: "Hello" },
      { type: "token", content: " world" },
    ];
    vi.spyOn(streaming, "streamAgentQuery").mockReturnValue(makeAgentGenerator(events));

    const { result } = renderHook(() => useAgentStream());

    await act(async () => {
      await result.current.submit("hi");
    });

    const assistant = result.current.messages.find((m) => m.role === "assistant");
    expect(assistant?.content).toBe("Hello world");
  });

  it("done event sets isStreaming to false", async () => {
    const events: AgentStreamEvent[] = [{ type: "done" }];
    vi.spyOn(streaming, "streamAgentQuery").mockReturnValue(makeAgentGenerator(events));

    const { result } = renderHook(() => useAgentStream());

    await act(async () => {
      await result.current.submit("hi");
    });

    expect(result.current.isStreaming).toBe(false);
  });

  it("submit is a no-op when isStreaming is true", async () => {
    vi.spyOn(streaming, "streamAgentQuery").mockImplementation(async function* () {
      yield { type: "token", content: "hello" } as AgentStreamEvent;
      await new Promise<void>(() => {
        /* never resolves */
      });
    });

    const { result } = renderHook(() => useAgentStream());
    const submitSpy = vi.spyOn(streaming, "streamAgentQuery");

    act(() => {
      void result.current.submit("first query");
    });

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(true);
    });

    const callCountBeforeSecondSubmit = submitSpy.mock.calls.length;

    await act(async () => {
      await result.current.submit("second query while streaming");
    });

    expect(submitSpy.mock.calls.length).toBe(callCountBeforeSecondSubmit);
  });

  it("sessionId is written to sessionStorage on first render and reused", () => {
    expect(sessionStorage.getItem("kb_rag_session_id")).toBeNull();

    const { result } = renderHook(() => useAgentStream());
    const id = result.current.sessionId;

    expect(id).toBeTruthy();
    expect(sessionStorage.getItem("kb_rag_session_id")).toBe(id);

    // Re-render hook — same session ID should come back
    const { result: result2 } = renderHook(() => useAgentStream());
    expect(result2.current.sessionId).toBe(id);
  });

  it("citations event sets citations and confidence on assistant message", async () => {
    const citations = [
      {
        chunk_id: "c1",
        filename: "doc.pdf",
        source_path: "/docs/doc.pdf",
        page_number: 1,
      },
    ];
    const events: AgentStreamEvent[] = [
      { type: "citations", citations, confidence: 0.95, chunks_retrieved: 3 },
    ];
    vi.spyOn(streaming, "streamAgentQuery").mockReturnValue(makeAgentGenerator(events));

    const { result } = renderHook(() => useAgentStream());

    await act(async () => {
      await result.current.submit("hi");
    });

    const assistant = result.current.messages.find((m) => m.role === "assistant");
    expect(assistant?.citations).toEqual(citations);
    expect(assistant?.confidence).toBe(0.95);
  });
});
