import type { Citation, DonePayload, QueryRequest, StreamEvent } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_KEY ?? "";

export async function* streamQuery(
  payload: QueryRequest,
  onError?: (err: Error) => void
): AsyncGenerator<StreamEvent> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
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
  let currentEventType = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          try {
            const parsed: unknown = JSON.parse(raw);
            yield {
              type: currentEventType as StreamEvent["type"],
              data: parsed as string | Citation[] | DonePayload,
            };
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
