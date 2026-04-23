import type { ApiError, HealthResponse, Session, IngestResponse } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Parses the `detail` field of an ApiError into a human-readable string.
 *
 * FastAPI returns `detail: string` for domain errors (KBRagError) and a
 * JSON-stringified validation list for 422 errors. This helper handles both.
 */
export function parseApiError(error: ApiError): string {
  try {
    const parsed: unknown = JSON.parse(error.detail);
    if (Array.isArray(parsed)) {
      return (parsed as Array<{ msg: string }>)
        .map((e) => e.msg)
        .join(", ");
    }
  } catch {
    // not JSON — return as-is
  }
  return error.detail;
}
const API_KEY = process.env.API_KEY ?? "";

function authHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
  };
}

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/api/v1/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json() as Promise<HealthResponse>;
}

export async function getSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/api/v1/sessions`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch sessions: ${res.status}`);
  }
  return res.json() as Promise<Session[]>;
}

export async function triggerIngest(): Promise<IngestResponse> {
  const res = await fetch(`${API_URL}/api/v1/ingest`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Ingest failed: ${res.status}`);
  }
  return res.json() as Promise<IngestResponse>;
}
