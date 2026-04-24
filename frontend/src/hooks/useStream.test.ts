import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useStream } from "./useStream";
import * as streaming from "@/lib/streaming";
import type { StreamEvent, TokenEvent } from "@/types";

vi.mock("@/lib/streaming");

async function* makeGenerator(events: StreamEvent[]): AsyncGenerator<StreamEvent> {
  for (const event of events) {
    yield event;
  }
}

describe("useStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with empty state", () => {
    const { result } = renderHook(() => useStream());
    expect(result.current.messages).toEqual([]);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("appends user message immediately on submit and sets isStreaming", async () => {
    vi.spyOn(streaming, "streamQuery").mockReturnValue(makeGenerator([]));
    const { result } = renderHook(() => useStream());

    await act(async () => {
      await result.current.submit("What is the policy?");
    });

    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe("What is the policy?");
    expect(result.current.isStreaming).toBe(false);
  });

  it("accumulates token events into assistant message content", async () => {
    const events: StreamEvent[] = [
      { type: "token", content: "Hello" },
      { type: "token", content: " world" },
    ];
    vi.spyOn(streaming, "streamQuery").mockReturnValue(makeGenerator(events));
    const { result } = renderHook(() => useStream());

    await act(async () => {
      await result.current.submit("hi");
    });

    const assistant = result.current.messages.find((m) => m.role === "assistant");
    expect(assistant?.content).toBe("Hello world");
  });

  it("updates citations from citations event", async () => {
    const citations = [
      {
        chunk_id: "c1",
        filename: "doc.pdf",
        source_path: "/docs/doc.pdf",
        page_number: 3,
      },
    ];
    const events: StreamEvent[] = [
      { type: "citations", citations, confidence: 0.9 },
    ];
    vi.spyOn(streaming, "streamQuery").mockReturnValue(makeGenerator(events));
    const { result } = renderHook(() => useStream());

    await act(async () => {
      await result.current.submit("hi");
    });

    const assistant = result.current.messages.find((m) => m.role === "assistant");
    expect(assistant?.citations).toEqual(citations);
  });

  it("sets confidence and clears isStreaming on citations event", async () => {
    const events: StreamEvent[] = [
      {
        type: "citations",
        citations: [],
        confidence: 0.88,
      },
    ];
    vi.spyOn(streaming, "streamQuery").mockReturnValue(makeGenerator(events));
    const { result } = renderHook(() => useStream());

    await act(async () => {
      await result.current.submit("hi");
    });

    const assistant = result.current.messages.find((m) => m.role === "assistant");
    expect(assistant?.confidence).toBe(0.88);
    expect(result.current.isStreaming).toBe(false);
  });

  it("sets error state on network failure (error path)", async () => {
    vi.spyOn(streaming, "streamQuery").mockImplementation(
      (_payload, onError) => {
        onError?.(new Error("Network error"));
        return makeGenerator([]);
      },
    );
    const { result } = renderHook(() => useStream());

    await act(async () => {
      await result.current.submit("hi");
    });

    expect(result.current.error?.message).toBe("Network error");
    expect(result.current.isStreaming).toBe(false);
  });

  it("isStreaming is true while stream is in flight", async () => {
    // Generator yields one token then stalls indefinitely — simulates mid-stream state.
    vi.spyOn(streaming, "streamQuery").mockImplementation(async function* () {
      yield { type: "token", content: "hello" } as TokenEvent;
      await new Promise<void>(() => {
        /* never resolves — keeps the stream open */
      });
    });

    const { result } = renderHook(() => useStream());

    // Start submit but intentionally do not await — the stream is in flight.
    act(() => {
      void result.current.submit("test?");
    });

    // After the first token is dispatched, isStreaming must still be true.
    await waitFor(() => {
      expect(result.current.isStreaming).toBe(true);
    });
  });

  it("resets error via resetError", async () => {
    vi.spyOn(streaming, "streamQuery").mockImplementation(
      (_payload, onError) => {
        onError?.(new Error("fail"));
        return makeGenerator([]);
      },
    );
    const { result } = renderHook(() => useStream());

    await act(async () => {
      await result.current.submit("hi");
    });
    expect(result.current.error).not.toBeNull();

    act(() => result.current.resetError());
    expect(result.current.error).toBeNull();
  });
});
