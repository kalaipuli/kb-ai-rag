import type {
  CollectionsResponse,
  IngestAcceptedResponse,
} from "@/types";

export async function getCollections(): Promise<CollectionsResponse> {
  const res = await fetch("/api/proxy/collections");
  if (!res.ok) {
    throw new Error(`Failed to fetch collections: ${res.status}`);
  }
  return res.json() as Promise<CollectionsResponse>;
}

export async function triggerIngest(): Promise<IngestAcceptedResponse> {
  const res = await fetch("/api/proxy/ingest", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Ingest failed: ${res.status}`);
  }
  return res.json() as Promise<IngestAcceptedResponse>;
}
