import type { AgentStreamEvent, QueryRequest, StreamEvent } from "@/types";

export async function* streamQuery(
  payload: QueryRequest,
  onError?: (err: Error) => void
): AsyncGenerator<StreamEvent> {
  let response: Response;
  try {
    response = await fetch("/api/proxy/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    const error = err instanceof Error ? err : new Error(String(err));
    onError?.(error);
    return;
  }

  if (!response.ok) {
    onError?.(new Error(`Query failed: ${response.status}`));
    return;
  }

  if (!response.body) {
    onError?.(new Error("Response body is null"));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          try {
            const parsed: unknown = JSON.parse(raw);
            yield parsed as StreamEvent;
          } catch {
            // skip malformed SSE line
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function* streamAgentQuery(
  payload: QueryRequest,
  sessionId: string,
  onError?: (err: Error) => void,
): AsyncGenerator<AgentStreamEvent> {
  let response: Response;
  try {
    response = await fetch("/api/proxy/query/agentic", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionId,
      },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    const error = err instanceof Error ? err : new Error(String(err));
    onError?.(error);
    return;
  }

  if (!response.ok) {
    onError?.(new Error(`Agentic query failed: ${response.status}`));
    return;
  }

  if (!response.body) {
    onError?.(new Error("Response body is null"));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          try {
            const parsed: unknown = JSON.parse(raw);
            yield parsed as AgentStreamEvent;
          } catch {
            // skip malformed SSE line
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
