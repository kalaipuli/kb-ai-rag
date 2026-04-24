import { type NextRequest } from "next/server";
import { BACKEND_URL, API_KEY } from "@/lib/config";

export async function POST(req: NextRequest): Promise<Response> {
  const body: unknown = await req.json();
  const upstream = await fetch(`${BACKEND_URL}/api/v1/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(null, { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
