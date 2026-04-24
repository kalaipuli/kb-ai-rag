import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { streamQuery } from "./streaming";
import type { StreamEvent } from "@/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a ReadableStream from one or more string chunks (SSE wire format). */
function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

function makeOkStreamResponse(body: ReadableStream<Uint8Array>): Response {
  return {
    ok: true,
    status: 200,
    body,
  } as unknown as Response;
}

function makeErrorResponse(status: number): Response {
  return {
    ok: false,
    status,
    body: null,
  } as unknown as Response;
}

function makeNullBodyResponse(): Response {
  return {
    ok: true,
    status: 200,
    body: null,
  } as unknown as Response;
}

/** Drain an async generator into an array. */
async function collect(
  gen: AsyncGenerator<StreamEvent>,
): Promise<StreamEvent[]> {
  const events: StreamEvent[] = [];
  for await (const e of gen) {
    events.push(e);
  }
  return events;
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe("streamQuery", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // -------------------------------------------------------------------------
  // Happy path
  // -------------------------------------------------------------------------

  it("streamQuery_when_server_sends_token_event_yields_token_event", async () => {
    const wire = 'data: {"type":"token","content":"Hello"}\n\n';
    vi.mocked(fetch).mockResolvedValueOnce(makeOkStreamResponse(makeStream([wire])));

    const events = await collect(streamQuery({ query: "test?" }));

    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({ type: "token", content: "Hello" });
  });

  it("streamQuery_when_server_sends_token_citations_done_yields_all_events", async () => {
    const citation = {
      chunk_id: "c1",
      filename: "doc.pdf",
      source_path: "/docs/doc.pdf",
      page_number: 3,
    };
    const wire = [
      'data: {"type":"token","content":"hi"}\n\n',
      `data: {"type":"citations","citations":[${JSON.stringify(citation)}],"confidence":0.87}\n\n`,
      'data: {"type":"done"}\n\n',
    ].join("");

    vi.mocked(fetch).mockResolvedValueOnce(makeOkStreamResponse(makeStream([wire])));

    const events = await collect(streamQuery({ query: "what?" }));

    expect(events).toHaveLength(3);
    expect(events[0]).toEqual({ type: "token", content: "hi" });
    expect(events[1]).toEqual({
      type: "citations",
      citations: [citation],
      confidence: 0.87,
    });
    expect(events[2]).toEqual({ type: "done" });
  });

  it("streamQuery_when_events_arrive_in_multiple_chunks_reassembles_and_yields_correctly", async () => {
    // Simulate a token event split across two network chunks
    const part1 = 'data: {"type":"token","cont';
    const part2 = 'ent":"split"}\n\n';
    vi.mocked(fetch).mockResolvedValueOnce(
      makeOkStreamResponse(makeStream([part1, part2])),
    );

    const events = await collect(streamQuery({ query: "test?" }));

    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({ type: "token", content: "split" });
  });

  it("streamQuery_passes_query_payload_to_fetch_as_json_body", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      makeOkStreamResponse(makeStream(['data: {"type":"done"}\n\n'])),
    );

    await collect(streamQuery({ query: "hello", k: 5 }));

    expect(fetch).toHaveBeenCalledWith("/api/proxy/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "hello", k: 5 }),
    });
  });

  // -------------------------------------------------------------------------
  // Network error path
  // -------------------------------------------------------------------------

  it("streamQuery_when_fetch_throws_calls_onError_and_yields_no_events", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("Network failure"));

    const onError = vi.fn();
    const events = await collect(streamQuery({ query: "test?" }, onError));

    expect(events).toHaveLength(0);
    expect(onError).toHaveBeenCalledOnce();
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect((onError.mock.calls[0][0] as Error).message).toBe("Network failure");
  });

  it("streamQuery_when_fetch_throws_non_error_wraps_in_error_and_calls_onError", async () => {
    vi.mocked(fetch).mockRejectedValueOnce("plain string error");

    const onError = vi.fn();
    await collect(streamQuery({ query: "test?" }, onError));

    expect(onError).toHaveBeenCalledOnce();
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
  });

  // -------------------------------------------------------------------------
  // Non-OK HTTP status
  // -------------------------------------------------------------------------

  it("streamQuery_when_server_returns_503_calls_onError_with_status_in_message", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(makeErrorResponse(503));

    const onError = vi.fn();
    const events = await collect(streamQuery({ query: "test?" }, onError));

    expect(events).toHaveLength(0);
    expect(onError).toHaveBeenCalledOnce();
    expect((onError.mock.calls[0][0] as Error).message).toContain("503");
  });

  it("streamQuery_when_server_returns_401_calls_onError_with_status_in_message", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(makeErrorResponse(401));

    const onError = vi.fn();
    await collect(streamQuery({ query: "test?" }, onError));

    expect((onError.mock.calls[0][0] as Error).message).toContain("401");
  });

  // -------------------------------------------------------------------------
  // Null body
  // -------------------------------------------------------------------------

  it("streamQuery_when_response_body_is_null_calls_onError", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(makeNullBodyResponse());

    const onError = vi.fn();
    const events = await collect(streamQuery({ query: "test?" }, onError));

    expect(events).toHaveLength(0);
    expect(onError).toHaveBeenCalledOnce();
    expect((onError.mock.calls[0][0] as Error).message).toContain("null");
  });

  // -------------------------------------------------------------------------
  // Malformed JSON
  // -------------------------------------------------------------------------

  it("streamQuery_when_stream_contains_malformed_json_skips_bad_line_and_yields_valid_events", async () => {
    const wire = [
      'data: {"type":"token","content":"before"}\n\n',
      "data: not-valid-json\n\n",
      'data: {"type":"done"}\n\n',
    ].join("");
    vi.mocked(fetch).mockResolvedValueOnce(makeOkStreamResponse(makeStream([wire])));

    const events = await collect(streamQuery({ query: "test?" }));

    // The bad line must be skipped; valid events before and after are kept
    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ type: "token", content: "before" });
    expect(events[1]).toEqual({ type: "done" });
  });

  it("streamQuery_when_stream_is_entirely_malformed_yields_no_events_and_no_error", async () => {
    const wire = "data: {broken\n\ndata: also-bad\n\n";
    vi.mocked(fetch).mockResolvedValueOnce(makeOkStreamResponse(makeStream([wire])));

    const onError = vi.fn();
    const events = await collect(streamQuery({ query: "test?" }, onError));

    expect(events).toHaveLength(0);
    // malformed JSON is silently skipped — onError is NOT called for parse errors
    expect(onError).not.toHaveBeenCalled();
  });

  // -------------------------------------------------------------------------
  // Empty stream
  // -------------------------------------------------------------------------

  it("streamQuery_when_server_sends_empty_stream_yields_no_events", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(makeOkStreamResponse(makeStream([])));

    const events = await collect(streamQuery({ query: "test?" }));

    expect(events).toHaveLength(0);
  });

  // -------------------------------------------------------------------------
  // Lines without data: prefix are ignored
  // -------------------------------------------------------------------------

  it("streamQuery_when_stream_contains_non_data_lines_ignores_them", async () => {
    const wire = ": keep-alive\n\ndata: {\"type\":\"done\"}\n\n";
    vi.mocked(fetch).mockResolvedValueOnce(makeOkStreamResponse(makeStream([wire])));

    const events = await collect(streamQuery({ query: "test?" }));

    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({ type: "done" });
  });
});
