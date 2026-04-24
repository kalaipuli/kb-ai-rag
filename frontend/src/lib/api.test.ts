import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { getCollections, triggerIngest } from "./api";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeOkResponse(body: unknown, status = 200): Response {
  return {
    ok: true,
    status,
    json: () => Promise.resolve(body),
  } as unknown as Response;
}

function makeErrorResponse(status: number): Response {
  return {
    ok: false,
    status,
    json: () => Promise.reject(new Error("should not call .json() on error response")),
  } as unknown as Response;
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe("api — getCollections", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("getCollections_when_fetch_succeeds_returns_collections_response", async () => {
    const payload = {
      collections: [{ name: "kb", document_count: 10, vector_count: 100 }],
    };
    vi.mocked(fetch).mockResolvedValueOnce(makeOkResponse(payload));

    const result = await getCollections();

    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith("/api/proxy/collections");
    expect(result).toEqual(payload);
  });

  it("getCollections_when_fetch_returns_empty_collections_returns_empty_array", async () => {
    const payload = { collections: [] };
    vi.mocked(fetch).mockResolvedValueOnce(makeOkResponse(payload));

    const result = await getCollections();

    expect(result.collections).toEqual([]);
  });

  it("getCollections_when_server_returns_503_throws_error_with_status", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(makeErrorResponse(503));

    await expect(getCollections()).rejects.toThrow("503");
  });

  it("getCollections_when_server_returns_401_throws_error_with_status", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(makeErrorResponse(401));

    await expect(getCollections()).rejects.toThrow("401");
  });

  it("getCollections_when_network_throws_propagates_error", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("Network failure"));

    await expect(getCollections()).rejects.toThrow("Network failure");
  });
});

describe("api — triggerIngest", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("triggerIngest_when_fetch_succeeds_returns_ingest_accepted_response", async () => {
    const payload = { status: "accepted", message: "Ingestion started" };
    vi.mocked(fetch).mockResolvedValueOnce(makeOkResponse(payload));

    const result = await triggerIngest();

    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith("/api/proxy/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    expect(result).toEqual(payload);
  });

  it("triggerIngest_when_server_returns_503_throws_error_with_status", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(makeErrorResponse(503));

    await expect(triggerIngest()).rejects.toThrow("503");
  });

  it("triggerIngest_when_server_returns_500_throws_error_with_status", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(makeErrorResponse(500));

    await expect(triggerIngest()).rejects.toThrow("500");
  });

  it("triggerIngest_when_network_throws_propagates_error", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error("Connection refused"));

    await expect(triggerIngest()).rejects.toThrow("Connection refused");
  });
});
