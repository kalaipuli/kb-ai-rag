import { NextResponse } from "next/server";
import { BACKEND_URL, API_KEY } from "@/lib/config";

export async function POST(): Promise<NextResponse> {
  const res = await fetch(`${BACKEND_URL}/api/v1/ingest`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY, "Content-Type": "application/json" },
  });
  const data: unknown = await res.json();
  return NextResponse.json(data, { status: res.status });
}
